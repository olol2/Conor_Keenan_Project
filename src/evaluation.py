# src/evaluation.py

from pathlib import Path
from typing import Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_core_results(results: Dict):
    """Save result tables / figures to the results/ folder."""

    # 1) Descriptive summaries
    by_season = results.get("injury_summary_by_season")
    if isinstance(by_season, pd.DataFrame):
        out_path = RESULTS_DIR / "injury_summary_by_season.csv"
        by_season.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

    overall = results.get("injury_summary_overall")
    if isinstance(overall, pd.DataFrame):
        out_path = RESULTS_DIR / "injury_summary_overall.csv"
        overall.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

    # 2) Regression coefficient table
    coef = results.get("injury_reg_coef")
    if isinstance(coef, pd.DataFrame):
        out_path = RESULTS_DIR / "injury_regression_coefficients.csv"
        coef.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

    # 3) Full regression summary text
    summary_text = results.get("injury_reg_summary_text")
    if isinstance(summary_text, str):
        out_path = RESULTS_DIR / "injury_regression_summary.txt"
        with open(out_path, "w") as f:
            f.write(summary_text)
        print(f"Saved {out_path}")
