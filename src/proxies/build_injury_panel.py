from __future__ import annotations
"""
Build a player–team–match injury panel dataset by combining:
  - team–match data with expected points (xPts) and injury counts
  - injury spells per player–team–season (already standardised)
  - Understat per-player match minutes & starting info (already standardised)

Outputs:
  data/processed/panel_injury.parquet
  data/processed/panel_injury.csv
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

# Project root: /files/Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[2]

DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# 1) MATCHES file (team–match with xPts and squad injury counts)
MATCHES_FILE = DATA_PROCESSED / "matches" / "matches_with_injuries_all_seasons.csv"

# 2) INJURIES master file (already standardised team names)
INJURIES_FILE = DATA_PROCESSED / "injuries" / "injuries_2019_2025_all_seasons.csv"

# 3) UNDERSTAT master file (already standardised team names)
UNDERSTAT_FILE = DATA_PROCESSED / "understat" / "understat_player_matches_master.csv"


# ---------------------------------------------------------------------
# Load matches (team–match, with xPts and squad injuries)
# ---------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load team–match data with xPts and injury counts for the injury panel.

    Expected columns in MATCHES_FILE:
      Season, MatchID, Date, Team, Opponent, is_home, xPts,
      injured_players, injury_spells, ...
    """
    path = MATCHES_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run build_match_panel.py and add_injuries_to_matches.py first."
        )

    df = pd.read_csv(path)

    df = df.rename(
        columns={
            "Season": "season_label",
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
    df["season"] = df["season_label"].astype(str).str.slice(0, 4).astype(int)

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
    Load injury/suspension spells from the combined injuries master.

    We expect per-row in INJURIES_FILE:
      player_name, team, start_date, end_date, season (e.g. '2019-2020'),
      season_start_year, type, ...

    We return:
      player_id, team_id, start_date, end_date, season (int, first year)
    """
    path = INJURIES_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run build_injuries_all_seasons.py first."
        )

    df = pd.read_csv(path)

    required = {"player_name", "team", "start_date", "end_date", "season"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in injuries master: {missing}")

    spells = pd.DataFrame(
        {
            "player_id": df["player_name"],
            "team_id": df["team"],
            "start_date": pd.to_datetime(df["start_date"], errors="coerce"),
            "end_date": pd.to_datetime(df["end_date"], errors="coerce"),
            "season_label": df["season"].astype(str),
        }
    )

    # Drop rows with missing dates
    spells = spells.dropna(subset=["start_date", "end_date"])

    # Ensure start_date <= end_date
    mask = spells["start_date"] > spells["end_date"]
    if mask.any():
        tmp = spells.loc[mask, "start_date"].copy()
        spells.loc[mask, "start_date"] = spells.loc[mask, "end_date"]
        spells.loc[mask, "end_date"] = tmp

    # Convert season_label like "2019-2020" -> 2019
    spells["season"] = spells["season_label"].str.slice(0, 4).astype(int)

    return spells[["player_id", "team_id", "start_date", "end_date", "season"]].copy()


# ---------------------------------------------------------------------
# Load Understat player minutes (from processed master)
# ---------------------------------------------------------------------

def load_player_minutes() -> pd.DataFrame:
    """
    Load per-player match minutes & starting info from the Understat master:

      data/processed/understat/understat_player_matches_master.csv

    We use *player names* as the key (same as in the injuries data).
    """

    path = UNDERSTAT_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run build_understat_master.py first."
        )

    df = pd.read_csv(path)

    # Date column: try 'match_date' first, then 'Date'
    date_col = None
    for cand in ["match_date", "Date", "date"]:
        if cand in df.columns:
            date_col = cand
            break
    if date_col is None:
        raise ValueError(
            f"No date column ('match_date'/'Date'/'date') found in {path}. "
            f"Columns: {list(df.columns)}"
        )

    # Team column: 'team' in the master
    if "team" not in df.columns:
        raise ValueError(
            f"No 'team' column found in {path}. Columns: {list(df.columns)}"
        )

    # Season: prefer 'season_start_year', else 'season'
    if "season_start_year" in df.columns:
        season_series = df["season_start_year"].astype(int)
    elif "season" in df.columns:
        season_series = df["season"].astype(str).str.slice(0, 4).astype(int)
    else:
        raise ValueError(
            f"No season column ('season_start_year' or 'season') in {path}. "
            f"Columns: {list(df.columns)}"
        )

    # Player name (we'll use this as the key)
    if "player_name" not in df.columns:
        raise ValueError(f"'player_name' column missing in {path}")

    if "Min" not in df.columns:
        raise ValueError(f"'Min' column (minutes) missing in {path}")
    if "started" not in df.columns:
        raise ValueError(f"'started' column missing in {path}")

    out = pd.DataFrame(
        {
            "season": season_series,
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "team_id": df["team"].astype(str),
            # IMPORTANT: use player_name as player_id so it matches injuries
            "player_id": df["player_name"].astype(str),
            "minutes": df["Min"],
            "started": df["started"],
        }
    )

    # started can be boolean or 'True'/'False' strings
    if out["started"].dtype == object:
        out["started"] = (
            out["started"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
        )
    out["started"] = out["started"].fillna(False).astype(bool)

    out["minutes"] = pd.to_numeric(out["minutes"], errors="coerce").fillna(0).astype(float)

    return out



# ---------------------------------------------------------------------
# Build the player–team–match injury panel
# ---------------------------------------------------------------------

def build_panel() -> pd.DataFrame:
    """
    Build player–team–match panel using:

      - matches (team_id, opponent_id, date, season, xpts, n_injured_squad)
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

    # Parquet (fast / compact)
    out_parquet = DATA_PROCESSED / "panel_injury.parquet"
    panel.to_parquet(out_parquet, index=False)

    # CSV (easy to inspect / submit)
    out_csv = DATA_PROCESSED / "panel_injury.csv"
    panel.to_csv(out_csv, index=False)

    print(f"✅ Saved panel with shape {panel.shape} to")
    print(f"   - {out_parquet}")
    print(f"   - {out_csv}")


if __name__ == "__main__":
    main()
