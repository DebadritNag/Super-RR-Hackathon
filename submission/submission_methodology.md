# Submission methodology: pressure performance of IPL and T20I batters and bowlers

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

Both lists are the best-supported ordering available. Neither is a validated ranking. The label of each list is the label the evidence earned under thresholds declared before any result was seen.

## Part 1. The report in plain language

### 1.1 What was asked

Name the ten batters and the ten bowlers who perform best under pressure, in order, and explain how pressure was defined, how players were measured, and how far the conclusions can be trusted. This is a player-performance question. It is not a squad-building exercise.

### 1.2 What was done, in five steps

1. **Describe the situation of every ball.** For each delivery, only what was known before the ball was bowled is used: score, wickets lost, balls left, target, required rate, phase, innings, batting order.
2. **Give each ball a pressure level between 0 and 1.** The level used is *resource scarcity*: the share of wickets already lost multiplied by the share of the innings already used. A ball late in an innings with many wickets down is high pressure. Balls at level 0.5 or above form the pressure sample and each counts in proportion to its level, so a very high-pressure ball counts more than a borderline one; balls below 0.5 define the player's normal play.
3. **Ask what normally happens in that situation.** A statistical model trained on earlier matches (to the end of 2024) predicts the runs and the chance of a wicket for each ball from the situation alone, without knowing who is playing. A player's performance is the gap between what happened and what the model expected.
4. **Compare pressure with normal play.** Each player's pressure gap is set beside the same gap on low-pressure balls, so a player who is simply good all the time is not mistaken for a player who rises under pressure.
5. **Be honest about noise.** Small samples are pulled towards the average, every score has an interval from resampling whole matches, and the whole procedure was tested for whether it gives the same answer on two halves of the same data.

### 1.3 What was found

- Three different approaches were built and compared under criteria written down and hashed before any result existed (A: observed against expected; B: win probability added; C: a Pressure Response Index). Batters are submitted from approach **A**, bowlers from approach **C**.
- The split-half reliability of the submitted batter measure is **0.057** and of the bowler measure **0.267** (1.0 would mean two halves of the data give the same order; the declared thresholds were 0.5 for PROVISIONAL and 0.7 for VALIDATED). Both fall short, and both intervals include 0.
- So the data do not show that these players are reliably better under pressure than players just below them. The earlier Phase 6 finding stands: match-level data are too thin to separate players on pressure performance with confidence.
- The lists are still useful as a transparent, reproducible description of who beat the model's expectation most in difficult situations from 2022 to 2025, with each player's evidence shown.

### 1.4 How to read the two lists

**Batters** (approach A: context-adjusted performance; higher score is better)

| rank | player | score | interval (95%) | pressure matches | pressure balls | IPL / T20I matches | top-10 probability | rank interval | evidence class | status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 0.0440 | 0.0306 to 0.0590 | 72 | 1247 | 51 / 67 | 91% | 1 to 17 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Tim David | 0.0386 | 0.0255 to 0.0517 | 74 | 961 | 42 / 35 | 83% | 1 to 33 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Heinrich Klaasen | 0.0336 | 0.0243 to 0.0436 | 48 | 870 | 39 / 16 | 60% | 2 to 42 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | Romario Shepherd | 0.0328 | 0.0220 to 0.0438 | 53 | 613 | 12 / 42 | 63% | 1 to 58 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Andre Russell | 0.0323 | 0.0202 to 0.0450 | 57 | 785 | 45 / 12 | 52% | 1 to 80 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Tristan Stubbs | 0.0307 | 0.0199 to 0.0426 | 46 | 763 | 30 / 22 | 42% | 2 to 86 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | David Miller | 0.0305 | 0.0178 to 0.0446 | 65 | 1068 | 48 / 21 | 33% | 2 to 110 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Rinku Singh | 0.0301 | 0.0180 to 0.0422 | 63 | 966 | 43 / 24 | 31% | 2 to 108 | INCONSISTENT | EXPLORATORY |
| 9 | Nicholas Pooran | 0.0299 | 0.0166 to 0.0432 | 70 | 1130 | 56 / 43 | 23% | 2 to 123 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 10 | Mark Chapman | 0.0292 | 0.0182 to 0.0408 | 32 | 503 | 0 / 47 | 41% | 1 to 114 | STRONG_SUBSTANTIAL | EXPLORATORY |

