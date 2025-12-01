# src/analysis/proxy2_injury_plots.py

from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# This is the “final named” injury proxy we created
INJURY_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

def load_injury_data() -> pd.DataFrame:
    df = pd.read_csv(INJURY_FILE)

    # Ensure expected columns exist (some may come from earlier scripts)
    # We'll be forgiving and just fill missing ones with NaN if needed.
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

    # Basic types
    df["season"] = df["season"].astype(int)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)

    return df


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def plot_hist_xpts_per_match(df: pd.DataFrame) -> None:
    data = df["xpts_per_match_present"].dropna()

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=20, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.xlabel("xPts per match when present")
    plt.ylabel("Number of player-seasons")
    plt.title("Distribution of injury impact per match (xPts)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_hist_xpts_per_match.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_hist_xpts_season_total(df: pd.DataFrame) -> None:
    data = df["xpts_season_total"].dropna()

    plt.figure(figsize=(8, 5))
    plt.hist(data, bins=20, edgecolor="black")
    plt.axvline(0, linestyle="--")
    plt.xlabel("Season impact in xPts")
    plt.ylabel("Number of player-seasons")
    plt.title("Distribution of season-level injury impact (xPts)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_hist_xpts_season_total.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_top10_xpts_season(df: pd.DataFrame) -> None:
    # Top 10 positive impacts
    top = (
        df.dropna(subset=["xpts_season_total"])
          .sort_values("xpts_season_total", ascending=False)
          .head(10)
    )

    if top.empty:
        print("No data for xpts_season_total; skipping top-10 xPts plot.")
        return

    labels = [
        f"{row.player_name} ({row.team_id} {row.season})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["xpts_season_total"][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Season impact in xPts")
    plt.title("Top 10 player-seasons by injury impact (xPts)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_top10_xpts_season.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_top10_value_gbp(df: pd.DataFrame) -> None:
    # Top 10 highest £ impact
    top = (
        df.dropna(subset=["value_gbp_season_total"])
          .sort_values("value_gbp_season_total", ascending=False)
          .head(10)
    )

    if top.empty:
        print("No data for value_gbp_season_total; skipping top-10 £ plot.")
        return

    labels = [
        f"{row.player_name} ({row.team_id} {row.season})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["value_gbp_season_total"][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Season impact in £ (expected)")
    plt.title("Top 10 player-seasons by injury impact (£)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_top10_value_gbp.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_scatter_points_vs_gbp(df: pd.DataFrame) -> None:
    sub = df.dropna(subset=["xpts_season_total", "value_gbp_season_total"])
    if sub.empty:
        print("No data for scatter; skipping.")
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["xpts_season_total"], sub["value_gbp_season_total"])
    plt.xlabel("Season impact in xPts")
    plt.ylabel("Season impact in £")
    plt.title("Relationship between points and monetary impact")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_scatter_xpts_vs_gbp.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    df = load_injury_data()
    print(f"Loaded {len(df)} player-seasons for plotting.")

    plot_hist_xpts_per_match(df)
    plot_hist_xpts_season_total(df)
    plot_top10_xpts_season(df)
    plot_top10_value_gbp(df)
    plot_scatter_points_vs_gbp(df)


if __name__ == "__main__":
    main()
