from __future__ import annotations
"""
This script builds a player–team–match injury panel dataset by combining:
  - team–match data with expected points (xPts) and injury counts
  - injury spells per player–team–season
  - Understat per-player match minutes & starting info (if available)

The output is saved as a parquet file in:
    data/processed/panel_injury.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd


TEAM_NAME_MAP = {
    # Premier League canonical short names -> matches file uses these
    # Long / alternative -> short canonical

    # Basic “FC” variants
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Everton FC": "Everton",
    "Liverpool FC": "Liverpool",
    "Fulham FC": "Fulham",
    "Burnley FC": "Burnley",
    "Brentford FC": "Brentford",
    "Watford FC": "Watford",
    "Southampton FC": "Southampton",

    # Bournemouth / West Brom variants
    "AFC Bournemouth": "Bournemouth",
    "West Bromwich Albion": "West Brom",

    # Town / City / United variants
    "Ipswich Town": "Ipswich",
    "Luton Town": "Luton",
    "Leicester City": "Leicester",
    "Norwich City": "Norwich",
    "Leeds United": "Leeds",
    "Newcastle United": "Newcastle",
    "Manchester City": "Man City",
    "Manchester Utd": "Man United",   # defensive
    "Manchester United": "Man United",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield Utd",

    # “& Hove Albion”, “Wanderers”, “Hotspur”
    "Brighton & Hove Albion": "Brighton",
    "Brighton and Hove Albion": "Brighton",
    "Wolverhampton Wanderers": "Wolves",
    "Tottenham Hotspur": "Tottenham",

    # West Ham
    "West Ham United": "West Ham",
}


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

# Project root: /files/Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[2]

DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# 1) MATCHES file (team–match with xPts)
MATCHES_FILE = DATA_PROCESSED / "matches" / "matches_with_injuries_all_seasons.csv"

# 2) INJURIES directory (contains per-season parquet / csv from Transfermarkt)
INJURIES_DIR = DATA_PROCESSED / "injuries"

# 3) UNDERSTAT minutes directory (your understat_player_matches_2019.csv etc.)
UNDERSTAT_DIR = ROOT / "data" / "raw" / "understat_player_matches"


# ---------------------------------------------------------------------
# Load matches (team–match, with xPts)
# ---------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load team–match data with xPts and injury counts for the injury panel.

    Expected columns in the raw CSV:
      Season, MatchID, Date, Team, Opponent, is_home, xPts,
      injured_players, injury_spells, ...
    """
    path = MATCHES_FILE
    df = pd.read_csv(path)

    df = df.rename(
        columns={
            "Season": "season",
            "MatchID": "match_id",
            "Team": "team_id",
            "Opponent": "opponent_id",
            "Date": "date",
            "xPts": "xpts",
            "injured_players": "n_injured_squad",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    # "2019-2020" -> 2019 (first year of the season)
    df["season"] = df["season"].astype(str).str.slice(0, 4).astype(int)

    # Standardise team names to canonical short forms
    df["team_id"] = df["team_id"].astype(str).replace(TEAM_NAME_MAP)
    df["opponent_id"] = df["opponent_id"].astype(str).replace(TEAM_NAME_MAP)

    needed = [
        "match_id",
        "team_id",
        "opponent_id",
        "date",
        "season",
        "xpts",
        "n_injured_squad",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in matches file: {missing}")

    return df[needed].copy()


# ---------------------------------------------------------------------
# Load injury spells
# ---------------------------------------------------------------------

def load_injury_spells() -> pd.DataFrame:
    """
    Load injury/suspension spells from all files in INJURIES_DIR.

    We expect per-row:
      - player_id (or player name; we treat as ID)
      - team_id  (club name; should match Team in matches table)
      - start_date
      - end_date
      - season   (or we derive from start_date year)
    """

    if not INJURIES_DIR.exists():
        raise FileNotFoundError(f"Injuries directory not found: {INJURIES_DIR}")

    parquet_files = sorted(INJURIES_DIR.glob("*.parquet"))
    csv_files = sorted(INJURIES_DIR.glob("*.csv"))

    files = parquet_files or csv_files
    if not files:
        raise FileNotFoundError(
            f"No injury files (.parquet or .csv) found in {INJURIES_DIR}"
        )

    frames: list[pd.DataFrame] = []

    for path in files:
        if path.suffix == ".parquet":
            tmp = pd.read_parquet(path)
        else:
            tmp = pd.read_csv(path)
        tmp["__source_file"] = path.name
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True)

    # Try to normalise column names
    rename_map: dict[str, str] = {}

    # Player ID/name
    if "player_id" not in df.columns:
        if "PlayerID" in df.columns:
            rename_map["PlayerID"] = "player_id"
        elif "player_name" in df.columns:
            rename_map["player_name"] = "player_id"
        elif "Player" in df.columns:
            rename_map["Player"] = "player_id"

    # Team / club
    if "team_id" not in df.columns:
        if "team" in df.columns:
            rename_map["team"] = "team_id"
        elif "club" in df.columns:
            rename_map["club"] = "team_id"
        elif "Club" in df.columns:
            rename_map["Club"] = "team_id"

    # Dates
    if "start_date" not in df.columns:
        if "from_date" in df.columns:
            rename_map["from_date"] = "start_date"
        elif "From" in df.columns:
            rename_map["From"] = "start_date"
    if "end_date" not in df.columns:
        if "to_date" in df.columns:
            rename_map["to_date"] = "end_date"
        elif "To" in df.columns:
            rename_map["To"] = "end_date"

    # Season
    if "season" not in df.columns and "Season" in df.columns:
        rename_map["Season"] = "season"

    df = df.rename(columns=rename_map)

    needed = ["player_id", "team_id", "start_date", "end_date"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in injuries files after rename: {missing}"
        )

    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    # If season column missing, derive from start_date year
    if "season" not in df.columns:
        df["season"] = df["start_date"].dt.year

    def _parse_season_to_int(val):
        """
        Convert season values like '2019-2020' or '2019' to an integer year.

        For '2019-2020' we take the FIRST year (2019),
        to match load_matches(), which also uses the first year.
        """
        if pd.isna(val):
            return np.nan

        s = str(val).strip()
        if s == "":
            return np.nan

        if "-" in s:
            # e.g. '2019-2020' -> '2019'
            parts = s.split("-")
            year_str = parts[0]
        else:
            year_str = s

        try:
            return int(year_str)
        except ValueError:
            # e.g. junk strings like 'Unknown'
            return np.nan

    # First pass: parse season strings
    parsed = df["season"].map(_parse_season_to_int)

    # Second pass: for any NaNs, fall back to start_date year
    mask_na = parsed.isna()
    if mask_na.any():
        parsed.loc[mask_na] = df.loc[mask_na, "start_date"].dt.year

    # Third pass: if still NaN, drop those rows with a warning
    mask_na2 = parsed.isna()
    if mask_na2.any():
        n_drop = int(mask_na2.sum())
        print(f"⚠️ Dropping {n_drop} injury rows with unparseable season.")
        df = df.loc[~mask_na2].copy()
        parsed = parsed.loc[~mask_na2]

    df["season"] = parsed.astype(int)

    # Standardise team names in injuries to match matches
    df["team_id"] = df["team_id"].astype(str).replace(TEAM_NAME_MAP)

    # Keep only useful columns
    return df[["player_id", "team_id", "start_date", "end_date", "season"]].copy()


# ---------------------------------------------------------------------
# Load Understat player minutes
# ---------------------------------------------------------------------

def load_player_minutes() -> pd.DataFrame:
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

    df = df.rename(
        columns={
            "season": "season",
            "Date": "date",
            "team": "team_id",
            "player_id": "player_id",
            "player_name": "player_name",
            "Min": "minutes",
            "started": "started",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["season"].astype(int)

    # Standardise team names to canonical short forms
    df["team_id"] = df["team_id"].astype(str).replace(TEAM_NAME_MAP)

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
# Build the player–team–match injury panel
# ---------------------------------------------------------------------

def build_panel() -> pd.DataFrame:
    """
    Build player–team–match panel using:

      - matches (team_id, opponent_id, date, season, xpts)
      - injury spells (player_id, team_id, start/end, season)
      - Understat minutes (player_id, team_id, date, season, minutes, started)

    Steps:
      1) For each player–team–season from injury spells, attach all that
         team's matches in that season.
      2) Mark unavailable = 1 if match date is inside ANY injury spell.
      3) Attach minutes/started info where the player actually played.
    """

    matches = load_matches()
    spells = load_injury_spells()

    # Restrict spells to seasons & teams that exist in matches
    spells = spells.merge(
        matches[["team_id", "season"]].drop_duplicates(),
        on=["team_id", "season"],
        how="inner",
    )

    # Step 1: unique player–team–season
    pts = spells[["player_id", "team_id", "season"]].drop_duplicates()

    # Step 2: all matches for each team–season
    tsm = matches[
        ["match_id", "team_id", "season", "date", "opponent_id", "xpts", "n_injured_squad"]
    ]

    # Cross-join player–team–season with that team's matches
    panel = pts.merge(
        tsm,
        on=["team_id", "season"],
        how="left",
    )

    # Attach spells again to test whether each match is inside any spell
    panel = panel.merge(
        spells,
        on=["player_id", "team_id", "season"],
        how="left",
        suffixes=("", "_spell"),
    )

    injured_flag = (
        (panel["date"] >= panel["start_date"]) &
        (panel["date"] <= panel["end_date"])
    )

    panel["unavailable_raw"] = injured_flag.fillna(False).astype(int)

    # Collapse in case of multiple spells per player-season
    panel_injury = (
        panel.groupby(
            ["match_id", "team_id", "player_id"],
            as_index=False,
        )
        .agg(
            date=("date", "first"),
            season=("season", "first"),
            opponent_id=("opponent_id", "first"),
            xpts=("xpts", "first"),
            n_injured_squad=("n_injured_squad", "first"),
            unavailable=("unavailable_raw", "max"),
        )
    )

    # Attach Understat minutes/started
    try:
        minutes = load_player_minutes()

        panel_injury = panel_injury.merge(
            minutes,
            on=["season", "date", "team_id", "player_id"],
            how="left",
        )

        panel_injury["minutes"] = panel_injury["minutes"].fillna(0).astype(float)
        panel_injury["started"] = panel_injury["started"].fillna(False).astype(bool)

    except FileNotFoundError as e:
        print(f"⚠️ Understat minutes not found, building panel without minutes/started: {e}")
    except Exception as e:
        print(f"⚠️ Failed to merge Understat minutes, proceeding without them: {e}")

    # Sanity check
    if panel_injury[["match_id", "team_id", "player_id"]].duplicated().any():
        raise ValueError("Duplicates found in (match_id, team_id, player_id) after build.")

    return panel_injury


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    panel = build_panel()
    out_path = DATA_PROCESSED / "panel_injury.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"✅ Saved panel with shape {panel.shape} to {out_path}")


if __name__ == "__main__":
    main()
