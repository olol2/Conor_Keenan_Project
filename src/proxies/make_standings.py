# src/proxies/make_standings.py
"""Build Premier League final standings from processed odds_master.csv."""

import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

ODDS_MASTER_PATH = ROOT_DIR / "data" / "processed" / "odds" / "odds_master.csv"
OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "standings"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_standings(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """
    df_season: matches for one PL season (football-data format columns)
    season_label: e.g. '2019-2020'
    """

    # Home stats
    home = df_season.groupby("HomeTeam").agg(
        MP_home=("HomeTeam", "size"),
        GF_home=("FTHG", "sum"),
        GA_home=("FTAG", "sum"),
        W_home=("FTR", lambda s: (s == "H").sum()),
        D_home=("FTR", lambda s: (s == "D").sum()),
        L_home=("FTR", lambda s: (s == "A").sum()),
    )

    # Away stats
    away = df_season.groupby("AwayTeam").agg(
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
    table = table.sort_values(
        by=["Pts", "GD", "GF"],
        ascending=[False, False, False],
    )

    # Clean up
    table = table[["MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]]
    table = table.reset_index().rename(columns={"index": "Team"})
    table.insert(0, "Position", range(1, len(table) + 1))
    table.insert(0, "Season", season_label)

    return table


def main() -> None:
    # Read odds master
    df_all = pd.read_csv(ODDS_MASTER_PATH)

    # We expect at least these columns
    required = {"season", "home_team", "away_team", "FTHG", "FTAG", "FTR"}
    missing = required - set(df_all.columns)
    if missing:
        raise ValueError(f"Missing columns in odds_master: {missing}")

    all_standings = []

    # Group by season label in odds_master (e.g. '2019-2020')
    for season_label, df_season_raw in df_all.groupby("season"):
        print(f"Building standings for {season_label}...")
        df_season = df_season_raw.rename(
            columns={
                "home_team": "HomeTeam",
                "away_team": "AwayTeam",
            }
        ).copy()

        standings = build_standings(df_season, season_label)

        out_path = OUTPUT_DIR / f"standings_{season_label}.csv"
        standings.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

        all_standings.append(standings)

    # Optional combined standings file
    if all_standings:
        combined = pd.concat(all_standings, ignore_index=True)
        combined.to_csv(OUTPUT_DIR / "standings_all_seasons.csv", index=False)
        print(f"Saved combined standings_all_seasons.csv")


if __name__ == "__main__":
    main()
