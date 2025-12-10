from __future__ import annotations

from src.data_loader import load_all_panels
from src.evaluation import run_full_evaluation


def main() -> None:
    """
    Entry point for the project for grading.

    Steps:
      1) Load final rotation and injury panels from data/processed.
      2) Run the evaluation script to create summary tables and figures.
    """
    print("=== Conor_Keenan_Project: starting main pipeline ===")

    rotation, injury = load_all_panels()
    print(
        f"Loaded rotation panel: {len(rotation)} rows, "
        f"{rotation['season'].nunique()} seasons, "
        f"{rotation['team_id'].nunique()} teams."
    )
    print(
        f"Loaded injury panel:   {len(injury)} rows, "
        f"{injury['season'].nunique()} seasons, "
        f"{injury['team_id'].nunique()} teams."
    )

    run_full_evaluation()

    print("=== Pipeline completed successfully ===")


if __name__ == "__main__":
    main()
