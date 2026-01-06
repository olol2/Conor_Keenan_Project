# src/evaluation.py
"""
Evaluation / visualization entry point.

This module is intentionally thin. It delegates to the analysis pipeline
and can run evaluation directly via:

    python -m src.evaluation
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    # Run the evaluation/validation script as a module to avoid import/path issues.
    cmd = [sys.executable, "-m", "src.analysis.proxy_summary_and_validation"]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