**Bowlers** (approach C: Pressure Response Index; higher score is better)

| rank | player | score | interval (95%) | pressure matches | pressure balls | IPL / T20I matches | top-10 probability | rank interval | evidence class | status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Matheesha Pathirana | 3.6132 | 3.0641 to 9.2850 | 46 | 930 | 32 / 16 | 86% | 1 to 26 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Kuldeep Yadav | 3.0271 | 1.8085 to 7.5369 | 64 | 973 | 53 / 19 | 56% | 1 to 51 | INCONSISTENT | EXPLORATORY |
| 3 | Jasprit Bumrah | 2.8289 | 1.5024 to 7.6972 | 51 | 636 | 38 / 15 | 56% | 1 to 56 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | Varun Chakravarthy | 2.8151 | 1.3280 to 7.1786 | 69 | 999 | 52 / 25 | 45% | 1 to 64 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Sunil Narine | 2.7856 | 1.4815 to 7.8043 | 48 | 713 | 54 / 0 | 57% | 1 to 58 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Akeal Hosein | 2.7590 | 1.4790 to 7.5519 | 47 | 486 | 1 / 60 | 54% | 1 to 56 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | Rashid Khan | 2.4892 | 0.9857 to 6.2976 | 88 | 1340 | 59 / 34 | 27% | 2 to 75 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Mohammad Nawaz | 2.4317 | 1.0627 to 7.5332 | 40 | 467 | 0 / 47 | 49% | 1 to 69 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Wanindu Hasaranga | 1.9309 | -0.0333 to 5.8102 | 70 | 1069 | 35 / 45 | 14% | 3 to 107 | STRONG_LIMITED | EXPLORATORY |
| 10 | Abbas Afridi | 1.8937 | 0.7330 to 7.6883 | 19 | 223 | 0 / 21 | 44% | 1 to 81 | STRONG_SUBSTANTIAL | EXPLORATORY |

Top-10 probability is the share of 1,000 resamples of whole matches in which the player is in the Top 10. The rank interval is the 95% range of the player's rank across the same resamples. A player with a probability near 50% and a rank interval spanning twenty places has an order that should not be taken literally.

### 1.5 What the status labels mean

See the glossary in section 14. In short: every row and both lists are EXPLORATORY.

## Part 2. Methodology in detail

## 2. Data and provenance

Only the official IPL and T20I data supplied for the competition are used. `updated_ball_by_ball.csv` is authoritative; `ball_by_ball.csv` is used for comparison only. Source files are read-only and were hashed before and after the Phase 8 run: every recorded hash was compared at the end of the run (results in the test report; one documented intentional change to a Phase 7 registry file, none to a source file or database).

| file | role | bytes | sha256 |
|---|---|---|---|
| updated_ball_by_ball.csv | authoritative ball-by-ball deliveries | 41071837 | 01e2b4379edfbab6a6e456d304cb3c70f554cb312ef93d9588f3f32a82cb396e |
| matches.csv | match headers | 123864 | bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef |
| competitions.csv | competitions | 7624 | 507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b |
| teams.csv | teams | 6922 | a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d |
| playing_eleven.csv | playing XI | 966287 | 7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27 |
| competition_team_player_mapping.csv | player to team mapping | 462969 | 1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12 |
| ball_by_ball.csv | comparison only (not a scoring source) | 41071609 | a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889 |

Not used: matches 2026.csv; batting_stats2026.csv; bowling_stats2026.csv; fielding_stats2026.csv; any Cricsheet file (never a feature, model or ranking source).

| file | role | sha256 |
|---|---|---|
| superr.duckdb | official database built from the source files (read-only) | cb4077eebbd811534f9b1ee434bd92a385849e5b99a0955d48fb2dc5164a391d |
| exploratory.duckdb | pre-delivery state and Phase 3 to 6 tables (read-only in Phase 8) | 7b396e42a2acb281fd5ffd64051064d7ac48e82bdfad23dd229bd20b9ca6277d |
| phase8.duckdb | Phase 8 tables, prefix p8_ (written by Phase 8 only) | c77ad8df883131a196bd5faae26003abd9a3a055f375bc797aca61a1117d407d |

