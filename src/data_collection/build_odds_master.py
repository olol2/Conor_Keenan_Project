# src/data_collection/build_odds_master.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

"""
Build a single odds_master.csv from all Football-Data E0 files.

Input (already in your project):
  data/raw/Odds/results/1920/E0.csv
  data/raw/Odds/results/2021/E0.csv
  data/raw/Odds/results/2122/E0.csv
  data/raw/Odds/results/2223/E0.csv
  data/raw/Odds/results/2324/E0.csv
  data/raw/Odds/results/2425/E0.csv

Output:
  data/processed/odds/odds_master.csv
"""

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_ODDS_DIR = DATA_DIR / "raw" / "Odds" / "results"

ODDS_PROCESSED_DIR = DATA_DIR / "processed" / "odds"
ODDS_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = ODDS_PROCESSED_DIR / "odds_master.csv"

# folder name -> season start year
SEASON_DIR_TO_YEAR = {
    "1920": 2019,  # 2019-20
    "2021": 2020,  # 2020-21
    "2122": 2021,  # 2021-22
    "2223": 2022,  # 2022-23
    "2324": 2023,  # 2023-24
    "2425": 2024,  # 2024-25
}


def load_one_season(folder: str, season_start_year: int) -> pd.DataFrame:
    """
    Load one E0.csv file, add season info.
    Football-Data team names already match your canonical team names,
    so we just copy them into home_team / away_team.
    """
    path = RAW_ODDS_DIR / folder / "E0.csv"
    if not path.exists():
        raise FileNotFoundError(f"Expected odds file not found: {path}")

    df = pd.read_csv(path)

    # Keep only Premier League division if Div exists
    if "Div" in df.columns:
        df = df[df["Div"] == "E0"].copy()

    # Season metadata
    df["season_start_year"] = season_start_year
    df["season"] = (
        df["season_start_year"].astype(str)
        + "-"
        + (df["season_start_year"] + 1).astype(str)
    )

    # Parse date
    if "Date" not in df.columns:
        raise KeyError("Expected 'Date' column in odds file.")
    df["match_date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # Team names (already canonical)
    df["home_team"] = df["HomeTeam"]
    df["away_team"] = df["AwayTeam"]

    return df


def build_odds_master() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for folder, year in SEASON_DIR_TO_YEAR.items():
        print(f"Loading odds for folder {folder} (season {year}-{year+1})...")
        df_season = load_one_season(folder, year)
        frames.append(df_season)

    if not frames:
        raise RuntimeError("No odds data loaded – check SEASON_DIR_TO_YEAR / RAW_ODDS_DIR.")

    odds_all = pd.concat(frames, ignore_index=True)

    # Match ID to help merges with matches if you want it
    odds_all["match_id"] = (
        odds_all["season_start_year"].astype(str)
        + "_"
        + odds_all["home_team"]
        + "_"
        + odds_all["away_team"]
        + "_"
        + odds_all["match_date"].dt.strftime("%Y%m%d")
    )

    # Keep only the columns you actually need
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
        # add more odds columns here if you end up using them
    ]
    cols_keep = [c for c in cols_keep if c in odds_all.columns]
    odds_all = odds_all[cols_keep]

    # Optional: drop any duplicate match_ids if they exist
    if "match_id" in odds_all.columns:
        odds_all = odds_all.drop_duplicates(subset=["match_id"])

    return odds_all


def main() -> None:
    print("Building odds_master ...")
    print(f"Reading from: {RAW_ODDS_DIR}")
    print(f"Writing to:   {OUT_FILE}")

    odds_all = build_odds_master()
    odds_all.to_csv(OUT_FILE, index=False)

    print("Done!")
    print(f"odds_master shape: {odds_all.shape}")
    print(f"Saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
