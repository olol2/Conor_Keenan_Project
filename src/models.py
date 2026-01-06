# src/models.py
"""
Model / proxy construction entry point.

This project implements "models" as proxy-building modules under `src.proxies`.
This file is a thin wrapper for template compatibility.

Run from repo root:
    python -m src.models
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    # Run whichever proxy pipeline you want as the "models" entrypoint.
    # Keep this thin and delegate to the real modules in src.proxies.
    modules = [
        "src.proxies.build_injury_panel",
        "src.proxies.build_rotation_panel",
        "src.proxies.proxy2_injury_did",
        "src.proxies.proxy2_injury_did_points",
        "src.proxies.proxy2_injury_summary",
        "src.proxies.proxy1_rotation_elasticity",
    ]

    for m in modules:
        cmd = [sys.executable, "-m", m]
        print("RUN:", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
