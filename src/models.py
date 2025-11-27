# src/models.py

from typing import Dict
import pandas as pd


def run_core_analysis(data: Dict[str, pd.DataFrame]):
    """
    First simple core analysis:
    - Use the team–match panel with injuries
    - Compare average points and xPts when teams have injuries vs no injuries,
      by season (for seasons where we actually have injury data).

    This is a descriptive first step, not the final model.
    """

    matches = data["matches"].copy()

    # For now, restrict to seasons where we have proper injury data.
    # 2024-2025 will still have injured_players == 0 everywhere.
    matches = matches[matches["Season"] != "2024-2025"]

    # Flag whether the team had any injured players on that match date
    matches["has_injured"] = matches["injured_players"] > 0

    # Basic summary by season and injury flag
    injury_summary = (
        matches.groupby(["Season", "has_injured"])
        .agg(
            n_team_matches=("Team", "size"),
            avg_pts=("Pts", "mean"),
            avg_xpts=("xPts", "mean"),
            avg_injured_players=("injured_players", "mean"),
        )
        .reset_index()
        .sort_values(["Season", "has_injured"])
    )

    # Also compute overall averages across seasons (optional)
    overall_summary = (
        matches.groupby("has_injured")
        .agg(
            n_team_matches=("Team", "size"),
            avg_pts=("Pts", "mean"),
            avg_xpts=("xPts", "mean"),
            avg_injured_players=("injured_players", "mean"),
        )
        .reset_index()
        .sort_values("has_injured")
    )

    return {
        "injury_summary_by_season": injury_summary,
        "injury_summary_overall": overall_summary,
    }
