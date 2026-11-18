# Submission methodology: pressure performance of IPL and T20I batters and bowlers (Phase 9)

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.32 below 0.5; split-half lower bound not above 0.

Window 2022-01-22 to 2026-11-01. The 2026 matches are included by owner decision D1 (owner attestation, not an official verification) and the TEST lock is released: no pristine hold-out remains. The label of each list is the label the evidence earned under thresholds declared before any result was seen and left unchanged.

## Part 1. The report in plain language

### 1.1 What was asked

Name the ten batters and the ten bowlers who perform best under pressure, in order, and explain how pressure was defined, how players were measured, and how far the conclusions can be trusted. This is a player-performance question.

### 1.2 What was done, in five steps

1. **Describe the situation of every ball.** Only what was known before the ball was bowled is used: score, wickets lost, balls left, target, required rate, phase, innings, batting order.
2. **Give each ball a pressure level between 0 and 1** (resource scarcity: share of wickets lost times share of the innings used). Balls at 0.5 or above form the pressure sample and count in proportion to their level; balls below 0.5 define the player's normal play.
3. **Ask what normally happens in that situation.** A statistical model predicts runs and the chance of a wicket from the situation alone, without knowing who is playing. A player's performance is the gap between what happened and what was expected. Every ball is scored by a model that did not see its own match.
4. **Compare pressure with normal play** so a player who is simply good all the time is not mistaken for a player who rises under pressure.
5. **Be honest about noise.** Small samples are pulled towards the average, every score has an interval from resampling whole matches, and the whole procedure was tested for whether it gives the same answer on two halves of the data.

### 1.3 What was found

- Three approaches were compared under criteria written down and hashed before any result existed (A: observed against expected; B: win probability added; C: Pressure Response Index). Batters are submitted from approach **A**, bowlers from approach **C**.
- Split-half reliability of the submitted batter measure is **0.019 (95% interval -0.184 to 0.359)** and of the bowler measure **0.319 (95% interval -0.107 to 0.386)** (declared thresholds: 0.5 for PROVISIONAL, 0.7 for VALIDATED). Both lists fall short of the PROVISIONAL threshold (0.5) and both intervals include 0.
- Result: batters EXPLORATORY, bowlers EXPLORATORY. The label did not change when the 2026 matches were added: see `phase9_comparison.md` for the change against Phase 8.

### 1.4 How to read the two lists

**Batters** (approach A; higher score is better)

| rank | player | score | interval (95%) | pressure matches | pressure balls | top-10 probability | rank interval | evidence class | status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 0.0345 | 0.0244 to 0.0455 | 79 | 1369 | 88% | 1 to 22 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Tim David | 0.0326 | 0.0226 to 0.0425 | 91 | 1146 | 87% | 1 to 30 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Heinrich Klaasen | 0.0277 | 0.0205 to 0.0360 | 62 | 1181 | 51% | 2 to 51 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | David Miller | 0.0265 | 0.0172 to 0.0370 | 75 | 1210 | 38% | 2 to 96 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Rinku Singh | 0.0265 | 0.0166 to 0.0364 | 79 | 1242 | 38% | 2 to 107 | INCONSISTENT | EXPLORATORY |
| 6 | Andre Russell | 0.0263 | 0.0174 to 0.0359 | 57 | 785 | 51% | 1 to 92 | INCONSISTENT | EXPLORATORY |
| 7 | Romario Shepherd | 0.0261 | 0.0186 to 0.0344 | 64 | 696 | 54% | 1 to 67 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Tristan Stubbs | 0.0256 | 0.0179 to 0.0340 | 58 | 956 | 38% | 2 to 84 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Shreyas Iyer | 0.0248 | 0.0161 to 0.0342 | 61 | 975 | 30% | 2 to 125 | INCONSISTENT | EXPLORATORY |
| 10 | Shivam Dube | 0.0238 | 0.0158 to 0.0325 | 83 | 1343 | 16% | 4 to 116 | INCONSISTENT | EXPLORATORY |

**Bowlers** (approach C; higher score is better)

