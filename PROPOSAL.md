# Category: Sports Analytics + Finance
## Problem Statement / Motivation:
Instead of inferring individual impact by slicing team xPts, I will value players using observable managerial choices (who starts when it matters) and availability shocks (injuries/suspensions), then translate those effects into € via a points→€ mapping.

## Planned Approach & Technologies:
Scope: Premier League; public lineups/benches and injury windows.
Data: Football-Data (results, closing odds), lineups (starts vs subs), injury/suspension dates, venue/competition, congestion; optional transfer fees/wage bands for external validation.

### Method:
**Proxy 1 — Rotation Elasticity:**  
Mixed-effects logistic model for “player starts this match,” with fixed effects for opponent strength (odds), venue, days-rest; random effects for club and player. High elasticity in high-stakes fixtures ⇒ higher value.
**Proxy 2 — Injury/suspension DiD:**
 Within club-season, estimate ATT on xPts from odds for matches with vs without Player X using two-way FE (opponent & date), clustered SEs; exclude multi-injury/suspension spells.

### Aggregation: 
Convert elasticity/ATT (xPts) to € using the season’s points→€ curve; bootstrap CIs.
### Product:
Dashboard ranking players by Rotation Elasticity and Injury/suspension ATT, with filters by position/club and downloadable tables.
### Tech:
Python (pandas, numpy, statsmodels/sklearn), Plotly/Altair, Streamlit, pytest.

## Expected Challenges & Mitigations:
Confounding from concurrent absences → exclusion rules (red card during a game might affect the match even though player played the game) + sensitivity checks; lineup noise → encode competition/venue/congestion.

## Success Criteria:
Significant ATT for key players; elasticity correlates with subsequent fees/wage-band moves; reproducible one-command setup and clear Top-10 value-add list.

## Stretch Goals (time permitting):
Ownership-news case study analyzed separately; scenario simulator for “what if Player X misses four weeks.”