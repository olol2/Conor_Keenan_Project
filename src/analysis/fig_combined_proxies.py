# src/analysis/fig_combined_proxies_interactive.py

from __future__ import annotations
"""
Interactive scatter of the two player-value proxies:

- x-axis: rotation_elasticity (proxy 1)
- y-axis: season injury impact in xPts (inj_xpts, proxy 2)

Output:
    results/figures/proxies_scatter_rotation_vs_injury_xpts_interactive.html
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

COMBINED_FILE = RESULTS_DIR / "proxies_combined.csv"
OUT_HTML = FIG_DIR / "proxies_scatter_rotation_vs_injury_xpts_interactive.html"


def main() -> None:
    # -----------------------------------------------------------------
    # 1) Load combined proxies
    # -----------------------------------------------------------------
    if not COMBINED_FILE.exists():
        raise FileNotFoundError(
            f"{COMBINED_FILE} not found. Run src/proxies/combine_proxies.py first."
        )

    df = pd.read_csv(COMBINED_FILE)

    # Ensure we have an injury-in-points column called inj_xpts
    if "inj_xpts" not in df.columns and "xpts_season_total" in df.columns:
        df = df.rename(columns={"xpts_season_total": "inj_xpts"})

    required = {"rotation_elasticity", "inj_xpts"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns {missing} in {COMBINED_FILE}.\n"
            f"Available columns: {list(df.columns)}"
        )

    # Coerce to numeric just in case
    df["rotation_elasticity"] = pd.to_numeric(df["rotation_elasticity"], errors="coerce")
    df["inj_xpts"] = pd.to_numeric(df["inj_xpts"], errors="coerce")

    sub = df.dropna(subset=["rotation_elasticity", "inj_xpts"])
    print("Rows with both proxies:", len(sub))
    if len(sub) == 0:
        print("No overlap between proxies; skipping scatter.")
        return

    # Optional: correlation as a quick summary
    corr = sub["rotation_elasticity"].corr(sub["inj_xpts"])
    print(f"Correlation (rotation_elasticity vs inj_xpts): {corr:.3f}")

    # -----------------------------------------------------------------
    # 2) Build a clean label for hover: 'Player (Team Season)'
    # -----------------------------------------------------------------
    if "player_name" in sub.columns:
        player_col = "player_name"
    elif "player_id" in sub.columns:
        player_col = "player_id"
    else:
        sub["player_name"] = sub.index
        player_col = "player_name"

    team_col = "team_id" if "team_id" in sub.columns else None
    season_col = "season" if "season" in sub.columns else None

    label = sub[player_col].astype(str)
    if team_col is not None:
        label = label + " (" + sub[team_col].astype(str)
        if season_col is not None:
            label = label + " " + sub[season_col].astype(str)
        label = label + ")"
    sub["label"] = label

    # -----------------------------------------------------------------
    # 3) Symmetric axes around zero
    # -----------------------------------------------------------------
    x = sub["rotation_elasticity"].to_numpy(dtype=float)
    y = sub["inj_xpts"].to_numpy(dtype=float)

    x_max = float(np.nanmax(np.abs(x)))
    y_max = float(np.nanmax(np.abs(y)))

    # Slight padding so points are not on the frame
    x_lim = 1.05 * x_max if x_max > 0 else 1.0
    y_lim = 1.05 * y_max if y_max > 0 else 1.0

    # -----------------------------------------------------------------
    # 4) Plotly scatter
    # -----------------------------------------------------------------
    color_col = team_col  # colour by team

    fig = px.scatter(
        sub,
        x="rotation_elasticity",
        y="inj_xpts",
        color=color_col,
        hover_name="label",
        labels={
            "rotation_elasticity": "Rotation elasticity (hard - easy)",
            "inj_xpts": "Season injury impact in xPts",
            color_col: "Team" if color_col else "",
        },
        title="Relationship between rotation role and injury impact (interactive)",
        template="simple_white",
    )

    # Zero lines
    fig.add_vline(x=0.0, line_dash="dash", line_color="gray", opacity=0.6)
    fig.add_hline(y=0.0, line_dash="dash", line_color="gray", opacity=0.6)

    # Symmetric limits
    fig.update_xaxes(range=[-x_lim, x_lim])
    fig.update_yaxes(range=[-y_lim, y_lim])

    # Cleaner hover box
    fig.update_traces(
        marker=dict(size=8),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Rotation elasticity: %{x:.3f}<br>"
            "Season injury impact: %{y:.2f} xPts<br>"
            "<extra></extra>"
        ),
        customdata=sub[["label"]].to_numpy(),
    )

    # -----------------------------------------------------------------
    # 5) Save HTML
    # -----------------------------------------------------------------
    fig.write_html(OUT_HTML, include_plotlyjs="cdn")
    print(f"✅ Saved interactive figure to {OUT_HTML}")


if __name__ == "__main__":
    main()
