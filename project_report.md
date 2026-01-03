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

- **Objectives and goals**

The project’s objective is not to directly estimate transfer fees or wages, but to provide actionable inputs for downstream analysis in scouting, squad planning, and performance diagnostics. Specifically, the project aims to produce two proxy measures with four design properties: interpretability, scalability, reproducibility, and season comparability.

The deliverables include:
        **Proxy 1 - Rotation Elasticity (player-season):** a measure of selective deployment, defined as the change in a player’s starting likelihood between “hard” and “easy” fixtures.
        **Proxy 2 - Injury Impact (player-season):** a measure of the associated change in team outcomes during a player’s injury absences, constructed using within-team comparisons to reduce sensitivity to persistent team quality.
    
- **Report organization**

The remainder of the report is structured as follows. Section 2 reviews relevant literature on fixture congestion and rotation, injury incidence and player availability, and performance measurement in football. Section 3 describes the datasets, preprocessing steps, match-context definitions, and the construction of the two proxies. Section 4 presents empirical results and validation figures. Section 5 discusses interpretation, limitations, and robustness considerations. Section 6 concludes and outlines extensions, including alternative context definitions, stronger identification strategies, and applications to recruitment and squad optimisation.

# 2. Literature Review

This project draws on four closely related bodies of work:
1. squad rotation and fixture congestion
2. injury incidence and player availability
3. public injury datasets (and limitations)
4. Football performance measurement frameworks (xG/xPts and attribution methods)
Together, these streams motivate the proxy-based approach used here and clarify the gap the project addresses.

## 2.1 Squat rotation, fixture congestion, and performance trade-offs

Rotation is commonly framed as a managerial response to congested schedules and cumulative fatigue, with the aim of sustaining performance and mitigating injury risk. Systematic evidence indicates that injury risk is generally higher during fixture-congested periods, although effects can vary by injury definition and setting. At the club-study level, Carling et al. (2012) report that high-intensity running and injury risk were largely unchanged during a prolonged congested period—an outcome they interpret as consistent with compensatory strategies such as squad rotation and recovery protocols.
Beyond congestion, recent applied research has begun to quantify whether rotation correlates with results. Mehta et al. (2024) examine squad rotation in top European leagues and suggest that rotation is not uniformly beneficial for points accumulation; effects depend on context such as team resources/quality. At the match level, Yang et al. (2025) find evidence consistent with the idea that excessive rotation is associated with worse outcomes, partly mediated through passing and shooting performance.

Relevance for this project. The literature motivates a rotation measure that is contextual, since “rotation” is not only about total minutes but also about selective deployment across match difficulty.

## 2.2 Injuries, availability and team success

Elite football injury epidemiology is well established. The UEFA injury study documents stable but substantial injury incidence in professional football and provides benchmark rates and patterns for match versus training injuries.Importantly, research also links injuries to competitive outcomes. Hägglund et al. (2013), using an 11-year follow-up of UEFA Champions League teams, report that higher injury burden and lower match availability are associated with worse performance outcomes in league and European competition.
A complementary practitioner-facing scientific stream emphasises player availability as an operational performance driver in elite team sports, arguing that keeping key players selectable may matter more than maintaining occasional peak performance.

Relevance for this project. This evidence supports treating injuries as availability shocks with potential downstream performance costs, motivating an “injury impact” proxy anchored in team outcomes during absence periods.

## 2.3 Public injury data (Transfermarkt) and measurement constraints

Because verified medical datasets are rarely public, many applied studies rely on media-compiled injury records such as Transfermarkt. However, the validity of media-based injury reporting is not uniform. Krutsch et al. (2020) evaluate media-reported injuries against clinical information and conclude that validity is higher for certain severe injury types, implying that researchers should apply cautious designs when using such data.
Despite these limitations, public databases can support large-scale analysis: Hoenig et al. (2022) analyse more than 20,000 injuries using a citizen-science approach and discuss both the opportunity and caveats for epidemiological research.

Relevance for this project. These findings motivate conservative claims and robustness-oriented proxy construction—specifically, relying on within-team comparisons rather than assuming high-fidelity medical labels.

## 2.4 Performance measurement: xG, xPts and player attribution

Football outcomes are low-scoring and noisy, motivating the use of model-based metrics such as expected goals (xG) and derived probability-based outcomes. Mead et al. (2023) provide recent peer-reviewed evidence that expected-goals models can be strong predictors of future team success relative to traditional statistics and discuss evaluation of xG modelling choices.
For player-level impact estimation, plus–minus frameworks adapt methods used in basketball and hockey to football. Kharrat, López Peña, and McHale propose variants using expected goals and expected points to reduce variance and align contributions with probabilistic match outcomes.

