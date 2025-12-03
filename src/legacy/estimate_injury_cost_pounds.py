# src/estimate_injury_cost_pounds.py
""" This script estimates the cost of injuries in terms of GBP lost
per team-season, based on the estimated points lost due to injuries
and the value of Premier League points in GBP.
It outputs a CSV file mapping team-seasons to estimated GBP lost due to injuries. The csv just adds two columns to data/processed/injury_cost_points.csv
and is stored in data/processed/injury_cost_pounds.csv.
"""

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT_DIR / "data" / "processed"

INJURY_POINTS_FILE = PROC_DIR / "injury_cost_points.csv"
POINTS_TO_POUNDS_DIR = PROC_DIR / "points_to_pounds"
OUT_FILE = PROC_DIR / "injury_cost_pounds.csv"


def load_injury_cost_points() -> pd.DataFrame:
    if not INJURY_POINTS_FILE.exists():
        raise FileNotFoundError(
            f"{INJURY_POINTS_FILE} not found. "
            "Run src/estimate_injury_cost_points.py first."
        )
    df = pd.read_csv(INJURY_POINTS_FILE)
    return df


def load_points_to_pounds() -> pd.DataFrame:
    """
    Load all points_to_pounds_*.csv files and get £ per point for each Season.
    These files are season-level (one row per Season) with columns:
      Season, Points, Money_gbp
    """
    if not POINTS_TO_POUNDS_DIR.exists():
        raise FileNotFoundError(
            f"{POINTS_TO_POUNDS_DIR} not found. "
            "Make sure points_to_pounds.py has been run."
        )

    paths = sorted(POINTS_TO_POUNDS_DIR.glob("points_to_pounds_*.csv"))
    if not paths:
        raise FileNotFoundError(
            f"No points_to_pounds_*.csv files found in {POINTS_TO_POUNDS_DIR}."
        )

    frames = []
    for p in paths:
        df = pd.read_csv(p)
        frames.append(df)

    pp = pd.concat(frames, ignore_index=True)

    cols = {c.lower(): c for c in pp.columns}

    # 1) Try to find an explicit "per point" column
    per_point_col = None
    for cand in ["gbp_per_point", "pounds_per_point", "pl_gbp_per_point", "eur_per_point"]:
        if cand in cols:
            per_point_col = cols[cand]
            break

    # 2) Otherwise compute it from total money and points
    if per_point_col is None:
        # money column candidates
        money_col = None
        for cand in ["pl_total_gbp", "total_gbp", "pl_total_money_gbp", "total_money_gbp", "money_gbp"]:
            if cand in cols:
                money_col = cols[cand]
                break

        # points column candidates
        pts_col = None
        for cand in ["pts", "points", "total_points"]:
            if cand in cols:
                pts_col = cols[cand]
                break

        if money_col is None or pts_col is None:
            raise ValueError(
                "Could not find either an existing '£ per point' column or "
                "both money+points columns in points_to_pounds files. "
                f"Columns available: {list(pp.columns)}"
            )

        pp["gbp_per_point"] = pp[money_col] / pp[pts_col]
        per_point_col = "gbp_per_point"

    # Season-level: keep just Season and gbp_per_point
    out = pp[["Season", per_point_col]].copy()
    out = out.rename(columns={per_point_col: "gbp_per_point"})

    # Ensure one row per Season
    out = out.drop_duplicates(subset=["Season"])
    return out


def main():
    injury = load_injury_cost_points()
    pp = load_points_to_pounds()

    # Merge £ per point onto injury points table by Season only
    merged = injury.merge(
        pp,
        on="Season",
        how="left",
        validate="many_to_one",   # many teams per season, one row per season in pp
    )

    # Check for any missing £ per point
    missing = merged[merged["gbp_per_point"].isna()][["Season", "Team"]]
    if not missing.empty:
        print("WARNING: missing gbp_per_point for these team-seasons:")
        print(missing.to_string(index=False))

    # Compute £ lost due to injuries
    merged["gbp_lost_due_to_injuries"] = (
        merged["points_lost_due_to_injuries"] * merged["gbp_per_point"]
    )

    # Save
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_FILE, index=False)
    print(f"Saved injury cost in £ to {OUT_FILE}")


if __name__ == "__main__":
    main()
