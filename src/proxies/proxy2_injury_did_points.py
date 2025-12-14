# src/proxies/proxy2_injury_did_points.py
from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Load DiD results
# ---------------------------------------------------------------------
def load_did_results(path: Path, logger) -> tuple[pd.DataFrame, str]:
    """
    Load DiD estimates produced by proxy2_injury_did.py.

    Accepts either:
      - player_name-based output, or
      - player_id-based output

    Returns:
      (df, player_key_col)
    """
    if not path.exists():
        raise FileNotFoundError(f"DiD results not found: {path}")

    df = pd.read_parquet(path)

    # Support both versions
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

    df["season"] = df["season"].astype(int)
    logger.info("Loaded DiD results: shape=%s | player_key=%s", df.shape, player_key)

    return df[needed].copy(), player_key


# ---------------------------------------------------------------------
# Build £ per point mapping from all per-season CSVs
# ---------------------------------------------------------------------
def load_points_to_pounds_all_seasons(points_dir: Path, logger) -> pd.DataFrame:
    """
    Build a mapping season -> gbp_per_point using all CSVs in points_dir.

    For each season file, fit: money_gbp ~ alpha + beta * points
    and use beta as gbp_per_point.
    """
    if not points_dir.exists():
        raise FileNotFoundError(f"Points-to-pounds directory not found: {points_dir}")

    files = sorted(points_dir.glob("points_to_pounds_*.csv"))
    if not files:
        raise FileNotFoundError(f"No files named 'points_to_pounds_*.csv' found in {points_dir}")

    rows: list[dict] = []

    for path in files:
        tmp = pd.read_csv(path)

        # Normalise column names
        tmp = tmp.rename(
            columns={
                "Season": "season_str",
                "Points": "points",
                "Money_gbp": "money_gbp",
            }
        )

        needed = ["season_str", "points", "money_gbp"]
        missing = [c for c in needed if c not in tmp.columns]
        if missing:
            raise ValueError(f"Missing columns in {path.name}: {missing}")

        tmp["season"] = tmp["season_str"].astype(str).str.slice(0, 4).astype(int)

        # Make sure money is numeric even if formatted like "52_527_464.78" or "52,527,464.78"
        money_raw = tmp["money_gbp"].astype(str).str.replace("_", "", regex=False).str.replace(",", "", regex=False)
        y = pd.to_numeric(money_raw, errors="coerce").to_numpy(dtype=float)
        x = pd.to_numeric(tmp["points"], errors="coerce").to_numpy(dtype=float)

        if np.isnan(x).any() or np.isnan(y).any():
            raise ValueError(f"NaNs after numeric conversion in {path.name}. Check money/points formatting.")

        if len(np.unique(x)) < 2:
            raise ValueError(f"Not enough variation in points in {path.name} to fit a slope.")

        slope, intercept = np.polyfit(x, y, 1)

        season_year = int(tmp["season"].iloc[0])
        rows.append({"season": season_year, "gbp_per_point": float(slope)})

    mapping = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    logger.info("Built gbp_per_point mapping: seasons=%d", len(mapping))
    return mapping


# ---------------------------------------------------------------------
# Add xPts + £ interpretation
# ---------------------------------------------------------------------
def add_points_interpretation(did: pd.DataFrame) -> pd.DataFrame:
    """
    Compute:
      - xpts_per_match_present = -beta_unavailable
      - xpts_season_total = xpts_per_match_present * n_matches
    """
    out = did.copy()
    out["xpts_per_match_present"] = -out["beta_unavailable"]
    out["xpts_season_total"] = out["xpts_per_match_present"] * out["n_matches"]
    return out


def add_money_interpretation(did_points: pd.DataFrame, mapping: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Merge £/point mapping and compute:
      - value_gbp_per_match
      - value_gbp_season_total
    """
    out = did_points.merge(mapping, on="season", how="left")

    if out["gbp_per_point"].isna().any():
        missing_seasons = sorted(out.loc[out["gbp_per_point"].isna(), "season"].unique().tolist())
        logger.warning("Missing gbp_per_point for seasons=%s (values will be NaN).", missing_seasons)

    out["value_gbp_per_match"] = out["xpts_per_match_present"] * out["gbp_per_point"]
    out["value_gbp_season_total"] = out["xpts_season_total"] * out["gbp_per_point"]

    return out


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Add xPts + £ interpretation to Proxy 2 DiD estimates.")
    p.add_argument("--did", type=str, default=None, help="Override results/proxy2_injury_did.parquet path")
    p.add_argument("--points-dir", type=str, default=None, help="Override data/processed/points_to_pounds directory")
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

    # Derive root/results from cfg.processed (no cfg.project_root in your Config)
    project_root = cfg.processed.parent.parent
    results_dir = project_root / "results"

    did_path = Path(args.did) if args.did else (results_dir / "proxy2_injury_did.parquet")
    points_dir = Path(args.points_dir) if args.points_dir else (cfg.processed / "points_to_pounds")

    out_csv = Path(args.out_csv) if args.out_csv else (results_dir / "proxy2_injury_did_points_gbp.csv")
    out_parquet = Path(args.out_parquet) if args.out_parquet else (results_dir / "proxy2_injury_did_points_gbp.parquet")

    logger.info("Reading DiD from:       %s", did_path)
    logger.info("Reading points-dir:     %s", points_dir)
    logger.info("Writing output CSV to:  %s", out_csv)
    logger.info("Writing output PQ to:   %s", out_parquet)

    did, player_key = load_did_results(did_path, logger)
    did_points = add_points_interpretation(did)

    mapping = load_points_to_pounds_all_seasons(points_dir, logger)
    did_full = add_money_interpretation(did_points, mapping, logger)

    # Stable column order (keep player id/name first)
    cols_front = [player_key, "team_id", "season"]
    cols_rest = [c for c in did_full.columns if c not in cols_front]
    did_full = did_full[cols_front + cols_rest].copy()

    if args.dry_run:
        logger.info("Dry-run complete. Output not written. shape=%s", did_full.shape)
        print(f"✅ dry-run complete | shape={did_full.shape} | output NOT written")
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    did_full.to_csv(out_csv, index=False)
    did_full.to_parquet(out_parquet, index=False)

    logger.info("Wrote outputs: csv=%s parquet=%s shape=%s", out_csv, out_parquet, did_full.shape)
    print(f"✅ Saved points+£ proxy | shape={did_full.shape}")
    print(f"   - {out_parquet}")
    print(f"   - {out_csv}")


if __name__ == "__main__":
    main()
