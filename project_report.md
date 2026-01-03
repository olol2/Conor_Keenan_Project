# Abstract

Rotation and injury-related absences are routinely cited as drivers of team performance in the English Premier League (EPL), yet they are rarely quantified in a player-specific, season-comparable way using public data. This project addresses that measurement gap by constructing two interpretable player-season proxies that link squad management decisions and availability shocks to performance outcomes. 
Using match-level lineups and injury logs across six seasons (2019/20–2024/25) and 27 teams (including promoted and relegated clubs), I define match context via opponent strength and estimate **Rotation Elasticity** as the change in a player’s starting likelihood between “hard” and “easy” fixtures. I also estimate **Injury Impact** by comparing team outcomes during a player’s injury absences to within-team baselines, reducing sensitivity to persistent team quality. Performance is measured primarily in expected points (xPts) and can be expressed in approximate monetary terms (GBP) through the financial stakes of league position. Empirically, both proxies exhibit substantial heterogeneity across roles and squads: Rotation Elasticity is concentrated near zero on average but shows wide dispersion, while Injury Impact is more negative for high-usage players, consistent with larger marginal losses when core starters are unavailable. The main contribution is a reproducible pipeline and dataset of player-season measures enabling downstream ranking, profiling, and squad-level aggregation.


**Keywords:** Data Science, Python, Sports Analytics, Football, Premier League, Expected Points, Player Availability, Squad Rotation

\newpage

# Table of Contents

