# src/proxies/proxy1_rotation_elasticity.py

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PANEL_ROTATION_FILE = DATA_PROCESSED / "panel_rotation.parquet"


# ---------------------------------------------------------------------
# Load rotation panel
# ---------------------------------------------------------------------

def load_panel_rotation() -> pd.DataFrame:
    df = pd.read_parquet(PANEL_ROTATION_FILE)

    needed = [
        "match_id",
        "player_id",
        "player_name",
        "team_id",
        "season",
        "date",
        "opponent_id",
        "is_home",
        "xpts",
        "minutes",
        "started",
        "days_rest",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in panel_rotation: {missing}")

    df["season"] = df["season"].astype(int)
    df["player_id"] = df["player_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)

    return df[needed].copy()


# ---------------------------------------------------------------------
# Classify match stakes using xPts
# ---------------------------------------------------------------------

def add_stakes_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each *team-season*, classify matches into:
      - 'hard'   (bottom 1/3 of that team’s xPts that season)
      - 'medium'
      - 'easy'   (top 1/3 of that team’s xPts that season)

    This makes sense for weak teams like Norwich / West Brom, who rarely
    have truly high xPts at league level but *do* have relatively easier
    games compared to their own baseline.
    """
    df = df.copy()

    def team_season_stakes(sub: pd.DataFrame) -> pd.DataFrame:
        q_low = sub["xpts"].quantile(1 / 3)
        q_high = sub["xpts"].quantile(2 / 3)

        def categorize(x):
            if x <= q_low:
                return "hard"
            elif x >= q_high:
                return "easy"
            else:
                return "medium"

        sub["stakes"] = sub["xpts"].apply(categorize)
        return sub

    # 🔁 now group by team *and* season
    df = df.groupby(["team_id", "season"], group_keys=False).apply(team_season_stakes)

    return df


# ---------------------------------------------------------------------
# Compute per-player-season rotation elasticity
# ---------------------------------------------------------------------

def compute_rotation_elasticity(
    df: pd.DataFrame,
    min_matches: int = 3,
    min_hard: int = 1,
    min_easy: int = 1,
) -> pd.DataFrame:
    """
    For each player-season, compute:

      - n_matches: number of matches where the player appeared
      - n_starts, start_rate_all
      - start_rate_hard = start rate in 'hard' matches
      - start_rate_easy = start rate in 'easy' matches
      - rotation_elasticity = start_rate_hard - start_rate_easy
    """
    df = df.copy()
    df["appearance"] = 1

    def agg_rates(sub: pd.DataFrame) -> pd.Series:
        n_matches = sub["appearance"].sum()
        n_starts = sub["started"].sum()

        start_rate_all = n_starts / n_matches if n_matches > 0 else np.nan

        hard = sub[sub["stakes"] == "hard"]
        n_hard = hard["appearance"].sum()
        n_hard_starts = hard["started"].sum()
        start_rate_hard = n_hard_starts / n_hard if n_hard > 0 else np.nan

        easy = sub[sub["stakes"] == "easy"]
        n_easy = easy["appearance"].sum()
        n_easy_starts = easy["started"].sum()
        start_rate_easy = n_easy_starts / n_easy if n_easy > 0 else np.nan

        rotation_elasticity = (
            start_rate_hard - start_rate_easy
            if (not np.isnan(start_rate_hard) and not np.isnan(start_rate_easy))
            else np.nan
        )

        return pd.Series(
            {
                "n_matches": n_matches,
                "n_starts": n_starts,
                "start_rate_all": start_rate_all,
                "n_hard": n_hard,
                "n_hard_starts": n_hard_starts,
                "start_rate_hard": start_rate_hard,
                "n_easy": n_easy,
                "n_easy_starts": n_easy_starts,
                "start_rate_easy": start_rate_easy,
                "rotation_elasticity": rotation_elasticity,
            }
        )

    grouped = (
        df.groupby(["player_id", "player_name", "team_id", "season"])
        .apply(agg_rates)
        .reset_index()
    )

    # Apply more lenient filters so we don't lose whole teams
    grouped["keep"] = (
        (grouped["n_matches"] >= min_matches)
        & (grouped["n_hard"] >= min_hard)
        & (grouped["n_easy"] >= min_easy)
        & grouped["rotation_elasticity"].notna()
    )

    # Diagnostics: see which teams survive the filter
    teams_before = sorted(grouped["team_id"].unique())
    teams_after = sorted(grouped.loc[grouped["keep"], "team_id"].unique())
    print("Teams in rotation panel (before filter):", teams_before)
    print("Teams in rotation proxy  (after filter):", teams_after)
    print(f"Number of teams before: {len(teams_before)}, after: {len(teams_after)}")

    filtered = grouped[grouped["keep"]].drop(columns=["keep"])
    return filtered


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("Loading rotation panel ...")
    df = load_panel_rotation()
    print(f"Rotation panel shape: {df.shape}")

    print("Classifying match stakes (hard / medium / easy) ...")
    df = add_stakes_category(df)

    print("Computing per-player-season rotation elasticity ...")
    rot = compute_rotation_elasticity(df)
    print(f"Computed rotation proxy for {len(rot)} player-seasons.")

    out_path = RESULTS_DIR / "proxy1_rotation_elasticity.csv"
    rot.to_csv(out_path, index=False)
    print(f"✅ Saved rotation elasticity proxy to {out_path}")


if __name__ == "__main__":
    main()
