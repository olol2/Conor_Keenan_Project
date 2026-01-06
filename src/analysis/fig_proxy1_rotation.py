"""
Creates summary figures for Proxy 1 (Rotation Elasticity).

Input:
  results/proxy1_rotation_elasticity.csv

Output:
  results/figures/
    - proxy1_hist_rotation_elasticity.png
    - proxy1_top_rotation_elasticity.png
    - proxy1_team_boxplot_rotation_elasticity.png
    - proxy1_trend_rotation_elasticity_by_season.png

Notes:
- This script is deterministic: it only reads the already-built proxy CSV and writes figures.
"""

from __future__ import annotations
from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Defaults (root-relative, independent of Config internals)
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2] 
DEFAULT_ROT_FILE = ROOT / "results" / "proxy1_rotation_elasticity.csv"
DEFAULT_FIG_DIR = ROOT / "results" / "figures"


# ---------------------------------------------------------------------
# Load + basic validation
# ---------------------------------------------------------------------

def load_rotation(rot_file: Path) -> pd.DataFrame:
    """
    Load Proxy 1 rotation elasticity output and enforce required schema.

    Required columns:
      season, player_name, team_id, rotation_elasticity

    Returns:
      Cleaned DataFrame with types coerced and invalid rows dropped for plotting.
    """
    if not rot_file.exists():
        raise FileNotFoundError(f"Rotation proxy not found: {rot_file}")

    df = pd.read_csv(rot_file)
    df.columns = [c.strip() for c in df.columns]

    required = {"season", "player_name", "team_id", "rotation_elasticity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Rotation proxy missing columns: {sorted(missing)}. Columns={list(df.columns)}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")

    # Drops rows unusable for plots
    df = df.dropna(subset=["season", "team_id", "player_name", "rotation_elasticity"]).copy()

    return df


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def _save(fig_dir: Path, fname: str, logger=None) -> Path:
    """Tight layout + save figure consistently."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_path = fig_dir / fname
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    if logger:
        logger.info("Saved figure: %s", out_path)
    print(f"Saved {out_path}")
    return out_path


def plot_hist_rotation(df: pd.DataFrame, fig_dir: Path, bins: int, logger=None) -> None:
    """Histogram of rotation_elasticity with reference lines at 0 and the mean."""
    data = df["rotation_elasticity"].dropna()
    if data.empty:
        if logger:
            logger.warning("No rotation_elasticity data; skipping histogram.")
        return

    mean_val = float(data.mean())

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=bins, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.axvline(mean_val, linestyle=":", linewidth=2)

    plt.xlabel("Rotation elasticity (start_rate_hard - start_rate_easy)")
    plt.ylabel("Number of player-seasons")
    plt.title("Distribution of rotation elasticity")

    _save(fig_dir, "proxy1_hist_rotation_elasticity.png", logger=logger)


def plot_top_rotation(df: pd.DataFrame, fig_dir: Path, top_n: int, logger=None) -> None:
    """Top-N player-seasons by rotation_elasticity."""
    top = (
        df.dropna(subset=["rotation_elasticity"])
        .sort_values("rotation_elasticity", ascending=False)
        .head(top_n)
        .copy()
    )
    if top.empty:
        if logger:
            logger.warning("No data for rotation_elasticity; skipping top-N plot.")
        return

    labels = [f"{row.player_name} ({row.team_id} {int(row.season)})" for _, row in top.iterrows()]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["rotation_elasticity"].iloc[::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Rotation elasticity (hard - easy)")
    plt.title(f"Top {top_n} player-seasons by rotation elasticity")

    _save(fig_dir, "proxy1_top_rotation_elasticity.png", logger=logger)


def plot_team_boxplot_rotation(df: pd.DataFrame, fig_dir: Path, logger=None) -> None:
    """Boxplot of rotation_elasticity by team, ordered by team median."""
    sub = df.dropna(subset=["rotation_elasticity"]).copy()
    if sub.empty:
        if logger:
            logger.warning("No rotation_elasticity data; skipping team boxplot.")
        return

    # Order teams by median elasticity for readability
    med = sub.groupby("team_id")["rotation_elasticity"].median().sort_values()
    ordered_teams = med.index.tolist()
    sub["team_id"] = pd.Categorical(sub["team_id"], categories=ordered_teams, ordered=True)

    plt.figure(figsize=(12, 6))
    sub.boxplot(column="rotation_elasticity", by="team_id")
    plt.xticks(rotation=60, ha="right")
    plt.ylabel("Rotation elasticity (hard - easy)")
    plt.title("Rotation elasticity by team")
    plt.suptitle("")  

    _save(fig_dir, "proxy1_team_boxplot_rotation_elasticity.png", logger=logger)


def plot_rotation_trend_by_season(df: pd.DataFrame, fig_dir: Path, logger=None) -> None:
    """League-wide mean rotation_elasticity by season (start year)."""
    sub = df.dropna(subset=["rotation_elasticity"]).copy()
    if sub.empty:
        if logger:
            logger.warning("No rotation_elasticity data; skipping trend plot.")
        return

    season_mean = (
        sub.groupby("season")["rotation_elasticity"]
        .mean()
        .reset_index()
        .sort_values("season")
    )

    plt.figure(figsize=(7, 4))
    plt.plot(season_mean["season"].astype(int), season_mean["rotation_elasticity"], marker="o")
    plt.xlabel("Season (start year)")
    plt.ylabel("Average rotation elasticity")
    plt.title("League-wide trend in rotation elasticity by season")

    _save(fig_dir, "proxy1_trend_rotation_elasticity_by_season.png", logger=logger)


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create figures for Proxy 1 (rotation) outputs.")
    p.add_argument("--rot-file", type=Path, default=DEFAULT_ROT_FILE,
                   help="Path to proxy1_rotation_elasticity.csv")
    p.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR,
                   help="Directory to write figures into")
    p.add_argument("--bins", type=int, default=20, help="Histogram bins")
    p.add_argument("--top-n", type=int, default=10, help="Top N for bar chart")
    p.add_argument("--dry-run", action="store_true",
                   help="Load + validate only; do not write figures")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = Config.load()
    logger = setup_logger("fig_proxy1_rotation", cfg.logs, "fig_proxy1_rotation.log")
    meta_path = write_run_metadata(cfg.metadata, "fig_proxy1_rotation", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    logger.info("Reading rotation proxy from: %s", args.rot_file)
    logger.info("Writing figures to:         %s", args.fig_dir)
    logger.info("Params: bins=%s top_n=%s dry_run=%s", args.bins, args.top_n, args.dry_run)

    df = load_rotation(args.rot_file)
    logger.info("Loaded rotation proxy: shape=%s cols=%s", df.shape, len(df.columns))
    print(f"Loaded {len(df)} player-seasons from {args.rot_file}")

    if args.dry_run:
        print("✅ dry-run complete | figures NOT written")
        logger.info("Dry-run complete. Figures not written.")
        return

    args.fig_dir.mkdir(parents=True, exist_ok=True)

    plot_hist_rotation(df, args.fig_dir, bins=args.bins, logger=logger)
    plot_top_rotation(df, args.fig_dir, top_n=args.top_n, logger=logger)
    plot_team_boxplot_rotation(df, args.fig_dir, logger=logger)
    plot_rotation_trend_by_season(df, args.fig_dir, logger=logger)

    print(f"✅ wrote figures to: {args.fig_dir}")
    logger.info("Wrote figures to: %s", args.fig_dir)


if __name__ == "__main__":
    main()
