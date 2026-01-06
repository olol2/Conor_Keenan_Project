"""
Build a consolidated player value table from the combined proxies.

What this script does:
- Reads the combined proxies file (rotation + injury proxies merged at player-season level).
- Standardises injury proxy column names (handles legacy names in older outputs).
- Computes z-scores for each proxy.
- Computes a simple combined index: mean(rot_z, inj_xpts_z), ignoring missing values.

Expected input (default):
- <project_root>/results/proxies_combined.csv

Output (default):
- <project_root>/results/player_value_table.csv

Notes:
- This is a lightweight post-processing step; it does not re-run any scraping or proxy construction.
- The combined table may contain players with only rotation or only injury proxy data; those rows are kept.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build consolidated player value table from combined proxies.")
    p.add_argument(
        "--combined",
        type=Path,
        default=None,
        help="Path to combined proxies CSV (default: <project_root>/results/proxies_combined.csv)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: <project_root>/results/player_value_table.csv)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + validate but do not write output",
    )
    return p.parse_args()


def _project_root() -> Path:
    """
    Resolve the project root in a repo-robust way.

    This file is expected at: <root>/src/analysis/build_player_value_table.py
    so parents[2] is <root>.
    """
    return Path(__file__).resolve().parents[2]


def _zscore(series: pd.Series) -> pd.Series:
    """
    Compute a z-score, ignoring NaNs.

    Returns all-NaN if the standard deviation is zero/undefined.
    """
    x = pd.to_numeric(series, errors="coerce")
    if not x.notna().any():
        return pd.Series([np.nan] * len(x), index=x.index)

    m = float(x.mean(skipna=True))
    s = float(x.std(skipna=True))

    if not np.isfinite(s) or s <= 0:
        return pd.Series([np.nan] * len(x), index=x.index)

    return (x - m) / s


def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("build_player_value_table", cfg.logs, "build_player_value_table.log")
    meta_path = write_run_metadata(cfg.metadata, "build_player_value_table", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    root = _project_root()

    combined_path = args.combined if args.combined else (root / "results" / "proxies_combined.csv")
    out_path = args.out if args.out else (root / "results" / "player_value_table.csv")

    logger.info("Reading combined proxies from: %s", combined_path)
    logger.info("Writing output to: %s", out_path)

    if not combined_path.exists():
        raise FileNotFoundError(f"Combined proxies file not found: {combined_path}")

    df = pd.read_csv(combined_path)
    df.columns = [c.strip() for c in df.columns]
    useful = df.copy()

    # ------------------------------------------------------------------
    # Standardise injury proxy names (handles legacy column names)
    # ------------------------------------------------------------------
    # Some earlier pipeline versions wrote injury proxy totals as:
    #   xpts_season_total, value_gbp_season_total
    # For a stable output schema, mapped to:
    #   inj_xpts, inj_gbp
    if "inj_xpts" not in useful.columns and "xpts_season_total" in useful.columns:
        useful["inj_xpts"] = useful["xpts_season_total"]

    if "inj_gbp" not in useful.columns and "value_gbp_season_total" in useful.columns:
        useful["inj_gbp"] = useful["value_gbp_season_total"]

    # ------------------------------------------------------------------
    # Basic typing / cleaning 
    # ------------------------------------------------------------------
    if "season" in useful.columns:
        useful["season"] = pd.to_numeric(useful["season"], errors="coerce").astype("Int64")

    for col in ["player_name", "team_id"]:
        if col in useful.columns:
            useful[col] = useful[col].astype(str).str.strip()

    for col in ["rotation_elasticity", "inj_xpts", "inj_gbp"]:
        if col in useful.columns:
            useful[col] = pd.to_numeric(useful[col], errors="coerce")

    # ------------------------------------------------------------------
    # Keep rows where at least one proxy is available
    # (combined proxies may have rotation-only or injury-only rows)
    # ------------------------------------------------------------------
    has_rot = useful["rotation_elasticity"].notna() if "rotation_elasticity" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_pts = useful["inj_xpts"].notna() if "inj_xpts" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_gbp = useful["inj_gbp"].notna() if "inj_gbp" in useful.columns else pd.Series(False, index=useful.index)

    useful = useful[has_rot | has_inj_pts | has_inj_gbp].copy()

    # ------------------------------------------------------------------
    # Z-scores (global across the combined dataset)
    # ------------------------------------------------------------------
    if "rotation_elasticity" in useful.columns:
        useful["rot_z"] = _zscore(useful["rotation_elasticity"])
    if "inj_xpts" in useful.columns:
        useful["inj_xpts_z"] = _zscore(useful["inj_xpts"])
    if "inj_gbp" in useful.columns:
        useful["inj_gbp_z"] = _zscore(useful["inj_gbp"])

    # Combined index: mean across available z-scores (NaNs ignored by pandas mean)
    proxy_cols_for_index = [c for c in ["rot_z", "inj_xpts_z"] if c in useful.columns]
    useful["combined_value_z"] = useful[proxy_cols_for_index].mean(axis=1) if proxy_cols_for_index else np.nan

    # ------------------------------------------------------------------
    # Column order for the final table (keeps only those present)
    # ------------------------------------------------------------------
    cols = [
        "player_id",          # Understat numeric ID (if present)
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

    value_table = useful[cols].copy()

    # Stable sorting for deterministic output files
    sort_cols = [c for c in ["season", "team_id", "player_name"] if c in value_table.columns]
    if sort_cols:
        value_table = value_table.sort_values(sort_cols).reset_index(drop=True)

    logger.info("Value table built: shape=%s", value_table.shape)

    if args.dry_run:
        print(f"✅ dry-run complete | output shape={value_table.shape} | output NOT written")
        print(value_table.head(10))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(value_table, out_path, index=False)

    logger.info("Saved player value table: %s (rows=%d)", out_path, len(value_table))
    print(f"✅ Saved player value table to {out_path} | rows={len(value_table)} | cols={len(value_table.columns)}")


if __name__ == "__main__":
    main()
