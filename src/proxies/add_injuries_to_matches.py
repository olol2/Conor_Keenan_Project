# src/add_injuries_to_matches.py
"""
Merge injuries onto matches_all_seasons.csv.

Input:
  data/processed/matches/matches_all_seasons.csv
  data/processed/injuries/injuries_2019_2025_all_seasons.csv

Output:
  data/processed/matches/matches_with_injuries_all_seasons.csv
  (adds columns: injured_players, injury_spells)
"""

from pathlib import Path
import pandas as pd

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]

MATCHES_DIR = ROOT_DIR / "data" / "processed" / "matches"
INJURIES_DIR = ROOT_DIR / "data" / "processed" / "injuries"
OUTPUT_DIR = MATCHES_DIR
OUTPUT_FILE = OUTPUT_DIR / "matches_with_injuries_all_seasons.csv"


# -------------------------------------------------------------------
# Loading matches
# -------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load the team–match panel built by build_match_panel.py.
    Team names are already in canonical form.
    """
    path = MATCHES_DIR / "matches_all_seasons.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run src/build_match_panel.py first."
        )
    df = pd.read_csv(path, parse_dates=["Date"])
    return df


# -------------------------------------------------------------------
# Loading injuries from the master file
# -------------------------------------------------------------------

def load_injuries_all_seasons() -> pd.DataFrame:
    """
    Load the combined injuries master and standardise to:
        Season, Team, player, from_date, to_date
    """
    path = INJURIES_DIR / "injuries_2019_2025_all_seasons.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run src/data_collection/build_injuries_all_seasons.py first."
        )

    df = pd.read_csv(path)

    # We expect columns: player_name, team, start_date, end_date, season (and season_start_year, type, ...)
    required = {"player_name", "team", "start_date", "end_date", "season"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in injuries master: {missing}")

    injuries = pd.DataFrame(
        {
            "Season": df["season"],
            "Team": df["team"],
            "player": df["player_name"],
            "from_date": pd.to_datetime(df["start_date"], errors="coerce"),
            "to_date": pd.to_datetime(df["end_date"], errors="coerce"),
        }
    )

    # Drop rows with missing dates
    injuries = injuries.dropna(subset=["from_date", "to_date"])

    # Ensure from_date <= to_date
    mask = injuries["from_date"] > injuries["to_date"]
    if mask.any():
        tmp = injuries.loc[mask, "from_date"].copy()
        injuries.loc[mask, "from_date"] = injuries.loc[mask, "to_date"]
        injuries.loc[mask, "to_date"] = tmp

    return injuries


# -------------------------------------------------------------------
# Merge injuries onto matches
# -------------------------------------------------------------------

def add_injury_counts(matches: pd.DataFrame, injuries: pd.DataFrame) -> pd.DataFrame:
    """
    For each Season, Team, Date in matches, count how many players are injured.
    """
    inj = injuries[["Season", "Team", "player", "from_date", "to_date"]].copy()

    # Merge matches with injuries on Season + Team (cartesian on dates)
    merged = matches[["Season", "Team", "Date"]].merge(
        inj, on=["Season", "Team"], how="left"
    )

    # Flag where the match date falls inside the injury spell
    mask = (merged["Date"] >= merged["from_date"]) & (merged["Date"] <= merged["to_date"])
    active = merged[mask].copy()

    if active.empty:
        # No overlapping spells found, just return matches with zeros
        matches["injured_players"] = 0
        matches["injury_spells"] = 0
        return matches

    # Group by Season, Team, Date to count injured players
    counts = (
        active.groupby(["Season", "Team", "Date"])
        .agg(
            injured_players=("player", "nunique"),
            injury_spells=("player", "size"),
        )
        .reset_index()
    )

    # Merge back to matches
    out = matches.merge(counts, on=["Season", "Team", "Date"], how="left")

    out["injured_players"] = out["injured_players"].fillna(0).astype(int)
    out["injury_spells"] = out["injury_spells"].fillna(0).astype(int)

    return out


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main() -> None:
    matches = load_matches()
    injuries = load_injuries_all_seasons()

    matches_with_inj = add_injury_counts(matches, injuries)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    matches_with_inj.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {OUTPUT_FILE} with shape {matches_with_inj.shape}")


if __name__ == "__main__":
    main()
