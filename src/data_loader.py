# src/data_loader.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PROCESSED = ROOT_DIR / "data" / "processed"


def _load_standings() -> pd.DataFrame:
    paths = sorted((DATA_PROCESSED / "standings").glob("standings_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No standings files in {DATA_PROCESSED / 'standings'}")
    dfs = [pd.read_csv(p) for p in paths]
    return pd.concat(dfs, ignore_index=True)


def _load_points_to_pounds() -> pd.DataFrame:
    paths = sorted((DATA_PROCESSED / "points_to_pounds").glob("points_to_pounds_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No points_to_pounds files in {DATA_PROCESSED / 'points_to_pounds'}")
    dfs = [pd.read_csv(p) for p in paths]
    return pd.concat(dfs, ignore_index=True)


def _load_injuries() -> pd.DataFrame:
    # season-level injuries_YYYY.csv (already used to build the match panel)
    paths = sorted((DATA_PROCESSED / "injuries").glob("injuries_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No injuries_*.csv files in {DATA_PROCESSED / 'injuries'}")
    dfs = [pd.read_csv(p) for p in paths]
    return pd.concat(dfs, ignore_index=True)


def _load_matches_with_injuries() -> pd.DataFrame:
    path = DATA_PROCESSED / "matches" / "matches_with_injuries_all_seasons.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run src/build_match_panel.py and src/add_injuries_to_matches.py first."
        )
    df = pd.read_csv(path, parse_dates=["Date"])
    return df


def load_processed_data():
    """
    Load key processed datasets into a dict.
    Extend this as your pipeline grows.
    """
    standings = _load_standings()
    points_to_pounds = _load_points_to_pounds()
    injuries = _load_injuries()
    matches = _load_matches_with_injuries()

    return {
        "standings": standings,
        "points_to_pounds": points_to_pounds,
        "injuries": injuries,
        "matches": matches,
    }
