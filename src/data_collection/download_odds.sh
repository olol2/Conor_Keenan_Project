#!/usr/bin/env bash
set -e

# Code used to import csv files from Football-Data.co.uk for the data analysis project
# Premier League odds and results data from seasons 2019-2020 to 2024-2025
for S in 1920 2021 2122 2223 2324 2425; do
  mkdir -p data/raw/Odds/results/$S
  curl -L -o data/raw/Odds/results/$S/E0.csv "https://www.football-data.co.uk/mmz4281/$S/E0.csv"
done
