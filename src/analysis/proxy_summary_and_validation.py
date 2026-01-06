"""
Summarises Proxy 1 and Proxy 2 outputs and runs basic validation checks.

Inputs:
  - results/proxy1_rotation_elasticity.csv
  - results/proxy2_injury_final_named.csv

Outputs:
  - summary_rotation_proxy.csv
  - summary_injury_proxy.csv
  - proxy_validation_rotation_vs_injury.txt
  - figures/proxy_validation_rotation_vs_injury_scatter.png
  - figures/proxy2_total_injury_xpts_by_club.png

Key robustness features:
- Injury file sometimes has 'understat_player_id' instead of 'player_id'.
  -> standardise it to 'player_id' on load.
- Avoids relying on cfg.project_root. Uses cfg.processed to infer root..
"""

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
from src.utils.io import atomic_write_csv

# ---------------------------------------------------------------------
# Paths helpers (do not rely on cfg.project_root)
# ---------------------------------------------------------------------
def infer_project_root(cfg: Config) -> Path:
    if getattr(cfg, "processed", None) is not None:
        return cfg.processed.parent.parent
    return Path(__file__).resolve().parents[2]


def infer_results_dir(cfg: Config) -> Path:
    root = infer_project_root(cfg)
    return getattr(cfg, "results", root / "results")


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------
def load_rotation(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Rotation proxy not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    required = {"player_id", "player_name", "team_id", "season", "rotation_elasticity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Rotation file is missing columns: {sorted(missing)}")

    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")
    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")

    # Optional columns (keep if present)
    for c in ["n_matches", "n_starts", "start_rate_all", "start_rate_hard", "start_rate_easy"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def load_injury(path: Path) -> pd.DataFrame:
    """
    Load injury proxy and standardise to these key columns where possible:
      - player_id (Int64)  [may come from 'understat_player_id']
      - player_name (str)
      - team_id (str)
      - season (Int64)

    Also keeps numeric metrics if present (xpts_season_total, xpts_per_match_present, n_unavail, etc.)
    """
    if not path.exists():
        raise FileNotFoundError(f"Injury proxy not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # --- Standardise player id column name ---
    # Current proxy2_injury_summary output writes 'understat_player_id', not 'player_id'
    if "player_id" not in df.columns and "understat_player_id" in df.columns:
        df = df.rename(columns={"understat_player_id": "player_id"})

    required_min = {"team_id", "season"}
    missing_min = required_min - set(df.columns)
    if missing_min:
        raise ValueError(f"Injury file is missing required columns: {sorted(missing_min)}")

    # player_id is strongly preferred, but allow missing (with warning in summary)
    if "player_id" in df.columns:
        df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")
    else:
        df["player_id"] = pd.Series([pd.NA] * len(df), dtype="Int64")

    if "player_name" in df.columns:
        df["player_name"] = df["player_name"].astype(str).str.strip()
    else:
        df["player_name"] = pd.Series([""] * len(df), dtype="string")

    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    # Prefer unified names
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df["inj_xpts"] = pd.to_numeric(df["xpts_season_total"], errors="coerce")
    if "inj_gbp" not in df.columns and "value_gbp_season_total" in df.columns:
        df["inj_gbp"] = pd.to_numeric(df["value_gbp_season_total"], errors="coerce")

    # Coerce likely numeric fields if present
    for c in [
        "xpts_season_total",
        "xpts_per_match_present",
        "n_unavail",
        "n_matches",
        "inj_xpts",
        "inj_gbp",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ---------------------------------------------------------------------
# 1) Summary tables
# ---------------------------------------------------------------------
def make_summary_tables(rot: pd.DataFrame, inj: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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

    # Injury summary prefers season-level impact if present
    if "inj_xpts" in inj_clean.columns:
        x_col = "inj_xpts"
    elif "xpts_season_total" in inj_clean.columns:
        x_col = "xpts_season_total"
    else:
        x_col = None

    # n_players: prefer numeric player_id; else fallback to player_name count
    if inj_clean["player_id"].notna().any():
        n_players_inj = (
            inj_clean[["player_id", "player_name"]]
            .dropna(subset=["player_id"])
            .drop_duplicates()
            .shape[0]
        )
    else:
        n_players_inj = inj_clean["player_name"].replace("", pd.NA).dropna().nunique()

    inj_summary = pd.DataFrame(
        {
            "n_player_seasons": [len(inj_clean)],
            "n_players": [n_players_inj],
            "n_teams": [inj_clean["team_id"].nunique()],
            "season_min": [inj_clean["season"].min()],
            "season_max": [inj_clean["season"].max()],
            "mean_injury_xpts_season_total": [inj_clean[x_col].mean() if x_col else np.nan],
            "sd_injury_xpts_season_total": [inj_clean[x_col].std() if x_col else np.nan],
            "share_missing_player_id": [float(inj_clean["player_id"].isna().mean()) if len(inj_clean) else np.nan],
        }
    )

    return rot_summary, inj_summary


# ---------------------------------------------------------------------
# 2) Validation: rotation vs injury/player value
# ---------------------------------------------------------------------
def merge_rotation_injury(rot: pd.DataFrame, inj: pd.DataFrame, logger=None) -> pd.DataFrame:
    """
    Merge on player_id/team_id/season.

    Note: injury player_id can be missing for some rows (unmatched Understat IDs).
    Those will naturally drop out of the inner merge.
    """
    before_inj = len(inj)
    inj_ok = inj.dropna(subset=["player_id", "team_id", "season"]).copy()
    dropped = before_inj - len(inj_ok)

    if logger and dropped > 0:
        logger.info("Dropped %d injury rows with missing merge keys before merge.", dropped)

    merged = rot.merge(
        inj_ok,
        on=["player_id", "team_id", "season"],
        how="inner",
        suffixes=("_rot", "_inj"),
    )

    if logger:
        logger.info("Merged proxies on player_id/team_id/season: rows=%d", len(merged))
    return merged


def pick_default_y_col(df: pd.DataFrame, requested: str) -> str:
    if requested:
        return requested

    for c in ["inj_xpts", "xpts_season_total", "value_gbp_season_total", "inj_gbp"]:
        if c in df.columns:
            return c
    # last-resort fallback
    return "xpts_season_total"


def validation_analysis(
    merged: pd.DataFrame,
    out_dir: Path,
    fig_dir: Path,
    y_col: str,
    write_outputs: bool,
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
    if sub["rotation_elasticity"].std(skipna=True) == 0:
        print("⚠️ rotation_elasticity has zero variance; regression not meaningful.")
        return

    X = sm.add_constant(sub[["rotation_elasticity"]])
    y = sub[y_col]
    model = sm.OLS(y, X).fit(cov_type="HC1")  # robust SE

    if write_outputs:
        out_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

        txt_path = out_dir / "proxy_validation_rotation_vs_injury.txt"
        txt_path.write_text(
            "\n".join(
                [
                    "Validation: rotation proxy vs injury/player-value proxy",
                    f"Outcome column: {y_col}",
                    f"Number of merged player-seasons: {len(sub)}",
                    f"Correlation: {corr:.3f}",
                    "",
                    model.summary().as_text(),
                ]
            ),
            encoding="utf-8",
        )
        if logger:
            logger.info("Wrote validation regression summary: %s", txt_path)

        # Scatter + fitted line
        plt.figure(figsize=(7, 5))
        plt.scatter(sub["rotation_elasticity"], sub[y_col], alpha=0.4, edgecolor="none")
        m, b = np.polyfit(sub["rotation_elasticity"], sub[y_col], deg=1)
        xs = np.linspace(sub["rotation_elasticity"].min(), sub["rotation_elasticity"].max(), 100)
        plt.plot(xs, m * xs + b, linestyle="--")

        plt.axvline(0, linestyle="--")
        plt.axhline(0, linestyle="--")
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
    else:
        print("✅ dry-run: regression summary + scatter would be written.")


# ---------------------------------------------------------------------
# 3) Club-level totals
# ---------------------------------------------------------------------
def plot_club_injury_totals(inj: pd.DataFrame, fig_dir: Path, write_outputs: bool, logger=None) -> None:
    """
    Preferred interpretation:
      xpts_lost_to_injury = xpts_per_match_present * n_unavail

    Fallback:
      sum inj_xpts (or xpts_season_total)
    """
    sub = inj.copy()

    if "xpts_per_match_present" in sub.columns and "n_unavail" in sub.columns:
        sub = sub.dropna(subset=["xpts_per_match_present", "n_unavail", "team_id"])
        sub["xpts_lost"] = sub["xpts_per_match_present"] * sub["n_unavail"]
        value_col = "xpts_lost"
        xlab = "Total xPts lost due to unavailable matches"
        title = "Total expected points lost to injuries by club"
    elif "inj_xpts" in sub.columns:
        sub = sub.dropna(subset=["inj_xpts", "team_id"])
        value_col = "inj_xpts"
        xlab = "Total season injury impact in xPts (proxy)"
        title = "Club totals from injury proxy (xPts)"
    elif "xpts_season_total" in sub.columns:
        sub = sub.dropna(subset=["xpts_season_total", "team_id"])
        value_col = "xpts_season_total"
        xlab = "Total xPts season value (proxy)"
        title = "Club totals from injury proxy (season value)"
    else:
        print("⚠️ No suitable injury value column found for club totals plot.")
        return

    club_totals = sub.groupby("team_id")[value_col].sum().sort_values(ascending=False)

    if club_totals.empty:
        print("⚠️ Club totals empty; skipping club plot.")
        return

    if write_outputs:
        fig_dir.mkdir(parents=True, exist_ok=True)

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
    else:
        print("✅ dry-run: club totals figure would be written.")


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------
def parse_args(default_rot: Path, default_inj: Path, default_out: Path, default_fig: Path) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarise proxies and run basic validation checks.")
    p.add_argument("--rot-file", type=Path, default=default_rot, help="Path to proxy1_rotation_elasticity.csv")
    p.add_argument("--inj-file", type=Path, default=default_inj, help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--out-dir", type=Path, default=default_out, help="Output directory (summaries + txt)")
    p.add_argument("--fig-dir", type=Path, default=default_fig, help="Figure output directory")
    p.add_argument("--y-col", type=str, default="", help="Outcome column for validation regression (blank = auto)")
    p.add_argument("--dry-run", action="store_true", help="Run compute/validation but do not write outputs")
    return p.parse_args()


def main() -> None:
    cfg = Config.load()
    logger = setup_logger("proxy_summary_and_validation", cfg.logs, "proxy_summary_and_validation.log")
    meta_path = write_run_metadata(cfg.metadata, "proxy_summary_and_validation")
    logger.info("Run metadata saved to: %s", meta_path)

    results_dir = infer_results_dir(cfg)
    default_rot = results_dir / "proxy1_rotation_elasticity.csv"
    default_inj = results_dir / "proxy2_injury_final_named.csv"
    default_out = results_dir
    default_fig = results_dir / "figures"

    args = parse_args(default_rot, default_inj, default_out, default_fig)

    write_outputs = not bool(args.dry_run)

    logger.info("Reading rotation proxy: %s", args.rot_file)
    logger.info("Reading injury proxy:   %s", args.inj_file)
    logger.info("Writing out-dir:        %s", args.out_dir)
    logger.info("Writing fig-dir:        %s", args.fig_dir)
    logger.info("Dry-run:                %s", args.dry_run)

    rot = load_rotation(args.rot_file)
    inj = load_injury(args.inj_file)

    logger.info("Rotation proxy loaded: rows=%d teams=%d", len(rot), rot["team_id"].nunique())
    logger.info("Injury proxy loaded:   rows=%d teams=%d", len(inj), inj["team_id"].nunique())

    print("Loading proxies ...")
    print(f"Rotation proxy: {len(rot)} player-seasons, {rot['team_id'].nunique()} teams.")
    print(f"Injury proxy:   {len(inj)} player-seasons, {inj['team_id'].nunique()} teams.")
    if "player_id" in inj.columns:
        print(f"Injury proxy missing player_id: {inj['player_id'].isna().mean():.1%}")

    # 1) Summary tables
    print("\n1) Making summary tables ...")
    rot_summary, inj_summary = make_summary_tables(rot, inj)
    print("Rotation proxy summary:\n", rot_summary.to_string(index=False))
    print("\nInjury proxy summary:\n", inj_summary.to_string(index=False))

    if write_outputs:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_csv(rot_summary, args.out_dir / "summary_rotation_proxy.csv", index=False)
        atomic_write_csv(inj_summary, args.out_dir / "summary_injury_proxy.csv", index=False)
        logger.info("Wrote summary tables to %s", args.out_dir)
    else:
        print("✅ dry-run: summary CSVs would be written.")

    # 2) Validation
    print("\n2) Validating rotation proxy vs injury/player value ...")
    merged = merge_rotation_injury(rot, inj, logger=logger)
    print(f"Number of player-seasons in merged set: {len(merged)}")

    y_col = pick_default_y_col(merged, args.y_col.strip())
    print(f"Validation outcome column: {y_col}")

    validation_analysis(
        merged,
        out_dir=args.out_dir,
        fig_dir=args.fig_dir,
        y_col=y_col,
        write_outputs=write_outputs,
        logger=logger,
    )

    # 3) Club totals plot
    print("\n3) Plotting club-level totals ...")
    plot_club_injury_totals(inj, fig_dir=args.fig_dir, write_outputs=write_outputs, logger=logger)

    print("\n✅ Finished summary, validation, and club plots.")


if __name__ == "__main__":
    main()
