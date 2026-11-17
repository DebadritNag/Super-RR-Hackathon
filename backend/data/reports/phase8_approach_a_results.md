# Phase 8 Approach A results: context-adjusted performance under continuous pressure

Status: **EXPERIMENTAL_NOT_VALIDATED**. This file reports Approach A only (chunk 2). Approaches B and C, the cross-approach selection and the submitted Top 10 files come later. Every number below is read from the `p8_a_*` and `p8_intensity_*` tables in `phase8.duckdb`.

## 1. What was run

- Data: IPL and T20I deliveries in TRAIN (to 2024-12-31) and VALIDATION (2025). TEST (2026 onward) was not opened.
- Expected-outcome models: gradient boosting on pre-delivery state, player-blind, fitted on TRAIN, one selection pass on VALIDATION; TRAIN scored out of fold (`match_id % 5`), VALIDATION scored by the TRAIN model.
- Unit of analysis: player-match-innings. Pressure units use deliveries with intensity >= 0.5 weighted by intensity.
- Shrinkage: REML random effect per scope (COMBINED with format-centred units, IPL, T20I). No variance floor is imposed.
- Declared deviations from the design: no early stopping on an internal holdout and no isotonic recalibration (calibration slope, intercept and decile tables are reported instead); test (d) of the intensity validity tests and candidates P1 and P2 need the win-probability model, which belongs to Approach B, so they are not available here.

### Data exclusions (from the data layer)

| reason | competition_type | rows | matches |
|---|---|---|---|
| OUT_OF_SCOPE_COMPETITION | OTHER_T20 | 6985 | 30 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | IPL | 10 | 1 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | T20I | 12 | 2 |
| DLS_NOT_RECONSTRUCTABLE | IPL | 377 | 3 |
| DLS_NOT_RECONSTRUCTABLE | T20I | 1941 | 23 |
| METRIC_WICKET_FLAG_ANOMALY | ALL | 11 | 11 |
| METRIC_EXTRAS_LABEL_UNVERIFIED | ALL | 205 | 166 |

## 2. Expected-outcome models (VALIDATION, out of sample)

| role | target | chosen | primary_metric | gbm_rmse | const_rmse | gbm_log_loss | const_log_loss | gain vs constant (%) |
|---|---|---|---|---|---|---|---|---|
| batter | runs | gbm | rmse | 1.7288 | 1.7574 | n/a | n/a | 1.6264 |
| batter | wicket | gbm | log_loss | n/a | n/a | 0.2102 | 0.2139 | 1.7433 |
| batter | dot | gbm | log_loss | n/a | n/a | 0.6405 | 0.6599 | 2.9451 |
| batter | boundary | gbm | log_loss | n/a | n/a | 0.4685 | 0.4834 | 3.0836 |
| bowler | runs | gbm | rmse | 1.7052 | 1.7313 | n/a | n/a | 1.5082 |
| bowler | wicket | gbm | log_loss | n/a | n/a | 0.2068 | 0.2100 | 1.5139 |
| bowler | dot | gbm | log_loss | n/a | n/a | 0.6401 | 0.6597 | 2.9639 |
| bowler | boundary | gbm | log_loss | n/a | n/a | 0.4685 | 0.4836 | 3.1177 |

The gain over a constant mean is small (a few percent at most). Ball outcomes are mostly noise given the pre-delivery state, so the expected value removes only a modest part of the context effect. This limits how much of a player's residual can be attributed to anything but chance.

Calibration of the chosen classifiers on VALIDATION (slope 1 and intercept 0 are perfect):

| role | target | chosen_log_loss | chosen_brier | chosen_slope | chosen_intercept |
|---|---|---|---|---|---|
| batter | wicket | 0.210 | 0.052 | 0.954 | -0.115 |
| batter | dot | 0.640 | 0.224 | 0.939 | -0.046 |
| batter | boundary | 0.469 | 0.148 | 0.982 | -0.001 |
| bowler | wicket | 0.207 | 0.051 | 0.948 | -0.132 |
| bowler | dot | 0.640 | 0.224 | 0.942 | -0.046 |
| bowler | boundary | 0.469 | 0.148 | 0.981 | 0.001 |

