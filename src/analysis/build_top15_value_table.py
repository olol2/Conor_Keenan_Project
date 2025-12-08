# src/analysis/build_top15_value_table.py

from __future__ import annotations

from pathlib import Path
import pandas as pd

# This file lives in /files/Conor_Keenan_Project/src/analysis
ROOT = Path(__file__).resolve().parents[2]  # -> /files/Conor_Keenan_Project
RESULTS_DIR = ROOT / "results"


def df_to_markdown(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    """
    Minimal markdown table formatter that does NOT depend on 'tabulate'.
    """
    cols = list(df.columns)

    def fmt_val(v):
        if isinstance(v, float):
            return format(v, floatfmt)
        return str(v)

    # Header
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, row in df.iterrows():
        cells = [fmt_val(row[c]) for c in cols]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, sep] + rows)


def main() -> None:
    value_path = RESULTS_DIR / "player_value_table.csv"
    if not value_path.exists():
        raise FileNotFoundError(
            f"player_value_table.csv not found at {value_path}. "
            f"Run build_player_value_table.py first."
        )

    # Load the full value table
    tbl = pd.read_csv(value_path)

    if "combined_value_z" not in tbl.columns:
        raise ValueError(
            "Column 'combined_value_z' not found. "
            "Make sure build_player_value_table.py created it."
        )

    # Ensure combined_value_z is numeric
    tbl["combined_value_z"] = pd.to_numeric(
        tbl["combined_value_z"], errors="coerce"
    )

    # Keep only rows where the combined index is defined
    tbl = tbl.dropna(subset=["combined_value_z"])

    # Sort by combined value (highest first) and take top 15
    top = (
        tbl.sort_values("combined_value_z", ascending=False)
           .head(15)
    )

    # Pick nice columns for the report (only keep those that exist)
    cols = [
        "player_id",          # Understat numeric ID (if present)
        "player_name",
        "team_id",
        "season",
        "rotation_elasticity",
        "inj_xpts",          # season injury impact in xPts
        "inj_gbp",           # season injury impact in £
        "combined_value_z",
    ]
    cols = [c for c in cols if c in top.columns]
    top = top[cols]

    # Save as CSV for reference
    out_csv = RESULTS_DIR / "player_value_top15.csv"
    top.to_csv(out_csv, index=False)

    # Also save as markdown text for easy copy-paste into the report
    out_md = RESULTS_DIR / "player_value_top15.md"
    markdown = df_to_markdown(top, floatfmt=".2f")
    out_md.write_text(markdown, encoding="utf-8")

    print(f"✅ Saved top-15 player value table to {out_csv}")
    print(f"✅ Saved markdown version to {out_md}")
    print("\nPreview:")
    print(markdown)


if __name__ == "__main__":
    main()
