# src/data_loader.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PROCESSED = ROOT_DIR / "data" / "processed"


def load_processed_data():
    """Load the key processed datasets into a dict."""

    standings = pd.concat(
        pd.read_csv(p) for p in sorted((DATA_PROCESSED / "standings").glob("standings_*.csv"))
    )

    points_to_pounds = pd.concat(
        pd.read_csv(p)
        for p in sorted((DATA_PROCESSED / "points_to_pounds").glob("points_to_pounds_*.csv"))
    )

    injuries = pd.concat(
        pd.read_csv(p)
        for p in sorted((DATA_PROCESSED / "injuries").glob("injuries_*.csv"))
    )

    return {
        "standings": standings,
        "points_to_pounds": points_to_pounds,
        "injuries": injuries,
        # later you can add player logs, match-level panel, etc.
    }
