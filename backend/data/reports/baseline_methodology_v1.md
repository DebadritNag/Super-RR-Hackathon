# Baseline methodology v1 (Phase 3 Stage 4, EXPLORATORY)

Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication `True`.

## 1. Status: exploratory versus validated

- **Validated numbers in this document: none.** Every figure is an exploratory computation on the
  official DuckDB through the pre-delivery state table.
- The baseline estimates what a typical delivery in the same context would produce. Actual minus
  expected (AvE) is a diagnostic residual, not a pressure score and not a ranking.
- Expectations, shrinkage hyperparameters and bootstrap results here are FULL_SAMPLE and descriptive.
  Predictive use needs the strictly-prior variant and the temporal split of the validation plan.
- No model is trained. Players appear only as `player_id` in the technical sample, flagged
  `TECHNICAL_SAMPLE_NOT_A_RANKING`.

## 2. Design

Separate baselines for batters and bowlers (different outcomes and different denominators).

| Role | Row unit | Streams |
|---|---|---|
| Batter | one ball faced (innings 1/2, not wide, not Penalty; the Phase 2.5 `BATTER_SQL` definition) | runs off the bat, dot, boundary, dismissal (striker dismissed, not Retire Out) |
| Bowler | one delivery charged to the bowler (all rows except Penalty, so wides and no-balls count) | charged runs (`BOWLER_SQL` definition), wicket credited to the bowler (Caught, Bowled, LBW, Stump, Hit Wicket), dot (legal ball, 0 runs), boundary |

Context controls (the cell): competition type (IPL/T20I), innings role (innings 1 or chase), innings
phase (powerplay/middle/death from the legal over index), wickets-remaining bin (global partition
from the Stage 3 merge). Match state enters through the role (chase versus innings 1) and, in the
per-candidate sensitivity baselines, through pressure membership as the finest level. The reference
baseline B0 has no pressure term, so it does not depend on any candidate definition.

Hierarchy (finest to coarsest): `comp|role|phase|wbin` -> `comp|role|phase` -> `comp|role` -> `comp`.
Per-candidate baselines add `pressure membership` as a new finest level above `L0`.

Estimator: for each level the cell mean (with the leave-out group removed) is shrunk to the value of
its parent level. Continuous streams use `shrink_to_parent(n_eff, cell_mean, parent_mean, k)`;
binary streams use `beta_binomial_shrink` with counts scaled by the design effect `n_eff / n`.
`k = sigma2_within / tau2` with `tau2 = max(between_moment, tau2_floor * sigma2_within)` and
`tau2_floor = 0.01`, so `k <= 1 / tau2_floor` and a zero or negative moment gives the
strongest shrinkage, never `k = 0`. `shrinkage_floor_hit` is recorded when the floor binds.
`n_eff` is the Kish effective number of innings in the cell (innings clustering, spec section 6
rule 6). This is conservative: the per-delivery variance is divided by an innings-sized count.
A cell with fewer than `min_cell_innings = 30` distinct innings takes its parent value
entirely; the level actually used is recorded for every row as `exp_cell_level_used`.

Leave-out variants: `pooled` (descriptive B0), `leave_player_out` (a player's own deliveries never set
their own expectation; the primary variant for AvE), `leave_match_out` (the whole match removed; always
reported as a named sensitivity). `k` and the Kish sizes are FULL_SAMPLE hyperparameters.
A `strictly_prior` baseline is not built in this chunk.

## 3. Calibration identity (code-correctness check on RAW cell means)

Inside every finest cell the sum of actual outcomes equals the sum of the raw pooled cell mean. Shrunk and leave-out expectations deliberately break this identity; their totals are shown beside it.

| role | stream | rows | actual mean | finest cells | max |cell residual| (raw) | sum(A-E) pooled shrunk | sum(A-E) leave-player-out | sum(A-E) leave-match-out |
|---|---|---|---|---|---|---|---|---|
| batter | runs | 183,251 | 1.40 | 24 | 3.38e-10 | 22.50 | 134.07 | 29.00 |
| batter | dot | 183,251 | 0.37 | 24 | 5.7e-11 | -59.42 | -101.56 | -61.75 |
| batter | boundary | 183,251 | 0.19 | 24 | 2.96e-11 | -39.57 | -22.53 | -38.82 |
| batter | dismissal | 183,251 | 0.05 | 24 | 5.7e-12 | -27.97 | -44.59 | -30.24 |
| bowler | charged | 190,584 | 1.39 | 24 | 4.26e-10 | 15.65 | -81.47 | 22.88 |
| bowler | wkt | 190,584 | 0.05 | 24 | 7.4e-12 | -25.92 | -25.19 | -28.18 |
| bowler | dot | 190,584 | 0.34 | 24 | 6.13e-11 | -52.87 | -33.64 | -55.42 |
| bowler | boundary | 190,584 | 0.18 | 24 | 6.18e-11 | -38.83 | -58.79 | -38.06 |

