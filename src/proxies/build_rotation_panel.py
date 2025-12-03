from __future__ import annotations
"""
This script builds a player–team–match injury panel dataset by combining:
  - team–match data with expected points (xPts) and injury counts
  - injury spells per player–team–season
  - Understat per-player match minutes & starting info (if available)
The output is saved as a parquet file in data/processed/panel_injury.parquet. Saved as parquet for efficiency. 
"""

from pathlib import Path

import numpy as np
import pandas as pd

TEAM_NAME_MAP = {
    # Long -> short (canonical)
    "Manchester City": "Man City",
    "Manchester Utd": "Man Utd",           # if it appears
    "Manchester United": "Man Utd",
    "Sheffield United": "Sheffield Utd",
    "Wolverhampton Wanderers": "Wolves",
    "Brighton and Hove Albion": "Brighton",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "West Ham United": "West Ham",
    "Tottenham Hotspur": "Tottenham",
    "Nottingham Forest": "Nottm Forest",   # if your matches use this
    # add more once you see what’s in Understat
}



# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Same matches file you used for injuries – adjust filename if needed
MATCHES_FILE = DATA_PROCESSED / "matches" / "matches_with_injuries_all_seasons.csv"

# Understat per-player match files like understat_player_matches_2019.csv, ...
UNDERSTAT_DIR = ROOT / "data" / "raw" / "understat_player_matches"


# ---------------------------------------------------------------------
# Load matches (team–match with xPts)
# ---------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load team–match data with xPts.

    Expected columns in MATCHES_FILE:
      Season, MatchID, Date, Team, Opponent, is_home, xPts, ...
    """
    df = pd.read_csv(MATCHES_FILE)

    df = df.rename(
        columns={
            "Season": "season",
            "MatchID": "match_id",
            "Team": "team_id",
            "Opponent": "opponent_id",
            "Date": "date",
            "is_home": "is_home",
            "xPts": "xpts",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    # "2019-2020" -> 2019
    df["season"] = df["season"].astype(str).str.slice(0, 4).astype(int)

    # 🔧 standardise team names
    df["team_id"] = df["team_id"].astype(str).replace(TEAM_NAME_MAP)
    df["opponent_id"] = df["opponent_id"].astype(str).replace(TEAM_NAME_MAP)

    df["is_home"] = df["is_home"].astype(bool)

    needed = ["match_id", "team_id", "opponent_id", "date", "season", "is_home", "xpts"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in matches file: {missing}")

    return df[needed].copy()


# ---------------------------------------------------------------------
# Load Understat minutes / starts
# ---------------------------------------------------------------------

def load_understat_minutes() -> pd.DataFrame:
    """
    Load per-player match minutes & starting info from Understat files:

      data/raw/understat_player_matches/understat_player_matches_2019.csv
      data/raw/understat_player_matches/understat_player_matches_2020.csv
      ...

    Expected columns in each file:
      season,Date,team,h_team,a_team,player_id,player_name,Min,started,...
    """

    if not UNDERSTAT_DIR.exists():
        raise FileNotFoundError(f"Understat directory not found: {UNDERSTAT_DIR}")

    files = sorted(UNDERSTAT_DIR.glob("understat_player_matches_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No Understat files of the form 'understat_player_matches_*.csv' "
            f"found in {UNDERSTAT_DIR}"
        )

    frames: list[pd.DataFrame] = []
    for path in files:
        tmp = pd.read_csv(path)
        tmp["__source_file"] = path.name
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True)

    # Normalise column names
    df = df.rename(
        columns={
            "season": "season",
            "Date": "date",      # some files may have 'Date'
            "team": "team_id",
            "player_id": "player_id",
            "player_name": "player_name",
            "Min": "minutes",
            "started": "started",
        }
    )

    # 🔧 Important: if some files already had a 'date' column in lowercase,
    # the rename above will create duplicate 'date' columns.
    # This drops duplicate-named columns, keeping the first occurrence.
    df = df.loc[:, ~df.columns.duplicated()]

    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["season"].astype(int)
    df["team_id"] = df["team_id"].astype(str)
    df["team_id"] = df["team_id"].replace(TEAM_NAME_MAP)
    # started can be boolean or 'True'/'False' strings
    if df["started"].dtype == object:
        df["started"] = (
            df["started"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
        )
    df["started"] = df["started"].fillna(False).astype(bool)

    df["minutes"] = df["minutes"].fillna(0).astype(float)

    needed = ["season", "date", "team_id", "player_id", "minutes", "started"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in Understat minutes: {missing}")

    return df[needed + ["player_name"]].copy()

# ---------------------------------------------------------------------
# Build rotation panel
# ---------------------------------------------------------------------

def build_rotation_panel() -> pd.DataFrame:
    """
    Build player–team–match panel for rotation / selection:

      - join Understat minutes to our matches by (season, date, team_id)
      - compute days_rest per player

    One row = player–team–match, with:
      match_id, player_id, player_name, team_id, season, date,
      opponent_id, is_home, xpts, minutes, started, days_rest
    """
    matches = load_matches()
    under = load_understat_minutes()

    # Make sure keys are the same type
    matches["team_id"] = matches["team_id"].astype(str)

    # Merge: for each player-appearance, attach match_id, opponent, is_home, xpts
    before = len(under)
    panel = under.merge(
        matches,
        on=["season", "date", "team_id"],
        how="inner",              # 👈 inner join: keep only matches present in our league data
        validate="many_to_one",
    )
    after = len(panel)
    dropped = before - after
    if dropped > 0:
        print(f"⚠️ Dropped {dropped} Understat rows that had no matching league match (cups/friendlies).")

    # Compute days_rest for each player (days since last appearance)
    panel = panel.sort_values(["player_id", "date"])
    panel["days_rest"] = (
        panel.groupby("player_id")["date"].diff().dt.days
    )

    # First appearance will have NaN days_rest -> treat as large rest, e.g. 30
    panel["days_rest"] = panel["days_rest"].fillna(30).astype(float)

    # Cap extreme values to avoid weird leverage
    panel["days_rest"] = panel["days_rest"].clip(lower=0, upper=30)

    panel = panel[
        [
            "match_id",
            "player_id",
            "player_name",
            "team_id",
            "season",
            "date",
            "opponent_id",
            "is_home",
            "xpts",
            "minutes",
            "started",
            "days_rest",
        ]
    ].copy()

    return panel


def main() -> None:
    panel = build_rotation_panel()
    out_path = DATA_PROCESSED / "panel_rotation.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"✅ Saved rotation panel with shape {panel.shape} to {out_path}")


if __name__ == "__main__":
    main()
