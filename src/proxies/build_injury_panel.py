# src/proxies/build_injury_panel.py
from __future__ import annotations

"""
Build a player–team–match injury panel dataset by combining:
  - team–match data with expected points (xPts) and squad injury counts
  - injury spells per player–team–season (already standardised)
  - Understat per-player match minutes & starting info (already standardised)

Outputs (defaults):
  <cfg.processed>/panel_injury.parquet
  <cfg.processed>/panel_injury.csv

One row per (match_id, team_id, player_name).
"""

from pathlib import Path
import argparse

import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


# ---------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------

def load_matches(path: Path) -> pd.DataFrame:
    """
    Load team–match panel with xPts and injury counts.

    Expected input columns (from matches_with_injuries_all_seasons.csv):
      Season, MatchID, Date, Team, Opponent, xPts, injured_players, ...

    Returns columns:
      match_id, season, season_label, date, team_id, opponent_id, xpts, n_injured_squad
    """
    if not path.exists():
        raise FileNotFoundError(f"Matches file not found: {path}")

    df = pd.read_csv(path)

    rename = {
        "Season": "season_label",
        "MatchID": "match_id",
        "Date": "date",
        "Team": "team_id",
        "Opponent": "opponent_id",
        "xPts": "xpts",
        "injured_players": "n_injured_squad",
    }
    df = df.rename(columns=rename)

    required = {"season_label", "match_id", "date", "team_id", "opponent_id", "xpts", "n_injured_squad"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[build_injury_panel] Matches missing columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        raise ValueError(f"[build_injury_panel] Matches has {bad_dates} rows with invalid dates.")

    df["season"] = df["season_label"].astype(str).str.slice(0, 4).astype(int)
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["opponent_id"] = df["opponent_id"].astype(str).str.strip()
    df["xpts"] = pd.to_numeric(df["xpts"], errors="coerce")
    df["n_injured_squad"] = pd.to_numeric(df["n_injured_squad"], errors="coerce").fillna(0).astype(int)

    out = df[
        ["match_id", "season", "season_label", "date", "team_id", "opponent_id", "xpts", "n_injured_squad"]
    ].copy()

    return out


def load_injury_spells(path: Path) -> pd.DataFrame:
    """
    Load injury/suspension spells from the combined injuries master.

    Expected input columns:
      player_name, team, start_date, end_date, season (e.g. '2019-2020')

    Returns columns:
      player_name, team_id, season, start_date, end_date
    """
    if not path.exists():
        raise FileNotFoundError(f"Injuries master not found: {path}")

    df = pd.read_csv(path)

    required = {"player_name", "team", "start_date", "end_date", "season"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[build_injury_panel] Injuries missing columns: {sorted(missing)}")

    spells = pd.DataFrame(
        {
            "player_name": df["player_name"].astype(str).str.strip(),
            "team_id": df["team"].astype(str).str.strip(),
            "start_date": pd.to_datetime(df["start_date"], errors="coerce"),
            "end_date": pd.to_datetime(df["end_date"], errors="coerce"),
            "season_label": df["season"].astype(str),
        }
    ).dropna(subset=["start_date", "end_date"])

    # Ensure start <= end
    flip = spells["start_date"] > spells["end_date"]
    if flip.any():
        tmp = spells.loc[flip, "start_date"].copy()
        spells.loc[flip, "start_date"] = spells.loc[flip, "end_date"]
        spells.loc[flip, "end_date"] = tmp

    spells["season"] = spells["season_label"].str.slice(0, 4).astype(int)

    out = spells[["player_name", "team_id", "season", "start_date", "end_date"]].copy()
    return out


def load_understat_minutes(path: Path) -> pd.DataFrame:
    """
    Load per-player match minutes & starting info from Understat master.

    Expected columns in understat master (at least):
      team, player_name, Min, started, and one of:
      - match_date / Date / date
      - season_start_year / season

    Returns columns:
      season, date, team_id, player_name, minutes, started

    IMPORTANT: Deduplicates to ONE row per (season, date, team_id, player_name)
    to avoid merge explosions.
    """
    if not path.exists():
        raise FileNotFoundError(f"Understat master not found: {path}")

    df = pd.read_csv(path)

    date_col = next((c for c in ["match_date", "Date", "date"] if c in df.columns), None)
    if date_col is None:
        raise ValueError(f"[build_injury_panel] Understat has no date column. Columns={list(df.columns)}")

    if "season_start_year" in df.columns:
        season_series = df["season_start_year"].astype(int)
    elif "season" in df.columns:
        season_series = df["season"].astype(str).str.slice(0, 4).astype(int)
    else:
        raise ValueError(f"[build_injury_panel] Understat has no season column. Columns={list(df.columns)}")

    required = {"team", "player_name", "Min", "started"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[build_injury_panel] Understat missing columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            "season": season_series,
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "team_id": df["team"].astype(str).str.strip(),
            "player_name": df["player_name"].astype(str).str.strip(),
            "minutes": pd.to_numeric(df["Min"], errors="coerce").fillna(0.0),
            "started": df["started"].astype("boolean"),
        }
    ).dropna(subset=["date"])

    # Collapse duplicates safely
    out = (
        out.groupby(["season", "date", "team_id", "player_name"], as_index=False)
        .agg(minutes=("minutes", "max"), started=("started", "max"))
    )
    out["started"] = out["started"].fillna(False).astype(bool)

    return out


# ---------------------------------------------------------------------
# Build injury panel
# ---------------------------------------------------------------------

def build_injury_panel(
    matches: pd.DataFrame,
    spells: pd.DataFrame,
    understat: pd.DataFrame | None,
    logger=None,
) -> pd.DataFrame:
    """
    One row per (match_id, team_id, player_name), for players who appear in spells.

    Columns:
      match_id, season, season_label, date, team_id, opponent_id, player_name,
      xpts, n_injured_squad, unavailable, minutes, started
    """
    # Restrict spells to team-season pairs that exist in matches (defensive)
    spells2 = spells.merge(
        matches[["team_id", "season"]].drop_duplicates(),
        on=["team_id", "season"],
        how="inner",
    )

    # Player–team–season universe (players who ever had a spell)
    pts = spells2[["player_name", "team_id", "season"]].drop_duplicates()

    # Team–season match set
    tsm = matches[
        ["match_id", "season", "season_label", "date", "team_id", "opponent_id", "xpts", "n_injured_squad"]
    ].copy()

    # Cross join: each player-team-season gets all matches for that team-season
    base = pts.merge(tsm, on=["team_id", "season"], how="left")

    # Attach spells to mark whether each match date is inside any spell
    tmp = base.merge(
        spells2,
        on=["player_name", "team_id", "season"],
        how="left",
        suffixes=("", "_spell"),
    )

    in_spell = (tmp["date"] >= tmp["start_date"]) & (tmp["date"] <= tmp["end_date"])
    tmp["unavailable_raw"] = in_spell.fillna(False).astype(int)

    panel = (
        tmp.groupby(["match_id", "team_id", "player_name"], as_index=False)
        .agg(
            season=("season", "first"),
            season_label=("season_label", "first"),
            date=("date", "first"),
            opponent_id=("opponent_id", "first"),
            xpts=("xpts", "first"),
            n_injured_squad=("n_injured_squad", "first"),
            unavailable=("unavailable_raw", "max"),
        )
    )

    # Merge Understat minutes/starts (optional)
    if understat is not None and len(understat) > 0:
        panel = panel.merge(
            understat,
            on=["season", "date", "team_id", "player_name"],
            how="left",
            validate="many_to_one",
        )
        panel["minutes"] = panel["minutes"].fillna(0.0).astype(float)
        panel["started"] = panel["started"].fillna(False).astype(bool)
    else:
        panel["minutes"] = 0.0
        panel["started"] = False

    # Final uniqueness check
    key = ["match_id", "team_id", "player_name"]
    dups = int(panel.duplicated(key).sum())
    if dups:
        sample = panel.loc[panel.duplicated(key, keep=False), key].head(10)
        raise ValueError(
            f"Duplicates found in {tuple(key)} after build. dup_rows={dups}. Sample:\n{sample}"
        )

    # Stable column order (NOTE: includes player_name)
    cols = [
        "match_id",
        "season",
        "season_label",
        "date",
        "team_id",
        "opponent_id",
        "player_name",
        "xpts",
        "n_injured_squad",
        "unavailable",
        "minutes",
        "started",
    ]
    panel = panel[cols].copy()

    if logger:
        logger.info("Injury panel built: shape=%s | unavailable_rate=%.3f",
                    panel.shape, float(panel["unavailable"].mean()))
    return panel


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main() -> None:
    cfg = Config.load()
    logger = setup_logger("build_injury_panel", cfg.logs, "build_injury_panel.log")
    meta_path = write_run_metadata(cfg.metadata, "build_injury_panel")
    logger.info("Run metadata saved to: %s", meta_path)

    p = argparse.ArgumentParser(description="Build player–team–match injury panel.")
    p.add_argument("--matches", type=Path, default=cfg.processed / "matches" / "matches_with_injuries_all_seasons.csv",
                   help="Override matches_with_injuries_all_seasons.csv path")
    p.add_argument("--injuries", type=Path, default=cfg.processed / "injuries" / "injuries_2019_2025_all_seasons.csv",
                   help="Override injuries_2019_2025_all_seasons.csv path")
    p.add_argument("--understat", type=Path, default=cfg.processed / "understat" / "understat_player_matches_master.csv",
                   help="Override understat_player_matches_master.csv path")
    p.add_argument("--out-csv", type=Path, default=cfg.processed / "panel_injury.csv",
                   help="Override output CSV path")
    p.add_argument("--out-parquet", type=Path, default=cfg.processed / "panel_injury.parquet",
                   help="Override output parquet path")
    p.add_argument("--dry-run", action="store_true",
                   help="Run full build/validation but do not write outputs")
    args = p.parse_args()

    logger.info("Reading matches from:   %s", args.matches)
    logger.info("Reading injuries from:  %s", args.injuries)
    logger.info("Reading understat from: %s", args.understat)
    logger.info("Writing CSV to:         %s", args.out_csv)
    logger.info("Writing parquet to:     %s", args.out_parquet)

    matches = load_matches(args.matches)
    spells = load_injury_spells(args.injuries)

    try:
        understat = load_understat_minutes(args.understat)
    except FileNotFoundError as e:
        logger.warning("Understat master not found; building panel without minutes/started. %s", e)
        understat = None

    panel = build_injury_panel(matches, spells, understat, logger=logger)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | panel shape: {panel.shape} | output NOT written")
        return

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)

    atomic_write_csv(panel, args.out_csv, index=False)
    panel.to_parquet(args.out_parquet, index=False)

    logger.info("Wrote outputs: csv=%s parquet=%s", args.out_csv, args.out_parquet)
    print(f"✅ wrote panel | shape={panel.shape}")
    print(f"   - {args.out_parquet}")
    print(f"   - {args.out_csv}")


if __name__ == "__main__":
    main()
