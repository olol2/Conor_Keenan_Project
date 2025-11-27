# src/evaluation.py

from pathlib import Path
from typing import Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_core_results(results: Dict):
    """Save result tables / figures to the results/ folder."""

    # Save injury summaries if present
    by_season = results.get("injury_summary_by_season")
    if isinstance(by_season, (pd.Series, pd.DataFrame)):
        out_path = RESULTS_DIR / "injury_summary_by_season.csv"
        by_season.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

    overall = results.get("injury_summary_overall")
    if isinstance(overall, (pd.Series, pd.DataFrame)):
        out_path = RESULTS_DIR / "injury_summary_overall.csv"
        overall.to_csv(out_path, index=False)
        print(f"Saved {out_path}")
