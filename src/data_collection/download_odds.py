# src/data_collection/download_odds.py
from __future__ import annotations
from pathlib import Path
import requests

""" this code downloads football match odds data from football-data.co.uk for specified seasons and saves the data into CSV files.
the csv files are stored in the data/raw/Odds/results directory.
"""

# Seasons in Football-Data format (same as your bash loop)
SEASONS = ["1920", "2021", "2122", "2223", "2324", "2425"]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/E0.csv"

# Project root: .../Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[2]
OUT_BASE = ROOT / "data" / "raw" / "Odds" / "results"


def download_season(season: str) -> None:
    url = BASE_URL.format(season=season)
    out_dir = OUT_BASE / season
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "E0.csv"

    print(f"Downloading {season}: {url}")
    resp = requests.get(url, allow_redirects=True, timeout=30)
    resp.raise_for_status()  # will error if download failed

    out_file.write_bytes(resp.content)
    print(f"Saved to {out_file}")


def main() -> None:
    for s in SEASONS:
        download_season(s)


if __name__ == "__main__":
    main()