| rank | player | score | interval (95%) | pressure matches | pressure balls | top-10 probability | rank interval | evidence class | status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Sunil Narine | 3.6470 | 3.4355 to 7.9420 | 61 | 849 | 98% | 1 to 10 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Matheesha Pathirana | 2.9185 | 2.2140 to 7.0689 | 48 | 958 | 86% | 1 to 22 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Kuldeep Yadav | 2.6776 | 1.3149 to 6.5073 | 78 | 1173 | 64% | 1 to 41 | INCONSISTENT | EXPLORATORY |
| 4 | Jasprit Bumrah | 2.6634 | 1.5215 to 6.7617 | 69 | 866 | 70% | 1 to 35 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Varun Chakravarthy | 2.4053 | 0.9899 to 5.8373 | 85 | 1224 | 51% | 2 to 47 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Abrar Ahmed | 1.8407 | 0.6667 to 6.2021 | 34 | 447 | 48% | 1 to 53 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | Rashid Khan | 1.7636 | 0.3329 to 4.3898 | 114 | 1707 | 17% | 5 to 66 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Akeal Hosein | 1.7472 | 0.2056 to 5.6218 | 57 | 568 | 35% | 2 to 66 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Wanindu Hasaranga | 1.6494 | 0.1234 to 4.7273 | 77 | 1152 | 20% | 4 to 70 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 10 | Mohammad Nawaz | 1.6336 | -0.0238 to 5.8135 | 44 | 540 | 36% | 2 to 73 | STRONG_LIMITED | EXPLORATORY |

Top-10 probability is the share of 1,000 resamples of whole matches in which the player is in the Top 10. The rank interval is the 95% range of the player's rank across the same resamples.

## Part 2. Methodology in detail

## 2. Data and provenance

Only the official IPL and T20I data supplied for the competition are used (`updated_ball_by_ball.csv` is authoritative). Source files, `superr.duckdb`, `exploratory.duckdb` and `phase8.duckdb` are read-only and were hash-checked before and after every stage.

| file | role | sha256 |
|---|---|---|
| updated_ball_by_ball.csv | authoritative ball-by-ball deliveries | 01e2b4379edfbab6a6e456d304cb3c70f554cb312ef93d9588f3f32a82cb396e |
| matches.csv | match headers | bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef |
| competitions.csv | competitions | 507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b |
| teams.csv | teams | a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d |
| playing_eleven.csv | playing XI | 7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27 |
| competition_team_player_mapping.csv | player to team mapping | 1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12 |
| ball_by_ball.csv | comparison only (not a scoring source) | a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889 |

Not used: matches 2026.csv; batting_stats2026.csv; bowling_stats2026.csv; fielding_stats2026.csv; any Cricsheet file (never a feature, model or ranking source).

The official database holds 200,999 deliveries and 883 matches. The Phase 9 window is 2022-01-22 to 2026-11-01: matches of TRAIN (to 2024-12-31), VALIDATION (calendar 2025) and the 2026 period (previously TEST). Period boundaries are those of `config/phase4_split_v1.json`.

| period | competition | matches | first match | last match |
|---|---|---|---|---|
| TEST | IPL | 74 | 2026-03-28 | 2026-05-31 |
| TEST | T20I | 70 | 2026-01-07 | 2026-11-01 |
| TRAIN | IPL | 219 | 2022-03-26 | 2024-05-26 |
| TRAIN | OTHER_T20 | 15 | 2024-10-18 | 2024-10-27 |
| TRAIN | T20I | 278 | 2022-01-22 | 2024-12-30 |
| VALIDATION | IPL | 74 | 2025-03-22 | 2025-06-03 |
| VALIDATION | OTHER_T20 | 15 | 2025-11-14 | 2025-11-23 |
| VALIDATION | T20I | 122 | 2025-01-02 | 2025-12-19 |

After the existing data-quality exclusions, 190,584 regulation deliveries carry no exclusion reason; of the 144 2026 matches in scope, 137 contribute scored deliveries (31,996 of 33,086 2026 deliveries). 40 of the 42 late-dated T20I matches (after 2026-05-31) are included; the other 2 carry only restricted rows.

Rows removed before scoring, with reason (whole window):