Component standardisation constants (TRAIN standard deviation of each oriented residual):

| component | train_sd |
|---|---|
| batter_runs | 1.6841 |
| batter_wicket | 0.2248 |
| batter_dot | 0.4727 |
| batter_boundary | 0.3798 |
| bowler_runs | 1.6619 |
| bowler_wicket | 0.2221 |
| bowler_dot | 0.4727 |
| bowler_boundary | 0.3798 |

## 3. Pressure-intensity definitions under the predeclared validity tests

Tests a, b, c, e use TRAIN deciles (edges within each stratum), confirmed with the same edges on VALIDATION. Pass rule: a, b, e hold pooled on TRAIN, the signs of a and b hold on VALIDATION, and a and b hold in at least two of three phases. P0 is the Phase 6 style binary reference and is never primary.

| candidate | pass | test_a | test_b | test_c | test_e | validation_signs_ok | phases_passing | innings_coverage | n_tests_passed | reference_only | primary | primary_basis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | yes | 2 | 1 | 3 | yes | no |  |
| P3 | no | yes | yes | yes | no | yes | 1 | 1 | 3 | no | no |  |
| P4 | no | yes | yes | yes | no | yes | 2 | 2 | 3 | no | yes | BEST_AVAILABLE_NOT_PASSING |
| P5 | no | no | no | yes | no | no | 0 | 0 | 1 | no | no |  |
| P6 | no | no | yes | yes | no | yes | 1 | 0 | 2 | no | no |  |

Pooled decile contrasts (highest minus lowest intensity bin; runs are relative to the TRAIN mean of the same innings and phase):

| candidate | period | n_cell | runs_diff | runs_halfwidth | wkt_diff | wkt_halfwidth | var_diff | runs_spearman | wkt_spearman |
|---|---|---|---|---|---|---|---|---|---|
| P0 | TRAIN | 115212 | -0.0589 | 0.0307 | 0.0290 | 0.0033 | 0.2376 | n/a | n/a |
| P0 | VALIDATION | 43376 | -0.1430 | 0.0420 | 0.0316 | 0.0051 | 0.0845 | n/a | n/a |
| P3 | TRAIN | 54316 | -0.1105 | 0.0989 | 0.0474 | 0.0102 | 0.2854 | 0.2606 | 0.8667 |
| P3 | VALIDATION | 20295 | -0.1569 | 0.1340 | 0.0503 | 0.0144 | 0.2613 | -0.5030 | 0.8061 |
| P4 | TRAIN | 115212 | -0.1920 | 0.0601 | 0.0573 | 0.0057 | 0.0847 | -0.5152 | 0.8788 |
| P4 | VALIDATION | 43376 | -0.3275 | 0.0807 | 0.0553 | 0.0094 | -0.0976 | -0.9758 | 0.9879 |
| P5 | TRAIN | 53823 | 0.2325 | 0.0858 | -0.0031 | 0.0074 | 0.4191 | 0.2121 | -0.2727 |
| P5 | VALIDATION | 20105 | 0.1408 | 0.1441 | -0.0051 | 0.0111 | 0.0515 | 0.8788 | -0.3091 |
| P6 | TRAIN | 54316 | -0.0697 | 0.0919 | 0.0530 | 0.0093 | 0.3390 | 0.2121 | 0.8424 |
| P6 | VALIDATION | 20295 | -0.1263 | 0.1415 | 0.0528 | 0.0154 | 0.1818 | -0.7333 | 0.9273 |

**No candidate passes the predeclared rule.** The monotonic-trend test (e) fails for every candidate on TRAIN. The predeclared ordering (tests passed, then innings coverage, then id) was applied to the non-reference candidates only to obtain a working definition: **P4** (BEST_AVAILABLE_NOT_PASSING). This choice was made from delivery-level validity tests and never from player rankings. It means the intensity definition itself is unvalidated and no list built on it can exceed EXPLORATORY.

