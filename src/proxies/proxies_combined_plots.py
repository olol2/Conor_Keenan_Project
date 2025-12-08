# src/analysis/proxies_combined_plots.py

from __future__ import annotations
"""
Plot the relationship between the rotation proxy (proxy 1)
and the injury proxy in xPts (proxy 2), using the combined
proxies file.

Output:
    results/figures/proxies_scatter_rotation_vs_injury_xpts.png
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

    # Make sure key columns are numeric
    df["rotation_elasticity"] = pd.to_numeric(
        df.get("rotation_elasticity"), errors="coerce"
    )

    # Use inj_xpts if available, else xpts_season_total
    if "inj_xpts" in df.columns:
        df["inj_xpts"] = pd.to_numeric(df["inj_xpts"], errors="coerce")
        y_col = "inj_xpts"
    else:
        df["xpts_season_total"] = pd.to_numeric(
            df.get("xpts_season_total"), errors="coerce"
        )
        y_col = "xpts_season_total"

    # Keep rows where we have both proxies
    sub = df.dropna(subset=["rotation_elasticity", y_col])
    print("Rows with both proxies:", len(sub))

    if len(sub) == 0:
        print("No overlap between proxies, skipping plot.")
        return

    # Optional: correlation for sanity
    corr = sub["rotation_elasticity"].corr(sub[y_col])
    print(f"Correlation (rotation_elasticity vs {y_col}): {corr:.3f}")

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["rotation_elasticity"], sub[y_col])
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
