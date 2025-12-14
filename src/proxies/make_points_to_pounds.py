# src/make_points_to_pounds.py
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

"""
Compute an approximate value of Premier League points in GBP based on
final league standings and total prize money.

For each season:
  pounds_per_point = total_money / total_points

Then create a linear mapping:
  Money_gbp = Points * pounds_per_point
and save it to data/processed/points_to_pounds/points_to_pounds_<season>.csv
"""


# ---------- paths ----------
# IMPORTANT: this file lives in /scripts, so parents[1] is the project root
ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_STANDINGS_DIR = ROOT_DIR / "data" / "processed" / "standings"
DEFAULT_PRIZE_FILE = ROOT_DIR / "data" / "raw" / "pl_prize_money.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "points_to_pounds"
# ---------------------------


def load_standings(standings_dir: Path) -> pd.DataFrame:
    """Load all per-season standings_*.csv into one DataFrame."""
    frames = []
    for path in sorted(standings_dir.glob("standings_*.csv")):
        if "all_seasons" in path.name:
            continue
        frames.append(pd.read_csv(path))

    if not frames:
        raise FileNotFoundError(
            f"No per-season standings_*.csv files found in {standings_dir}. "
            "Run make_standings.py first."
        )

    standings = pd.concat(frames, ignore_index=True)
    standings.columns = [c.strip() for c in standings.columns]

    # Ensure required columns exist
    if "Season" not in standings.columns:
        raise ValueError(f"'Season' column not found in standings. Columns: {list(standings.columns)}")
    if "Team" not in standings.columns:
        raise ValueError(f"'Team' column not found in standings. Columns: {list(standings.columns)}")
    if "Pts" not in standings.columns:
        raise ValueError(f"'Pts' column not found in standings. Columns: {list(standings.columns)}")

    # Basic cleaning
    standings["Season"] = standings["Season"].astype(str).str.strip()
    standings["Team"] = standings["Team"].astype(str).str.strip()
    standings["Pts"] = pd.to_numeric(standings["Pts"], errors="coerce")

    return standings


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build points-to-pounds mapping from standings + prize money.")
    p.add_argument("--standings-dir", type=Path, default=DEFAULT_STANDINGS_DIR, help="Directory with standings_*.csv")
    p.add_argument("--prize-file", type=Path, default=DEFAULT_PRIZE_FILE, help="Path to pl_prize_money.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for points_to_pounds_*.csv")
    p.add_argument("--dry-run", action="store_true", help="Compute but do not write outputs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    standings = load_standings(args.standings_dir)

    if not args.prize_file.exists():
        raise FileNotFoundError(f"Prize money file not found: {args.prize_file}")

    prize = pd.read_csv(args.prize_file)
    prize.columns = [c.strip() for c in prize.columns]

    required_cols = {"Season", "Team", "pl_total_gbp"}
    missing = required_cols - set(prize.columns)
    if missing:
        raise ValueError(f"pl_prize_money.csv missing columns: {sorted(missing)}. Needs: {sorted(required_cols)}")

    prize["Season"] = prize["Season"].astype(str).str.strip()
    prize["Team"] = prize["Team"].astype(str).str.strip()
    prize["pl_total_gbp"] = pd.to_numeric(prize["pl_total_gbp"], errors="coerce")

    # Merge money onto standings
    df = standings.merge(
        prize[["Season", "Team", "pl_total_gbp"]],
        on=["Season", "Team"],
        how="inner",
    )

    if df.empty:
        raise ValueError(
            "Merge produced 0 rows. This usually means team names or Season labels "
            "do not match between standings and pl_prize_money.csv."
        )

    # Report merge coverage (useful for debugging)
    n_stand = len(standings)
    n_merged = len(df)
    if n_merged < n_stand:
        print(f"⚠️ Merge coverage: {n_merged}/{n_stand} rows matched. Some teams/seasons may be missing in prize file.")

    df = df.rename(columns={"pl_total_gbp": "money_gbp"})

    # Build season mappings
    written = 0
    for season, df_season in df.groupby("Season"):
        total_money = df_season["money_gbp"].sum()
        total_points = df_season["Pts"].sum()

        if pd.isna(total_points) or total_points == 0:
            print(f"Skipping {season}: total_points is invalid ({total_points})")
            continue

        pounds_per_point = float(total_money / total_points)
        print(f"{season}: value per point ≈ £{pounds_per_point:,.0f}")

        min_pts = int(df_season["Pts"].min())
        max_pts = int(df_season["Pts"].max())

        mapping = pd.DataFrame(
            {
                "Season": [season] * (max_pts - min_pts + 1),
                "Points": list(range(min_pts, max_pts + 1)),
            }
        )
        mapping["Money_gbp"] = mapping["Points"] * pounds_per_point

        out_path = args.out_dir / f"points_to_pounds_{season}.csv"

        if args.dry_run:
            print(f"[dry-run] Would write {out_path} (rows={len(mapping)})")
        else:
            mapping.to_csv(out_path, index=False)
            print(f"Saved {out_path}")
            written += 1

    if args.dry_run:
        print("✅ dry-run complete | no files written")
    else:
        print(f"✅ wrote {written} season mapping files to {args.out_dir}")


if __name__ == "__main__":
    main()
