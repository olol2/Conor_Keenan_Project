import asyncio
import sys
from pathlib import Path

import pandas as pd
from aiohttp import ClientSession
from understat import Understat

from src.utils.config import Config
from src.utils.logging_setup import setup_logger
from src.utils.run_metadata import write_run_metadata
from src.utils.io import atomic_write_csv


"""
Fetch EPL player match data from understat.com for specified seasons.

Why:
- Builds per-season player-match CSVs used downstream for proxy construction.

CLI:
- python -m src.data_collection.understat_fetch_players 2019 2020 ...
"""

SEASONS = sys.argv[1:] or ["2019", "2020", "2021", "2022", "2023", "2024"]

cfg = Config.load()
OUT = cfg.processed
OUT.mkdir(parents=True, exist_ok=True)


def tidy(matches, player, team_title, season):
    if not matches: return pd.DataFrame()
    df = pd.DataFrame(matches)
    if df.empty: return df
    df["season"] = int(season)
    df["team"] = team_title
    df["player_id"] = player["id"]
    df["player_name"] = player.get("player_name") or player.get("title")
    df["Date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["Min"] = pd.to_numeric(df.get("time"), errors="coerce").fillna(0).astype(int)
    if "is_sub" in df.columns:
        raw = df["is_sub"]
        if raw.dtype == object:
            m = raw.astype(str).str.strip().str.lower()
            # treat common truthy strings as subs
            is_sub = m.isin(["1", "true", "t", "y", "yes"])
        else:
            # numeric/bool → to bool
            is_sub = raw.astype(int).astype(bool)
    else:
        # fallback: infer subs from position text if is_sub not present
        pos = df.get("position")
        is_sub = pos.astype(str).str.contains("sub", case=False, na=False)
    df["started"] = (~is_sub).astype(bool)  
    # numeric stats
    for col in ("xG","xA"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["goals"]   = pd.to_numeric(df.get("goals"), errors="coerce").fillna(0).astype(int)
    df["assists"] = pd.to_numeric(df.get("assists"), errors="coerce").fillna(0).astype(int)
    df = df[["season","Date","team","h_team","a_team","player_id","player_name",
             "Min","started","goals","assists","xG","xA"]]
    return df.drop_duplicates()

async def fetch_season(season: str, logger):
    out = OUT / f"understat_player_matches_{season}.csv"
    if out.exists(): print("[skip]", out); return
    async with ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as s:
        u = Understat(s)
        try:
            teams = await u.get_teams("epl", season)
        except AttributeError as e:
            logger.error(
                "Understat parsing failed while fetching league teams (season=%s). "
                "This typically means understat.com page structure changed or the request was blocked.",
                season,
            )
            logger.error(
                "If you already have the CSVs in %s, you do not need to run this script for grading.",
                OUT,
            )
            raise RuntimeError(
                f"Understat scrape failed for season={season}. "
                "Use existing processed CSVs or update the scraper/library."
            ) from e

        frames = []
        for t in teams:
            team_title = t.get("title")
            # ---- squad
            try:
                squad = await u.get_team_players(team_title, season=season)
            except Exception:
                squad = await u.get_team_players(int(t["id"]), season=season)
            # ---- player matches
            for p in squad:
                ms = await u.get_player_matches(p["id"], season=season)
                df = tidy(ms, p, team_title, season)
                if not df.empty: frames.append(df)
                await asyncio.sleep(0.1)
        big = pd.concat(frames, ignore_index=True).drop_duplicates()

        # Minimal fail-fast checks (avoids silently writing empty/broken files)
        required = {"season", "Date", "team", "player_id", "player_name", "Min", "started"}
        missing = required - set(big.columns)
        if missing:
            raise ValueError(f"[understat_fetch_players] Missing required columns for season={season}: {sorted(missing)}")
        if len(big) == 0:
            raise ValueError(f"[understat_fetch_players] No rows collected for season={season}")

        # Atomic write prevents partial CSVs if interrupted mid-write
        atomic_write_csv(big, out, index=False)

        logger.info("[saved] %s | rows=%d", out, len(big))
        print("[saved]", out, len(big))  # optional: keep exact old console behavior



async def main():
    logger = setup_logger("understat_fetch_players", cfg.logs, "understat_fetch_players.log")
    meta_path = write_run_metadata(cfg.metadata, "understat_fetch_players", extra={"seasons": SEASONS})
    logger.info("Run metadata saved to: %s", meta_path)

    for s in SEASONS:
        await fetch_season(s, logger)


if __name__ == "__main__":
    asyncio.run(main())
