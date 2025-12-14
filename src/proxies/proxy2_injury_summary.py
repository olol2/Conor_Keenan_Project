# src/proxies/proxy2_injury_summary.py
from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd


"""
Attach a consistent numeric Understat player_id to the Proxy 2 injury output
(proxy2_injury_did_points_gbp.*) using the Understat master.

Inputs (default):
  - results/proxy2_injury_did_points_gbp.csv  (or .parquet)
  - data/processed/understat/understat_player_matches_master.csv

Output (default):
  - results/proxy2_injury_final_named.csv

Robust to two DiD schemas:
  A) newer: has player_name column
  B) older: has player_id column that is actually a player name
"""


# ---------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------

def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    suf = path.suffix.lower()
    if suf == ".csv":
        return pd.read_csv(path)
    if suf in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type: {path.suffix} (expected .csv or .parquet)")


# ---------------------------------------------------------------------
# Load DiD + points + £ results
# ---------------------------------------------------------------------

def load_did(path: Path) -> pd.DataFrame:
    df = read_table(path)
    df.columns = [c.strip() for c in df.columns]

    # Prefer explicit player_name; fallback to older convention where player_id is a name
    if "player_name" in df.columns:
        df["player_name"] = df["player_name"].astype(str).str.strip()
        df["injury_player_name_raw"] = df["player_name"]
    elif "player_id" in df.columns:
        df["player_id"] = df["player_id"].astype(str).str.strip()
        df["player_name"] = df["player_id"]
        df["injury_player_name_raw"] = df["player_id"]
    else:
        raise ValueError(
            f"DiD file must contain either player_name or player_id. Columns: {df.columns.tolist()}"
        )

    if "team_id" not in df.columns:
        raise ValueError(f"DiD file missing team_id. Columns: {df.columns.tolist()}")

    df["team_id"] = df["team_id"].astype(str).str.strip()

    if "season" in df.columns:
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------------------
# Build lookup(s) from Understat master
# ---------------------------------------------------------------------

def load_understat_lookups(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    needed = {"player_id", "player_name", "team"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(
            f"Understat master missing columns: {sorted(missing)}. Found: {df.columns.tolist()}"
        )

    tmp = pd.DataFrame(
        {
            "player_name": df["player_name"].astype(str).str.strip(),
            "team_id": df["team"].astype(str).str.strip(),
            "understat_player_id": pd.to_numeric(df["player_id"], errors="coerce").astype("Int64"),
        }
    ).dropna(subset=["understat_player_id"])

    # (A) Best lookup: (player_name, team_id) -> most common understat_player_id
    by_team = (
        tmp.groupby(["player_name", "team_id", "understat_player_id"], as_index=False)
        .size()
        .sort_values(["player_name", "team_id", "size"], ascending=[True, True, False])
        .drop_duplicates(subset=["player_name", "team_id"])[["player_name", "team_id", "understat_player_id"]]
        .rename(columns={"understat_player_id": "player_id"})
        .reset_index(drop=True)
    )

    # (B) Fallback lookup: player_name -> most common understat_player_id
    by_name = (
        tmp.groupby(["player_name", "understat_player_id"], as_index=False)
        .size()
        .sort_values(["player_name", "size"], ascending=[True, False])
        .drop_duplicates(subset=["player_name"])[["player_name", "understat_player_id"]]
        .rename(columns={"understat_player_id": "player_id"})
        .reset_index(drop=True)
    )

    return by_team, by_name


# ---------------------------------------------------------------------
# Main transform
# ---------------------------------------------------------------------

def attach_understat_id(did: pd.DataFrame, lookup_team: pd.DataFrame, lookup_name: pd.DataFrame) -> pd.DataFrame:
    out = did.copy()

    # Pass 1: (player_name, team_id)
    out = out.merge(lookup_team, on=["player_name", "team_id"], how="left", suffixes=("", "_lk1"))

    # Pass 2: fill missing ids by player_name only
    missing_before = int(out["player_id"].isna().sum())
    if missing_before > 0:
        out = out.merge(
            lookup_name.rename(columns={"player_id": "player_id_name_only"}),
            on=["player_name"],
            how="left",
        )
        out["player_id"] = out["player_id"].fillna(out["player_id_name_only"])
        out = out.drop(columns=["player_id_name_only"])

    out["player_id"] = pd.to_numeric(out["player_id"], errors="coerce").astype("Int64")

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Attach Understat numeric player_id to Proxy 2 injury outputs.")
    p.add_argument("--did", type=str, default=None, help="Path to proxy2_injury_did_points_gbp.csv or .parquet")
    p.add_argument("--understat-master", type=str, default=None, help="Path to understat_player_matches_master.csv")
    p.add_argument("--out", type=str, default=None, help="Output CSV path")
    p.add_argument("--dry-run", action="store_true", help="Run full compute but do not write output")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parents[2]
    results_dir = root / "results"
    processed_dir = root / "data" / "processed"

    did_path = Path(args.did) if args.did else (results_dir / "proxy2_injury_did_points_gbp.csv")
    understat_path = Path(args.understat_master) if args.understat_master else (
        processed_dir / "understat" / "understat_player_matches_master.csv"
    )
    out_path = Path(args.out) if args.out else (results_dir / "proxy2_injury_final_named.csv")

    did = load_did(did_path)
    lookup_team, lookup_name = load_understat_lookups(understat_path)
    out = attach_understat_id(did, lookup_team, lookup_name)

    # Quick linkage diagnostics
    n_total = len(out)
    n_missing = int(out["player_id"].isna().sum())
    match_rate = 1.0 - (n_missing / n_total if n_total else 0.0)
    print(f"Loaded DiD: {did_path} | rows={n_total}")
    print(f"Understat ID match rate: {match_rate:.3%} | missing={n_missing}")

    # Keep a stable, readable column order (don’t drop any columns you already have)
    front = ["season", "team_id", "player_id", "player_name", "injury_player_name_raw"]
    front = [c for c in front if c in out.columns]
    rest = [c for c in out.columns if c not in front]
    out = out[front + rest].copy()

    # Optional sort for readability
    if "season" in out.columns and "xpts_season_total" in out.columns:
        out = out.sort_values(["season", "xpts_season_total"], ascending=[True, False])

    if args.dry_run:
        print(f"✅ dry-run complete | output shape={out.shape} | output NOT written")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"✅ Saved final named injury proxy to {out_path} | shape={out.shape}")


if __name__ == "__main__":
    main()
