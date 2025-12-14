# src/proxies/make_standings.py
"""
Build Premier League final standings from processed odds_master.csv.

Input (default):
  data/processed/odds/odds_master.csv

Outputs (default):
  data/processed/standings/standings_<season>.csv
  data/processed/standings/standings_all_seasons.csv

Assumptions:
  - One row per league match
  - Columns include season, home_team, away_team, FTHG, FTAG, FTR
  - FTR is "H"/"D"/"A"
"""

from __future__ import annotations

from pathlib import Path
import argparse
import logging

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ODDS_MASTER = ROOT_DIR / "data" / "processed" / "odds" / "odds_master.csv"
DEFAULT_OUT_DIR = ROOT_DIR / "data" / "processed" / "standings"


def build_standings(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """
    df_season: matches for one season (expects columns: HomeTeam, AwayTeam, FTHG, FTAG, FTR)
    season_label: e.g. '2019-2020'
    """
    required = {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
    missing = required - set(df_season.columns)
    if missing:
        raise ValueError(f"Season {season_label}: missing columns {sorted(missing)}")

    # Ensure clean team names
    df = df_season.copy()
    df["HomeTeam"] = df["HomeTeam"].astype(str).str.strip()
    df["AwayTeam"] = df["AwayTeam"].astype(str).str.strip()

    # Ensure numeric goals
    df["FTHG"] = pd.to_numeric(df["FTHG"], errors="coerce")
    df["FTAG"] = pd.to_numeric(df["FTAG"], errors="coerce")

    # Home stats
    home = df.groupby("HomeTeam").agg(
        MP_home=("HomeTeam", "size"),
        GF_home=("FTHG", "sum"),
        GA_home=("FTAG", "sum"),
        W_home=("FTR", lambda s: (s == "H").sum()),
        D_home=("FTR", lambda s: (s == "D").sum()),
        L_home=("FTR", lambda s: (s == "A").sum()),
    )

    # Away stats
    away = df.groupby("AwayTeam").agg(
        MP_away=("AwayTeam", "size"),
        GF_away=("FTAG", "sum"),
        GA_away=("FTHG", "sum"),
        W_away=("FTR", lambda s: (s == "A").sum()),
        D_away=("FTR", lambda s: (s == "D").sum()),
        L_away=("FTR", lambda s: (s == "H").sum()),
    )

    # Combine
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

    # Sort by points, goal difference, goals for
    table = table.sort_values(by=["Pts", "GD", "GF"], ascending=[False, False, False])

    # Clean + cast to int where appropriate
    table = table[["MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]].copy()
    for c in ["MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
        table[c] = pd.to_numeric(table[c], errors="coerce").fillna(0).astype(int)

    table = table.reset_index().rename(columns={"index": "Team"})
    table.insert(0, "Position", range(1, len(table) + 1))
    table.insert(0, "Season", season_label)

    return table


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build league standings from odds_master.csv.")
    p.add_argument("--odds-master", type=str, default=str(DEFAULT_ODDS_MASTER),
                   help="Path to odds_master.csv")
    p.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR),
                   help="Output directory for standings CSVs")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute but do not write outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    odds_master_path = Path(args.odds_master)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not odds_master_path.exists():
        raise FileNotFoundError(f"odds_master.csv not found: {odds_master_path}")

    df_all = pd.read_csv(odds_master_path)

    required = {"season", "home_team", "away_team", "FTHG", "FTAG", "FTR"}
    missing = required - set(df_all.columns)
    if missing:
        raise ValueError(f"Missing columns in odds_master: {sorted(missing)}")

    all_standings: list[pd.DataFrame] = []

    for season_label, df_season_raw in df_all.groupby("season"):
        logging.info("Building standings for %s...", season_label)

        df_season = df_season_raw.rename(
            columns={"home_team": "HomeTeam", "away_team": "AwayTeam"}
        ).copy()

        standings = build_standings(df_season, str(season_label))

        # Basic sanity check (warn only)
        n_teams = len(standings)
        mp_vals = standings["MP"].unique().tolist()
        if n_teams != 20:
            logging.warning("Season %s: standings has %s teams (expected 20).", season_label, n_teams)
        if len(mp_vals) > 1:
            logging.warning("Season %s: teams have different MP values: %s", season_label, mp_vals)

        out_path = out_dir / f"standings_{season_label}.csv"
        if not args.dry_run:
            standings.to_csv(out_path, index=False)
            logging.info("Saved %s", out_path)

        all_standings.append(standings)

    if all_standings:
        combined = pd.concat(all_standings, ignore_index=True)
        combined_path = out_dir / "standings_all_seasons.csv"
        if args.dry_run:
            logging.info("Dry-run: combined standings would be written to %s (rows=%s).", combined_path, len(combined))
            print("✅ dry-run complete | combined shape:", combined.shape)
        else:
            combined.to_csv(combined_path, index=False)
            logging.info("Saved %s", combined_path)
            print("✅ wrote standings | combined shape:", combined.shape)
    else:
        logging.warning("No seasons found in odds_master.")


if __name__ == "__main__":
    main()