1. [Introduction](#introduction)
2. [Literature Review](#literature-review)
3. [Methodology](#methodology)
4. [Results](#results)
5. [Discussion](#discussion)
6. [Conclusion](#conclusion)
7. [References](#references)
8. [Appendices](#appendices)

\newpage

# 1. Introduction

**Background and motivation**

The EPL is one of the most prominent football leagues globally in terms of viewership, competetive intensity and financial stakes. Clubs operate under tight constraints such as congested match calendars, high physical demands and substantial incentives linked to league position through broadcast revenue, prize money and European qualification. Within this environment, teams continuously manage two closely related challenges:

First, rotation decisions determine how minutes and starts are allocated across the squad. Managers must balance short-term match objectives against longer-horizon considerations such as fatigue accumulation, readiness across competitions, and injury prevention. Second, injury risk and player availability constrain selection decisions. Injuries disrupt planned lineups, force tactical adjustments, and can shift responsibilities to less-preferred alternatives—effects that may be meaningful even when traditional season totals (minutes, appearances, goals/assists) appear similar across players.

Despite extensive discussion in football analytics and the industry, quantifying rotation and injury impact in a manner that is player-specific, season-comparable and outcome-linked remains non-trivial. Standard descriptive statistics typically do not capture when a player is used (e.g., whether a player is trusted in higher-difficulty fixtures) or the performance cost of a player's unavailability in a way that can be compared across teams and seasons.

- **Problem statement**

The central problem addressed in this report is measurement. Rotation and injury impact are frequently referenced qualitatively, but rigorous player-season quantification requires defining match context consistently, dealing with selection effects (e.g., stronger players start more often), and separating the effect of a player’s absence from broader team dynamics such as tactics, form, and opponent quality. Moreover, because verified medical datasets are rarely available publicly, the approach must remain robust to the limitations of public injury logs.

Accordingly, the project asks whether robust, interpretable player-season measures can be constructed from broadly obtainable lineup and injury data to capture context-dependent rotation and the performance cost of injury-related unavailability. 

To address this objective, the report is structured into three research questions:
1. **Rotation behavior:** Do teams systematically vary the probability that a given player starts depending on match difficulty and can this be summarized as a player-season statistic?
2. **Injury-related performance cost:** When a player is unavailable due to injury, what is the associated change in team performance, and can this be attributed at the player-season level in a comparable way?
3. **"Fair value" interpretation:** Do the resulting proxies provide meaningful differentiation between players (e.g., core starters vs. situational players; high-impact absences vs. low-impact absences) that complements conventional performance measures?

- **Objectives and goals**:
The project’s objective is not to directly estimate transfer fees or wages, but to provide actionable inputs for downstream analysis in scouting, squad planning, and performance diagnostics. Specifically, the project aims to produce two proxy measures with four design properties: interpretability, scalability, reproducibility, and season comparability.

The deliverables include:
        **Proxy 1 - Rotation Elasticity (player-season):** a measure of selective deployment, defined as the change in a player’s starting likelihood between “hard” and “easy” fixtures.
        **Proxy 2 - Injury Impact (player-season):** a measure of the associated change in team outcomes during a player’s injury absences, constructed using within-team comparisons to reduce sensitivity to persistent team quality.
    
- **Report organization**:
The remainder of the report is structured as follows. Section 2 reviews relevant literature on fixture congestion and rotation, injury incidence and player availability, and performance measurement in football. Section 3 describes the datasets, preprocessing steps, match-context definitions, and the construction of the two proxies. Section 4 presents empirical results and validation figures. Section 5 discusses interpretation, limitations, and robustness considerations. Section 6 concludes and outlines extensions, including alternative context definitions, stronger identification strategies, and applications to recruitment and squad optimisation.

# 2. Literature Review

Discuss relevant prior work, existing solutions, or theoretical background:

- Previous approaches to similar problems
- Relevant algorithms or methodologies
- Datasets used in related studies
- Gap in existing work that your project addresses

This section situates the project with three adjacent research streams:
    - squad rotation and workload management
    - injury occurence and player availability
    - performance measurement frameworks that allow player-level attribution (or, at minimum, interpretable player-season summaries)

## 2.1 Squat rotation, fixture congestion, and performance trade-offs

Squad rotation is typically discussed as a managerial response to constrained recovery time, match congestion, and heterogeneous opponent difficulty. Sports-science evidence has long examined whether congested schedules degrade match running outputs or elevate injury risk, and to what extent rotation and recovery protocols mitigate these effects. Early club-based evidence suggested that high-intensity running and injury risk may be relatively stable across short congested periods, plausibly


# 3. Methodology

There are three major steps in my project, the first being data collection/processing. This step relied on scraping the data from several websites to obtain the data needed for the project. Once this raw per-season data was in a csv format, an extra but optional step was to create a master dataset with all seasons combined in one csv file per source. Then, some master datasets needed to be merged and derive new columns or remove some. Secondly, creating the proxies, this is where the main pipeline starts, using the processed data to create two seperate proxies followed by a combined version of both proxies. Lastly, the analysis, this part is mainly evaluating the results of the proxies created and printing results, graphs and figures.

## 3.1 Data Description

Describe your dataset(s):

- **Source**: Where did the data come from?
Data was extracted from multiple sources depending on the data needed. Football-data.co.uk provides a csv file that can be downloaded directly from the website for each match per season with many statistical information with the main purpose of match logs and betting odds. Understat provides detailed per-game player statistics, including minutes played and whether they started or not. One of the most important and "difficult" data sources was transfermarkt, providing every injury absence for every player for every season. Finally the official Premier League website provides the prize money per season that each team earned.

- **Size**: Number of samples, features
Gathering all of this data, there is essentially 3 big datasets from Understat, Transfermarkt and Football-Data, the PL prize money is very small in comparison to these. The various big datasets provided thousands of entries which then had to be combined into structured panels for the main pipeline. An important step in merging these datasets was to standardize team names (e.g., one source presents a team such as: Man United, where another might be Man Utd), this step involved checking every single of the 27 team names across the four data sources and to create one canonical team name per team. There were many data samples, but it was important to remove those with too fewer appearances (e.g., a rotation / often injured player that played for a team that only played one season -> bad estimates)

- **Characteristics**: Type of data, distribution
The competition is the EPL, the dataset consists of 27 unique teams, with 20 teams per season with 3 teams changing per season (relegation/promotion). All collected data was transformed into csv files, with values such as strings, integers and binaries. The primary units are match-team observations (team performance + lineup usage per match), player-season observations (final proxy outputs), Injury spells (player availability intervals).

- **Features**: Description of important variables
At minimum, the pipeline relies on the following fields,
1. Match panel:
    - season,match_id,date
    - team_id,opponent_id, home_away
    - player_name (or player_id)
    - started (binary), minutes(integer)
    - xpts (or translated into GBP through prize money)
    - difficulty_label (hard/easy)

2. Injury panel
    - season, team_id, player_name
    - injury_start, injury_end
    - derived: missed_match_id list or match-level availability indicator
- **Data quality**: Missing values, outliers, etc.
There are a few issues regarding the data, transfermarkt injury data provides the expected absence of a certain injury, which in reality, sometimes players can be back sooner than expected (e.g., a player is expected to be out for 9 months with an ACL injury, but in reality was back on the pitch 8 months later), this creates inconsistencies between Understat data which says he played X minutes, even though transfermarkt said he was unavailable due to injury.

## 3.2 Approach

Detail your technical approach:

- **Algorithms**: Which methods did you use and why?
To retrieve data from websties such as Understat and football-data, the algorithm's were relatively basic and for football-data, this could have been done manually very easily by downloading the csv file directly on their website. For transfermarkt, this data collection was more complex, this involved writing a script that would scrape the data from their website and took around 25 minutes to create an csv files with injury data per season.
- **Preprocessing**: Data cleaning and transformation steps

In order to process data, it was important to remove some NaN values, to do so I did not take into account any players with some type of NaN values. When merging, very important to standardise team names to avoid missing values. Very few players has different spellings in the datasets, because they were so little, they were not taking into account for this analysis. Deduplication; collapse duplicate injury windows where applicable. Sample restrictions; excluded player-seasons without sufficient observations (e.g., too few matches in a category to estimate stable rates or impacts)
- **Model architecture**: If using ML/DL, describe the model
- **Evaluation metrics**: How do you measure success?

## 3.3 Implementation

Discuss the implementation details:

- **Languages and libraries**: Python packages used
- **System architecture**: How components fit together
- **Key code components**: Important functions/classes

Example code snippet:

```python
def preprocess_data(df):
    """
    Preprocess the input dataframe.
    
    Args:
        df: Input pandas DataFrame
    
    Returns:
        Preprocessed DataFrame
    """
    # Remove missing values
    df = df.dropna()
    
    # Normalize numerical features
    scaler = StandardScaler()
    df[numerical_cols] = scaler.fit_transform(df[numerical_cols])
    
    return df
```

# 4. Results

## 4.1 Experimental Setup

Describe your experimental environment:

- **Hardware**: CPU/GPU specifications
- **Software**: Python version, key library versions
- **Hyperparameters**: Learning rate, batch size, etc.
- **Training details**: Number of epochs, cross-validation

## 4.2 Performance Evaluation

Present your results with tables and figures.

| Model | Accuracy | Precision | Recall | F1-Score |
|-------|----------|-----------|--------|----------|
| Baseline | 0.75 | 0.72 | 0.78 | 0.75 |
| Your Model | 0.85 | 0.83 | 0.87 | 0.85 |

*Table 1: Model performance comparison*

## 4.3 Visualizations

Include relevant plots and figures:

- Learning curves
- Confusion matrices
- Feature importance plots
- Results visualizations

![Example Results](path/to/figure.png)
*Figure 1: Description of your results*

# 5. Discussion

Analyze and interpret your results:

- **What worked well?** Successful aspects of your approach
- **Challenges encountered**: Problems faced and how you solved them
- **Comparison with expectations**: How do results compare to hypotheses?
- **Limitations**: What are the constraints of your approach?
- **Surprising findings**: Unexpected discoveries

# 6. Conclusion

## 6.1 Summary

Summarize your key findings and contributions:

- Main achievements
- Project objectives met
- Impact of your work

## 6.2 Future Work

Suggest potential improvements or extensions:

- Methodological improvements
- Additional experiments to try
- Real-world applications
- Scalability considerations

# References

1. Author, A. (2024). *Title of Article*. Journal Name, 10(2), 123-145.

2. Smith, B. & Jones, C. (2023). *Book Title*. Publisher.

3. Dataset Source. (2024). Dataset Name. Available at: https://example.com

4. Library Documentation. (2024). *Library Name Documentation*. https://docs.example.com

# Appendices

## Appendix A: Additional Results

Include supplementary figures or tables that support but aren't essential to the main narrative.

## Appendix B: Code Repository

**GitHub Repository:** https://github.com/yourusername/project-repo

### Repository Structure

```
project-repo/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── preprocessing.py
│   ├── models.py
│   └── evaluation.py
├── notebooks/
│   └── exploration.ipynb
└── results/
    └── figures/
```

### Installation Instructions

```bash
git clone https://github.com/yourusername/project-repo
cd project-repo
pip install -r requirements.txt
```

### Reproducing Results

```bash
python src/main.py --config config.yaml
```

---

*Note: This report should be exactly 10 pages when rendered. Use the page count in your PDF viewer to verify.*

---

## Conversion to PDF

To convert this Markdown file to PDF, use pandoc:

```bash
pandoc project_report.md -o project_report.pdf --pdf-engine=xelatex
```

Or with additional options:

```bash
pandoc project_report.md \
  -o project_report.pdf \
  --pdf-engine=xelatex \
  --highlight-style=pygments \
  --toc \
  --number-sections
```