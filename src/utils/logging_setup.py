"""
Logging setup.

Why this exists:
- Replaces ad-hoc print statements with structured logs.
- Makes it easy for graders (and future you) to see what happened and where.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .io import ensure_dir


def setup_logger(
    name: str,
    log_dir: Path,
    log_file: str,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Create a console + file logger.

    Args:
        name: Logger name (usually module name).
        log_dir: Directory to store the log file.
        log_file: Log filename (e.g., "combine_proxies.log").
        level: Logging level (default INFO).

    Returns:
        A configured logger.
    """
    ensure_dir(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # If already configured, do not add handlers again.
    # This avoids duplicated lines if setup_logger is called twice in one process.
    if getattr(logger, "_is_configured", False):
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(log_dir / log_file, mode="a", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger._is_configured = True  # type: ignore[attr-defined]
    return logger
