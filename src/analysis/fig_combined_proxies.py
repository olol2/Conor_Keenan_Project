# src/analysis/fig_combined_proxies.py

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

COMBINED_FILE = RESULTS_DIR / "proxies_combined.csv"


def main() -> None:
    df = pd.read_csv(COMBINED_FILE)

    # Ensure expected names (same as in combine_proxies script)
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df = df.rename(columns={"xpts_season_total": "inj_xpts"})

    sub = df.dropna(subset=["rotation_elasticity", "inj_xpts"])
    print("Rows with both proxies:", len(sub))

    if len(sub) == 0:
        print("No overlap between proxies; skipping scatter.")
        return

    plt.figure(figsize=(8, 6))
    plt.scatter(sub["rotation_elasticity"], sub["inj_xpts"])
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
