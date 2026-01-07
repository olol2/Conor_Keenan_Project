# Conor_Keenan_Project
**Fair Value in the English Premier League** — MSc Finance  
Course: **Data Science and Advanced Programming (Capstone Project)**  
Author: **Conor Keenan**  
Institution: **HEC Lausanne, University of Lausanne**  
Seasons covered: **2019/20 to 2024/25** (6 seasons), **27 teams** (across promotions/relegations)

---

## 1. Project Overview

This project studies the relationship between **player rotation**, **injuries**, and **team performance** in the English Premier League (EPL).

The core deliverables are two player-season proxy measures:

- **Proxy 1 — Rotation Elasticity:** captures how selectively a player is used across match contexts (e.g., higher-stakes vs lower-stakes matches).
- **Proxy 2 — Injury Impact (DiD on xPts):** estimates the expected points impact of a player’s unavailability, aggregated to player-season level; optionally mapped to **£** using a **£ per point** schedule.

### Reproducibility / Grading Contract (Important)
- The grading entry point is **`main.py`**.
- **`main.py` does not scrape** external websites and is designed to run **without internet access**.
- The pipeline starts from **pre-generated processed inputs** committed under **`data/processed/`** and writes outputs to **`results/`**.

---

## 2. Research Questions

1. How do **rotation dynamics** (Proxy 1) vary across players, teams, and seasons?
2. What is the **expected performance cost** of player injuries (Proxy 2), measured in **expected points (xPts)** and optionally in **£**?
3. Are the two proxies related (e.g., are highly rotated players also those with lower/higher injury impacts)?

---

## 3. Data

### 3.1 Data Sources (Raw / External)
Raw data originally came from public football sources:
- **Football-Data (football-data.co.uk):** match results and bookmaker odds (Premier League)
- **Understat:** player-match statistics (minutes, starts, xG/xA, etc.)
- **Transfermarkt:** injury spells (start/end dates, injury type)
- **Premier League prize money tables / points value:** mapping points to £ by season (used for conversion)

### 3.2 Repository Convention
To ensure the project runs reliably for grading:
- `main.py` **does not** download/scrape anything.
- `main.py` begins from **processed inputs** under `data/processed/`.
- Outputs are written to `results/`.

---

## 4. Repository Structure

```text
Conor_Keenan_Project/
├── main.py                      # single entrypoint
├── README.md
├── PROPOSAL.md
├── AI_USAGE.md
├── environment.yml              # conda environment
├── requirements.txt             # grading/runtime dependencies
│
├── data/
│   ├── raw/                     # optional (not required for main.py)
│   └── processed/               # required inputs for pipeline
│
├── results/                     # pipeline outputs (figures/tables/metadata)
│
└── src/
    ├── data_collection/         # optional: scraping/build-from-scratch scripts
    ├── proxies/                 # proxy construction (rotation/injury)
    ├── analysis/                # validation, tables, figures
    ├── data_loader.py           # convenience loader for processed panels (optional)
    ├── models.py                # optional: template wrapper
    └── evaluation.py            # evaluation shim (optional)
```

## 5. Quickstart (How to Run)

### 5.1 Environment Setup

From the repository root:

```bash 
conda env create -f environment.yml
conda activate Conor_Keenan_Project
```
(or with pip):
```bash 
pip install -r requirements.txt
```

### 5.2 Run the Full Pipeline
 
 From the repository root:
```bash
python main.py
```
This will run the full pipeline end-to-end using processed inputs in data/processed/ and will write outputs to results/.

Runtime note: starting from data/processed/, the pipeline should complete in a few minutes on a typical laptop.

### 5.3 Expected Outputs

### Notes on outputs (generated at runtime)

Running `python main.py` writes results to `results/` and creates lightweight run artifacts:

- `results/figures/`: figures regenerated each run.
- `results/metadata/`: JSON metadata per step (inputs, parameters, timestamps) for reproducibility/debugging (not tracked in Git).
- `results/logs/` (if present): execution logs for traceability (not tracked in Git).
- `results/`: CSV outputs regenerated each run.

