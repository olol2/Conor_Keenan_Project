# main.py
"""
Minimal project orchestrator.

Purpose:
- Provide a single entrypoint to reproduce the key outputs.
- Keep orchestration thin: run existing modules in a sensible order.
- Robust to where certain scripts live (src.proxies vs src.analysis).
"""

from __future__ import annotations

import os
import subprocess
import sys
import importlib.util
from pathlib import Path


def module_exists(module: str) -> bool:
    """Return True if `python -m <module>` should be importable."""
    return importlib.util.find_spec(module) is not None


def run_module(module: str, *args: str) -> None:
    """Run a module via `python -m module ...` and fail fast on error."""
    cmd = [sys.executable, "-m", module, *args]
    print("\n" + "=" * 80)
    print("RUN:", " ".join(cmd))
    print("=" * 80)
    subprocess.run(cmd, check=True)


def run_first_available(candidates: list[str], *args: str) -> str:
    """
    Try multiple module paths and run the first one that exists.
    Returns the module path used.
    """
    for m in candidates:
        if module_exists(m):
            run_module(m, *args)
            return m
    raise ModuleNotFoundError(
        "None of these modules exist:\n  - " + "\n  - ".join(candidates)
    )


def main() -> None:
    # Ensure consistent working directory.
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    # -------------------------
    # Build / refresh panels
    # -------------------------
    run_module("src.proxies.build_injury_panel")
    run_module("src.proxies.build_rotation_panel")
    # -------------------------
    # Proxy 2 (injury): DiD -> points/£ -> attach Understat ID
    # -------------------------
    run_module("src.proxies.proxy2_injury_did")
    run_module("src.proxies.proxy2_injury_did_points")
    run_module("src.proxies.proxy2_injury_summary")

    # -------------------------
    # Proxy 1 (rotation)
    # -------------------------
    run_module("src.proxies.proxy1_rotation_elasticity")

    # -------------------------
    # Combine proxies + derived tables
    # (combine_proxies might live in src.proxies or src.analysis)
    # -------------------------
    run_first_available(
        ["src.analysis.combine_proxies", "src.proxies.combine_proxies"]
    )

    run_module("src.analysis.build_player_value_table")

    # -------------------------
    # Validation + key figures (static)
    # -------------------------
    run_module("src.analysis.proxy_summary_and_validation")
    run_module("src.analysis.fig_proxy1_rotation")
    run_module("src.analysis.fig_proxy2_injury")
    run_module("src.analysis.proxies_combined_plots")

    # -------------------------
    # Optional: interactive plot (Plotly)
    # (only run if module exists in your repo)
    # -------------------------
    if module_exists("src.analysis.fig_combined_proxies"):
        run_module("src.analysis.fig_combined_proxies")

    print("\n✅ Pipeline complete.")


if __name__ == "__main__":
    main()
