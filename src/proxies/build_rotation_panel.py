"""
Build a player–team–match rotation panel by joining:

  - team–match panel with xPts (from odds)      [matches_with_injuries_all_seasons.csv]
  - Understat per-player match minutes/starts  [understat_player_matches_master.csv]

Output (one row per player–team–match):
  - <cfg.processed>/panel_rotation.csv
  - <cfg.processed>/panel_rotation.parquet   (optional; skipped if parquet engine missing)

Notes:
- This script is a preprocessing/proxy-builder step. main.py may read the already-produced
  CSV rather than rebuilding from scratch.
- Can use --dry-run to validate inputs, merges, and output schema without writing files.
"""

from __future__ import annotations
from pathlib import Path
import argparse

import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.validation.checks import assert_non_empty, require_columns


# ----------------------------
# Helpers
# ----------------------------

def _normalize_date(s: pd.Series) -> pd.Series:
    """Normalize timestamps to midnight (date-only) so joins are robust to time components."""
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def _assert_unique_keys(df: pd.DataFrame, keys: list[str], name: str, logger) -> None:
    """Fail fast if keys are not unique (prevents many-to-many merges)."""
    require_columns(df, keys, name=name)
    dup = df.duplicated(keys).sum()
    if dup > 0:
        example = df.loc[df.duplicated(keys, keep=False), keys].head(10)
        msg = f"[{name}] Found {dup} duplicate rows on keys={keys}. Example:\n{example}"
        logger.error(msg)
        raise ValueError(msg)


# ----------------------------
# Loaders
# ----------------------------

def load_matches(matches_path: Path, logger) -> pd.DataFrame:
    """
    Load team–match data with xPts.

    Expected input columns:
      Season, MatchID, Date, Team, Opponent, is_home, xPts

    Returns (standardised schema):
      season, season_label, date, team_id, opponent_id, match_id, is_home, xpts

    Uniqueness:
      Enforces uniqueness on (season, date, team_id), which should be one row per team per league match.
    """
    if not matches_path.exists():
        raise FileNotFoundError(
            f"{matches_path} not found. Run build_match_panel.py and add_injuries_to_matches.py first."
        )

    df = pd.read_csv(matches_path)

    require_columns(
        df,
        ["Season", "MatchID", "Date", "Team", "Opponent", "is_home", "xPts"],
        name="matches_with_injuries_all_seasons",
    )

    out = pd.DataFrame(
        {
            "season_label": df["Season"].astype(str),
            "match_id": pd.to_numeric(df["MatchID"], errors="coerce"),
            "team_id": df["Team"].astype(str),
            "opponent_id": df["Opponent"].astype(str),
            "date": _normalize_date(df["Date"]),
            "is_home": df["is_home"].astype(bool),
            "xpts": pd.to_numeric(df["xPts"], errors="coerce"),
        }
    )

    # "2019-2020" -> 2019
    out["season"] = out["season_label"].str.slice(0, 4).astype(int)

    assert_non_empty(out, "matches_clean")
    require_columns(out, ["season", "date", "team_id", "match_id"], name="matches_clean")

    _assert_unique_keys(out, ["season", "date", "team_id"], "matches_clean", logger)

    logger.info("Matches loaded: shape=%s", out.shape)
    return out


def load_understat_minutes(understat_path: Path, logger) -> pd.DataFrame:
    """
    Load per-player match minutes & starting info from Understat master.

    Required columns:
      team, player_id, player_name, Min, started
    Plus:
      - one date column in {'match_date','Date','date'}
      - one season column in {'season_start_year','season'}

    Returns (standardised schema):
      season, date, team_id, player_id, player_name, minutes, started
    """
    if not understat_path.exists():
        raise FileNotFoundError(
            f"{understat_path} not found. Run build_understat_master.py first."
        )

    df = pd.read_csv(understat_path)

    # Date column
    date_col = next((c for c in ["match_date", "Date", "date"] if c in df.columns), None)
    if date_col is None:
        raise ValueError(
            f"No date column found in {understat_path}. "
            f"Expected one of: match_date, Date, date. Columns={list(df.columns)}"
        )

    # Season column
    if "season_start_year" in df.columns:
        season = pd.to_numeric(df["season_start_year"], errors="coerce").astype("Int64")
    elif "season" in df.columns:
        # allow either 2019 or "2019-2020" formats
        season = (
            df["season"]
            .astype(str)
            .str.slice(0, 4)
            .pipe(pd.to_numeric, errors="coerce")
            .astype("Int64")
        )
    else:
        raise ValueError(
            f"No season column found in {understat_path}. "
            f"Expected 'season_start_year' or 'season'. Columns={list(df.columns)}"
        )

    require_columns(df, ["team", "player_id", "player_name", "Min", "started"], name="understat_master")

    out = pd.DataFrame(
        {
            "season": season.astype(int),
            "date": _normalize_date(df[date_col]),
            "team_id": df["team"].astype(str),
            "player_id": pd.to_numeric(df["player_id"], errors="coerce").astype("Int64"),
            "player_name": df["player_name"].astype(str),
            "minutes": pd.to_numeric(df["Min"], errors="coerce").fillna(0).astype(float),
            "started": df["started"],
        }
    )

    # Coerce started -> bool robustly (handles strings like "True"/"False"/"1"/"0")
    if out["started"].dtype == object:
        out["started"] = (
            out["started"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False})
        )
    out["started"] = out["started"].fillna(False).astype(bool)

    assert_non_empty(out, "understat_minutes")
    require_columns(out, ["season", "date", "team_id", "player_id"], name="understat_minutes")

    logger.info("Understat minutes loaded: shape=%s", out.shape)
    return out


