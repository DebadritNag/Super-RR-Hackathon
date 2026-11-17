# Phase 8 Approach B results: match leverage and Win Probability Added (WPA)

Status: **EXPERIMENTAL_NOT_VALIDATED**. Every player list below is an exploratory ordering produced by Approach B alone. It is not the submitted ranking and it is not validated: the Phase 6 findings (between-player variance at the shrinkage floor, split-half reliability far below 0.5, zero contexts passing the 0.5 data-weight gate) were re-tested and still hold (section 7). The submitted lists are chosen later by the predeclared rule. Every number is read from the `p8_wp_*`, `p8_delivery_leverage`, `p8_wpa_*` and `p8_b_*` tables in `phase8.duckdb`. TEST (2026 onward) was not opened.

## 1. Definitions kept apart

| Object | Definition | Uses outcome of the ball? |
|---|---|---|
| Pressure intensity | pre-delivery situational difficulty in [0,1] (section 5) | no |
| Leverage `L` | expected absolute win-probability swing of the next ball, `sum_k p_k abs(WP_k - WP_before)` over seven outcome classes | no |
| WPA | realised `WP_after - WP_before`, credited to players by the rules in section 4 | yes |
| WPA above leverage expectation | WPA minus a TRAIN-fitted linear expectation from leverage, phase, innings and A-model expected runs | yes |

High WPA is never read as pressure. Leverage is reported as a candidate intensity (P1) and tested like any other candidate; it is mechanically tied to WPA, which is flagged wherever it matters.

## 2. Win-probability models

Population: IPL and T20I, TRAIN (487 matches) and VALIDATION (188 matches). Labels use decisive regulation results only: 644 matches are labelled and 31 in-scope matches are excluded and never imputed (no result, abandoned, tied, Super Over or eliminator, DLS or D/L text, revised target).

| reason_group | matches |
|---|---|
| NO_WINNER | 13 |
| RESULT_TEXT | 18 |

Models (`app/phase8/winprob.py`): `W2` (innings 2, target: chasing side wins) and `W1` (innings 1, target: batting side eventually wins) are HistGradientBoosting classifiers on pre-delivery state only (features in the artefact metadata). One pass over the declared grid on VALIDATION chose the parameters by log loss; TRAIN deliveries are scored out of fold (`match_id % 5`) and VALIDATION deliveries by the model fitted on all of TRAIN. Baselines: constant prior and a logistic regression on a few state variables. Both opposing-team priors (win rate over the last five earlier decisive matches) are used instead of the batting side's alone (declared change; both are pre-match information).

Validation metrics (out of sample, 2025):

| model | n_validation | brier | brier_const | brier_logit | brier_gain_vs_const | brier_gain_vs_logit | log_loss | log_loss_const | log_loss_logit | slope | intercept |
|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 22086 | 0.2150 | 0.2510 | 0.2227 | 0.1434 | 0.0346 | 0.6201 | 0.6951 | 0.6369 | 0.8855 | -0.1380 |
| W2 | 20040 | 0.1167 | 0.2506 | 0.1224 | 0.5344 | 0.0464 | 0.3629 | 0.6943 | 0.3789 | 1.1337 | -0.0246 |

Innings-1 gate (declared before results: calibration slope in [0.8, 1.2] and Brier gain of at least 2% over the constant):

| model | gate_slope_ok | gate_brier_gain_ok | gate_passed |
|---|---|---|---|
| W1 | yes | yes | yes |
| W2 | yes | yes | yes |

W1 passes the declared gate on VALIDATION (slope 0.886, Brier gain 0.143). The out-of-fold TRAIN scores are weaker (slope 0.574, Brier gain 0.059), so the innings-1 model is less stable than the validation gate alone suggests. The gate was not changed after seeing results; the estimates are therefore also reported with innings 1 excluded (`innings2_only` in section 7).

Decile calibration on VALIDATION (equal-count bins of predicted probability):

`W2`:

| bin | n | mean_pred | mean_obs |
|---|---|---|---|
| 1 | 2004 | 0.010 | 0.001 |
| 2 | 2004 | 0.049 | 0.046 |
| 3 | 2004 | 0.144 | 0.117 |
| 4 | 2004 | 0.275 | 0.257 |
| 5 | 2004 | 0.410 | 0.347 |
| 6 | 2004 | 0.555 | 0.555 |
| 7 | 2004 | 0.697 | 0.719 |
| 8 | 2004 | 0.831 | 0.864 |
| 9 | 2004 | 0.947 | 0.982 |
| 10 | 2004 | 0.992 | 0.987 |

`W1`:

