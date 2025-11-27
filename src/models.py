# src/models.py

from typing import Dict
import pandas as pd
import statsmodels.formula.api as smf


def _build_injury_summaries(matches: pd.DataFrame):
    """Descriptive summaries you already generated."""
    # Drop 2024-2025 for now (no reliable injury data)
    matches = matches[matches["Season"] != "2024-2025"].copy()

    matches["has_injured"] = matches["injured_players"] > 0

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

    return injury_summary, overall_summary


def _run_injury_regression(matches: pd.DataFrame) -> Dict[str, object]:
    """
    Core model:
      pts_minus_xpts ~ injured_players + Season FE + Team FE
    """

    # keep only seasons with injury data
    df = matches[matches["Season"] != "2024-2025"].copy()

    # outcome: performance vs expectation
    df["pts_minus_xpts"] = df["Pts"] - df["xPts"]

    # basic sanity filter (optional, avoids crazy outliers if any)
    df = df[df["injured_players"] <= 25]

    # fit OLS with season and team fixed effects
    model = smf.ols(
        "pts_minus_xpts ~ injured_players + C(Season) + C(Team)",
        data=df,
    ).fit(cov_type="cluster", cov_kwds={"groups": df["Team"]})

    # build a tidy coefficient table
    coef_table = (
        pd.DataFrame(
            {
                "term": model.params.index,
                "coef": model.params.values,
                "std_err": model.bse.values,
                "t_value": model.tvalues.values,
                "p_value": model.pvalues.values,
            }
        )
        .sort_values("term")
        .reset_index(drop=True)
    )

    summary_text = model.summary().as_text()

    return {
        "injury_reg_coef": coef_table,
        "injury_reg_summary_text": summary_text,
    }


def run_core_analysis(data: Dict[str, pd.DataFrame]) -> Dict[str, object]:
    """
    Run core analyses:
      1) descriptive summaries by injury status
      2) regression of pts_minus_xpts on injured_players with FE
    """

    matches = data["matches"].copy()

    injury_summary, overall_summary = _build_injury_summaries(matches)
    reg_results = _run_injury_regression(matches)

    results: Dict[str, object] = {
        "injury_summary_by_season": injury_summary,
        "injury_summary_overall": overall_summary,
    }
    results.update(reg_results)
    return results
