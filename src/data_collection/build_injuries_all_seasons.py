"""
Combine per-season Transfermarkt injury CSVs into a single all-seasons file and standardise team names.

Why:
- Downstream analysis/proxies should read one consistent master injury panel.
- Standardised team names ensure stable joins across datasets.

Inputs (expected; created by fetch_injuries_tm.py and stored under processed/injuries/):
- <cfg.processed>/injuries/injuries_2020.csv   (2019-2020 season)
- <cfg.processed>/injuries/injuries_2021.csv
- <cfg.processed>/injuries/injuries_2022.csv
- <cfg.processed>/injuries/injuries_2023.csv
- <cfg.processed>/injuries/injuries_2024.csv
- <cfg.processed>/injuries/injuries_2025.csv

Output (default):
- <cfg.processed>/injuries/injuries_2019_2025_all_seasons.csv

Safe checks:
- --help shows usage only
- --dry-run reads/combines/validates but does not write output
"""

from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Team name standardisation: Transfermarkt -> chosen unique short names
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

REQUIRED_COLS = {"player_name", "team", "start_date", "end_date"}


def standardise_team_name_injuries(name: str) -> str:
    """Map Transfermarkt club display names to short canonical names used elsewhere in the project."""
    if pd.isna(name):
        return name
    return INJURIES_TEAM_MAP.get(str(name), str(name))


def _season_files_default() -> list[tuple[str, str]]:
    """
    Default mapping from season labels to filenames written by fetch_injuries_tm.py.
    injuries_<end_year>.csv corresponds to season (end_year-1)-(end_year).
    """
    return [
        ("2019-2020", "injuries_2020.csv"),
        ("2020-2021", "injuries_2021.csv"),
        ("2021-2022", "injuries_2022.csv"),
        ("2022-2023", "injuries_2023.csv"),
        ("2023-2024", "injuries_2024.csv"),
        ("2024-2025", "injuries_2025.csv"),
    ]


def load_one_season(injuries_dir: Path, season_label: str, filename: str, logger) -> pd.DataFrame:
    """
    Load one season's injury CSV from injuries_dir and attach standard season columns.

    Adds:
    - season (e.g. '2019-2020')
    - season_start_year (e.g. 2019)

    Standardises:
    - team names via INJURIES_TEAM_MAP
    """
    path = injuries_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Expected injury file not found: {path}")

    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"[{filename}] Missing required columns: {sorted(missing)}")

    # Standard season fields
    df["season"] = season_label
    df["season_start_year"] = int(season_label[:4])

    # Standardise team names
    df["team"] = df["team"].apply(standardise_team_name_injuries)

    logger.info("Loaded season=%s file=%s shape=%s", season_label, filename, df.shape)
    return df


def combine_seasons(
    injuries_dir: Path,
    season_files: list[tuple[str, str]],
    *,
    drop_source: bool,
    logger,
) -> pd.DataFrame:
    """Concatenate all per-season injury CSVs into one DataFrame and apply light cleaning."""
    frames: list[pd.DataFrame] = []

    for season_label, filename in season_files:
        logger.info("Loading injuries for %s from %s", season_label, filename)
        print(f"Loading injuries for {season_label} from {filename}...")
        frames.append(load_one_season(injuries_dir, season_label, filename, logger))

    if not frames:
        raise RuntimeError("No injury data loaded. Check season_files mapping and injuries_dir.")

    combined = pd.concat(frames, ignore_index=True)

    # Parse dates to datetime and drop invalid rows
    combined["start_date"] = pd.to_datetime(combined["start_date"], errors="coerce")
    combined["end_date"] = pd.to_datetime(combined["end_date"], errors="coerce")
    combined = combined.dropna(subset=["start_date", "end_date"])

    # Strip whitespace in common string columns
    for col in ["player_name", "team", "type"]:
        if col in combined.columns:
            combined[col] = combined[col].astype(str).str.strip()

    # Optional: drop URL/source to keep master compact
    if drop_source and "source" in combined.columns:
        combined = combined.drop(columns=["source"])

    # Stable ordering
    sort_cols = [c for c in ["season_start_year", "season", "team", "player_name"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols).reset_index(drop=True)

    if len(combined) == 0:
        raise ValueError("Combined injuries is empty after cleaning (date parsing may have failed).")

    logger.info("Combined injuries shape=%s", combined.shape)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a combined all-seasons injuries master CSV.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional override for output path. Default: <cfg.processed>/injuries/injuries_2019_2025_all_seasons.csv",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Keep the 'source' column (URL). Default behavior drops it.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full read/combine/validation, but do not write output.",
    )
    args = parser.parse_args()

    cfg = Config.load()
    logger = setup_logger("build_injuries_all_seasons", cfg.logs, "build_injuries_all_seasons.log")
    meta_path = write_run_metadata(cfg.metadata, "build_injuries_all_seasons", extra={"dry_run": args.dry_run})
    logger.info("Run metadata saved to: %s", meta_path)

    injuries_dir = cfg.processed / "injuries"
    season_files = _season_files_default()

    out_path = Path(args.output) if args.output else (injuries_dir / "injuries_2019_2025_all_seasons.csv")

    logger.info("Reading from: %s", injuries_dir)
    logger.info("Writing to:   %s", out_path)

    print("Building combined injuries file ...")
    print(f"Reading from: {injuries_dir}")
    print(f"Writing to:   {out_path}")

    combined = combine_seasons(
        injuries_dir,
        season_files,
        drop_source=not args.keep_source,
        logger=logger,
    )

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | combined shape: {combined.shape} | output NOT written")
        return

    atomic_write_csv(combined, out_path, index=False)

    logger.info("Saved combined injuries to: %s", out_path)
    logger.info("Combined shape: %s", combined.shape)
    print("Done!")
    print(f"Combined shape: {combined.shape}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
