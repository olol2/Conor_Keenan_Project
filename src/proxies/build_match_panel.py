# src/build_match_panel.py
""" This script takes raw match results with betting odds and builds a
team–match panel dataset with expected points based on implied probabilities
from the odds.

"""
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]

RAW_RESULTS_DIR = ROOT_DIR / "data" / "raw" / "Odds" / "results"
OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "matches"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def season_label_from_folder(folder_name: str) -> str:
    """
    '1920' -> '2019-2020'
    '2021' -> '2020-2021'
    '2122' -> '2021-2022'
    etc.
    """
    start_short = int(folder_name[:2])   # e.g. 19
    end_short = int(folder_name[2:])     # e.g. 20
    start_full = 2000 + start_short      # 2019
    end_full = 2000 + end_short          # 2020
    return f"{start_full}-{end_full}"


def compute_probs_from_odds(df: pd.DataFrame,
                            col_h: str,
                            col_d: str,
                            col_a: str) -> pd.DataFrame:
    """Convert 1X2 odds into implied probabilities (normalised)."""
    # basic inverse-odds, then renormalise to sum to 1
    inv_h = 1.0 / df[col_h].astype(float)
    inv_d = 1.0 / df[col_d].astype(float)
    inv_a = 1.0 / df[col_a].astype(float)
    total = inv_h + inv_d + inv_a

    df["p_home"] = inv_h / total
    df["p_draw"] = inv_d / total
    df["p_away"] = inv_a / total
    return df


def build_team_match_rows(df_season: pd.DataFrame, season_label: str) -> pd.DataFrame:
    """Return long-form team–match panel for one season."""

    # Parse date
    if "Date" not in df_season.columns:
        raise ValueError("Expected a 'Date' column in E0.csv")

    df = df_season.copy()
    df["Season"] = season_label
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # Choose a set of closing odds columns – Bet365 is common
    # adjust if your file uses different names
    for prefix in ["B365", "PS", "Max", "Avg"]:
        h, d, a = f"{prefix}H", f"{prefix}D", f"{prefix}A"
        if {h, d, a}.issubset(df.columns):
            odds_cols = (h, d, a)
            break
    else:
        raise ValueError(
            "Could not find any known odds columns (e.g. B365H/B365D/B365A) "
            f"in columns: {list(df.columns)}"
        )

    df = compute_probs_from_odds(df, *odds_cols)

    # Expected points per side
    df["xPts_home"] = 3 * df["p_home"] + 1 * df["p_draw"]
    df["xPts_away"] = 3 * df["p_away"] + 1 * df["p_draw"]

    # Actual points
    def pts_home(result: str) -> int:
        if result == "H":
            return 3
        if result == "D":
            return 1
        return 0

    def pts_away(result: str) -> int:
        if result == "A":
            return 3
        if result == "D":
            return 1
        return 0

    df["Pts_home"] = df["FTR"].map(pts_home)
    df["Pts_away"] = df["FTR"].map(pts_away)

    # Make a simple match id within season
    df = df.reset_index(drop=True)
    df["MatchID"] = df.index + 1

    # Long form: one row per team–match
    home_rows = pd.DataFrame(
        {
            "Season": df["Season"],
            "MatchID": df["MatchID"],
            "Date": df["Date"],
            "Team": df["HomeTeam"],
            "Opponent": df["AwayTeam"],
            "is_home": True,
            "goals_for": df["FTHG"],
            "goals_against": df["FTAG"],
            "result": df["FTR"],
            "Pts": df["Pts_home"],
            "xPts": df["xPts_home"],
        }
    )

    away_rows = pd.DataFrame(
        {
            "Season": df["Season"],
            "MatchID": df["MatchID"],
            "Date": df["Date"],
            "Team": df["AwayTeam"],
            "Opponent": df["HomeTeam"],
            "is_home": False,
            "goals_for": df["FTAG"],
            "goals_against": df["FTHG"],
            "result": df["FTR"],
            "Pts": df["Pts_away"],
            "xPts": df["xPts_away"],
        }
    )

    team_matches = pd.concat([home_rows, away_rows], ignore_index=True)
    team_matches.sort_values(["Date", "MatchID", "is_home"], inplace=True)

    return team_matches


def main():
    all_seasons = []

    for season_dir in sorted(RAW_RESULTS_DIR.iterdir()):
        if not season_dir.is_dir():
            continue

        csv_path = season_dir / "E0.csv"
        if not csv_path.exists():
            print(f"Skipping {season_dir}, no E0.csv found")
            continue

        season_code = season_dir.name  # e.g. '1920'
        season_label = season_label_from_folder(season_code)

        print(f"Building match panel for {season_label} from {csv_path}")
        df_season = pd.read_csv(csv_path)

        team_matches = build_team_match_rows(df_season, season_label)

        out_path = OUTPUT_DIR / f"matches_{season_label}.csv"
        team_matches.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

        all_seasons.append(team_matches)

    if all_seasons:
        panel = pd.concat(all_seasons, ignore_index=True)
        out_all = OUTPUT_DIR / "matches_all_seasons.csv"
        panel.to_csv(out_all, index=False)
        print(f"Saved combined panel to {out_all}")


if __name__ == "__main__":
    main()
