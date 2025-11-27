# src/add_injuries_to_matches.py

from pathlib import Path
import re
import pandas as pd


# -------------------------------------------------------------------
# Team name standardisation
# -------------------------------------------------------------------

TEAM_MAP = {
    # Big 6
    "Arsenal FC": "Arsenal",
    "Liverpool FC": "Liverpool",
    "Chelsea FC": "Chelsea",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Manchester United FC": "Man United",
    "Tottenham Hotspur": "Tottenham",

    # Others, 2019–2025-ish PL teams
    "Leicester City": "Leicester",
    "Brighton & Hove Albion": "Brighton",
    "Wolverhampton Wanderers": "Wolves",
    "AFC Bournemouth": "Bournemouth",
    "Newcastle United": "Newcastle",
    "West Ham United": "West Ham",
    "West Bromwich Albion": "West Brom",
    "Norwich City": "Norwich",
    "Sheffield United": "Sheffield Utd",
    "Leeds United": "Leeds",
    "Nottingham Forest": "Nott'm Forest",
    "Luton Town": "Luton",
    "Ipswich Town": "Ipswich",
    "Cardiff City": "Cardiff",
    "Huddersfield Town": "Huddersfield",
    # If a name is already the football-data name, we just leave it unchanged
}


def standardise_team(name: str) -> str:
    """
    Map various scraped team names to the canonical names used
    in matches_all_seasons.csv (e.g. 'Liverpool FC' -> 'Liverpool').
    """
    if not isinstance(name, str):
        return name
    # strip a trailing " FC"
    name = name.replace(" FC", "")
    # apply manual mapping
    return TEAM_MAP.get(name, name)


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

MATCHES_DIR = ROOT_DIR / "data" / "processed" / "matches"
INJURIES_DIR = ROOT_DIR / "data" / "processed" / "injuries"
OUTPUT_DIR = MATCHES_DIR
OUTPUT_FILE = OUTPUT_DIR / "matches_with_injuries_all_seasons.csv"


# -------------------------------------------------------------------
# Loading matches
# -------------------------------------------------------------------

def load_matches() -> pd.DataFrame:
    """
    Load the team–match panel built by build_match_panel.py
    and standardise the Team names.
    """
    path = MATCHES_DIR / "matches_all_seasons.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run src/build_match_panel.py first."
        )
    df = pd.read_csv(path, parse_dates=["Date"])
    df["Team"] = df["Team"].map(standardise_team)
    return df


# -------------------------------------------------------------------
# Loading injuries (all seasons, including 2024–2025)
# -------------------------------------------------------------------

def season_label_from_year(year: int) -> str:
    """
    Map file year (season END year) to season label.

    Example:
        injuries_2020.csv  ->  season '2019-2020'
        injuries_2021.csv  ->  season '2020-2021'
        injuries_2025.csv  ->  season '2024-2025'
    """
    start_year = year - 1
    end_year = year
    return f"{start_year}-{end_year}"


def load_injuries_all_seasons() -> pd.DataFrame:
    """
    Load injuries_*.csv from data/processed/injuries and standardise columns:
        Season, Team, player, from_date, to_date
    This will automatically include injuries_2025.csv if it exists.
    """
    paths = sorted(INJURIES_DIR.glob("injuries_*.csv"))
    if not paths:
        raise FileNotFoundError(
            f"No injuries_*.csv files found in {INJURIES_DIR}. "
            "Make sure you have run your fetch_injuries script."
        )

    frames = []

    for path in paths:
        # extract year from filename, e.g. injuries_2020.csv -> 2020
        m = re.search(r"(\d{4})", path.name)
        if not m:
            print(f"Skipping {path}, could not find year in filename")
            continue
        year = int(m.group(1))
        season_label = season_label_from_year(year)

        df = pd.read_csv(path)
        cols_lower = {c.lower(): c for c in df.columns}

        # --- club/team column ----------------------------------------
        club_col = None
        for cand in ["club", "team"]:
            if cand in cols_lower:
                club_col = cols_lower[cand]
                break
        if club_col is None:
            raise ValueError(
                f"Could not find club/team column in {path}. "
                f"Columns: {list(df.columns)}"
            )

        # --- player column -------------------------------------------
        player_col = None
        # first try exact matches
        for cand in ["player", "name", "player_name"]:
            if cand in cols_lower:
                player_col = cols_lower[cand]
                break
        # if still not found, fall back to any column starting with "player"
        if player_col is None:
            for c in df.columns:
                if c.lower().startswith("player"):
                    player_col = c
                    break
        if player_col is None:
            raise ValueError(
                f"Could not find player column in {path}. "
                f"Columns: {list(df.columns)}"
            )

        # --- start / end date columns --------------------------------
        start_col = None
        for cand in ["from", "from_date", "start_date", "injury_from"]:
            if cand in cols_lower:
                start_col = cols_lower[cand]
                break
        if start_col is None:
            raise ValueError(
                f"Could not find start date column in {path}. "
                f"Columns: {list(df.columns)}"
            )

        end_col = None
        for cand in ["to", "to_date", "end_date", "injury_to"]:
            if cand in cols_lower:
                end_col = cols_lower[cand]
                break
        if end_col is None:
            raise ValueError(
                f"Could not find end date column in {path}. "
                f"Columns: {list(df.columns)}"
            )

        # --- standardised frame --------------------------------------
        df_std = pd.DataFrame(
            {
                "Season": season_label,
                "Team": df[club_col].map(standardise_team),
                "player": df[player_col],
                "from_date": pd.to_datetime(df[start_col], errors="coerce"),
                "to_date": pd.to_datetime(df[end_col], errors="coerce"),
            }
        )

        # drop rows with missing dates
        df_std = df_std.dropna(subset=["from_date", "to_date"])
        frames.append(df_std)

    injuries = pd.concat(frames, ignore_index=True)

    # ensure from_date <= to_date
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

    # merge matches with injuries on Season + Team (cartesian on dates)
    merged = matches[["Season", "Team", "Date"]].merge(
        inj, on=["Season", "Team"], how="left"
    )

    # flag where the match date falls inside the injury spell
    mask = (merged["Date"] >= merged["from_date"]) & (merged["Date"] <= merged["to_date"])
    active = merged[mask].copy()

    if active.empty:
        # no overlapping spells found, just return matches with zeros
        matches["injured_players"] = 0
        matches["injury_spells"] = 0
        return matches

    # group by Season, Team, Date to count injured players
    counts = (
        active.groupby(["Season", "Team", "Date"])
        .agg(
            injured_players=("player", "nunique"),
            injury_spells=("player", "size"),
        )
        .reset_index()
    )

    # merge back to matches
    out = matches.merge(counts, on=["Season", "Team", "Date"], how="left")

    out["injured_players"] = out["injured_players"].fillna(0).astype(int)
    out["injury_spells"] = out["injury_spells"].fillna(0).astype(int)

    return out


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main():
    matches = load_matches()
    injuries = load_injuries_all_seasons()

    matches_with_inj = add_injury_counts(matches, injuries)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    matches_with_inj.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