Relevance for this project. Rather than estimating a full regularised plus–minus model (which is data- and modelling-intensive), this project adopts a proxy approach using expected-points-facing outcomes (xPts) and transparent within-team contrasts, prioritising interpretability and reproducibility.

## 2.5 Gap addressed by this project

Across the literature, two practical gaps remain for a reproducible, player-season framework using public data:
    1. **Context-dependent rotation at the player-season level.** Existing rotation work often focuses on team-level rotation rates or match-level stability and links rotation to points or performance channels.Fewer approaches produce an interpretable player-season statistic capturing how a player’s starting likelihood changes by match difficulty (i.e., selective deployment).
    2. Outcome-linked injury cost measures robust to public injury data limitations. Injuries and availability are strongly connected to team performance, yet public injury logs contain measurement error. This creates scope for a method that remains informative under noisy injury reporting while still linking absences to expectation-based performance outcomes.

This project addresses these gaps by constructing two interpretable player-season proxies Rotation Elasticity (contextual starting selectivity) and Injury Impact (within-team outcome change during injury absences) and delivering a reproducible dataset suitable for downstream ranking, profiling, and squad-level aggregation.


# 3. Methodology

This project is implemented as a reproducible three-stage pipeline that starts from public football data and ends with two interpretable player-season proxy measures. The guiding methodological choice is to prioritise transparent, season-comparable measurement over a complex predictive model. In practice, turning rotation behaviour and injury impact into player-specific quantities requires careful data integration, consistent operational definitions, and conservative handling of noisy public injury records. The pipeline therefore proceeds in three steps: data collection and processing, proxy construction, and evaluation and reporting.

## 3.1 Data Description


- **Source**
The dataset combines four sources, each covering a distinct component of the measurement problem. Match structure and basic match-level information are taken from Football-Data.co.uk (per-season CSV files). Player match participation and lineup usage are taken from Understat, which provides match-level player data including minutes played and whether a player started. Injury absences are taken from Transfermarkt, which lists injury spells (start and end dates) and is one of the few sources available at scale for multiple EPL seasons. Finally, the official Premier League website provides season-level prize money by league position, which can be used to express expected performance differences in approximate monetary terms (GBP) as an optional translation layer.

- **Size**
After extraction, the data are transformed into structured panels that support proxy estimation. The primary competition is the EPL, covering six seasons (2019/20–2024/25). Across this period there are 27 unique clubs due to promotion and relegation (20 teams per season, with three changing each year). The pipeline produces three main data structures. First, a match–team / match–player panel aligns each match to season, match identifier, date, team and opponent identifiers, and the key player usage fields required for rotation measurement (starter indicator and minutes). Second, an injury spell panel represents each injury as an interval with a start and end date, linked to season, team, and player. Third, the pipeline generates player-season proxy tables, one row per player-season-team, which form the final outputs.

- **Characteristics**
All collected data are stored in consistent CSV formats and include a mix of string identifiers, numeric fields, and binary indicators. A critical preprocessing task is entity harmonisation. Team names differ across sources (e.g., “Man United” vs “Man Utd”), which can silently break merges and induce missingness. To prevent this, the pipeline constructs a canonical mapping of all 27 club names and applies it consistently across datasets prior to merging. Where player name discrepancies occur, they are handled conservatively: because the number of inconsistent spellings is small relative to the overall dataset, unresolved cases are excluded rather than risking incorrect matches. 
A key intermediate dataset its the rotation panel, built by joining a team-match panel containing match-level xPts (from the processed match pipeline), and understat per-player match rows containing minutes and a starter indicator.
Concretely, the join is performed on (season, date, team_id) after normalising dates to midnight to avoid timestamp mismatches. The match panel is validated to ensure uniqueness on these join keys (one row per team per league match), and the merge is constrained as a many-to-one join (many player rows per team-match). Understat rows that do not match the league schedule (e.g., cup matches, friendlies, or remaining date inconsistencies) are dropped. The resulting output is written as panel_rotation.csv (and optionally as Parquet), with one row per player–team–match containing identifiers and core analysis fields.

