# src/data_collection/build_injuries_all_seasons.py

from __future__ import annotations
"""
Combine the per-season injury CSV files into a single CSV file with a
consistent format and canonical team names.

Input (already in your project):
  data/processed/injuries/injuries_2020.csv
  data/processed/injuries/injuries_2021.csv
  data/processed/injuries/injuries_2022.csv
  data/processed/injuries/injuries_2023.csv
  data/processed/injuries/injuries_2024.csv
  data/processed/injuries/injuries_2025.csv

Output:
  data/processed/injuries/injuries_2019_2025_all_seasons.csv
"""

from pathlib import Path
import pandas as pd

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INJURIES_DIR = PROJECT_ROOT / "data" / "processed" / "injuries"

# Map the files to season labels
SEASON_FILES = [
    ("2019-2020", "injuries_2020.csv"),
    ("2020-2021", "injuries_2021.csv"),
    ("2021-2022", "injuries_2022.csv"),
    ("2022-2023", "injuries_2023.csv"),
    ("2023-2024", "injuries_2024.csv"),
    ("2024-2025", "injuries_2025.csv"),
]

# Combined output
OUTPUT_FILE = INJURIES_DIR / "injuries_2019_2025_all_seasons.csv"

# ---------------------------------------------------------------------
# Team name standardisation: Transfermarkt -> canonical short names
# (matches/odds/understat all use the canonical versions)
# ---------------------------------------------------------------------

INJURIES_TEAM_MAP = {
    "AFC Bournemouth": "Bournemouth",
    "Arsenal FC": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Brentford FC": "Brentford",
    "Brighton & Hove Albion": "Brighton",
    "Burnley FC": "Burnley",
    "Chelsea FC": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Liverpool FC": "Liverpool",
    "Luton Town": "Luton",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Norwich City": "Norwich",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield United",
    "Southampton FC": "Southampton",
    "Tottenham Hotspur": "Tottenham",
    "Watford FC": "Watford",
    "West Bromwich Albion": "West Brom",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
}


def standardise_team_name_injuries(name: str) -> str:
    if pd.isna(name):
        return name
    return INJURIES_TEAM_MAP.get(name, name)


def load_one_season(season_label: str, filename: str) -> pd.DataFrame:
    """
    Load one season's injury data and attach a clean season label.
    """
    path = INJURIES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Expected injury file not found: {path}")

    df = pd.read_csv(path)

    # Ensure we have a 'season' column for later merges / analysis
    if "season" not in df.columns:
        df["season"] = season_label
    else:
        df["season"] = df["season"].astype(str).fillna(season_label)

    # Numeric season start year (useful for sorting/merging)
    if "season_start_year" not in df.columns:
        df["season_start_year"] = int(season_label[:4])

    # Standardise team names
    if "team" in df.columns:
        df["team"] = df["team"].apply(standardise_team_name_injuries)

    return df


def combine_seasons() -> pd.DataFrame:
    """
    Concatenate all the per-season injury CSVs into one DataFrame.
    """
    all_frames: list[pd.DataFrame] = []

    for season_label, filename in SEASON_FILES:
        print(f"Loading injuries for {season_label} from {filename}...")
        df_season = load_one_season(season_label, filename)
        all_frames.append(df_season)

    if not all_frames:
        raise RuntimeError("No injury data loaded – check SEASON_FILES and INJURIES_DIR path.")

    combined = pd.concat(all_frames, ignore_index=True)

    # Convert common date columns to datetime if they exist
    for col in ["from", "to", "start_date", "end_date"]:
        if col in combined.columns:
            combined[col] = pd.to_datetime(combined[col], errors="coerce")

    # Strip whitespace in common string columns
    for col in ["player_name", "team", "injury", "position"]:
        if col in combined.columns:
            combined[col] = combined[col].astype(str).str.strip()

    # Optionally drop the Transfermarkt URL column from the master
    if "source" in combined.columns:
        combined = combined.drop(columns=["source"])

    # Sort by season + player if available (handy later)
    sort_cols = [c for c in ["season_start_year", "season", "team", "player_name"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols).reset_index(drop=True)

    return combined


def main() -> None:
    print("Building combined injuries file ...")
    print(f"Reading from: {INJURIES_DIR}")
    print(f"Writing to:   {OUTPUT_FILE}")

    combined = combine_seasons()
    combined.to_csv(OUTPUT_FILE, index=False)

    print("Done!")
    print(f"Combined shape: {combined.shape}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
