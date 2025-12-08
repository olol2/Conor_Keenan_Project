# src/build_match_panel.py
"""
Build a team–match panel dataset with expected points using the
processed odds_master.csv file.

Input:
  data/processed/odds/odds_master.csv

Output:
  data/processed/matches/matches_all_seasons.csv
"""

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]

ODDS_MASTER_PATH = ROOT_DIR / "data" / "processed" / "odds" / "odds_master.csv"
OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "matches"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_ALL = OUTPUT_DIR / "matches_all_seasons.csv"


def compute_probs_from_odds(df: pd.DataFrame,
                            col_h: str,
                            col_d: str,
                            col_a: str) -> pd.DataFrame:
    """Convert 1X2 odds into implied probabilities (normalised)."""
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

    if "Date" not in df_season.columns:
        raise ValueError("Expected a 'Date' column")

    df = df_season.copy()
    df["Season"] = season_label
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # Choose odds columns – in odds_master we always have B365H/D/A
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

    # MatchID within season
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
    team_matches.sort_values(["Season", "Date", "MatchID", "is_home"], inplace=True)

    return team_matches


def main() -> None:
    # Read the processed odds master
    df_all = pd.read_csv(ODDS_MASTER_PATH)

    if "match_date" not in df_all.columns:
        raise KeyError("Expected 'match_date' column in odds_master.csv")
    df_all["match_date"] = pd.to_datetime(df_all["match_date"], errors="coerce")

    if "season" not in df_all.columns:
        raise KeyError("Expected 'season' column in odds_master.csv")

    all_seasons = []

    # Group by season to keep MatchID separate per season
    for season_label, df_season_raw in df_all.groupby("season"):
        df_season = df_season_raw.rename(
            columns={
                "match_date": "Date",
                "home_team": "HomeTeam",
                "away_team": "AwayTeam",
            }
        ).copy()

        print(f"Building match panel for {season_label} from odds_master...")
        team_matches = build_team_match_rows(df_season, season_label)
        all_seasons.append(team_matches)

    if not all_seasons:
        raise RuntimeError("No seasons found in odds_master.csv")

    panel = pd.concat(all_seasons, ignore_index=True)
    panel.to_csv(OUT_ALL, index=False)
    print(f"Saved combined panel to {OUT_ALL} with shape {panel.shape}")


if __name__ == "__main__":
    main()
