# Conor_Keenan_Project
Fair Value in the Premier League - MSc Finance - Data Science and Advanced Programming (Capstone Project)

## Project Plan
See [PROPOSAL.md](PROPOSAL.md).

## Repo Map
- [PROPOSAL.md](PROPOSAL.md)
- Code: `src/`
- Tests: `tests/`
- Docs: `docs/`
- Examples: `examples/`
- Results/figures: `results/`

## Additions of details of project
Will be on 5 seasons 19-20, 20-21, 21-22, 22-23, 23-24 and then tested on season N°6: 24-25            

## Project process

06.11: Project Proposal was accepted

11.11: Created a Github repository for my project

### Data Collection process

14.11: Added team Data for each season - Football-data.co.uk, downloaded csv directly from website
    -> This data consistent of every league game of the season, with very detailed team statistics and most importantly betting odds.
    -> into E0.csv files, which were used to create Expected Points per team, per game, per season

19.11: Added Per Player Per Match Data - understat (package aid on github)
    -> This data provided basic in game stats per player for every single game, starter or benched, minutes played, goals, assists, expected goals and expected assists.
    -> into understat_player_matches_20XX.csv files for XXX

       Added player injuries data by scraping data off transfermarkt.com.
    -> Provides ever players injuries start date and end date and injury type
    -> used for regression on expected money lost due to injury (in processed data as I scraped the data)

       Added manually data from PL.com in regards to prize money distributed to each team and their position in the league table
    -> used calculate expected cost of injuries   
### Data manipulation
PROJECT 1: team-level injury

27.11: Created a PL table of each season thanks to E0.csv files
       Created a points to point table per season
       Created a table for injury cost/point
       Created a table for injury cost/pound (thanks to point -> pound mapping)
       Did a regression and created many different tables, plots for these findings
       -> can show much more, analysis yet to be done
       
01.12: Start Proxy 2 - Injury DiD
    "Within club-season, estimate ATT on xPts from odds for matches with vs without Player X using two-way FE (opponent & date), clustered SEs; exclude multi-injury/suspension spells."

    1 problem occured:
    “In the baseline specification we allow matches with multiple injured players. The DiD coefficient should therefore be interpreted as the marginal effect of the focal player within the realised injury environment.” decide to not exclude multi-injury/suspesnion spells.

    Created build_injury_panel that allowed to create the proxy in proxies folder under name proxy2...

01.12: Start Proxy 1 - Rotation Elasticity


### Analysis

Could maybe make interactive plots, to see which players are where in plots

## Data

The project uses public football data from several sources. All files needed to reproduce the results are included in the repository. Some data has been scraped using API's or other personal features. main.py only uses the csv files created from scraping the data from external sources.

### Raw data (`data/raw/`)

These are external inputs that are **not** created by `main.py`:

- `data/raw/Odds/results/*/E0.csv`  
  Premier League match odds and results from [football-data.co.uk] scraped using 
  src/data_collection/download_odds.py 
  One CSV per season (2019–2020 to 2024–2025).
  ->mainly used for ranking difficulty of games for each team and obviously results.

- `data/raw/understat_player_matches/understat_player_matches_*.csv`  
  Per-player, per-match statistics (minutes, xG, xA, goals, assists) scraped from Understat **once** using src/data_collection/understat_fetch_players.py  
  ->mainly used for player statistics used in both proxies

- `data/raw/pl_prize_money.csv`  
  Data was manually imported from the official Premier League website, showing a PDF table of rankings and prize money per year.
  ->used to calculate "price of a point" used in DiD

### Processed inputs (`data/processed/`)

These files are cleaned / curated versions of the raw data that the analysis builds on:

- `data/processed/injuries/injuries_20xx.csv`  
  Player injury/suspension spells by season, collected from Transfermarkt and manually cleaned.  
  The scraping step was done in a separate environment (pycharm). at first it worked in nuvolos (src/data_collection/fetch_injuries_tm.py), but when testing again, it only worked in pycharm; the final per-season CSVs are included here.
  ->mainly used for absence due to injury information