| bin | n | mean_pred | mean_obs |
|---|---|---|---|
| 1 | 2209 | 0.166 | 0.228 |
| 2 | 2209 | 0.279 | 0.224 |
| 3 | 2209 | 0.375 | 0.272 |
| 4 | 2209 | 0.443 | 0.410 |
| 5 | 2209 | 0.499 | 0.458 |
| 6 | 2209 | 0.553 | 0.608 |
| 7 | 2208 | 0.607 | 0.593 |
| 8 | 2208 | 0.674 | 0.613 |
| 9 | 2208 | 0.755 | 0.699 |
| 10 | 2208 | 0.863 | 0.796 |

Feature recompute check (the one function that builds features for real rows and for hypothetical next states reproduces the stored state columns):

| column | max_abs_diff |
|---|---|
| rrr | 0.000000000000 |
| gap | 0.000000000000 |
| resource_ratio | 0.000000000000 |
| projected_total | 0.000000000000 |
| crr | 0.000000000000 |

Artefact: `backend/data/models/p8_wp_v1.joblib` with `p8_wp_v1.json` (algorithm, version, training period `matches up to 2024-12-31 (config/phase4_split_v1.json)`, matches and deliveries, features, targets, metrics, exploratory database hash `7b396e42a2acb281fd5ffd64051064d7ac48e82bdfad23dd229bd20b9ca6277d`, seed 20260512, timestamp 2026-11-17T14:00:20.069444+00:00, criteria hash 9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64).

## 3. Leverage

The next-ball class model (dot, 1, 2, 3, 4, 6, wicket; legal balls) uses situation features only (no batter or bowler variables) with fixed declared parameters (no tuning). Validation: multi-class log loss 1.5070 against 1.5328 for the class prior (gain 0.017); wicket-probability Brier 0.05348 against 0.05374. The class probabilities add little over the prior, so leverage is driven mainly by the win-probability surface, not by the outcome mix.

| period | innings_number | balls | defined | mean_leverage | median_leverage | p95 | mean_abs_wpa |
|---|---|---|---|---|---|---|---|
| TRAIN | 1 | 60405 | 60405 | 0.0148 | 0.0103 | 0.0422 | 0.0149 |
| TRAIN | 2 | 54807 | 54316 | 0.0209 | 0.0138 | 0.0624 | 0.0205 |
| VALIDATION | 1 | 23081 | 23081 | 0.0152 | 0.0108 | 0.0445 | 0.0153 |
| VALIDATION | 2 | 20295 | 20295 | 0.0198 | 0.0133 | 0.0583 | 0.0202 |

Check that leverage measures what it claims: on VALIDATION the Spearman correlation between pre-delivery leverage and the realised absolute swing of the ball is 0.594 (43312 balls). Leverage is computed before the ball and never uses its outcome.

## 4. WPA attribution

`WP_after` of a ball is `WP_before` of the next ball of the same innings; the last ball of an innings 2 uses the match result, the last ball of an innings 1 uses `1 - WP2` of the first ball of the chase. WP is clipped to [0.005, 0.995] before differencing. Rules (`app/phase8/wpa.py`):

