import asyncio, sys, time
from pathlib import Path
import pandas as pd
from aiohttp import ClientSession
from understat import Understat
import numpy as np

#**********************************************************************
# This code fetches player match data from understat.com for specified seasons
# and saves the data into CSV files. the csv files are stored in the data/processed directory.
#**********************************************************************
SEASONS = sys.argv[1:] or ["2019","2020","2021","2022","2023","2024"]
OUT = Path("data/processed"); OUT.mkdir(parents=True, exist_ok=True)

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

async def fetch_season(season: str):
    out = OUT / f"understat_player_matches_{season}.csv"
    if out.exists(): print("[skip]", out); return
    async with ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as s:
        u = Understat(s)
        teams = await u.get_teams("epl", season)  # this call is fine
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
                time.sleep(0.1)
        big = pd.concat(frames, ignore_index=True).drop_duplicates()
        big.to_csv(out, index=False)
        print("[saved]", out, len(big))


async def main():
    for s in SEASONS:
        await fetch_season(s)

if __name__ == "__main__":
    asyncio.run(main())
