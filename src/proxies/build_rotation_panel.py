# src/proxies/build_rotation_panel.py
from __future__ import annotations
"""
Build a player–team–match rotation panel using:

  - league matches with expected points (xPts)
  - Understat per-player match minutes & starting info

Outputs:
  data/processed/panel_rotation.parquet
  data/processed/panel_rotation.csv

(one row per player–team–match)
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # /files/Conor_Keenan_Project
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Team–match panel with xPts (and injuries, but we only need xPts here)
MATCHES_FILE = DATA_PROCESSED / "matches" / "matches_with_injuries_all_seasons.csv"

# Understat master (already combined & team names standardised)
UNDERSTAT_FILE = DATA_PROCESSED / "understat" / "understat_player_matches_master.csv"


# ---------------------------------------------------------------------
# Load matches (team–match with xPts)
# ---------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load team–match data with xPts.

    Expected columns in MATCHES_FILE:
      Season, MatchID, Date, Team, Opponent, is_home, xPts, ...
    """
    if not MATCHES_FILE.exists():
        raise FileNotFoundError(
            f"{MATCHES_FILE} not found. Run build_match_panel.py and add_injuries_to_matches.py first."
        )

    df = pd.read_csv(MATCHES_FILE)

    df = df.rename(
        columns={
            "Season": "season_label",
            "MatchID": "match_id",
            "Team": "team_id",
            "Opponent": "opponent_id",
            "Date": "date",
            "is_home": "is_home",
            "xPts": "xpts",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    # "2019-2020" -> 2019 (first year of season)
    df["season"] = df["season_label"].astype(str).str.slice(0, 4).astype(int)
    df["is_home"] = df["is_home"].astype(bool)

    needed = ["match_id", "team_id", "opponent_id", "date", "season", "is_home", "xpts"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in matches file: {missing}")

    return df[needed].copy()


# ---------------------------------------------------------------------
# Load Understat minutes / starts from master
# ---------------------------------------------------------------------

def load_understat_minutes() -> pd.DataFrame:
    """
    Load per-player match minutes & starting info from the Understat master:

      data/processed/understat/understat_player_matches_master.csv

    Expected columns (at least):
      season or season_start_year,
      Date or match_date,
      team (canonical),
      player_id, player_name, Min, started, ...
    """
    if not UNDERSTAT_FILE.exists():
        raise FileNotFoundError(
            f"{UNDERSTAT_FILE} not found. Run build_understat_master.py first."
        )

    df = pd.read_csv(UNDERSTAT_FILE)

    # Date column: try 'match_date', then 'Date', then 'date'
    date_col = None
    for cand in ["match_date", "Date", "date"]:
        if cand in df.columns:
            date_col = cand
            break
    if date_col is None:
        raise ValueError(
            f"No date column ('match_date'/'Date'/'date') found in {UNDERSTAT_FILE}. "
            f"Columns: {list(df.columns)}"
        )

    # Team column
    if "team" not in df.columns:
        raise ValueError(
            f"No 'team' column found in {UNDERSTAT_FILE}. "
            f"Columns: {list(df.columns)}"
        )

    # Season: prefer 'season_start_year', else 'season'
    if "season_start_year" in df.columns:
        season_series = df["season_start_year"].astype(int)
    elif "season" in df.columns:
        season_series = df["season"].astype(str).str.slice(0, 4).astype(int)
    else:
        raise ValueError(
            f"No season column ('season_start_year' or 'season') in {UNDERSTAT_FILE}. "
            f"Columns: {list(df.columns)}"
        )

    # Player id/name, minutes, started
    if "player_id" not in df.columns:
        raise ValueError(f"'player_id' column missing in {UNDERSTAT_FILE}")
    if "player_name" not in df.columns:
        raise ValueError(f"'player_name' column missing in {UNDERSTAT_FILE}")
    if "Min" not in df.columns:
        raise ValueError(f"'Min' column (minutes) missing in {UNDERSTAT_FILE}")
    if "started" not in df.columns:
        raise ValueError(f"'started' column missing in {UNDERSTAT_FILE}")

    out = pd.DataFrame(
        {
            "season": season_series,
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "team_id": df["team"].astype(str),
            "player_id": df["player_id"],          # numeric or string is fine here
            "player_name": df["player_name"].astype(str),
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

    needed = ["season", "date", "team_id", "player_id", "player_name", "minutes", "started"]
    missing = [c for c in needed if c not in out.columns]
    if missing:
        raise ValueError(f"Missing columns in Understat minutes: {missing}")

    return out[needed].copy()


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

    before = len(under)
    panel = under.merge(
        matches,
        on=["season", "date", "team_id"],
        how="inner",              # keep only league matches in our dataset
        validate="many_to_one",
    )
    after = len(panel)
    dropped = before - after
    if dropped > 0:
        print(f"⚠️ Dropped {dropped} Understat rows with no matching league match (cups/friendlies).")

    # Compute days_rest for each player (days since last appearance)
    panel = panel.sort_values(["player_id", "date"])
    panel["days_rest"] = panel.groupby("player_id")["date"].diff().dt.days

    # First appearance: treat NaN as large rest, e.g. 30 days
    panel["days_rest"] = panel["days_rest"].fillna(30).astype(float)

    # Cap extreme values
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


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    panel = build_rotation_panel()

    # Parquet (fast / compact)
    out_parquet = DATA_PROCESSED / "panel_rotation.parquet"
    panel.to_parquet(out_parquet, index=False)

    # CSV (easy to inspect / submit)
    out_csv = DATA_PROCESSED / "panel_rotation.csv"
    panel.to_csv(out_csv, index=False)

    print(f"✅ Saved rotation panel with shape {panel.shape} to")
    print(f"   - {out_parquet}")
    print(f"   - {out_csv}")


if __name__ == "__main__":
    main()