| file | sha256 |
|---|---|
| config/phase8_selection_criteria_v1.json | 9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64 |
| config/phase4_split_v1.json | da12fcd3969361d33b1893186f72af6e021cf9c93d131e5211ae6864ce7e4894 |
| config/data_quality_restrictions_v1.json | 5f243fa7e460b3e17596bd3903664ea10a567a6c72ada28adfa20d8650653b3b |

Counts: the official database holds 200,999 deliveries, 883 matches and 1,217 players. Phase 8 scores the pre-test window only (TRAIN to 2024-12-31 and VALIDATION, calendar 2025). The 2026 matches (TEST) were never loaded.

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

After exclusions, 157,839 regulation deliveries in the IPL and T20I carry no exclusion reason and are available for scoring (the stored delivery table has 158,588 rows including those with a stated exclusion reason).

| period | competition | deliveries used | matches |
|---|---|---|---|
| TRAIN | IPL | 52364 | 219 |
| TRAIN | T20I | 62163 | 268 |
| VALIDATION | IPL | 16965 | 73 |
| VALIDATION | T20I | 26347 | 115 |

Rows removed before scoring, with the reason (source-data exclusions):

| reason | competition_type | rows | matches |
|---|---|---|---|
| OUT_OF_SCOPE_COMPETITION | OTHER_T20 | 6985 | 30 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | IPL | 10 | 1 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | T20I | 12 | 2 |
| DLS_NOT_RECONSTRUCTABLE | IPL | 377 | 3 |
| DLS_NOT_RECONSTRUCTABLE | T20I | 1941 | 23 |
| METRIC_WICKET_FLAG_ANOMALY | ALL | 11 | 11 |
| METRIC_EXTRAS_LABEL_UNVERIFIED | ALL | 205 | 166 |

Deliveries dropped at the scoring stage because a needed quantity was undefined (never filled with zero):

| reason | deliveries | matches |
|---|---|---|
| EXTRAS_OTHER_OR_PENALTY | 205 | 166 |
| METRIC_FLAG_ANOMALY | 11 | 11 |
| UNUSUAL_EVENT | 7 | 7 |
| WP_UNAVAILABLE | 526 | 35 |

Super Over deliveries (innings 3 and 4 of the six restricted matches), deliveries in matches whose chase target cannot be reconstructed after a rain-reduced target, and the wicket-flag and extras-label anomalies listed in the restriction register are excluded at the metric they affect. Missing values are never treated as zero. The 42 T20I matches with late-dated records stay out of the primary evaluation.

## 3. Pressure definition and why it was chosen

Pressure is defined here as observable difficulty of the match situation, not as a psychological state. Seven definitions were declared before any player was ranked (P0 to P6) and tested on balls, not on players:

- a: runs per ball are lower at high intensity than at low intensity;
- b: the chance of a wicket is higher at high intensity;
- c: outcomes vary more at high intensity;
- d: the win probability swings more (mechanical for the win-probability definitions);
- e: the relation is monotonic across the ten intensity bands (Spearman at least 0.7).

| candidate | pass | test_a | test_b | test_c | test_e | test_d | n_tests_passed | phases_passing | innings_coverage | primary_basis |
|---|---|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | no | 3 | 2 | 1 |  |
| P1 | no | no | no | no | no | yes | 0 | 0 | 0 |  |
| P2 | no | no | no | no | no | yes | 0 | 0 | 0 |  |
| P3 | no | yes | yes | yes | no | yes | 3 | 1 | 1 |  |
| P4 | no | yes | yes | yes | no | no | 3 | 2 | 2 | BEST_AVAILABLE_NOT_PASSING |
| P5 | no | no | no | yes | no | yes | 1 | 0 | 0 |  |
| P6 | no | no | yes | yes | no | no | 2 | 1 | 0 |  |

