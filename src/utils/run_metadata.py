"""
Run metadata capture.

Why this exists:
- Helps you prove reproducibility (time, python version, key packages, git commit).
- Makes debugging much faster when outputs differ between runs/machines.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys
from importlib import metadata as importlib_metadata

from .io import ensure_dir


def _git_commit_hash() -> str | None:
    """
    Try to read the current git commit hash.

    Why:
    - Links results to a specific code state.
    - If git is unavailable (e.g., zipped submission), it safely returns None.
    """
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return None


def _safe_version(pkg: str) -> str | None:
    """Return installed package version, or None if not installed."""
    try:
        return importlib_metadata.version(pkg)
    except Exception:
        return None


def write_run_metadata(out_dir: Path, run_name: str, extra: dict | None = None) -> Path:
    """
    Write a JSON file describing the execution environment.

    Args:
        out_dir: Directory to save metadata (e.g., results/metadata).
        run_name: Short identifier (e.g., "combine_proxies").
        extra: Optional additional metadata (e.g., season range, parameters).

    Returns:
        Path to the written JSON file.
    """
    ensure_dir(out_dir)

    meta = {
        "run_name": run_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_commit": _git_commit_hash(),
        # Keep the list small and relevant—avoid huge environment dumps.
        "packages": {
            "pandas": _safe_version("pandas"),
            "numpy": _safe_version("numpy"),
            "statsmodels": _safe_version("statsmodels"),
            "matplotlib": _safe_version("matplotlib"),
            "requests": _safe_version("requests"),
            "beautifulsoup4": _safe_version("beautifulsoup4"),
            "plotly": _safe_version("plotly"),
            "argv": sys.argv,

        },
        "extra": extra or {},
    }

    out_path = out_dir / f"{run_name}_metadata.json"
    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_path