| reason | competition_type | rows | matches |
|---|---|---|---|
| OUT_OF_SCOPE_COMPETITION | OTHER_T20 | 6985 | 30 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | IPL | 14 | 2 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | T20I | 12 | 2 |
| DLS_NOT_RECONSTRUCTABLE | IPL | 762 | 5 |
| DLS_NOT_RECONSTRUCTABLE | T20I | 2642 | 29 |
| METRIC_WICKET_FLAG_ANOMALY | ALL | 11 | 11 |
| METRIC_EXTRAS_LABEL_UNVERIFIED | ALL | 255 | 206 |

All Phase 8 restrictions apply unchanged: Super Over deliveries (innings 3 and 4), matches whose chase target cannot be reconstructed after a rain-reduced target, wicket-flag and extras-label anomalies (excluded at the metric they affect), and OTHER_T20 (out of scope). Missing values are never treated as zero. The only change is that the exclusion of the 42 late-dated T20I matches no longer applies (D1).

### 2.1 Owner decisions

- **D1.** The owner attests that all 2026 data are genuine, including the 42 late-dated T20I matches; they are used for training and scoring. This is an owner attestation, not a third-party verification (cross-source check: 36 of 42 consistent, 6 single-source, 0 conflicts; original dates unchanged). The TEST lock is released: event `RELEASE`, reason `owner decision phase 9`, in `phase9_lock_release_log.json` (the Phase 4 and Phase 5 lock logs are unchanged). **There is no pristine hold-out any more.**
- **D2.** The word EXPLORATORY and the status banners are removed from the frontend pages (presentation decision). The data files and reports keep the label the evidence earned.

## 3. Pressure definition and why it was chosen

Pressure is observable difficulty of the match situation, not a psychological state. Seven definitions (P0 to P6) were declared before any player was ranked and tested on balls: (a) runs per ball lower at high intensity; (b) wicket chance higher; (c) outcomes vary more; (d) win probability swings more (mechanical for the win-probability definitions); (e) monotonic across ten bands (Spearman at least 0.7). The procedure is rerun unchanged on the Phase 9 window:

| candidate | pass | test_a | test_b | test_c | test_e | test_d | n_tests_passed | phases_passing | innings_coverage | primary_basis |
|---|---|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | no | 3 | 2 | 1 |  |
| P1 | no | no | no | no | no | yes | 0 | 0 | 0 |  |
| P2 | no | no | no | no | no | yes | 0 | 0 | 0 |  |
| P3 | no | yes | yes | yes | no | yes | 3 | 1 | 1 |  |
| P4 | no | yes | yes | yes | no | no | 3 | 2 | 2 | BEST_AVAILABLE_NOT_PASSING |
| P5 | no | no | no | yes | no | no | 1 | 0 | 0 |  |
| P6 | no | no | yes | yes | no | no | 2 | 1 | 0 |  |

No candidate passes the declared rule (the monotonic trend test (e) fails for all). The declared ordering picks P4 (resource scarcity, both innings): 3 tests passed, coverage of 2 innings. Pressure balls at P4 have fewer runs per ball and a higher wicket probability than low-pressure balls (pooled TRAIN difference -0.192 runs and 0.057 wicket probability). The definition is the best available, not validated. The mechanical selection did not pick a definition other than P4.

## 4. Batter and bowler metrics

Batters and bowlers are analysed separately and never compared with each other. Approach A: for every pressure ball, runs scored minus runs expected and expected minus actual dismissal, each divided by its TRAIN standard deviation and averaged with equal weight. Approach C: a Pressure Response Index combining A, B (win probability added above what leverage predicts) and CONS (share of pressure appearances that beat the expectation) with weights from split-half reliability on a fitting half of the matches:

| role | component | n_players_fit | split_half_sb | tau2_fit | floor_fit | status | final_weight |
|---|---|---|---|---|---|---|---|
| batter | A | 144 | 0.099 | 0.000 | yes | NO_SIGNAL_FLOOR | 0.000 |
| batter | B | 140 | 0.114 | 0.000 | no | ACTIVE | 0.445 |
| batter | CONS | 144 | 0.139 | 0.004 | no | ACTIVE | 0.555 |
| bowler | A | 148 | 0.074 | 0.000 | no | ACTIVE | 0.500 |
| bowler | B | 145 | -0.085 | 0.000 | no | NO_SIGNAL_NONPOSITIVE_RELIABILITY | 0.000 |
| bowler | CONS | 148 | 0.251 | 0.005 | no | ACTIVE | 0.500 |

