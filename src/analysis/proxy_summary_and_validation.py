from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------

def load_rotation(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Rotation proxy not found: {path}")

    df = pd.read_csv(path)

    required = {"player_id", "player_name", "team_id", "season", "rotation_elasticity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Rotation file is missing columns: {sorted(missing)}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["team_id"] = df["team_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")
    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")

    return df


def load_injury(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Injury proxy not found: {path}")

    df = pd.read_csv(path)

    required = {"player_id", "player_name", "team_id", "season"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Injury file is missing columns: {sorted(missing)}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["team_id"] = df["team_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")

    # Prefer these if present
    for c in ["xpts_season_total", "xpts_per_match_present", "n_unavail"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ---------------------------------------------------------------------
# 1) Summary tables
# ---------------------------------------------------------------------

def make_summary_tables(rot: pd.DataFrame, inj: pd.DataFrame, out_dir: Path, logger=None) -> None:
    rot_clean = rot.dropna(subset=["season", "team_id"]).copy()
    inj_clean = inj.dropna(subset=["season", "team_id"]).copy()

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

    # Injury summary prefers xpts_season_total if available
    x_col = "xpts_season_total" if "xpts_season_total" in inj_clean.columns else None
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
            "mean_xpts_season_total": [inj_clean[x_col].mean() if x_col else np.nan],
            "sd_xpts_season_total": [inj_clean[x_col].std() if x_col else np.nan],
        }
    )

    rot_out = out_dir / "summary_rotation_proxy.csv"
    inj_out = out_dir / "summary_injury_proxy.csv"

    rot_summary.to_csv(rot_out, index=False)
    inj_summary.to_csv(inj_out, index=False)

    if logger:
        logger.info("Wrote summary tables: %s and %s", rot_out, inj_out)

    print("Rotation proxy summary:\n", rot_summary)
    print("\nInjury proxy summary:\n", inj_summary)


# ---------------------------------------------------------------------
# 2) Validation: rotation vs injury/player value
# ---------------------------------------------------------------------

def merge_rotation_injury(rot: pd.DataFrame, inj: pd.DataFrame, logger=None) -> pd.DataFrame:
    merged = rot.merge(
        inj,
        on=["player_id", "team_id", "season"],
        how="inner",
        suffixes=("_rot", "_inj"),
    )
    if logger:
        logger.info("Merged proxies on player_id/team_id/season: rows=%d", len(merged))
    return merged


def validation_analysis(
    merged: pd.DataFrame,
    out_dir: Path,
    fig_dir: Path,
    y_col: str = "xpts_season_total",
    logger=None,
) -> None:
    if merged.empty:
        print("⚠️ No merged rows for validation – cannot run correlation/regression.")
        return

    if "rotation_elasticity" not in merged.columns:
        print("⚠️ rotation_elasticity missing in merged data.")
        return

    if y_col not in merged.columns:
        print(f"⚠️ '{y_col}' missing in merged data. Available: {list(merged.columns)}")
        return

    sub = merged.dropna(subset=["rotation_elasticity", y_col]).copy()
    if sub.empty:
        print(f"⚠️ No rows with both rotation_elasticity and {y_col}.")
        return

    # Correlation
    corr = sub["rotation_elasticity"].corr(sub[y_col])
    print(f"\nCorrelation(rotation_elasticity, {y_col}) = {corr:.3f}")

    # OLS: y ~ rotation_elasticity
    X = sm.add_constant(sub[["rotation_elasticity"]])
    y = sub[y_col]

    if sub["rotation_elasticity"].std() == 0:
        print("⚠️ rotation_elasticity has zero variance; regression not meaningful.")
        return

    model = sm.OLS(y, X).fit(cov_type="HC1")  # robust SE

    txt_path = out_dir / "proxy_validation_rotation_vs_injury.txt"
    with open(txt_path, "w") as f:
        f.write("Validation: rotation proxy vs injury/player-value proxy\n")
        f.write(f"Outcome column: {y_col}\n")
        f.write(f"Number of merged player-seasons: {len(sub)}\n")
        f.write(f"Correlation: {corr:.3f}\n\n")
        f.write(model.summary().as_text())

    if logger:
        logger.info("Wrote validation regression summary: %s", txt_path)

    # Scatter + fitted line
    plt.figure(figsize=(7, 5))
    plt.scatter(sub["rotation_elasticity"], sub[y_col], alpha=0.4, edgecolor="none")

    m, b = np.polyfit(sub["rotation_elasticity"], sub[y_col], deg=1)
    xs = np.linspace(sub["rotation_elasticity"].min(), sub["rotation_elasticity"].max(), 100)
    plt.plot(xs, m * xs + b, linestyle="--")

    plt.xlabel("Rotation elasticity (hard − easy)")
    plt.ylabel(y_col)
    plt.title("Rotation proxy vs injury/player-value proxy")
    plt.tight_layout()

    fig_path = fig_dir / "proxy_validation_rotation_vs_injury_scatter.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()

    if logger:
        logger.info("Wrote validation scatter: %s", fig_path)

    print(f"Saved validation summary to {txt_path}")
    print(f"Saved validation scatter plot to {fig_path}")


# ---------------------------------------------------------------------
# 3) Club-level totals
# ---------------------------------------------------------------------

def plot_club_injury_totals(inj: pd.DataFrame, fig_dir: Path, logger=None) -> None:
    """
    Preferred interpretation:
      xpts_lost_to_injury = xpts_per_match_present * n_unavail

    Fallback:
      sum xpts_season_total (NOT strictly "lost to injuries" — more like season value)
    """
    sub = inj.copy()

    if "xpts_per_match_present" in sub.columns and "n_unavail" in sub.columns:
        sub = sub.dropna(subset=["xpts_per_match_present", "n_unavail"])
        sub["xpts_lost"] = sub["xpts_per_match_present"] * sub["n_unavail"]
        value_col = "xpts_lost"
        xlab = "Total xPts lost due to unavailable matches"
        title = "Total expected points lost to injuries by club"
    elif "xpts_season_total" in sub.columns:
        sub = sub.dropna(subset=["xpts_season_total"])
        value_col = "xpts_season_total"
        xlab = "Total xPts season value (proxy; not strictly 'lost')"
        title = "Club totals from injury proxy (season value)"
    else:
        print("⚠️ No suitable injury value column found for club totals plot.")
        return

    club_totals = sub.groupby("team_id")[value_col].sum().sort_values(ascending=False)

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(club_totals)), club_totals.values[::-1])
    plt.yticks(range(len(club_totals)), club_totals.index[::-1])
    plt.xlabel(xlab)
    plt.title(title)
    plt.tight_layout()

    fig_path = fig_dir / "proxy2_total_injury_xpts_by_club.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()

    if logger:
        logger.info("Wrote club totals figure: %s", fig_path)

    print(f"Saved club-level chart to {fig_path}")


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def main() -> None:
    cfg = Config.load()
    logger = setup_logger("proxy_summary_and_validation", cfg.logs, "proxy_summary_and_validation.log")
    meta_path = write_run_metadata(cfg.metadata, "proxy_summary_and_validation")
    logger.info("Run metadata saved to: %s", meta_path)

    default_rot = cfg.project_root / "results" / "proxy1_rotation_elasticity.csv" if hasattr(cfg, "project_root") else Path("results/proxy1_rotation_elasticity.csv")
    default_inj = cfg.project_root / "results" / "proxy2_injury_final_named.csv" if hasattr(cfg, "project_root") else Path("results/proxy2_injury_final_named.csv")
    default_out = cfg.project_root / "results" if hasattr(cfg, "project_root") else Path("results")
    default_fig = default_out / "figures"

    p = argparse.ArgumentParser(description="Summarise proxies and run basic validation checks.")
    p.add_argument("--rot-file", type=Path, default=default_rot, help="Path to proxy1_rotation_elasticity.csv")
    p.add_argument("--inj-file", type=Path, default=default_inj, help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--out-dir", type=Path, default=default_out, help="Output directory (summaries + txt)")
    p.add_argument("--fig-dir", type=Path, default=default_fig, help="Figure output directory")
    p.add_argument("--y-col", type=str, default="xpts_season_total", help="Outcome column for validation regression")
    p.add_argument("--dry-run", action="store_true", help="Run compute/validation but do not write outputs")
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.fig_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Reading rotation proxy: %s", args.rot_file)
    logger.info("Reading injury proxy:   %s", args.inj_file)
    logger.info("Writing out-dir:        %s", args.out_dir)
    logger.info("Writing fig-dir:        %s", args.fig_dir)
    logger.info("Validation y-col:       %s", args.y_col)

    rot = load_rotation(args.rot_file)
    inj = load_injury(args.inj_file)

    logger.info("Rotation proxy loaded: rows=%d teams=%d", len(rot), rot["team_id"].nunique())
    logger.info("Injury proxy loaded:   rows=%d teams=%d", len(inj), inj["team_id"].nunique())

    print("Loading proxies ...")
    print(f"Rotation proxy: {len(rot)} player-seasons, {rot['team_id'].nunique()} teams.")
    print(f"Injury proxy:   {len(inj)} player-seasons, {inj['team_id'].nunique()} teams.")

    print("\n1) Making summary tables ...")
    if not args.dry_run:
        make_summary_tables(rot, inj, out_dir=args.out_dir, logger=logger)
    else:
        print("✅ dry-run: summary tables would be written.")

    print("\n2) Validating rotation proxy vs injury/player value ...")
    merged = merge_rotation_injury(rot, inj, logger=logger)
    print(f"Number of player-seasons in merged set: {len(merged)}")
    if not args.dry_run:
        validation_analysis(merged, out_dir=args.out_dir, fig_dir=args.fig_dir, y_col=args.y_col, logger=logger)
    else:
        print("✅ dry-run: validation outputs would be written.")

    print("\n3) Plotting club-level totals ...")
    if not args.dry_run:
        plot_club_injury_totals(inj, fig_dir=args.fig_dir, logger=logger)
    else:
        print("✅ dry-run: club totals figure would be written.")

    print("\n✅ Finished summary, validation, and club plots.")


if __name__ == "__main__":
    main()
