# src/analysis/fig_proxy1_rotation.py

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

def load_rotation() -> pd.DataFrame:
    df = pd.read_csv(ROT_FILE)
    df["season"] = df["season"].astype(int)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)
    return df


# ---------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------

def plot_hist_rotation(df: pd.DataFrame) -> None:
    """Histogram of rotation elasticity with mean + zero line."""
    data = df["rotation_elasticity"].dropna()

    if data.empty:
        print("No rotation_elasticity data; skipping histogram.")
        return

    mean_val = data.mean()

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=20, edgecolor="black")
    # reference lines
    plt.axvline(0, linestyle="--")
    plt.axvline(mean_val, linestyle=":", linewidth=2)

    plt.xlabel("Rotation elasticity (start_rate_hard - start_rate_easy)")
    plt.ylabel("Number of player-seasons")
    plt.title("Distribution of rotation elasticity")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy1_hist_rotation_elasticity.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_top10_rotation(df: pd.DataFrame) -> None:
    """Top 10 player-seasons by rotation elasticity."""
    top = (
        df.dropna(subset=["rotation_elasticity"])
          .sort_values("rotation_elasticity", ascending=False)
          .head(10)
    )
    if top.empty:
        print("No data for rotation_elasticity; skipping top-10 plot.")
        return

    labels = [
        f"{row.player_name} ({row.team_id} {row.season})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["rotation_elasticity"][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Rotation elasticity (hard - easy)")
    plt.title("Top 10 player-seasons by rotation elasticity")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy1_top10_rotation_elasticity.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_team_boxplot_rotation(df: pd.DataFrame) -> None:
    """Boxplot of rotation elasticity by team."""
    sub = df.dropna(subset=["rotation_elasticity"]).copy()
    if sub.empty:
        print("No rotation_elasticity data; skipping team boxplot.")
        return

    # Order teams by median elasticity
    med = sub.groupby("team_id")["rotation_elasticity"].median().sort_values()
    ordered_teams = med.index.tolist()
    sub["team_id"] = pd.Categorical(sub["team_id"], categories=ordered_teams, ordered=True)

    plt.figure(figsize=(12, 6))
    sub.boxplot(column="rotation_elasticity", by="team_id")
    plt.xticks(rotation=60, ha="right")
    plt.ylabel("Rotation elasticity (hard - easy)")
    plt.title("Rotation elasticity by team")
    plt.suptitle("")  # remove pandas’ automatic super title
    plt.tight_layout()

    out_path = FIG_DIR / "proxy1_team_boxplot_rotation_elasticity.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_rotation_trend_by_season(df: pd.DataFrame) -> None:
    """League-wide mean rotation elasticity by season."""
    sub = df.dropna(subset=["rotation_elasticity"]).copy()
    if sub.empty:
        print("No rotation_elasticity data; skipping trend plot.")
        return

    season_mean = (
        sub.groupby("season")["rotation_elasticity"]
           .mean()
           .reset_index()
    )

    plt.figure(figsize=(7, 4))
    plt.plot(season_mean["season"], season_mean["rotation_elasticity"], marker="o")
    plt.xlabel("Season (first year)")
    plt.ylabel("Average rotation elasticity")
    plt.title("League-wide trend in rotation elasticity by season")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy1_trend_rotation_elasticity_by_season.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    df = load_rotation()
    print(f"Loaded {len(df)} player-seasons from {ROT_FILE}")

    plot_hist_rotation(df)
    plot_top10_rotation(df)
    plot_team_boxplot_rotation(df)
    plot_rotation_trend_by_season(df)


if __name__ == "__main__":
    main()
