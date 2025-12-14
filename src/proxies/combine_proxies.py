# src/analysis/combine_proxies.py
"""
Combine proxy datasets into one player-season-team panel.

Why this script exists:
- Downstream analysis/plots should depend on a single, merged dataset.
- A single file also makes the pipeline easier to reproduce and grade.

Inputs (expected in results/):
- proxy1_rotation_elasticity.csv
- proxy2_injury_final_named.csv

Output (written to results/):
- proxies_combined.csv
"""

from __future__ import annotations

import pandas as pd

from src.utils.config import Config
from src.utils.io import atomic_write_csv
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.validation.checks import assert_non_empty, require_columns


def load_rotation(path: str) -> pd.DataFrame:
    """
    Load rotation proxy and standardise merge keys.

    Why:
    - Standardising dtypes here avoids silent merge issues later (e.g., '11' vs 11).
    """
    rot = pd.read_csv(path)

    rot["player_id"] = pd.to_numeric(rot["player_id"], errors="coerce").astype("Int64")
    rot["season"] = pd.to_numeric(rot["season"], errors="coerce").astype("Int64")
    rot["player_name"] = rot["player_name"].astype(str)
    rot["team_id"] = rot["team_id"].astype(str)

    return rot


def load_injury(path: str) -> pd.DataFrame:
    """
    Load final injury proxy and standardise merge keys.

    Why:
    - Ensures the merge keys align with the rotation dataset.
    - Some versions of the injury file may not include every column, so we
      standardise what we can and validate later.
    """
    inj = pd.read_csv(path)

    inj["player_id"] = pd.to_numeric(inj["player_id"], errors="coerce").astype("Int64")
    inj["season"] = pd.to_numeric(inj["season"], errors="coerce").astype("Int64")
    if "player_name" in inj.columns:
        inj["player_name"] = inj["player_name"].astype(str)
    inj["team_id"] = inj["team_id"].astype(str)

    return inj


def _assert_no_duplicate_keys(df: pd.DataFrame, keys: list[str], name: str) -> None:
    """
    Fail fast on duplicate merge keys (for non-missing keys only).

    Why:
    - Duplicate keys create many-to-many merges, which silently inflate row counts.
    - We drop rows with missing keys in this check because missing IDs are sometimes
      unavoidable (scraped data gaps), and treating all missing IDs as duplicates
      can cause false positives.
    """
    require_columns(df, keys, name=name)

    df_nn = df.dropna(subset=keys)
    dup = df_nn.duplicated(keys).sum()
    if dup > 0:
        raise ValueError(
            f"[{name}] Found {dup} duplicate rows on merge keys {keys} (non-missing only)."
        )


def main() -> None:
    cfg = Config.load()
    logger = setup_logger("combine_proxies", cfg.logs, "combine_proxies.log")

    # Record execution context for reproducibility/debugging.
    meta_path = write_run_metadata(
        cfg.metadata,
        "combine_proxies",
        extra={
            "season_min": cfg.season_min,
            "season_max": cfg.season_max,
        },
    )
    logger.info("Run metadata saved to: %s", meta_path)

    rot_path = cfg.results / "proxy1_rotation_elasticity.csv"
    inj_path = cfg.results / "proxy2_injury_final_named.csv"
    out_path = cfg.results / "proxies_combined.csv"

    logger.info("Loading rotation proxy from: %s", rot_path)
    logger.info("Loading injury proxy from:   %s", inj_path)

    rot = load_rotation(str(rot_path))
    inj = load_injury(str(inj_path))

    # --- Validate inputs early so failures are readable and localised ---
    assert_non_empty(rot, "rotation_proxy")
    assert_non_empty(inj, "injury_proxy")

    require_columns(rot, ["player_id", "season", "team_id", "player_name"], "rotation_proxy")
    require_columns(inj, ["player_id", "season", "team_id"], "injury_proxy")  # name may be missing

    # Protect against silent many-to-many merges.
    _assert_no_duplicate_keys(rot, ["player_id", "season", "team_id"], "rotation_proxy")
    _assert_no_duplicate_keys(inj, ["player_id", "season", "team_id"], "injury_proxy")

    logger.info("Rotation proxy shape: %s", rot.shape)
    logger.info("Injury proxy shape:   %s", inj.shape)

    # Columns to keep from each side (keeps merged output stable across runs).
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
    rot = rot[rot_keep]

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
    inj_keep = [c for c in inj_keep if c in inj.columns]  # keep only columns present
    inj = inj[inj_keep]

    # --- Merge ---
    # Why outer merge:
    # - Some player-seasons exist only in one proxy (coverage differs),
    #   and we want to keep them for later inspection and robustness checks.
    combined = rot.merge(
        inj,
        on=["player_id", "season", "team_id"],
        how="outer",
        suffixes=("_rot", "_inj"),
    )
    assert_non_empty(combined, "combined_proxies")

    # Build a single player_name column (prefer rotation name, fall back to injury).
    if "player_name_rot" in combined.columns and "player_name_inj" in combined.columns:
        combined["player_name"] = combined["player_name_rot"].fillna(combined["player_name_inj"])
    elif "player_name_rot" in combined.columns:
        combined["player_name"] = combined["player_name_rot"]
    elif "player_name_inj" in combined.columns:
        combined["player_name"] = combined["player_name_inj"]

    # Drop intermediate name columns to keep a clean output schema.
    for col in ["player_name_rot", "player_name_inj"]:
        if col in combined.columns:
            combined = combined.drop(columns=col)

    # Convenience flags used in plots/summaries.
    combined["has_rotation"] = ~combined.get("rotation_elasticity").isna()
    combined["has_injury"] = ~combined.get("xpts_season_total").isna()

    # Now that flags exist, we can safely log coverage stats.
    logger.info(
        "Coverage: has_rotation=%d, has_injury=%d, both=%d",
        int(combined["has_rotation"].sum()),
        int(combined["has_injury"].sum()),
        int((combined["has_rotation"] & combined["has_injury"]).sum()),
    )

    # Optional: standard name for plotting / compatibility with existing notebooks/scripts.
    if "xpts_season_total" in combined.columns and "inj_xpts" not in combined.columns:
        combined["inj_xpts"] = combined["xpts_season_total"]

    # Nice ordering for inspection/debugging.
    combined = combined.sort_values(["season", "team_id", "player_name"]).reset_index(drop=True)

    # Atomic save avoids partial CSVs if run is interrupted.
    atomic_write_csv(combined, out_path, index=False)

    logger.info("Saved combined proxies to: %s", out_path)
    logger.info("Rows: %d | Distinct teams: %d", len(combined), combined["team_id"].nunique())
    logger.info("Head (first 5 rows):\n%s", combined.head().to_string(index=False))

    print(f"✅ Saved combined proxies to {out_path}")
    print(f"Rows: {len(combined)} | Distinct teams: {combined['team_id'].nunique()}")


if __name__ == "__main__":
    main()
