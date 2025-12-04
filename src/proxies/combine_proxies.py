# src/analysis/combine_proxies.py

from __future__ import annotations
""" NEED TO KNOW WHAT THIS SCRIPT DOES
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"
INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"


def load_rotation() -> pd.DataFrame:
    rot = pd.read_csv(ROT_FILE)
    rot["season"] = rot["season"].astype(int)
    rot["player_name"] = rot["player_name"].astype(str)
    rot["team_id"] = rot["team_id"].astype(str)
    return rot


def load_injury() -> pd.DataFrame:
    inj = pd.read_csv(INJ_FILE)
    inj["season"] = inj["season"].astype(int)
    inj["player_name"] = inj["player_name"].astype(str)
    inj["team_id"] = inj["team_id"].astype(str)
    return inj


def main() -> None:
    rot = load_rotation()
    inj = load_injury()

    # keep only the columns we really need from each side
    rot_keep = [
        "player_id", "player_name", "team_id", "season",
        "n_matches", "n_starts", "start_rate_all",
        "start_rate_hard", "start_rate_easy",
        "rotation_elasticity",
    ]
    rot = rot[rot_keep]

    inj_keep = [
        "player_name", "team_id", "season",
        "beta_unavailable",            # DiD coefficient (missing vs present)
        "xpts_per_match_present",
        "xpts_season_total",
        "value_gbp_season_total",      # £ impact from injuries
    ]
    # only keep cols that actually exist
    inj_keep = [c for c in inj_keep if c in inj.columns]
    inj = inj[inj_keep]

    combined = rot.merge(
        inj,
        on=["player_name", "team_id", "season"],
        how="outer",
        suffixes=("_rot", "_inj"),
    )

    combined["has_rotation"] = ~combined["rotation_elasticity"].isna()
    combined["has_injury"] = ~combined["xpts_season_total"].isna()

    out_path = RESULTS_DIR / "proxies_combined.csv"
    combined.to_csv(out_path, index=False)
    print(f"✅ Saved combined proxies to {out_path}")
    print(f"Rows: {len(combined)}")
    print(combined.head())


if __name__ == "__main__":
    main()
