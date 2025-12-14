# src/proxies/proxy1_rotation_elasticity.py
from __future__ import annotations

"""
Run Proxy 1: rotation elasticity.

Input (default):
  <cfg.processed>/panel_rotation.parquet

Output (default):
  <project_root>/results/proxy1_rotation_elasticity.csv

Definition:
For each player–team–season, classify matches into hard/medium/easy based on
team-season xPts terciles, then compute:

  rotation_elasticity = start_rate_hard - start_rate_easy

One row per (player_id, player_name, team_id, season).
"""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


# ---------------------------------------------------------------------
# Load rotation panel
# ---------------------------------------------------------------------

def load_panel_rotation(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"panel_rotation.parquet not found: {path}")

    df = pd.read_parquet(path)

    needed = [
        "match_id",
        "player_id",
        "player_name",
        "team_id",
        "season",
        "date",
        "opponent_id",
        "is_home",
        "xpts",
        "minutes",
        "started",
        "days_rest",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in panel_rotation: {missing}")

    # Basic typing
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype(int)
    df["player_id"] = df["player_id"].astype(str)
    df["player_name"] = df["player_name"].astype(str)
    df["team_id"] = df["team_id"].astype(str)
    df["opponent_id"] = df["opponent_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["xpts"] = pd.to_numeric(df["xpts"], errors="coerce")
    df["started"] = df["started"].astype(bool)

    if df["date"].isna().any():
        bad = int(df["date"].isna().sum())
        raise ValueError(f"panel_rotation has {bad} rows with invalid dates")

    return df[needed].copy()


# ---------------------------------------------------------------------
# Classify match stakes using team-season xPts terciles
# ---------------------------------------------------------------------

def add_stakes_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each team-season, classify matches into:
      - hard   (bottom tercile of team-season xPts)
      - medium
      - easy   (top tercile of team-season xPts)
    """
    df = df.copy()

    def team_season_stakes(sub: pd.DataFrame) -> pd.DataFrame:
        q_low = sub["xpts"].quantile(1 / 3)
        q_high = sub["xpts"].quantile(2 / 3)

        def categorize(x: float) -> str:
            if x <= q_low:
                return "hard"
            if x >= q_high:
                return "easy"
            return "medium"

        sub = sub.copy()
        sub["stakes"] = sub["xpts"].apply(categorize)
        return sub

    # Group by team + season (important)
    out = df.groupby(["team_id", "season"], group_keys=False).apply(team_season_stakes)
    return out


# ---------------------------------------------------------------------
# Compute per-player-season rotation elasticity
# ---------------------------------------------------------------------

def compute_rotation_elasticity(
    df: pd.DataFrame,
    min_matches: int = 3,
    min_hard: int = 1,
    min_easy: int = 1,
) -> pd.DataFrame:
    """
    For each player-team-season, compute:
      start_rate_hard, start_rate_easy, and rotation_elasticity = hard - easy.
    """
    df = df.copy()
    df["appearance"] = 1
    df["started_int"] = df["started"].astype(int)

    def agg_rates(sub: pd.DataFrame) -> pd.Series:
        n_matches = int(sub["appearance"].sum())
        n_starts = int(sub["started_int"].sum())
        start_rate_all = n_starts / n_matches if n_matches > 0 else np.nan

        hard = sub[sub["stakes"] == "hard"]
        n_hard = int(hard["appearance"].sum())
        n_hard_starts = int(hard["started_int"].sum())
        start_rate_hard = n_hard_starts / n_hard if n_hard > 0 else np.nan

        easy = sub[sub["stakes"] == "easy"]
        n_easy = int(easy["appearance"].sum())
        n_easy_starts = int(easy["started_int"].sum())
        start_rate_easy = n_easy_starts / n_easy if n_easy > 0 else np.nan

        if (not np.isnan(start_rate_hard)) and (not np.isnan(start_rate_easy)):
            rotation_elasticity = float(start_rate_hard - start_rate_easy)
        else:
            rotation_elasticity = np.nan

        return pd.Series(
            {
                "n_matches": n_matches,
                "n_starts": n_starts,
                "start_rate_all": start_rate_all,
                "n_hard": n_hard,
                "n_hard_starts": n_hard_starts,
                "start_rate_hard": start_rate_hard,
                "n_easy": n_easy,
                "n_easy_starts": n_easy_starts,
                "start_rate_easy": start_rate_easy,
                "rotation_elasticity": rotation_elasticity,
            }
        )

    grouped = (
        df.groupby(["player_id", "player_name", "team_id", "season"])
        .apply(agg_rates)
        .reset_index()
    )

    grouped["keep"] = (
        (grouped["n_matches"] >= min_matches)
        & (grouped["n_hard"] >= min_hard)
        & (grouped["n_easy"] >= min_easy)
        & grouped["rotation_elasticity"].notna()
    )

    filtered = grouped.loc[grouped["keep"]].drop(columns=["keep"]).copy()
    return filtered


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Proxy 1: rotation elasticity.")
    p.add_argument("--panel", type=str, default=None, help="Override panel_rotation.parquet path")
    p.add_argument("--out-csv", type=str, default=None, help="Override output CSV path")
    p.add_argument("--min-matches", type=int, default=3, help="Minimum matches per player-season")
    p.add_argument("--min-hard", type=int, default=1, help="Minimum hard matches per player-season")
    p.add_argument("--min-easy", type=int, default=1, help="Minimum easy matches per player-season")
    p.add_argument("--dry-run", action="store_true", help="Compute but do not write output")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("proxy1_rotation_elasticity", cfg.logs, "proxy1_rotation_elasticity.log")

    meta_path = write_run_metadata(
        cfg.metadata,
        "proxy1_rotation_elasticity",
        extra={
            "dry_run": bool(args.dry_run),
            "min_matches": int(args.min_matches),
            "min_hard": int(args.min_hard),
            "min_easy": int(args.min_easy),
        },
    )
    logger.info("Run metadata saved to: %s", meta_path)

    # Resolve project root/results dir robustly (Config may not define project_root/results)
    project_root = (
        getattr(cfg, "project_root", None)
        or getattr(cfg, "root", None)
        or Path(__file__).resolve().parents[2]
    )
    results_dir = getattr(cfg, "results", None) or (project_root / "results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Default panel path: prefer cfg.processed if available
    default_panel = (
        (getattr(cfg, "processed", None) / "panel_rotation.parquet")
        if getattr(cfg, "processed", None) is not None
        else (project_root / "data" / "processed" / "panel_rotation.parquet")
    )
    panel_path = Path(args.panel) if args.panel else default_panel

    out_csv = Path(args.out_csv) if args.out_csv else (results_dir / "proxy1_rotation_elasticity.csv")

    logger.info("Reading panel from: %s", panel_path)
    logger.info("Writing output to:  %s", out_csv)
    logger.info("Filters: min_matches=%s min_hard=%s min_easy=%s", args.min_matches, args.min_hard, args.min_easy)

    df = load_panel_rotation(panel_path)
    logger.info("Rotation panel loaded: shape=%s", df.shape)

    df = add_stakes_category(df)
    rot = compute_rotation_elasticity(
        df,
        min_matches=int(args.min_matches),
        min_hard=int(args.min_hard),
        min_easy=int(args.min_easy),
    )

    logger.info("Rotation proxy built: shape=%s | mean_elasticity=%.6f",
                rot.shape, float(rot["rotation_elasticity"].mean()) if len(rot) else float("nan"))

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | rotation proxy shape: {rot.shape} | output NOT written")
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(rot, out_csv, index=False)

    logger.info("Saved rotation elasticity proxy: %s (rows=%s)", out_csv, len(rot))
    print(f"✅ Saved rotation elasticity proxy | shape={rot.shape}")
    print(f"   - {out_csv}")


if __name__ == "__main__":
    main()
