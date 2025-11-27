# src/evaluation.py

from pathlib import Path
from typing import Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_core_results(results: Dict):
    """Save any result tables / figures to the results/ folder."""

    summary = results.get("standings_summary")
    if isinstance(summary, (pd.Series, pd.DataFrame)):
        summary.to_csv(RESULTS_DIR / "standings_summary.csv")