Test (d) (mean absolute win-probability change) and candidates P1 and P2 are NOT_AVAILABLE in this chunk.

## 4. Estimation and reliability by intensity definition (COMBINED scope, eligible players)

| role | intensity | reference_only | n_eligible | tau2 | sigma2 | floor | mean_B | share_B_gt_0_5 | split-half SB | SB low | SB high | time_sb | icc1 | rho(estimate, exposure) | volume_bias_flag | out-of-time rho | oot low | players with Top-10 prob >= 0.5 | median_rank_interval_width | indicative_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| batter | P0 | yes | 160 | 0.0000 | 1.0707 | yes | 0.0000 | 0.0000 | -0.0442 | -0.2108 | 0.3716 | -0.0463 | 0.0033 | 0.3629 | yes | 0.1331 | -0.0875 | 5 | 113.0000 | EXPLORATORY |
| batter | P3 | no | 130 | 0.0000 | 1.0378 | yes | 0.0000 | 0.0000 | 0.1428 | -0.2477 | 0.5317 | 0.0908 | 0.0087 | 0.4466 | yes | 0.1528 | -0.2005 | 6 | 92.0250 | EXPLORATORY |
| batter | P4 | no | 225 | 0.0003 | 1.0197 | no | 0.0691 | 0.0000 | 0.0571 | -0.2201 | 0.3607 | 0.1278 | 0.0064 | 0.3419 | yes | 0.1991 | 0.0173 | 5 | 163.0250 | EXPLORATORY |
| batter | P5 | no | 145 | 0.0000 | 0.8716 | no | 0.0028 | 0.0000 | 0.3045 | -0.1385 | 0.5088 | 0.2035 | 0.0153 | 0.2954 | no | 0.2778 | -0.0362 | 5 | 101.0000 | EXPLORATORY |
| batter | P6 | no | 120 | 0.0000 | 1.0200 | yes | 0.0000 | 0.0000 | 0.0683 | -0.2888 | 0.4816 | -0.0403 | 0.0048 | 0.3965 | yes | 0.2971 | -0.0855 | 5 | 85.0250 | EXPLORATORY |
| bowler | P0 | yes | 164 | 0.0008 | 0.8023 | no | 0.1754 | 0.0000 | 0.0282 | -0.2741 | 0.3443 | 0.0440 | 0.0109 | 0.0473 | no | 0.1514 | -0.0849 | 6 | 119.5250 | EXPLORATORY |
| bowler | P3 | no | 110 | 0.0006 | 0.7245 | no | 0.1579 | 0.0000 | 0.1537 | -0.4813 | 0.3886 | 0.0665 | 0.0208 | 0.0929 | no | 0.2628 | -0.0057 | 4 | 77.5250 | EXPLORATORY |
| bowler | P4 | no | 221 | 0.0008 | 0.7005 | no | 0.2371 | 0.0633 | 0.2197 | -0.2280 | 0.3299 | 0.1220 | 0.0131 | 0.1549 | no | 0.1314 | -0.0742 | 6 | 157.0250 | EXPLORATORY |
| bowler | P5 | no | 131 | 0.0000 | 0.6859 | yes | 0.0000 | 0.0000 | 0.1027 | -0.5546 | 0.3609 | 0.1374 | -0.0071 | 0.1715 | no | 0.1678 | -0.0839 | 6 | 95.0500 | EXPLORATORY |
| bowler | P6 | no | 116 | 0.0006 | 0.7267 | no | 0.1581 | 0.0000 | 0.1729 | -0.3689 | 0.4436 | 0.1310 | 0.0116 | 0.0806 | no | 0.1889 | -0.1071 | 4 | 81.0250 | EXPLORATORY |

