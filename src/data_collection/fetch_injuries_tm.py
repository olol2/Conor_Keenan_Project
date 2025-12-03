# scripts/fetch_injuries_tm_py.py
from __future__ import annotations
import re, time, random, glob
from pathlib import Path
from datetime import date
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse

#**********************************************************************
# This code fetches player injury and suspension data from transfermarkt.com
# for specified seasons and saves the data into CSV files. The csv files are stored in the data/processed directory.
#**********************************************************************


OUT_DIR = Path("data/processed"); OUT_DIR.mkdir(parents=True, exist_ok=True)
URL_DIR = Path("data/raw/injuries/urls")   # where your *_tm_urls.csv files live
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; UniCourseProject/1.0; +https://example.edu)",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.transfermarkt.com/",
}

# ---------------- helpers ----------------

def _season_window(season_end_year: int) -> tuple[date, date]:
    return date(season_end_year - 1, 7, 1), date(season_end_year, 6, 30)

def _request(url: str, max_retries: int = 5) -> str:
    s = requests.Session(); s.headers.update(HEADERS)
    for i in range(max_retries):
        r = s.get(url, timeout=30)
        if r.status_code == 200:
            return r.text
        if r.status_code in (403, 429, 503):
            wait = 1.0 + i * 1.2 + random.random()
            print(f"[{r.status_code}] backoff {wait:.1f}s → {url}")
            time.sleep(wait); continue
        r.raise_for_status()
    raise RuntimeError(f"Failed after retries: {url}")

def _clean_type(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if "suspens" in s:
        return "suspension"
    return f"injury-{s or 'unknown'}"

def _clip(df: pd.DataFrame, season_end_year: int) -> pd.DataFrame:
    start, end = _season_window(season_end_year)
    m = df.copy()
    m["start_date"] = pd.to_datetime(m["start_date"]).dt.date
    m["end_date"]   = pd.to_datetime(m["end_date"]).dt.date
    m = m[~(m["end_date"] < start) & ~(m["start_date"] > end)]
    m.loc[m["start_date"] < start, "start_date"] = start
    m.loc[m["end_date"] > end,   "end_date"]     = end
    return m

def _with_query(url: str, **params) -> str:
    u = urlparse(url)
    q = parse_qs(u.query)
    q.update({k: [str(v)] for k, v in params.items()})
    return urlunparse((u.scheme, u.netloc, u.path, u.params,
                       urlencode({k: v[0] for k, v in q.items()}), u.fragment))

# ------------- parsers -------------------

def fetch_player_injury_history(player_name: str, tm_inj_url: str, team: str) -> pd.DataFrame:
    """
    tm_inj_url example:
      https://www.transfermarkt.com/ollie-watkins/verletzungen/spieler/324358
    """
    html = _request(tm_inj_url)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.items")
    if table is None:
        return pd.DataFrame(columns=["player_name","team","start_date","end_date","type","source"])

    tables = pd.read_html(str(table))
    if not tables:
        return pd.DataFrame(columns=["player_name","team","start_date","end_date","type","source"])
    df = tables[0]
    cols = {c.lower(): c for c in df.columns}

    c_injury = cols.get("injury") or cols.get("reason") or list(df.columns)[0]
    c_from   = cols.get("from")   or cols.get("since")  or "From"
    c_until  = cols.get("until")  or cols.get("to")     or "Until"

    out = pd.DataFrame({
        "player_name": player_name,
        "team": team,
        "start_date": df[c_from].apply(lambda x: dtparse(str(x), dayfirst=False, fuzzy=True)),
        "end_date":   df[c_until].apply(lambda x: dtparse(str(x), dayfirst=False, fuzzy=True)),
        "type":       df[c_injury].astype(str).map(_clean_type),
        "source":     tm_inj_url
    }).dropna(subset=["start_date","end_date"])

    return out

def fetch_club_table(url_base: str, season_end_year: int, tag: str) -> pd.DataFrame:
    """
    url_base examples:
      Injuries:    https://www.transfermarkt.com/arsenal-fc/verletzungen/verein/11
      Suspensions: https://www.transfermarkt.com/arsenal-fc/sperren/verein/11
    Transfermarkt expects saison_id = season START year, i.e. (end_year - 1)
    """
    url = _with_query(url_base, saison_id=season_end_year - 1)
    html = _request(url)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.items")
    if table is None:
        return pd.DataFrame(columns=["player_name","team","start_date","end_date","type","source"])

    df = pd.read_html(str(table))[0]
    cols = {c.lower(): c for c in df.columns}
    c_player = cols.get("player") or cols.get("name") or list(df.columns)[0]
    c_from   = cols.get("from")   or cols.get("since") or "From"
    c_until  = cols.get("until")  or cols.get("to")    or "Until"
    c_reason = cols.get("injury") or cols.get("reason") or cols.get("suspension") or list(df.columns)[1]

    team_name = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
    out = pd.DataFrame({
        "player_name": df[c_player].astype(str).str.replace(r"\s+\(.*?\)$", "", regex=True),
        "team": team_name,
        "start_date": df[c_from].apply(lambda x: dtparse(str(x), dayfirst=False, fuzzy=True)),
        "end_date":   df[c_until].apply(lambda x: dtparse(str(x), dayfirst=False, fuzzy=True)),
        "type":       df[c_reason].astype(str).map(lambda s: "suspension" if tag == "susp" else _clean_type(s)),
        "source":     url
    }).dropna(subset=["start_date","end_date"])

    return out

def fetch_squad_player_urls(squad_base_url: str, season_start_year: int, team_label: str | None = None) -> pd.DataFrame:
    """
    squad_base_url example:
      https://www.transfermarkt.com/arsenal-fc/startseite/verein/11
    We append /saison_id/<YYYY> where YYYY is the *start* year (end_year-1).
    Returns: player_name, tm_url (injury history), team
    """
    url = squad_base_url.rstrip("/") + f"/saison_id/{season_start_year}"
    html = _request(url)
    soup = BeautifulSoup(html, "lxml")

    if team_label is None:
        h1 = soup.select_one("h1")
        team_label = h1.get_text(strip=True) if h1 else "Unknown Team"

    table = soup.select_one("table.items")
    if table is None:
        return pd.DataFrame(columns=["player_name","tm_url","team"])

    players = []
    for a in table.select("a[href*='/profil/spieler/']"):
        name = a.get_text(strip=True)
        href = a.get("href", "")
        if not name or not href:
            continue
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        profile_url = base + href
        injuries_url = profile_url.replace("/profil/", "/verletzungen/")
        players.append({"player_name": name, "tm_url": injuries_url, "team": team_label})

    return pd.DataFrame(players).drop_duplicates(subset=["tm_url"])

# ------------- builders -------------------

def build_from_player_url_df(season_end_year: int, url_df: pd.DataFrame) -> Path:
    rows = []
    for _, r in url_df.iterrows():
        nm, url, team = r["player_name"], r["tm_url"], r["team"]
        print(f"[{season_end_year}] {team} - {nm}")
        try:
            rows.append(fetch_player_injury_history(nm, url, team))
            time.sleep(0.6 + random.random() * 0.4)  # polite delay
        except Exception as e:
            print("  warn:", e)
    inj = (pd.concat(rows, ignore_index=True)
           if rows else pd.DataFrame(columns=["player_name","team","start_date","end_date","type","source"]))
    inj = _clip(inj, season_end_year)
    out = OUT_DIR / f"injuries_{season_end_year}.csv"
    inj.to_csv(out, index=False)
    print("Saved:", out, "rows=", len(inj))
    return out

def build_from_player_url_lists(season_end_year: int, club_files: list[Path]) -> Path:
    frames = []
    for f in club_files:
        if f.exists():
            frames.append(pd.read_csv(f))
    url_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["player_name","tm_url","team"])
    if url_df.empty:
        print("No player URL CSVs found.")
        return OUT_DIR / f"injuries_{season_end_year}.csv"
    return build_from_player_url_df(season_end_year, url_df)

