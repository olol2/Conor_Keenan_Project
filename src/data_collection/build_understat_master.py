# src/data_collection/build_understat_master.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

"""
Build a single Understat master file from the per-season
understat_player_matches_YYYY.csv files.

Input (already in your project):
  data/raw/understat_player_matches/understat_player_matches_2019.csv
  data/raw/understat_player_matches/understat_player_matches_2020.csv
  ...
  data/raw/understat_player_matches/understat_player_matches_2025.csv

Output:
  data/processed/understat/understat_player_matches_master.csv
"""

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

RAW_UNDERSTAT_DIR = DATA_DIR / "raw" / "understat_player_matches"

UNDERSTAT_PROCESSED_DIR = DATA_DIR / "processed" / "understat"
UNDERSTAT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = UNDERSTAT_PROCESSED_DIR / "understat_player_matches_master.csv"

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


def standardise_team_name_understat(name: str) -> str:
    if pd.isna(name):
        return name
    return UNDERSTAT_TEAM_MAP.get(name, name)


def load_one_file(path: Path) -> pd.DataFrame:
    """
    Load a single understat_player_matches_YYYY.csv and tidy it.
    """
    df = pd.read_csv(path)

    # Ensure date is datetime
    if "Date" not in df.columns:
        raise KeyError(f"Expected 'Date' column in {path}")
    df["match_date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Understat 'season' is the starting year (2019 => 2019-2020)
    if "season" not in df.columns:
        raise KeyError(f"Expected 'season' column in {path}")
    df["season_start_year"] = df["season"].astype(int)
    df["season_label"] = (
        df["season_start_year"].astype(str)
        + "-"
        + (df["season_start_year"] + 1).astype(str)
    )

    # Standardise all the team columns
    for col in ["team", "h_team", "a_team"]:
        if col in df.columns:
            df[col] = df[col].apply(standardise_team_name_understat)

    return df


def build_understat_master() -> pd.DataFrame:
    files = sorted(RAW_UNDERSTAT_DIR.glob("understat_player_matches_20*.csv"))
    if not files:
        raise RuntimeError(f"No understat_player_matches_20*.csv files in {RAW_UNDERSTAT_DIR}")

    frames: list[pd.DataFrame] = []
    for f in files:
        print(f"Reading {f}")
        frames.append(load_one_file(f))

    master = pd.concat(frames, ignore_index=True)

    # Optional: sort nicely
    sort_cols = [c for c in ["season_start_year", "match_date", "team", "player_name"] if c in master.columns]
    if sort_cols:
        master = master.sort_values(sort_cols).reset_index(drop=True)

    return master


def main() -> None:
    print("Building Understat master ...")
    print(f"Reading from: {RAW_UNDERSTAT_DIR}")
    print(f"Writing to:   {OUT_FILE}")

    master = build_understat_master()
    master.to_csv(OUT_FILE, index=False)

    print("Done!")
    print(f"Understat master shape: {master.shape}")
    print(f"Saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
