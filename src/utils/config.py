"""
Central configuration loader.

Why this exists:
- Avoids hardcoding paths/seasons inside analysis scripts.
- Makes runs reproducible and easier for graders to execute.
- Provides one source of truth for pipeline parameters.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


def project_root() -> Path:
    """
    Return the project root directory.

    Why:
    - Allows absolute paths to be computed consistently regardless of where
      the script is launched from (terminal, IDE, grader runner, etc.).
    """
    # This file is in src/utils/, so parents[2] should be the repo root.
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    """
    Parsed project configuration (paths + key parameters).

    Notes:
    - We include `project_root` as a field so older scripts can do:
          cfg.project_root / "results" / "file.csv"
      without breaking.
    """

    # Project root (backward-compatible)
    project_root: Path

    # Paths
    raw: Path
    processed: Path
    results: Path
    figures: Path
    logs: Path
    metadata: Path

    # Seasons
    season_min: int
    season_max: int

    # Thresholds / knobs (add more as needed)
    min_matches_for_estimation: int

    @staticmethod
    def load(path: Path | None = None) -> "Config":
        """
        Load config.json and return a Config object.

        Args:
            path: Optional path to a config file. If None, uses <repo>/config.json.

        Returns:
            Config: A validated, path-resolved config object.
        """
        root = project_root()
        cfg_path = path or (root / "config.json")

        with cfg_path.open("r", encoding="utf-8") as f:
            d: Dict[str, Any] = json.load(f)

        paths = d["paths"]
        seasons = d["seasons"]
        thr = d.get("thresholds", {})

        # Resolve all paths relative to project root to avoid CWD issues.
        def p(rel: str) -> Path:
            return (root / rel).resolve()

        return Config(
            project_root=root.resolve(),
            raw=p(paths["data_raw"]),
            processed=p(paths["data_processed"]),
            results=p(paths["results"]),
            figures=p(paths["figures"]),
            logs=p(paths["logs"]),
            metadata=p(paths["metadata"]),
            season_min=int(seasons["min"]),
            season_max=int(seasons["max"]),
            min_matches_for_estimation=int(thr.get("min_matches_for_estimation", 0)),
        )