def build_from_club_pages(season_end_year: int, club_injury_urls: list[str], club_susp_urls: list[str]) -> Path:
    rows = []
    for u in club_injury_urls:
        print(f"[{season_end_year}] club injuries:", u)
        try:
            rows.append(fetch_club_table(u, season_end_year, tag="inj"))
            time.sleep(0.8 + random.random() * 0.6)
        except Exception as e:
            print("  warn:", e)
    for u in club_susp_urls:
        print(f"[{season_end_year}] club suspensions:", u)
        try:
            rows.append(fetch_club_table(u, season_end_year, tag="susp"))
            time.sleep(0.8 + random.random() * 0.6)
        except Exception as e:
            print("  warn:", e)
    inj = (pd.concat(rows, ignore_index=True)
           if rows else pd.DataFrame(columns=["player_name","team","start_date","end_date","type","source"]))
    inj = _clip(inj, season_end_year)
    out = OUT_DIR / f"injuries_{season_end_year}.csv"
    inj.to_csv(out, index=False)
    print("Saved:", out, "rows=", len(inj))
    return out

# ------------- CLI ------------------------

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, required=True,
                   help="Season end year, e.g. 2024 for 2024/25")
    p.add_argument("--mode", choices=["players", "clubs", "squad"], default="players")

    # players mode
    p.add_argument("--club", action="append",
                   help="Club slug for URL CSVs: data/raw/injuries/urls/<season>/<club>_tm_urls.csv")

    # clubs mode
    p.add_argument("--injury-url", action="append",
                   help="Club injuries base URL(s), e.g. https://www.transfermarkt.com/arsenal-fc/verletzungen/verein/11")
    p.add_argument("--susp-url", action="append",
                   help="Club suspensions base URL(s), e.g. https://www.transfermarkt.com/arsenal-fc/sperren/verein/11")

    # squad mode
    p.add_argument("--squad-url", action="append",
                   help="Squad base URL(s): https://www.transfermarkt.com/<club>/startseite/verein/<id>")
    p.add_argument("--team-label", action="append",
                   help="Optional team labels for squad URLs (in same order)")

    args = p.parse_args()

    if args.mode == "players":
        clubs = args.club or []
        files: list[Path] = []
        if clubs:
            files = [Path(f"data/raw/injuries/urls/{args.season}/{c}_tm_urls.csv") for c in clubs]
        else:
            files = [Path(p) for p in glob.glob(f"data/raw/injuries/urls/{args.season}/*_tm_urls.csv")]
        build_from_player_url_lists(args.season, files)

    elif args.mode == "clubs":
        build_from_club_pages(args.season, args.injury_url or [], args.susp_url or [])

    else:  # squad
        if not args.squad_url:
            raise SystemExit("Provide at least one --squad-url for --mode squad")
        start_year = args.season - 1  # TM squad page wants season START year
        all_urls = []
        for i, u in enumerate(args.squad_url):
            lbl = args.team_label[i] if (args.team_label and i < len(args.team_label)) else None
            print(f"[{args.season}] reading squad: {u}")
            df_urls = fetch_squad_player_urls(u, season_start_year=start_year, team_label=lbl)
            if not df_urls.empty:
                all_urls.append(df_urls)
        if not all_urls:
            print("No players found from squad pages.")
            raise SystemExit(0)
        url_df = pd.concat(all_urls, ignore_index=True)
        build_from_player_url_df(args.season, url_df)