`share_B_gt_0_5` is the share of eligible players whose data weight (shrinkage factor B) exceeds 0.5, the Phase 6 gate quantity, reported unchanged and not used for labels. SB is the Spearman-Brown corrected odd/even match split-half correlation of unshrunk precision-weighted means with a 1000-draw match-cluster interval.

## 5. Primary cell

Primary definition: P4 (BEST_AVAILABLE_NOT_PASSING).

| role | intensity | intensity_basis | indicative_list_status | reason |
|---|---|---|---|---|
| batter | P4 | BEST_AVAILABLE_NOT_PASSING | EXPLORATORY | split-half 0.06 below 0.5; split-half lower bound not above 0 |
| bowler | P4 | BEST_AVAILABLE_NOT_PASSING | EXPLORATORY | split-half 0.22 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0 |

REML variance components (units are standardised residual units per ball):

| role | scope | mu | tau2 | sigma2 | lambda | floor | label | mean_B | n_players | n_units |
|---|---|---|---|---|---|---|---|---|---|---|
| batter | COMBINED | 0.00876 | 0.00028 | 1.01974 | 0.00028 | no | BETWEEN_PLAYER_SIGNAL | 0.06906 | 225 | 5520 |
| batter | IPL | 0.00399 | 0.00037 | 0.99831 | 0.00037 | no | BETWEEN_PLAYER_SIGNAL | 0.08852 | 104 | 2393 |
| batter | T20I | -0.00199 | 0.00000 | 1.01452 | 0.00000 | yes | NO_BETWEEN_PLAYER_SIGNAL | 0.00000 | 140 | 2649 |
| bowler | COMBINED | 0.00105 | 0.00081 | 0.70053 | 0.00116 | no | BETWEEN_PLAYER_SIGNAL | 0.23706 | 221 | 5721 |
| bowler | IPL | -0.00657 | 0.00080 | 0.72661 | 0.00110 | no | BETWEEN_PLAYER_SIGNAL | 0.22665 | 102 | 2467 |
| bowler | T20I | 0.00333 | 0.00128 | 0.66944 | 0.00192 | no | BETWEEN_PLAYER_SIGNAL | 0.28177 | 154 | 2950 |

Bootstrap: ranks, Top-10 inclusion and rank intervals use a full REML refit in each of 1000 match-cluster draws. A faster variant that holds the variance components fixed was compared with it (largest gap in Top-10 inclusion over players with probability >= 0.1):

| role | intensity | draws | players_compared | max_abs_gap | fixed_variance_within_0_05 |
|---|---|---|---|---|---|
| batter | P4 | 1000 | 27 | 0.207 | no |
| bowler | P4 | 1000 | 24 | 0.269 | no |

### Batter: Approach A ordering (exploratory, not the submission)

Ranking basis: `REML_POSTERIOR`. The Top 10 inclusion probability is the share of 1000 match-cluster draws in which the player is in the Top 10.

