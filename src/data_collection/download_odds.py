# src/data_collection/download_odds.py

"""
Download football match odds data from football-data.co.uk for specified seasons.

Purpose:
- Optional data collection script (NOT used by main.py).
- Provided for transparency on how raw odds CSVs were obtained.

Output:
- data/raw/Odds/results/<season>/E0.csv
"""
from __future__ import annotations
from pathlib import Path
import argparse
import requests

SEASONS = ["1920", "2021", "2122", "2223", "2324", "2425"]
BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/E0.csv"

ROOT = Path(__file__).resolve().parents[2]
OUT_BASE = ROOT / "data" / "raw" / "Odds" / "results"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UniCourseProject/1.0)"}


def download_season(season: str, *, overwrite: bool = False, dry_run: bool = False) -> Path:
    """Download E0.csv for a given season and save it under data/raw/Odds/results/<season>/."""
    url = BASE_URL.format(season=season)
    out_dir = OUT_BASE / season
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "E0.csv"

    if dry_run:
        action = "overwrite" if overwrite else "skip-if-exists"
        print(f"[dry-run] ({action}) Would download {season}: {url} -> {out_file}")
        return out_file

    if out_file.exists() and not overwrite:
        print(f"[skip] {season} already exists: {out_file}")
        return out_file


    print(f"Downloading {season}: {url}")
    resp = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=30)
    resp.raise_for_status()
    out_file.write_bytes(resp.content)
    print(f"Saved to {out_file}")
    return out_file


def main() -> None:
    p = argparse.ArgumentParser(description="Download football-data.co.uk odds CSVs (optional; not used by main.py).")
    p.add_argument("--seasons", nargs="*", default=SEASONS, help="Seasons in football-data format (e.g., 1920 2021 2122).")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing E0.csv files.")
    p.add_argument("--dry-run", action="store_true", help="Print what would be downloaded without making requests.")
    args = p.parse_args()

    for s in args.seasons:
        download_season(s, overwrite=args.overwrite, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
