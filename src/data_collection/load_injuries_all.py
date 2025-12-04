from __future__ import annotations
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INJURIES_ALL = PROJECT_ROOT / "data" / "processed" / "injuries" / "injuries_2019_2025_all_seasons.csv"

def load_injuries_all() -> pd.DataFrame:
    df = pd.read_csv(INJURIES_ALL)

    # Ensure season columns are nicely typed
    if "season_start_year" in df.columns:
        df["season_start_year"] = df["season_start_year"].astype(int)

    return df


def load_injuries_for_season(season_start_year: int) -> pd.DataFrame:
    """
    Example: season_start_year=2019 -> 2019-2020 season.
    """
    df = load_injuries_all()
    if "season_start_year" not in df.columns:
        raise KeyError("Expected 'season_start_year' in injuries file.")
    return df[df["season_start_year"] == season_start_year].copy()
