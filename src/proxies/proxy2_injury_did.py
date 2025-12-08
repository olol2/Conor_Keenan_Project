# src/proxies/proxy2_injury_did.py

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

"""
This script takes the panel data `panel_injury.parquet` built from
`build_injury_panel.py` and runs a difference-in-differences regression
for each player–team–season to estimate the impact of player unavailability
on team expected points (xPts).

The output is saved as `results/proxy2_injury_did.parquet`.
"""

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

# Project root: /files/Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Load panel
# ---------------------------------------------------------------------

def load_panel() -> pd.DataFrame:
    """
    Load the player–team–match injury panel created by build_injury_panel.py.

    Expected columns in panel_injury.parquet:
      match_id, team_id, player_id, date, season, opponent_id, xpts,
      unavailable, n_injured_squad
    """
    path = DATA_PROCESSED / "panel_injury.parquet"
    if not path.exists():
        raise FileNotFoundError(f"panel_injury.parquet not found at: {path}")

    df = pd.read_parquet(path)

    needed = [
        "match_id",
        "team_id",
        "player_id",
        "date",
        "season",
        "opponent_id",
        "xpts",
        "unavailable",
        "n_injured_squad",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in panel_injury: {missing}")

    # Basic cleaning / typing
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["season"].astype(int)
    df["unavailable"] = df["unavailable"].astype(int)

    return df[needed].copy()


# ---------------------------------------------------------------------
# Summarise player–seasons
# ---------------------------------------------------------------------

def summarise_player_seasons(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each player–team–season, count matches available vs unavailable.
    """
    summary = (
        df.groupby(["player_id", "team_id", "season"])
        .agg(
            n_matches=("match_id", "nunique"),
            n_unavail=("unavailable", "sum"),
            n_avail=("unavailable", lambda s: (1 - s).sum()),
        )
        .reset_index()
    )
    return summary


def filter_player_seasons(
    summary: pd.DataFrame,
    min_unavail: int = 2,
    min_avail: int = 2,
) -> pd.DataFrame:
    """
    Keep only player–team–seasons with enough variation in availability.
    """
    good = summary.query(
        "n_unavail >= @min_unavail and n_avail >= @min_avail"
    ).copy()

    print(
        f"Player-seasons with variation "
        f"(min_unavail={min_unavail}, min_avail={min_avail}): {len(good)}"
    )
    return good


# ---------------------------------------------------------------------
# Per player–season DiD regression
# ---------------------------------------------------------------------

def estimate_did_for_player_season(
    df: pd.DataFrame,
    pid,
    tid,
    season,
) -> dict | None:
    """
    Run DiD-style OLS for one player–team–season:

        xpts ~ unavailable + C(opponent_id) + C(matchday_index)

    Returns a dict with beta and SE, or None if estimation fails.
    """
    g = df[
        (df["player_id"] == pid)
        & (df["team_id"] == tid)
        & (df["season"] == season)
    ].copy()

    # Need at least some matches in and out
    if g["unavailable"].nunique() < 2:
        return None

    # Sort by date and create a simple time index (matchday FE)
    g = g.sort_values("date")
    g["matchday_index"] = np.arange(len(g))

    try:
        model = smf.ols(
            "xpts ~ unavailable + C(opponent_id) + C(matchday_index)",
            data=g,
        ).fit(cov_type="cluster", cov_kwds={"groups": g["opponent_id"]})

        beta = model.params.get("unavailable", np.nan)
        se = model.bse.get("unavailable", np.nan)

        return {
            "player_id": pid,
            "team_id": tid,
            "season": season,
            "beta_unavailable": float(beta),
            "se_unavailable": float(se),
            "n_matches": int(len(g)),
            "n_unavail": int(g["unavailable"].sum()),
            "n_avail": int((1 - g["unavailable"]).sum()),
        }

    except Exception as e:
        print(f"❌ Failed for player {pid}, team {tid}, season {season}: {e}")
        return None


def run_did(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    min_unavail: int = 2,
    min_avail: int = 2,
) -> pd.DataFrame:
    """
    Loop over all qualifying player–team–seasons and estimate DiD.
    """
    good_ps = filter_player_seasons(
        summary, min_unavail=min_unavail, min_avail=min_avail
    )

    results: list[dict] = []
    for _, row in good_ps.iterrows():
        pid = row["player_id"]
        tid = row["team_id"]
        season = row["season"]

        est = estimate_did_for_player_season(df, pid, tid, season)
        if est is not None:
            results.append(est)

    if not results:
        print(
            "⚠️ No successful DiD estimates. "
            "Consider lowering min_unavail/min_avail or checking panel data."
        )
        return pd.DataFrame()

    out = pd.DataFrame(results)
    return out


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("Loading panel_injury.parquet ...")
    df = load_panel()
    print(f"Panel shape: {df.shape}")

    print("Summarising player–season availability ...")
    summary = summarise_player_seasons(df)
    print(f"Total player–seasons: {len(summary)}")

    print("Running DiD estimations ...")
    did_results = run_did(df, summary, min_unavail=2, min_avail=2)

    if did_results.empty:
        print("No DiD results to save.")
        return

    out_parquet = RESULTS_DIR / "proxy2_injury_did.parquet"
    out_csv = RESULTS_DIR / "proxy2_injury_did.csv"

    did_results.to_parquet(out_parquet, index=False)
    did_results.to_csv(out_csv, index=False)

    print(f"✅ Saved {len(did_results)} player-season estimates to")
    print(f"   - {out_parquet}")
    print(f"   - {out_csv}")



if __name__ == "__main__":
    main()
