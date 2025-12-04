from __future__ import annotations
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"
INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"


def main() -> None:
    rot = pd.read_csv(ROT_FILE)
    inj = pd.read_csv(INJ_FILE)

    # Make sure key columns are aligned
    for df in (rot, inj):
        df["season"] = df["season"].astype(int)
        df["team_id"] = df["team_id"].astype(str)
        df["player_id"] = df["player_id"].astype(str)

    merged = rot.merge(
        inj[
            ["player_id", "team_id", "season", "xpts_season_total"]
        ],
        on=["player_id", "team_id", "season"],
        how="inner",
    )

    print("Merged player-seasons:", len(merged))

    sub = merged.dropna(subset=["rotation_elasticity", "xpts_season_total"])
    plt.figure(figsize=(8, 5))
    plt.scatter(sub["rotation_elasticity"], sub["xpts_season_total"], alpha=0.5)
    plt.xlabel("Rotation elasticity (hard - easy)")
    plt.ylabel("Season injury impact in xPts")
    plt.title("Rotation role vs injury impact (player-seasons)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxies_scatter_rotation_vs_injury_xpts_static.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
