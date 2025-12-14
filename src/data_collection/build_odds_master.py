# src/data_collection/build_odds_master.py
from __future__ import annotations

"""
Build a single odds_master.csv from all Football-Data (E0) season CSVs.

Why:
- Consolidates per-season odds/results files into one master dataset.
- Provides consistent season/date/team fields for optional merges and robustness checks.

Inputs (expected; already in this project after download_odds.py):
- <cfg.raw>/Odds/results/1920/E0.csv
- <cfg.raw>/Odds/results/2021/E0.csv
- <cfg.raw>/Odds/results/2122/E0.csv
- <cfg.raw>/Odds/results/2223/E0.csv
- <cfg.raw>/Odds/results/2324/E0.csv
- <cfg.raw>/Odds/results/2425/E0.csv

Output (default):
- <cfg.processed>/odds/odds_master.csv

Safe checks:
- --help shows usage only
- --dry-run reads/combines/validates but does not write output
"""

from pathlib import Path
import argparse

import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# Folder name -> season start year
SEASON_DIR_TO_YEAR: dict[str, int] = {
    "1920": 2019,  # 2019-20
    "2021": 2020,  # 2020-21
    "2122": 2021,  # 2021-22
    "2223": 2022,  # 2022-23
    "2324": 2023,  # 2023-24
    "2425": 2024,  # 2024-25
}

# Minimal columns required to build match_date and team keys
REQUIRED_COLS = {"Date", "HomeTeam", "AwayTeam"}


def load_one_season(raw_odds_dir: Path, folder: str, season_start_year: int, logger) -> pd.DataFrame:
    """
    Load one E0.csv file and attach season + standard team/date columns.

    Notes:
    - Football-Data HomeTeam/AwayTeam are assumed to match the project's canonical team names.
    - Date parsing uses dayfirst=True, consistent with football-data.co.uk formatting.
    """
    path = raw_odds_dir / folder / "E0.csv"
    if not path.exists():
        raise FileNotFoundError(f"Expected odds file not found: {path}")

    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"[{path}] Missing required columns: {sorted(missing)}")

    # Keep only Premier League division if Div exists
    if "Div" in df.columns:
        df = df[df["Div"] == "E0"].copy()

    # Season metadata
    df["season_start_year"] = int(season_start_year)
    df["season"] = df["season_start_year"].astype(str) + "-" + (df["season_start_year"] + 1).astype(str)

    # Parse date
    df["match_date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["match_date"])

    # Team names (already canonical)
    df["home_team"] = df["HomeTeam"].astype(str).str.strip()
    df["away_team"] = df["AwayTeam"].astype(str).str.strip()

    logger.info("Loaded folder=%s file=%s shape=%s", folder, path.name, df.shape)
    return df


def build_match_id(df: pd.DataFrame) -> pd.Series:
    """
    Build a stable match_id for optional merges.

    Format:
    <season_start_year>_<home_team>_<away_team>_<YYYYMMDD>

    This is not guaranteed unique across all competitions, but is reasonable for EPL-only context.
    """
    return (
        df["season_start_year"].astype(str)
        + "_"
        + df["home_team"].astype(str)
        + "_"
        + df["away_team"].astype(str)
        + "_"
        + df["match_date"].dt.strftime("%Y%m%d")
    )


def build_odds_master(raw_odds_dir: Path, logger) -> pd.DataFrame:
    """Concatenate odds across seasons and keep a stable subset of columns."""
    frames: list[pd.DataFrame] = []

    for folder, year in SEASON_DIR_TO_YEAR.items():
        logger.info("Loading odds folder=%s season=%d-%d", folder, year, year + 1)
        print(f"Loading odds for folder {folder} (season {year}-{year+1})...")
        frames.append(load_one_season(raw_odds_dir, folder, year, logger))

    if not frames:
        raise RuntimeError("No odds data loaded. Check SEASON_DIR_TO_YEAR mapping and raw_odds_dir.")

    odds_all = pd.concat(frames, ignore_index=True)

    if len(odds_all) == 0:
        raise ValueError("Odds master is empty after filtering/cleaning. Check input files and parsing.")

    # Construct match_id for optional merges
    odds_all["match_id"] = build_match_id(odds_all)

    # Keep only the columns you actually need (robust to missing bookmaker columns)
    cols_keep = [
        "season_start_year",
        "season",
        "match_date",
        "match_id",
        "home_team",
        "away_team",
        "FTHG",
        "FTAG",
        "FTR",
        "B365H",
        "B365D",
        "B365A",
        "B365>2.5",
        "B365<2.5",
    ]
    cols_keep = [c for c in cols_keep if c in odds_all.columns]
    odds_all = odds_all[cols_keep]

    # Drop any duplicate match_ids (defensive; shouldn't typically occur)
    odds_all = odds_all.drop_duplicates(subset=["match_id"])

    # Stable ordering
    sort_cols = [c for c in ["season_start_year", "match_date", "home_team", "away_team"] if c in odds_all.columns]
    if sort_cols:
        odds_all = odds_all.sort_values(sort_cols).reset_index(drop=True)

    logger.info("Odds master shape=%s", odds_all.shape)
    return odds_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Build odds master CSV from football-data.co.uk season files.")
    parser.add_argument(
        "--raw-dir",
        default=None,
        help="Optional override for raw odds directory. Default: <cfg.raw>/Odds/results",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional override for output CSV. Default: <cfg.processed>/odds/odds_master.csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full read/combine/validation, but do not write output.",
    )
    args = parser.parse_args()

    cfg = Config.load()
    logger = setup_logger("build_odds_master", cfg.logs, "build_odds_master.log")
    meta_path = write_run_metadata(cfg.metadata, "build_odds_master", extra={"dry_run": args.dry_run})
    logger.info("Run metadata saved to: %s", meta_path)

    raw_odds_dir = Path(args.raw_dir) if args.raw_dir else (cfg.raw / "Odds" / "results")
    out_dir = cfg.processed / "odds"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = Path(args.output) if args.output else (out_dir / "odds_master.csv")

    logger.info("Reading from: %s", raw_odds_dir)
    logger.info("Writing to:   %s", out_path)

    print("Building odds_master ...")
    print(f"Reading from: {raw_odds_dir}")
    print(f"Writing to:   {out_path}")

    odds_all = build_odds_master(raw_odds_dir, logger)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | odds_master shape: {odds_all.shape} | output NOT written")
        return

    atomic_write_csv(odds_all, out_path, index=False)

    logger.info("Saved odds_master to: %s", out_path)
    print("Done!")
    print(f"odds_master shape: {odds_all.shape}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