No candidate passes the declared rule, because the monotonic trend test (e) fails for all. P4 (resource scarcity, both innings) was used because the declared ordering picks the candidate that passes the most tests with the widest innings coverage (3 tests passed, coverage of 2 innings). Pressure balls at P4 have 0.192 fewer runs per ball and a 0.057 higher wicket probability (pooled difference, TRAIN) than low-pressure balls. The definition is therefore the best available, not validated, and this alone caps both lists at EXPLORATORY. Win-probability based definitions (P1, P2) were built but failed the direction tests; they are reported in the comparison.

Why these indicators are meaningful: wickets in hand and balls remaining are the two resources a batting side spends, and scarcity of both is what commentators describe as pressure; both are known before each ball, so there is no look-ahead. Close-match and last-overs definitions were not assumed. The first principal component of P3 and P4 (P6) and the Phase 6 style slice (P0) were kept as sensitivity checks.

## 4. Batter and bowler metrics

Batters and bowlers are analysed separately and never compared with each other.

- **Batter, approach A.** For every pressure ball, runs scored minus runs expected, and expected minus actual dismissal (so not being dismissed counts as better), each divided by its TRAIN standard deviation and averaged with equal weight. Dot-ball and boundary components are reported but not scored.
- **Bowler, approach C.** The Pressure Response Index combines three components: A (the same expected-outcome residual from the bowler's side), B (win probability added above what the leverage predicts) and CONS (the share of pressure appearances in which the bowler beat the expectation). Component weights come from split-half reliability on a fitting half of the matches; the table below shows the weights that resulted.

| role | component | n_players_fit | split_half_sb | tau2_fit | floor_fit | status | final_weight |
|---|---|---|---|---|---|---|---|
| batter | A | 214 | 0.069 | 0.000 | yes | NO_SIGNAL_FLOOR | 0.000 |
| batter | B | 214 | -0.226 | 0.000 | yes | NO_SIGNAL_FLOOR | 0.000 |
| batter | CONS | 214 | 0.187 | 0.003 | no | ACTIVE | 1.000 |
| bowler | A | 212 | -0.233 | 0.000 | no | NO_SIGNAL_NONPOSITIVE_RELIABILITY | 0.000 |
| bowler | B | 212 | -0.100 | 0.000 | yes | NO_SIGNAL_FLOOR | 0.000 |
| bowler | CONS | 212 | 0.175 | 0.004 | no | ACTIVE | 1.000 |

Every weight rule gave components A and B zero weight for both roles, because they showed no between-player signal on the fitting matches. The index therefore reduces to the consistency component. It is a share of appearances, not an A plus B composite, and the bowler list should be read with that in mind.

The unit of analysis is one player in one innings (a batting innings or a bowling spell). Matches, not balls, are the resampling unit, because balls in the same match are not independent.

## 5. Normal-performance baselines

The *normal baseline* of a player is the unweighted mean residual on balls below intensity 0.5 (low-pressure balls), in the same units as the pressure score. The *pressure level* is the intensity-weighted mean residual on balls at or above 0.5. The pressure-versus-baseline difference (`pressure_delta`) is the second minus the first. Both are in the CSV columns `normal_baseline`, `pressure_performance_unshrunk` and `pressure_delta`, and in every player's explanation. The expected value for each ball comes from a player-blind model, so the baseline reflects the player's performance relative to the typical player in the same situation, not a raw average.

## 6. Context adjustment

Expected runs and wicket probability are predicted by gradient-boosting models fitted on TRAIN only from pre-delivery information: innings, phase, wickets remaining, balls remaining, score, target and required rate in a chase, current run rate, batting order, stage and competition type. No player identifier and no outcome column is a feature; a leakage test mutates future rows and shows the expectation of earlier balls does not change. TRAIN balls are predicted out of fold (fold = match_id modulo 5) so no ball is scored by a model that saw its own match.

Out-of-sample quality on VALIDATION (calendar 2025):

| role | target | chosen | gain_vs_const_pct | n_train | n_validation |
|---|---|---|---|---|---|
| batter | boundary | gbm | 3.084 | 110695 | 41691 |
| batter | dot | gbm | 2.945 | 110695 | 41691 |
| batter | runs | gbm | 1.626 | 110695 | 41691 |
| batter | wicket | gbm | 1.743 | 110842 | 41738 |
| bowler | boundary | gbm | 3.118 | 110353 | 41565 |
| bowler | dot | gbm | 2.964 | 110353 | 41565 |
| bowler | runs | gbm | 1.508 | 115056 | 43327 |
| bowler | wicket | gbm | 1.514 | 110344 | 41563 |

The gain over a constant prediction is 1.5% to 3.1%. Ball outcomes are mostly chance given the situation, which limits how much of any residual can be credited to the player. The win-probability models used by approach B are better calibrated:

| model | n_validation | brier | brier_const | brier_logit | slope | intercept | gate_passed |
|---|---|---|---|---|---|---|---|
| W1 | 22086 | 0.215 | 0.251 | 0.223 | 0.886 | -0.138 | yes |
| W2 | 20040 | 0.117 | 0.251 | 0.122 | 1.134 | -0.025 | yes |

W1 is the first-innings model and W2 the chase model. Both beat a constant and a logistic baseline and passed the declared calibration gates. Technical soundness does not establish that the resulting player order is reliable (section 10).

## 7. IPL and T20I comparison

Competition is a model feature, and scores are centred by format before combination. Whether a single combined score is justified was tested, not assumed: the declared rule needs a cross-format correlation with lower 95% bound of at least 0.3 across at least 30 players who appear in both formats.

| approach | role | players_both_formats | spearman | spearman_low | spearman_high | combination_supported |
|---|---|---|---|---|---|---|
| A | batter | 85 | 0.100 | -0.136 | 0.290 | no |
| A | bowler | 76 | 0.064 | -0.185 | 0.300 | no |
| B | batter | 85 | 0.040 | -0.168 | 0.263 | no |
| B | bowler | 76 | -0.174 | -0.378 | 0.061 | no |
| C | batter | 85 | -0.105 | -0.318 | 0.116 | no |
| C | bowler | 76 | 0.221 | -0.018 | 0.430 | no |

No approach meets the rule for either role, so the combined estimate is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`: each player-match unit is weighted by its own precision and there is no fixed 70:30 split. IPL and T20I matches, contributions, scores and ranks are shown separately for every listed player in the CSV (`ipl_matches`, `t20i_matches`, `ipl_contribution`, `t20i_contribution`, `ipl_score`, `t20i_score`, `rank_in_IPL`, `rank_in_T20I`). Players' IPL and T20I results are essentially uncorrelated, which is itself evidence of how noisy single-format results are.

## 8. Eligibility and sample size

Declared floors (criteria file, hash below): at least 8 matches, at least 60 balls faced or 72 balls bowled, at least 8 high-intensity units, an effective sample of at least 60, and at least 4 matches in the 2025 window. Floors were also halved and doubled as a sensitivity check.

Eligible players: 225 batters (approach A) and 221 bowlers (approach C). A player below a floor is `INSUFFICIENT_EVIDENCE`, which says nothing about quality. No list is padded.

## 9. Shrinkage and uncertainty

Player estimates are shrunk towards the cohort mean by a random-effects model fitted by REML on the match-level units, so a player with few pressure appearances moves further towards the mean. Shrinkage was not removed or weakened to make a gate pass. Between-player variance (tau squared) estimated for approach A at the P4 intensity, by scope:

| role | scope | n_players | tau2 | sigma2 | floor | label |
|---|---|---|---|---|---|---|
| batter | COMBINED | 225 | 0.000 | 1.020 | no | BETWEEN_PLAYER_SIGNAL |
| batter | IPL | 104 | 0.000 | 0.998 | no | BETWEEN_PLAYER_SIGNAL |
| batter | T20I | 140 | 0.000 | 1.015 | yes | NO_BETWEEN_PLAYER_SIGNAL |
| bowler | COMBINED | 221 | 0.001 | 0.701 | no | BETWEEN_PLAYER_SIGNAL |
| bowler | IPL | 102 | 0.001 | 0.727 | no | BETWEEN_PLAYER_SIGNAL |
| bowler | T20I | 154 | 0.001 | 0.669 | no | BETWEEN_PLAYER_SIGNAL |

The variances are tiny relative to the residual variance (sigma squared), so the data find very little player-to-player difference to shrink towards. Where a scope sits at the floor (tau squared 0), the predeclared rule orders players by the unshrunk precision-weighted mean and forces the label EXPLORATORY. For the submitted combined scope the status table stores tau squared 0.0000 for batters and 0.0008 for bowlers.

Intervals are 95% percentile intervals from a 1,000-draw bootstrap that resamples whole matches (seed 20260512), re-estimating the between-player variance in every draw. Each row also reports Top-10 inclusion probability, a 95% rank interval and a sample-reliability (shrinkage) figure. Bowler score intervals are skewed above the point estimate because the scale is held at its full-sample value while shrinkage changes; 9 of 10 bowler rows carry the flag `ASYMMETRIC_UPPER_TAIL`. Rank intervals and inclusion probabilities use every draw and are the better guide.

Evidence classes (declared in advance): STRONG_SUBSTANTIAL (interval above 0, at least twice the match floor, positive share at least 0.5), STRONG_LIMITED, INCONSISTENT and INSUFFICIENT.

## 10. Reliability validation

Reliability asks whether the method gives the same order twice. Two matched halves of each player's matches are scored independently (odd and even matches by date, and early against late), the correlation is corrected to full length (Spearman-Brown) and its interval comes from a match-cluster bootstrap. An out-of-time test correlates TRAIN-period estimates with VALIDATION-period estimates. Batters first, then bowlers:

**Batters**

| approach | split-half (Spearman-Brown) | 95% interval | out-of-time r | out-of-time lower bound | ICC(1) | variance at floor | mean data weight | passes 0.5 data-weight gate | eligible players | submitted |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.057 | -0.220 to 0.361 | 0.199 | 0.017 | 0.0064 | no | 0.069 | no | 225 | yes |
| B | 0.042 | -0.331 to 0.360 | -0.001 | -0.201 | 0.0052 | yes | 0.000 | no | 224 | no |
| C | 0.057 | -0.190 to 0.300 | -0.020 | -0.197 | n/a | no | 0.117 | no | 224 | no |

**Bowlers**

| approach | split-half (Spearman-Brown) | 95% interval | out-of-time r | out-of-time lower bound | ICC(1) | variance at floor | mean data weight | passes 0.5 data-weight gate | eligible players | submitted |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.220 | -0.228 to 0.330 | 0.131 | -0.074 | 0.0131 | no | 0.237 | no | 221 | no |
| B | -0.135 | -0.465 to 0.258 | -0.176 | -0.364 | 0.0319 | yes | 0.000 | no | 221 | no |
| C | 0.267 | -0.078 to 0.391 | 0.199 | 0.027 | n/a | no | 0.263 | no | 221 | yes |

Approach C's figures use held-out matches only (its weights were fitted on the other half), so its columns are not like for like with A and B; the selection rule was applied as declared and the difference is disclosed rather than corrected. The Phase 6 data-weight gate (mean data weight of at least 0.5) is reported unchanged and no approach passes it.

Phase 6 findings that remain true after Phase 8: between-player variance sits at the shrinkage floor in all 48 contexts; pooled odd/even reliability was 0.37 (0.3656) with a median of 0.25 over the 47 estimable contexts; 0 of 48 contexts pass the 0.5 data-weight gate; no pressure definition passed the predeclared criteria; rankings are sensitive to definitions and resampling. Phase 8 changed the method (continuous intensity, richer expected-outcome models, match-level units, REML) and tested whether the result improved. The technical pipeline improved; the central finding did not change.

## 11. Sensitivity analysis

Each row compares the submitted order with a variant: Spearman correlation over the players both versions rank, and how many of the ten submitted players remain in the variant's Top 10.

| role | family | comparison | n_common | spearman | top10_overlap |
|---|---|---|---|---|---|
| batter | pressure definition | intensity_P0 | 160 | 0.818 | 3 |
| batter | pressure definition | intensity_P3 | 129 | 0.655 | 3 |
| batter | pressure definition | intensity_P5 | 122 | 0.364 | 4 |
| batter | pressure definition | intensity_P6 | 120 | 0.729 | 3 |
| batter | format (IPL, T20I, combined) | scope_IPL_only | 104 | 0.867 | 6 |
| batter | format (IPL, T20I, combined) | scope_T20I_only | 140 | 0.811 | 5 |
| batter | assumption (ordering, weights, innings) | rank_by_pressure_delta | 167 | 0.522 | 1 |
| batter | assumption (ordering, weights, innings) | unshrunk_ordering | 225 | 0.935 | 3 |
| batter | eligibility floor | eligibility_floor_x0.5 | 225 | 0.998 | 10 |
| batter | eligibility floor | eligibility_floor_x2.0 | 134 | 0.994 | 10 |
| batter | component or approach | component_runs_only | 225 | 0.645 | 5 |
| batter | component or approach | component_wicket_only | 225 | 0.683 | 0 |
| batter | bootstrap | bootstrap_method_check | 27 | n/a | n/a |
| batter | calendar window | window_2022_2024 | 186 | 0.831 | 3 |
| batter | calendar window | window_2025 | 146 | 0.669 | 3 |
| bowler | component or approach | published_approach_A_rank | 221 | 0.776 | 8 |
| bowler | component or approach | published_approach_B_rank | 221 | 0.386 | 0 |
| bowler | component or approach | component_A_only | 221 | 0.778 | 8 |
| bowler | component or approach | component_B_only | 221 | 0.386 | 0 |
| bowler | component or approach | component_CONS_only | 221 | 1.000 | 10 |
| bowler | assumption (ordering, weights, innings) | equal_weights_not_data_derived | 221 | 0.851 | 8 |
| bowler | format (IPL, T20I, combined) | scope_IPL_only | 102 | 0.839 | 6 |
| bowler | format (IPL, T20I, combined) | scope_T20I_only | 154 | 0.920 | 7 |
| bowler | eligibility floor | eligibility_floor_x0.5 | 221 | 0.998 | 10 |
| bowler | eligibility floor | eligibility_floor_x2.0 | 136 | 0.999 | 10 |
| bowler | assumption (ordering, weights, innings) | unshrunk_ordering | 221 | 0.967 | 2 |
| bowler | format (IPL, T20I, combined) | hierarchical_format_common_effect | 221 | 0.999 | 10 |
| bowler | assumption (ordering, weights, innings) | innings2_units_only | 221 | 0.626 | 8 |
| bowler | bootstrap | bootstrap_method_check | 221 | n/a | n/a |
| bowler | calendar window | window_2022_2024 | 179 | 0.860 | 4 |
| bowler | calendar window | window_2025 | 138 | 0.586 | 3 |
| bowler | pressure definition | intensity_P0 | 164 | 0.665 | 7 |
| bowler | pressure definition | intensity_P3 | 110 | 0.592 | 6 |
| bowler | pressure definition | intensity_P5 | 131 | 0.323 | 1 |
| bowler | pressure definition | intensity_P6 | 116 | 0.591 | 6 |

The ordering is stable to the eligibility floors and moderately stable to format and calendar window. Membership of the Top 10 changes substantially with the pressure definition, with the shrinkage assumption and with the components used. This matches the Phase 6 sensitivity finding and is a further reason the lists are EXPLORATORY.

## 12. Final ranking evidence

Approach selection used only approach-level metrics declared in advance (split-half and out-of-time lower bounds, inclusion concentration, an explainability checklist), never a player's rank or name. For batters the rule path was `NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE` and chose A; for bowlers it was `NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE` and chose C. Both the lower-bound path and the point-estimate path agree in each role.

For batters, approaches A and C are within 0.001 of each other on the split-half point estimate and both intervals include 0, so the choice of A should not be read as a performance difference. Bowlers' approach C leads on the split-half point estimate and on the out-of-time lower bound but its interval also includes 0, and approach A has one more player with a Top-10 probability of at least 0.5.

Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`, was verified against the run log before every comparison step.

Player-level evidence for all twenty listed players, and for near-miss and high-raw-statistic players who were not listed, with data-based reasons, is in `player_selection_explanations.md` (batter NEAR_MISS: 24, batter RAW_STANDOUT: 31, batter SELECTED: 10, bowler NEAR_MISS: 22, bowler RAW_STANDOUT: 29, bowler SELECTED: 10 entries). A player left out is never described as poor merely for lacking evidence.

## 13. Limitations

- No approach reached the declared PROVISIONAL threshold. The orders are not shown to separate players beyond noise.
- The pressure definition used (P4) did not pass the declared validity rule.
- Ball outcomes are mostly chance given the situation: the expected-outcome models improve on a constant by 1.5% to 3.1%.
- The sample is small: the twenty listed players have 19 to 88 pressure appearances each (one appearance is one innings or one spell at pressure intensity 0.5 or more), over 2022 to 2025.
- IPL and T20I results are not correlated enough to combine; the combined estimate is a precision-weighted compromise, labelled as such.
- The bowler index reduces to a consistency share, which rewards beating the expectation often rather than by much.
- The 2026 matches are not used. They were opened once in an earlier phase and are not a clean hold-out; using them needs an explicit owner decision.
- The 42 T20I matches with late-dated records are excluded from primary evaluation and have not been verified against an official source.
- Win-probability models for the first innings are less well calibrated (slope 0.89) than for chases (slope 1.13).
- The experimental AI predictions are a separate, validation-period diagnostic and are not part of the submitted ranking.

## 14. Glossary of status labels

- **VALIDATED**: split-half reliability at least 0.70 with an interval lower bound at least 0.50 and an out-of-time lower bound above 0.30, all declared before any result. *Nothing in this submission has this label.*
- **PROVISIONAL**: split-half reliability at least 0.50 with an interval lower bound above 0 and an out-of-time lower bound above 0, but not every VALIDATED threshold. *Nothing in this submission has this label.*
- **EXPLORATORY**: an ordered list exists but the PROVISIONAL thresholds were not met. The order is the best available description of the data and is not shown to separate players beyond noise. *Both submitted lists and all twenty rows have this label.*
- **INSUFFICIENT_EVIDENCE**: fewer than ten players meet the eligibility floors, or the approach cannot be computed. A player with this label is not ranked and nothing is implied about their quality. *No list needed it; players below an eligibility floor are not ranked.*

A row never carries a stronger label than its list. The submitted ranking status (is this order reliable?) is kept apart from the model validation status (did the method pass its declared tests?).

## Appendix A. Technical details

**Splits.** `config/phase4_split_v1.json`: TRAIN to 2024-12-31, VALIDATION calendar 2025, TEST 2026 onwards (never loaded; a lock log hash was identical before and after every stage). Chronological, whole matches only, checked by test.

**Models.** Expected-outcome: scikit-learn gradient boosting (regressor for runs, histogram classifier for wicket, dot, boundary), grid of learning rate {0.05, 0.1}, depth {3, 5}, L2 {0, 1}, 200 iterations, minimum leaf 200, chosen once on VALIDATION by RMSE or log loss. Win probability: histogram gradient boosting with logistic and isotonic baselines. Artefacts in `backend/data/models/` with metadata JSON and SHA-256 (see `ai_pipeline_verification.md`). Seed 20260512.

**REML.** Random-effects model per scope (combined with format-centred units, IPL, T20I): player effect with variance tau squared, residual variance sigma squared, estimated by REML; posterior mean per player. A tau squared below 1e-8 sigma squared is flagged FLOOR and no floor is imposed.

**Win probability added attribution.** Striker receives runs off the bat; bowler receives wickets with bowler credit, wides and no-balls; byes and leg-byes go to the batting side collectively; run-outs and other non-credit dismissals never give bowler credit; unusual events are excluded and counted in `p8_wpa_excluded_events`.

**Reliability estimators.** Split-half on unshrunk precision-weighted unit means; Spearman-Brown 2r/(1+r); Fisher-z pooling; one-way ICC(1) on unit means of players with at least two matches; 1,000-draw match-cluster bootstrap.

**Reproduction.** From `d:/Data/backend` with `PYTHONUTF8=1`: `python scripts/phase8_final_ranking.py all` regenerates the lists and reports from the stored tables (two runs give byte-identical CSV and JSON); `python scripts/run_phase8.py all` regenerates this document, the test report, the audit, the manifest and the bundle. The manifest `phase8_build_manifest.json` records input hashes, output hashes and tool versions.

**Versions.** Methodology `phase8_methodology_v1`; criteria `phase8_selection_criteria_v1` (SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`); generated 2026-11-18T06:14:05+00:00.
