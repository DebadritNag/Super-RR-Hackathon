# Phase 6 variance-component and floor investigation

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, in-sample diagnostics on TRAIN and VALIDATION. TEST outcomes: not used. Cricsheet: not used. No gate, threshold or Phase 4/5 artifact was changed. Code version `0061c9d62abd2c99`, seed 20260512, 1000 match-cluster bootstrap draws. Criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` (declared before this run, run-log seq 88 for this step).

## 1. Preconditions
- Floor inputs recomputed from the stored context rows reproduce `p5_context_fit` (48/48 contexts, max abs difference 4.90e-11, reproduces = True).
- `k_for` agrees with the hand formula in 14/14 configuration-branch rows (section 2).

## 2. Floor arithmetic
`k_for` gives `tau2 = max(max(between, floor_abs) * mult, floor_abs)` and `k = sigma2 / tau2`. The multiplier acts after the floor. Table from running `k_for` on a floor-hit fit (between -1, sigma2 3) and on the non-finite branch:

| config | branch | floor | mult | k_for | k_hand | agrees |
|---|---|---|---|---|---|---|
| shrink_none | floor_hit | 0.01 | 1.00 | 0.00 | 0.00 | yes |
| shrink_none | non_finite | 0.01 | 1.00 | 0.00 | 0.00 | yes |
| shrink_eb | floor_hit | 0.01 | 1.00 | 100.00 | 100.00 | yes |
| shrink_eb | non_finite | 0.01 | 1.00 | 100.00 | 100.00 | yes |
| shrink_tau0.5 | floor_hit | 0.01 | 0.50 | 100.00 | 100.00 | yes |
| shrink_tau0.5 | non_finite | 0.01 | 0.50 | 100.00 | 100.00 | yes |
| shrink_tau2 | floor_hit | 0.01 | 2.00 | 50.00 | 50.00 | yes |
| shrink_tau2 | non_finite | 0.01 | 2.00 | 100.00 | 100.00 | yes |
| shrink_tau4 | floor_hit | 0.01 | 4.00 | 25.00 | 25.00 | yes |
| shrink_tau4 | non_finite | 0.01 | 4.00 | 100.00 | 100.00 | yes |
| shrink_floor0.001 | floor_hit | 0.001 | 1.00 | 1000.00 | 1000.00 | yes |
| shrink_floor0.001 | non_finite | 0.001 | 1.00 | 1000.00 | 1000.00 | yes |
| shrink_target0 | floor_hit | 0.01 | 1.00 | 100.00 | 100.00 | yes |
| shrink_target0 | non_finite | 0.01 | 1.00 | 100.00 | 100.00 | yes |


For `shrink_tau4` on a floor hit: k = 25.0 = 1 / (4 x 0.01). In the stored contexts 48 of 48 TRAIN fits are floor hits and k under `shrink_tau4` takes the values [25.0].

## 3. Verdicts per context
Verdicts come from the pre-declared flag table; the text is not hand-written.

**PRE_TEST (primary window), 48 contexts.** Verdict counts: {"H-B_SUPPORTED": 4, "H-C_SUPPORTED": 16, "MIXED": 19, "NOT_ESTIMABLE": 1, "UNIDENTIFIED": 8}. Identification counts: {"NOT_ESTIMABLE": 1, "identified_positive": 5, "weakly_identified": 42}.

**TRAIN, 48 contexts.** Verdict counts: {"H-B_SUPPORTED": 2, "H-C_SUPPORTED": 13, "MIXED": 22, "NOT_ESTIMABLE": 4, "UNIDENTIFIED": 7}. Identification counts: {"NOT_ESTIMABLE": 4, "identified_positive": 4, "weakly_identified": 40}.

## 4. Why is the estimate at the floor? Flag counts (PRE_TEST contexts)
| flag | supported in |
|---|---|
| flag_H-A_null | 0/48 |
| flag_H-A_power | 20/48 |
| flag_H-B_i | 4/48 |
| flag_H-B_ii | 40/48 |
| flag_H-B_iii | 9/48 |
| flag_H-B_iv | 22/48 |
| flag_H-B_overall | 24/48 |
| flag_H-C | 36/48 |


- H-A_null: split-covariance interval contains 0 and fewer than 90% of bootstrap draws are positive.
- H-A_power: detectability simulation, share of positive estimates at tau2/sigma2 = 0.01 at least 0.8.
- H-B(i) to (iv): noise-model misspecification tests (Kish arithmetic, sign flip across bases, tercile variance ratio, ICC and dispersion).
- H-C: the lower bound is positive and the required sample exceeds the observed median balls.

### Between-variance sign by noise basis (PRE_TEST contexts)
| basis | contexts with raw between variance > 0 | median raw between variance |
|---|---|---|
| Phase 4 Kish | 0/48 | -1.17 |
| independent balls | 39/48 | 0.15 |
| match cluster | 40/48 | 0.07 |


### Split-half covariance (E7, at least 6 balls per half) and E6
| statistic | value |
|---|---|
| contexts with E7 lower bound > 0 | 5/48 |
| contexts with E6 positive-draw share >= 0.9 | 48/48 |
| median detectability (share positive) at ratio 0.01 | 0.76 |
| median Kish/ball noise ratio over balls per match | 0.61 |
| median player-match ICC | 0.05 |
| median Pearson dispersion | 0.27 |


### How far the verdict labels can be trusted
- Model-free split covariance (E7), 47 estimable contexts: lower bound above 0 in 5, interval contains 0 in 42. This is the only estimator that does not depend on a noise model.
- E6 positive-draw share is at least 0.9 in 47/47 contexts. The pre-declared H-A null needs a share below 0.9, so `H-A_SUPPORTED` could not be reached in this data even where E7 includes 0.
- The E6 bootstrap median of the match-cluster estimate exceeds its point estimate in 47/47 contexts, so resampled estimates are shifted upwards and the E6 lower bound above 0 (used for H-C) is a weaker kind of evidence than the E7 lower bound.
- Median ratio of the E7 estimate to the match-cluster point estimate: 0.33. The cluster basis therefore gives larger between-variance than the model-free split covariance, in line with a cluster noise estimate that is biased low for players with few matches.
- Labels `H-C_SUPPORTED` and `MIXED` below rest partly on E6 and the cluster basis. They say the cluster-basis estimate is positive and larger samples would help; they do not show that the between-player variance is positive.

## 5. Cells of the study (definition x format x role x stream), PRE_TEST
72 cells. Verdict counts: {"H-B_SUPPORTED": 6, "H-C_SUPPORTED": 20, "MIXED": 28, "UNIDENTIFIED": 18}.

| definition | format | role | stream | players | verdict | ident. | E7 lo | E7 hi | E6 share>0 | between Kish | between cluster |
|---|---|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | IPL | batter | runs | 267 | MIXED | identified_positive | 0.03 | 0.13 | 1.00 | -1.01 | 0.22 |
| any\|q0.75 | T20I | batter | runs | 537 | H-C_SUPPORTED | identified_positive | 0.03 | 0.10 | 1.00 | -1.09 | 0.10 |
| any\|q0.75 | IPL | batter | dismissal | 267 | H-B_SUPPORTED | weakly_identified | -0.000219 | 0.00247 | 1.00 | -0.00874 | 0.00419 |
| any\|q0.75 | T20I | batter | dismissal | 537 | H-B_SUPPORTED | weakly_identified | -0.000632 | 0.00218 | 1.00 | -0.00866 | 0.00331 |
| any\|q0.75 | IPL | bowler | charged | 182 | MIXED | weakly_identified | -0.0097 | 0.08 | 1.00 | -0.83 | 0.03 |
| any\|q0.75 | T20I | bowler | charged | 359 | H-C_SUPPORTED | weakly_identified | -0.00976 | 0.06 | 1.00 | -0.96 | 0.08 |
| any\|q0.75 | IPL | bowler | wkt | 182 | H-C_SUPPORTED | weakly_identified | -0.00023 | 0.000664 | 1.00 | -0.02 | 0.000407 |
| any\|q0.75 | T20I | bowler | wkt | 359 | H-C_SUPPORTED | weakly_identified | -0.000212 | 0.000797 | 1.00 | -0.03 | 0.00033 |


## 6. Estimator comparison (primary streams, any|q0.75, PRE_TEST)
| format | role | estimator | basis | value | raw between | status | lo | hi |
|---|---|---|---|---|---|---|---|---|
| IPL | batter | E1 | phase4_kish | 0.03 | -1.01 | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | batter | E2 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | batter | E3 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | batter | E6 | phase4_kish | -0.72 | n/a | ESTIMATED | -0.87 | -0.57 |
| IPL | batter | E1b | ball_independent | 0.08 | 0.08 | ESTIMATED | n/a | n/a |
| IPL | batter | E2 | ball_independent | 0.08 | n/a | ESTIMATED | n/a | n/a |
| IPL | batter | E3 | ball_independent | 0.08 | n/a | ESTIMATED | n/a | n/a |
| IPL | batter | E6 | ball_independent | 0.16 | n/a | ESTIMATED | 0.08 | 0.27 |
| IPL | batter | E1c | match_cluster | 0.22 | 0.22 | ESTIMATED | n/a | n/a |
| IPL | batter | E2 | match_cluster | 0.22 | n/a | ESTIMATED | n/a | n/a |
| IPL | batter | E3 | match_cluster | 0.22 | n/a | ESTIMATED | n/a | n/a |
| IPL | batter | E6 | match_cluster | 0.34 | n/a | ESTIMATED | 0.26 | 0.47 |
| IPL | batter | E7 | split_half_covariance\|min_balls=12 | 0.05 | n/a | ESTIMATED | 0.03 | 0.13 |
| IPL | batter | E5 | gamma_poisson | 0.17 | n/a | ESTIMATED | n/a | n/a |
| T20I | batter | E1 | phase4_kish | 0.03 | -1.09 | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | batter | E2 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | batter | E3 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | batter | E6 | phase4_kish | -0.72 | n/a | ESTIMATED | -0.88 | -0.54 |
| T20I | batter | E1b | ball_independent | 0.08 | 0.08 | ESTIMATED | n/a | n/a |
| T20I | batter | E2 | ball_independent | 0.06 | n/a | ESTIMATED | n/a | n/a |
| T20I | batter | E3 | ball_independent | 0.06 | n/a | ESTIMATED | n/a | n/a |
| T20I | batter | E6 | ball_independent | 0.22 | n/a | ESTIMATED | 0.10 | 0.35 |
| T20I | batter | E1c | match_cluster | 0.10 | 0.10 | ESTIMATED | n/a | n/a |
| T20I | batter | E2 | match_cluster | 0.17 | n/a | ESTIMATED | n/a | n/a |
| T20I | batter | E3 | match_cluster | 0.16 | n/a | ESTIMATED | n/a | n/a |
| T20I | batter | E6 | match_cluster | 0.36 | n/a | ESTIMATED | 0.24 | 0.52 |
| T20I | batter | E7 | split_half_covariance\|min_balls=12 | 0.06 | n/a | ESTIMATED | 0.03 | 0.10 |
| T20I | batter | E5 | gamma_poisson | 0.12 | n/a | ESTIMATED | n/a | n/a |
| IPL | bowler | E1 | phase4_kish | 0.03 | -0.83 | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | bowler | E2 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | bowler | E3 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| IPL | bowler | E6 | phase4_kish | -0.50 | n/a | ESTIMATED | -0.77 | -0.20 |
| IPL | bowler | E1b | ball_independent | 0.23 | 0.23 | ESTIMATED | n/a | n/a |
| IPL | bowler | E2 | ball_independent | 0.03 | n/a | ESTIMATED | n/a | n/a |
| IPL | bowler | E3 | ball_independent | 0.03 | n/a | ESTIMATED | n/a | n/a |
| IPL | bowler | E6 | ball_independent | 0.37 | n/a | ESTIMATED | 0.14 | 0.61 |
| IPL | bowler | E1c | match_cluster | 0.03 | 0.03 | ESTIMATED | n/a | n/a |
| IPL | bowler | E2 | match_cluster | 0.06 | n/a | ESTIMATED | n/a | n/a |
| IPL | bowler | E3 | match_cluster | 0.06 | n/a | ESTIMATED | n/a | n/a |
| IPL | bowler | E6 | match_cluster | 0.27 | n/a | ESTIMATED | 0.09 | 0.54 |
| IPL | bowler | E7 | split_half_covariance\|min_balls=12 | 0.05 | n/a | ESTIMATED | -0.0097 | 0.08 |
| IPL | bowler | E5 | gamma_poisson | 0.06 | n/a | ESTIMATED | n/a | n/a |
| T20I | bowler | E1 | phase4_kish | 0.03 | -0.96 | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | bowler | E2 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | bowler | E3 | phase4_kish | 0.00 | n/a | BETWEEN_VARIANCE_NOT_POSITIVE | n/a | n/a |
| T20I | bowler | E6 | phase4_kish | -0.68 | n/a | ESTIMATED | -0.84 | -0.50 |
| T20I | bowler | E1b | ball_independent | 0.20 | 0.20 | ESTIMATED | n/a | n/a |
| T20I | bowler | E2 | ball_independent | 0.03 | n/a | ESTIMATED | n/a | n/a |
| T20I | bowler | E3 | ball_independent | 0.03 | n/a | ESTIMATED | n/a | n/a |
| T20I | bowler | E6 | ball_independent | 0.29 | n/a | ESTIMATED | 0.19 | 0.42 |
| T20I | bowler | E1c | match_cluster | 0.08 | 0.08 | ESTIMATED | n/a | n/a |
| T20I | bowler | E2 | match_cluster | 0.13 | n/a | ESTIMATED | n/a | n/a |
| T20I | bowler | E3 | match_cluster | 0.13 | n/a | ESTIMATED | n/a | n/a |
| T20I | bowler | E6 | match_cluster | 0.26 | n/a | ESTIMATED | 0.16 | 0.44 |
| T20I | bowler | E7 | split_half_covariance\|min_balls=12 | 0.03 | n/a | ESTIMATED | -0.00976 | 0.06 |
| T20I | bowler | E5 | gamma_poisson | 0.08 | n/a | ESTIMATED | n/a | n/a |


## 7. Required sample (balls per player for reliability 0.5, 0.7, 0.8)
Computed only where a lower bound is above 0; otherwise `NOT_ESTIMABLE`.

| format | role | phase | situation | n* R=0.5 | n* R=0.7 | n* R=0.8 | median balls |
|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 153.79 | 358.83 | 615.14 | 26.00 |
| IPL | batter | ALL | chase | 76.35 | 178.15 | 305.40 | 17.00 |
| IPL | batter | ALL | first_innings | 10.04 | 23.42 | 40.16 | 18.00 |
| IPL | batter | powerplay | ALL | 50.14 | 116.98 | 200.54 | 11.00 |
| IPL | batter | powerplay | first_innings | 19.08 | 44.52 | 76.32 | 9.00 |
| IPL | batter | middle | ALL | 37.95 | 88.54 | 151.79 | 21.00 |
| IPL | batter | middle | chase | 33.84 | 78.96 | 135.36 | 14.50 |
| IPL | batter | middle | first_innings | 27.86 | 65.00 | 111.42 | 17.00 |
| IPL | batter | death | ALL | 15.02 | 35.04 | 60.07 | 14.00 |
| IPL | batter | death | chase | 14.70 | 34.31 | 58.82 | 11.00 |
| IPL | batter | death | first_innings | 20.58 | 48.03 | 82.33 | 8.00 |
| IPL | bowler | ALL | ALL | 132.03 | 308.07 | 528.12 | 50.50 |
| IPL | bowler | ALL | chase | 86.33 | 201.43 | 345.31 | 37.00 |
| IPL | bowler | ALL | first_innings | 169.50 | 395.50 | 678.00 | 32.00 |
| IPL | bowler | powerplay | ALL | 22.65 | 52.84 | 90.58 | 12.00 |
| IPL | bowler | powerplay | chase | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 10.00 |
| IPL | bowler | powerplay | first_innings | 91.79 | 214.19 | 367.18 | 9.00 |
| IPL | bowler | middle | ALL | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 29.00 |
| IPL | bowler | middle | chase | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 19.00 |
| IPL | bowler | middle | first_innings | 35.11 | 81.92 | 140.44 | 19.00 |
| IPL | bowler | death | ALL | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 23.50 |
| IPL | bowler | death | chase | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 19.00 |
| IPL | bowler | death | first_innings | 84.25 | 196.59 | 337.01 | 19.00 |
| T20I | batter | ALL | ALL | 98.98 | 230.96 | 395.94 | 19.00 |
| T20I | batter | ALL | chase | 72.38 | 168.90 | 289.54 | 14.00 |
| T20I | batter | ALL | first_innings | 33.72 | 78.68 | 134.88 | 13.00 |
| T20I | batter | powerplay | ALL | 20.73 | 48.36 | 82.91 | 7.00 |
| T20I | batter | powerplay | chase | 6.85 | 15.98 | 27.40 | 7.50 |
| T20I | batter | powerplay | first_innings | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 6.00 |
| T20I | batter | middle | ALL | 18.90 | 44.10 | 75.59 | 15.00 |
| T20I | batter | middle | chase | 21.15 | 49.35 | 84.60 | 10.00 |
| T20I | batter | middle | first_innings | 44.18 | 103.08 | 176.70 | 14.00 |
| T20I | batter | death | ALL | 28.72 | 67.01 | 114.87 | 11.50 |
| T20I | batter | death | chase | 6.67 | 15.56 | 26.68 | 9.00 |
| T20I | batter | death | first_innings | 19.06 | 44.48 | 76.25 | 9.00 |
| T20I | bowler | ALL | ALL | 38.77 | 90.46 | 155.08 | 31.00 |
| T20I | bowler | ALL | chase | 35.12 | 81.94 | 140.47 | 23.00 |
| T20I | bowler | ALL | first_innings | 41.01 | 95.68 | 164.02 | 21.00 |
| T20I | bowler | powerplay | ALL | 19.16 | 44.70 | 76.63 | 9.00 |
| T20I | bowler | powerplay | chase | 10.17 | 23.73 | 40.68 | 11.00 |
| T20I | bowler | powerplay | first_innings | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 7.00 |
| T20I | bowler | middle | ALL | 35.83 | 83.60 | 143.31 | 20.00 |
| T20I | bowler | middle | chase | 50.47 | 117.76 | 201.88 | 13.00 |
| T20I | bowler | middle | first_innings | 35.75 | 83.43 | 143.02 | 15.00 |
| T20I | bowler | death | ALL | 97.43 | 227.34 | 389.72 | 17.00 |
| T20I | bowler | death | chase | 476.86 | 1112.67 | 1907.43 | 13.00 |
| T20I | bowler | death | first_innings | NOT_ESTIMABLE | NOT_ESTIMABLE | NOT_ESTIMABLE | 13.00 |


## 8. Consequence
Verdicts over the 48 contexts: {"H-B_SUPPORTED": 4, "H-C_SUPPORTED": 16, "MIXED": 19, "NOT_ESTIMABLE": 1, "UNIDENTIFIED": 8}. Identification: {"NOT_ESTIMABLE": 1, "identified_positive": 5, "weakly_identified": 42}.
- Contexts that are `UNIDENTIFIED` or `NOT_ESTIMABLE`: the data cannot identify the between-player variance. Consequence: wider uncertainty (intervals from E6), shorter lists, and these contexts stay restricted. The shrinkage estimator is not changed here.
- Contexts with `H-B_SUPPORTED` or `MIXED`: noise-model misspecification is supported. OPEN DECISION for the user: whether to switch the noise basis in the methodology. Not applied; a methodology change is outside this phase's stop condition.
- Contexts with `H-C_SUPPORTED`: a positive lower bound exists but the sample is below the required size; more data would be needed.

## 9. Limits
- Every number is in-sample. A consistent finding across estimators is not validation.
- The noise model cannot be tested with these data alone; the three noise bases bracket it.
- E4 and E5 are sensitivity checks. E5 is `MISSPECIFIED_FOR_RUNS` on runs streams.
- Within-innings dependence is not separable: stored context rows are match-level sums.
- The detectability simulation is parametric; its noise comes from the observed match-cluster basis.

## 10. Per-context table (PRE_TEST)
| format | role | phase | situation | players | between Kish | between cluster | E7 | E7 lo | E7 hi | E6 share>0 | verdict | ident. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 267 | -1.01 | 0.22 | 0.05 | 0.03 | 0.13 | 1.00 | MIXED | identified_positive |
| IPL | batter | ALL | chase | 231 | -1.38 | 0.21 | 0.08 | 0.02 | 0.18 | 1.00 | MIXED | identified_positive |
| IPL | batter | ALL | first_innings | 209 | -1.16 | 0.21 | 0.07 | -7.89e-06 | 0.14 | 1.00 | H-B_SUPPORTED | weakly_identified |
| IPL | batter | powerplay | ALL | 102 | -1.66 | 0.07 | 0.0088 | -0.14 | 0.23 | 1.00 | MIXED | weakly_identified |
| IPL | batter | powerplay | chase | 54 | -2.70 | 0.03 | -0.06 | -1.09 | 0.29 | 0.99 | NOT_ESTIMABLE | NOT_ESTIMABLE |
| IPL | batter | powerplay | first_innings | 91 | -1.55 | 0.14 | 0.21 | -0.11 | 0.54 | 1.00 | MIXED | weakly_identified |
| IPL | batter | middle | ALL | 193 | -1.09 | 0.06 | -0.02 | -0.05 | 0.06 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | batter | middle | chase | 154 | -1.57 | 0.06 | 0.05 | -0.08 | 0.12 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | batter | middle | first_innings | 150 | -1.02 | 0.05 | 0.00294 | -0.04 | 0.08 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | batter | death | ALL | 229 | -1.42 | 0.18 | 0.06 | -0.000365 | 0.21 | 1.00 | MIXED | weakly_identified |
| IPL | batter | death | chase | 196 | -1.59 | 0.16 | 0.07 | -0.04 | 0.25 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | batter | death | first_innings | 163 | -1.65 | 0.13 | 0.07 | -0.08 | 0.21 | 1.00 | MIXED | weakly_identified |
| IPL | bowler | ALL | ALL | 182 | -0.83 | 0.03 | 0.05 | -0.0091 | 0.08 | 1.00 | MIXED | weakly_identified |
| IPL | bowler | ALL | chase | 151 | -1.04 | 0.05 | 0.06 | -0.02 | 0.11 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | bowler | ALL | first_innings | 153 | -0.87 | 0.02 | 0.04 | -0.02 | 0.09 | 1.00 | MIXED | weakly_identified |
| IPL | bowler | powerplay | ALL | 103 | -1.30 | 0.15 | 0.03 | -0.15 | 0.17 | 1.00 | MIXED | weakly_identified |
| IPL | bowler | powerplay | chase | 53 | -2.39 | -0.03 | -0.13 | -0.50 | 0.55 | 1.00 | UNIDENTIFIED | weakly_identified |
| IPL | bowler | powerplay | first_innings | 94 | -0.79 | 0.03 | 0.01 | -0.18 | 0.25 | 1.00 | MIXED | weakly_identified |
| IPL | bowler | middle | ALL | 162 | -0.84 | -0.00379 | 0.02 | -0.03 | 0.07 | 1.00 | UNIDENTIFIED | weakly_identified |
| IPL | bowler | middle | chase | 133 | -0.93 | -0.00219 | -0.03 | -0.10 | 0.10 | 1.00 | UNIDENTIFIED | weakly_identified |
| IPL | bowler | middle | first_innings | 130 | -0.97 | 0.06 | 0.04 | -0.03 | 0.11 | 1.00 | H-C_SUPPORTED | weakly_identified |
| IPL | bowler | death | ALL | 144 | -0.75 | -0.02 | -0.01 | -0.09 | 0.08 | 1.00 | UNIDENTIFIED | weakly_identified |
| IPL | bowler | death | chase | 125 | -0.92 | -0.00532 | 0.01 | -0.08 | 0.13 | 1.00 | UNIDENTIFIED | weakly_identified |
| IPL | bowler | death | first_innings | 105 | -1.00 | 0.05 | 0.06 | -0.09 | 0.19 | 1.00 | MIXED | weakly_identified |
| T20I | batter | ALL | ALL | 537 | -1.09 | 0.10 | 0.06 | 0.03 | 0.10 | 1.00 | H-C_SUPPORTED | identified_positive |
| T20I | batter | ALL | chase | 423 | -1.56 | 0.16 | 0.08 | 0.03 | 0.16 | 1.00 | MIXED | identified_positive |
| T20I | batter | ALL | first_innings | 411 | -1.13 | 0.06 | 0.03 | -0.03 | 0.09 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | batter | powerplay | ALL | 188 | -1.37 | 0.15 | 0.02 | -0.16 | 0.23 | 1.00 | MIXED | weakly_identified |
| T20I | batter | powerplay | chase | 96 | -2.07 | 0.59 | -0.41 | -0.81 | 0.46 | 1.00 | H-B_SUPPORTED | weakly_identified |
| T20I | batter | powerplay | first_innings | 145 | -1.04 | -0.14 | 0.16 | -0.21 | 0.39 | 1.00 | UNIDENTIFIED | weakly_identified |
| T20I | batter | middle | ALL | 393 | -1.17 | 0.12 | -0.00179 | -0.04 | 0.05 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | batter | middle | chase | 290 | -1.57 | 0.12 | 0.00408 | -0.10 | 0.13 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | batter | middle | first_innings | 271 | -1.06 | 0.04 | 0.00761 | -0.04 | 0.07 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | batter | death | ALL | 430 | -1.23 | 0.18 | 0.13 | 0.04 | 0.21 | 1.00 | H-C_SUPPORTED | identified_positive |
| T20I | batter | death | chase | 337 | -1.66 | 0.31 | 0.10 | -0.01 | 0.29 | 1.00 | H-B_SUPPORTED | weakly_identified |
| T20I | batter | death | first_innings | 291 | -1.36 | 0.09 | 0.03 | -0.06 | 0.12 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | bowler | ALL | ALL | 359 | -0.96 | 0.08 | 0.03 | -0.00781 | 0.06 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | bowler | ALL | chase | 265 | -1.38 | 0.10 | 0.03 | -0.03 | 0.08 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | bowler | ALL | first_innings | 291 | -0.96 | 0.07 | 0.03 | -0.01 | 0.08 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | powerplay | ALL | 159 | -1.25 | 0.16 | 0.04 | -0.09 | 0.23 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | powerplay | chase | 68 | -2.02 | 0.35 | 0.06 | -0.15 | 0.54 | 1.00 | H-B_SUPPORTED | weakly_identified |
| T20I | bowler | powerplay | first_innings | 130 | -0.86 | -0.11 | 0.06 | -0.10 | 0.28 | 1.00 | UNIDENTIFIED | weakly_identified |
| T20I | bowler | middle | ALL | 293 | -0.86 | 0.08 | 0.03 | -0.03 | 0.08 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | middle | chase | 202 | -1.38 | 0.06 | 0.03 | -0.06 | 0.09 | 1.00 | H-C_SUPPORTED | weakly_identified |
| T20I | bowler | middle | first_innings | 225 | -0.91 | 0.07 | 0.02 | -0.03 | 0.12 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | death | ALL | 285 | -1.23 | 0.03 | 0.00739 | -0.04 | 0.07 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | death | chase | 217 | -1.54 | 0.00279 | -0.00597 | -0.09 | 0.11 | 1.00 | MIXED | weakly_identified |
| T20I | bowler | death | first_innings | 202 | -1.17 | -0.01 | -0.00365 | -0.10 | 0.06 | 1.00 | UNIDENTIFIED | weakly_identified |