# ----------------------------
# Core build
# ----------------------------

def build_rotation_panel(matches: pd.DataFrame, under: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Join Understat player-match rows to the league match panel by (season, date, team_id).

    Notes:
    - The merge is inner: Understat rows that do not match a league fixture are dropped
      (these are typically cup matches, friendlies, or date mismatches).
    - days_rest is computed as days since the player's previous Understat appearance
      (player-level, regardless of team). Values are clipped to [0, 30] and missing is set to 30.
    """
    before = len(under)

    # matches was already validated as unique on (season,date,team_id),
    # so this is many-to-one from Understat -> matches.
    panel = under.merge(
        matches,
        on=["season", "date", "team_id"],
        how="inner",
        validate="many_to_one",
    )

    after = len(panel)
    dropped = before - after
    if dropped > 0:
        logger.warning(
            "Dropped %d Understat rows with no matching league match (likely cups/friendlies or date mismatches).",
            dropped,
        )

    assert_non_empty(panel, "rotation_panel")

    # days_rest per player: days since previous appearance (player-level)
    panel = panel.sort_values(["player_id", "date"])
    panel["days_rest"] = panel.groupby("player_id")["date"].diff().dt.days
    panel["days_rest"] = panel["days_rest"].fillna(30).astype(float).clip(lower=0, upper=30)

    # Final schema / stable column order
    cols = [
        "match_id",
        "player_id",
        "player_name",
        "team_id",
        "season",
        "date",
        "opponent_id",
        "is_home",
        "xpts",
        "minutes",
        "started",
        "days_rest",
    ]
    panel = panel[cols].copy()

    logger.info("Rotation panel built: shape=%s", panel.shape)
    return panel


# ----------------------------
# CLI / main
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build player–team–match rotation panel from matches + Understat.")
    p.add_argument("--matches", type=str, default=None, help="Override path to matches_with_injuries_all_seasons.csv")
    p.add_argument("--understat", type=str, default=None, help="Override path to understat_player_matches_master.csv")
    p.add_argument("--out-csv", type=str, default=None, help="Override output CSV path")
    p.add_argument("--out-parquet", type=str, default=None, help="Override output parquet path")
    p.add_argument("--dry-run", action="store_true", help="Run full build/validation but do not write outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("build_rotation_panel", cfg.logs, "build_rotation_panel.log")

    meta_path = write_run_metadata(cfg.metadata, "build_rotation_panel", extra={"dry_run": args.dry_run})
    logger.info("Run metadata saved to: %s", meta_path)

    # Default paths from config (consistent with other scripts)
    default_matches = cfg.processed / "matches" / "matches_with_injuries_all_seasons.csv"
    default_under = cfg.processed / "understat" / "understat_player_matches_master.csv"
    default_out_csv = cfg.processed / "panel_rotation.csv"
    default_out_parquet = cfg.processed / "panel_rotation.parquet"

    matches_path = Path(args.matches) if args.matches else default_matches
    under_path = Path(args.understat) if args.understat else default_under
    out_csv = Path(args.out_csv) if args.out_csv else default_out_csv
    out_parquet = Path(args.out_parquet) if args.out_parquet else default_out_parquet

    logger.info("Reading matches from:   %s", matches_path)
    logger.info("Reading understat from: %s", under_path)
    logger.info("Writing CSV to:         %s", out_csv)
    logger.info("Writing parquet to:     %s", out_parquet)

    matches = load_matches(matches_path, logger)
    under = load_understat_minutes(under_path, logger)
    panel = build_rotation_panel(matches, under, logger)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | panel shape: {panel.shape} | output NOT written")
        return

    # Ensure output dir exists and write CSV (required output)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(panel, out_csv, index=False)

    # Parquet is optional (environment-dependent)
    try:
        out_parquet.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(out_parquet, index=False)
        parquet_status = "written"
    except Exception as e:
        parquet_status = f"skipped ({type(e).__name__}: {e})"
        logger.warning("Parquet write failed; continuing with CSV only. Reason: %s", parquet_status)

    logger.info("Saved rotation panel CSV rows=%d cols=%d", panel.shape[0], panel.shape[1])
    print("✅ Saved rotation panel")
    print(f"   - CSV:     {out_csv}")
    print(f"   - Parquet: {out_parquet} ({parquet_status})")
    print(f"   Shape: {panel.shape}")


if __name__ == "__main__":
    main()