Core deliverables used in the report include:
- `results/proxy1_rotation_elasticity.csv`
- `results/proxy2_injury_final_named.csv`
- `results/summary_rotation_proxy.csv`
- `results/summary_injury_proxy.csv`
- `results/proxies_combined.csv`

## 6. Methodology

### 6.1 Proxy 1 - Rotation Elasticity

**Goal**: quantify how a player's selection/usage changes across match contexts.

Implementation (high level):
  - Classify matches into difficulty bins "easy" vs "hard" contexts using team-season difficulty signal.
  - Compute a player's start rates in each context.
  - Define:
          rotation_elasticity = start_rate_hard - start_rate_easy


**Key output**: results/proxy1_rotation_elasticity.csv

Interpretation: 
  - Positive values: player starts relatively more in hard matches rather than easy ones.
  - Negative values: player starts relatively more in easy matches rather than hard ones.
  - Near zero: player usage is comparatively stable across contexts.

### 6.2 Proxy 2 - Injury impact via DiD (Expected Points)

**Goal**: estimate the marginal effect of a player being unavailable on team expected points.

Implementation (high level):
- Build a player-match panel with team xPts, player availability, and match controls.
- Estimate within player-team-season, comparing "available vs unavailable" periods (DiD-style logic).
- Aggregate to player-season total impact in xPts and optionally convert to £ using a season-specific £ per point mapping.

**Key output**: `results/proxy2_injury_final_named.csv`

**Interpretation note:** Effects are interpreted as marginal impacts within the realized injury environment. Matches may contain multiple absences.

---

## 7. Running Individual Components (Optional/Development)

Run all commands from the **repository root**.

### 7.1 Build Panels

```bash
python -m src.proxies.build_rotation_panel
python -m src.proxies.build_injury_panel
```
### 7.2 Build Proxies

```bash
python -m src.proxies.proxy1_rotation_elasticity
python -m src.proxies.proxy2_injury_did
python -m src.proxies.proxy2_injury_did_points
python -m src.proxies.proxy2_injury_summary
```

### 7.3 Combine + Analysis Outputs

```bash
python -m src.proxies.combine_proxies
python -m src.analysis.build_player_value_table
python -m src.analysis.proxy_summary_and_validation
python -m src.analysis.fig_proxy1_rotation
python -m src.analysis.fig_proxy2_injury
python -m src.analysis.proxies_combined_plots
python -m src.analysis.fig_combined_proxies
```

## 8. Optional: Data Acquisition (Scraping)

The `main.py` pipeline does not scrape (Transfermarkt scraping can take multiple hours), which is why all required inputs are already committed under `data/processed/`.

Scraping scripts are provided for documentation/reproducibility under `src/data_collection/`, but they may be slower and less stable due to external website constraints and typically require internet access.

> Note: Scripts in `src/data_collection/` are optional and not used by `main.py`. Depending on your local VS Code interpreter/linter configuration, you may see lint warnings for these files even though they run correctly.

---

## 9. Known Data Issues / Limitations

- **Transfermarkt return dates vs actual returns**: listed return dates may differ from true return-to-play dates, creating occasional availability inconsistencies.
- **Cross-source name matching**: Understat / Transfermarkt / Football-Data use different naming conventions; standardized mappings are used but some mismatches remain.
- **Match join drops**: a small number of Understat rows may not match the match panel (e.g., date discrepancies) and are dropped from the rotation panel build.
- **Player-ID coverage**: some injury player names cannot be matched to Understat numeric IDs; these observations may be excluded in cross-proxy merges.

---

## 10. Reproducibility Notes

- **Grading entry point:** `python main.py`
- **No internet required for grading:** the pipeline starts from `data/processed/`.
- **Python version:** developed and tested on Python 3.11+ for the `main.py` pipeline.

---

## 11. References / Acknowledgements

- Football-Data (EPL odds/results): football-data.co.uk
- Understat player-match statistics (via community tooling)
- Transfermarkt injury histories (scraped responsibly)
- Premier League prize money tables (manually curated for points-to-£ mapping)

---

## 12. Contact

Author: **Conor Keenan**  
E-mail: ***conor.keenan@unil.ch***

---
