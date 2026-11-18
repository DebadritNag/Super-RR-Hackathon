# Methodology comparison: three approaches under predeclared criteria

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`. The hash was verified against the hash file and the run-log row `seq = 1` before this comparison ran, and the criteria were not altered after any result was seen. Every number comes from the stored `p8_*` tables. Batters and bowlers are compared within their own role only.

## 1. The three approaches

- **A, context-adjusted performance.** A player-blind gradient-boosting model predicts the runs and the wicket probability of each delivery from the pre-delivery situation. A player's score is the intensity-weighted mean of observed minus expected, shrunk by REML random effects. Baseline: the same residual on low-intensity deliveries.
- **B, leverage and win probability added (WPA).** A calibrated win-probability model values each delivery; credit goes to the striker, bowler or team by explicit rules (wides and no-balls to the bowler, byes to the team, run-outs never to the bowler). The score is WPA above what the leverage of the situation predicts.
- **C, Pressure Response Index (PRI).** Components A, B and a consistency component (share of pressure units that beat the expectation) are weighted by data-derived reliability on FIT matches only. Every weight rule gave A and B no weight, so the PRI reduces to the consistency component for both roles. It is not an A plus B composite.

## 2. Pressure definitions tested (delivery level, before any player ranking)

| candidate | pass | test_a | test_b | test_c | test_e | test_d | n_tests_passed | phases_passing | innings_coverage | primary | primary_basis |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | no | 3 | 2 | 1 | no |  |
| P1 | no | no | no | no | no | yes | 0 | 0 | 0 | no |  |
| P2 | no | no | no | no | no | yes | 0 | 0 | 0 | no |  |
| P3 | no | yes | yes | yes | no | yes | 3 | 1 | 1 | no |  |
| P4 | no | yes | yes | yes | no | no | 3 | 2 | 2 | yes | BEST_AVAILABLE_NOT_PASSING |
| P5 | no | no | no | yes | no | yes | 1 | 0 | 0 | no |  |
| P6 | no | no | yes | yes | no | no | 2 | 1 | 0 | no |  |

No candidate passes the predeclared rule: the monotonic trend test (e) fails for all. P4 (wickets lost share times innings progress, both innings) was used as the best available definition by the predeclared ordering (most tests passed, widest innings coverage). P1 and P2 (win-probability based) fail the direction tests. The intensity definition is therefore unvalidated and no list can exceed EXPLORATORY.

## 3. Predictive quality of the building blocks (chronological validation)

Expected-outcome models of Approach A on VALIDATION (2025), against a constant:

| role | target | chosen | gain vs constant (%) |
|---|---|---|---|
| batter | runs | gbm | 1.626 |
| batter | wicket | gbm | 1.743 |
| batter | dot | gbm | 2.945 |
| batter | boundary | gbm | 3.084 |
| bowler | runs | gbm | 1.508 |
| bowler | wicket | gbm | 1.514 |
| bowler | dot | gbm | 2.964 |
| bowler | boundary | gbm | 3.118 |

Win-probability models of Approach B on VALIDATION:

| model | n_validation | brier | brier_const | brier_logit | slope | intercept | gate_passed |
|---|---|---|---|---|---|---|---|
| W1 | 22086 | 0.2150 | 0.2510 | 0.2227 | 0.8855 | -0.1380 | yes |
| W2 | 20040 | 0.1167 | 0.2506 | 0.1224 | 1.1337 | -0.0246 | yes |

The win-probability models are well calibrated and beat both baselines, so the pipeline is technically sound. The expected-outcome models gain only 1.5% to 3% over a constant: ball outcomes are mostly noise given the pre-delivery state, which limits how much of a residual can be attributed to anything but chance. Approach C has no predictive model of its own.

## 4. Player differentiation, reliability and stability (predeclared metrics)

**Batters**

| approach | split-half SB | SB low | SB high | time_sb | out-of-time rho | oot low | icc1 | between_player_variance_at_floor | mean_data_weight | phase6_gate_passed | players with Top-10 prob >= 0.5 | n_eligible | basis | chosen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A (context-adjusted performance) | 0.057 | -0.220 | 0.361 | 0.128 | 0.199 | 0.017 | 0.006 | no | 0.069 | no | 5.000 | 225 | all PRE_TEST matches | yes |
| B (leverage and win probability added) | 0.042 | -0.331 | 0.360 | -0.072 | -0.001 | -0.201 | 0.005 | yes | 0.000 | no | 1.000 | 224 | all PRE_TEST matches | no |
| C (Pressure Response Index) | 0.057 | -0.190 | 0.300 | -0.087 | -0.020 | -0.197 | n/a | no | 0.117 | no | 2.000 | 224 | held-out matches only (weights fitted on FIT matches) | no |

**Bowlers**

| approach | split-half SB | SB low | SB high | time_sb | out-of-time rho | oot low | icc1 | between_player_variance_at_floor | mean_data_weight | phase6_gate_passed | players with Top-10 prob >= 0.5 | n_eligible | basis | chosen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A (context-adjusted performance) | 0.220 | -0.228 | 0.330 | 0.122 | 0.131 | -0.074 | 0.013 | no | 0.237 | no | 6.000 | 221 | all PRE_TEST matches | no |
| B (leverage and win probability added) | -0.135 | -0.465 | 0.258 | 0.043 | -0.176 | -0.364 | 0.032 | yes | 0.000 | no | 0.000 | 221 | all PRE_TEST matches | no |
| C (Pressure Response Index) | 0.267 | -0.078 | 0.391 | 0.175 | 0.199 | 0.027 | n/a | no | 0.263 | no | 5.000 | 221 | held-out matches only (weights fitted on FIT matches) | yes |

SB is the Spearman-Brown corrected odd/even match split-half correlation of unshrunk precision-weighted means (interval: 1000-draw match-cluster bootstrap). Approach C's figures use held-out matches only (its weights were fitted on FIT matches), A's and B's use all matches, so the columns are not like for like (C has fewer matches per player in each half, which lowers reliability by construction). The selection rule was applied to these figures as declared and the difference is reported, not corrected. The Phase 6 data-weight gate (mean data weight >= 0.5) is reported unchanged: no approach passes it.

Approach C data-derived weights (FIT matches only):

| role | component | n_players_fit | split_half_sb | tau2_fit | floor_fit | status | final_weight |
|---|---|---|---|---|---|---|---|
| batter | A | 214 | 0.0695 | 0.0000 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| batter | B | 214 | -0.2256 | 0.0000 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| batter | CONS | 214 | 0.1875 | 0.0031 | no | ACTIVE | 1.0000 |
| bowler | A | 212 | -0.2329 | 0.0003 | no | NO_SIGNAL_NONPOSITIVE_RELIABILITY | 0.0000 |
| bowler | B | 212 | -0.1001 | 0.0000 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| bowler | CONS | 212 | 0.1754 | 0.0039 | no | ACTIVE | 1.0000 |

Between-player variance over noise and ICC(1) per component:

| role | component | icc1 | between_over_noise |
|---|---|---|---|
| batter | A | 0.0066 | 0.0836 |
| batter | B | 0.0053 | 0.0000 |
| batter | CONS | 0.0042 | 0.1386 |
| bowler | A | 0.0132 | 0.3630 |
| bowler | B | 0.0319 | 0.0000 |
| bowler | CONS | 0.0151 | 0.4047 |

## 5. Format fairness (IPL and T20I)

| approach | role | players_both_formats | spearman | low | high | combination_supported |
|---|---|---|---|---|---|---|
| A | batter | 85 | 0.100 | -0.136 | 0.290 | no |
| A | bowler | 76 | 0.064 | -0.185 | 0.300 | no |
| B | batter | 85 | 0.040 | -0.168 | 0.263 | no |
| B | bowler | 76 | -0.174 | -0.378 | 0.061 | no |
| C | batter | 85 | -0.105 | -0.318 | 0.116 | no |
| C | bowler | 76 | 0.221 | -0.018 | 0.430 | no |

The declared combination rule needs a cross-format lower bound of at least 0.3 with at least 30 players in both formats. No approach meets it, so the combined estimate is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`: units are format-centred and each unit is weighted by its own precision, with no fixed 70:30 split. Each listed player's IPL and T20I scores and ranks are shown in the CSV.

