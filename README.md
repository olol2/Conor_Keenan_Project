# Conor_Keenan_Project
**Fair Value in the Premier League** — MSc Finance  
Course: **Data Science and Advanced Programming (Capstone Project)**  
Author: **Conor Keenan**  
Institution: **HEC Lausanne, University of Lausanne**  
Seasons covered: **2019/20 to 2024/25** (6 seasons), **27 teams** (across promotions/relegations)

---

## 1. Project Overview

This project studies the relationship between **player rotation**, **injuries**, and **team performance** in the English Premier League.

The core deliverables are two player-season “proxy” measures:

- **Proxy 1 — Rotation Elasticity:** captures how selectively a player is used across match contexts (e.g., higher-stakes vs lower-stakes matches).
- **Proxy 2 — Injury Impact (DiD on xPts):** estimates the expected points impact of a player’s unavailability, aggregated to player-season level; can be mapped into monetary terms using a **£ per point** schedule.

The pipeline is built to be **reproducible for grading**: the grading entry point **does not scrape** external sources and instead relies on **pre-generated processed files** committed to the repository.

---

## 2. Research Question

1. How do **rotation dynamics** (Proxy 1) vary across players, teams, and seasons?
2. What is the **expected performance cost** of player injuries (Proxy 2), measured in **expected points (xPts)** and optionally in **£**?
3. Are the two proxies related (e.g., are highly rotated players also those with lower/higher injury impacts)?

---

## 3. Data

### 3.1 Data Sources (Raw)

This project uses public football data from multiple sources:

- **Football-Data (football-data.co.uk):** bookmaker odds + results (Premier League)
- **Understat:** player-level match statistics (minutes, starts, xG/xA, etc.)
- **Transfermarkt:** injury spells (start/end dates, injury type)
- **Premier League prize money tables:** used to map points to £ (value of league points)

### 3.2 Repository Convention

To ensure the project runs reliably for grading:

- `main.py` **does not** scrape or download anything.
- `main.py` starts from **already-prepared CSV/parquet files** under `data/processed/` (and reads/writes additional artifacts under `results/`).

> **Grading workflow does not require internet access.**

---

## 4. Repository Structure

High-level structure:

```text
Conor_Keenan_Project/
├── main.py
├── README.md
├── PROPOSAL.md
├── requirements.txt
├── environment.yml                    # optional (if present)
│
├── data/
│   ├── raw/                           # optional for reproduction from scratch
│   │   ├── Odds/results/*/E0.csv
│   │   └── understat_player_matches/understat_player_matches_*.csv
│   └── processed/                     # required by main.py
│       ├── panel_rotation.(parquet|csv)
│       ├── panel_injury.(parquet|csv)
│       ├── matches/                   # match-level panels (if included)
│       ├── injuries/                  # cleaned injury spells
│       ├── points_to_pounds/           # season-specific £/point mapping
│       └── standings/                 # league tables per season
│
├── results/
│   ├── figures/
│   ├── proxy1_rotation_elasticity.csv
│   ├── proxy2_injury_final_named.csv
│   ├── summary_rotation_proxy.csv
│   ├── summary_injury_proxy.csv
│   └── (other tables/figures produced by analysis scripts)
│
└── src/
    ├── data_collection/               # optional reproducibility scripts (not used by main.py)
    ├── proxies/                       # proxy construction code
    └── analysis/                      # summaries, validation, and plotting
```
## 5. Quickstart (How to Run)

### 5.1 Environment Setup

### Option A - Conda (if 'environment.yml' exists)

```bash
conda env create -f environment.yml
conda activate conor_keenan_project
```
### Option B -pip

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 5.2 Run the Full (Grading) Pipeline
 
 From the repository root:
```bash
python main.py
```

### 5.3 Expected Outputs

 Running main.py should generate:
  - Proxy output files (csv) in results/
  - Summary tables in results/
  - Figures in results/figures/

## 6. Methodology

### 6.1 Proxy 1 - Rotation Elasticity

**Goal**: quantify how a player's selection/usage changes across match contexts.

