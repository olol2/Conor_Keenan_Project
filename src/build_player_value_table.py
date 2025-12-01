# src/analysis/build_player_value_table.py

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
COMBINED_FILE = RESULTS_DIR / "proxies_combined.csv"


def main() -> None:
    df = pd.read_csv(COMBINED_FILE)

    # Keep only rows where we have at least one proxy
    useful = df.copy()

    # Rename for convenience
    if "xpts_season_total" in useful.columns:
        useful = useful.rename(columns={"xpts_season_total": "inj_xpts"})
    if "value_gbp_season_total" in useful.columns:
        useful = useful.rename(columns={"value_gbp_season_total": "inj_gbp"})

    # --- basic cleaning ---
    useful["season"] = useful["season"].astype(int)
    useful["player_name"] = useful["player_name"].astype(str)
    useful["team_id"] = useful["team_id"].astype(str)

    # --- standardise continuous proxies (z-scores) ---

    def zscore(col):
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

    # --- simple combined index ---
    # Example: average of rotation_z and injury_xPts_z where both exist
    useful["combined_value_z"] = useful[
        ["rot_z", "inj_xpts_z"]
    ].mean(axis=1)

    # Order columns nicely
    cols = [
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
    value_table = useful[cols].copy()

    out_path = RESULTS_DIR / "player_value_table.csv"
    value_table.to_csv(out_path, index=False)
    print(f"✅ Saved player value table to {out_path}")
    print("Rows:", len(value_table))
    print(value_table.head())


if __name__ == "__main__":
    main()
