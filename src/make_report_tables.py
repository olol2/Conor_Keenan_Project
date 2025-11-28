# src/make_report_tables.py

from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"

RANKINGS_FILE = RESULTS_DIR / "injury_cost_rankings_by_season.csv"
CLUB_SUMMARY_FILE = RESULTS_DIR / "injury_cost_club_summary.csv"


def load_rankings() -> pd.DataFrame:
    if not RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"{RANKINGS_FILE} not found. "
            "Run src/summarise_injury_costs.py first."
        )
    return pd.read_csv(RANKINGS_FILE)


def load_club_summary() -> pd.DataFrame:
    if not CLUB_SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"{CLUB_SUMMARY_FILE} not found. "
            "Run src/summarise_injury_costs.py first."
        )
    return pd.read_csv(CLUB_SUMMARY_FILE)


def top_n_for_season(df: pd.DataFrame, season: str, n: int = 10) -> pd.DataFrame:
    sub = df[df["Season"] == season].copy()
    if sub.empty:
        raise ValueError(f"No rows found for Season = {season}")
    sub = sub.sort_values("gbp_lost_due_to_injuries", ascending=False)
    return sub.head(n)


def main():
    rankings = load_rankings()
    club_summary = load_club_summary()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1) Top 10 £ lost in 2023-2024 (last complete season) ------------
    try:
        top_2324 = top_n_for_season(rankings, "2023-2024", n=10)
        out1 = RESULTS_DIR / "report_top10_gbp_lost_2023_2024.csv"
        top_2324.to_csv(out1, index=False)
        print(f"Saved {out1}")
    except ValueError as e:
        print(e)

    # --- 2) Top 10 £ lost in 2024-2025 (current season), if available ----
    try:
        top_2425 = top_n_for_season(rankings, "2024-2025", n=10)
        out2 = RESULTS_DIR / "report_top10_gbp_lost_2024_2025.csv"
        top_2425.to_csv(out2, index=False)
        print(f"Saved {out2}")
    except ValueError as e:
        print(e)

    # --- 3) Overall top 10 clubs by total £ lost -------------------------
    top_clubs = club_summary.head(10)
    out3 = RESULTS_DIR / "report_top10_clubs_total_gbp_lost.csv"
    top_clubs.to_csv(out3, index=False)
    print(f"Saved {out3}")


if __name__ == "__main__":
    main()