Calibration identity holds for all streams: **True**. Second run identical (determinism): **True**.

## 4. Expected-value plausibility and levels used

| role | stream | expected min | mean | max | NaN | mean |LPO - pooled| | mean |LMO - pooled| |
|---|---|---|---|---|---|---|---|
| batter | runs | 1.17 | 1.40 | 1.76 | 0 | 0.00206 | 0.000972 |
| batter | dot | 0.28 | 0.37 | 0.51 | 0 | 0.000605 | 0.00028 |
| batter | boundary | 0.13 | 0.19 | 0.25 | 0 | 0.000466 | 0.000206 |
| batter | dismissal | 0.04 | 0.05 | 0.09 | 0 | 0.000193 | 9.13e-05 |
| bowler | charged | 1.18 | 1.39 | 1.73 | 0 | 0.00168 | 0.000936 |
| bowler | wkt | 0.04 | 0.05 | 0.08 | 0 | 0.000146 | 8.62e-05 |
| bowler | dot | 0.24 | 0.34 | 0.46 | 0 | 0.000462 | 0.000271 |
| bowler | boundary | 0.13 | 0.18 | 0.24 | 0 | 0.000369 | 0.000197 |

`exp_cell_level_used` (leave-player-out, rows per level) and shrinkage floor hits:

| role | stream | L0 comp|role|phase|wbin | L1 comp|role|phase | L2 comp|role | L3 comp | floor-hit rows | floor-hit parents | parents |
|---|---|---|---|---|---|---|---|---|
| batter | runs | 183,251 | 0 | 0 | 0 | 150,471 | 16 | 18 |
| batter | dot | 183,251 | 0 | 0 | 0 | 141,770 | 11 | 18 |
| batter | boundary | 183,251 | 0 | 0 | 0 | 183,251 | 18 | 18 |
| batter | dismissal | 183,251 | 0 | 0 | 0 | 183,251 | 18 | 18 |
| bowler | charged | 190,584 | 0 | 0 | 0 | 170,273 | 17 | 18 |
| bowler | wkt | 190,584 | 0 | 0 | 0 | 190,584 | 18 | 18 |
| bowler | dot | 190,584 | 0 | 0 | 0 | 156,629 | 12 | 18 |
| bowler | boundary | 190,584 | 0 | 0 | 0 | 190,584 | 18 | 18 |

## 5. Phase context: raw rates are never compared across phases without expectation

Raw runs per ball differ strongly by phase. The expectation sits inside the phase cell, so the residual (actual minus expected) removes the phase effect before any player comparison.

| role | stream | comp | ctx | phase | rows | actual mean | expected mean (LPO) | mean residual |
|---|---|---|---|---|---|---|---|---|
| batter | runs | IPL | chase | death | 8,094 | 1.62 | 1.60 | 0.02 |
| batter | runs | IPL | chase | middle | 18,954 | 1.40 | 1.40 | -0.00381 |
| batter | runs | IPL | chase | powerplay | 12,905 | 1.45 | 1.45 | -0.00483 |
| batter | runs | IPL | inn1 | death | 10,663 | 1.72 | 1.70 | 0.03 |
| batter | runs | IPL | inn1 | middle | 19,623 | 1.38 | 1.39 | -0.00701 |
| batter | runs | IPL | inn1 | powerplay | 13,157 | 1.42 | 1.43 | -0.01 |
| batter | runs | T20I | chase | death | 8,701 | 1.45 | 1.44 | 0.02 |
| batter | runs | T20I | chase | middle | 22,472 | 1.27 | 1.28 | -0.000349 |
| batter | runs | T20I | chase | powerplay | 15,605 | 1.30 | 1.31 | -0.00749 |
| batter | runs | T20I | inn1 | death | 12,929 | 1.58 | 1.56 | 0.02 |
| batter | runs | T20I | inn1 | middle | 23,967 | 1.29 | 1.29 | -0.000738 |
| batter | runs | T20I | inn1 | powerplay | 16,181 | 1.28 | 1.28 | -0.0075 |
| bowler | charged | IPL | chase | death | 8,604 | 1.60 | 1.58 | 0.02 |
| bowler | charged | IPL | chase | middle | 19,602 | 1.39 | 1.40 | -0.00503 |
| bowler | charged | IPL | chase | powerplay | 13,393 | 1.45 | 1.45 | -0.00563 |
| bowler | charged | IPL | inn1 | death | 11,357 | 1.69 | 1.67 | 0.02 |
| bowler | charged | IPL | inn1 | middle | 20,311 | 1.37 | 1.38 | -0.00837 |
| bowler | charged | IPL | inn1 | powerplay | 13,644 | 1.42 | 1.43 | -0.01 |
| bowler | charged | T20I | chase | death | 9,157 | 1.44 | 1.43 | 0.01 |
| bowler | charged | T20I | chase | middle | 23,192 | 1.27 | 1.28 | -0.0012 |
| bowler | charged | T20I | chase | powerplay | 16,211 | 1.31 | 1.32 | -0.00819 |
| bowler | charged | T20I | inn1 | death | 13,640 | 1.57 | 1.55 | 0.02 |
| bowler | charged | T20I | inn1 | middle | 24,703 | 1.29 | 1.29 | -0.00137 |
| bowler | charged | T20I | inn1 | powerplay | 16,770 | 1.28 | 1.29 | -0.00834 |

