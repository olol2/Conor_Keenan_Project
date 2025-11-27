# src/estimate_injury_cost_points.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]

MATCHES_FILE = ROOT_DIR / "data" / "processed" / "matches" / "matches_with_injuries_all_seasons.csv"
COEF_FILE = ROOT_DIR / "results" / "injury_regression_coefficients.csv"
OUT_FILE = ROOT_DIR / "data" / "processed" / "injury_cost_points.csv"


def load_injured_players_coef() -> float:
    """
    Load the regression coefficient on injured_players from
    results/injury_regression_coefficients.csv.
    """
    if not COEF_FILE.exists():
        raise FileNotFoundError(
            f"{COEF_FILE} not found. "
            "Run `python main.py` first to fit the regression."
        )

    coef_df = pd.read_csv(COEF_FILE)
    row = coef_df.loc[coef_df["term"] == "injured_players"]
    if row.empty:
        raise ValueError(
            "Could not find 'injured_players' term in regression coefficients. "
            "Check results/injury_regression_coefficients.csv."
        )
    return float(row["coef"].iloc[0])


def main():
    # 1) Load matches with injuries
    if not MATCHES_FILE.exists():
        raise FileNotFoundError(
            f"{MATCHES_FILE} not found. "
            "Run `python src/add_injuries_to_matches.py` first."
        )

    matches = pd.read_csv(MATCHES_FILE, parse_dates=["Date"])

    # Keep all seasons, including 2024-2025 now that injuries_2025 exists
    # (no Season filter here)

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

    # Extra info: flag whether we actually ever saw an injury for this team-season
    grp["has_any_injury_data"] = grp["total_injured_players"] > 0

    # Interpret as "points lost" (positive = cost)
    grp["points_lost_due_to_injuries"] = -grp["total_injury_effect_pts_minus_xpts"]

    # 5) Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    grp.to_csv(OUT_FILE, index=False)
    print(f"Saved injury cost (points) per team-season to {OUT_FILE}")


if __name__ == "__main__":
    main()