- **Features**
At minimum, the pipeline relies on the following fields,
1. Rotation panel:
    - identifiers: season, match_id, date
    - context: team_id, opponent_id, home_away
    - player usage: player_name (or player_id), started (binary), minutes(integer)
    - performance: xpts (or optionally translated into GBP based on prize money)
    - derived: days_rest (days since the player's previous appearance, capped to a maximum to avoid extreme values)

2. Injury panel:
    - identifiers: season, team_id, player_name
    - injury spell: injury_start, injury_end
    - derived fields: match-level availability indicator or a list of missed matches generated by intersecting injury windows with match dates
    
- **Data quality**
Public injury data introduces important measurement constraints. Transfermarkt injury windows can be approximate: players may return earlier or later than listed, creating apparent inconsistencies when Understat records minutes played during a nominal injury spell. The methodology treats this as noise inherent to public injury reporting rather than as a data “error” that can be fully corrected. To reduce sensitivity to this issue, the Injury Impact proxy relies on within-team comparisons, and the pipeline applies sample restrictions to exclude player-seasons with insufficient support for stable estimation (e.g., very few appearances or too few matches in relevant categories). These restrictions limit extreme values driven by small samples and improve the comparability of proxy estimates across seasons and teams.

## 3.2 Approach

The project’s central methodological contribution is the construction of two proxies that translate qualitative football concepts—rotation and injury-related unavailability—into player-season measures that are interpretable and comparable across clubs and seasons. The approach is deliberately measurement-focused rather than model-heavy: the priority is to build transparent and auditable quantities from public data, while acknowledging and mitigating the limitations that come with scraping and integrating heterogeneous sources.

- **Algorithms**
Data acquisition combines direct downloads and scripted extraction depending on the source. Football-Data.co.uk provides season-level CSV files that can be downloaded directly, so the “algorithmic” component is primarily automated ingestion and consistent season-by-season organisation. Understat does not provide a simple bulk export for the player-match fields required here (minutes played and starter indicators). Understat data are therefore collected programmatically by extracting match-level player participation and compiling it into structured season files and a consolidated master dataset.

Transfermarkt injuries are the most operationally complex source. Injury spells must be scraped from web pages and transformed into season-level injury logs with start and end dates per player. This extraction step is also the most time-consuming (roughly 20–25 minutes per season), reflecting both the volume of pages and the need for respectful request pacing.

Two implementation choices that materially improved reliability without changing the statistical logic were logging and run metadata. Logging records what each script did (inputs read, outputs written, rows dropped, validation checks passed/failed), which is critical when multi-source integration can otherwise fail silently. Run metadata records execution context (timestamp, script name, key parameters such as thresholds and dry-run flags, and output paths). Together, these produce an audit trail that improves debugging, reproducibility, and external verifiability.

- **Preprocessing**
Preprocessing is designed to produce merge-ready panels and to prevent silent inconsistencies from contaminating proxy estimates. First, identifiers and types are standardised across sources: dates are parsed and normalised, numeric variables are coerced consistently, and starter indicators are converted robustly to binary. Rows with missing values in fields essential for proxy construction are excluded rather than imputed, since imputation would introduce additional assumptions and could mechanically affect rate-based or regression-based estimates.

Second, entity harmonisation is treated as a core requirement. Team names differ across sources and can otherwise lead to missed joins or duplicate entities. A canonical mapping is applied prior to merging so that each club is represented consistently across seasons and datasets. Player-name discrepancies occur less frequently; unresolved cases are handled conservatively by exclusion rather than uncertain matching.

Third, the project constructs two intermediate panels that form the input to proxy estimation:
- A team-match panel with expected points (xPts), built from 1X2 betting odds.
- A player-team-match rotation panel and a player-team-match injury panel, both aligned to the team-match panel by (season, date, team).
The rotation panel is produced via a validated many-to-one merge (many player rows to one team-match row), and Understat rows that do not match the league schedule (e.g., cups/friendlies or residual date mismatches) are dropped. The injury panel is built by expanding each player–team–season in the injury spell data to all matches for that team-season, then marking match-level unavailability by intersecting match dates with injury windows. Where available, Understat minutes/starts are merged into the injury panel as additional context.

Finally, the pipeline applies sample restrictions to limit instability from sparse player-seasons (e.g., minimum match counts for Proxy 1 and minimum unavailable/available matches for Proxy 2).

- **Model architecture**
No machine learning or deep learning architecture is used; instead, the “model” is the proxy construction logic and the associated estimation design. The pipeline produces two player-season outputs and then merges them into a single combined player-season panel to support downstream analysis.

Expected points (xPts) construction (input to both proxies).
Match-level expected points are computed from 1X2 betting odds by converting odds into implied probabilities and normalising to remove the bookmaker margin. Let $p_H$, $p_D$, and $p_A$ denote the normalised implied probabilities of a home win, draw, and away win, respectively. Expected points are then computed per side as:

$$
xPts_{home} = 3p_H + 1p_D, \qquad xPts_{away} = 3p_A + 1p_D.
$$

This produces a long-form team–match panel with two rows per match (home and away), which is used downstream in both proxy construction and validation.

**Proxy 1 — Rotation Elasticity (player–team–season)**

Rotation Elasticity is computed from the player–team–match rotation panel (joined on $(season, date, team\_id)$), which contains `started`, `minutes`, and match-level `xpts`. Match context is defined within each team-season using the distribution of team match-level xPts. For each $(team\_id, season)$ pair, tercile thresholds are computed:

$$
q_{low} = \text{quantile}(xPts, 1/3), \qquad q_{high} = \text{quantile}(xPts, 2/3).
$$

Each match is assigned a stakes category:

- **hard** if $xPts \le q_{low}$
- **easy** if $xPts \ge q_{high}$
- **medium** otherwise

For each player–team–season, starting rates are computed within the hard and easy groups:

$$
\text{start\_rate}_{hard} = \Pr(\text{started}=1 \mid \text{hard}), \qquad
\text{start\_rate}_{easy} = \Pr(\text{started}=1 \mid \text{easy}).
$$

Rotation Elasticity is then defined as:

$$
\text{rotation\_elasticity} = \text{start\_rate}_{hard} - \text{start\_rate}_{easy}.
$$

Player–team–seasons are retained only if the estimate is supported by sufficient observations (default thresholds: `min_matches = 3`, `min_hard = 1`, `min_easy = 1`) and the resulting elasticity is non-missing.

**Proxy 2 - Injury Impact (DiD-style OLS per player-team-season)**

Injury Impact is estimated using a player–team–match injury panel with one row per $(match\_id, team\_id, player)$, where `unavailable` indicates whether the match date falls within any recorded injury spell for that player in the same team-season. The panel also includes match-level `xpts`, opponent identity, and the number of injured players in the squad (`n_injured_squad`). Where available, Understat `minutes` and `started` are merged in as additional context.

Estimation is performed separately for each player–team–season using an OLS specification:

$$
xPts_m = \alpha + \beta \cdot \text{unavailable}_m + \gamma \cdot \text{n\_injured\_squad}_m
+ \delta_{\text{opponent}(m)} + \tau \cdot \text{match\_index}_m + \varepsilon_m.
$$

The model includes opponent fixed effects ($C(opponent\_id)$) and a numeric within-sample time trend (`match_index`) to reduce sensitivity to gradual within-season changes. The coefficient $\beta$ on `unavailable` is retained as the player-season injury proxy (`beta_unavailable`). Player–team–seasons are filtered to ensure estimability and support in both states (default thresholds: `min_unavail = 2`, `min_avail = 2`). Standard errors are clustered by opponent when enough opponent clusters are available; otherwise heteroskedasticity-robust (HC1) standard errors are used.

**Combined dataset**
Finally, the rotation and injury proxy outputs are merged into a single player-season-team dataset using an outer join on $(player\_id, season, team\_id)$. An outer merge is used because coverage differs across proxies; retaining unmatched player-seasons supports inspection and robustness checks. The combined file also includes simple coverage flags (e.g., whether a player-season has a valid rotation proxy and/or injury proxy).

- **Evaluation metrics**

Because the project’s objective is measurement rather than prediction, evaluation focuses on whether the proxies are computable, stable, and interpretable at scale. Success is assessed through reproducibility of outputs given fixed inputs (supported by deterministic scripts, logging, and run metadata), coverage and stability ensuring estimates are not driven by sparse player-seasons and face-validity diagnostics, including summary statistics and plots that verify whether the proxies behave plausibly (e.g., differentiating core starters from situational players and exhibiting meaningful variation across roles and squads). The analysis phase therefore emphasises diagnostic evidence that the proxies capture interpretable structure in the data, rather than optimising a predictive score.

## 3.3 Implementation

The project is implemented entirely in Python and organised as a modular, file-based pipeline. The implementation philosophy is pragmatic: each stage produces clearly defined intermediate artefacts (CSV and, where available, Parquet), so downstream steps operate on stable inputs rather than recomputing upstream work. This design improves reproducibility, makes failures easier to diagnose, and allows individual components (e.g., a panel builder or a proxy script) to be executed and tested in isolation.

- **Languages and libraries**
All code is written in Python 3 using a standard data-science stack. pandas and NumPy provide the core functionality for tabular manipulation—type coercion, joins, group-by aggregation, and feature engineering. statsmodels is used for the regression-based estimation of the injury proxy, where the goal is not prediction but a structured within-season comparison that returns an interpretable coefficient. The scripts use argparse to expose a consistent command-line interface (input paths, output paths, thresholds, and dry-run flags), and pathlib to ensure file paths are handled robustly across environments. In the analysis stage, figures and summary outputs rely on common plotting utilities (e.g., matplotlib) and descriptive summarisation in pandas.

Beyond these external libraries, a small set of internal utilities supports robustness and engineering quality. A central configuration object (Config.load()) standardises directory structure and default paths; logging helpers (setup_logger) provide consistent run-time traces; and run metadata (write_run_metadata) records execution context and key parameters so results can be reproduced and audited. Finally, outputs are written using an atomic write utility (atomic_write_csv) to avoid partial files if a run is interrupted.

- **System architecture**
The system architecture follows a “build panels → build proxies → merge → analyse” pattern. Conceptually, the pipeline is a directed chain of transformations where each component has a narrow responsibility and communicates with the next stage through explicit data products on disk.

At the foundation is a team–match panel that provides match-level expected points (xPts). In the implementation, xPts is derived from 1X2 betting odds by converting odds into implied probabilities, normalising to remove the bookmaker margin, and then translating those probabilities into expected points for the home and away teams. The result is a long-form match panel with two rows per match (home and away), which becomes the shared performance backbone for both proxies.

On top of this match backbone, the pipeline constructs two player-oriented panels. The rotation panel is produced by aligning Understat player-match participation (minutes and a starter indicator) with the team–match panel. The merge is performed on (season, date, team_id) after normalising dates to prevent timestamp mismatches, and it is guarded by key-uniqueness checks that prevent unintended many-to-many joins. Rows that cannot be matched to league fixtures (typically cups, friendlies, or residual date inconsistencies) are dropped so the panel represents the EPL schedule only. This panel is then enriched with derived fields such as days_rest, computed as the number of days since a player’s previous recorded appearance and capped to avoid extreme values.

The injury panel is built in a way that reflects the structure of injury data itself. Injury information enters as spell intervals (start date and end date) rather than match-level observations. The implementation therefore expands each player–team–season present in the injury spell data to all matches in the corresponding team-season, and then flags match-level unavailability by checking whether each match date falls within any injury interval. Where available, Understat minutes and starter information are merged into this panel to provide additional context. The resulting dataset is indexed at the match level (one row per (match_id, team_id, player)), which is the natural format for the regression-based injury proxy.

Proxy estimation is then performed as dedicated, deterministic scripts. Proxy 1 (Rotation Elasticity) assigns match context using team-season xPts terciles and computes the difference between starting rates in “hard” and “easy” contexts. Proxy 2 (Injury Impact) estimates a per player–team–season OLS model of xPts on a match-level unavailability indicator, controlling for opponent fixed effects, a within-season time trend, and squad-level injury burden. Both scripts implement minimum-support filters to reduce small-sample instability and output one row per player–team–season.

Finally, the proxy outputs are combined into a single player-season dataset through a controlled merge step. The implementation uses an outer join on (player_id, season, team_id) because coverage differs across proxies; retaining player-seasons that appear in only one proxy supports later inspection, robustness checks, and transparent reporting of sample sizes. The combined dataset is then used in downstream analysis scripts to generate summary tables, validation figures, and descriptive insights.

- **Key code components**

Implementation quality relies on a small number of recurring patterns that appear across scripts and materially reduce the risk of silent errors.

First, the code consistently applies schema validation before and after major transformations. Required columns are checked explicitly, and non-empty assertions fail fast when an upstream step has not produced valid outputs. Second, joins are treated as a high-risk operation and are therefore handled defensively: match panels are validated for uniqueness on join keys, merges use validate="many_to_one" where appropriate, and duplicate-key checks prevent many-to-many merges that would silently inflate row counts.

Third, reproducibility is supported by an explicit execution trace. Logging records the shape of key datasets, the number of dropped rows (e.g., unmatched Understat rows), the thresholds used in filtering, and the location of outputs. Run metadata complements this by recording the runtime context (script name, timestamp, parameter values such as min_matches, min_unavail, and min_avail). This combination is particularly valuable in a multi-stage pipeline: it makes it possible to understand exactly how a given output was produced, and it allows the pipeline to be rerun under identical conditions.

Lastly, outputs are written using atomic writes to protect against partial or corrupted files. This is a small engineering detail, but it is important in practice: many pipeline issues stem from incomplete outputs produced by interrupted runs. Atomic writes ensure that a file is only replaced once a full write has completed successfully, which helps keep intermediate artefacts reliable for downstream stages.


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