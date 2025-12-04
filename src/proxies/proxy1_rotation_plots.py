# src/analysis/proxy1_rotation_plots.py

from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"


def load_rotation_proxy() -> pd.DataFrame:
    df = pd.read_csv(ROT_FILE)
    df["season"] = df["season"].astype(int)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)
    return df


def plot_hist_rotation_elasticity(df: pd.DataFrame) -> None:
    data = df["rotation_elasticity"].dropna()

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=20, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.xlabel("Rotation elasticity (start_rate_hard - start_rate_easy)")
    plt.ylabel("Number of player-seasons")
    plt.title("Distribution of rotation elasticity")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy1_hist_rotation_elasticity.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_top10_rotation(df: pd.DataFrame) -> None:
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
    # Only keep player-seasons with a valid elasticity
    sub = df.dropna(subset=["rotation_elasticity"]).copy()

    # Order teams by median elasticity (nicely sorted x-axis)
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
    sub = df.dropna(subset=["rotation_elasticity"]).copy()
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



def main() -> None:
    df = load_rotation_proxy()
    print(f"Loaded {len(df)} player-seasons for rotation plots.")

    plot_hist_rotation_elasticity(df)
    plot_top10_rotation(df)
    plot_rotation_trend_by_season(df)   # 👈 call function 2 here


if __name__ == "__main__":
    main()
