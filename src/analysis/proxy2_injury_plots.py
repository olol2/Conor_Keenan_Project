"""
Makes diagnostic/summary plots for Proxy 2 (injury DiD interpretation).

Input:
  results/proxy2_injury_final_named.csv

Outputs:
  - proxy2_hist_xpts_per_match.png
  - proxy2_hist_xpts_season_total.png
  - proxy2_top10_xpts_season.png
  - proxy2_top10_value_gbp.png
  - proxy2_scatter_xpts_vs_gbp.png

Column compatibility:
- Accepts both "new" and "old" naming conventions:
    xpts_season_total        -> inj_xpts
    value_gbp_season_total   -> inj_gbp
- Also supports using xpts_per_match_present if present.
"""

from __future__ import annotations
from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR_DEFAULT = RESULTS_DIR / "figures"
INJURY_FILE_DEFAULT = RESULTS_DIR / "proxy2_injury_final_named.csv"


# ---------------------------------------------------------------------
# Load + normalize schema
# ---------------------------------------------------------------------

def load_injury_data(path: Path) -> pd.DataFrame:
    """
    Load injury proxy and create a consistent set of plotting columns.

    Normalized columns produced (if possible):
      - inj_xpts: season injury impact in xPts
      - inj_gbp : season injury impact in GBP
      - xpts_per_match_present: xPts impact per match when present (if provided)
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Normalize key labels
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df = df.rename(columns={"xpts_season_total": "inj_xpts"})
    if "inj_gbp" not in df.columns and "value_gbp_season_total" in df.columns:
        df = df.rename(columns={"value_gbp_season_total": "inj_gbp"})

    # Ensure expected columns exist (so plotting code can skip gracefully)
    expected_cols = [
        "player_name",
        "team_id",
        "season",
        "xpts_per_match_present",
        "inj_xpts",
        "inj_gbp",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # Basic cleanup / typing
    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    for col in ["xpts_per_match_present", "inj_xpts", "inj_gbp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _fmt_season(x) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return str(int(x))
    except Exception:
        return "NA"


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def savefig(fig_dir: Path, fname: str) -> Path:
    """Save current matplotlib figure to fig_dir/fname with consistent styling."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_path = fig_dir / fname
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")
    return out_path


def plot_hist(df: pd.DataFrame, col: str, xlabel: str, title: str, fig_dir: Path, fname: str, bins: int) -> None:
    data = df[col].dropna()
    if data.empty:
        print(f"No data for {col}; skipping {fname}.")
        return

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=bins, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.xlabel(xlabel)
    plt.ylabel("Number of player-seasons")
    plt.title(title)
    savefig(fig_dir, fname)


def plot_top_barh(
    df: pd.DataFrame,
    col: str,
    xlabel: str,
    title: str,
    fig_dir: Path,
    fname: str,
    top_n: int,
) -> None:
    sub = df.dropna(subset=[col]).copy()
    if sub.empty:
        print(f"No data for {col}; skipping {fname}.")
        return

    top = sub.sort_values(col, ascending=False).head(top_n)

    labels = [
        f"{row.player_name} ({row.team_id} {_fmt_season(row.season)})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top[col].iloc[::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel(xlabel)
    plt.title(title)
    savefig(fig_dir, fname)


def plot_scatter(df: pd.DataFrame, x: str, y: str, title: str, fig_dir: Path, fname: str) -> None:
    sub = df.dropna(subset=[x, y]).copy()
    if sub.empty:
        print(f"No data for scatter ({x} vs {y}); skipping {fname}.")
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub[x], sub[y])
    plt.axvline(0, linestyle="--")
    plt.axhline(0, linestyle="--")
    plt.xlabel("Season impact in xPts")
    plt.ylabel("Season impact in £")
    plt.title(title)
    savefig(fig_dir, fname)


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Make plots for Proxy 2 (injury DiD) outputs.")
    p.add_argument("--injury-file", type=str, default=str(INJURY_FILE_DEFAULT),
                   help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--fig-dir", type=str, default=str(FIG_DIR_DEFAULT),
                   help="Directory to write figures into")
    p.add_argument("--bins", type=int, default=20, help="Histogram bins")
    p.add_argument("--top-n", type=int, default=10, help="Top N for bar charts")
    p.add_argument("--dry-run", action="store_true", help="Load + validate only; do not write figures")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    injury_file = Path(args.injury_file)
    fig_dir = Path(args.fig_dir)

    df = load_injury_data(injury_file)
    print(f"Loaded {len(df)} player-seasons for plotting from {injury_file}")

    if args.dry_run:
        # dry-run should not create directories or write files
        print("✅ dry-run complete | figures NOT written")
        return

    # 1) Histogram: per-match impact (if available)
    plot_hist(
        df,
        col="xpts_per_match_present",
        xlabel="xPts per match when present",
        title="Distribution of injury impact per match (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_hist_xpts_per_match.png",
        bins=args.bins,
    )

    # 2) Histogram: season xPts impact
    plot_hist(
        df,
        col="inj_xpts",
        xlabel="Season impact in xPts",
        title="Distribution of season-level injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_hist_xpts_season_total.png",
        bins=args.bins,
    )

    # 3) Top-N player-seasons by xPts impact
    plot_top_barh(
        df,
        col="inj_xpts",
        xlabel="Season impact in xPts",
        title=f"Top {args.top_n} player-seasons by injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_top10_xpts_season.png",
        top_n=args.top_n,
    )

    # 4) Top-N player-seasons by GBP impact (if available)
    plot_top_barh(
        df,
        col="inj_gbp",
        xlabel="Season impact in £ (expected)",
        title=f"Top {args.top_n} player-seasons by injury impact (£)",
        fig_dir=fig_dir,
        fname="proxy2_top10_value_gbp.png",
        top_n=args.top_n,
    )

    # 5) Scatter: xPts vs £ (if both exist)
    plot_scatter(
        df,
        x="inj_xpts",
        y="inj_gbp",
        title="Relationship between points and monetary impact",
        fig_dir=fig_dir,
        fname="proxy2_scatter_xpts_vs_gbp.png",
    )

    print(f"✅ wrote figures to: {fig_dir}")


if __name__ == "__main__":
    main()
