# src/analysis/proxies_combined_plots.py

from __future__ import annotations
""" NEED TO KNOW WHAT THIS SCRIPT DOES
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

COMBINED_FILE = RESULTS_DIR / "proxies_combined.csv"


def main() -> None:
    df = pd.read_csv(COMBINED_FILE)

    # keep rows where we have both proxies
    sub = df.dropna(subset=["rotation_elasticity", "xpts_season_total"])
    print("Rows with both proxies:", len(sub))

    if len(sub) == 0:
        print("No overlap between proxies, skipping plot.")
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["rotation_elasticity"], sub["xpts_season_total"])
    plt.axvline(0, linestyle="--")
    plt.axhline(0, linestyle="--")
    plt.xlabel("Rotation elasticity (hard - easy)")
    plt.ylabel("Season injury impact in xPts")
    plt.title("Relationship between rotation role and injury impact")
    plt.tight_layout()

    out_path = FIG_DIR / "proxies_scatter_rotation_vs_injury_xpts.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
