"""
Run Proxy 1: Rotation Elasticity (fixture-context selectivity).

Concept:
- A player is “rotated” if their starting probability changes across match contexts.
- We proxy match context using team-level expected points (xPts) from odds.

Definition:
For each player–team–season:
1) Classify that team’s matches into hard/medium/easy based on team-season xPts terciles:
     hard   = low xPts (matches where the team is expected to perform worse)
     medium = middle tercile
     easy   = high xPts
2) Compute start rates by context:
     start_rate_hard = P(start | hard matches)
     start_rate_easy = P(start | easy matches)
3) Rotation Elasticity:
     rotation_elasticity = start_rate_hard - start_rate_easy

Interpretation:
- Negative elasticity: player starts more in “easy” matches (more likely to be rotated out in hard matches).
- Positive elasticity: player starts more in “hard” matches (trusted/important in tougher contexts).

Input (default):
- <cfg.processed>/panel_rotation.parquet
  (If parquet is unavailable, will try <cfg.processed>/panel_rotation.csv)

Output (default):
- <project_root>/results/proxy1_rotation_elasticity.csv

One row per (player_id, player_name, team_id, season).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


# ---------------------------------------------------------------------
# Load rotation panel
# ---------------------------------------------------------------------

REQUIRED_COLS = [
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


def load_panel_rotation(path: Path) -> pd.DataFrame:
    """
    Load the rotation panel.

    Supports:
    - parquet (preferred)
    - csv fallback (if parquet engine missing)

    Returns a DataFrame with standardised dtypes and required columns only.
    """
    if not path.exists():
        raise FileNotFoundError(f"Rotation panel not found: {path}")

    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file type for rotation panel: {path.suffix}")

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in panel_rotation: {missing}")

    # Basic typing (keeps subsequent groupby logic stable)
    out = df[REQUIRED_COLS].copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce").astype(int)
    out["player_id"] = out["player_id"].astype(str)
    out["player_name"] = out["player_name"].astype(str)
    out["team_id"] = out["team_id"].astype(str)
    out["opponent_id"] = out["opponent_id"].astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["xpts"] = pd.to_numeric(out["xpts"], errors="coerce")
    out["started"] = out["started"].astype(bool)

    bad_dates = int(out["date"].isna().sum())
    if bad_dates:
        raise ValueError(f"panel_rotation has {bad_dates} rows with invalid dates")

    return out


# ---------------------------------------------------------------------
# Classify match contexts using team-season xPts terciles
# ---------------------------------------------------------------------

def add_stakes_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each team-season, classify matches into stakes categories using xPts terciles.

    hard   = bottom tercile of xPts (team expected points are low)
    medium = middle tercile
    easy   = top tercile of xPts

    Note:
    - Using xPts (rather than opponent table position) keeps the definition consistent
      with the odds-based expected performance approach used elsewhere in the project.
    """
    df = df.copy()

    def team_season_stakes(sub: pd.DataFrame) -> pd.DataFrame:
        # Drop missing xpts inside group to avoid quantile issues
        sub = sub.copy()
        x = sub["xpts"]

        q_low = x.quantile(1 / 3)
        q_high = x.quantile(2 / 3)

        def categorize(v: float) -> str:
            if v <= q_low:
                return "hard"
            if v >= q_high:
                return "easy"
            return "medium"

        sub["stakes"] = sub["xpts"].apply(categorize)
        return sub

    # Group by team + season (context must be team-season specific)
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
    For each player-team-season, compute start rates by context and the elasticity metric.

    Filters:
    - min_matches: minimum total matches observed for that player-team-season
    - min_hard/min_easy: minimum matches in the hard/easy terciles
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

        rotation_elasticity = (
            float(start_rate_hard - start_rate_easy)
            if np.isfinite(start_rate_hard) and np.isfinite(start_rate_easy)
            else np.nan
        )

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

    keep = (
        (grouped["n_matches"] >= min_matches)
        & (grouped["n_hard"] >= min_hard)
        & (grouped["n_easy"] >= min_easy)
        & grouped["rotation_elasticity"].notna()
    )
    filtered = grouped.loc[keep].copy()
    return filtered


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Proxy 1: rotation elasticity.")
    p.add_argument("--panel", type=str, default=None, help="Override rotation panel path (.parquet or .csv)")
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

    # Results dir: default to <project_root>/results
    project_root = getattr(cfg, "project_root", None) or getattr(cfg, "root", None) or Path(__file__).resolve().parents[2]
    results_dir = getattr(cfg, "results", None) or (project_root / "results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Default panel path: prefer parquet; fallback to CSV if parquet missing
    processed_dir = getattr(cfg, "processed", None) or (project_root / "data" / "processed")
    default_parquet = processed_dir / "panel_rotation.parquet"
    default_csv = processed_dir / "panel_rotation.csv"

    if args.panel:
        panel_path = Path(args.panel)
    else:
        panel_path = default_parquet if default_parquet.exists() else default_csv

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

    mean_el = float(rot["rotation_elasticity"].mean()) if len(rot) else float("nan")
    logger.info("Rotation proxy built: shape=%s | mean_elasticity=%.6f", rot.shape, mean_el)

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"[OK] dry-run complete | rotation proxy shape: {rot.shape} | output NOT written")
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(rot, out_csv, index=False)

    logger.info("Saved rotation elasticity proxy: %s (rows=%s)", out_csv, len(rot))
    print(f"[OK] Saved rotation elasticity proxy | shape={rot.shape}")
    print(f"     {out_csv}")


if __name__ == "__main__":
    main()
