#!/usr/bin/env bash
set -e

# Code used to import csv files from Football-Data.co.uk for data analysis project
for S in 1920 2021 2122 2223 2324 2425; do
  mkdir -p data/raw/$S
  curl -L -o data/raw/$S/E0.csv "https://www.football-data.co.uk/mmz4281/$S/E0.csv"
done