## 6. Pressure samples: B0 versus per-candidate baselines (diagnostic, not a selection)

B0 has no match-state or pressure term, so its mean residual in a pressure sample is not zero. The per-candidate baseline adds pressure membership and is the match-state control for that candidate. Four candidate definitions are used as diagnostics here; the other candidates are not built in this chunk.

| ctx | signal | q | role_stream | pressure rows | B0 mean residual | candidate-baseline mean residual | calibration max |cell residual| | floor-hit rows |
|---|---|---|---|---|---|---|---|---|
| chase | rrr | 0.75 | batter_runs | 21,331 | 0.08 | 0.05 | 1.5e-10 | 183,251 |
| chase | rrr | 0.75 | bowler_charged | 22,195 | 0.06 | 0.02 | 1.35e-10 | 190,584 |
| chase | rrr | 0.75 | bowler_wkt | 22,195 | -0.00847 | -0.00473 | 7.4e-12 | 189,698 |
| chase | rrr | 0.90 | batter_runs | 8,476 | 0.02 | 0.02 | 3.38e-10 | 183,251 |
| chase | rrr | 0.90 | bowler_charged | 8,880 | 0.12 | 0.07 | 1.35e-10 | 190,584 |
| chase | rrr | 0.90 | bowler_wkt | 8,880 | -0.00374 | -0.00232 | 7.4e-12 | 189,665 |
| inn1 | neg_par_dev | 0.75 | batter_runs | 24,269 | -0.13 | -0.06 | 3.38e-10 | 183,251 |
| inn1 | neg_par_dev | 0.75 | bowler_charged | 25,120 | 0.19 | 0.09 | 4.26e-10 | 163,931 |
| inn1 | neg_par_dev | 0.75 | bowler_wkt | 25,120 | 0.0017 | 0.000726 | 5.81e-12 | 190,584 |
| inn1 | neg_par_dev | 0.90 | batter_runs | 9,699 | -0.18 | -0.11 | 3.38e-10 | 182,986 |
| inn1 | neg_par_dev | 0.90 | bowler_charged | 10,049 | 0.27 | 0.18 | 4.26e-10 | 134,776 |
| inn1 | neg_par_dev | 0.90 | bowler_wkt | 10,049 | 0.00266 | 0.00194 | 5.81e-12 | 190,584 |

## 7. Player actual-versus-expected, shrinkage and bootstrap (technical illustration)

Pressure sample: chase, RRR >= p75 (absolute, per format), used only to exercise the machinery. Residuals are leave-player-out B0. Each player-format is shrunk towards the pooled mean residual of OTHER players (FULL_SAMPLE, descriptive; strictly prior when used predictively); target 0 is the named sensitivity. Bootstrap by match, stratified by format, seed 20260512, 500 resamples, baseline held fixed inside the resample (the prior k is re-estimated per resample).

| stream | pressure rows | pressure-sample mean residual | player-formats | floor 2 | players >= floor 2 | median n | median matches | median shrunk AvE | median CI width | share CI excludes 0 | share point inside CI | eb k | |shift| target 0 vs pooled (all) | |shift| target 0 vs pooled (>= floor 2) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| batter_runs | 21,331 | 0.08 | 724 | 60 | 98 | 98.00 | 8.00 | 0.19 | 0.59 | 0.35 | 1.00 | 39.49 | 0.06 | 0.02 |
| bowler_charged | 22,195 | 0.06 | 549 | 48 | 156 | 83.00 | 9.00 | 0.04 | 0.51 | 0.12 | 1.00 | 70.42 | 0.04 | 0.03 |
| bowler_wkt | 22,195 | -0.00847 | 549 | 48 | 156 | 83.00 | 9.00 | -0.00662 | 0.04 | 0.22 | 0.92 | 3894.52 | 0.00842 | 0.00829 |

