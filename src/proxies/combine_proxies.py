"""
Combine proxy datasets into one player–team–season panel.

Why this script?:
- Downstream analysis/plots should depend on a single merged dataset.
- Coverage differs by proxy (outer merge keeps rows that exist in only one proxy).

Inputs (defaults):
- results/proxy1_rotation_elasticity.csv
- results/proxy2_injury_final_named.csv

Output (default):
- results/proxies_combined.csv

Robustness:
- Injury proxy may store Understat numeric IDs as either:
    - player_id (preferred), or
    - understat_player_id (legacy / intermediate)
- If both exist, player_id is used.
"""

from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.validation.checks import assert_non_empty, require_columns


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Combine Proxy 1 (rotation) and Proxy 2 (injury) into one dataset.")
    p.add_argument("--rotation", type=str, default=None, help="Path to proxy1_rotation_elasticity.csv")
    p.add_argument("--injury", type=str, default=None, help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--out", type=str, default=None, help="Output path for proxies_combined.csv")
    p.add_argument("--dry-run", action="store_true", help="Run full load/merge/validation but do not write output")
    return p.parse_args()


# ---------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------
def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def load_rotation(path: Path) -> pd.DataFrame:
    rot = pd.read_csv(path)
    rot = _normalize_cols(rot)

    # Required merge keys
    require_columns(rot, ["player_id", "team_id", "season"], "rotation_proxy")

    rot["player_id"] = pd.to_numeric(rot["player_id"], errors="coerce").astype("Int64")
    rot["season"] = pd.to_numeric(rot["season"], errors="coerce").astype("Int64")
    rot["team_id"] = rot["team_id"].astype(str).str.strip()
    if "player_name" in rot.columns:
        rot["player_name"] = rot["player_name"].astype(str).str.strip()

    return rot


def load_injury(path: Path) -> pd.DataFrame:
    inj = pd.read_csv(path)
    inj = _normalize_cols(inj)

    # Accept common variants and standardise to: player_id, team_id, season
    # --- player_id ---
    if "player_id" in inj.columns:
        pass
    elif "understat_player_id" in inj.columns:
        inj = inj.rename(columns={"understat_player_id": "player_id"})
    else:
        # Keep file readable: show columns
        raise ValueError(
            "[injury_proxy] Missing player identifier. Expected 'player_id' or 'understat_player_id'. "
            f"Columns: {inj.columns.tolist()}"
        )

    # --- team_id ---
    if "team_id" not in inj.columns and "Team" in inj.columns:
        inj = inj.rename(columns={"Team": "team_id"})

    # --- season ---
    if "season" not in inj.columns and "Season" in inj.columns:
        inj = inj.rename(columns={"Season": "season"})

    require_columns(inj, ["player_id", "team_id", "season"], "injury_proxy")

    inj["player_id"] = pd.to_numeric(inj["player_id"], errors="coerce").astype("Int64")
    inj["season"] = pd.to_numeric(inj["season"], errors="coerce").astype("Int64")
    inj["team_id"] = inj["team_id"].astype(str).str.strip()

    if "player_name" in inj.columns:
        inj["player_name"] = inj["player_name"].astype(str).str.strip()

    return inj


def _assert_no_duplicate_keys(df: pd.DataFrame, keys: list[str], name: str) -> None:
    """
    Fail fast on duplicate merge keys (for non-missing keys only).

    Why:
    - Duplicate keys cause many-to-many merges and silently inflate row counts.
    """
    require_columns(df, keys, name=name)
    df_nn = df.dropna(subset=keys)
    dup = int(df_nn.duplicated(keys).sum())
    if dup > 0:
        example = df_nn.loc[df_nn.duplicated(keys, keep=False), keys].head(10)
        raise ValueError(f"[{name}] Found {dup} duplicate rows on keys={keys}. Example:\n{example}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    cfg = Config.load()
    logger = setup_logger("combine_proxies", cfg.logs, "combine_proxies.log")
    meta_path = write_run_metadata(cfg.metadata, "combine_proxies", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    # Resolve paths robustly
    root = Path(__file__).resolve().parents[2]
    results_dir = getattr(cfg, "results", None) or (root / "results")
    results_dir.mkdir(parents=True, exist_ok=True)

    rot_path = Path(args.rotation) if args.rotation else (results_dir / "proxy1_rotation_elasticity.csv")
    inj_path = Path(args.injury) if args.injury else (results_dir / "proxy2_injury_final_named.csv")
    out_path = Path(args.out) if args.out else (results_dir / "proxies_combined.csv")

    logger.info("Loading rotation proxy from: %s", rot_path)
    logger.info("Loading injury proxy from:   %s", inj_path)
    logger.info("Writing combined output to:  %s", out_path)

    if not rot_path.exists():
        raise FileNotFoundError(f"Rotation proxy not found: {rot_path}")
    if not inj_path.exists():
        raise FileNotFoundError(f"Injury proxy not found: {inj_path}")

    rot = load_rotation(rot_path)
    inj = load_injury(inj_path)

    assert_non_empty(rot, "rotation_proxy")
    assert_non_empty(inj, "injury_proxy")

    # Protect against merge explosions
    _assert_no_duplicate_keys(rot, ["player_id", "season", "team_id"], "rotation_proxy")
    _assert_no_duplicate_keys(inj, ["player_id", "season", "team_id"], "injury_proxy")

    # Keep a stable subset of columns (but don’t crash if some are missing)
    rot_keep = [
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
    ]
    rot_keep = [c for c in rot_keep if c in rot.columns]
    rot = rot[rot_keep].copy()

    inj_keep = [
        "player_id",
        "player_name",
        "team_id",
        "season",
        "beta_unavailable",
        "xpts_per_match_present",
        "xpts_season_total",
        "value_gbp_season_total",
    ]
    inj_keep = [c for c in inj_keep if c in inj.columns]
    inj = inj[inj_keep].copy()

    # Outer merge to keep unmatched rows (coverage differs)
    combined = rot.merge(
        inj,
        on=["player_id", "season", "team_id"],
        how="outer",
        suffixes=("_rot", "_inj"),
    )
    assert_non_empty(combined, "combined_proxies")

    # Consolidate player_name if both sides present
    if "player_name_rot" in combined.columns and "player_name_inj" in combined.columns:
        combined["player_name"] = combined["player_name_rot"].fillna(combined["player_name_inj"])
        combined = combined.drop(columns=["player_name_rot", "player_name_inj"])
    elif "player_name_rot" in combined.columns:
        combined = combined.rename(columns={"player_name_rot": "player_name"})
    elif "player_name_inj" in combined.columns:
        combined = combined.rename(columns={"player_name_inj": "player_name"})

    # Coverage flags
    combined["has_rotation"] = combined["rotation_elasticity"].notna() if "rotation_elasticity" in combined.columns else False
    combined["has_injury"] = combined["xpts_season_total"].notna() if "xpts_season_total" in combined.columns else False

    # Convenience alias used elsewhere
    if "xpts_season_total" in combined.columns and "inj_xpts" not in combined.columns:
        combined["inj_xpts"] = combined["xpts_season_total"]

    # Stable sort for deterministic output
    sort_cols = [c for c in ["season", "team_id", "player_name", "player_id"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols).reset_index(drop=True)

    logger.info(
        "Combined shape=%s | has_rotation=%d | has_injury=%d | both=%d",
        combined.shape,
        int(combined["has_rotation"].sum()) if "has_rotation" in combined.columns else 0,
        int(combined["has_injury"].sum()) if "has_injury" in combined.columns else 0,
        int((combined["has_rotation"] & combined["has_injury"]).sum()) if {"has_rotation", "has_injury"}.issubset(combined.columns) else 0,
    )

    if args.dry_run:
        print(f"✅ dry-run complete | combined shape={combined.shape} | output NOT written")
        print(combined.head(10).to_string(index=False))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(combined, out_path, index=False)

    print(f"✅ Saved combined proxies to {out_path}")
    print(f"Rows: {len(combined)} | Distinct teams: {combined['team_id'].nunique() if 'team_id' in combined.columns else 'NA'}")


if __name__ == "__main__":
    main()
