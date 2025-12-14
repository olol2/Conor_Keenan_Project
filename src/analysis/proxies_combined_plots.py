from __future__ import annotations

"""
Plot the relationship between Proxy 1 (rotation elasticity)
and Proxy 2 (injury impact in xPts) using the combined proxies file.

Default input:
  results/proxies_combined.csv

Default output:
  results/figures/proxies_scatter_rotation_vs_injury_xpts.png
"""

from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot Proxy 1 vs Proxy 2 relationship from combined proxies file.")
    p.add_argument("--combined", type=str, default=None,
                   help="Path to combined proxies CSV (default: results/proxies_combined.csv)")
    p.add_argument("--fig-dir", type=str, default=None,
                   help="Directory to write figures into (default: results/figures)")
    p.add_argument("--out", type=str, default=None,
                   help="Output PNG path (default: <fig-dir>/proxies_scatter_rotation_vs_injury_xpts.png)")
    p.add_argument("--y-col", type=str, default=None,
                   help="Override injury column for y-axis (else auto: inj_xpts then xpts_season_total)")
    p.add_argument("--dry-run", action="store_true",
                   help="Load + validate only; do not write figure")
    return p.parse_args()


def pick_y_col(df: pd.DataFrame, override: str | None) -> str:
    if override:
        if override not in df.columns:
            raise ValueError(f"--y-col='{override}' not found. Columns: {list(df.columns)}")
        return override

    for c in ["inj_xpts", "xpts_season_total", "injury_xpts", "inj_xpts_season_total"]:
        if c in df.columns:
            return c

    raise ValueError(
        "Could not find injury xPts column. Tried: inj_xpts, xpts_season_total, injury_xpts, inj_xpts_season_total. "
        f"Columns found: {list(df.columns)}"
    )


def main() -> None:
    args = parse_args()

    cfg = Config.load()
    root = Path(__file__).resolve().parents[2]
    results_dir = getattr(cfg, "results", root / "results")
    logs_dir = getattr(cfg, "logs", root / "logs")
    meta_dir = getattr(cfg, "metadata", Path(results_dir) / "metadata")

    logger = setup_logger("proxies_combined_plots", logs_dir, "proxies_combined_plots.log")
    meta_path = write_run_metadata(meta_dir, "proxies_combined_plots", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    combined_path = Path(args.combined) if args.combined else (Path(results_dir) / "proxies_combined.csv")
    fig_dir = Path(args.fig_dir) if args.fig_dir else (Path(results_dir) / "figures")
    out_path = Path(args.out) if args.out else (fig_dir / "proxies_scatter_rotation_vs_injury_xpts.png")

    logger.info("Reading combined proxies from: %s", combined_path)
    logger.info("Writing figure to: %s", out_path)

    if not combined_path.exists():
        raise FileNotFoundError(f"Combined proxies file not found: {combined_path}")

    df = pd.read_csv(combined_path)
    df.columns = [c.strip() for c in df.columns]

    if "rotation_elasticity" not in df.columns:
        raise ValueError(f"'rotation_elasticity' not found. Columns: {list(df.columns)}")

    y_col = pick_y_col(df, args.y_col)

    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")
    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")

    sub = df.dropna(subset=["rotation_elasticity", y_col]).copy()
    print("Rows with both proxies:", len(sub))

    if len(sub) == 0:
        print("No overlap between proxies after numeric coercion; skipping plot.")
        return

    corr = sub["rotation_elasticity"].corr(sub[y_col])
    print(f"Correlation (rotation_elasticity vs {y_col}): {corr if pd.notna(corr) else 'NaN'}")

    if args.dry_run:
        print("✅ dry-run complete | figure NOT written")
        return

    fig_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["rotation_elasticity"], sub[y_col])
    plt.axvline(0, linestyle="--")
    plt.axhline(0, linestyle="--")
    plt.xlabel("Rotation elasticity (hard - easy)")
    plt.ylabel(f"Injury impact in xPts ({y_col})")
    plt.title("Relationship between rotation role and injury impact")
    plt.tight_layout()

    plt.savefig(out_path, dpi=150)
    plt.close()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