| rank | player_name | estimate | int low | int high | pressure (unshrunk) | normal_baseline | pressure_delta | n_matches | pressure_matches | balls | Top-10 prob | rank_low | rank_high | evidence_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 0.044 | 0.031 | 0.059 | 0.118 | 0.064 | 0.054 | 118 | 72 | 2413 | 0.913 | 1.000 | 17.025 | STRONG_SUBSTANTIAL |
| 2 | Tim David | 0.039 | 0.026 | 0.052 | 0.115 | 0.223 | -0.107 | 77 | 74 | 979 | 0.826 | 1.000 | 33.025 | STRONG_SUBSTANTIAL |
| 3 | Heinrich Klaasen | 0.034 | 0.024 | 0.044 | 0.096 | 0.095 | 0.001 | 55 | 48 | 1018 | 0.599 | 1.975 | 42.000 | STRONG_SUBSTANTIAL |
| 4 | Romario Shepherd | 0.033 | 0.022 | 0.044 | 0.116 | -0.326 | 0.442 | 54 | 53 | 582 | 0.632 | 1.000 | 58.000 | STRONG_SUBSTANTIAL |
| 5 | Andre Russell | 0.032 | 0.020 | 0.045 | 0.096 | n/a | n/a | 57 | 57 | 732 | 0.522 | 1.000 | 80.000 | STRONG_SUBSTANTIAL |
| 6 | Tristan Stubbs | 0.031 | 0.020 | 0.043 | 0.086 | -0.128 | 0.215 | 52 | 46 | 824 | 0.417 | 2.000 | 86.025 | STRONG_SUBSTANTIAL |
| 7 | David Miller | 0.031 | 0.018 | 0.045 | 0.070 | -0.062 | 0.132 | 69 | 65 | 1106 | 0.326 | 2.000 | 110.000 | STRONG_SUBSTANTIAL |
| 8 | Rinku Singh | 0.030 | 0.018 | 0.042 | 0.072 | 0.025 | 0.047 | 67 | 63 | 1003 | 0.314 | 2.000 | 108.025 | INCONSISTENT |
| 9 | Nicholas Pooran | 0.030 | 0.017 | 0.043 | 0.066 | 0.083 | -0.018 | 99 | 70 | 1766 | 0.232 | 2.000 | 123.025 | STRONG_SUBSTANTIAL |
| 10 | Mark Chapman | 0.029 | 0.018 | 0.041 | 0.103 | -0.038 | 0.141 | 47 | 32 | 784 | 0.411 | 1.000 | 114.025 | STRONG_SUBSTANTIAL |
| 11 | Shashank Singh | 0.029 | 0.018 | 0.039 | 0.104 | -0.002 | 0.105 | 32 | 30 | 485 | 0.391 | 1.000 | 116.075 | INCONSISTENT |
| 12 | Dinesh Karthik | 0.028 | 0.016 | 0.039 | 0.077 | 0.199 | -0.122 | 60 | 59 | 636 | 0.279 | 2.000 | 138.000 | INCONSISTENT |
| 13 | Mahendra Singh Dhoni | 0.027 | 0.018 | 0.037 | 0.091 | -0.140 | 0.231 | 47 | 46 | 459 | 0.308 | 2.000 | 113.000 | STRONG_SUBSTANTIAL |
| 14 | Matthew Wade | 0.027 | 0.019 | 0.035 | 0.127 | -0.090 | 0.217 | 29 | 19 | 407 | 0.318 | 2.000 | 100.025 | STRONG_SUBSTANTIAL |
| 15 | Rovman Powell | 0.027 | 0.014 | 0.039 | 0.050 | 0.040 | 0.010 | 82 | 77 | 1259 | 0.120 | 5.000 | 143.050 | INCONSISTENT |

Eligible players: 225. Evidence classes: INCONSISTENT 175, STRONG_SUBSTANTIAL 43, UNCLASSIFIED_LOW 7. Players with Top-10 probability >= 0.5: 5.

### Bowler: Approach A ordering (exploratory, not the submission)

Ranking basis: `REML_POSTERIOR`. The Top 10 inclusion probability is the share of 1000 match-cluster draws in which the player is in the Top 10.

