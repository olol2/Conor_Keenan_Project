# Abstract

Provide a concise summary (150-200 words) of your project including:
- The problem you're solving
- Your approach/methodology  
- Key results/findings
- Main contributions

This project investigates how player rotation and injury-related absences relate to team performance in the English Premier League (EPL). Using match-level lineups and injury logs across six seasons (2019/2020 - 2024/2025) and 27 total teams (accounting for promoted and relegated teams), I build two player season proxies designed to quantify how selectively a player is used and how costly a plyer's absence is in performance terms such as Expected Points (xPts) or money (GBP).

First I propose a Rotation Elasticity proxy that measures how a player's starting likelihood changes between "hard" and "easy" fixtures (defined from opponent strength / match difficulty).

Secondly, I construct an Injury Impact proxy that attributes changes in team outcomes, around periods when a player is unavailable, using within-team comparisons to mitigate confounding factors.

The resulting dataset provides interpretable player-season measures that can be used for downstream analysis (ranking, profiling, and team-level aggregation). Empirically, the proxies reveal substantial heterogeneity across roles and squads, highlighting that "value" in football is partially driven by context-dependant usage and the marginal performance loss associated with availability shocks.

**Keywords:** Data Science, Python, Machine Learning, Sports Analytics, Football, Premier League, Causal Inference, Expected Points

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

Introduce your project and its context. This section should include:

- **Background and motivation**: Why is this problem important?

The EPL is one if not the biggest league in the world when it comes to viewership, popularity and therefore money! Like many of the top leagues, the teams operate under tight constraints such as congested match calendars, high physical demands and substantial stakes linked to league position (Broadcast revenue, prize money and European qualification). Within this environment, clubs continously manage two intertwined problems:
1. Rotation decisions: coaches must allocate minutes across players while balancing short-term match objectives and longer-term fatigue/injury management.
2. Injury risk and availability: injuries disrupt quad plans, forcing tactival adjustments and altering the distribution of minutes and starts.

Despite widespread siscussion in the football industry, quandtifying these concepts in a way that is player-specific, season-comparable, and tightly linked to performance remains non-trivial. Traditional player metrics such as minutes, appearances, goals/assists do not fully capture how and when a player is used, nor do they isolate the performance cost of absences in a comparable way.

This project focuses on building data-driven, interpretable proxies that operationalize these concepts and enable subsequent analysis of "fair value" drivers beyond headline statistics.

- **Problem statement**: What specific problem are you solving?

The central issue is measurement: rotation adn injury impact are often referenced qualitively, but rigourous player-season quantification requires defining match contexts, dealoing with selection effects (better player start more) and seperating the effect of a player's absence from broader team dynamics.
Accordingly, the project asks: can we construct robust player-season measures that capture selective usage (rotation) and the performance cost of availibility shocks(injuries), using only broadly obtainable match and injury data?

The report is structured into three research questions:
1. Rotation behavior: Do teams systematically vary the probability that a given player starts depending on match difficulty and can this be summarized as a player-season statistic?
2. Injury-related performance cost: When a player is unavailable due to injury, what is the associated change in team performance, and can this be attributed at the player-season level in a comparable way?
3. "Fair value" interpretation: Do the resulting proxies provide meaningful differentiation between players (e.g., core starters vs. situational players; high-impact absences vs. low-impact absences) that complements conventional performance measures?

- **Objectives and goals**: What do you aim to achieve?
The project's objective is not to "solve" transfer pricing or wage valuation directly, but to contibute two proxy measures that are:
    - Interpretable: aligned with football decision-making (starts in hard matches; cost of missing games).
    - Scalable: computable across seasons and clubs from consistent data sources.
    - Actionable: usage as inputs for later valuation, scouting, squad planning, or robustness checks in performance modeling.
    - Deliverables include:
        Proxy 1 - Rotation Elasticity (player-season): context-sensitive starting selectivity
        Proxy 2 - Injury Impact (player-season): marginal performance loss associated with injury absence.
High level approach?
    
- **Report organization**: Brief overview of the report structure
The report is structured as follows. Section 2 reviews prior work on squad rotation, match congestion, injury evidence, and performance measurement (including expected goals/expected points). Section 3 details data sources, variable construction and proxy definitions. Section 4 presents empirical results and validation figures. Section 5 discusses interpretation, limitations and robustness considerations. Section 6 concludes and proposes further work.

# 2. Literature Review

Discuss relevant prior work, existing solutions, or theoretical background:

- Previous approaches to similar problems
- Relevant algorithms or methodologies
- Datasets used in related studies
- Gap in existing work that your project addresses

# 3. Methodology

## 3.1 Data Description

Describe your dataset(s):

- **Source**: Where did the data come from?
- **Size**: Number of samples, features
- **Characteristics**: Type of data, distribution
- **Features**: Description of important variables
- **Data quality**: Missing values, outliers, etc.

## 3.2 Approach

Detail your technical approach:

- **Algorithms**: Which methods did you use and why?
- **Preprocessing**: Data cleaning and transformation steps
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