Technical sample (first ten `comp|player_id` with enough observations; ordered by id, not by value):

**batter_runs**

| player (comp|id) | n | matches | shrunk residual | CI low | CI high | label |
|---|---|---|---|---|---|---|
| IPL|1077 | 145.00 | 16 | 0.52 | 0.26 | 0.85 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1318 | 98.00 | 13 | 0.09 | -0.28 | 0.53 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|143 | 98.00 | 8 | 0.28 | -0.24 | 0.67 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|152 | 183.00 | 13 | 0.05 | -0.06 | 0.18 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1699 | 191.00 | 14 | 0.24 | 0.03 | 0.44 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|19714 | 69.00 | 5 | -0.18 | -0.46 | -0.03 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|20702 | 143.00 | 10 | 0.39 | 0.05 | 0.73 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|220 | 132.00 | 6 | -0.01 | -0.16 | 0.09 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|2258 | 97.00 | 6 | 0.43 | 0.25 | 0.84 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|23450 | 138.00 | 8 | 0.18 | 0.0095 | 0.32 | TECHNICAL_SAMPLE_NOT_A_RANKING |

**bowler_charged**

| player (comp|id) | n | matches | shrunk residual | CI low | CI high | label |
|---|---|---|---|---|---|---|
| IPL|1071 | 72.00 | 9 | 0.06 | -0.16 | 0.33 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1318 | 61.00 | 9 | 0.12 | -0.19 | 0.45 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|152 | 130.00 | 15 | -0.09 | -0.30 | 0.13 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1566 | 111.00 | 15 | 0.14 | -0.08 | 0.50 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1596 | 68.00 | 7 | -0.08 | -0.31 | 0.11 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1612 | 144.00 | 11 | -0.12 | -0.38 | 0.15 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1758 | 147.00 | 14 | 0.09 | -0.09 | 0.29 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1813 | 83.00 | 15 | 0.04 | -0.29 | 0.27 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|19316 | 86.00 | 7 | -0.08 | -0.26 | 0.04 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|20005 | 67.00 | 8 | 0.23 | 0.00419 | 0.70 | TECHNICAL_SAMPLE_NOT_A_RANKING |

**bowler_wkt**

| player (comp|id) | n | matches | shrunk residual | CI low | CI high | label |
|---|---|---|---|---|---|---|
| IPL|1071 | 72.00 | 9 | -0.00536 | -0.03 | 0.00765 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1318 | 61.00 | 9 | -0.00592 | -0.00393 | 0.07 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|152 | 130.00 | 15 | -0.00522 | -0.03 | 0.00116 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1566 | 111.00 | 15 | -0.0052 | -0.03 | -0.000939 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1596 | 68.00 | 7 | -0.00577 | -0.00566 | 0.03 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1612 | 144.00 | 11 | -0.00579 | -0.01 | 0.04 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1758 | 147.00 | 14 | -0.00586 | -0.01 | 0.04 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|1813 | 83.00 | 15 | -0.00553 | -0.02 | 0.02 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|19316 | 86.00 | 7 | -0.00522 | -0.03 | -0.00877 | TECHNICAL_SAMPLE_NOT_A_RANKING |
| IPL|20005 | 67.00 | 8 | -0.00535 | -0.02 | 0.00162 | TECHNICAL_SAMPLE_NOT_A_RANKING |

The percentile interval comes from the bootstrap distribution with the shrinkage prior re-estimated in every resample. When the between-player variance is barely identified (wicket stream: eb k in the thousands) the full-sample point estimate can sit outside its own interval; the column share point inside CI reports how often this happens. Such intervals describe prior instability, not player skill.

### tau2_floor sensitivity

The floor is a fraction of the per-delivery within-cell variance, so it binds in most parents (the between-cell variance of runs per ball is small relative to the per-ball variance). Rows below show the leave-player-out expectation under the two sensitivity values.