Components with weight 0 (no between-player signal on the fitting matches): batter A, bowler B. The index is the weighted combination of the remaining components.

The unit of analysis is one player in one innings (a batting innings or a bowling spell). Matches, not balls, are the resampling unit.

## 5. Normal-performance baselines

The normal baseline of a player is the unweighted mean residual on balls below intensity 0.5; the pressure level is the intensity-weighted mean residual on balls at or above 0.5; `pressure_delta` is the second minus the first. All three are CSV columns and appear in every player's explanation. The expectation comes from a player-blind model.

## 6. Context adjustment and training scheme

Expected runs and wicket probability come from gradient-boosting models using pre-delivery information only (innings, phase, wickets and balls remaining, score, target, required rate, current run rate, batting order, stage, competition). No player identifier or outcome column is a feature.

**Phase 9 scheme.** The 8 expected-outcome models and the win-probability models W1 and W2 (and the next-ball class model) are refitted on matches up to 2025-12-31 (TRAIN and VALIDATION of Phase 4) with the same learners and hyperparameters Phase 8 chose (read from the Phase 8 artefacts; nothing was tuned). Deliveries up to 2025-12-31 are scored out of fold (`match_id % 5`, models fitted on the other four folds). The 2026 deliveries are scored by the fit on all matches to 2025-12-31. So no delivery is scored by a model that saw its match. Earlier balls can be scored by models trained on later matches (as in Phase 8). Artefacts: `backend/data/models/p9_*.joblib` with `.json` metadata; the Phase 8 artefacts are untouched. Retraining with the same seed and parameters reproduced every artefact's predictions exactly (maximum absolute difference 0.0 over 10 models).

### 6.1 2026 out-of-time check; data previously held out, released by owner decision

The models were fitted on matches to 2025-12-31 and evaluated on the 2026 matches. This is the first use of 2026 outcomes for evaluation in this pipeline. Nothing was tuned on it. Gain is against a constant prediction (RMSE or log loss; Brier for win probability).

| model | metric | model_value_2026 | constant_value_2026 | gain_vs_constant_pct | n_2026 | slope |
|---|---|---|---|---|---|---|
| batter_runs | rmse | 1.794 | 1.825 | 1.706 | 30610 | n/a |
| batter_wicket | log_loss | 0.207 | 0.210 | 1.677 | 30660 | 0.940 |
| batter_dot | log_loss | 0.629 | 0.650 | 3.220 | 30610 | 0.984 |
| batter_boundary | log_loss | 0.500 | 0.516 | 3.118 | 30610 | 0.907 |
| bowler_runs | rmse | 1.767 | 1.794 | 1.552 | 31946 | n/a |
| bowler_wicket | log_loss | 0.204 | 0.207 | 1.477 | 30527 | 0.938 |
| bowler_dot | log_loss | 0.629 | 0.650 | 3.219 | 30527 | 0.985 |
| bowler_boundary | log_loss | 0.499 | 0.516 | 3.143 | 30527 | 0.906 |
| W1 | brier | 0.239 | 0.252 | 5.130 | 16541 | 0.621 |
| W2 | brier | 0.123 | 0.254 | 51.533 | 14853 | 1.076 |

| role | target | chosen | gain_vs_const_pct | n_train | n_2026 |
|---|---|---|---|---|---|
| batter | boundary | gbm | 3.118 | 152386 | 30610 |
| batter | dot | gbm | 3.220 | 152386 | 30610 |
| batter | runs | gbm | 1.706 | 152386 | 30610 |
| batter | wicket | gbm | 1.677 | 152579 | 30660 |
| bowler | boundary | gbm | 3.143 | 151918 | 30527 |
| bowler | dot | gbm | 3.219 | 151918 | 30527 |
| bowler | runs | gbm | 1.552 | 158383 | 31946 |
| bowler | wicket | gbm | 1.477 | 151907 | 30527 |

| model | n_2026 | brier | brier_const | brier_logit | slope | intercept | gate_passed |
|---|---|---|---|---|---|---|---|
| W1 | 16541 | 0.239 | 0.252 | 0.242 | 0.621 | -0.392 | no |
| W2 | 14853 | 0.123 | 0.254 | 0.135 | 1.076 | 0.675 | yes |

