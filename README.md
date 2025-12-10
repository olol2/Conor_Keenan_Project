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
