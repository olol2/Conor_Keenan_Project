# src/proxies/proxy2_injury_summary.py

from __future__ import annotations

from pathlib import Path
import pandas as pd

"""
Take the injury DiD proxy with points + £
(results/proxy2_injury_did_points_gbp.csv)
and attach a consistent numeric player_id based on the
Understat master file.

Output:
    results/proxy2_injury_final_named.csv

Conventions:
    - In the DiD results, `player_id` is actually a player *name*
      coming from the injuries panel.
    - In the Understat master, `player_id` is the numeric Understat ID,
      and `player_name` is the human-readable name.
    - Team names are already in canonical short form everywhere
      (Arsenal, Man City, Nott'm Forest, ...).
"""

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DATA_PROCESSED = ROOT / "data" / "processed"
UNDERSTAT_MASTER = DATA_PROCESSED / "understat" / "understat_player_matches_master.csv"

DID_FILE = RESULTS_DIR / "proxy2_injury_did_points_gbp.csv"


# ---------------------------------------------------------------------
# Load DiD + points + £ results
# ---------------------------------------------------------------------

def load_did() -> pd.DataFrame:
    """
    Load DiD + points + £ results and expose a clear player_name column.

    Expected columns in DID_FILE include at least:
        player_id  (string name from injuries panel)
        team_id    (canonical short team name)
        season
        xpts_season_total, value_gbp_season_total, ...
    """
    if not DID_FILE.exists():
        raise FileNotFoundError(f"DiD results file not found: {DID_FILE}")

    df = pd.read_csv(DID_FILE)

    # In our pipeline, 'player_id' here is actually a name.
    df["player_name"] = df["player_id"].astype(str)
    df["team_id"] = df["team_id"].astype(str)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------------------
# Build (player_name, team_id) -> Understat numeric ID lookup
# ---------------------------------------------------------------------

def load_player_lookup() -> pd.DataFrame:
    """
    Build a lookup (player_name, team_id) -> understat_player_id
    from the Understat master file:

        data/processed/understat/understat_player_matches_master.csv

    Expected columns include:
        player_id   (numeric Understat ID)
        player_name
        team        (canonical short team name)
    """
    if not UNDERSTAT_MASTER.exists():
        raise FileNotFoundError(
            f"Understat master file not found: {UNDERSTAT_MASTER}.\n"
            f"Run build_understat_master.py first."
        )

    df = pd.read_csv(UNDERSTAT_MASTER)

    needed = {"player_id", "player_name", "team"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(
            f"Understat master file is missing columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    df["player_name"] = df["player_name"].astype(str)
    df["team"] = df["team"].astype(str)

    players = (
        df.rename(
            columns={
                "player_id": "understat_player_id",
                "team": "team_id",
            }
        )[["player_name", "team_id", "understat_player_id"]]
        .drop_duplicates(subset=["player_name", "team_id"])
    )

    return players


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    did = load_did()
    players = load_player_lookup()

    # Merge on player_name + team_id to attach the Understat ID
    did_named = did.merge(
        players,
        on=["player_name", "team_id"],
        how="left",
    )

    # Make Understat IDs nice nullable integers
    did_named["understat_player_id"] = pd.to_numeric(
        did_named["understat_player_id"], errors="coerce"
    ).astype("Int64")

    # Align with rotation: use Understat numeric ID as `player_id`,
    # keep the original injuries name separately.
    did_named = did_named.rename(
        columns={
            "player_id": "injury_player_name_raw",   # original name from injuries
            "understat_player_id": "player_id",      # Understat numeric ID
        }
    )

    # Sort for readability: within each season, highest season xPts first
    if "xpts_season_total" in did_named.columns:
        did_named = did_named.sort_values(
            ["season", "xpts_season_total"], ascending=[True, False]
        )
    else:
        did_named = did_named.sort_values(["season", "team_id", "player_name"])

    out_path = RESULTS_DIR / "proxy2_injury_final_named.csv"
    did_named.to_csv(out_path, index=False)
    print(f"✅ Saved final named injury proxy to {out_path}")

    # Optional: quick summary of match quality of the linkage
    n_total = len(did_named)
    n_missing_id = did_named["player_id"].isna().sum()
    if n_missing_id:
        print(
            f"⚠️ Note: {n_missing_id} of {n_total} rows "
            f"could not be matched to an Understat player_id."
        )


if __name__ == "__main__":
    main()
