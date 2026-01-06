"""
Post-process Proxy 2 DiD estimates into interpretable units (xPts and £).

Inputs:
- results/proxy2_injury_did.(parquet|csv)  [from src/proxies/proxy2_injury_did.py]
- data/processed/points_to_pounds/points_to_pounds_<season>.csv
  (one file per season; maps Points -> Money_gbp)

Outputs (default):
- results/proxy2_injury_did_points_gbp.csv
- results/proxy2_injury_did_points_gbp.parquet (optional; skipped if parquet engine missing)

Interpretation:
- proxy2_injury_did estimates: beta_unavailable from xpts ~ unavailable + controls
  where unavailable=1 means the player is absent.
- Therefore, xPts gain from having the player available (present) is:
    xpts_per_match_present = -beta_unavailable
- Season total value in xPts:
    xpts_season_total = xpts_per_match_present * n_matches
- Convert xPts -> GBP using season-specific gbp_per_point.
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
# IO: read did results (parquet or csv)
# ---------------------------------------------------------------------
def _read_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"DiD results not found: {path}")

    suf = path.suffix.lower()
    if suf == ".parquet":
        return pd.read_parquet(path)
    if suf == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported file type: {path.suffix} (expected .parquet or .csv)")


def load_did_results(path: Path, logger) -> tuple[pd.DataFrame, str]:
    """
    Load DiD estimates produced by proxy2_injury_did.py.

    Supports either:
      - player_name-based outputs, or
      - player_id-based outputs

    Returns:
      (df, player_key_col)
    """
    df = _read_results(path)

    # Detect player identifier column
    if "player_name" in df.columns:
        player_key = "player_name"
    elif "player_id" in df.columns:
        player_key = "player_id"
    else:
        raise ValueError(
            f"DiD results must contain 'player_name' or 'player_id'. Columns={list(df.columns)}"
        )

    needed = [
        player_key,
        "team_id",
        "season",
        "beta_unavailable",
        "se_unavailable",
        "n_matches",
        "n_unavail",
        "n_avail",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DiD results: {missing}")

    out = df[needed].copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce").astype(int)
    out["n_matches"] = pd.to_numeric(out["n_matches"], errors="coerce").fillna(0).astype(int)
    out["beta_unavailable"] = pd.to_numeric(out["beta_unavailable"], errors="coerce")

    logger.info("Loaded DiD results: shape=%s | player_key=%s | path=%s", out.shape, player_key, path)
    return out, player_key


# ---------------------------------------------------------------------
# Points-to-pounds mapping
# ---------------------------------------------------------------------
def load_points_to_pounds_all_seasons(points_dir: Path, logger) -> pd.DataFrame:
    """
    Build a mapping season -> gbp_per_point using all CSVs in points_dir.

    For each season file, fit a linear relationship:
      money_gbp ~ intercept + slope * points
    and use slope as gbp_per_point.

    This is equivalent to a constant £/point assumption within a season.
    """
    if not points_dir.exists():
        raise FileNotFoundError(f"Points-to-pounds directory not found: {points_dir}")

    files = sorted(points_dir.glob("points_to_pounds_*.csv"))
    if not files:
        raise FileNotFoundError(f"No files named 'points_to_pounds_*.csv' found in {points_dir}")

    rows: list[dict] = []

    for path in files:
        tmp = pd.read_csv(path)

        # Normalize column names across potential variants
        tmp = tmp.rename(columns={"Season": "season_str", "Points": "points", "Money_gbp": "money_gbp"})

        needed = ["season_str", "points", "money_gbp"]
        missing = [c for c in needed if c not in tmp.columns]
        if missing:
            raise ValueError(f"Missing columns in {path.name}: {missing}")

        tmp["season"] = tmp["season_str"].astype(str).str.slice(0, 4).astype(int)

        # Money could have commas/underscores; remove formatting safely
        money_raw = (
            tmp["money_gbp"]
            .astype(str)
            .str.replace("_", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        y = pd.to_numeric(money_raw, errors="coerce").to_numpy(dtype=float)
        x = pd.to_numeric(tmp["points"], errors="coerce").to_numpy(dtype=float)

        if np.isnan(x).any() or np.isnan(y).any():
            raise ValueError(f"NaNs after numeric conversion in {path.name}. Check money/points formatting.")
        if len(np.unique(x)) < 2:
            raise ValueError(f"Not enough variation in points in {path.name} to fit a slope.")

        slope, _intercept = np.polyfit(x, y, 1)

        season_year = int(tmp["season"].iloc[0])
        rows.append({"season": season_year, "gbp_per_point": float(slope)})

    mapping = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    logger.info("Built gbp_per_point mapping: seasons=%d", len(mapping))
    return mapping


# ---------------------------------------------------------------------
# Interpretation transforms
# ---------------------------------------------------------------------
def add_points_interpretation(did: pd.DataFrame) -> pd.DataFrame:
    """
    Convert DiD coefficient into "value when present" in xPts.

    Since unavailable=1 indicates the player is absent:
      beta_unavailable is the estimated change in xPts when absent.
    Therefore:
      xpts_per_match_present = -beta_unavailable
    """
    out = did.copy()
    out["xpts_per_match_present"] = -out["beta_unavailable"]
    out["xpts_season_total"] = out["xpts_per_match_present"] * out["n_matches"]
    return out


def add_money_interpretation(did_points: pd.DataFrame, mapping: pd.DataFrame, logger) -> pd.DataFrame:
    """Attach gbp_per_point by season and compute £ value per match and per season."""
    out = did_points.merge(mapping, on="season", how="left")

    if out["gbp_per_point"].isna().any():
        missing_seasons = sorted(out.loc[out["gbp_per_point"].isna(), "season"].unique().tolist())
        logger.warning("Missing gbp_per_point for seasons=%s (GBP values will be NaN).", missing_seasons)

    out["value_gbp_per_match"] = out["xpts_per_match_present"] * out["gbp_per_point"]
    out["value_gbp_season_total"] = out["xpts_season_total"] * out["gbp_per_point"]
    return out


# ---------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Add xPts + £ interpretation to Proxy 2 DiD estimates.")
    p.add_argument("--did", type=str, default=None, help="Override DiD results path (.parquet or .csv)")
    p.add_argument("--points-dir", type=str, default=None, help="Override points_to_pounds directory")
    p.add_argument("--out-csv", type=str, default=None, help="Override output CSV path")
    p.add_argument("--out-parquet", type=str, default=None, help="Override output parquet path")
    p.add_argument("--dry-run", action="store_true", help="Run compute but do not write outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("proxy2_injury_did_points", cfg.logs, "proxy2_injury_did_points.log")
    meta_path = write_run_metadata(cfg.metadata, "proxy2_injury_did_points", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    # Prefer cfg-based root; fallback to file location
    try:
        project_root = cfg.processed.parent.parent  # <root>/data/processed -> <root>
    except Exception:
        project_root = Path(__file__).resolve().parents[2]

    results_dir = project_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Default DiD file: prefer parquet if present, else CSV
    did_default_parquet = results_dir / "proxy2_injury_did.parquet"
    did_default_csv = results_dir / "proxy2_injury_did.csv"
    did_path = Path(args.did) if args.did else (did_default_parquet if did_default_parquet.exists() else did_default_csv)

    points_dir = Path(args.points_dir) if args.points_dir else (cfg.processed / "points_to_pounds")

    out_csv = Path(args.out_csv) if args.out_csv else (results_dir / "proxy2_injury_did_points_gbp.csv")
    out_parquet = Path(args.out_parquet) if args.out_parquet else (results_dir / "proxy2_injury_did_points_gbp.parquet")

    logger.info("Reading DiD from:   %s", did_path)
    logger.info("Reading points dir: %s", points_dir)
    logger.info("Writing CSV to:     %s", out_csv)
    logger.info("Writing parquet to: %s", out_parquet)

    did, player_key = load_did_results(did_path, logger)
    did_points = add_points_interpretation(did)

    mapping = load_points_to_pounds_all_seasons(points_dir, logger)
    did_full = add_money_interpretation(did_points, mapping, logger)

    # Stable column order
    cols_front = [player_key, "team_id", "season"]
    cols_rest = [c for c in did_full.columns if c not in cols_front]
    did_full = did_full[cols_front + cols_rest].copy()

    logger.info("Built interpreted proxy: shape=%s", did_full.shape)

    if args.dry_run:
        print(f"✅ dry-run complete | shape={did_full.shape} | output NOT written")
        print(did_full.head(10))
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(did_full, out_csv, index=False)

    # Parquet optional
    try:
        out_parquet.parent.mkdir(parents=True, exist_ok=True)
        did_full.to_parquet(out_parquet, index=False)
        parquet_status = "written"
    except Exception as e:
        parquet_status = f"skipped ({type(e).__name__}: {e})"
        logger.warning("Parquet write failed; continuing with CSV only. Reason: %s", parquet_status)

    print(f"✅ Saved points+£ proxy | shape={did_full.shape}")
    print(f"   - CSV:     {out_csv}")
    print(f"   - Parquet: {out_parquet} ({parquet_status})")


if __name__ == "__main__":
    main()
