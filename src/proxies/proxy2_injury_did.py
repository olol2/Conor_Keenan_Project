"""
Estimate Proxy 2: Injury Impact using a DiD-style within team-season regression.

Goal:
- Quantify how much a team's expected points (xPts) change when a given player is unavailable,
  controlling for opponent strength (opponent fixed effects), squad-wide injury burden, and a
  time trend within the season.

Model (estimated separately for each player–team–season):
  xpts ~ unavailable + n_injured_squad + C(opponent_id) + match_index

Key coefficient:
- beta_unavailable = estimated change in xPts when that player is unavailable (unavailable=1),
  relative to when they are available (unavailable=0), within the same team-season.

Inputs (default):
- <cfg.processed>/panel_injury.parquet
  (CSV fallback: <cfg.processed>/panel_injury.csv)

Outputs (default):
- <project_root>/results/proxy2_injury_did.parquet
- <project_root>/results/proxy2_injury_did.csv

Notes:
- player key is auto-detected: prefer 'player_name', else 'player_id'
- match_index is a numeric time trend to avoid time fixed-effect saturation
- covariance: cluster by opponent if there are enough opponent clusters; otherwise HC1
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


# ---------------------------------------------------------------------
# Project-level defaults (independent of Config internals)
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------
def _read_panel(path: Path) -> pd.DataFrame:
    """Read panel from parquet or csv."""
    if not path.exists():
        raise FileNotFoundError(f"Panel not found: {path}")

    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported panel format: {path.suffix} (expected .parquet or .csv)")


def load_panel(panel_path: Path, logger) -> tuple[pd.DataFrame, str]:
    """
    Load the injury panel and standardise minimal columns needed for regression.

    Returns:
    - df: cleaned DataFrame
    - player_key: either 'player_name' or 'player_id' (auto-detected)
    """
    df = _read_panel(panel_path)

    # Detect player key for grouping/estimation
    if "player_name" in df.columns:
        player_key = "player_name"
    elif "player_id" in df.columns:
        player_key = "player_id"
    else:
        raise ValueError(
            "panel_injury is missing both 'player_name' and 'player_id'. "
            f"Columns={list(df.columns)}"
        )

    needed = [
        "match_id",
        "team_id",
        "date",
        "season",
        "opponent_id",
        "xpts",
        "unavailable",
        "n_injured_squad",
        player_key,
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in panel_injury: {missing}")

    out = df[needed].copy()

    # Basic typing / cleaning
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["season"] = pd.to_numeric(out["season"], errors="coerce").astype(int)

    out["team_id"] = out["team_id"].astype(str).str.strip()
    out["opponent_id"] = out["opponent_id"].astype(str).str.strip()
    out[player_key] = out[player_key].astype(str).str.strip()

    out["unavailable"] = pd.to_numeric(out["unavailable"], errors="coerce").fillna(0).astype(int)
    out["xpts"] = pd.to_numeric(out["xpts"], errors="coerce")
    out["n_injured_squad"] = pd.to_numeric(out["n_injured_squad"], errors="coerce").fillna(0).astype(int)

    # Fail fast on unusable rows (statsmodels will silently drop NAs otherwise)
    bad_dates = int(out["date"].isna().sum())
    if bad_dates:
        raise ValueError(f"panel_injury has {bad_dates} rows with invalid dates.")

    # Drop rows with missing xpts (cannot be used in regression)
    before = len(out)
    out = out.dropna(subset=["xpts"]).copy()
    dropped = before - len(out)
    if dropped:
        logger.warning("Dropped %d rows with missing xpts before estimation.", dropped)

    logger.info("Panel loaded: shape=%s | player_key=%s | path=%s", out.shape, player_key, panel_path)
    return out, player_key


# ---------------------------------------------------------------------
# Filtering: keep only player-team-seasons with both available and unavailable matches
# ---------------------------------------------------------------------
def summarise_player_seasons(df: pd.DataFrame, player_key: str) -> pd.DataFrame:
    """Summarise match counts and (un)availability counts per player-team-season."""
    summary = (
        df.groupby([player_key, "team_id", "season"], dropna=False)
        .agg(
            n_matches=("match_id", "nunique"),
            n_unavail=("unavailable", "sum"),
        )
        .reset_index()
    )
    summary["n_avail"] = summary["n_matches"] - summary["n_unavail"]
    return summary


def filter_player_seasons(summary: pd.DataFrame, min_unavail: int, min_avail: int, logger) -> pd.DataFrame:
    """Apply minimum variation thresholds so the unavailable coefficient is identified."""
    good = summary.query("n_unavail >= @min_unavail and n_avail >= @min_avail").copy()
    logger.info(
        "Player-seasons kept: %d (min_unavail=%d, min_avail=%d) out of %d",
        len(good), min_unavail, min_avail, len(summary),
    )
    return good


# ---------------------------------------------------------------------
# Estimation: one regression per player-team-season
# ---------------------------------------------------------------------
def estimate_one(df: pd.DataFrame, player_key: str, pid: str, tid: str, season: int, logger) -> dict | None:
    """
    Estimate the unavailable effect for one player-team-season.

    Returns a dict of estimates (beta, SE, p-value, sample sizes), or None if not identified.
    """
    g = df[(df[player_key] == pid) & (df["team_id"] == tid) & (df["season"] == season)].copy()
    g = g.sort_values("date")

    # Need both unavailable=0 and unavailable=1 within this season for identification
    if g["unavailable"].nunique() < 2:
        return None

    # Numeric time trend within this team-season (avoids saturated time FE)
    g["match_index"] = np.arange(len(g), dtype=int)

    # Opponent FE: ensure it is treated as categorical in the formula
    g["opponent_id"] = g["opponent_id"].astype(str)

    # Covariance choice: cluster by opponent if enough clusters; else robust HC1
    n_clusters = int(g["opponent_id"].nunique())
    if n_clusters >= 10:
        cov_type = "cluster"
        fit_kw = {"cov_type": "cluster", "cov_kwds": {"groups": g["opponent_id"]}}
    else:
        cov_type = "HC1"
        fit_kw = {"cov_type": "HC1"}

    try:
        model = smf.ols(
            "xpts ~ unavailable + n_injured_squad + C(opponent_id) + match_index",
            data=g,
        ).fit(**fit_kw)

        beta = float(model.params.get("unavailable", np.nan))
        se = float(model.bse.get("unavailable", np.nan))
        pval = float(model.pvalues.get("unavailable", np.nan))

        return {
            player_key: pid,
            "team_id": tid,
            "season": int(season),
            "beta_unavailable": beta,
            "se_unavailable": se,
            "pvalue_unavailable": pval,
            "n_matches": int(len(g)),
            "n_unavail": int(g["unavailable"].sum()),
            "n_avail": int((g["unavailable"] == 0).sum()),
            "cov_type": cov_type,
            "n_opp_clusters": n_clusters,
        }
    except Exception as e:
        logger.warning(
            "Failed estimation for %s=%s team=%s season=%s: %s",
            player_key, pid, tid, season, e
        )
        return None


def run_did(df: pd.DataFrame, player_key: str, min_unavail: int, min_avail: int, logger) -> pd.DataFrame:
    """Run all player-team-season regressions and return the stacked results table."""
    summary = summarise_player_seasons(df, player_key)
    good = filter_player_seasons(summary, min_unavail=min_unavail, min_avail=min_avail, logger=logger)

    results: list[dict] = []
    for _, row in good.iterrows():
        pid = str(row[player_key])
        tid = str(row["team_id"])
        season = int(row["season"])

        est = estimate_one(df, player_key, pid, tid, season, logger)
        if est is not None:
            results.append(est)

    return pd.DataFrame(results) if results else pd.DataFrame()


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Proxy 2: injury DiD per player–team–season.")
    p.add_argument("--panel", type=str, default=None, help="Override panel_injury path (.parquet or .csv)")
    p.add_argument("--min-unavail", type=int, default=2, help="Min unavailable matches per player-season")
    p.add_argument("--min-avail", type=int, default=2, help="Min available matches per player-season")
    p.add_argument("--out-csv", type=str, default=None, help="Override output CSV path")
    p.add_argument("--out-parquet", type=str, default=None, help="Override output parquet path")
    p.add_argument("--dry-run", action="store_true", help="Run estimation but do not write outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config.load()

    logger = setup_logger("proxy2_injury_did", cfg.logs, "proxy2_injury_did.log")
    meta_path = write_run_metadata(
        cfg.metadata,
        "proxy2_injury_did",
        extra={
            "dry_run": bool(args.dry_run),
            "min_unavail": int(args.min_unavail),
            "min_avail": int(args.min_avail),
        },
    )
    logger.info("Run metadata saved to: %s", meta_path)

    # Default panel path: prefer parquet, fallback to CSV
    processed_dir = getattr(cfg, "processed", None) or (PROJECT_ROOT / "data" / "processed")
    default_parquet = processed_dir / "panel_injury.parquet"
    default_csv = processed_dir / "panel_injury.csv"
    panel_path = Path(args.panel) if args.panel else (default_parquet if default_parquet.exists() else default_csv)

    out_parquet = Path(args.out_parquet) if args.out_parquet else (RESULTS_DIR / "proxy2_injury_did.parquet")
    out_csv = Path(args.out_csv) if args.out_csv else (RESULTS_DIR / "proxy2_injury_did.csv")

    logger.info("Reading panel from: %s", panel_path)
    logger.info("Writing outputs to: parquet=%s csv=%s", out_parquet, out_csv)
    logger.info("Filters: min_unavail=%d min_avail=%d", args.min_unavail, args.min_avail)

    df, player_key = load_panel(panel_path, logger)
    did = run_did(df, player_key, min_unavail=int(args.min_unavail), min_avail=int(args.min_avail), logger=logger)

    if did.empty:
        logger.warning("No DiD estimates produced. Try lowering thresholds or inspect panel coverage.")
        print("[WARN] No DiD estimates produced.")
        return

    logger.info("DiD estimates built: shape=%s | mean_beta=%.4f",
                did.shape, float(did["beta_unavailable"].mean()))

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"[OK] dry-run complete | did shape: {did.shape} | output NOT written")
        return

    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Parquet is optional; do not fail the pipeline if parquet engines are missing
    try:
        did.to_parquet(out_parquet, index=False)
        parquet_status = "written"
    except Exception as e:
        parquet_status = f"skipped ({type(e).__name__}: {e})"
        logger.warning("Parquet write failed; continuing with CSV only. Reason: %s", parquet_status)

    atomic_write_csv(did, out_csv, index=False)

    print(f"[OK] Saved {len(did)} player-season estimates")
    print(f"     CSV:     {out_csv}")
    print(f"     Parquet: {out_parquet} ({parquet_status})")


if __name__ == "__main__":
    main()
