# scripts/points_to_pounds.py

import pandas as pd
from pathlib import Path
"""
    This script computes the value of Premier League points in GBP
    based on final league standings and prize money data.
    It outputs CSV files mapping points to pounds for each season.
"""
# ---------- paths ----------
ROOT_DIR = Path(__file__).resolve().parents[2]

STANDINGS_DIR = ROOT_DIR / "data/processed/standings"
PRIZE_FILE = ROOT_DIR / "data/raw/pl_prize_money.csv"
OUTPUT_DIR = ROOT_DIR / "data/processed/points_to_pounds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# ---------------------------


def load_standings() -> pd.DataFrame:
    """Load all per-season standings_*.csv into one DataFrame."""
    frames = []
    for path in sorted(STANDINGS_DIR.glob("standings_*.csv")):
        # Skip the combined file to avoid duplicates
        if "all_seasons" in path.name:
            continue
        df = pd.read_csv(path)
        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            f"No per-season standings_*.csv files found in {STANDINGS_DIR}. "
            "Run make_standings.py first."
        )

    standings = pd.concat(frames, ignore_index=True)

    # --- Make sure we have 'Season', 'Team', 'Pts' columns ---

    if "Season" not in standings.columns:
        raise ValueError(
            f"'Season' column not found in standings files. "
            f"Columns are: {list(standings.columns)}"
        )

    if "Team" not in standings.columns:
        if "HomeTeam" in standings.columns:
            standings = standings.rename(columns={"HomeTeam": "Team"})
        else:
            possible_team_cols = [
                c
                for c in standings.columns
                if c.lower() in ("team", "club", "squad", "hometeam", "awayteam")
            ]
            if not possible_team_cols:
                raise ValueError(
                    "Could not find a team column in standings files. "
                    f"Available columns: {list(standings.columns)}"
                )
            team_col = possible_team_cols[0]
            standings = standings.rename(columns={team_col: "Team"})

    if "Pts" not in standings.columns:
        raise ValueError(
            f"'Pts' column not found in standings files. "
            f"Columns are: {list(standings.columns)}"
        )

    return standings



def main():
    # 1) Load standings and prize-money data (all in GBP)
    standings = load_standings()
    prize = pd.read_csv(PRIZE_FILE)

    required_cols = {"Season", "Team", "pl_total_gbp"}
    missing = required_cols - set(prize.columns)
    if missing:
        raise ValueError(
            f"pl_prize_money.csv is missing columns: {missing}. "
            f"It must at least have: {required_cols}."
        )

    # 2) Merge money onto standings
    df = standings.merge(
        prize,
        on=["Season", "Team"],
        how="inner",
        validate="one_to_one",
    )

    # All money is in GBP
    df["money_gbp"] = df["pl_total_gbp"]

    # 3) For each season, compute pounds-per-point and save mapping CSV
    for season, df_season in df.groupby("Season"):
        total_money = df_season["money_gbp"].sum()
        total_points = df_season["Pts"].sum()

        if total_points == 0:
            print(f"Skipping {season}: total_points = 0")
            continue

        pounds_per_point = total_money / total_points
        print(f"{season}: value per point ≈ £{pounds_per_point:,.0f}")

        # Range of points observed that season
        min_pts = int(df_season["Pts"].min())
        max_pts = int(df_season["Pts"].max())

        mapping = pd.DataFrame(
            {
                "Season": [season] * (max_pts - min_pts + 1),
                "Points": list(range(min_pts, max_pts + 1)),
            }
        )
        mapping["Money_gbp"] = mapping["Points"] * pounds_per_point

        out_path = OUTPUT_DIR / f"points_to_pounds_{season}.csv"
        mapping.to_csv(out_path, index=False)
        print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