| rank | player_name | estimate | int low | int high | pressure (unshrunk) | normal_baseline | pressure_delta | n_matches | pressure_matches | balls | Top-10 prob | rank_low | rank_high | evidence_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Kuldeep Yadav | 0.066 | 0.037 | 0.098 | 0.121 | 0.024 | 0.097 | 72 | 64 | 1560 | 0.888 | 1.000 | 20.000 | INCONSISTENT |
| 2 | Jasprit Bumrah | 0.063 | 0.033 | 0.095 | 0.142 | 0.054 | 0.088 | 53 | 51 | 1228 | 0.885 | 1.000 | 22.000 | STRONG_SUBSTANTIAL |
| 3 | Varun Chakravarthy | 0.052 | 0.025 | 0.079 | 0.093 | 0.039 | 0.053 | 77 | 69 | 1720 | 0.615 | 1.000 | 42.025 | STRONG_SUBSTANTIAL |
| 4 | Sunil Narine | 0.049 | 0.027 | 0.071 | 0.103 | 0.008 | 0.095 | 54 | 48 | 1224 | 0.657 | 1.000 | 32.000 | STRONG_SUBSTANTIAL |
| 5 | Matheesha Pathirana | 0.049 | 0.024 | 0.075 | 0.089 | -0.015 | 0.104 | 48 | 46 | 1025 | 0.542 | 2.000 | 43.025 | STRONG_SUBSTANTIAL |
| 6 | Abrar Ahmed | 0.039 | 0.016 | 0.062 | 0.121 | -0.022 | 0.143 | 28 | 27 | 626 | 0.570 | 1.000 | 53.050 | STRONG_SUBSTANTIAL |
| 7 | Rashid Khan | 0.036 | 0.007 | 0.064 | 0.055 | 0.066 | -0.010 | 93 | 88 | 2157 | 0.145 | 4.000 | 93.025 | STRONG_SUBSTANTIAL |
| 8 | Mohammad Nawaz | 0.034 | 0.011 | 0.058 | 0.088 | 0.004 | 0.084 | 47 | 40 | 914 | 0.323 | 2.975 | 77.100 | STRONG_SUBSTANTIAL |
| 9 | Akeal Hosein | 0.034 | 0.008 | 0.061 | 0.083 | -0.017 | 0.101 | 61 | 47 | 1346 | 0.304 | 2.000 | 94.000 | STRONG_SUBSTANTIAL |
| 10 | Sufiyan Muqeem | 0.033 | 0.002 | 0.068 | 0.142 | 0.021 | 0.121 | 16 | 13 | 320 | 0.484 | 1.000 | 127.000 | STRONG_LIMITED |
| 11 | Abbas Afridi | 0.033 | 0.011 | 0.055 | 0.139 | 0.022 | 0.117 | 21 | 19 | 393 | 0.457 | 1.000 | 69.000 | STRONG_SUBSTANTIAL |
| 12 | Noor Ahmad | 0.032 | 0.004 | 0.060 | 0.065 | 0.039 | 0.025 | 49 | 46 | 1049 | 0.210 | 3.000 | 115.025 | STRONG_LIMITED |
| 13 | Wanindu Hasaranga | 0.031 | 0.002 | 0.055 | 0.051 | 0.042 | 0.010 | 80 | 70 | 1806 | 0.092 | 6.000 | 113.025 | STRONG_LIMITED |
| 14 | Harshal Patel | 0.029 | 0.001 | 0.060 | 0.047 | -0.017 | 0.064 | 73 | 72 | 1549 | 0.101 | 5.000 | 121.025 | STRONG_LIMITED |
| 15 | Mustafizur Rahman | 0.028 | 0.000 | 0.058 | 0.049 | 0.003 | 0.046 | 67 | 62 | 1504 | 0.101 | 5.975 | 120.025 | INCONSISTENT |

Eligible players: 221. Evidence classes: INCONSISTENT 146, UNCLASSIFIED_LOW 45, STRONG_LIMITED 20, STRONG_SUBSTANTIAL 10. Players with Top-10 probability >= 0.5: 6.

## 6. Sensitivity of the primary ordering

Spearman correlation and Top 10 overlap (out of 10) with the primary COMBINED ordering over common eligible players:

