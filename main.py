# src/main.py
from __future__ import annotations
"""
Master pipeline runner for the project.

Run from the project root as:

    python -m src.main

This will:

  1) Build base processed data (matches, injuries, understat master, etc.)
  2) Build player–match panels (injury + rotation)
  3) Estimate the injury proxy (DiD + points + £)
  4) Estimate the rotation proxy
  5) Combine proxies, build value tables, and generate key figures

Adjust imports below if any script paths or names differ slightly
(e.g. if you move scripts between src/data_collection, src/proxies, src/analysis, etc.).
"""

# ---------------------------------------------------------------------
# Imports: call each script's `main()` in order
# ---------------------------------------------------------------------

# 1) DATA PREPARATION / COLLECTION
from .data_collection.build_injuries_all_seasons import main as build_injuries_all_seasons
from .build_match_panel import main as build_match_panel
from .proxies.add_injuries_to_matches import main as add_injuries_to_matches
from .analysis.build_understat_master import main as build_understat_master  # adjust path if needed

# 2) PANELS
from .proxies.build_injury_panel import main as build_injury_panel
from .proxies.build_rotation_panel import main as build_rotation_panel

# 3) INJURY PROXY (proxy 2)
from .proxies.proxy2_injury_did import main as run_injury_did
from .proxies.make_points_to_pounds import main as make_points_to_pounds
from .proxies.proxy2_injury_did_points import main as add_points_and_gbp
from .proxies.proxy2_injury_summary import main as build_injury_final_named

# 4) ROTATION PROXY (proxy 1)
from .proxies.proxy1_rotation_elasticity import main as build_rotation_proxy

# 5) COMBINE + ANALYSIS / FIGURES
from .analysis.combine_proxies import main as combine_proxies
from .analysis.build_player_value_table import main as build_player_value_table
from .analysis.build_top15_value_table import main as build_top15_value_table
from .analysis.proxy_summary_and_validation import main as proxy_summary_and_validation
from .analysis.fig_proxy1_rotation import main as fig_rotation
from .analysis.fig_proxy2_injury import main as fig_injury
from .analysis.proxies_combined_plots import main as fig_combined
from .analysis.fig_combined_proxies_interactive import main as fig_combined_interactive


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------

def main() -> None:
    # ---------- STEP 1: Base processed data ----------
    print("=== STEP 1: Base processed data ===")
    # Requires: raw injuries per season in data/processed/injuries
    build_injuries_all_seasons()

    # Requires: football-data odds in data/raw/Odds/results/*/E0.csv
    build_match_panel()

    # Requires: matches_all_seasons + per-season injuries_*.csv
    add_injuries_to_matches()

    # Requires: raw Understat per-season match files in data/raw/understat_player_matches
    build_understat_master()

    # ---------- STEP 2: Panels ----------
    print("\n=== STEP 2: Build panels ===")
    # Uses: matches_with_injuries_all_seasons + injuries
    build_injury_panel()

    # Uses: matches_with_injuries_all_seasons + Understat per-player matches
    build_rotation_panel()

    # ---------- STEP 3: Injury proxy (DiD + points + £) ----------
    print("\n=== STEP 3: Injury proxy (DiD + points + £) ===")
    # Uses: panel_injury.parquet
    run_injury_did()

    # Uses: standings_*.csv + pl_prize_money.csv
    make_points_to_pounds()

    # Uses: proxy2_injury_did.parquet + points_to_pounds_*.csv
    add_points_and_gbp()

    # Uses: proxy2_injury_did_points_gbp.csv + understat master
    build_injury_final_named()

    # ---------- STEP 4: Rotation proxy ----------
    print("\n=== STEP 4: Rotation proxy ===")
    # Uses: panel_rotation.parquet
    build_rotation_proxy()

    # ---------- STEP 5: Combine + value tables + figures ----------
    print("\n=== STEP 5: Combine proxies & build outputs ===")
    # Uses: proxy1_rotation_elasticity.csv + proxy2_injury_final_named.csv
    combine_proxies()

    # Uses: proxies_combined.csv
    build_player_value_table()
    build_top15_value_table()

    # Uses: rotation & injury proxies
    proxy_summary_and_validation()

    # Figures
    fig_rotation()
    fig_injury()
    fig_combined()
    fig_combined_interactive()

    print("\n✅ Pipeline finished successfully.")


if __name__ == "__main__":
    main()
