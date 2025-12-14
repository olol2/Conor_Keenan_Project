# src/analysis/build_player_value_table.py
from __future__ import annotations

"""
Build a consolidated player value table from the combined proxies:

- Rotation proxy (rotation_elasticity + usage rates)
- Injury proxy in points (inj_xpts) and £ (inj_gbp)
- Z-scores for each proxy
- A simple combined index: average of rot_z and inj_xpts_z

Output (default):
    results/player_value_table.csv
"""

from pathlib import Path
import argparse
import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build consolidated player value table from combined proxies.")
    p.add_argument(
        "--combined",
        type=str,
        default=None,
        help="Path to combined proxies CSV (default: results/proxies_combined.csv)",
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output CSV path (default: results/player_value_table.csv)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + validate but do not write output",
    )
    return p.parse_args()


def _zscore(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    m = float(x.mean(skipna=True)) if x.notna().any() else np.nan
    s = float(x.std(skipna=True)) if x.notna().any() else np.nan
    if not np.isfinite(s) or s <= 0:
        return pd.Series([np.nan] * len(x), index=x.index)
    return (x - m) / s


def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("build_player_value_table", cfg.logs, "build_player_value_table.log")
    meta_path = write_run_metadata(cfg.metadata, "build_player_value_table", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    combined_path = Path(args.combined) if args.combined else (cfg.project_root / "results" / "proxies_combined.csv") \
        if hasattr(cfg, "project_root") else (cfg.processed.parents[0] / "results" / "proxies_combined.csv")
    # The fallback above avoids relying on cfg.project_root. In your repo, cfg.processed is <root>/data/processed,
    # so cfg.processed.parents[0] is <root>/data, and parents[1] is <root>. We want <root>/results.
    if not combined_path.exists():
        # safer fallback to the conventional location relative to this file:
        root = Path(__file__).resolve().parents[2]
        combined_path = root / "results" / "proxies_combined.csv"

    out_path = Path(args.out) if args.out else (combined_path.parent / "player_value_table.csv")

    logger.info("Reading combined proxies from: %s", combined_path)
    logger.info("Writing output to: %s", out_path)

    if not combined_path.exists():
        raise FileNotFoundError(f"Combined proxies file not found: {combined_path}")

    df = pd.read_csv(combined_path)
    df.columns = [c.strip() for c in df.columns]
    useful = df.copy()

    # ------------------------------------------------------------------
    # Ensure injury columns have standard names
    # ------------------------------------------------------------------
    if "inj_xpts" not in useful.columns and "xpts_season_total" in useful.columns:
        useful["inj_xpts"] = useful["xpts_season_total"]

    if "inj_gbp" not in useful.columns and "value_gbp_season_total" in useful.columns:
        useful["inj_gbp"] = useful["value_gbp_season_total"]

    # ------------------------------------------------------------------
    # Basic typing
    # ------------------------------------------------------------------
    if "season" in useful.columns:
        useful["season"] = pd.to_numeric(useful["season"], errors="coerce").astype("Int64")

    for col in ["player_name", "team_id"]:
        if col in useful.columns:
            useful[col] = useful[col].astype(str)

    for col in ["rotation_elasticity", "inj_xpts", "inj_gbp"]:
        if col in useful.columns:
            useful[col] = pd.to_numeric(useful[col], errors="coerce")

    # ------------------------------------------------------------------
    # Keep rows where at least one proxy exists
    # ------------------------------------------------------------------
    has_rot = useful["rotation_elasticity"].notna() if "rotation_elasticity" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_pts = useful["inj_xpts"].notna() if "inj_xpts" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_gbp = useful["inj_gbp"].notna() if "inj_gbp" in useful.columns else pd.Series(False, index=useful.index)

    useful = useful[has_rot | has_inj_pts | has_inj_gbp].copy()

    # ------------------------------------------------------------------
    # Z-scores
    # ------------------------------------------------------------------
    if "rotation_elasticity" in useful.columns:
        useful["rot_z"] = _zscore(useful["rotation_elasticity"])
    if "inj_xpts" in useful.columns:
        useful["inj_xpts_z"] = _zscore(useful["inj_xpts"])
    if "inj_gbp" in useful.columns:
        useful["inj_gbp_z"] = _zscore(useful["inj_gbp"])

    # Combined index = mean(rot_z, inj_xpts_z) where available
    proxy_cols_for_index = [c for c in ["rot_z", "inj_xpts_z"] if c in useful.columns]
    useful["combined_value_z"] = useful[proxy_cols_for_index].mean(axis=1) if proxy_cols_for_index else np.nan

    # ------------------------------------------------------------------
    # Order columns nicely (keep only those present)
    # ------------------------------------------------------------------
    cols = [
        "player_id",          # Understat numeric ID (if present in combined file)
        "player_name",
        "team_id",
        "season",
        "n_matches",
        "n_starts",
        "start_rate_all",
        "start_rate_hard",
        "start_rate_easy",
        "rotation_elasticity",
        "rot_z",
        "inj_xpts",
        "inj_xpts_z",
        "inj_gbp",
        "inj_gbp_z",
        "combined_value_z",
    ]
    cols = [c for c in cols if c in useful.columns]

    # Stable sorting
    sort_cols = [c for c in ["season", "team_id", "player_name"] if c in useful.columns]
    value_table = useful[cols].copy()
    if sort_cols:
        value_table = value_table.sort_values(sort_cols)

    logger.info("Value table built: shape=%s", value_table.shape)

    if args.dry_run:
        print(f"✅ dry-run complete | output shape={value_table.shape} | output NOT written")
        # small preview
        print(value_table.head(10))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(value_table, out_path, index=False)

    logger.info("Saved player value table: %s (rows=%d)", out_path, len(value_table))
    print(f"✅ Saved player value table to {out_path} | rows={len(value_table)} | cols={len(value_table.columns)}")


if __name__ == "__main__":
    main()
