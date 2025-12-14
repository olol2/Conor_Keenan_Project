"""
Validation checks for intermediate and final datasets.

Why this exists:
- Converts "it seems right" into enforceable guarantees.
- Prevents silent errors (bad merges, missing columns, empty outputs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    """Lightweight structure if you later want non-fatal checks."""
    ok: bool
    message: str


def require_columns(df: pd.DataFrame, cols: Sequence[str], name: str = "df") -> None:
    """
    Assert that required columns exist.

    Why:
    - Merge/transform code often fails later with confusing errors.
    - This gives an immediate, readable failure message.
    """
    if df is None:
        raise ValueError(f"[{name}] DataFrame is None.")

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"[{name}] Missing required columns: {missing}")


def assert_non_empty(df: pd.DataFrame, name: str = "df") -> None:
    """
    Assert that a DataFrame has at least one row.

    Why:
    - Empty outputs usually indicate upstream filtering bugs, broken scraping,
      or incorrect merge keys.
    """
    if df is None or df.empty:
        raise ValueError(f"[{name}] DataFrame is empty.")


def assert_unique_key(df: pd.DataFrame, key_cols: Sequence[str], name: str = "df") -> None:
    """
    Assert that key columns uniquely identify rows.

    Why:
    - Prevents accidental many-to-many merges (which silently inflate counts).
    - Makes your unit-of-analysis explicit (e.g., player-season is unique).
    """
    require_columns(df, key_cols, name=name)
    dup = int(df.duplicated(list(key_cols)).sum())
    if dup > 0:
        raise ValueError(f"[{name}] Found {dup} duplicate rows on key {list(key_cols)}.")


def assert_in_range(
    df: pd.DataFrame,
    col: str,
    low: float | None = None,
    high: float | None = None,
    name: str = "df",
    *,
    allow_na: bool = True,
    require_numeric: bool = False,
) -> None:
    """
    Assert numeric values fall within a range.

    Why:
    - Catches unit mistakes (minutes vs seconds), parsing errors, or bad merges.

    Args:
        allow_na: If True, ignore NaNs when checking the range.
        require_numeric: If True, fail if coercion to numeric produces any NaNs.
    """
    require_columns(df, [col], name=name)

    s = pd.to_numeric(df[col], errors="coerce")

    if require_numeric:
        n_bad = int(s.isna().sum())
        if n_bad > 0:
            raise ValueError(
                f"[{name}] Column '{col}' has {n_bad} non-numeric/NaN values after coercion."
            )

    if not allow_na and s.isna().any():
        raise ValueError(f"[{name}] Column '{col}' contains missing values but allow_na=False.")

    s2 = s.dropna() if allow_na else s

    if low is not None:
        bad = int((s2 < low).sum())
        if bad > 0:
            raise ValueError(f"[{name}] Column '{col}' has {bad} values < {low}.")

    if high is not None:
        bad = int((s2 > high).sum())
        if bad > 0:
            raise ValueError(f"[{name}] Column '{col}' has {bad} values > {high}.")


def assert_no_inf(df: pd.DataFrame, col: str, name: str = "df") -> None:
    """
    Assert a numeric column does not contain +/- inf.

    Why:
    - Stats/plots can explode if inf values sneak in.
    """
    require_columns(df, [col], name=name)
    s = pd.to_numeric(df[col], errors="coerce")
    n_inf = int(np.isinf(s.to_numpy(dtype=float, copy=False)).sum())
    if n_inf > 0:
        raise ValueError(f"[{name}] Column '{col}' contains {n_inf} inf values.")


def report_missingness(df: pd.DataFrame, cols: Iterable[str] | None = None) -> pd.Series:
    """
    Return missingness rates per column (fraction missing).

    Why:
    - Lets you log or save a compact view of data quality after key steps.
    """
    if df is None:
        raise ValueError("[df] DataFrame is None.")
    use = list(cols) if cols is not None else list(df.columns)
    return df[use].isna().mean().sort_values(ascending=False)