The first-innings model W1 misses the declared calibration gate on 2026 (slope 0.62, required 0.8 to 1.2). Under the unchanged Approach B rule, first-innings win-probability credit is therefore withheld (`INNINGS1_WP_NOT_RELIABLE`); this affects approach B and the win-probability component (B) of approach C, not approach A.

## 7. IPL and T20I comparison

Competition is a model feature and scores are centred by format before combination. The declared rule allows one combined score only when the cross-format correlation has a lower 95% bound of at least 0.3 across at least 30 players with both formats:

| approach | role | players_both_formats | spearman | spearman_low | spearman_high | combination_supported |
|---|---|---|---|---|---|---|
| A | batter | 96 | 0.056 | -0.145 | 0.227 | no |
| A | bowler | 89 | 0.137 | -0.069 | 0.341 | no |
| B | batter | 56 | -0.057 | -0.328 | 0.191 | no |
| B | bowler | 60 | -0.243 | -0.486 | 0.034 | no |
| C | batter | 56 | 0.069 | -0.159 | 0.327 | no |
| C | bowler | 89 | 0.186 | -0.005 | 0.389 | no |

The rule is not met in 6 of 6 approach and role cells; those combined estimates are flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED` (each unit weighted by its own precision, no fixed split). IPL and T20I matches, contributions, scores and ranks are shown separately for every listed player.

## 8. Eligibility and sample size

Declared floors (criteria file, unchanged): at least 8 matches, at least 60 balls faced or 72 balls bowled, at least 8 high-intensity units, an effective sample of at least 60, and at least 4 matches in the recent window (the criteria name it `min_matches_2025_window`; in Phase 9 it is applied to the most recent window, 2025 and 2026, and is used for the late half of the out-of-time test and the window sensitivity). Eligible players: 256 batters (approach A) and 156 bowlers (approach C). A player below a floor is `INSUFFICIENT_EVIDENCE`, which says nothing about quality. No list is padded.

## 9. Shrinkage and uncertainty

Player estimates are shrunk towards the cohort mean by a random-effects model fitted by REML on match-level units. Between-player variance (tau squared) for approach A at P4, by scope:

| role | scope | n_players | tau2 | sigma2 | floor | label |
|---|---|---|---|---|---|---|
| batter | COMBINED | 256 | 0.000 | 1.021 | no | BETWEEN_PLAYER_SIGNAL |
| batter | IPL | 119 | 0.000 | 0.995 | no | BETWEEN_PLAYER_SIGNAL |
| batter | T20I | 170 | 0.000 | 1.025 | yes | NO_BETWEEN_PLAYER_SIGNAL |
| bowler | COMBINED | 243 | 0.001 | 0.701 | no | BETWEEN_PLAYER_SIGNAL |
| bowler | IPL | 122 | 0.001 | 0.713 | no | BETWEEN_PLAYER_SIGNAL |
| bowler | T20I | 171 | 0.001 | 0.685 | no | BETWEEN_PLAYER_SIGNAL |

Where a scope sits at the floor (tau squared 0), the predeclared rule orders players by the unshrunk precision-weighted mean and forces the label EXPLORATORY. Intervals are 95% percentile intervals from a 1,000-draw bootstrap that resamples whole matches (seed 20260512), re-estimating the between-player variance in every draw. Each row also reports Top-10 inclusion probability, a 95% rank interval and a sample-reliability figure. Evidence classes (declared in advance): STRONG_SUBSTANTIAL, STRONG_LIMITED, INCONSISTENT, INSUFFICIENT.

## 10. Reliability validation

Two matched halves of each player's matches are scored independently (odd and even matches by date, and early against late), the correlation is corrected to full length (Spearman-Brown) and its interval comes from a match-cluster bootstrap. The out-of-time test correlates 2022-2024 estimates with 2025-2026 estimates (TRAIN against VALIDATION of the Phase 9 window labelling).

**Batters**

| approach | split-half (Spearman-Brown) | 95% interval | out-of-time r | out-of-time lower bound | ICC(1) | variance at floor | mean data weight | eligible players | submitted |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.019 | -0.184 to 0.359 | 0.121 | -0.054 | 0.0079 | no | 0.052 | 256 | yes |
| B | -0.013 | -0.389 to 0.294 | -0.068 | -0.342 | -0.0002 | yes | 0.000 | 148 | no |
| C | -0.229 | -0.367 to 0.307 | -0.051 | -0.321 | n/a | no | 0.159 | 148 | no |

**Bowlers**

| approach | split-half (Spearman-Brown) | 95% interval | out-of-time r | out-of-time lower bound | ICC(1) | variance at floor | mean data weight | eligible players | submitted |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.120 | -0.243 to 0.297 | 0.205 | 0.034 | 0.0113 | no | 0.222 | 243 | no |
| B | -0.104 | -0.494 to 0.341 | -0.099 | -0.346 | 0.0016 | no | 0.007 | 156 | no |
| C | 0.319 | -0.107 to 0.386 | 0.218 | 0.059 | n/a | no | 0.333 | 156 | yes |

Approach C's figures use held-out matches only (its weights were fitted on the other half), so its columns are not like for like with A and B; the selection rule was applied as declared. The Phase 6 data-weight gate (mean data weight of at least 0.5) is reported unchanged and is not a label input.

Phase 6 findings stay in force: between-player variance at the shrinkage floor in all 48 contexts; pooled odd/even reliability 0.37 (0.3656), median 0.25 over the 47 estimable contexts; 0 of 48 contexts pass the 0.5 data-weight gate; no pressure definition passed the predeclared criteria.

## 11. Sensitivity analysis

Each row compares the submitted order with a variant: Spearman correlation over the players both versions rank, and how many of the ten submitted players remain in the variant's Top 10.

| role | family | comparison | n_common | spearman | top10_overlap |
|---|---|---|---|---|---|
| batter | pressure definition | intensity_P0 | 193 | 0.787 | 0 |
| batter | pressure definition | intensity_P3 | 144 | 0.611 | 2 |
| batter | pressure definition | intensity_P5 | 140 | 0.416 | 4 |
| batter | pressure definition | intensity_P6 | 142 | 0.711 | 2 |
| batter | format (IPL, T20I, combined) | scope_IPL_only | 119 | 0.796 | 7 |
| batter | format (IPL, T20I, combined) | scope_T20I_only | 170 | 0.820 | 3 |
| batter | assumption (ordering, weights, innings) | rank_by_pressure_delta | 184 | 0.535 | 1 |
| batter | assumption (ordering, weights, innings) | unshrunk_ordering | 256 | 0.925 | 2 |
| batter | eligibility floor | eligibility_floor_x0.5 | 256 | 0.997 | 10 |
| batter | eligibility floor | eligibility_floor_x2.0 | 152 | 0.995 | 9 |
| batter | component or approach | component_runs_only | 256 | 0.640 | 4 |
| batter | component or approach | component_wicket_only | 256 | 0.668 | 0 |
| batter | bootstrap | bootstrap_method_check | 31 | n/a | n/a |
| batter | calendar window | window_2022_2024 | 188 | 0.787 | 3 |
| batter | calendar window | window_2025 | 189 | 0.669 | 1 |
| bowler | component or approach | published_approach_A_rank | 156 | 0.945 | 8 |
| bowler | component or approach | published_approach_B_rank | 156 | 0.315 | 3 |
| bowler | component or approach | component_A_only | 156 | 0.944 | 8 |
| bowler | component or approach | component_B_only | 156 | 0.315 | 3 |
| bowler | component or approach | component_CONS_only | 156 | 0.954 | 9 |
| bowler | assumption (ordering, weights, innings) | equal_weights_not_data_derived | 156 | 0.906 | 9 |
| bowler | format (IPL, T20I, combined) | scope_IPL_only | 84 | 0.868 | 5 |
| bowler | format (IPL, T20I, combined) | scope_T20I_only | 87 | 0.903 | 7 |
| bowler | eligibility floor | eligibility_floor_x0.5 | 156 | 0.999 | 9 |
| bowler | eligibility floor | eligibility_floor_x2.0 | 78 | 0.998 | 10 |
| bowler | assumption (ordering, weights, innings) | unshrunk_ordering | 156 | 0.976 | 4 |
| bowler | format (IPL, T20I, combined) | hierarchical_format_common_effect | 156 | 0.999 | 10 |
| bowler | assumption (ordering, weights, innings) | innings2_units_only | 156 | 0.646 | 7 |
| bowler | bootstrap | bootstrap_method_check | 156 | n/a | n/a |
| bowler | calendar window | window_2022_2024 | 133 | 0.774 | 5 |
| bowler | calendar window | window_2025 | 140 | 0.681 | 1 |
| bowler | pressure definition | intensity_P0 | 147 | 0.684 | 7 |
| bowler | pressure definition | intensity_P3 | 126 | 0.578 | 6 |
| bowler | pressure definition | intensity_P5 | 141 | 0.425 | 3 |
| bowler | pressure definition | intensity_P6 | 136 | 0.635 | 7 |

## 12. Final ranking evidence

- Batters: rule path `NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE`, chosen approach A. Chosen approach A by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects A and the point-estimate path selects A: the two paths agree.
- Bowlers: rule path `NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE`, chosen approach C. Chosen approach C by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects C and the point-estimate path selects C: the two paths agree.

Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`, was verified against the run log before every step. Player-level evidence for the listed players and for near-miss and high-raw-statistic players is in `player_selection_explanations.md` (batter NEAR_MISS: 25, batter RAW_STANDOUT: 38, batter SELECTED: 10, bowler NEAR_MISS: 24, bowler RAW_STANDOUT: 29, bowler SELECTED: 10 entries).

