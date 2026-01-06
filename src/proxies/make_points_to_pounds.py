"""
Compute an approximate value of Premier League points in GBP using
final league standings and total prize money.

Method (per season):
  pounds_per_point = total_prize_money_gbp / total_league_points

Then create a linear mapping:
  Money_gbp = Points * pounds_per_point

Outputs (default):
  <cfg.processed>/points_to_pounds/points_to_pounds_<season>.csv

Inputs (defaults):
  - <cfg.processed>/standings/standings_*.csv
  - <cfg.raw>/pl_prize_money.csv

Notes:
- This is an approximation intended for interpretability (points → money scale).
- If the merge produces fewer rows than expected, it usually indicates team-name
  mismatches between standings files and the prize money file.
- Standings files sometimes use different team-name columns; this script
  standardises them to 'Team'.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from src.utils.config import Config


def _standardise_standings_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise standings schema to at least:
      Season, Team, Pts

    Accepts common variants:
      - Team column may be named: Team / HomeTeam / Club
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # Season must exist
    if "Season" not in df.columns:
        raise ValueError(f"[standings] Missing 'Season'. Columns: {list(df.columns)}")

    # Team column may have different names in different pipelines
    if "Team" not in df.columns:
        for alt in ["HomeTeam", "Club"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "Team"})
                break

    if "Team" not in df.columns:
        raise ValueError(f"[standings] Missing team column (expected 'Team' or 'HomeTeam' or 'Club'). Columns: {list(df.columns)}")

    if "Pts" not in df.columns:
        raise ValueError(f"[standings] Missing 'Pts'. Columns: {list(df.columns)}")

    # Basic cleaning
    df["Season"] = df["Season"].astype(str).str.strip()
    df["Team"] = df["Team"].astype(str).str.strip()
    df["Pts"] = pd.to_numeric(df["Pts"], errors="coerce")

    return df


def load_standings(standings_dir: Path) -> pd.DataFrame:
    """Load all per-season standings_*.csv into one DataFrame (standardised to Season/Team/Pts)."""
    frames: list[pd.DataFrame] = []

    for path in sorted(standings_dir.glob("standings_*.csv")):
        if "all_seasons" in path.name:
            continue
        frames.append(pd.read_csv(path))

    if not frames:
        raise FileNotFoundError(
            f"No per-season standings_*.csv files found in {standings_dir}. "
            "If your standings are stored elsewhere, pass --standings-dir."
        )

    standings = pd.concat(frames, ignore_index=True)
    standings = _standardise_standings_schema(standings)
    return standings


def parse_args(cfg: Config) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build points-to-pounds mapping from standings + prize money.")
    p.add_argument(
        "--standings-dir",
        type=Path,
        default=cfg.processed / "standings",
        help="Directory with standings_*.csv (default: <cfg.processed>/standings)",
    )
    p.add_argument(
        "--prize-file",
        type=Path,
        default=cfg.raw / "pl_prize_money.csv",
        help="Path to pl_prize_money.csv (default: <cfg.raw>/pl_prize_money.csv)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=cfg.processed / "points_to_pounds",
        help="Output directory (default: <cfg.processed>/points_to_pounds)",
    )
    p.add_argument("--dry-run", action="store_true", help="Compute but do not write outputs")
    return p.parse_args()


def main() -> None:
    cfg = Config.load()
    args = parse_args(cfg)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    standings = load_standings(args.standings_dir)

    if not args.prize_file.exists():
        raise FileNotFoundError(f"Prize money file not found: {args.prize_file}")

    prize = pd.read_csv(args.prize_file)
    prize.columns = [c.strip() for c in prize.columns]

    required_cols = {"Season", "Team", "pl_total_gbp"}
    missing = required_cols - set(prize.columns)
    if missing:
        raise ValueError(
            f"[pl_prize_money.csv] Missing columns: {sorted(missing)}. "
            f"Needs: {sorted(required_cols)}"
        )

    prize["Season"] = prize["Season"].astype(str).str.strip()
    prize["Team"] = prize["Team"].astype(str).str.strip()
    prize["pl_total_gbp"] = pd.to_numeric(prize["pl_total_gbp"], errors="coerce")

    # Merge prize money onto standings
    df = standings.merge(
        prize[["Season", "Team", "pl_total_gbp"]],
        on=["Season", "Team"],
        how="inner",
    )

    if df.empty:
        raise ValueError(
            "Merge produced 0 rows. This usually means team names or Season labels "
            "do not match between standings files and pl_prize_money.csv."
        )

    # Report merge coverage (useful for debugging)
    n_stand = len(standings)
    n_merged = len(df)
    if n_merged < n_stand:
        print(f"[WARN] Merge coverage: {n_merged}/{n_stand} rows matched. Some teams/seasons may be missing in prize file.")

    df = df.rename(columns={"pl_total_gbp": "money_gbp"})

    written = 0
    for season, df_season in df.groupby("Season"):
        total_money = df_season["money_gbp"].sum()
        total_points = df_season["Pts"].sum()

        if pd.isna(total_points) or total_points == 0:
            print(f"[WARN] Skipping {season}: total_points is invalid ({total_points})")
            continue

        pounds_per_point = float(total_money / total_points)
        print(f"{season}: value per point ≈ £{pounds_per_point:,.0f}")

        min_pts = int(df_season["Pts"].min())
        max_pts = int(df_season["Pts"].max())

        mapping = pd.DataFrame(
            {"Season": [season] * (max_pts - min_pts + 1), "Points": list(range(min_pts, max_pts + 1))}
        )
        mapping["Money_gbp"] = mapping["Points"] * pounds_per_point

        out_path = args.out_dir / f"points_to_pounds_{season}.csv"

        if args.dry_run:
            print(f"[dry-run] Would write {out_path} (rows={len(mapping)})")
        else:
            mapping.to_csv(out_path, index=False)
            print(f"[OK] Saved {out_path}")
            written += 1

    if args.dry_run:
        print("[OK] dry-run complete | no files written")
    else:
        print(f"[OK] wrote {written} season mapping files to {args.out_dir}")


if __name__ == "__main__":
    main()
