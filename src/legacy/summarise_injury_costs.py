# src/summarise_injury_costs.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT_DIR / "data" / "processed"
RESULTS_DIR = ROOT_DIR / "results"

INJURY_POUNDS_FILE = PROC_DIR / "injury_cost_pounds.csv"


def load_injury_cost_pounds() -> pd.DataFrame:
    if not INJURY_POUNDS_FILE.exists():
        raise FileNotFoundError(
            f"{INJURY_POUNDS_FILE} not found. "
            "Run src/estimate_injury_cost_pounds.py first."
        )
    df = pd.read_csv(INJURY_POUNDS_FILE)
    return df


def make_rankings_by_season(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each Season, rank teams by £ lost to injuries (highest first).
    """
    cols_needed = [
        "Season",
        "Team",
        "n_matches",
        "avg_injured_players",
        "points_lost_due_to_injuries",
        "gbp_per_point",
        "gbp_lost_due_to_injuries",
    ]
    # keep only columns that actually exist
    cols = [c for c in cols_needed if c in df.columns]
    tmp = df[cols].copy()

    # sort within season and create a rank (1 = most £ lost)
    tmp = tmp.sort_values(
        ["Season", "gbp_lost_due_to_injuries"],
        ascending=[True, False],
    )

    tmp["rank_in_season_by_gbp_lost"] = (
        tmp.groupby("Season")["gbp_lost_due_to_injuries"].rank(
            method="min", ascending=False
        )
    )

    return tmp


def make_club_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Overall per-club summary across all seasons:
      - how many seasons
      - average points lost
      - average £ lost
      - total £ lost
    """
    grp = (
        df.groupby("Team")
        .agg(
            n_seasons=("Season", "nunique"),
            total_points_lost=("points_lost_due_to_injuries", "sum"),
            avg_points_lost=("points_lost_due_to_injuries", "mean"),
            total_gbp_lost=("gbp_lost_due_to_injuries", "sum"),
            avg_gbp_lost=("gbp_lost_due_to_injuries", "mean"),
        )
        .reset_index()
    )

    # sort by total £ lost, biggest first
    grp = grp.sort_values("total_gbp_lost", ascending=False)

    return grp


def main():
    df = load_injury_cost_pounds()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Rankings by season
    by_season = make_rankings_by_season(df)
    out1 = RESULTS_DIR / "injury_cost_rankings_by_season.csv"
    by_season.to_csv(out1, index=False)
    print(f"Saved {out1}")

    # 2) Overall club summary
    club_summary = make_club_summary(df)
    out2 = RESULTS_DIR / "injury_cost_club_summary.csv"
    club_summary.to_csv(out2, index=False)
    print(f"Saved {out2}")


if __name__ == "__main__":
    main()