- `data/processed/matches/*.csv`  
  Team-match level data for each season, including xPts derived from betting odds and injury counts with standardised team names.
  src/proxies/build_match_panel.py and add_injuries_to_matches.py
  ->used to link injuries to games used in DiD proxy.

- `data/processed/points_to_pounds/*.csv`  
  Mapping from league points to GBP value for each season, takes info from prize_money.csv and standings.
  src/proxies/make_points_to_pounds.py
  ->used to "value" points into currency (GBP)

- `data/processed/standings/*.csv`  
  Final league tables (position, points) for each season. calculated from odds_master using src/make_standings.py.
  ->instead of importing league table, it is possible to make code that will create a league table, as we have information about wins and goal difference, which is all that is needed for these standings in our calculations.

- `data/processed/panel_injury.parquet (.csv)`  
  Player–match–season panel used for the injury DiD proxy. Created a parquet to work on it as is "smaller" and quicker. Outputet a csv to read and have as a visual.

- `data/processed/panel_rotation.parquet (.csv)`  
  Player–match–season panel used for the rotation elasticity proxy.Created a parquet to work on it as is "smaller" and quicker. Outputet a csv to read and have as a visual.

  The four different sources provide different team names for unique teams (e.g. Manchester United, Man United, Man Utd), master csv files were created to have all seasons in one file with standardised names. src/data_collection/ : 
  build_odds_master.py , build_understat_master.py.


`main.py` assumes that all of the above files are present. It does **not** re-download or re-scrape any external data; it starts from these CSV/parquet files and reproduces all panels, proxies, and figures.

The scripts for data_collection which can not be done manually have been included in the src/data_collection folder.

Potential inconsistencies:
 panel_injury.csv transfermarkt will put injury down from x date to recovery date, but in reality some players can come back before their predicted return which would show inconsistencies if a player is "unavailable" but still played the game. just a disagreement between two sourcess.

 panel_rotation.csv Understat player-match data were merged to the match panel on season, date and team. A small number of Understat rows (around 2–3k across all seasons) did not have an exact match in the Football-Data results (for example due to date discrepancies) and were dropped. The final rotation panel therefore contains only matches present in both sources.

 ### Main Project code
  src/proxies
  ## Proxy 2 : Injury DiD
  proxy2_injury_summary.py: When aligning the injury-based DiD proxy with the Understat-based rotation proxy, around 18% of player–season observations could not be matched to a numeric Understat ID (based on name + team). These players are excluded from the combined proxy, so the final analysis focuses on players for whom both rotation and injury information are available.

## Data collection (optional)

This project includes data-collection scripts (e.g., Understat/Transfermarkt scraping) used to build the processed datasets.  
Because these sources are external websites and may change or block automated requests, **data collection is not required for reproducing the results for grading**.

All analysis scripts and the final pipeline operate on the **pre-generated CSV files** stored under:

- `data/processed/` (processed match/player panels)
- `results/` (proxy outputs and analysis-ready tables)
This makes your intent unambiguous:

