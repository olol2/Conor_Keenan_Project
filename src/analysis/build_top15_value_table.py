"""
Create a "Top N" player value table for reporting.

Inputs:
  - results/player_value_table.csv
    (created by: python -m src.analysis.build_player_value_table)

Outputs:
  - player_value_top15.csv
  - player_value_top15.md

What it does:
- Loads the consolidated value table (player-seasons)
- Filters to rows where combined_value_z is defined
- Sorts descending by combined_value_z
- Exports the top N rows as CSV + a markdown table

Why this file exists:
- For visuals in reports / presentations
"""

from __future__ import annotations
from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from src.utils.io import atomic_write_csv

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def df_to_markdown(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    """
    Minimal markdown formatter.

    Design choices:
    - NaNs -> empty cells
    - integer-like floats (e.g., 2019.0) -> "2019"
    - other floats -> formatted using floatfmt (default ".2f")
    """
    cols = list(df.columns)

    def fmt_val(v) -> str:
        if pd.isna(v):
            return ""

        # Numpy/pandas ints
        if isinstance(v, (np.integer, int)):
            return str(int(v))

        # Floats: avoid "2019.0" if integer-like
        if isinstance(v, (np.floating, float)):
            vv = float(v)
            if np.isfinite(vv) and vv.is_integer():
                return str(int(vv))
            if np.isfinite(vv):
                return format(vv, floatfmt)
            return ""

        return str(v)

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, row in df.iterrows():
        cells = [fmt_val(row[c]) for c in cols]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, sep] + rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export a Top-N table from results/player_value_table.csv.")
    p.add_argument("--value-table", type=str, default=None, help="Override path to player_value_table.csv")
    p.add_argument("--top-n", type=int, default=15, help="Number of rows to export (default: 15)")
    p.add_argument("--out-csv", type=str, default=None, help="Override output CSV path")
    p.add_argument("--out-md", type=str, default=None, help="Override output Markdown path")
    p.add_argument("--dry-run", action="store_true", help="Compute + print preview, but do not write files")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    value_path = Path(args.value_table) if args.value_table else (RESULTS_DIR / "player_value_table.csv")
    if not value_path.exists():
        raise FileNotFoundError(
            f"player_value_table.csv not found at {value_path}. "
            "Run: python -m src.analysis.build_player_value_table"
        )

    out_csv = Path(args.out_csv) if args.out_csv else (RESULTS_DIR / f"player_value_top{args.top_n}.csv")
    out_md = Path(args.out_md) if args.out_md else (RESULTS_DIR / f"player_value_top{args.top_n}.md")

    # -----------------------
    # Load + basic validation
    # -----------------------
    tbl = pd.read_csv(value_path)
    tbl.columns = [c.strip() for c in tbl.columns]

    if "combined_value_z" not in tbl.columns:
        raise ValueError(
            "Column 'combined_value_z' not found in player_value_table.csv. "
            "Make sure build_player_value_table.py created it."
        )

    # Clean types for sorting/printing
    tbl["combined_value_z"] = pd.to_numeric(tbl["combined_value_z"], errors="coerce")

    if "season" in tbl.columns:
        tbl["season"] = pd.to_numeric(tbl["season"], errors="coerce").astype("Int64")

    # Ensure numeric-ish columns are numeric (if present)
    for c in ["rotation_elasticity", "inj_xpts", "inj_gbp"]:
        if c in tbl.columns:
            tbl[c] = pd.to_numeric(tbl[c], errors="coerce")

    # --------------------------------
    # Filter + take top N deterministically
    # --------------------------------
    before = len(tbl)
    tbl = tbl.dropna(subset=["combined_value_z"]).copy()
    after = len(tbl)

    top = (
        tbl.sort_values(
            ["combined_value_z", "season", "team_id", "player_name"],
            ascending=[False, True, True, True],
            na_position="last",
        )
        .head(int(args.top_n))
        .copy()
    )

    # Select "report-friendly" columns (keep only those that exist)
    cols = [
        "player_id",
        "player_name",
        "team_id",
        "season",
        "rotation_elasticity",
        "inj_xpts",
        "inj_gbp",
        "combined_value_z",
    ]
    cols = [c for c in cols if c in top.columns]
    top = top[cols].copy()

    # Markdown output
    markdown = df_to_markdown(top, floatfmt=".2f")

    # -----------------------
    # Print useful diagnostics
    # -----------------------
    print(f"Loaded value table: {value_path} | rows={before}")
    print(f"Kept rows with combined_value_z: {after} ({after/before:.1%} of total)")
    print(f"Top N exported: {len(top)} (requested {args.top_n})")
    print("\nPreview:\n")
    print(markdown)

    if args.dry_run:
        print("\n✅ dry-run complete | no files written")
        return

    # -----------------------
    # Write outputs
    # -----------------------
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    atomic_write_csv(top, out_csv, index=False)
    out_md.write_text(markdown, encoding="utf-8")

    print(f"\n✅ Saved CSV: {out_csv}")
    print(f"✅ Saved Markdown: {out_md}")


if __name__ == "__main__":
    main()
