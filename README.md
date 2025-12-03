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

Need to verify consistency in code with different team names (e.g. Man Utd, Manchester Utd, Man United, Manchester United)

Could maybe make interactive plots, to see which players are where in plots

## Data

The project uses public football data from several sources. All files needed to reproduce the results are included in the repository. Some data has been scraped using API's or other personal features. main.py only uses the csv files created from scraping the data from external sources.

### Raw data (`data/raw/`)

These are external inputs that are **not** created by `main.py`:

- `data/raw/Odds/results/*/E0.csv`  
  Premier League match odds and results from [football-data.co.uk].  
  One CSV per season (2019–2020 to 2024–2025).
  ->mainly used for ranking difficulty of games for each team and obviously results.

- `data/raw/understat_player_matches/understat_player_matches_*.csv`  
  Per-player, per-match statistics (minutes, xG, xA, goals, assists) scraped from Understat **once** using a separate script.  
  The scraping code is not part of the main pipeline; the cleaned CSVs are provided here as starting data.

- `data/raw/pl_prize_money.csv`  
  Data was manually imported from the official Premier League website, showing a table of rankings and prize money per year.

### Processed inputs (`data/processed/`)

These files are cleaned / curated versions of the raw data that the analysis builds on:

- `data/processed/injuries/injuries_20xx.csv`  
  Player injury/suspension spells by season, collected from Transfermarkt and manually cleaned.  
  The scraping step was done in a separate environment (pycharm) at first it worked in nuvolos, but when testing again, it only worked in pycharm; the final per-season CSVs are included here.

- `data/processed/matches/*.csv`  
  Team-match level data for each season, including xPts derived from betting odds and injury counts.

- `data/processed/points_to_pounds/*.csv`  
  Mapping from league points to GBP value for each season.

- `data/processed/standings/*.csv`  
  Final league tables (position, points) for each season.

- `data/processed/panel_injury.parquet`  
  Player–match–season panel used for the injury DiD proxy.

- `data/processed/panel_rotation.parquet`  
  Player–match–season panel used for the rotation elasticity proxy.

`main.py` assumes that all of the above files are present. It does **not** re-download or re-scrape any external data; it starts from these CSV/parquet files and reproduces all panels, proxies, and figures.

The scripts for data_collection which can not be done manually have been included in the src/data_collection folder.

