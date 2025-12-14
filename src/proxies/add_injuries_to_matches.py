# src/proxies/add_injuries_to_matches.py
"""
Attach injury exposure measures to the team–match panel.

What this produces:
- For each (Season, Team, Date) row in matches_all_seasons.csv, compute:
  - injured_players: number of distinct players with an active injury spell on that date
  - injury_spells: total number of active injury spells on that date (counts rows, not unique players)

Inputs (expected):
- <cfg.processed>/matches/matches_all_seasons.csv
- <cfg.processed>/injuries/injuries_2019_2025_all_seasons.csv

Output:
- <cfg.processed>/matches/matches_with_injuries_all_seasons.csv

Notes:
- This is deterministic and fast on your dataset sizes.
- Data collection (scraping) is not performed here; only saved CSVs are read.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.validation.checks import assert_non_empty, require_columns


def load_matches(path: Path) -> pd.DataFrame:
    """Load matches panel and enforce required schema."""
    if not path.exists():
        raise FileNotFoundError(f"Matches file not found: {path}")

    df = pd.read_csv(path)
    require_columns(df, ["Season", "Team", "Date"], name="matches")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().any():
        raise ValueError("[matches] Found unparseable Date values.")

    assert_non_empty(df, "matches")
    return df


def load_injuries(path: Path) -> pd.DataFrame:
    """
    Load injuries master and standardise columns needed for interval logic:
    Season, Team, player, from_date, to_date.
    """
    if not path.exists():
        raise FileNotFoundError(f"Injuries master file not found: {path}")

    df = pd.read_csv(path)
    require_columns(df, ["season", "team", "player_name", "start_date", "end_date"], name="injuries_master")
    assert_non_empty(df, "injuries_master")

    inj = pd.DataFrame(
        {
            "Season": df["season"].astype(str),
            "Team": df["team"].astype(str),
            "player": df["player_name"].astype(str),
            "from_date": pd.to_datetime(df["start_date"], errors="coerce"),
            "to_date": pd.to_datetime(df["end_date"], errors="coerce"),
        }
    ).dropna(subset=["from_date", "to_date"])

    # ensure from_date <= to_date
    swap = inj["from_date"] > inj["to_date"]
    if swap.any():
        tmp = inj.loc[swap, "from_date"].copy()
        inj.loc[swap, "from_date"] = inj.loc[swap, "to_date"]
        inj.loc[swap, "to_date"] = tmp

    assert_non_empty(inj, "injuries")
    return inj


def _compute_counts_for_group(m: pd.DataFrame, inj: pd.DataFrame) -> pd.DataFrame:
    """
    Compute injured_players and injury_spells for a single (Season, Team) group.
    This avoids a global cartesian merge.
    """
    dates = m["Date"].to_numpy(dtype="datetime64[ns]")

    # If no injuries for this team-season, return zeros.
    if inj.empty:
        out = m.copy()
        out["injured_players"] = 0
        out["injury_spells"] = 0
        return out

    froms = inj["from_date"].to_numpy(dtype="datetime64[ns]")
    tos = inj["to_date"].to_numpy(dtype="datetime64[ns]")

    # active[i, j] = match_date[i] is within injury interval j
    active = (dates[:, None] >= froms[None, :]) & (dates[:, None] <= tos[None, :])

    # injury_spells: count active spells per date
    injury_spells = active.sum(axis=1).astype(int)

    # injured_players: count distinct players among active spells per date
    players = inj["player"].to_numpy()
    injured_players = np.zeros(len(dates), dtype=int)
    for i in range(len(dates)):
        if injury_spells[i] == 0:
            injured_players[i] = 0
        else:
            injured_players[i] = len(np.unique(players[active[i]]))

    out = m.copy()
    out["injured_players"] = injured_players
    out["injury_spells"] = injury_spells
    return out


def add_injury_counts(matches: pd.DataFrame, injuries: pd.DataFrame, logger) -> pd.DataFrame:
    """Attach injury counts by matching Season+Team and checking Date within [from_date, to_date]."""
    # Standardise Season/Team types
    matches = matches.copy()
    matches["Season"] = matches["Season"].astype(str)
    matches["Team"] = matches["Team"].astype(str)

    injuries = injuries.copy()
    injuries["Season"] = injuries["Season"].astype(str)
    injuries["Team"] = injuries["Team"].astype(str)

    out_frames: list[pd.DataFrame] = []
    n_groups = 0

    for (season, team), m_grp in matches.groupby(["Season", "Team"], sort=False):
        n_groups += 1
        inj_grp = injuries[(injuries["Season"] == season) & (injuries["Team"] == team)]
        out_frames.append(_compute_counts_for_group(m_grp, inj_grp))

    out = pd.concat(out_frames, ignore_index=True)
    out = out.sort_values(["Season", "Date", "Team"]).reset_index(drop=True)

    logger.info("Processed %d (Season, Team) groups.", n_groups)
    logger.info(
        "Coverage summary: mean injured_players=%.3f, max injured_players=%d",
        float(out["injured_players"].mean()),
        int(out["injured_players"].max()),
    )

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge injury exposure counts onto matches panel.")
    p.add_argument("--matches", type=str, default=None, help="Optional override path to matches_all_seasons.csv")
    p.add_argument("--injuries", type=str, default=None, help="Optional override path to injuries_2019_2025_all_seasons.csv")
    p.add_argument("--output", type=str, default=None, help="Optional override output path for matches_with_injuries_all_seasons.csv")
    p.add_argument("--dry-run", action="store_true", help="Run full read/compute/validation but do not write output.")
    return p.parse_args()


def main() -> None:
    cfg = Config.load()
    args = parse_args()

    logger = setup_logger("add_injuries_to_matches", cfg.logs, "add_injuries_to_matches.log")
    meta_path = write_run_metadata(cfg.metadata, "add_injuries_to_matches", extra={"dry_run": args.dry_run})
    logger.info("Run metadata saved to: %s", meta_path)

    matches_path = Path(args.matches) if args.matches else (cfg.processed / "matches" / "matches_all_seasons.csv")
    injuries_path = Path(args.injuries) if args.injuries else (cfg.processed / "injuries" / "injuries_2019_2025_all_seasons.csv")
    out_path = Path(args.output) if args.output else (cfg.processed / "matches" / "matches_with_injuries_all_seasons.csv")

    logger.info("Reading matches from:  %s", matches_path)
    logger.info("Reading injuries from: %s", injuries_path)
    logger.info("Writing output to:     %s", out_path)

    matches = load_matches(matches_path)
    injuries = load_injuries(injuries_path)

    out = add_injury_counts(matches, injuries, logger=logger)
    assert_non_empty(out, "matches_with_injuries")

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | output shape: {out.shape} | output NOT written")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(out, out_path, index=False)

    logger.info("Saved: %s | shape=%s", out_path, out.shape)
    print(f"✅ Saved {out_path} with shape {out.shape}")


if __name__ == "__main__":
    main()