## 13. Limitations

- Label earned: batters EXPLORATORY, bowlers EXPLORATORY. The orders are not shown to separate players beyond noise unless the status table says otherwise.
- The pressure definition used (P4) did not pass the declared validity rule.
- No pristine hold-out remains. The 2026 check of the models used data held out earlier and nothing was tuned on it, but it is not an independent test.
- The 2026 data, including the 42 late-dated T20I matches, rest on the owner's attestation; no official third-party verification exists. Cross-source consistency: 36 of 42 consistent, 6 single-source, 0 conflicts.
- The twenty listed players have 34 to 114 pressure appearances each over 2022 to 2026.
- Ball outcomes are mostly chance given the situation: expected-outcome models improve on a constant by about 1.5% to 3.2% on the 2026 matches.
- Earlier balls can be scored by models trained on later matches (out-of-fold design).
- The experimental AI predictions are a separate diagnostic and are not part of the submitted ranking.

## 14. Glossary of status labels

- **VALIDATED**: split-half reliability at least 0.70 with an interval lower bound at least 0.50 and an out-of-time lower bound above 0.30, declared before any result.
- **PROVISIONAL**: split-half reliability at least 0.50 with an interval lower bound above 0 and an out-of-time lower bound above 0.
- **EXPLORATORY**: an ordered list exists but the PROVISIONAL thresholds were not met.
- **INSUFFICIENT_EVIDENCE**: fewer than ten eligible players, or the approach cannot be computed.