## 6. Explainability (fixed checklist, last tie-break)

A scores 3 (observed against expected from observable inputs only), B and C score 2 (a modelled win-probability state, or a data-weighted index). The checklist decided nothing in this run because an earlier criterion separated the approaches.

## 7. Selection under the predeclared rule

- **Batters**: Chosen approach A by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects A and the point-estimate path selects A: the two paths agree. Rule text: highest split-half lower bound; within 0.05 choose by out-of-time lower bound, then inclusion concentration, then explainability, then id order A, B, C.
- **Bowlers**: Chosen approach C by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects C and the point-estimate path selects C: the two paths agree. Rule text: highest split-half lower bound; within 0.05 choose by out-of-time lower bound, then inclusion concentration, then explainability, then id order A, B, C.

For batters A and C are within 0.001 of each other on the split-half point estimate (0.0571 and 0.0570) and both intervals include 0; A is chosen because both branches of the rule select it (it also has the better out-of-time lower bound). The choice between them should not be read as a performance difference. For bowlers C leads on the split-half point estimate, its lower bound and the out-of-time lower bound, while A has one more player with a Top-10 inclusion probability of at least 0.5; C's interval also includes 0, and C's figures come from held-out matches only.

## 8. Sensitivity of the submitted orderings

Each row compares the submitted ordering with a variant: Spearman correlation over common eligible players and the overlap of the two Top 10 sets (out of 10).

**Batters** (approach A)

