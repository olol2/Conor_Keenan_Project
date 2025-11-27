# src/models.py

from typing import Dict
import pandas as pd


def run_core_analysis(data: Dict[str, pd.DataFrame]):
    """
    Placeholder for your actual modelling.

    For now it can just return the data or a small summary; later
    you'll add the regression / xPts / injuries logic here.
    """
    standings = data["standings"].copy()
    summary = standings.groupby("Season")["Pts"].describe()

    return {"standings_summary": summary}
