# src/analysis/combine_proxies.py

from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"
INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"
OUT_FILE = RESULTS_DIR / "proxies_combined.csv"


def load_rotation() -> pd.DataFrame:
    """Load rotation proxy and standardise keys."""
    rot = pd.read_csv(ROT_FILE)

    rot["player_id"] = pd.to_numeric(rot["player_id"], errors="coerce").astype("Int64")
    rot["season"] = pd.to_numeric(rot["season"], errors="coerce").astype("Int64")
    rot["player_name"] = rot["player_name"].astype(str)
    rot["team_id"] = rot["team_id"].astype(str)

    return rot


def load_injury() -> pd.DataFrame:
    """Load final injury proxy with Understat IDs and short team names."""
    inj = pd.read_csv(INJ_FILE)

    inj["player_id"] = pd.to_numeric(inj["player_id"], errors="coerce").astype("Int64")
    inj["season"] = pd.to_numeric(inj["season"], errors="coerce").astype("Int64")
    if "player_name" in inj.columns:
        inj["player_name"] = inj["player_name"].astype(str)
    inj["team_id"] = inj["team_id"].astype(str)

    return inj


def main() -> None:
    rot = load_rotation()
    inj = load_injury()

    # Columns to keep from each side
    rot_keep = [
        "player_id",
        "player_name",
        "team_id",
        "season",
        "n_matches",
        "n_starts",
        "start_rate_all",
        "start_rate_hard",
        "start_rate_easy",
        "rotation_elasticity",
    ]
    rot = rot[rot_keep]

    inj_keep = [
        "player_id",
        "player_name",
        "team_id",
        "season",
        "beta_unavailable",
        "xpts_per_match_present",
        "xpts_season_total",
        "value_gbp_season_total",
    ]
    inj_keep = [c for c in inj_keep if c in inj.columns]
    inj = inj[inj_keep]

    # Merge on IDs + season + team
    combined = rot.merge(
        inj,
        on=["player_id", "season", "team_id"],
        how="outer",
        suffixes=("_rot", "_inj"),
    )

    # Build a single player_name column (prefer rotation name, fall back to injury)
    if "player_name_rot" in combined.columns and "player_name_inj" in combined.columns:
        combined["player_name"] = combined["player_name_rot"].fillna(
            combined["player_name_inj"]
        )
    elif "player_name_rot" in combined.columns:
        combined["player_name"] = combined["player_name_rot"]
    elif "player_name_inj" in combined.columns:
        combined["player_name"] = combined["player_name_inj"]

    # Drop the intermediate name columns if they exist
    for col in ["player_name_rot", "player_name_inj"]:
        if col in combined.columns:
            combined = combined.drop(columns=col)

    # Convenience flags
    combined["has_rotation"] = ~combined["rotation_elasticity"].isna()
    combined["has_injury"] = ~combined["xpts_season_total"].isna()

    # Optional: create inj_xpts column for plotting / summaries
    if "xpts_season_total" in combined.columns and "inj_xpts" not in combined.columns:
        combined["inj_xpts"] = combined["xpts_season_total"]

    # Nice ordering for inspection
    combined = combined.sort_values(
        ["season", "team_id", "player_name"]
    ).reset_index(drop=True)

    combined.to_csv(OUT_FILE, index=False)
    print(f"✅ Saved combined proxies to {OUT_FILE}")
    print(f"Rows: {len(combined)}")
    print("Distinct teams:", combined["team_id"].nunique())
    print(combined.head())


if __name__ == "__main__":
    main()