| family | comparison | n_common | spearman | top10_overlap | note |
|---|---|---|---|---|---|
| assumption (ordering, weights, innings) | rank_by_pressure_delta | 167 | 0.522 | 1.000 |  |
| assumption (ordering, weights, innings) | unshrunk_ordering | 225 | 0.935 | 3.000 |  |
| bootstrap | bootstrap_method_check | 27 | n/a | n/a | fixed-variance versus full-refit Top-10 inclusion: largest gap 0.207 over 27 players (within 0.05: False); the full refit is used |
| calendar window | window_2022_2024 | 186 | 0.831 | 3.000 | main Top 10 players estimable in window: 10; statistic: precision-weighted mean residual; floors {'TRAIN': 8, 'VALIDATION': 4} |
| calendar window | window_2025 | 146 | 0.669 | 3.000 | main Top 10 players estimable in window: 9; statistic: precision-weighted mean residual; floors {'TRAIN': 8, 'VALIDATION': 4} |
| component or approach | component_runs_only | 225 | 0.645 | 5.000 |  |
| component or approach | component_wicket_only | 225 | 0.683 | 0.000 |  |
| eligibility floor | eligibility_floor_x0.5 | 225 | 0.998 | 10.000 |  |
| eligibility floor | eligibility_floor_x2.0 | 134 | 0.994 | 10.000 |  |
| format (IPL, T20I, combined) | scope_IPL_only | 104 | 0.867 | 6.000 |  |
| format (IPL, T20I, combined) | scope_T20I_only | 140 | 0.811 | 5.000 |  |
| pressure definition | intensity_P0 | 160 | 0.818 | 3.000 |  |
| pressure definition | intensity_P3 | 129 | 0.655 | 3.000 |  |
| pressure definition | intensity_P5 | 122 | 0.364 | 4.000 |  |
| pressure definition | intensity_P6 | 120 | 0.729 | 3.000 |  |

**Bowlers** (approach C)

| family | comparison | n_common | spearman | top10_overlap | note |
|---|---|---|---|---|---|
| assumption (ordering, weights, innings) | equal_weights_not_data_derived | 221 | 0.851 | 8.000 |  |
| assumption (ordering, weights, innings) | innings2_units_only | 221 | 0.626 | 8.000 |  |
| assumption (ordering, weights, innings) | unshrunk_ordering | 221 | 0.967 | 2.000 |  |
| bootstrap | bootstrap_method_check | 221 | n/a | n/a | 1000 draws, floor-draw share {"CONS": 0.0}, weights fixed from FIT matches (TRAIN odd parity) |
| calendar window | window_2022_2024 | 179 | 0.860 | 4.000 | main Top 10 players estimable in window: 10; statistic: share of positive units; floors {'TRAIN': 8, 'VALIDATION': 4} |
| calendar window | window_2025 | 138 | 0.586 | 3.000 | main Top 10 players estimable in window: 10; statistic: share of positive units; floors {'TRAIN': 8, 'VALIDATION': 4} |
| component or approach | component_A_only | 221 | 0.778 | 8.000 |  |
| component or approach | component_B_only | 221 | 0.386 | 0.000 |  |
| component or approach | component_CONS_only | 221 | 1.000 | 10.000 |  |
| component or approach | published_approach_A_rank | 221 | 0.776 | 8.000 |  |
| component or approach | published_approach_B_rank | 221 | 0.386 | 0.000 |  |
| eligibility floor | eligibility_floor_x0.5 | 221 | 0.998 | 10.000 |  |
| eligibility floor | eligibility_floor_x2.0 | 136 | 0.999 | 10.000 |  |
| format (IPL, T20I, combined) | hierarchical_format_common_effect | 221 | 0.999 | 10.000 |  |
| format (IPL, T20I, combined) | scope_IPL_only | 102 | 0.839 | 6.000 |  |
| format (IPL, T20I, combined) | scope_T20I_only | 154 | 0.920 | 7.000 |  |
| pressure definition | intensity_P0 | 164 | 0.665 | 7.000 | eligibility from the A-unit floors |
| pressure definition | intensity_P3 | 110 | 0.592 | 6.000 | eligibility from the A-unit floors |
| pressure definition | intensity_P5 | 131 | 0.323 | 1.000 | eligibility from the A-unit floors |
| pressure definition | intensity_P6 | 116 | 0.591 | 6.000 | eligibility from the A-unit floors |

Reading: the ordering is stable to eligibility floors and moderately stable to format and window, but the Top 10 membership changes substantially with the pressure definition, the shrinkage assumption (unshrunk ordering) and the components used, which is the sensitivity Phase 6 reported. The fixed-variance bootstrap shortcut differs from the full refit by more than the declared 0.05 for batters, so the full refit is used for every published inclusion probability.

## 9. Conclusion

No approach meets the PROVISIONAL threshold in either role. The selected approaches are the best-supported available (batters A, bowlers C) and both lists are EXPLORATORY. The central Phase 6 finding is confirmed with a richer method: the match-level data do not reliably separate players on pressure performance.

