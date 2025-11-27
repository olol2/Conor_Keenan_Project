# main.py

from src.data_loader import load_processed_data
from src.models import run_core_analysis
from src.evaluation import save_core_results


def main():
    # 1) Load the main processed datasets
    data = load_processed_data()

    # 2) Run your core modelling pipeline
    results = run_core_analysis(data)

    # 3) Save tables / figures to results/
    save_core_results(results)


if __name__ == "__main__":
    main()
