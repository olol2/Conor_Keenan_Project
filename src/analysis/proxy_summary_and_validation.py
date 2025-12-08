# src/analysis/proxy_summary_and_validation.py

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

ROT_FILE = RESULTS_DIR / "proxy1_rotation_elasticity.csv"
INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

def load_rotation() -> pd.DataFrame:
    df = pd.read_csv(ROT_FILE)

    required = {
        "player_id",
        "player_name",
        "team_id",
        "season",
        "rotation_elasticity",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Rotation file is missing columns: {missing}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["team_id"] = df["team_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")

    return df


def load_injury() -> pd.DataFrame:
    df = pd.read_csv(INJ_FILE)

    required = {
        "player_id",
        "player_name",
        "team_id",
        "season",
        "xpts_season_total",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Injury file is missing columns: {missing}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["team_id"] = df["team_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------------------
# 1) Summary tables
# ---------------------------------------------------------------------

def make_summary_tables(rot: pd.DataFrame, inj: pd.DataFrame) -> None:
    # Drop rows with missing season/team for summaries
    rot_clean = rot.dropna(subset=["season", "team_id"]).copy()
    inj_clean = inj.dropna(subset=["season", "team_id"]).copy()

    # Rotation proxy summary
    rot_summary = pd.DataFrame(
        {
            "n_player_seasons": [len(rot_clean)],
            "n_players": [
                rot_clean[["player_id", "player_name"]]
                .dropna(subset=["player_id"])
                .drop_duplicates()
                .shape[0]
            ],
            "n_teams": [rot_clean["team_id"].nunique()],
            "season_min": [rot_clean["season"].min()],
            "season_max": [rot_clean["season"].max()],
            "mean_rotation_elasticity": [rot_clean["rotation_elasticity"].mean()],
            "sd_rotation_elasticity": [rot_clean["rotation_elasticity"].std()],
        }
    )

    # Injury proxy summary
    inj_summary = pd.DataFrame(
        {
            "n_player_seasons": [len(inj_clean)],
            "n_players": [
                inj_clean[["player_id", "player_name"]]
                .dropna(subset=["player_id"])
                .drop_duplicates()
                .shape[0]
            ],
            "n_teams": [inj_clean["team_id"].nunique()],
            "season_min": [inj_clean["season"].min()],
            "season_max": [inj_clean["season"].max()],
            "mean_xpts_season_total": [inj_clean["xpts_season_total"].mean()],
            "sd_xpts_season_total": [inj_clean["xpts_season_total"].std()],
        }
    )

    rot_out = RESULTS_DIR / "summary_rotation_proxy.csv"
    inj_out = RESULTS_DIR / "summary_injury_proxy.csv"

    rot_summary.to_csv(rot_out, index=False)
    inj_summary.to_csv(inj_out, index=False)

    print("Rotation proxy summary:\n", rot_summary)
    print("\nInjury proxy summary:\n", inj_summary)
    print(f"\nSaved rotation summary to {rot_out}")
    print(f"Saved injury summary to {inj_out}")


# ---------------------------------------------------------------------
# 2) Validation: rotation vs injury impact
# ---------------------------------------------------------------------

def merge_rotation_injury(rot: pd.DataFrame, inj: pd.DataFrame) -> pd.DataFrame:
    """
    Merge proxies at player_id–team–season level.
    With the current pipeline both proxies use the Understat numeric ID
    and canonical short team names, so a simple inner join is enough.
    """
    merged = rot.merge(
        inj,
        on=["player_id", "team_id", "season"],
        how="inner",
        suffixes=("_rot", "_inj"),
    )
    print(f"Merge on player_id/team/season -> {len(merged)} rows")
    return merged


def validation_analysis(merged: pd.DataFrame) -> None:
    if merged.empty:
        print("⚠️ No merged rows for validation – cannot run correlation/regression.")
        return

    # Keep rows with both variables present
    if "rotation_elasticity" not in merged.columns or "xpts_season_total" not in merged.columns:
        print("⚠️ Required columns missing in merged data; skipping validation.")
        return

    sub = merged.dropna(subset=["rotation_elasticity", "xpts_season_total"])
    if sub.empty:
        print("⚠️ No rows with both rotation_elasticity and xpts_season_total.")
        return

    corr = sub["rotation_elasticity"].corr(sub["xpts_season_total"])
    print(f"\nCorrelation(rotation_elasticity, xpts_season_total) = {corr:.3f}")

    # Simple OLS: xpts_season_total ~ rotation_elasticity
    X = sub[["rotation_elasticity"]].copy()
    y = sub["xpts_season_total"].copy()

    if len(X) == 0:
        print("⚠️ No observations left after filtering – skipping regression.")
        return

    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()

    txt_path = RESULTS_DIR / "proxy_validation_rotation_vs_injury.txt"
    with open(txt_path, "w") as f:
        f.write("Validation of rotation proxy vs injury impact\n")
        f.write(f"Number of merged player-seasons: {len(sub)}\n")
        f.write(f"Correlation: {corr:.3f}\n\n")
        f.write(model.summary().as_text())

    print(f"Saved validation summary to {txt_path}")

    # Scatter plot with regression line
    plt.figure(figsize=(7, 5))
    plt.scatter(
        sub["rotation_elasticity"],
        sub["xpts_season_total"],
        alpha=0.4,
        edgecolor="none",
    )

    # Regression line
    m, b = np.polyfit(
        sub["rotation_elasticity"],
        sub["xpts_season_total"],
        deg=1,
    )
    xs = np.linspace(
        sub["rotation_elasticity"].min(),
        sub["rotation_elasticity"].max(),
        100,
    )
    plt.plot(xs, m * xs + b, linestyle="--")

    plt.xlabel("Rotation elasticity (hard − easy)")
    plt.ylabel("Season injury impact in xPts")
    plt.title("Rotation importance vs injury impact")
    plt.tight_layout()

    fig_path = FIG_DIR / "proxy_validation_rotation_vs_injury_scatter.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"Saved validation scatter plot to {fig_path}")


# ---------------------------------------------------------------------
# 3) Club-level bar chart of total injury impact
# ---------------------------------------------------------------------

def plot_club_injury_totals(inj: pd.DataFrame) -> None:
    """
    Sum xPts lost to injury over all seasons for each team.
    Positive values = more points lost.
    """
    if "xpts_season_total" not in inj.columns:
        print("⚠️ 'xpts_season_total' not in injury data; skipping club totals plot.")
        return

    sub = inj.dropna(subset=["xpts_season_total"]).copy()

    club_totals = (
        sub.groupby("team_id")["xpts_season_total"]
        .sum()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(club_totals)), club_totals.values[::-1])
    plt.yticks(range(len(club_totals)), club_totals.index[::-1])
    plt.xlabel("Total xPts lost to injuries (2019–2024)")
    plt.title("Total expected points lost to injuries by club")
    plt.tight_layout()

    fig_path = FIG_DIR / "proxy2_total_injury_xpts_by_club.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"Saved club-level injury bar chart to {fig_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("Loading proxies ...")
    rot = load_rotation()
    inj = load_injury()
    print(f"Rotation proxy: {len(rot)} player-seasons, {rot['team_id'].nunique()} teams.")
    print(f"Injury proxy:   {len(inj)} player-seasons, {inj['team_id'].nunique()} teams.")

    print("\n1) Making summary tables ...")
    make_summary_tables(rot, inj)

    print("\n2) Validating rotation proxy vs injury impact ...")
    merged = merge_rotation_injury(rot, inj)
    print(f"Number of player-seasons in merged set: {len(merged)}")
    validation_analysis(merged)

    print("\n3) Plotting club-level injury totals ...")
    plot_club_injury_totals(inj)

    print("\n✅ Finished summary, validation, and club plots.")


if __name__ == "__main__":
    main()
