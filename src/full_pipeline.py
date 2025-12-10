from __future__ import annotations

"""
Full end-to-end pipeline.

Run with:
    python -m src.full_pipeline
"""

# 1) DATA PREPARATION / COLLECTION
from src.data_collection.build_injuries_all_seasons import main as build_injuries_all_seasons
from src.data_collection.build_match_panel import main as build_match_panel
from src.proxies.add_injuries_to_matches import main as add_injuries_to_matches
from src.data_collection.build_understat_master import main as build_understat_master

# 2) PANELS
from src.proxies.build_injury_panel import main as build_injury_panel
from src.proxies.build_rotation_panel import main as build_rotation_panel

# 3) INJURY PROXY (proxy 2)
from src.proxies.proxy2_injury_did import main as run_injury_did
from src.proxies.make_points_to_pounds import main as make_points_to_pounds
from src.proxies.proxy2_injury_did_points import main as add_points_and_gbp
from src.proxies.proxy2_injury_summary import main as build_injury_final_named

# 4) ROTATION PROXY (proxy 1)
from src.proxies.proxy1_rotation_elasticity import main as build_rotation_proxy

# 5) COMBINE + ANALYSIS / FIGURES
from src.analysis.combine_proxies import main as combine_proxies
from src.analysis.build_player_value_table import main as build_player_value_table
from src.analysis.build_top15_value_table import main as build_top15_value_table
from src.analysis.proxy_summary_and_validation import main as proxy_summary_and_validation
from src.analysis.fig_proxy1_rotation import main as fig_rotation
from src.analysis.fig_proxy2_injury import main as fig_injury
from src.analysis.proxies_combined_plots import main as fig_combined
from src.analysis.fig_combined_plots import main as fig_combined  # adjust if filename differs
# from src.analysis.fig_combined_proxies_interactive import main as fig_combined_interactive

def main() -> None:
    print("=== STEP 1: Base processed data ===")
    build_injuries_all_seasons()
    build_match_panel()
    add_injuries_to_matches()
    build_understat_master()

    print("\n=== STEP 2: Build panels ===")
    build_injury_panel()
    build_rotation_panel()

    print("\n=== STEP 3: Injury proxy (DiD + points + £) ===")
    run_injury_did()
    make_points_to_pounds()
    add_points_and_gbp()
    build_injury_final_named()

    print("\n=== STEP 4: Rotation proxy ===")
    build_rotation_proxy()

    print("\n=== STEP 5: Combine proxies & build outputs ===")
    combine_proxies()
    build_player_value_table()
    build_top15_value_table()
    proxy_summary_and_validation()
    fig_rotation()
    fig_injury()
    fig_combined()
    # fig_combined_interactive()

    print("\n✅ Full pipeline finished successfully.")


if __name__ == "__main__":
    main()
