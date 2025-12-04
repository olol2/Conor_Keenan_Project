# src/proxies/proxy2_injury_summary.py

from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
DATA_PROCESSED = ROOT / "data" / "processed"
UNDERSTAT_DIR = ROOT / "data" / "raw" / "understat_player_matches"

DID_FILE = RESULTS_DIR / "proxy2_injury_did_points_gbp.csv"


def load_did() -> pd.DataFrame:
    """Load DiD + points + £ results and add a player_name column."""
    df = pd.read_csv(DID_FILE)

    # In our pipeline, 'player_id' is actually a name coming from the
    # injuries data, so treat it explicitly as player_name.
    df["player_name"] = df["player_id"].astype(str)
    df["team_id"] = df["team_id"].astype(str)

    # Map injuries-style short names to Understat-style long names
    TEAM_NAME_MAP = {
        "Man City": "Manchester City",
        "Man United": "Manchester United",
        "Newcastle": "Newcastle United",
        "Nott'm Forest": "Nottingham Forest",
        "Sheffield Utd": "Sheffield United",
        "West Brom": "West Bromwich Albion",
        "Wolves": "Wolverhampton Wanderers",
    }

    df["team_id"] = df["team_id"].replace(TEAM_NAME_MAP)

    return df



def load_player_lookup() -> pd.DataFrame:
    """
    Build a lookup (player_name, team_id) -> (player_name, team_id, numeric_understat_id)
    from all Understat per-match files.
    """
    files = sorted(UNDERSTAT_DIR.glob("understat_player_matches_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No Understat files found in {UNDERSTAT_DIR} "
            f"(expected understat_player_matches_*.csv)"
        )

    frames = []
    for path in files:
        tmp = pd.read_csv(path)
        tmp = tmp.rename(
            columns={
                "player_id": "understat_player_id",
                "player_name": "player_name",
                "team": "team_id",
            }
        )
        tmp["player_name"] = tmp["player_name"].astype(str)
        tmp["team_id"] = tmp["team_id"].astype(str)
        frames.append(tmp[["player_name", "team_id", "understat_player_id"]])

    players = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["player_name", "team_id"])
    )

    return players


def main() -> None:
    did = load_did()
    players = load_player_lookup()

    did_named = did.merge(
        players, on=["player_name", "team_id"], how="left"
    )

    # make Understat IDs nice integers
    did_named["understat_player_id"] = pd.to_numeric(
        did_named["understat_player_id"], errors="coerce"
    ).astype("Int64")

    # align with rotation: player_id = Understat id
    did_named = did_named.rename(
        columns={
            "player_id": "injury_player_name_raw",   # original name from injuries
            "understat_player_id": "player_id",      # Understat ID
        }
    )

    did_named = did_named.sort_values(
        ["season", "xpts_season_total"], ascending=[True, False]
    )

    out_path = RESULTS_DIR / "proxy2_injury_final_named.csv"
    did_named.to_csv(out_path, index=False)
    print(f"✅ Saved final named injury proxy to {out_path}")



if __name__ == "__main__":
    main()
