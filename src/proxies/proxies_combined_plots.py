# src/analysis/proxies_combined_plots.py
from __future__ import annotations

"""
Plot the relationship between the rotation proxy (proxy 1)
and the injury proxy in xPts (proxy 2), using the combined
proxies file.

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
    p.add_argument("--combined", type=str, default=None, help="Path to combined proxies CSV (default: results/proxies_combined.csv)")
    p.add_argument("--fig-dir", type=str, default=None, help="Directory to write figures into (default: results/figures)")
    p.add_argument("--out", type=str, default=None, help="Output PNG path (default: <fig-dir>/proxies_scatter_rotation_vs_injury_xpts.png)")
    p.add_argument("--y-col", type=str, default=None, help="Override injury column for y-axis (else auto: inj_xpts then xpts_season_total)")
    p.add_argument("--dry-run", action="store_true", help="Load + validate only; do not write figure")
    return p.parse_args()


def _pick_y_col(df: pd.DataFrame, override: str | None) -> str:
    if override:
        if override not in df.columns:
            raise ValueError(f"--y-col='{override}' not found in columns: {list(df.columns)}")
        return override

    # Prefer common names (keep this ordered)
    candidates = [
        "inj_xpts",
        "xpts_season_total",
        "injury_xpts",
        "inj_xpts_season_total",
    ]
    for c in candidates:
        if c in df.columns:
            return c

    raise ValueError(
        "Could not find an injury xPts column. Looked for: "
        + ", ".join(candidates)
        + f". Columns found: {list(df.columns)}"
    )


def main() -> None:
    args = parse_args()

    # Use Config if available; fall back to ROOT-based paths safely
    cfg = Config.load()
    root = Path(__file__).resolve().parents[2]
    results_dir = getattr(cfg, "results", root / "results")
    logs_dir = getattr(cfg, "logs", root / "logs")
    meta_dir = getattr(cfg, "metadata", results_dir / "metadata")

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
        raise ValueError(f"'rotation_elasticity' not found in combined file. Columns: {list(df.columns)}")

    y_col = _pick_y_col(df, args.y_col)

    # Coerce numeric
    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")
    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")

    sub = df.dropna(subset=["rotation_elasticity", y_col]).copy()
    n = len(sub)
    logger.info("Rows with both proxies: %d", n)
    print("Rows with both proxies:", n)

    if n == 0:
        print("No overlap between proxies (after numeric coercion), skipping plot.")
        return

    corr = sub["rotation_elasticity"].corr(sub[y_col])
    if pd.isna(corr):
        logger.info("Correlation is NaN (likely constant series).")
        print(f"Correlation (rotation_elasticity vs {y_col}): NaN")
    else:
        logger.info("Correlation(rotation_elasticity, %s)=%.4f", y_col, float(corr))
        print(f"Correlation (rotation_elasticity vs {y_col}): {float(corr):.3f}")

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
    logger.info("Saved figure: %s", out_path)


if __name__ == "__main__":
    main()
