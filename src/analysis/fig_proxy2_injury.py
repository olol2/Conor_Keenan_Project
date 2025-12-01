# src/analysis/fig_proxy2_injury.py

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"


def load_injury() -> pd.DataFrame:
    df = pd.read_csv(INJ_FILE)

    # Standardise column names if needed
    # (adjust if your file uses slightly different names)
    rename_map = {}
    if "xpts_season_total" in df.columns:
        rename_map["xpts_season_total"] = "inj_xpts"
    if "value_gbp_season_total" in df.columns:
        rename_map["value_gbp_season_total"] = "inj_gbp"

    df = df.rename(columns=rename_map)

    df["season"] = df["season"].astype(int)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)

    return df


def plot_top10_injury_players(df: pd.DataFrame) -> None:
    if "inj_xpts" not in df.columns:
        print("Column 'inj_xpts' not found; skipping top-10 injury plot.")
        return

    top = (
        df.dropna(subset=["inj_xpts"])
        .sort_values("inj_xpts", ascending=False)
        .head(10)
    )
    if top.empty:
        print("No injury impact data; skipping top-10 player plot.")
        return

    labels = [
        f"{row.player_name} ({row.team_id} {row.season})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["inj_xpts"][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Season injury impact in xPts")
    plt.title("Top 10 player-seasons by injury impact (xPts)")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_top10_injury_xpts.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def plot_club_injury_bill(df: pd.DataFrame) -> None:
    """
    Sum injury impact per team-season and plot top 10 club-seasons.
    Uses inj_gbp if available, else inj_xpts.
    """
    metric = "inj_gbp" if "inj_gbp" in df.columns else "inj_xpts"
    if metric not in df.columns:
        print("No 'inj_gbp' or 'inj_xpts' column; skipping club injury bill plot.")
        return

    club = (
        df.groupby(["team_id", "season"], as_index=False)[metric]
        .sum()
    )

    top = club.sort_values(metric, ascending=False).head(10)
    if top.empty:
        print("No club injury data; skipping club injury bill plot.")
        return

    labels = [f"{row.team_id} {row.season}" for _, row in top.iterrows()]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top[metric][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    ylabel = "Total injury cost in £" if metric == "inj_gbp" else "Total injury impact in xPts"
    plt.xlabel(ylabel)
    plt.title("Top 10 club-seasons by total injury cost")
    plt.tight_layout()

    out_path = FIG_DIR / "proxy2_club_injury_bill.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved {out_path}")


def main() -> None:
    df = load_injury()
    print(f"Loaded {len(df)} player-seasons from {INJ_FILE}")
    plot_top10_injury_players(df)
    plot_club_injury_bill(df)


if __name__ == "__main__":
    main()
