# scripts/PL_table_creator.py
""" This script processes raw Premier League match results
and computes the final league standings for each season.
"""
import pandas as pd
from pathlib import Path

# -------- paths --------
ROOT_DIR = Path(__file__).resolve().parents[2]

RESULTS_DIR = ROOT_DIR / "data/raw/Odds/results"
OUTPUT_DIR = ROOT_DIR / "data/processed/standings"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# -----------------------


def build_standings(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """
    df_season: matches for one PL season (football-data format)
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


def season_label_from_folder(folder_name: str) -> str:
    """
    '1920' -> '2019-2020'
    '2021' -> '2020-2021'
    '2122' -> '2021-2022'
    etc.
    """
    start_short = int(folder_name[:2])   # e.g. 19
    end_short = int(folder_name[2:])     # e.g. 20
    start_full = 2000 + start_short      # 2019
    end_full = 2000 + end_short          # 2020
    return f"{start_full}-{end_full}"


def main():
    # loop over season folders: 1920, 2021, 2122, ...
    for season_dir in sorted(RESULTS_DIR.iterdir()):
        if not season_dir.is_dir():
            continue

        csv_path = season_dir / "E0.csv"   # PL file inside that folder
        if not csv_path.exists():
            print(f"Skipping {season_dir}, no E0.csv found")
            continue

        print(f"Processing {csv_path}...")
        df = pd.read_csv(csv_path)

        # Build a nice season label from folder name
        season_code = season_dir.name      # e.g. '1920'
        season_label = season_label_from_folder(season_code)

        standings = build_standings(df, season_label)

        out_path = OUTPUT_DIR / f"standings_{season_label}.csv"
        standings.to_csv(out_path, index=False)
        print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
