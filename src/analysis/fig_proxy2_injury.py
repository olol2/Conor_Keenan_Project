"""
Creates summary figures for Proxy 2 (Injury DiD interpretation).

Input:
  results/proxy2_injury_final_named.csv

Output:
  results/figures/
    - proxy2_top_injury_xpts.png
    - proxy2_club_injury_bill.png

What these plots show:
1) Top player-seasons by injury impact (in season xPts impact).
2) Top club-seasons by total injury bill (sum across players), in £ if available,
   otherwise in xPts.

Notes:
- This script is deterministic: it reads the already-built injury proxy CSV and writes figures.
"""

from __future__ import annotations
from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Defaults / Paths (root-relative, independent of Config internals)
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
DEFAULT_INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"
DEFAULT_FIG_DIR = RESULTS_DIR / "figures"


# ---------------------------------------------------------------------
# Loading + normalization
# ---------------------------------------------------------------------

def load_injury(path: Path) -> pd.DataFrame:
    """
    Load final injury proxy and normalize metric column names.

    Normalized metrics:
      - inj_xpts : season injury impact in xPts
      - inj_gbp  : season injury impact in £

    Accepts older/newer schemas by mapping:
      xpts_season_total         -> inj_xpts
      value_gbp_season_total    -> inj_gbp
    """
    if not path.exists():
        raise FileNotFoundError(f"Injury proxy not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Normalize names
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df = df.rename(columns={"xpts_season_total": "inj_xpts"})
    if "inj_gbp" not in df.columns and "value_gbp_season_total" in df.columns:
        df = df.rename(columns={"value_gbp_season_total": "inj_gbp"})

    # Basic typing
    if "season" in df.columns:
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    if "player_name" in df.columns:
        df["player_name"] = df["player_name"].astype(str).str.strip()
    if "team_id" in df.columns:
        df["team_id"] = df["team_id"].astype(str).str.strip()

    for c in ["inj_xpts", "inj_gbp"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------

def _save(fig_dir: Path, fname: str, logger=None) -> Path:
    """Tight layout + save figure consistently."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_path = fig_dir / fname
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    if logger:
        logger.info("Saved figure: %s", out_path)
    print(f"Saved {out_path}")
    return out_path


def _fmt_season(x) -> str:
    """Format nullable Int64 seasons safely for labels."""
    try:
        if pd.isna(x):
            return "NA"
        return str(int(x))
    except Exception:
        return "NA"


# ---------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------

def plot_topN_injury_players(df: pd.DataFrame, fig_dir: Path, top_n: int, logger=None) -> Path | None:
    """
    Top-N player-seasons by season injury impact in xPts (inj_xpts).
    Higher inj_xpts implies larger season-level impact in xPts.
    """
    if "inj_xpts" not in df.columns:
        if logger:
            logger.warning("Column inj_xpts missing; skipping player top-N plot.")
        return None

    sub = df.dropna(subset=["inj_xpts"]).copy()
    if sub.empty:
        if logger:
            logger.warning("No non-missing inj_xpts rows; skipping player top-N plot.")
        return None

    # Prefer having player_name/team_id; if missing, still plot with placeholders
    if "player_name" not in sub.columns:
        sub["player_name"] = "UNKNOWN"
    if "team_id" not in sub.columns:
        sub["team_id"] = "UNKNOWN"
    if "season" not in sub.columns:
        sub["season"] = pd.NA

    top = sub.sort_values("inj_xpts", ascending=False).head(top_n)

    labels = [
        f"{row.player_name} ({row.team_id} {_fmt_season(row.season)})"
        for _, row in top.iterrows()
    ]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["inj_xpts"].iloc[::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Season injury impact in xPts (inj_xpts)")
    plt.title(f"Top {top_n} player-seasons by injury impact (xPts)")

    return _save(fig_dir, "proxy2_top_injury_xpts.png", logger=logger)


def plot_topN_club_injury_bill(df: pd.DataFrame, fig_dir: Path, top_n: int, logger=None) -> Path | None:
    """
    Sum injury impact per team-season and plot the top-N club-seasons.

    Uses:
      - inj_gbp if available (preferred for interpretability),
      - otherwise inj_xpts.
    """
    metric = "inj_gbp" if "inj_gbp" in df.columns else ("inj_xpts" if "inj_xpts" in df.columns else None)
    if metric is None:
        if logger:
            logger.warning("Neither inj_gbp nor inj_xpts exists; skipping club bill plot.")
        return None

    if "team_id" not in df.columns or "season" not in df.columns:
        if logger:
            logger.warning("team_id/season missing; cannot build club-season totals. Skipping.")
        return None

    club = (
        df.groupby(["team_id", "season"], as_index=False)[metric]
        .sum()
        .dropna(subset=[metric])
    )

    if club.empty:
        if logger:
            logger.warning("Club-season aggregation empty; skipping club bill plot.")
        return None

    top = club.sort_values(metric, ascending=False).head(top_n)

    labels = [f"{row.team_id} {_fmt_season(row.season)}" for _, row in top.iterrows()]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top[metric].iloc[::-1])
    plt.yticks(range(len(top)), labels[::-1])

    if metric == "inj_gbp":
        plt.xlabel("Total injury value in £ (expected)")
        plt.title(f"Top {top_n} club-seasons by total injury value (£ proxy)")
    else:
        plt.xlabel("Total injury impact in xPts")
        plt.title(f"Top {top_n} club-seasons by total injury impact (xPts)")

    return _save(fig_dir, "proxy2_club_injury_bill.png", logger=logger)


# ---------------------------------------------------------------------
# CLI / Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create figures for Proxy 2 (injury) outputs.")
    p.add_argument("--injury-file", type=Path, default=DEFAULT_INJ_FILE,
                   help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR,
                   help="Directory to write figures into")
    p.add_argument("--top-n", type=int, default=10, help="Top N for bar charts")
    p.add_argument("--dry-run", action="store_true", help="Load + validate only; do not write figures")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = Config.load()
    logger = setup_logger("fig_proxy2_injury", cfg.logs, "fig_proxy2_injury.log")
    meta_path = write_run_metadata(cfg.metadata, "fig_proxy2_injury", extra={"dry_run": bool(args.dry_run)})
    logger.info("Run metadata saved to: %s", meta_path)

    logger.info("Reading injury proxy from: %s", args.injury_file)
    logger.info("Writing figures to:       %s", args.fig_dir)
    logger.info("Top N:                    %s", args.top_n)
    logger.info("Dry-run:                  %s", args.dry_run)

    df = load_injury(args.injury_file)
    logger.info("Loaded injury proxy: shape=%s cols=%s", df.shape, len(df.columns))

    # Basic validation: at least one of the injury metrics should exist
    if ("inj_xpts" not in df.columns) and ("inj_gbp" not in df.columns):
        raise ValueError(
            "Injury file has neither inj_xpts nor inj_gbp. "
            "Expected inj_xpts or xpts_season_total; inj_gbp or value_gbp_season_total."
        )

    if args.dry_run:
        print(f"Loaded {len(df)} player-seasons from {args.injury_file}")
        print("✅ dry-run complete | figures NOT written")
        return

    out1 = plot_topN_injury_players(df, args.fig_dir, top_n=args.top_n, logger=logger)
    out2 = plot_topN_club_injury_bill(df, args.fig_dir, top_n=args.top_n, logger=logger)

    if out1 is None:
        print("Skipped top player injury plot (missing or empty inj_xpts).")
    if out2 is None:
        print("Skipped club injury bill plot (missing/empty inj_xpts & inj_gbp or missing team/season).")

    print(f"✅ wrote figures to: {args.fig_dir}")


if __name__ == "__main__":
    main()
