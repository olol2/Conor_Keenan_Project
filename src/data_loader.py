# src/data_loader.py

""" This module contains functions to load the processed data files used in analysis and modeling.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


# Project root: Conor_Keenan_Project
ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = ROOT / "data" / "processed"


def load_rotation_panel() -> pd.DataFrame:
    """Load final rotation panel from processed data."""
    path = DATA_PROCESSED / "panel_rotation.csv"
    df = pd.read_csv(path)
    return df


def load_injury_panel() -> pd.DataFrame:
    """Load final injury panel from processed data."""
    path = DATA_PROCESSED / "panel_injury.csv"
    df = pd.read_csv(path)
    return df


def load_all_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function used by main.py:
    returns (rotation_panel, injury_panel).
    """
    rot = load_rotation_panel()
    inj = load_injury_panel()
    print(f"Loaded rotation panel: {len(rot)} rows")
    print(f"Loaded injury panel:   {len(inj)} rows")
    return rot, inj