```markdown
The grading workflow does not require internet access; `main.py` uses only the included CSV files.

Data collection and preprocessing (optional)

This repository includes src/data_collection/ scripts that document how the raw datasets were downloaded and consolidated into the processed CSV files committed under data/processed/.

Important: The grading entrypoint main.py does not scrape websites or download external data. It reads the already-prepared CSVs from data/processed/ (and/or results/) to ensure the project runs reliably on the grader’s machine.

What is in src/data_collection/?

These scripts are provided for transparency and reproducibility:

download_odds.py
Downloads Premier League odds CSVs from football-data.co.uk into:

data/raw/Odds/results/<season>/E0.csv
This script is optional and not used by main.py.

fetch_injuries_tm.py
Scrapes injury/suspension spells from Transfermarkt and writes:

data/processed/injuries_<season_end_year>.csv
This script is optional and not used by main.py (scraping can be slow and depends on external website availability).

build_injuries_all_seasons.py
Combines the per-season injury CSVs into one standardized master file:

data/processed/injuries/injuries_2019_2025_all_seasons.csv
Includes canonical team-name mapping and basic validation.

Two master-builder scripts (latest)

These two scripts consolidate raw per-season files into “master” processed datasets used downstream:

build_understat_master.py
Builds a single Understat player-match master CSV from per-season files in:

Input: data/raw/understat_player_matches/understat_player_matches_20*.csv

Output: data/processed/understat/understat_player_matches_master.csv
Adds season labels and standardizes team names.

build_odds_master.py
Builds a single odds master CSV from the football-data season folders:

Input: data/raw/Odds/results/<season>/E0.csv

Output: data/processed/odds/odds_master.csv
Adds season metadata and a match identifier for later joins.

Proxies (src/proxies/)

This folder contains the end-to-end code used to construct the two core “proxy” measures used in the analysis, plus supporting preprocessing utilities. Each script is designed to be runnable from the command line (typically via python -m ...) and writes its outputs to either data/processed/ (intermediate panels/mappings) or results/ (final proxy outputs and tables). Most scripts also support a --dry-run mode to validate inputs and run the full computation without writing files.

Proxy 1: Rotation Elasticity (Squad Rotation Proxy)

Script: proxy1_rotation_elasticity.py

Inputs: data/processed/panel_rotation.parquet

Method: For each team-season, matches are classified into hard/medium/easy using team-season-specific xPts terciles. For each player–team–season, the script computes start rates in hard vs easy matches and defines rotation elasticity as:
rotation_elasticity = start_rate_hard − start_rate_easy
This captures whether a player is preferentially started in higher-stakes matches relative to lower-stakes matches.

Output: results/proxy1_rotation_elasticity.csv

Proxy 2: Injury Impact via Difference-in-Differences (Injury Proxy)

Proxy 2 is built in multiple steps:

Build the player–team–match injury panel

Script: build_injury_panel.py

Inputs:

data/processed/matches/matches_with_injuries_all_seasons.csv (match-level xPts + squad injury counts)

data/processed/injuries/injuries_2019_2025_all_seasons.csv (injury spells)

data/processed/understat/understat_player_matches_master.csv (minutes/starts)

Output: data/processed/panel_injury.parquet and data/processed/panel_injury.csv

Panel definition: One row per (match_id, team_id, player_name) with availability (unavailable), minutes and starting status.

Estimate player-season DiD effects

Script: proxy2_injury_did.py

Input: data/processed/panel_injury.parquet

Method: Runs a per player–team–season DiD-style regression of team xPts on player unavailability, controlling for opponent and matchday fixed effects.

Outputs: results/proxy2_injury_did.parquet and results/proxy2_injury_did.csv

Convert xPts effects into season totals and £ values

Script: proxy2_injury_did_points.py

Inputs:

results/proxy2_injury_did.parquet

data/processed/points_to_pounds/points_to_pounds_*.csv (season-specific £/point mapping)

Outputs: results/proxy2_injury_did_points_gbp.parquet and results/proxy2_injury_did_points_gbp.csv

Attach consistent numeric Understat player IDs

Script: proxy2_injury_summary.py

Inputs:

results/proxy2_injury_did_points_gbp.csv

data/processed/understat/understat_player_matches_master.csv

Output: results/proxy2_injury_final_named.csv

Note: Some injury-based player names cannot be matched to an Understat numeric ID due to naming inconsistencies across sources; these rows retain the name but have missing player_id.

Supporting utilities

League standings builder: make_standings.py
Builds final league tables from data/processed/odds/odds_master.csv, writing per-season standings files to data/processed/standings/ and a combined file standings_all_seasons.csv. These are used downstream for prize-money/points mappings.

src/analysis/ — Analysis, figures, validation, and report tables

This folder contains the “analysis layer” of the project: sanity checks, summary/validation outputs, and all figures/tables used in the report. These scripts consume outputs produced by the data processing and proxy-building steps (mainly from data/processed/ and results/) and write report-ready artifacts into results/ and results/figures/.

Key conventions

Inputs: read from results/ (proxy outputs) and occasionally data/processed/.

Outputs: written to:

results/figures/ (PNG/HTML figures)

results/ (tables, summaries, markdown snippets)

results/metadata/ (run metadata JSON when enabled)

Many scripts support a --dry-run flag to validate inputs and column requirements without writing files.

Most scripts can be run either as a module (python -m ...) or as a file (python src/analysis/...py), depending on how the repository is configured.

Summary + validation

proxy_summary_and_validation.py
Creates summary tables for both proxies and runs a simple validation check between them.

Reads:

results/proxy1_rotation_elasticity.csv

results/proxy2_injury_final_named.csv

Writes:

results/summary_rotation_proxy.csv

results/summary_injury_proxy.csv

results/proxy_validation_rotation_vs_injury.txt

results/figures/proxy_validation_rotation_vs_injury_scatter.png

results/figures/proxy2_total_injury_xpts_by_club.png

Run:

python -m py_compile src/analysis/proxy_summary_and_validation.py
python -m src.analysis.proxy_summary_and_validation

Proxy-specific figures

fig_proxy1_rotation.py
Generates visualisations for Proxy 1 (rotation elasticity), such as histogram, top players, team distributions, and season trend.

Reads: results/proxy1_rotation_elasticity.csv

Writes (examples):

results/figures/proxy1_hist_rotation_elasticity.png

results/figures/proxy1_team_boxplot_rotation_elasticity.png

results/figures/proxy1_trend_rotation_elasticity_by_season.png

Run:

python -m py_compile src/analysis/fig_proxy1_rotation.py
python -m src.analysis.fig_proxy1_rotation --dry-run
python -m src.analysis.fig_proxy1_rotation


fig_proxy2_injury.py
Generates figures for Proxy 2 (injury DiD), including top injured player-seasons and club-level injury totals (xPts or £).

Reads: results/proxy2_injury_final_named.csv

Writes (examples):

results/figures/proxy2_top10_injury_xpts.png

results/figures/proxy2_club_injury_bill.png

Run:

python -m py_compile src/analysis/fig_proxy2_injury.py
python -m src.analysis.fig_proxy2_injury --dry-run
python -m src.analysis.fig_proxy2_injury

Combined proxy figures

proxies_combined_plots.py
Creates a static scatter plot relating Proxy 1 (rotation) to Proxy 2 (injury xPts) using the combined proxies file.

Reads: results/proxies_combined.csv

Writes:

results/figures/proxies_scatter_rotation_vs_injury_xpts.png

Run:

python -m py_compile src/analysis/proxies_combined_plots.py
python -m src.analysis.proxies_combined_plots --dry-run
python -m src.analysis.proxies_combined_plots


fig_combined_proxies.py (interactive)
Builds an interactive Plotly scatter (HTML) of rotation elasticity vs injury xPts.

Reads: results/proxies_combined.csv

Writes:

results/figures/proxies_scatter_rotation_vs_injury_xpts_interactive.html

Run:

python -m py_compile src/analysis/fig_combined_proxies.py
python -c "import src.analysis.fig_combined_proxies as m; print('import-ok')"
python -m src.analysis.fig_combined_proxies

Report tables

build_player_value_table.py
Creates a consolidated player-value table by combining proxy outputs and computing z-scores plus a simple combined index.

Reads: results/proxies_combined.csv

Writes:

results/player_value_table.csv

Run:

python -m py_compile src/analysis/build_player_value_table.py
python -m src.analysis.build_player_value_table --dry-run
python -m src.analysis.build_player_value_table


build_top15_value_table.py
Creates a “Top 15” table (CSV + Markdown) for direct inclusion in the report.

Reads: results/player_value_table.csv

Writes:

results/player_value_top15.csv

results/player_value_top15.md

Run:

python -m py_compile src/analysis/build_top15_value_table.py
python -m src.analysis.build_top15_value_table

Quick “is everything OK?” checks

Common checks used across scripts:

# Syntax
python -m py_compile src/analysis/<script>.py

# Import wiring
python -c "import src.analysis.<script_module> as m; print('import-ok')"

# Dry-run (if supported)
python -m src.analysis.<script_module> --dry-run

------------------------------------------------------------------
# Player Rotation, Injuries and Expected Points in the Premier League

Final project for **Data Science and Advanced Programming 2025**  
HEC Lausanne, University of Lausanne  
Author: **Conor Keenan**

---

## 1. Project Overview

This project studies the relationship between **player rotation**, **injuries**, and **team performance** in the English Premier League.

The main goals are:

- To build a **rotation proxy** that captures how “rotatable” a player is within their team (rotation elasticity).
- To build an **injury cost proxy** that measures the expected league points lost due to a player’s injuries.
- To explore how these two proxies are related and which players provide the best “value” considering both rotation and injury impact.

The analysis covers Premier League seasons **2019–2020 to 2024–2025** for **27 teams**, using match-level and player-level data.

---

## 2. Data

### 2.1 Data sources

The project uses data from several public sources:

- **Understat**: player-level match statistics and xG/xPts.
- **Transfermarkt**: injury histories and absence periods.
- **Football-Data / odds files**: bookmaker odds used to derive expected points.
- **Premier League prize money**: to map league points into pound values (£ per point).

### 2.2 Processed data used by the main pipeline

To keep the main pipeline fast and reproducible for grading, all heavy data collection and preprocessing has already been run. The key processed files are stored in:

- `data/processed/`  
  - `panel_rotation.csv`  
    Final player–season panel for the **rotation proxy**.
  - `panel_injury.csv`  
    Final player–season panel for the **injury proxy** (expected points lost).

These processed panels are what `main.py` uses. You do **not** need to re-scrape data or rebuild all intermediate files to run the main analysis.

---

## 3. Methodology (high-level)

- **Rotation proxy (Proxy 1 – rotation elasticity)**  
  For each player-season, the project estimates how a player’s minutes vary relative to changes in match context (e.g. expected points, fixture congestion). This yields a **rotation elasticity** measure per player-season.

- **Injury proxy (Proxy 2 – expected points lost)**  
  Using a difference-in-differences setup on match-level **expected points**, the project estimates how much each injury event reduces the team’s expected points. These match-level effects are then aggregated to player-season level and mapped into monetary terms using a **£ per point** schedule.

- **Validation & combined analysis**  
  The proxies are validated via:
  - summary statistics (distributions, coverage),
  - correlation between rotation elasticity and injury impact,
  - club-level aggregates and visualizations.

All the code for these steps lives in the `src/` folder (see structure below). The main entry point for grading reuses the final panels and runs summary + validation.

More detail is provided in the report (`project_report.md` / `project_report.pdf`).

---

## 4. Repository Structure

At a high level:

```text
Conor_Keenan_Project/
├── main.py                  # Entry point for graders (uses processed panels)
├── README.md
├── PROPOSAL.md
├── project_report.md        # Markdown report (source)
├── project_report.pdf       # Final report (PDF, generated from MD)
├── requirements.txt
│
├── data/
│   ├── raw/                 # Raw inputs (odds, understat, injuries, etc.) – not all required to run main.py
│   └── processed/           # Processed datasets used by main.py
│       ├── panel_rotation.csv
│       └── panel_injury.csv
│
├── results/
│   ├── figures/             # Generated figures
│   ├── summary_rotation_proxy.csv
│   ├── summary_injury_proxy.csv
│   └── proxy_validation_rotation_vs_injury.txt
│
├── notebooks/               # Optional exploratory notebooks
│
└── src/
    ├── __init__.py
    │
    ├── data_loader.py       # Loads processed panels from data/processed
    ├── evaluation.py        # Runs summary + validation pipeline
    ├── full_pipeline.py     # (Optional) Full end-to-end rebuild from raw data
    │
    ├── data_collection/     # Scripts to build raw/processed datasets from sources
    ├── proxies/             # Construction of rotation & injury proxies
    ├── analysis/            # Summary tables, validation, and figures
    └── legacy/              # Older or experimental code kept for reference
