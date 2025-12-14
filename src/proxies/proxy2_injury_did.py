# src/proxies/proxy2_injury_did.py
from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


"""
Estimate Proxy 2 (Injury DiD-style effect) per player–team–season.

Input:
  <cfg.processed>/panel_injury.parquet   (built by src/proxies/build_injury_panel.py)

Output (defaults):
  results/proxy2_injury_did.parquet
  results/proxy2_injury_did.csv

Model (per player–team–season):
  xpts ~ unavailable + n_injured_squad + C(opponent_id) + match_index

Notes:
- player key is auto-detected: prefers 'player_name', else 'player_id'
- match_index is a numeric time trend (avoids saturation/collinearity issues)
"""


# ---------------------------------------------------------------------
# Paths (project-root based, independent of Config internals)
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------
def load_panel(panel_path: Path, logger) -> tuple[pd.DataFrame, str]:
    if not panel_path.exists():
        raise FileNotFoundError(f"panel_injury.parquet not found at: {panel_path}")

    df = pd.read_parquet(panel_path)

    # Detect player key
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
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["season"] = out["season"].astype(int)
    out["unavailable"] = pd.to_numeric(out["unavailable"], errors="coerce").fillna(0).astype(int)
    out["xpts"] = pd.to_numeric(out["xpts"], errors="coerce")
    out["n_injured_squad"] = pd.to_numeric(out["n_injured_squad"], errors="coerce").fillna(0).astype(int)

    bad_dates = int(out["date"].isna().sum())
    if bad_dates:
        raise ValueError(f"panel_injury has {bad_dates} rows with invalid dates.")

    logger.info("Panel loaded: shape=%s | player_key=%s", out.shape, player_key)
    return out, player_key


def summarise_player_seasons(df: pd.DataFrame, player_key: str) -> pd.DataFrame:
    summary = (
        df.groupby([player_key, "team_id", "season"])
        .agg(
            n_matches=("match_id", "nunique"),
            n_unavail=("unavailable", "sum"),
        )
        .reset_index()
    )
    summary["n_avail"] = summary["n_matches"] - summary["n_unavail"]
    return summary


def filter_player_seasons(summary: pd.DataFrame, min_unavail: int, min_avail: int, logger) -> pd.DataFrame:
    good = summary.query("n_unavail >= @min_unavail and n_avail >= @min_avail").copy()
    logger.info(
        "Player-seasons kept: %d (min_unavail=%d, min_avail=%d) out of %d",
        len(good), min_unavail, min_avail, len(summary),
    )
    return good


# ---------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------
def estimate_one(df: pd.DataFrame, player_key: str, pid, tid, season, logger) -> dict | None:
    g = df[(df[player_key] == pid) & (df["team_id"] == tid) & (df["season"] == season)].copy()
    g = g.sort_values("date")

    if g["unavailable"].nunique() < 2:
        return None

    # numeric time trend (avoids saturation)
    g["match_index"] = np.arange(len(g), dtype=int)

    # Choose covariance type: cluster by opponent if enough clusters; else HC1
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
        logger.warning("Failed estimation for %s=%s team=%s season=%s: %s", player_key, pid, tid, season, e)
        return None


def run_did(df: pd.DataFrame, player_key: str, min_unavail: int, min_avail: int, logger) -> pd.DataFrame:
    summary = summarise_player_seasons(df, player_key)
    good = filter_player_seasons(summary, min_unavail=min_unavail, min_avail=min_avail, logger=logger)

    results: list[dict] = []
    for _, row in good.iterrows():
        pid = row[player_key]
        tid = row["team_id"]
        season = row["season"]
        est = estimate_one(df, player_key, pid, tid, season, logger)
        if est is not None:
            results.append(est)

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results)
    return out


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Proxy 2: injury DiD per player–team–season.")
    p.add_argument("--panel", type=str, default=None, help="Override panel_injury.parquet path")
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
    meta_path = write_run_metadata(cfg.metadata, "proxy2_injury_did", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    panel_path = Path(args.panel) if args.panel else (cfg.processed / "panel_injury.parquet")

    out_parquet = Path(args.out_parquet) if args.out_parquet else (RESULTS_DIR / "proxy2_injury_did.parquet")
    out_csv = Path(args.out_csv) if args.out_csv else (RESULTS_DIR / "proxy2_injury_did.csv")

    logger.info("Reading panel from: %s", panel_path)
    logger.info("Writing outputs to: parquet=%s csv=%s", out_parquet, out_csv)
    logger.info("Filters: min_unavail=%d min_avail=%d", args.min_unavail, args.min_avail)

    df, player_key = load_panel(panel_path, logger)
    did = run_did(df, player_key, min_unavail=args.min_unavail, min_avail=args.min_avail, logger=logger)

    if did.empty:
        logger.warning("No DiD estimates produced. Try lowering min thresholds or inspect panel coverage.")
        print("⚠️ No DiD estimates produced.")
        return

    logger.info("DiD estimates built: shape=%s | mean_beta=%.4f",
                did.shape, float(did["beta_unavailable"].mean()))

    if args.dry_run:
        logger.info("Dry-run complete. Output not written.")
        print(f"✅ dry-run complete | did shape: {did.shape} | output NOT written")
        return

    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    did.to_parquet(out_parquet, index=False)
    atomic_write_csv(did, out_csv, index=False)

    print(f"✅ Saved {len(did)} player-season estimates to")
    print(f"   - {out_parquet}")
    print(f"   - {out_csv}")


if __name__ == "__main__":
    main()