A typical operationalization used in this project:
  - Classify matches into difficulty bins (e.g., easy/medium/hard) using team-season-specific xPts terciles
  - Compute player start rates by bin
  - Define rotation elasticity as the difference between start rates across bins, e.g.:
      $\text{rotation\_elasticity} = \text{start\_rate}_{\text{hard}} - \text{start\_rate}_{\text{easy}}$

**Primary output**: results/proxy1_rotation_elasticity.csv

### 6.2 Proxy 2 - Injury impact via DiD (xPts)

**Goal**: estimate the marginal effect of a player being unavailable on the team's expected points.

High-level approach:
   - build a player-match panel containing team xPts, player availability, and match controls
   - estimate a DiD-style regression within player-team-season with fixed effects (e.g., opponent and matchday/date)
   - aggregate estimated effects into player-season totals (xPts) and optionally convert to GBP using a seasomn-specific mapping

**Primary output**: results/proxy2_injury_final_named.csv

**Interpretation note:** matches wioth multiple injuries may be included; coefficients are interpreted as marginal effects within the realised injury environment.

## 7. Running Individual Components (Optional/Development)

These commands are useful for debugging or re-running parts of the pipeline. Run from the repo root.

### 7.1 Summary + Validation

```bash
python src/analysis/proxy_summary_and_validation.py
```
### 7.2 Combine Proxies (if used)

```bash
python src/analysis/combine_proxies.py
```

### 7.3 Proxy Construction (if you want to re-run)

```bash
python src/proxies/proxy2_injury_did.py
```

## 8. Data Collection Scripts (Optional)
 This repository includes scripts under src/data_collection/ that document how the raw datasets were downloaded/scraped and consolidated into processed files.

 Because these sources are external websites and may block automated requests:
  - For the main pipeline, main.py **does not** scrape data, it takes the already processed csv files
  - Additionally, transfermarkt scraping can take around 20 minutes per season depending on the site and connection

## 9. Known Data Issues / Limitations

  - **Transfermarkt return dates vs actual returns**: predicted return dates may not match true return-to-play dates; this can create cases where a player is listed as unavailable but still played.
  - **Cross-source name matching**: Understat/Transfermarkt/Football-Data use different naming conventions for player and teams. Team-name master mappings were created to standardize joins.
  - **Match join drops**: a small number of Understat rows may fail to match the Football-Data match panel (e.g., date discrepencies) and were dropped from the final rotation panel.
  -**Player-ID coverage**: some injury-based player names cannot be matched to numeric Understat ID's due to naming inconsistencies; these observations may be excluded in combined_proxy analysis depending on the step.

  ## 10. Project Timeline

  - **06.11** Proposal Accepted
  - **11.11** Repository created
  - **14-19.11** Data collected (Football-Data, Understat, Transfermarkt, Premier League)
  - **27.11** Initial injury-cost processing and exploratory regressions
  - **01.12** Proxy 2 (injury DiD) and Proxy1 (Rotation Elasticity)
  - **05.12** Analysis
  - **08.12** 
  - **14-20.12** Final Phase: Validation, combined plots, and report-ready outputs

  ## 11. References/acknowledgements
  - Football-Data odds and results: football-data.co.uk
  - Understat player-match statistics (via community tooling)
  - Transfermarkt injury histories (scraped responsibly)
  - Premier League prize money tables (manually curated for points-to-£ mapping)

## 12. Contact

Author: **Conor Keenan**
E-mail: ***conor.keenan@unil.ch***

## Optional: data acquisition (scraping)
Raw data was originally collected via scraping scripts (Understat / Transfermarkt).
This step is NOT required for grading because the project includes the processed inputs needed
to run `python main.py` end-to-end.

Scraping was performed in a separate environment (`footy311`, Python 3.11) because some
scraping dependencies are more stable on Python 3.11 than on Python 3.13.

To re-run scraping (optional):
conda activate footy311
pip install -r requirements-scrape.txt
python src/data_collection/understat_fetch_players.py
