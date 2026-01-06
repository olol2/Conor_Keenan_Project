"""
Build Premier League final standings from the processed odds master file.

Input (default):
  <cfg.processed>/odds/odds_master.csv

Outputs (default):
  <cfg.processed>/standings/standings_<season>.csv
  <cfg.processed>/standings/standings_all_seasons.csv

Assumptions:
- One row per Premier League match in odds_master.csv.
- Required columns in odds_master.csv:
    season, home_team, away_team, FTHG, FTAG, FTR
  where FTR is "H"/"D"/"A" from the home-team perspective.

Notes:
- Standings are computed deterministically from match results only.
- This is fast and does not require any web scraping.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.utils.config import Config


def build_standings(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """
    Compute a final league table for one season.

    Parameters
    ----------
    df_season:
        Match-level data for one season. Expects columns:
          HomeTeam, AwayTeam, FTHG, FTAG, FTR
    season_label:
        e.g. '2019-2020'

    Returns
    -------
    DataFrame with columns:
      Season, Position, Team, MP, W, D, L, GF, GA, GD, Pts
    """
    required = {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
    missing = required - set(df_season.columns)
    if missing:
        raise ValueError(f"Season {season_label}: missing columns {sorted(missing)}")

    df = df_season.copy()

    # Clean team names
    df["HomeTeam"] = df["HomeTeam"].astype(str).str.strip()
    df["AwayTeam"] = df["AwayTeam"].astype(str).str.strip()

    # Ensure numeric goals (robust to any parsing issues)
    df["FTHG"] = pd.to_numeric(df["FTHG"], errors="coerce")
    df["FTAG"] = pd.to_numeric(df["FTAG"], errors="coerce")

    # Home-side aggregates
    home = df.groupby("HomeTeam").agg(
        MP_home=("HomeTeam", "size"),
        GF_home=("FTHG", "sum"),
        GA_home=("FTAG", "sum"),
        W_home=("FTR", lambda s: (s == "H").sum()),
        D_home=("FTR", lambda s: (s == "D").sum()),
        L_home=("FTR", lambda s: (s == "A").sum()),
    )

    # Away-side aggregates (away goals are FTAG; away conceded are FTHG)
    away = df.groupby("AwayTeam").agg(
        MP_away=("AwayTeam", "size"),
        GF_away=("FTAG", "sum"),
        GA_away=("FTHG", "sum"),
        W_away=("FTR", lambda s: (s == "A").sum()),
        D_away=("FTR", lambda s: (s == "D").sum()),
        L_away=("FTR", lambda s: (s == "H").sum()),
    )

    # Combine home + away stats
    table = home.join(away, how="outer").fillna(0)

    # Totals
    table["MP"] = table["MP_home"] + table["MP_away"]
    table["W"] = table["W_home"] + table["W_away"]
    table["D"] = table["D_home"] + table["D_away"]
    table["L"] = table["L_home"] + table["L_away"]
    table["GF"] = table["GF_home"] + table["GF_away"]
    table["GA"] = table["GA_home"] + table["GA_away"]
    table["GD"] = table["GF"] - table["GA"]
    table["Pts"] = 3 * table["W"] + table["D"]

    # Sort by points, then goal difference, then goals for (standard tie-break ordering)
    table = table.sort_values(by=["Pts", "GD", "GF"], ascending=[False, False, False])

    # Keep final columns and cast to int
    table = table[["MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]].copy()
    for c in table.columns:
        table[c] = pd.to_numeric(table[c], errors="coerce").fillna(0).astype(int)

    table = table.reset_index().rename(columns={"index": "Team"})
    table.insert(0, "Position", range(1, len(table) + 1))
    table.insert(0, "Season", season_label)

    return table


def parse_args(cfg: Config) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build league standings from odds_master.csv.")
    p.add_argument(
        "--odds-master",
        type=Path,
        default=cfg.processed / "odds" / "odds_master.csv",
        help="Path to odds_master.csv (default: <cfg.processed>/odds/odds_master.csv)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=cfg.processed / "standings",
        help="Output directory for standings CSVs (default: <cfg.processed>/standings)",
    )
    p.add_argument("--dry-run", action="store_true", help="Compute but do not write outputs")
    return p.parse_args()


def main() -> None:
    cfg = Config.load()
    args = parse_args(cfg)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    odds_master_path = args.odds_master
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not odds_master_path.exists():
        raise FileNotFoundError(f"odds_master.csv not found: {odds_master_path}")

    df_all = pd.read_csv(odds_master_path)

    required = {"season", "home_team", "away_team", "FTHG", "FTAG", "FTR"}
    missing = required - set(df_all.columns)
    if missing:
        raise ValueError(f"Missing columns in odds_master: {sorted(missing)}")

    all_standings: list[pd.DataFrame] = []

    for season_label, df_season_raw in df_all.groupby("season", dropna=False):
        season_label = str(season_label)
        logging.info("Building standings for %s...", season_label)

        # Rename to the HomeTeam/AwayTeam schema used inside build_standings()
        df_season = df_season_raw.rename(columns={"home_team": "HomeTeam", "away_team": "AwayTeam"}).copy()

        standings = build_standings(df_season, season_label)

        # Sanity checks (warnings only)
        n_teams = len(standings)
        mp_vals = standings["MP"].unique().tolist()
        if n_teams != 20:
            logging.warning("Season %s: standings has %s teams (expected 20).", season_label, n_teams)
        if len(mp_vals) > 1:
            logging.warning("Season %s: teams have different MP values: %s", season_label, mp_vals)

        out_path = out_dir / f"standings_{season_label}.csv"
        if args.dry_run:
            logging.info("Dry-run: would write %s (rows=%d)", out_path, len(standings))
        else:
            standings.to_csv(out_path, index=False)
            logging.info("Saved %s", out_path)

        all_standings.append(standings)

    if not all_standings:
        logging.warning("No seasons found in odds_master.")
        return

    combined = pd.concat(all_standings, ignore_index=True)
    combined_path = out_dir / "standings_all_seasons.csv"

    if args.dry_run:
        logging.info("Dry-run: combined standings would be written to %s (rows=%d).", combined_path, len(combined))
        print("[OK] dry-run complete | combined shape:", combined.shape)
        return

    combined.to_csv(combined_path, index=False)
    logging.info("Saved %s", combined_path)
    print("[OK] wrote standings | combined shape:", combined.shape)


if __name__ == "__main__":
    main()
