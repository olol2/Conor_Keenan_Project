# src/estimate_injury_cost_points.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]

MATCHES_FILE = ROOT_DIR / "data" / "processed" / "matches" / "matches_with_injuries_all_seasons.csv"
COEF_FILE = ROOT_DIR / "results" / "injury_regression_coefficients.csv"
OUT_FILE = ROOT_DIR / "data" / "processed" / "injury_cost_points.csv"


def load_injured_players_coef() -> float:
    coef_df = pd.read_csv(COEF_FILE)
    row = coef_df.loc[coef_df["term"] == "injured_players"]
    if row.empty:
        raise ValueError("Could not find 'injured_players' term in regression coefficients.")
    return float(row["coef"].iloc[0])


def main():
    # 1) Load matches with injuries
    matches = pd.read_csv(MATCHES_FILE, parse_dates=["Date"])

    # Drop 2024-2025 for now (no reliable injury data)
    matches = matches[matches["Season"] != "2024-2025"].copy()

    # 2) Load regression coefficient
    beta_inj = load_injured_players_coef()
    print(f"Using injured_players coefficient: {beta_inj:.4f} (Pts - xPts per injured player)")

    # 3) Compute per-match injury effect on (Pts - xPts)
    matches["injury_effect_pts_minus_xpts"] = beta_inj * matches["injured_players"]

    # 4) Aggregate per team-season
    grp = (
        matches.groupby(["Season", "Team"])
        .agg(
            n_matches=("Team", "size"),
            avg_injured_players=("injured_players", "mean"),
            total_injured_players=("injured_players", "sum"),
            total_injury_effect_pts_minus_xpts=("injury_effect_pts_minus_xpts", "sum"),
        )
        .reset_index()
    )

    # Interpret as "points lost" (multiply by -1 so positive = cost)
    grp["points_lost_due_to_injuries"] = -grp["total_injury_effect_pts_minus_xpts"]

    # 5) Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    grp.to_csv(OUT_FILE, index=False)
    print(f"Saved injury cost (points) per team-season to {OUT_FILE}")


if __name__ == "__main__":
    main()