Labels earned in Phase 9: batters EXPLORATORY; bowlers EXPLORATORY. A row never carries a stronger label than its list.

## Appendix A. Technical details

**Splits.** `config/phase4_split_v1.json`: TRAIN to 2024-12-31, VALIDATION calendar 2025, TEST 2026 onward (released by owner decision). Model-fit group: matches to 2025-12-31; scoring group for 2026. Folds `match_id % 5`.

**Models.** Gradient boosting (regressor for runs, classifier for wicket, dot, boundary), grid of learning rate, depth and L2 as in Phase 8, 200 iterations, minimum leaf 200; the Phase 8 choice per target is applied unchanged. Win probability: histogram gradient boosting with logistic baseline. Seed 20260512.

**REML, attribution, reliability estimators** are as in Phase 8 (REML posterior per scope; striker, bowler, wicket, extras and run-out rules; split-half with Spearman-Brown, Fisher-z pooling, ICC(1), 1,000-draw match-cluster bootstrap).

**Reproduction.** From `d:/Data/backend` with `PYTHONUTF8=1` and `PYTHONPATH=d:/Data/backend`: `python scripts/run_phase9_pipeline.py` regenerates the p9 tables and lists; `python scripts/phase9_models_check.py`, `python scripts/phase9_ai_verify.py`, `python scripts/run_phase9_docs.py docs` regenerate the checks and this document.

**Versions.** Methodology `phase9_methodology_v1`; criteria `phase8_selection_criteria_v1` (SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`); generated 2026-11-18T08:36:49+00:00.
