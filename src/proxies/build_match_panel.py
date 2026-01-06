"""
Build a team–match panel dataset with expected points using odds_master.csv.

Why:
- Produces a long-form team–match panel (2 rows per match: home + away).
- Used downstream for proxy construction / validation.

Input:
- <cfg.processed>/odds/odds_master.csv

Output:
- <cfg.processed>/matches/matches_all_seasons.csv

Notes:
- odds_master.csv is built earlier and already contains canonical team names.
- This script is quick; data collection is not required for grading.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.validation.checks import assert_non_empty, require_columns


def compute_probs_from_odds(df: pd.DataFrame, col_h: str, col_d: str, col_a: str) -> pd.DataFrame:
    """Convert 1X2 odds into implied probabilities (normalised)."""
    x = df.copy()
    x[col_h] = pd.to_numeric(x[col_h], errors="coerce")
    x[col_d] = pd.to_numeric(x[col_d], errors="coerce")
    x[col_a] = pd.to_numeric(x[col_a], errors="coerce")

    ok = (x[col_h] > 0) & (x[col_d] > 0) & (x[col_a] > 0)
    x = x.loc[ok].copy()

    inv_h = 1.0 / x[col_h]
    inv_d = 1.0 / x[col_d]
    inv_a = 1.0 / x[col_a]
    total = inv_h + inv_d + inv_a

    x["p_home"] = inv_h / total
    x["p_draw"] = inv_d / total
    x["p_away"] = inv_a / total
    return x


def build_team_match_rows(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """Return long-form team–match panel for one season."""
    df = df_season.copy()

    require_columns(df, ["match_date", "home_team", "away_team", "FTR"], name=f"odds_master[{season_label}]")
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.dropna(subset=["match_date", "home_team", "away_team", "FTR"]).copy()

    # Prefer Bet365; fall back to other common Football-Data prefixes if needed.
    odds_cols: tuple[str, str, str] | None = None
    for prefix in ["B365", "PS", "Max", "Avg"]:
        h, d, a = f"{prefix}H", f"{prefix}D", f"{prefix}A"
        if {h, d, a}.issubset(df.columns):
            odds_cols = (h, d, a)
            break

    if odds_cols is None:
        raise ValueError(
            f"[{season_label}] Could not find odds columns (e.g. B365H/B365D/B365A) in: {list(df.columns)}"
        )

    df = compute_probs_from_odds(df, *odds_cols)

    # Expected points per side
    df["xPts_home"] = 3.0 * df["p_home"] + 1.0 * df["p_draw"]
    df["xPts_away"] = 3.0 * df["p_away"] + 1.0 * df["p_draw"]

    # Actual points from Football-Data FTR (home perspective)
    def pts_home(result: str) -> int:
        if result == "H":
            return 3
        if result == "D":
            return 1
        return 0

    def pts_away(result: str) -> int:
        if result == "A":
            return 3
        if result == "D":
            return 1
        return 0

    df["Pts_home"] = df["FTR"].astype(str).map(pts_home)
    df["Pts_away"] = df["FTR"].astype(str).map(pts_away)

    # MatchID within season 
    df = df.sort_values(["match_date", "home_team", "away_team"]).reset_index(drop=True)
    df["MatchID"] = df.index + 1

    # Output schema matches existing CSV (capitalised column names)
    home_rows = pd.DataFrame(
        {
            "Season": season_label,
            "MatchID": df["MatchID"],
            "Date": df["match_date"],
            "Team": df["home_team"],
            "Opponent": df["away_team"],
            "is_home": True,
            "goals_for": df.get("FTHG"),
            "goals_against": df.get("FTAG"),
            "result": df["FTR"],  # keep as-is for backward compatibility
            "Pts": df["Pts_home"],
            "xPts": df["xPts_home"],
        }
    )

    away_rows = pd.DataFrame(
        {
            "Season": season_label,
            "MatchID": df["MatchID"],
            "Date": df["match_date"],
            "Team": df["away_team"],
            "Opponent": df["home_team"],
            "is_home": False,
            "goals_for": df.get("FTAG"),
            "goals_against": df.get("FTHG"),
            "result": df["FTR"],  # keep as-is for backward compatibility
            "Pts": df["Pts_away"],
            "xPts": df["xPts_away"],
        }
    )

    out = pd.concat([home_rows, away_rows], ignore_index=True)
    out = out.sort_values(["Season", "Date", "MatchID", "is_home"]).reset_index(drop=True)
    return out


def main() -> None:
    cfg = Config.load()
    logger = setup_logger("build_match_panel", cfg.logs, "build_match_panel.log")

    meta_path = write_run_metadata(cfg.metadata, "build_match_panel", extra={})
    logger.info("Run metadata saved to: %s", meta_path)

    p = argparse.ArgumentParser(description="Build team–match panel with expected points from odds_master.csv.")
    p.add_argument(
        "--input",
        type=Path,
        default=cfg.processed / "odds" / "odds_master.csv",
        help="Path to odds_master.csv (default: <cfg.processed>/odds/odds_master.csv)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=cfg.processed / "matches" / "matches_all_seasons.csv",
        help="Output CSV path (default: <cfg.processed>/matches/matches_all_seasons.csv)",
    )
    p.add_argument("--dry-run", action="store_true", help="Build + validate, but do not write output.")
    args = p.parse_args()

    in_path: Path = args.input
    out_path: Path = args.output

    logger.info("Reading odds master from: %s", in_path)
    df_all = pd.read_csv(in_path)

    assert_non_empty(df_all, "odds_master")
    require_columns(df_all, ["season", "match_date", "home_team", "away_team", "FTR"], "odds_master")

    panels: list[pd.DataFrame] = []
    for season_label, df_season in df_all.groupby("season", dropna=False):
        season_label = str(season_label)
        logger.info("Building match panel for season=%s rows=%d", season_label, len(df_season))
        panels.append(build_team_match_rows(df_season, season_label))

    if not panels:
        raise RuntimeError("No seasons found in odds_master.csv")

    panel = pd.concat(panels, ignore_index=True)
    assert_non_empty(panel, "matches_all_seasons")

    logger.info("Built match panel shape=%s", panel.shape)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | panel shape: {panel.shape} | output NOT written")
        return

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    atomic_write_csv(panel, out_path, index=False)
    logger.info("Saved match panel to: %s", out_path)
    print(f"✅ Saved match panel to {out_path} | shape={panel.shape}")


if __name__ == "__main__":
    main()
