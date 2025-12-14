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
# Load data
# ---------------------------------------------------------------------

def load_injury_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

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

    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    for col in ["xpts_per_match_present", "xpts_season_total", "value_gbp_season_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def savefig(fig_dir: Path, fname: str) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_path = fig_dir / fname
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


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


def plot_top10_barh(df: pd.DataFrame, col: str, xlabel: str, title: str, fig_dir: Path, fname: str, top_n: int) -> None:
    sub = df.dropna(subset=[col]).copy()
    if sub.empty:
        print(f"No data for {col}; skipping {fname}.")
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
    savefig(fig_dir, fname)


def plot_scatter(df: pd.DataFrame, x: str, y: str, title: str, fig_dir: Path, fname: str) -> None:
    sub = df.dropna(subset=[x, y]).copy()
    if sub.empty:
        print(f"No data for scatter ({x} vs {y}); skipping {fname}.")
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub[x], sub[y])
    plt.xlabel("Season impact in xPts")
    plt.ylabel("Season impact in £")
    plt.title(title)
    savefig(fig_dir, fname)


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Make plots for Proxy 2 (injury DiD) outputs.")
    p.add_argument("--injury-file", type=str, default=str(INJURY_FILE_DEFAULT), help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--fig-dir", type=str, default=str(FIG_DIR_DEFAULT), help="Directory to write figures into")
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
    )

    plot_hist(
        df,
        col="xpts_season_total",
        xlabel="Season impact in xPts",
        title="Distribution of season-level injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_hist_xpts_season_total.png",
        bins=args.bins,
    )

    plot_top10_barh(
        df,
        col="xpts_season_total",
        xlabel="Season impact in xPts",
        title=f"Top {args.top_n} player-seasons by injury impact (xPts)",
        fig_dir=fig_dir,
        fname="proxy2_top10_xpts_season.png",
        top_n=args.top_n,
    )

    plot_top10_barh(
        df,
        col="value_gbp_season_total",
        xlabel="Season impact in £ (expected)",
        title=f"Top {args.top_n} player-seasons by injury impact (£)",
        fig_dir=fig_dir,
        fname="proxy2_top10_value_gbp.png",
        top_n=args.top_n,
    )

    plot_scatter(
        df,
        x="xpts_season_total",
        y="value_gbp_season_total",
        title="Relationship between points and monetary impact",
        fig_dir=fig_dir,
        fname="proxy2_scatter_xpts_vs_gbp.png",
    )

    print(f"✅ wrote figures to: {fig_dir}")


if __name__ == "__main__":
    main()