| tau2_floor | role | stream | floor-hit rows | floor-hit parents | mean |E - E_primary| | max |E - E_primary| |
|---|---|---|---|---|---|---|
| 0.001 | batter | runs | 110,899 | 11 | 0.02 | 0.15 |
| 0.001 | batter | dot | 60,772 | 7 | 0.00396 | 0.02 |
| 0.001 | batter | boundary | 126,504 | 11 | 0.00569 | 0.02 |
| 0.001 | batter | dismissal | 183,251 | 14 | 0.00236 | 0.00754 |
| 0.001 | bowler | charged | 115,715 | 12 | 0.02 | 0.15 |
| 0.001 | bowler | wkt | 190,584 | 14 | 0.00295 | 0.00891 |
| 0.001 | bowler | dot | 86,956 | 8 | 0.00397 | 0.02 |
| 0.001 | bowler | boundary | 131,926 | 11 | 0.00605 | 0.02 |
| 0.10 | batter | runs | 183,251 | 18 | 0.02 | 0.21 |
| 0.10 | batter | dot | 183,251 | 18 | 0.00503 | 0.06 |
| 0.10 | batter | boundary | 183,251 | 18 | 0.00342 | 0.04 |
| 0.10 | batter | dismissal | 183,251 | 18 | 0.000865 | 0.01 |
| 0.10 | bowler | charged | 190,584 | 18 | 0.02 | 0.21 |
| 0.10 | bowler | wkt | 190,584 | 18 | 0.000745 | 0.01 |
| 0.10 | bowler | dot | 190,584 | 18 | 0.0047 | 0.05 |
| 0.10 | bowler | boundary | 190,584 | 18 | 0.00325 | 0.04 |

## 8. Season, competition and venue environment

Competition: for IPL one competition is one season, so a competition offset equals the season offset below. T20I competitions are many small tournaments and are not supportable as cells; the T20I season offset is used instead.

Season cells: 10 (comp x season), supportable (>= 30 distinct innings): 10. A leave-one-match-out season offset on the batter runs residual, shrunk to 0, was run as a sensitivity (`SENSITIVITY_ONLY_DEFAULT_OFF`): maximum |offset| 0.0809 runs per ball; effect on shrunk player residuals (median |shift|) 0.00474, (max) 0.04217. The primary baseline does not use it.

| comp|season | innings | rows | mean residual (runs/ball) |
|---|---|---|---|
| IPL|2022 | 148 | 17,207 | -0.13 |
| IPL|2023 | 146 | 17,147 | -0.06 |
| IPL|2024 | 142 | 16,374 | 0.04 |
| IPL|2025 | 143 | 16,301 | 0.06 |
| IPL|2026 | 143 | 16,367 | 0.09 |
| T20I|2022 | 200 | 23,069 | -0.04 |
| T20I|2023 | 124 | 14,109 | 0.00107 |
| T20I|2024 | 202 | 22,945 | -0.01 |
| T20I|2025 | 226 | 25,439 | -0.01 |
| T20I|2026 | 128 | 14,293 | 0.10 |

Venue: 94 venues, 17 with at least 30 innings (max 101). `NOT_USED_IN_BASELINE`: venue cells are too sparse for a per-venue baseline without further pooling, and pitch or dew data are absent.

## 9. Model options considered and not used

| Option | Why not now |
|---|---|
| Regularised logistic regression (dot, boundary, wicket) and linear/Poisson models for runs | Adds tuning freedom before the pressure definition is approved; needs the temporal-holdout calibration first |
| Gradient boosting | Same, plus interpretability cost; would hide the context cells that the report shows |
| Mixed models with player random effects | Player effects are exactly what the baseline must not absorb; reserved for the validation phase |
| Per-venue or per-season cells | Sparse (section 8); offered only as a sensitivity |

Nothing is trained in this phase.

## 10. Validation plan (not run here)

1. Strictly-prior baselines and a temporal split (fit before a cut date, evaluate later).
2. Calibration of expected versus actual by decile and pressure band on the held-out period.
3. Ablation of wickets bins, phase and pressure membership; `min_cell_innings` 15/30/60; `tau2_floor` 0.001/0.01/0.1.
4. Rank stability across neighbouring thresholds and candidate definitions (Stage 5).
5. DQ sensitivities: `other` extras rows in and out, wicket-flag disagreement rows, ten Cricsheet-total innings.

## 11. Limitations

1. Context is limited to format, innings role, phase and wickets bin (plus pressure membership in the sensitivity). Opposition, venue, pitch and weather are not controlled.
2. `n_eff` is a Kish count of innings; with per-delivery variance it over-shrinks, which is the conservative direction.
3. The bootstrap resamples matches but holds the baseline fixed; a refit-inside variant is not built.
4. Pressure-sample residuals under B0 are not zero because B0 has no match-state term; they are not a skill estimate.
5. The Stage 5 eligibility experiment and the Stage 6 weight sensitivity are separate steps awaiting approval.
