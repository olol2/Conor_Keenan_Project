# Conor_Keenan_Project
**Fair Value in the Premier League** — MSc Finance  
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
├── main.py
├── README.md
├── PROPOSAL.md
├── requirements.txt                  # grading/runtime dependencies
├── requirements-scrape.txt           # optional scraping dependencies
│
├── data/
│   ├── raw/                          # not required for grading (may be empty / partial)
│   └── processed/                    # required by main.py
│       ├── matches/
│       ├── injuries/
│       ├── understat/
│       ├── points_to_pounds/
│       ├── standings/
│       └── (panels created/updated by pipeline)
│
├── results/                          # outputs written by pipeline
│   ├── figures/                      # generated (ignored by git)
│   ├── logs/                         # generated (ignored by git)
│   ├── metadata/                     # generated (ignored by git)
│   └── (csv outputs; some are tracked, some ignored; see Section 7)
│
└── src/
    ├── data_collection/              # optional: reproduction from scratch (scraping)
    ├── proxies/                      # proxy construction
    └── analysis/                     # summaries, validation, plotting

```
## 5. Quickstart (How to Run)

### 5.1 Environment Setup

From the repository root:

```bash 
python install -r requirements.txt
```

### 5.2 Run the Full Pipeline (Grading Entry Point)
 
 From the repository root:
```bash
python main.py
```
This will run the full pipeline end-to-end using processed inputs in data/processed/ and will write outputs to results/.

### 5.3 Expected Outputs

 Running main.py should generate:
  - Proxy output files (csv) in results/
  - Summary tables in results/
  - Figures in results/figures/

## 6. Methodology

### 6.1 Proxy 1 - Rotation Elasticity

**Goal**: quantify how a player's selection/usage changes across match contexts.

Implementation (high level):
  - Classify matches into difficulty bins "easy" vs "hard" contexts using team-season difficulty signal.
  - Compute a player's start rates in each context.
  - Define:
$$
\text{rotation\_elasticity} = \text{start\_rate}_{\text{hard}} - \text{start\_rate}_{\text{easy}}
$$


**Key output**: results/proxy1_rotation_elasticity.csv

Interpretation: 
  - Positive values: player starts relatively more in hard matches than easy ones.
  - Negative values: player starts relatively more in easy matches than hard ones.
  - Near zero: player usage is comparatively stable across contexts.

### 6.2 Proxy 2 - Injury impact via DiD (Expected Points)

**Goal**: estimate the marginal effect of a player being unavailable on team expected points.

Implementation (high level):
   - Build a player-match panel with team xPts, player availability, and match controls.
   - Estimate within player-team-season, comparing "available vs unavailable" periods (DiD style logic).
   - Aggregate to player-season total impact in xPts and optionally convert to £ using a season-specific £ per point mapping.

**Key output**: results/proxy2_injury_final_named.csv

**Interpretation note:** Effects are interpreted as marginal impacts within the realized injury environment. Matches may contain multiple absences.

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
