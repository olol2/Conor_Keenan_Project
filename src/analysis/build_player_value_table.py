"""
Build a consolidated player value table from the combined proxies.

Unit of observation:
- One row per player–team–season (as provided by results/proxies_combined.csv).

What this computes:
- Rotation proxy: rotation_elasticity + usage rates (already computed upstream)
- Injury proxy: injury impact in xPts (inj_xpts) and GBP (inj_gbp)
- Global z-scores (standardized across ALL rows in the combined file)
- A simple combined index: mean(rot_z, inj_xpts_z)
  - Uses NaN-skipping mean: if only one proxy exists, combined_value_z equals that proxy’s z-score.

Default inputs/outputs:
  <repo>/results/proxies_combined.csv
  <repo>/results/player_value_table.csv
"""

from __future__ import annotations

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


def zscore(x: pd.Series) -> pd.Series:
    """
    Compute a standard z-score: (x - mean) / std with numeric coercion.
    Returns all-NaN if the series has no variance or cannot be computed safely.
    """
    s = pd.to_numeric(x, errors="coerce")
    mu = float(s.mean(skipna=True)) if s.notna().any() else np.nan
    sd = float(s.std(skipna=True)) if s.notna().any() else np.nan

    if not np.isfinite(mu) or not np.isfinite(sd) or sd <= 0:
        return pd.Series([np.nan] * len(s), index=s.index)

    return (s - mu) / sd


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parents[2]
    results_dir = root / "results"

    cfg = Config.load()
    logger = setup_logger("build_player_value_table", cfg.logs, "build_player_value_table.log")
    meta_path = write_run_metadata(cfg.metadata, "build_player_value_table", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    combined_path = Path(args.combined) if args.combined else (results_dir / "proxies_combined.csv")
    out_path = Path(args.out) if args.out else (results_dir / "player_value_table.csv")

    logger.info("Reading combined proxies from: %s", combined_path)
    logger.info("Writing output to: %s", out_path)

    if not combined_path.exists():
        raise FileNotFoundError(f"Combined proxies file not found: {combined_path}")

    df = pd.read_csv(combined_path)
    df.columns = [c.strip() for c in df.columns]
    useful = df.copy()

    # Fail fast on essential identifiers (helps catch upstream schema drift)
    required_ids = {"player_name", "team_id", "season"}
    missing_ids = required_ids - set(useful.columns)
    if missing_ids:
        raise ValueError(f"Combined proxies missing required columns: {sorted(missing_ids)}")

    # Standard injury column aliases (combine_proxies often creates inj_xpts)
    if "inj_xpts" not in useful.columns and "xpts_season_total" in useful.columns:
        useful["inj_xpts"] = useful["xpts_season_total"]
    if "inj_gbp" not in useful.columns and "value_gbp_season_total" in useful.columns:
        useful["inj_gbp"] = useful["value_gbp_season_total"]

    # Types
    useful["season"] = pd.to_numeric(useful["season"], errors="coerce").astype("Int64")
    useful["player_name"] = useful["player_name"].astype(str)
    useful["team_id"] = useful["team_id"].astype(str)

    for c in ["rotation_elasticity", "inj_xpts", "inj_gbp"]:
        if c in useful.columns:
            useful[c] = pd.to_numeric(useful[c], errors="coerce")

    # Keep rows with at least one proxy present
    has_rot = useful["rotation_elasticity"].notna() if "rotation_elasticity" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_pts = useful["inj_xpts"].notna() if "inj_xpts" in useful.columns else pd.Series(False, index=useful.index)
    has_inj_gbp = useful["inj_gbp"].notna() if "inj_gbp" in useful.columns else pd.Series(False, index=useful.index)
    useful = useful[has_rot | has_inj_pts | has_inj_gbp].copy()

    # Z-scores (global across the full file)
    if "rotation_elasticity" in useful.columns:
        useful["rot_z"] = zscore(useful["rotation_elasticity"])
    if "inj_xpts" in useful.columns:
        useful["inj_xpts_z"] = zscore(useful["inj_xpts"])
    if "inj_gbp" in useful.columns:
        useful["inj_gbp_z"] = zscore(useful["inj_gbp"])

    # Combined index = mean(rot_z, inj_xpts_z) skipping missing values
    z_cols = [c for c in ["rot_z", "inj_xpts_z"] if c in useful.columns]
    useful["combined_value_z"] = useful[z_cols].mean(axis=1) if z_cols else np.nan

    # Output columns (keeps only those present)
    cols = [
        "player_id",
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

    out = useful[cols].copy()
    out = out.sort_values(["season", "team_id", "player_name"], kind="mergesort")  # stable sort

    logger.info("Value table built: shape=%s", out.shape)

    if args.dry_run:
        print(f"✅ dry-run complete | output shape={out.shape} | output NOT written")
        print(out.head(10))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(out, out_path, index=False)

    logger.info("Saved player value table: %s (rows=%d)", out_path, len(out))
    print(f"✅ Saved player value table to {out_path} | rows={len(out)} | cols={len(out.columns)}")


if __name__ == "__main__":
    main()
