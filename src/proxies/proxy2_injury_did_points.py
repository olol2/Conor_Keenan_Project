# src/proxies/proxy2_injury_did_points.py

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

# Project root: /files/Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Directory that contains per-season CSVs like:
#   points_to_pounds_2019-2020.csv, points_to_pounds_2020-2021.csv, ...
POINTS_TO_POUNDS_DIR = DATA_PROCESSED / "points_to_pounds"


# ---------------------------------------------------------------------
# Load DiD results
# ---------------------------------------------------------------------

def load_did_results() -> pd.DataFrame:
    """
    Load the raw DiD estimates produced by proxy2_injury_did.py.

    Expected file:
      results/proxy2_injury_did.parquet

    Expected columns:
      player_id, team_id, season,
      beta_unavailable, se_unavailable,
      n_matches, n_unavail, n_avail
    """
    path = RESULTS_DIR / "proxy2_injury_did.parquet"
    df = pd.read_parquet(path)

    needed = [
        "player_id",
        "team_id",
        "season",
        "beta_unavailable",
        "se_unavailable",
        "n_matches",
        "n_unavail",
        "n_avail",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in proxy2_injury_did: {missing}")

    df["season"] = df["season"].astype(int)

    return df[needed].copy()


# ---------------------------------------------------------------------
# Build £ per point mapping from all per-season CSVs
# ---------------------------------------------------------------------

def load_points_to_pounds_all_seasons() -> pd.DataFrame:
    """
    Build a mapping season -> gbp_per_point using all CSVs in
    data/processed/points_to_pounds/.

    Each file is expected to look like:
        Season,Points,Money_gbp
        2019-2020,21,52_527_464.78
        2019-2020,22,55_028_772.63
        ...

    For each season, we fit a simple linear regression:
        Money_gbp ≈ alpha + beta * Points

    and use beta as 'gbp_per_point' for that season.
    """
    if not POINTS_TO_POUNDS_DIR.exists():
        raise FileNotFoundError(f"Points-to-pounds directory not found: {POINTS_TO_POUNDS_DIR}")

    files = sorted(POINTS_TO_POUNDS_DIR.glob("points_to_pounds_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No files named 'points_to_pounds_*.csv' found in {POINTS_TO_POUNDS_DIR}"
        )

    rows: list[dict] = []

    for path in files:
        tmp = pd.read_csv(path)

        # Normalise column names
        tmp = tmp.rename(
            columns={
                "Season": "season_str",
                "Points": "points",
                "Money_gbp": "money_gbp",
            }
        )

        needed = ["season_str", "points", "money_gbp"]
        missing = [c for c in needed if c not in tmp.columns]
        if missing:
            raise ValueError(f"Missing columns in {path.name}: {missing}")

        # Take the season year = first 4 chars of '2019-2020'
        tmp["season"] = tmp["season_str"].astype(str).str.slice(0, 4).astype(int)

        # Fit linear regression money_gbp ~ points
        x = tmp["points"].to_numpy(dtype=float)
        y = tmp["money_gbp"].to_numpy(dtype=float)

        # Simple check
        if len(np.unique(x)) < 2:
            raise ValueError(f"Not enough variation in points in {path.name} to fit a slope.")

        slope, intercept = np.polyfit(x, y, 1)

        season_year = int(tmp["season"].iloc[0])
        rows.append({"season": season_year, "gbp_per_point": float(slope)})

    mapping = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)

    return mapping


# ---------------------------------------------------------------------
# Add points and £ interpretation
# ---------------------------------------------------------------------

def add_points_interpretation(did: pd.DataFrame) -> pd.DataFrame:
    """
    From DiD estimates, compute:

      - xpts_per_match_present:
            how many expected points per match this player is worth
            when they are available (approx. -beta_unavailable).

      - xpts_season_total:
            xpts_per_match_present * n_matches,
            i.e. rough season-level impact in expected points.
    """
    out = did.copy()

    # When the player is unavailable, xpts change by beta_unavailable.
    # So when the player *is* present, we approximate the contribution as -beta.
    out["xpts_per_match_present"] = -out["beta_unavailable"]

    # Season-level impact: contribution per match times number of league matches
    out["xpts_season_total"] = out["xpts_per_match_present"] * out["n_matches"]

    return out


def add_money_interpretation(did_points: pd.DataFrame,
                             mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Merge £/point mapping and compute monetary values:

      - gbp_per_point (from mapping)
      - value_gbp_per_match  = xpts_per_match_present * gbp_per_point
      - value_gbp_season_total = xpts_season_total * gbp_per_point
    """
    out = did_points.merge(mapping, on="season", how="left")

    if out["gbp_per_point"].isna().any():
        missing_seasons = out.loc[out["gbp_per_point"].isna(), "season"].unique()
        print(
            f"⚠️ Warning: missing gbp_per_point for seasons {missing_seasons}. "
            f"Monetary values will be NaN for those rows."
        )

    out["value_gbp_per_match"] = out["xpts_per_match_present"] * out["gbp_per_point"]
    out["value_gbp_season_total"] = out["xpts_season_total"] * out["gbp_per_point"]

    return out


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("Loading DiD results from results/proxy2_injury_did.parquet ...")
    did = load_did_results()
    print(f"Loaded {len(did)} player-seasons.")

    print("Adding xPts-per-match and season-total interpretation ...")
    did_points = add_points_interpretation(did)

    print("Building points-to-pounds mapping from per-season CSVs ...")
    mapping = load_points_to_pounds_all_seasons()
    print(mapping)

    print("Adding monetary (£) interpretation ...")
    did_full = add_money_interpretation(did_points, mapping)

    # Save as CSV for easy inspection / report tables
    csv_path = RESULTS_DIR / "proxy2_injury_did_points_gbp.csv"
    did_full.to_csv(csv_path, index=False)
    print(f"✅ Saved points+£ proxy to {csv_path}")

    # Also save as parquet
    parquet_path = RESULTS_DIR / "proxy2_injury_did_points_gbp.parquet"
    did_full.to_parquet(parquet_path, index=False)
    print(f"✅ Saved points+£ proxy to {parquet_path}")


if __name__ == "__main__":
    main()
