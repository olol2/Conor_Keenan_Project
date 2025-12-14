# src/analysis/fig_proxy2_injury.py

from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import pandas as pd

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata


# ---------------------------------------------------------------------
# Defaults / Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
DEFAULT_INJ_FILE = RESULTS_DIR / "proxy2_injury_final_named.csv"
DEFAULT_FIG_DIR = RESULTS_DIR / "figures"


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------

def load_injury(path: Path) -> pd.DataFrame:
    """Load final injury proxy and normalise key column names."""
    if not path.exists():
        raise FileNotFoundError(f"Injury proxy not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Unified names
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df = df.rename(columns={"xpts_season_total": "inj_xpts"})
    if "inj_gbp" not in df.columns and "value_gbp_season_total" in df.columns:
        df = df.rename(columns={"value_gbp_season_total": "inj_gbp"})

    # Basic typing
    if "season" in df.columns:
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    if "player_name" in df.columns:
        df["player_name"] = df["player_name"].astype(str)
    if "team_id" in df.columns:
        df["team_id"] = df["team_id"].astype(str)

    # Ensure numeric metrics if present
    for c in ["inj_xpts", "inj_gbp"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ---------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------

def plot_topN_injury_players(df: pd.DataFrame, fig_dir: Path, top_n: int = 10) -> Path | None:
    """Top N player-seasons by season injury impact in xPts."""
    if "inj_xpts" not in df.columns:
        return None

    top = (
        df.dropna(subset=["inj_xpts"])
          .sort_values("inj_xpts", ascending=False)
          .head(top_n)
    )
    if top.empty:
        return None

    labels = [f"{row.player_name} ({row.team_id} {int(row.season)})" for _, row in top.iterrows()]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top["inj_xpts"][::-1])
    plt.yticks(range(len(top)), labels[::-1])
    plt.xlabel("Season injury impact in xPts")
    plt.title(f"Top {top_n} player-seasons by injury impact (xPts)")
    plt.tight_layout()

    out_path = fig_dir / "proxy2_top10_injury_xpts.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_topN_club_injury_bill(df: pd.DataFrame, fig_dir: Path, top_n: int = 10) -> Path | None:
    """
    Sum injury impact per team-season and plot top N club-seasons.

    Uses 'inj_gbp' if available, else 'inj_xpts'.
    """
    metric = "inj_gbp" if "inj_gbp" in df.columns else "inj_xpts"
    if metric not in df.columns:
        return None

    club = df.groupby(["team_id", "season"], as_index=False)[metric].sum()
    club = club.dropna(subset=[metric])

    top = club.sort_values(metric, ascending=False).head(top_n)
    if top.empty:
        return None

    labels = [f"{row.team_id} {int(row.season)}" for _, row in top.iterrows()]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top)), top[metric][::-1])
    plt.yticks(range(len(top)), labels[::-1])

    if metric == "inj_gbp":
        plt.xlabel("Total injury value in £ (expected)")
        plt.title(f"Top {top_n} club-seasons by total injury value (£ proxy)")
    else:
        plt.xlabel("Total injury impact in xPts")
        plt.title(f"Top {top_n} club-seasons by total injury impact (xPts)")

    plt.tight_layout()

    out_path = fig_dir / "proxy2_club_injury_bill.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


# ---------------------------------------------------------------------
# Main (CLI)
# ---------------------------------------------------------------------

def main() -> None:
    cfg = Config.load()
    logger = setup_logger("fig_proxy2_injury", cfg.logs, "fig_proxy2_injury.log")
    meta_path = write_run_metadata(cfg.metadata, "fig_proxy2_injury")
    logger.info("Run metadata saved to: %s", meta_path)

    p = argparse.ArgumentParser(description="Create figures for Proxy 2 (injury) outputs.")
    p.add_argument("--injury-file", type=Path, default=DEFAULT_INJ_FILE,
                   help="Path to proxy2_injury_final_named.csv")
    p.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR,
                   help="Directory to write figures into")
    p.add_argument("--top-n", type=int, default=10, help="Top N for bar charts")
    p.add_argument("--dry-run", action="store_true", help="Load + validate only; do not write figures")
    args = p.parse_args()

    args.fig_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Reading injury proxy from: %s", args.injury_file)
    logger.info("Writing figures to:       %s", args.fig_dir)
    logger.info("Top N:                    %s", args.top_n)

    df = load_injury(args.injury_file)
    logger.info("Loaded injury proxy: shape=%s cols=%s", df.shape, len(df.columns))

    # Basic “tests”
    needed_any = {"inj_xpts", "inj_gbp"}
    if not (needed_any & set(df.columns)):
        raise ValueError("Injury file has neither inj_xpts nor inj_gbp (nor their source columns).")

    if args.dry_run:
        print(f"Loaded {len(df)} player-seasons from {args.injury_file}")
        print("✅ dry-run complete | figures NOT written")
        return

    out1 = plot_topN_injury_players(df, args.fig_dir, top_n=args.top_n)
    out2 = plot_topN_club_injury_bill(df, args.fig_dir, top_n=args.top_n)

    if out1:
        logger.info("Saved %s", out1)
        print(f"Saved {out1}")
    else:
        logger.warning("Top player injury plot not produced (missing data).")
        print("Skipped top player injury plot (missing inj_xpts).")

    if out2:
        logger.info("Saved %s", out2)
        print(f"Saved {out2}")
    else:
        logger.warning("Club injury bill plot not produced (missing data).")
        print("Skipped club injury bill plot (missing inj_xpts/inj_gbp).")

    print(f"✅ wrote figures to: {args.fig_dir}")


if __name__ == "__main__":
    main()