- runs off the bat and dot balls: striker `+d`, bowler `-d`;
- wides and the no-ball penalty: bowler only; a wide gives the striker nothing;
- byes and leg-byes: batting side collectively, no striker and no bowler credit (the ball is left out of both players' records, not counted as zero);
- bowler-credited wicket (bowled, caught, lbw, stumped, hit wicket): dismissed batter `d_wkt`, bowler `-d_wkt`;
- run-outs: dismissed player takes the wicket share, the bowler gets neither credit nor blame (fielding is not modelled);
- retired, obstructing the field, extras of type other or penalty, metric-flag anomalies and balls with no defined WP are excluded and counted below.

When a ball has more than one component (for example a wicket with a dot, a no-ball with runs, a run-out with a run) the realised delta is split by a counterfactual rule: each component's delta is the WP change if only that component had happened, and the remainder is shared in proportion to the absolute component deltas, so the parts always add up to the ball's `d`. This replaces the plan's expected-share split (declared change). A non-striker dismissed in a run-out is recorded in the delivery table but does not enter the striker-keyed batter units.

| excluded_reason | innings | period | balls |
|---|---|---|---|
| EXTRAS_OTHER_OR_PENALTY | 1 | TRAIN | 84 |
| EXTRAS_OTHER_OR_PENALTY | 1 | VALIDATION | 26 |
| EXTRAS_OTHER_OR_PENALTY | 2 | TRAIN | 72 |
| EXTRAS_OTHER_OR_PENALTY | 2 | VALIDATION | 23 |
| METRIC_FLAG_ANOMALY | 1 | TRAIN | 5 |
| METRIC_FLAG_ANOMALY | 2 | TRAIN | 4 |
| METRIC_FLAG_ANOMALY | 2 | VALIDATION | 2 |
| UNUSUAL_EVENT | 1 | TRAIN | 2 |
| UNUSUAL_EVENT | 2 | TRAIN | 2 |
| UNUSUAL_EVENT | 2 | VALIDATION | 3 |
| WP_UNAVAILABLE | 1 | TRAIN | 17 |
| WP_UNAVAILABLE | 1 | VALIDATION | 7 |
| WP_UNAVAILABLE | 2 | TRAIN | 499 |
| WP_UNAVAILABLE | 2 | VALIDATION | 3 |

| split_rule | innings | balls | attributed |
|---|---|---|---|
| NOT_ATTRIBUTED | 1 | 141 | 0 |
| NOT_ATTRIBUTED | 2 | 608 | 0 |
| COUNTERFACTUAL | 1 | 4004 | 4004 |
| COUNTERFACTUAL | 2 | 3982 | 3982 |
| EQUAL_FALLBACK | 1 | 52 | 52 |
| EQUAL_FALLBACK | 2 | 13 | 13 |
| SINGLE | 1 | 78693 | 78693 |
| SINGLE | 2 | 70202 | 70202 |
| ZERO_DELTA | 1 | 596 | 596 |
| ZERO_DELTA | 2 | 297 | 297 |

`ZERO_DELTA` marks multi-component balls where WP is flat across all candidate states, so the split cannot matter. More generally the gradient-boosting WP surface is piecewise constant: 0.393 of the 157839 attributed balls have a realised WPA of exactly zero. This coarseness is a limitation of the tree model (small state changes inside one leaf do not move WP) and adds noise to every WPA total.

## 5. Pressure intensity: leverage (P1) and closeness (P2) against the predeclared tests

P1 and P2 are built from the out-of-fold win-probability model and scaled by the same TRAIN-only empirical CDF as the other candidates. Test (d) (mean absolute WP change larger in the top than in the bottom decile) is now available for every candidate; for P1 and P2 it is mechanical.

| candidate | pass | test_a | test_b | test_c | test_e | test_d | n_tests_passed | primary | primary_basis |
|---|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | no | 3 | no |  |
| P1 | no | no | no | no | no | yes | 0 | no |  |
| P2 | no | no | no | no | no | yes | 0 | no |  |
| P3 | no | yes | yes | yes | no | yes | 3 | no |  |
| P4 | no | yes | yes | yes | no | no | 3 | yes | BEST_AVAILABLE_NOT_PASSING |
| P5 | no | no | no | yes | no | yes | 1 | no |  |
| P6 | no | no | yes | yes | no | no | 2 | no |  |

| candidate | period | n | abs_wpa_low_decile | abs_wpa_high_decile | diff | spearman | test_d | mechanical |
|---|---|---|---|---|---|---|---|---|
| P0 | TRAIN | 114527.0000 | 0.0177 | n/a | n/a | n/a | no | no |
| P0 | VALIDATION | 43312.0000 | 0.0185 | n/a | n/a | n/a | no | no |
| P3 | TRAIN | 54230.0000 | 0.0073 | 0.0127 | 0.0054 | 0.3333 | yes | no |
| P3 | VALIDATION | 20264.0000 | 0.0056 | 0.0102 | 0.0046 | 0.0788 | yes | no |
| P4 | TRAIN | 114527.0000 | 0.0214 | 0.0199 | -0.0014 | -0.3455 | no | no |
| P4 | VALIDATION | 43312.0000 | 0.0231 | 0.0165 | -0.0066 | -0.5030 | no | no |
| P5 | TRAIN | 53738.0000 | 0.0139 | 0.0142 | 0.0003 | 0.2970 | yes | no |
| P5 | VALIDATION | 20074.0000 | 0.0146 | 0.0131 | -0.0015 | 0.3455 | no | no |
| P6 | TRAIN | 54230.0000 | 0.0201 | 0.0182 | -0.0019 | 0.0424 | no | no |
| P6 | VALIDATION | 20264.0000 | 0.0199 | 0.0134 | -0.0065 | 0.0545 | no | no |
| P2 | TRAIN | 114527.0000 | 0.0043 | 0.0262 | 0.0218 | 1.0000 | yes | yes |
| P2 | VALIDATION | 43312.0000 | 0.0033 | 0.0271 | 0.0238 | 0.9879 | yes | yes |
| P1 | TRAIN | 114527.0000 | 0.0006 | 0.0613 | 0.0607 | 1.0000 | yes | yes |
| P1 | VALIDATION | 43312.0000 | 0.0004 | 0.0584 | 0.0580 | 1.0000 | yes | yes |

No candidate passes the predeclared pass rule. Leverage (P1) and closeness (P2) do not mark situations with lower scoring or higher wicket risk, so they fail tests a, b, c and e: a ball can be high-stakes without being hard for the batting side. The primary intensity stays `P4` with basis `BEST_AVAILABLE_NOT_PASSING` (best available, not passing), as chosen for Approach A. The test (d) column shows that the primary intensity does not mark balls with larger WP swings either.

| candidate | period | runs_diff | wkt_diff | var_diff | test_a | test_b | test_c | test_e |
|---|---|---|---|---|---|---|---|---|
| P1 | TRAIN | 0.0053 | 0.0003 | -0.0728 | no | no | no | no |
| P1 | VALIDATION | 0.0493 | -0.0049 | -0.0550 | no | no | no | no |
| P2 | TRAIN | -0.0102 | -0.0155 | -0.2348 | no | no | no | no |
| P2 | VALIDATION | -0.0131 | -0.0074 | -0.2376 | no | no | no | no |

## 6. Player-level B score

Per delivery the credit is the role's WPA (striker or bowler). The B residual is `credit - fitted`, where `fitted` comes from a linear regression on leverage, leverage squared, phase, innings and the A-model expected runs, fitted on TRAIN only (out of fold for TRAIN rows). The unit is the player-match; the REML, eligibility floors, match-cluster bootstrap (1000 full refits), split-half, ICC and out-of-time procedures are exactly those of Approach A (`run_cell`). Pressure balls are those with intensity of at least 0.5; the normal baseline is the mean B residual on balls below 0.5. Positive is better for the player in both roles.

| role | const | L | L2 | middle | death | innings2 | exp_runs |
|---|---|---|---|---|---|---|---|
| batter | -0.0012 | -0.2799 | 1.1451 | -0.0018 | -0.0024 | 0.0009 | 0.0040 |
| bowler | 0.0017 | 0.2267 | -1.0460 | 0.0016 | 0.0018 | -0.0010 | -0.0040 |

## 7. Reliability, floor and sensitivity

**Batters** REML (primary intensity `P4`, combined formats):

| tau2 | sigma2 | floor | label | mean_B | share_B_gt_0_5 | n_players | n_units |
|---|---|---|---|---|---|---|---|
| 0.000000 | 0.002518 | yes | NO_BETWEEN_PLAYER_SIGNAL | 0.000000 | 0.000000 | 224 | 5474 |

**Bowlers** REML (primary intensity `P4`, combined formats):

| tau2 | sigma2 | floor | label | mean_B | share_B_gt_0_5 | n_players | n_units |
|---|---|---|---|---|---|---|---|
| 0.000000 | 0.001899 | yes | NO_BETWEEN_PLAYER_SIGNAL | 0.000000 | 0.000000 | 221 | 5704 |

Between-player variance is at the floor for the primary cell of both roles (tau2 is zero), so the posterior collapses to the league mean and the listed order is the unshrunk precision-weighted mean (`UNSHRUNK_FLOOR`). The share of players with data weight B above 0.5, the Phase 6 gate quantity, is reported unchanged in the `share_B_gt_0_5` column.

| role | intensity | n_eligible | split_half_sb | split_half_sb_low | split_half_sb_high | time_sb | icc1 | oot_spearman | oot_low | oot_players | floor | volume_spearman | indicative_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| batter | P1 | 246 | -0.110 | -0.473 | 0.360 | -0.229 | 0.008 | 0.097 | -0.103 | 127.000 | no | 0.221 | EXPLORATORY |
| batter | P2 | 215 | 0.115 | -0.607 | 0.335 | 0.151 | 0.014 | 0.029 | -0.174 | 106.000 | yes | 0.295 | EXPLORATORY |
| batter | P4 | 224 | 0.042 | -0.331 | 0.360 | -0.072 | 0.005 | -0.001 | -0.201 | 111.000 | yes | 0.373 | EXPLORATORY |
| bowler | P1 | 243 | -0.053 | -0.234 | 0.345 | 0.156 | 0.038 | -0.064 | -0.264 | 110.000 | no | 0.125 | EXPLORATORY |
| bowler | P2 | 215 | 0.113 | -0.211 | 0.387 | 0.003 | 0.004 | 0.069 | -0.137 | 98.000 | no | 0.173 | EXPLORATORY |
| bowler | P4 | 221 | -0.135 | -0.465 | 0.258 | 0.043 | 0.032 | -0.176 | -0.364 | 105.000 | yes | 0.096 | EXPLORATORY |

Reliability was computed for the primary intensity and for P1 and P2 (the remaining candidates were estimated without bootstrap and reliability to bound run time; they appear in the sensitivity table). Pass thresholds are those declared: split-half Spearman-Brown of at least 0.5 with a positive lower bound and a positive out-of-time lower bound for PROVISIONAL.

Sensitivity of the primary ordering (Spearman and Top-10 overlap with the primary):

| role | comparison | n_common | spearman | top10_overlap | n_eligible |
|---|---|---|---|---|---|
| batter | intensity_P0 | 159 | 0.902 | 6 | n/a |
| batter | intensity_P1 | 185 | 0.623 | 1 | n/a |
| batter | intensity_P2 | 164 | 0.550 | 2 | n/a |
| batter | intensity_P3 | 129 | 0.766 | 4 | n/a |
| batter | intensity_P5 | 121 | 0.566 | 1 | n/a |
| batter | intensity_P6 | 120 | 0.836 | 5 | n/a |
| batter | scope_IPL_only | 104 | 0.874 | 5 | n/a |
| batter | scope_T20I_only | 139 | 0.877 | 5 | n/a |
| batter | rank_by_pressure_delta | 167 | 0.578 | 2 | n/a |
| batter | unshrunk_ordering | 224 | 1.000 | 10 | n/a |
| batter | eligibility_floor_x0.5 | 224 | 1.000 | 5 | 330.000 |
| batter | eligibility_floor_x2.0 | 132 | 1.000 | 7 | 132.000 |
| batter | raw_wpa_not_leverage_adjusted | 224 | 0.958 | 8 | 224.000 |
| batter | innings2_only | 128 | 0.841 | 5 | 128.000 |
| batter | leverage_weighted_wpa_per_opportunity_all_balls | 224 | 0.684 | 2 | n/a |
| bowler | intensity_P0 | 163 | 0.841 | 5 | n/a |
| bowler | intensity_P1 | 220 | 0.700 | 0 | n/a |
| bowler | intensity_P2 | 198 | 0.620 | 0 | n/a |
| bowler | intensity_P3 | 110 | 0.851 | 2 | n/a |
| bowler | intensity_P5 | 131 | 0.608 | 2 | n/a |
| bowler | intensity_P6 | 116 | 0.877 | 3 | n/a |
| bowler | scope_IPL_only | 102 | 0.743 | 2 | n/a |
| bowler | scope_T20I_only | 154 | 0.815 | 3 | n/a |
| bowler | rank_by_pressure_delta | 221 | 0.624 | 5 | n/a |
| bowler | unshrunk_ordering | 221 | 1.000 | 10 | n/a |
| bowler | eligibility_floor_x0.5 | 221 | 1.000 | 7 | 321.000 |
| bowler | eligibility_floor_x2.0 | 136 | 1.000 | 3 | 136.000 |
| bowler | raw_wpa_not_leverage_adjusted | 221 | 0.896 | 0 | 221.000 |
| bowler | innings2_only | 133 | 0.886 | 3 | 133.000 |
| bowler | leverage_weighted_wpa_per_opportunity_all_balls | 221 | 0.657 | 6 | n/a |

IPL and T20I combination study (declared rule: lower 95% bound of the cross-format correlation at least 0.3 and at least 30 players with both):

| role | players_both_formats | spearman | spearman_low | spearman_high | combination_supported | combination_basis |
|---|---|---|---|---|---|---|
| batter | 85 | 0.040 | -0.168 | 0.263 | no | FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED |
| bowler | 76 | -0.174 | -0.378 | 0.061 | no | FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED |

Bootstrap check (fixed-variance draws against full refits; the full refit is used for every rank statistic):

| role | intensity | draws | players_compared | max_abs_gap | fixed_variance_within_0_05 |
|---|---|---|---|---|---|
| batter | P1 | 1000 | 44 | 0.459 | no |
| batter | P2 | 1000 | 42 | 0.645 | no |
| batter | P4 | 1000 | 46 | 0.563 | no |
| bowler | P1 | 1000 | 39 | 0.400 | no |
| bowler | P2 | 1000 | 30 | 0.336 | no |
| bowler | P4 | 1000 | 41 | 0.321 | no |

## 8. Exploratory Top 10 by Approach B (not the submitted ranking)

Ordered by the unshrunk pressure score of the B residual because the variance is at the floor. `top10_prob` is the share of 1000 match-cluster bootstrap draws in which the player is in the Top 10. The status of both lists under Approach B is EXPLORATORY; the lists are shown so the comparison chunk can contrast them with Approaches A and C, not as a recommendation.

### Batters

| rank | player_name | estimate | ci_low | pressure_delta | n_matches | balls | n_units | top_k_prob | rank_low | rank_high | evidence_class | matches_ipl | matches_t20i |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Dushmantha Chameera | 0.018 | -0.005 | n/a | 18 | 61 | 18 | 0.311 | 1.000 | 148.000 | INCONSISTENT | 9.000 | 9.000 |
| 2 | Jaydev Unadkat | 0.009 | 0.000 | n/a | 10 | 67 | 10 | 0.059 | 8.000 | 99.000 | STRONG_LIMITED | 10.000 | n/a |
| 3 | Tim David | 0.007 | 0.003 | 0.000 | 76 | 964 | 73 | 0.947 | 1.000 | 17.025 | STRONG_SUBSTANTIAL | 41.000 | 35.000 |
| 4 | Ashutosh Sharma | 0.006 | -0.002 | n/a | 18 | 232 | 18 | 0.361 | 1.000 | 156.000 | INCONSISTENT | 18.000 | n/a |
| 5 | Dewald Brevis | 0.006 | -0.002 | 0.007 | 28 | 481 | 16 | 0.337 | 2.000 | 139.000 | INCONSISTENT | 15.000 | 13.000 |
| 6 | Tony Munyonga | 0.006 | -0.012 | 0.013 | 11 | 115 | 11 | 0.200 | 2.000 | 207.000 | INCONSISTENT | n/a | 11.000 |
| 7 | Fakhar Zaman | 0.006 | -0.001 | 0.007 | 41 | 772 | 20 | 0.345 | 2.000 | 133.025 | INCONSISTENT | n/a | 41.000 |
| 8 | Ravichandran Ashwin | 0.006 | -0.002 | 0.011 | 37 | 309 | 32 | 0.330 | 1.000 | 164.000 | INCONSISTENT | 33.000 | 4.000 |
| 9 | Bhanuka Rajapaksa | 0.005 | -0.002 | 0.003 | 31 | 410 | 19 | 0.182 | 4.000 | 150.025 | STRONG_LIMITED | 13.000 | 18.000 |
| 10 | Matthew Wade | 0.005 | -0.002 | 0.009 | 29 | 399 | 19 | 0.275 | 2.000 | 159.100 | INCONSISTENT | 11.000 | 18.000 |

Of these ten, 1 have a Top-10 inclusion probability of at least 0.5 and 1 are classed STRONG_SUBSTANTIAL. The median 95% rank interval spans 147 places, so the order within and around the list is not distinguishable from noise. Players near the eligibility floor can reach the top because the unshrunk mean of a few units is volatile; that is the reason shrinkage exists, and it cannot help here because the between-player variance estimate is zero.

Ranks 11 to 20 (batters):

| rank | player_name | estimate | n_matches | balls | top_k_prob | evidence_class |
|---|---|---|---|---|---|---|
| 11 | Mohammad Rizwan | 0.005 | 36 | 1127 | 0.184 | INCONSISTENT |
| 12 | Anrich Nortje | 0.005 | 14 | 63 | 0.001 | INCONSISTENT |
| 13 | Rahul Tewatia | 0.005 | 41 | 376 | 0.400 | INCONSISTENT |
| 14 | Rassie van der Dussen | 0.005 | 20 | 305 | 0.092 | STRONG_LIMITED |
| 15 | Asif Ali | 0.004 | 13 | 77 | 0.001 | STRONG_LIMITED |
| 16 | Dasun Shanaka | 0.004 | 42 | 543 | 0.378 | INCONSISTENT |
| 17 | Usman Khan | 0.004 | 18 | 243 | 0.030 | INCONSISTENT |
| 18 | M Shahrukh Khan | 0.004 | 36 | 355 | 0.247 | INCONSISTENT |
| 19 | Shahbaz Ahmed | 0.004 | 30 | 384 | 0.285 | INCONSISTENT |
| 20 | Najibullah Zadran | 0.004 | 21 | 272 | 0.137 | INCONSISTENT |

Evidence behind the top ten (batters): observed and expected WPA on pressure balls, leverage, and leverage-weighted WPA per opportunity over all balls.

| rank | player_name | obs_wpa | exp_wpa_given_leverage | mean_leverage_pressure | lw_wpa_per_opp | normal_baseline | pressure_delta | pos_share |
|---|---|---|---|---|---|---|---|---|
| 1 | Dushmantha Chameera | 0.0169 | -0.0011 | 0.0216 | 0.3275 | n/a | n/a | 0.3333 |
| 2 | Jaydev Unadkat | 0.0104 | 0.0016 | 0.0313 | 0.1755 | n/a | n/a | 0.8000 |
| 3 | Tim David | 0.0050 | -0.0014 | 0.0247 | 0.0240 | 0.0069 | 0.0000 | 0.5342 |
| 4 | Ashutosh Sharma | 0.0040 | -0.0013 | 0.0249 | 0.0207 | n/a | n/a | 0.3889 |
| 5 | Dewald Brevis | 0.0056 | -0.0001 | 0.0132 | 0.0036 | -0.0008 | 0.0070 | 0.4375 |
| 6 | Tony Munyonga | 0.0042 | -0.0032 | 0.0243 | 0.0145 | -0.0069 | 0.0127 | 0.0909 |
| 7 | Fakhar Zaman | 0.0041 | -0.0017 | 0.0200 | -0.0005 | -0.0012 | 0.0070 | 0.4000 |
| 8 | Ravichandran Ashwin | 0.0038 | -0.0021 | 0.0207 | 0.0116 | -0.0056 | 0.0113 | 0.4375 |
| 9 | Bhanuka Rajapaksa | 0.0038 | -0.0015 | 0.0179 | 0.0068 | 0.0022 | 0.0031 | 0.5263 |
| 10 | Matthew Wade | 0.0021 | -0.0022 | 0.0298 | 0.0000 | -0.0037 | 0.0090 | 0.4737 |

Players excluded by the eligibility floors (batters): 526. Most frequent reasons:

| failed_rules | players |
|---|---|
| matches;effective_n;balls;high_intensity_units; | 373 |
| high_intensity_units; | 66 |
| effective_n;balls; | 37 |
| matches;high_intensity_units; | 36 |
| matches;effective_n;high_intensity_units; | 11 |
| effective_n;balls;high_intensity_units; | 2 |

### Bowlers

| rank | player_name | estimate | ci_low | pressure_delta | n_matches | balls | n_units | top_k_prob | rank_low | rank_high | evidence_class | matches_ipl | matches_t20i |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Paul van Meekeren | 0.011 | 0.000 | 0.009 | 10 | 185 | 9 | 0.456 | 1.000 | 116.025 | INCONSISTENT | n/a | 10.000 |
| 2 | Ehsan Khan | 0.008 | -0.001 | 0.003 | 8 | 183 | 8 | 0.330 | 1.000 | 129.025 | INCONSISTENT | n/a | 8.000 |
| 3 | Umesh Yadav | 0.008 | -0.000 | 0.010 | 29 | 548 | 19 | 0.415 | 1.000 | 114.075 | INCONSISTENT | 27.000 | 2.000 |
| 4 | Tendai Chatara | 0.006 | -0.002 | 0.004 | 10 | 212 | 9 | 0.133 | 3.000 | 140.025 | STRONG_LIMITED | n/a | 10.000 |
| 5 | Sufiyan Muqeem | 0.006 | 0.001 | 0.003 | 16 | 318 | 13 | 0.392 | 2.000 | 97.000 | STRONG_SUBSTANTIAL | n/a | 16.000 |
| 6 | Craig Young | 0.006 | -0.002 | 0.011 | 20 | 404 | 18 | 0.342 | 1.000 | 161.000 | INCONSISTENT | n/a | 20.000 |
| 7 | Spencer Johnson | 0.005 | -0.003 | 0.009 | 15 | 294 | 12 | 0.259 | 1.000 | 170.050 | INCONSISTENT | 9.000 | 6.000 |
| 8 | Mohsin Khan | 0.005 | -0.004 | 0.006 | 22 | 459 | 19 | 0.426 | 1.000 | 190.000 | INCONSISTENT | 22.000 | n/a |
| 9 | Fareed Malik | 0.005 | -0.006 | 0.011 | 14 | 257 | 12 | 0.279 | 1.000 | 197.025 | INCONSISTENT | n/a | 14.000 |
| 10 | Mayank Yadav | 0.005 | 0.001 | 0.006 | 9 | 189 | 8 | 0.049 | 7.950 | 106.000 | STRONG_LIMITED | 6.000 | 3.000 |

Of these ten, 0 have a Top-10 inclusion probability of at least 0.5 and 1 are classed STRONG_SUBSTANTIAL. The median 95% rank interval spans 133 places, so the order within and around the list is not distinguishable from noise. Players near the eligibility floor can reach the top because the unshrunk mean of a few units is volatile; that is the reason shrinkage exists, and it cannot help here because the between-player variance estimate is zero.

Ranks 11 to 20 (bowlers):

| rank | player_name | estimate | n_matches | balls | top_k_prob | evidence_class |
|---|---|---|---|---|---|---|
| 11 | Saqib Mahmood | 0.005 | 10 | 196 | 0.000 | STRONG_LIMITED |
| 12 | Dasun Shanaka | 0.004 | 30 | 352 | 0.203 | INCONSISTENT |
| 13 | Corbin Bosch | 0.004 | 10 | 194 | 0.145 | STRONG_LIMITED |
| 14 | Benjamin Lister | 0.004 | 11 | 215 | 0.000 | STRONG_LIMITED |
| 15 | Matt Henry | 0.004 | 21 | 463 | 0.156 | INCONSISTENT |
| 16 | Rasikh Salam | 0.004 | 12 | 204 | 0.000 | STRONG_LIMITED |
| 17 | Josh Hazlewood | 0.004 | 47 | 1062 | 0.450 | INCONSISTENT |
| 18 | Richard Gleeson | 0.004 | 9 | 192 | 0.004 | STRONG_LIMITED |
| 19 | William ORourke | 0.004 | 8 | 177 | 0.071 | INCONSISTENT |
| 20 | Benjamin Sears | 0.004 | 14 | 305 | 0.121 | STRONG_LIMITED |

Evidence behind the top ten (bowlers): observed and expected WPA on pressure balls, leverage, and leverage-weighted WPA per opportunity over all balls.

| rank | player_name | obs_wpa | exp_wpa_given_leverage | mean_leverage_pressure | lw_wpa_per_opp | normal_baseline | pressure_delta | pos_share |
|---|---|---|---|---|---|---|---|---|
| 1 | Paul van Meekeren | 0.0128 | 0.0001 | 0.0110 | 0.0409 | 0.0014 | 0.0092 | 0.7778 |
| 2 | Ehsan Khan | 0.0090 | -0.0001 | 0.0161 | 0.0276 | 0.0052 | 0.0029 | 0.7500 |
| 3 | Umesh Yadav | 0.0087 | 0.0000 | 0.0200 | 0.0195 | -0.0016 | 0.0096 | 0.6842 |
| 4 | Tendai Chatara | 0.0074 | 0.0003 | 0.0265 | 0.0285 | 0.0022 | 0.0039 | 0.5556 |
| 5 | Sufiyan Muqeem | 0.0056 | 0.0002 | 0.0128 | 0.0156 | 0.0024 | 0.0033 | 0.9231 |
| 6 | Craig Young | 0.0066 | 0.0006 | 0.0258 | 0.0140 | -0.0049 | 0.0105 | 0.7222 |
| 7 | Spencer Johnson | 0.0050 | -0.0001 | 0.0176 | 0.0024 | -0.0032 | 0.0086 | 0.6667 |
| 8 | Mohsin Khan | 0.0060 | 0.0003 | 0.0239 | 0.0147 | -0.0008 | 0.0062 | 0.6842 |
| 9 | Fareed Malik | 0.0057 | 0.0005 | 0.0302 | 0.0332 | -0.0057 | 0.0108 | 0.5833 |
| 10 | Mayank Yadav | 0.0033 | -0.0013 | 0.0057 | 0.0232 | -0.0008 | 0.0059 | 0.7500 |

Players excluded by the eligibility floors (bowlers): 321. Most frequent reasons:

| failed_rules | players |
|---|---|
| matches;effective_n;balls;high_intensity_units; | 217 |
| matches;high_intensity_units; | 53 |
| high_intensity_units; | 32 |
| matches;balls;high_intensity_units; | 8 |
| matches;effective_n;high_intensity_units; | 7 |
| effective_n;high_intensity_units; | 2 |

## 9. Status of Approach B

| role | intensity | intensity_basis | indicative_list_status | innings1_wp_gate_passed | reason |
|---|---|---|---|---|---|
| batter | P4 | BEST_AVAILABLE_NOT_PASSING | EXPLORATORY | yes | between-player variance at the floor (unshrunk ordering); split-half 0.04 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0 |
| bowler | P4 | BEST_AVAILABLE_NOT_PASSING | EXPLORATORY | yes | between-player variance at the floor (unshrunk ordering); split-half -0.13 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0 |

Both lists are EXPLORATORY. The win-probability models pass the declared calibration and Brier gates on VALIDATION (innings 2 clearly, innings 1 less stably), so the technical pipeline works. That does not make the player ordering reliable: the player-level scores do not separate players beyond noise (the floor binds, split-half and out-of-time lower bounds are not above zero), exactly the Phase 6 conclusion.

## 10. Leakage and integrity checks

- `WP_before`, leverage and every feature are functions of one row's pre-delivery columns; tests show they are unchanged when later rows are truncated or when outcomes and the result label are mutated (`tests/test_phase8_winprob.py`).
- Every fitted component (W1, W2, class model, WPA regression) is fitted on TRAIN only; TRAIN deliveries are scored by models that exclude their match; matches do not straddle partitions.
- The TEST lock state and the protected-file hashes were checked at the start and end of each stage.
- No external reference data source, player identity or rank is used as a feature.

## 11. Limitations

- Leverage uses next-ball classes of legal deliveries only; wides, no-balls and non-striker run-outs are credited through the attribution rules, not through leverage.
- WPA credit mixes player skill with team and match state; the leverage regression removes the average effect of the state, not the quality of the partner or the opposition.
- The innings-1 model is less stable out of fold than on VALIDATION (section 2).
- The class model adds little over the class prior, so leverage differences come mainly from the win-probability surface.
- Because the primary intensity is not validated, `pressure` here means the P4 resource-scarcity proxy, the best available and not a passing definition.
- Declared changes: both opposing-team priors in the WP models; counterfactual instead of expected-share split; fixed class-model parameters; no isotonic recalibration.

