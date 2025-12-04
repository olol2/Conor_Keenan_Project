# src/data_collection/build_injuries_all_seasons.py

from __future__ import annotations
""" This script "fixes" the injury dates for all seasons by combining
the per-season injury CSV files into a single CSV file with a consistent format.
It also changes around the injury dates as it caused issues in later analysis.
The output is saved as injuries_tm_all_seasons.csv in data/processed/.
"""
from pathlib import Path
import pandas as pd

# ---------------------------------------------------------------------
# Paths (adapted to your project)
# ---------------------------------------------------------------------
# Conor_Keenan_Project/
#   data/
#     processed/
#       injuries/
#         injuries_2020.csv
#         injuries_2021.csv
#         injuries_2022.csv
#         injuries_2023.csv
#         injuries_2024.csv
#         injuries_2025.csv
#   src/
#     data_collection/
#       build_injuries_all_seasons.py  <-- this file
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INJURIES_DIR = PROJECT_ROOT / "data" / "processed" / "injuries"

# Map the files to season labels (you can tweak the labels if you prefer)
SEASON_FILES = [
    ("2019-2020", "injuries_2020.csv"),
    ("2020-2021", "injuries_2021.csv"),
    ("2021-2022", "injuries_2022.csv"),
    ("2022-2023", "injuries_2023.csv"),
    ("2023-2024", "injuries_2024.csv"),
    ("2024-2025", "injuries_2025.csv"),
]

# Combined output will also live in data/processed/injuries
OUTPUT_FILE = INJURIES_DIR / "injuries_2019_2025_all_seasons.csv"


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

    # Optional helper: numeric season start year (useful for sorting/merging)
    if "season_start_year" not in df.columns:
        df["season_start_year"] = int(season_label[:4])

    return df


def combine_seasons() -> pd.DataFrame:
    """
    Concatenate all the per-season injury CSVs into one DataFrame.
    """
    all_frames = []

    for season_label, filename in SEASON_FILES:
        print(f"Loading injuries for {season_label} from {filename}...")
        df_season = load_one_season(season_label, filename)
        all_frames.append(df_season)

    if not all_frames:
        raise RuntimeError("No injury data loaded – check SEASON_FILES and INJURIES_DIR path.")

    combined = pd.concat(all_frames, ignore_index=True)

    # Optional: convert common date columns to datetime if they exist
    for col in ["from", "to", "start_date", "end_date"]:
        if col in combined.columns:
            combined[col] = pd.to_datetime(combined[col], errors="coerce")

    # Optional: strip whitespace in common string columns
    for col in ["player_name", "club_name", "injury", "position"]:
        if col in combined.columns:
            combined[col] = combined[col].astype(str).str.strip()

    # Sort by season + player if available (handy later)
    sort_cols = [c for c in ["season_start_year", "season", "player_name"] if c in combined.columns]
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
