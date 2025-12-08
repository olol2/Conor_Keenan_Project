# src/analysis/build_player_value_table.py

from __future__ import annotations
"""
Build a consolidated player value table from the combined proxies:

- Rotation proxy (rotation_elasticity + usage rates)
- Injury proxy in points (inj_xpts) and £ (inj_gbp)
- Z-scores for each proxy
- A simple combined index: average of rotation_z and injury_xPts_z

Output:
    results/player_value_table.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
COMBINED_FILE = RESULTS_DIR / "proxies_combined.csv"


def main() -> None:
    df = pd.read_csv(COMBINED_FILE)

    useful = df.copy()

    # ------------------------------------------------------------------
    # Make sure injury columns have standard names
    # ------------------------------------------------------------------
    # If we don't already have inj_xpts but do have xpts_season_total, create it
    if "inj_xpts" not in useful.columns and "xpts_season_total" in useful.columns:
        useful["inj_xpts"] = useful["xpts_season_total"]

    # If we don't already have inj_gbp but do have value_gbp_season_total, create it
    if "inj_gbp" not in useful.columns and "value_gbp_season_total" in useful.columns:
        useful["inj_gbp"] = useful["value_gbp_season_total"]

    # ------------------------------------------------------------------
    # Basic cleaning / typing
    # ------------------------------------------------------------------
    useful["season"] = pd.to_numeric(useful["season"], errors="coerce").astype("Int64")
    if "player_name" in useful.columns:
        useful["player_name"] = useful["player_name"].astype(str)
    if "team_id" in useful.columns:
        useful["team_id"] = useful["team_id"].astype(str)

    # Ensure key numeric columns are actually numeric
    for col in ["rotation_elasticity", "inj_xpts", "inj_gbp"]:
        if col in useful.columns:
            useful[col] = pd.to_numeric(useful[col], errors="coerce")

    # ------------------------------------------------------------------
    # Optionally: keep only rows where at least one proxy exists
    # ------------------------------------------------------------------
    has_rot = useful["rotation_elasticity"].notna() if "rotation_elasticity" in useful.columns else False
    has_inj_pts = useful["inj_xpts"].notna() if "inj_xpts" in useful.columns else False
    has_inj_gbp = useful["inj_gbp"].notna() if "inj_gbp" in useful.columns else False

    mask_keep = has_rot | has_inj_pts | has_inj_gbp
    useful = useful[mask_keep].copy()

    # ------------------------------------------------------------------
    # Standardise continuous proxies (z-scores)
    # ------------------------------------------------------------------
    def zscore(col: str) -> pd.Series:
        x = useful[col]
        m = x.mean()
        s = x.std()
        return (x - m) / s if s > 0 else np.nan

    if "rotation_elasticity" in useful.columns:
        useful["rot_z"] = zscore("rotation_elasticity")

    if "inj_xpts" in useful.columns:
        useful["inj_xpts_z"] = zscore("inj_xpts")

    if "inj_gbp" in useful.columns:
        useful["inj_gbp_z"] = zscore("inj_gbp")

    # ------------------------------------------------------------------
    # Simple combined index
    #    combined_value_z = mean of (rot_z, inj_xpts_z)
    # ------------------------------------------------------------------
    proxy_cols_for_index = [c for c in ["rot_z", "inj_xpts_z"] if c in useful.columns]
    if proxy_cols_for_index:
        useful["combined_value_z"] = useful[proxy_cols_for_index].mean(axis=1)
    else:
        useful["combined_value_z"] = np.nan

    # ------------------------------------------------------------------
    # Order columns nicely
    # ------------------------------------------------------------------
    cols = [
        "player_id",          # Understat numeric ID (if present)
        "player_name",
        "team_id",
        "season",
        "n_matches",
        "n_starts",
        "start_rate_all",
        "start_rate_hard",
        "start_rate_easy",
        "rotation_elasticity",
        "rot_z",
        "inj_xpts",
        "inj_xpts_z",
        "inj_gbp",
        "inj_gbp_z",
        "combined_value_z",
    ]
    cols = [c for c in cols if c in useful.columns]

    value_table = useful[cols].copy().sort_values(
        ["season", "team_id", "player_name"]
    )

    out_path = RESULTS_DIR / "player_value_table.csv"
    value_table.to_csv(out_path, index=False)
    print(f"✅ Saved player value table to {out_path}")
    print("Rows:", len(value_table))
    print(value_table.head())


if __name__ == "__main__":
    main()
