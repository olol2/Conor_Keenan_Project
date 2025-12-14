from __future__ import annotations

from pathlib import Path
import os
import pandas as pd


def ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def atomic_write_csv(df: pd.DataFrame, out_path: Path, index: bool = False) -> None:
    """Write a CSV atomically (write temp -> rename)."""
    ensure_dir(out_path.parent)

    tmp_path = out_path.with_suffix(out_path.suffix + f".tmp.{os.getpid()}")
    try:
        df.to_csv(tmp_path, index=index)
        tmp_path.replace(out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def atomic_write_parquet(df: pd.DataFrame, out_path: Path, index: bool = False) -> None:
    """Write a parquet atomically (write temp -> rename)."""
    ensure_dir(out_path.parent)

    tmp_path = out_path.with_suffix(out_path.suffix + f".tmp.{os.getpid()}")
    try:
        df.to_parquet(tmp_path, index=index)
        tmp_path.replace(out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
