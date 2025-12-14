# src/analysis/proxy2_injury_plots.py
from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

def load_injury_data(path: Path, logger) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Expected columns; if missing, create as NA (so plots can be skipped gracefully)
    expected_cols = [
        "player_name",
        "team_id",
        "season",
        "xpts_per_match_present",
        "xpts_season_total",
        "value_gbp_season_total",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # Basic cleanup
    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["team_id"] = df["team_id"].astype(str).str.strip()

    # season can be Int64 (nullable) if anything odd slips through
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    # numeric columns
    for col in ["xpts_per_match_present", "xpts_season_total", "value_gbp_season_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("Loaded injury proxy for plotting: shape=%s | path=%s", df.shape, path)
    return df


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def _savefig(fig_dir: Path, name: str, logger) -> None:
    out_path = fig_dir / name
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Saved figure: %s", out_path)


def plot_hist(df: pd.DataFrame, col: str, xlabel: str, title: str, fig_dir: Path, fname: str, bins: int, logger) -> None:
    data = df[col].dropna()
    if data.empty:
        logger.warning("No data for %s; skipping %s.", col, fname)
        return

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=bins, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.xlabel(xlabel)
    plt.ylabel("Number of player-seasons")
    plt.title(title)
    _savefig(fig_dir, fname, logger)


def plot_top10_barh(df: pd.DataFrame, col: str, xlabel: str, title: str, fig_dir: Path, fname: str, top_n: int, logger) -> None:
    sub = df.dropna(subset=[col]).copy()
    if sub.empty:
        logger.warning("No data for %s; skipping %s.", col, fname)
        return

    top = sub.sort_values(col, ascending=False).head(top_n)

    labels = [
        f"{row.player_name} ({row.team_id} {int(row.season) if pd.notna(row.season) else 'NA'})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top[col].iloc[::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel(xlabel)
    plt.title(title)
    _savefig(fig_dir, fname, logger)


def plot_scatter(df: pd.DataFrame, x: str, y: str, title: str, fig_dir: Path, fname: str, logger) -> None:
    sub = df.dropna(subset=[x, y]).copy()
    if sub.empty:
        logger.warning("No data for scatter (%s vs %s); skipping %s.", x, y, fname)
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub[x], sub[y])
    plt.xlabel("Season impact in xPts")
    plt.ylabel("Season impact in £")
    plt.title(title)
    _savefig(fig_dir, fname, logger)


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Make plots for Proxy 2 (injury DiD) outputs.")
    p.add_argument("--injury-file", type=str, default=None, help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--fig-dir", type=str, default=None, help="Directory to write figures into")
    p.add_argument("--bins", type=int, default=20, help="Histogram bins")
    p.add_argument("--top-n", type=int, default=10, help="Top N for bar charts")
    p.add_argument("--dry-run", action="store_true", help="Run load + validation but do not write figures")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config.load()

    logger = setup_logger("proxy2_injury_plots", cfg.logs, "proxy2_injury_plots.log")
    meta_path = write_run_metadata(cfg.metadata, "proxy2_injury_plots", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    injury_file = Path(args.injury_file) if args.injury_file else (cfg.project_root / "results" / "proxy2_injury_final_named.csv")
    fig_dir = Path(args.fig_dir) if args.fig_dir else (cfg.project_root / "results" / "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = load_injury_data(injury_file, logger)
    print(f"Loaded {len(df)} player-seasons for plotting.")

    if args.dry_run:
        logger.info("Dry-run complete. Figures not written.")
        print("✅ dry-run complete | figures NOT written")
        return

    plot_hist(
        df,
        col="xpts_per_match_present",
        xlabel="xPts per match when present",
        title="Distribution of injury impact per match (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_hist_xpts_per_match.png",
        bins=args.bins,
        logger=logger,
    )

    plot_hist(
        df,
        col="xpts_season_total",
        xlabel="Season impact in xPts",
        title="Distribution of season-level injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_hist_xpts_season_total.png",
        bins=args.bins,
        logger=logger,
    )

    plot_top10_barh(
        df,
        col="xpts_season_total",
        xlabel="Season impact in xPts",
        title=f"Top {args.top_n} player-seasons by injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_top10_xpts_season.png",
        top_n=args.top_n,
        logger=logger,
    )

    plot_top10_barh(
        df,
        col="value_gbp_season_total",
        xlabel="Season impact in £ (expected)",
        title=f"Top {args.top_n} player-seasons by injury impact (£)",
        fig_dir=fig_dir,
        fname="proxy2_top10_value_gbp.png",
        top_n=args.top_n,
        logger=logger,
    )

    plot_scatter(
        df,
        x="xpts_season_total",
        y="value_gbp_season_total",
        title="Relationship between points and monetary impact",
        fig_dir=fig_dir,
        fname="proxy2_scatter_xpts_vs_gbp.png",
        logger=logger,
    )

    print(f"✅ wrote figures to: {fig_dir}")


if __name__ == "__main__":
    main()