| role | comparison | n_common | spearman | top10_overlap | n_eligible |
|---|---|---|---|---|---|
| batter | intensity_P0 | 160 | 0.818 | 3 | n/a |
| batter | intensity_P3 | 129 | 0.655 | 3 | n/a |
| batter | intensity_P5 | 122 | 0.364 | 4 | n/a |
| batter | intensity_P6 | 120 | 0.729 | 3 | n/a |
| batter | scope_IPL_only | 104 | 0.867 | 6 | n/a |
| batter | scope_T20I_only | 140 | 0.811 | 5 | n/a |
| batter | rank_by_pressure_delta | 167 | 0.522 | 1 | n/a |
| batter | unshrunk_ordering | 225 | 0.935 | 3 | n/a |
| batter | eligibility_floor_x0.5 | 225 | 0.998 | 10 | 331.000 |
| batter | eligibility_floor_x2.0 | 134 | 0.994 | 10 | 134.000 |
| batter | component_runs_only | 225 | 0.645 | 5 | n/a |
| batter | component_wicket_only | 225 | 0.683 | 0 | n/a |
| bowler | intensity_P0 | 164 | 0.816 | 8 | n/a |
| bowler | intensity_P3 | 110 | 0.699 | 7 | n/a |
| bowler | intensity_P5 | 131 | 0.369 | 1 | n/a |
| bowler | intensity_P6 | 116 | 0.683 | 7 | n/a |
| bowler | scope_IPL_only | 102 | 0.828 | 5 | n/a |
| bowler | scope_T20I_only | 154 | 0.881 | 7 | n/a |
| bowler | rank_by_pressure_delta | 221 | 0.621 | 0 | n/a |
| bowler | unshrunk_ordering | 221 | 0.948 | 4 | n/a |
| bowler | eligibility_floor_x0.5 | 221 | 0.999 | 9 | 321.000 |
| bowler | eligibility_floor_x2.0 | 136 | 0.999 | 9 | 136.000 |
| bowler | component_runs_only | 221 | 0.770 | 6 | n/a |
| bowler | component_wicket_only | 221 | 0.630 | 4 | n/a |

## 7. IPL and T20I

| role | players_both_formats | spearman | spearman_low | spearman_high | pearson | combination_supported | combination_basis |
|---|---|---|---|---|---|---|---|
| batter | 85 | 0.100 | -0.136 | 0.290 | 0.087 | no | FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED |
| bowler | 76 | 0.064 | -0.185 | 0.300 | 0.061 | no | FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED |

The combination rule (lower 95% bound at least 0.3 and at least 30 players with both formats) is applied as declared. When it is not met the combined list is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED` and the per-format estimates remain in `p8_a_estimates`.

## 8. Reading these results

- Between-player variance at the floor in the primary COMBINED cells: 0 of 2.
- batter: split-half SB 0.057 (interval -0.220 to 0.361), out-of-time rho 0.199 (lower bound 0.017), indicative status EXPLORATORY.
- bowler: split-half SB 0.220 (interval -0.228 to 0.330), out-of-time rho 0.131 (lower bound -0.074), indicative status EXPLORATORY.
- Thresholds, gates and the shrinkage method were not changed to obtain these results. The Phase 6 data-weight gate is reported, not applied.
- A positive estimate means more runs saved or scored and fewer dismissals than the context-adjusted expectation. It still includes overall quality: `normal_baseline` and `pressure_delta` are reported so the reader can separate them.
- Evidence classes and intervals describe each player's estimate under the fitted random-effects model. They are not a validation: the list-level reliability above decides the status, and no row can be stronger than its list.
- Intensity definitions P3, P4 and P6 describe pressure from the match state shared by both sides; only P5 is defender-oriented, and P5 fails the validity direction tests. P5 appears only as a sensitivity. A bowler-specific definition is not validated.
- The remaining fairness strata of the design (batting-order group, pace or spin, opposition tercile) are deferred to the comparison chunk; this chunk reports IPL vs T20I, exposure by phase and innings, and the exposure (volume) correlation.
- Observed and expected runs and dismissal rates on pressure deliveries are in `p8_a_estimates` (`obs_*`, `exp_*`), with exposure by phase and innings in `p8_a_pressure_exposure`.
- Limitations: expected-outcome models explain little of the outcome variance; pressure intensity is built from the match state alone; residuals of one innings share conditions the model does not see; the bootstrap holds the variance components fixed (checked against 200 full refits).

