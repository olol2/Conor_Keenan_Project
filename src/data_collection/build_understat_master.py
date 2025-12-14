# src/data_collection/build_understat_master.py
from __future__ import annotations

"""
Build a single Understat master file from per-season understat_player_matches_YYYY.csv files.

Why:
- Consolidates Understat player-match data into one clean, analysis-ready panel.
- Adds season labels and standardises team names to match the rest of the project.

Inputs (expected; already in this project):
- <cfg.raw>/understat_player_matches/understat_player_matches_2019.csv
- ...
- <cfg.raw>/understat_player_matches/understat_player_matches_2024.csv (or 2025 depending on your data)

Output (default):
- <cfg.processed>/understat/understat_player_matches_master.csv

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


# ---------------------------------------------------------------------
# Minimal team mapping: Understat -> canonical short names
# ---------------------------------------------------------------------
UNDERSTAT_TEAM_MAP = {
    "Manchester City": "Man City",
    "Manchester Utd": "Man United",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Wolverhampton Wanderers": "Wolves",
    "West Bromwich Albion": "West Brom",
    "Brighton & Hove Albion": "Brighton",
    "Brighton and Hove Albion": "Brighton",
    "Leicester City": "Leicester",
    "Leeds United": "Leeds",
    "Ipswich Town": "Ipswich",
    "Luton Town": "Luton",
    "Norwich City": "Norwich",
    "Sheffield Utd": "Sheffield United",
}

REQUIRED_COLS = {"season", "Date", "team", "player_id", "player_name"}


def standardise_team_name_understat(name: str) -> str:
    """Map Understat team display names to the canonical short names used across the project."""
    if pd.isna(name):
        return name
    return UNDERSTAT_TEAM_MAP.get(str(name), str(name))


def load_one_file(path: Path, logger) -> pd.DataFrame:
    """
    Load one per-season Understat CSV and apply minimal cleaning/standardisation.

    Adds:
    - match_date (datetime from Date)
    - season_start_year (int)
    - season_label (e.g. 2019-2020)
    """
    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"[{path.name}] Missing required columns: {sorted(missing)}")

    # Ensure date is datetime (keeps later filtering/ordering robust)
    df["match_date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Understat 'season' is the starting year (2019 => 2019-2020)
    df["season_start_year"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    # Drop rows where key fields could not be parsed
    df = df.dropna(subset=["match_date", "season_start_year"])

    df["season_start_year"] = df["season_start_year"].astype(int)
    df["season_label"] = df["season_start_year"].astype(str) + "-" + (df["season_start_year"] + 1).astype(str)

    # Standardise team columns (if present)
    for col in ["team", "h_team", "a_team"]:
        if col in df.columns:
            df[col] = df[col].apply(standardise_team_name_understat)

    logger.info("Loaded file=%s shape=%s", path.name, df.shape)
    return df


def build_understat_master(raw_understat_dir: Path, logger) -> pd.DataFrame:
    """Read all per-season Understat CSVs and concatenate them into one master DataFrame."""
    files = sorted(raw_understat_dir.glob("understat_player_matches_20*.csv"))
    if not files:
        raise FileNotFoundError(f"No understat_player_matches_20*.csv files found in: {raw_understat_dir}")

    frames: list[pd.DataFrame] = []
    for f in files:
        logger.info("Reading %s", f)
        print(f"Reading {f.name} ...")
        frames.append(load_one_file(f, logger))

    master = pd.concat(frames, ignore_index=True)

    if len(master) == 0:
        raise ValueError("Understat master is empty after cleaning. Check date/season parsing and input files.")

    # Stable ordering for easier debugging and deterministic outputs
    sort_cols = [c for c in ["season_start_year", "match_date", "team", "player_name"] if c in master.columns]
    if sort_cols:
        master = master.sort_values(sort_cols).reset_index(drop=True)

    logger.info("Understat master shape=%s", master.shape)
    return master


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Understat master CSV from per-season Understat files.")
    parser.add_argument(
        "--raw-dir",
        default=None,
        help="Optional override for raw understat directory. Default: <cfg.raw>/understat_player_matches",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional override for output CSV. Default: <cfg.processed>/understat/understat_player_matches_master.csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full read/combine/validation, but do not write output.",
    )
    args = parser.parse_args()

    cfg = Config.load()
    logger = setup_logger("build_understat_master", cfg.logs, "build_understat_master.log")
    meta_path = write_run_metadata(cfg.metadata, "build_understat_master", extra={"dry_run": args.dry_run})
    logger.info("Run metadata saved to: %s", meta_path)

    raw_understat_dir = Path(args.raw_dir) if args.raw_dir else (cfg.raw / "understat_player_matches")
    out_dir = cfg.processed / "understat"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = Path(args.output) if args.output else (out_dir / "understat_player_matches_master.csv")

    logger.info("Reading from: %s", raw_understat_dir)
    logger.info("Writing to:   %s", out_path)

    print("Building Understat master ...")
    print(f"Reading from: {raw_understat_dir}")
    print(f"Writing to:   {out_path}")

    master = build_understat_master(raw_understat_dir, logger)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | master shape: {master.shape} | output NOT written")
        return

    atomic_write_csv(master, out_path, index=False)

    logger.info("Saved Understat master to: %s", out_path)
    print("Done!")
    print(f"Understat master shape: {master.shape}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
