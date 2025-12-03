# src/make_plots.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT_DIR / "results"

# Input tables created earlier
TOP10_2324_FILE = RESULTS_DIR / "report_top10_gbp_lost_2023_2024.csv"
TOP10_CLUBS_FILE = RESULTS_DIR / "report_top10_clubs_total_gbp_lost.csv"


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run make_report_tables.py first.")
    return pd.read_csv(path)


def plot_top10_2324():
    """Bar chart: top 10 £ lost to injuries in 2023-2024 season."""
    df = _load_csv(TOP10_2324_FILE)

    # Sort so biggest on top of the chart
    df = df.sort_values("gbp_lost_due_to_injuries", ascending=True)  # ascending for horizontal bar

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.barh(df["Team"], df["gbp_lost_due_to_injuries"])
    ax.set_xlabel("£ lost due to injuries (GBP)")
    ax.set_title("Top 10 clubs by £ lost to injuries – 2023-2024")

    # Add value labels on the bars (optional but nice)
    for i, v in enumerate(df["gbp_lost_due_to_injuries"]):
        ax.text(v, i, f"{v:,.0f}", va="center", ha="left", fontsize=8)

    fig.tight_layout()
    out_path = RESULTS_DIR / "fig_top10_gbp_lost_2023_2024.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_top10_clubs_overall():
    """Bar chart: top 10 clubs by total £ lost across all seasons."""
    df = _load_csv(TOP10_CLUBS_FILE)

    # we assume file is already sorted by total_gbp_lost desc
    df = df.sort_values("total_gbp_lost", ascending=True)

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.barh(df["Team"], df["total_gbp_lost"])
    ax.set_xlabel("Total £ lost due to injuries (GBP, 2019–2025 sample)")
    ax.set_title("Top 10 clubs by total £ lost to injuries")

    for i, v in enumerate(df["total_gbp_lost"]):
        ax.text(v, i, f"{v:,.0f}", va="center", ha="left", fontsize=8)

    fig.tight_layout()
    out_path = RESULTS_DIR / "fig_top10_total_gbp_lost_overall.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def main():
    plot_top10_2324()
    plot_top10_clubs_overall()


if __name__ == "__main__":
    main()
