# Phase 8 Approach C results: Pressure Response Index (PRI) and the IPL/T20I combination study

Status: **EXPERIMENTAL_NOT_VALIDATED**. This file reports Approach C (chunk 4) only. It does not select an approach and does not produce the submitted Top 10 files. Every number is read from the `p8_c_*` tables in `phase8.duckdb`. The PRI describes observable performance in difficult situations; it is not a psychological score.

## 1. Design

- Role systems are separate (batters and bowlers are never compared). Unit: player-match-innings pressure unit (deliveries with intensity >= 0.5, weighted by intensity; primary intensity `P4`, basis `BEST_AVAILABLE_NOT_PASSING`: the best available definition, which did **not** pass the predeclared criteria).
- Components, each shrunk by REML on those units: **A** context-adjusted performance (Approach A residual); **B** match impact (leverage-adjusted win-probability-added residual, Approach B); **CONS** consistency (share of pressure units with a positive A residual). Exposure (count and mean intensity) and sample reliability (the REML shrinkage factor) are reported and feed the evidence classes; they are not scored, because a score for facing pressure would reward opportunity.
- Weights are derived from data and fixed on the `FIT` matches (TRAIN, odd position in date order). Reliability, the split-half checks and the out-of-time check below use only the other matches (`HELD`: TRAIN even position plus VALIDATION). No weight was tuned on a ranking, and none was chosen by hand.
- Weight rule: split-half reliability r of each component on FIT (Spearman-Brown) gives w = r/(1-r) (r clipped at 0.99). A non-positive r, a non-estimable r or a REML floor on FIT gives weight 0 and the label `NO_SIGNAL_*`. When two active components correlate above 0.5 (Spearman, FIT) the first principal component of the standardised active components defines the weights. If every component has no signal the PRI is `NOT_DEFINED` and no ranking is produced.
- PRI = sum of weight x (level - cohort mean) / cohort SD over active components, so PRI 0 is the typical eligible player. Level is the REML posterior mean, or the unshrunk mean in a cell at the floor (predeclared rule). Shrinkage was kept in every component.

| role | fit_matches | held_matches | held_train | held_validation | n_players |
|---|---|---|---|---|---|
| batter | 243 | 432 | 244 | 188 | 224 |
| bowler | 243 | 432 | 244 | 188 | 221 |

## 2. Data-derived weights

| role | component | n_players_fit | split_half_sb | tau2_fit | floor_fit | reliability_weight | status | final_weight |
|---|---|---|---|---|---|---|---|---|
| batter | A | 214 | 0.0695 | 0.0000 | yes | 0.0000 | NO_SIGNAL_FLOOR | 0.0000 |
| batter | B | 214 | -0.2256 | 0.0000 | yes | 0.0000 | NO_SIGNAL_FLOOR | 0.0000 |
| batter | CONS | 214 | 0.1875 | 0.0031 | no | 0.2307 | ACTIVE | 1.0000 |
| bowler | A | 212 | -0.2329 | 0.0003 | no | 0.0000 | NO_SIGNAL_NONPOSITIVE_RELIABILITY | 0.0000 |
| bowler | B | 212 | -0.1001 | 0.0000 | yes | 0.0000 | NO_SIGNAL_FLOOR | 0.0000 |
| bowler | CONS | 212 | 0.1754 | 0.0039 | no | 0.2127 | ACTIVE | 1.0000 |

- batter: active components: CONS (weight 1.00).
- bowler: active components: CONS (weight 1.00).

The zero weights are the result of the rule, not a choice. A component whose between-player variance is indistinguishable from zero on FIT, or whose reliability is not positive, carries no information about differences between players there, so giving it weight would add noise to the order.

Spearman correlation of the unshrunk component means on FIT (decides whether PCA is used; threshold 0.5):

| role | component_a | component_b | spearman |
|---|---|---|---|
| batter | A | B | 0.486 |
| batter | A | CONS | 0.790 |
| batter | B | CONS | 0.388 |
| bowler | A | B | 0.571 |
| bowler | A | CONS | 0.730 |
| bowler | B | CONS | 0.445 |

CONS is built from the A units, so a high A-CONS correlation is partly mechanical and is not independent evidence. PCA is only used when at least two components are active.

## 3. Component estimates and the Phase 6 data-weight gate (unchanged)

| role | component | n_players | n_units | tau2 | sigma2 | floor | mean_B | share_B_gt_0_5 | gate_mean_B_ge_0_5 |
|---|---|---|---|---|---|---|---|---|---|
| batter | A | 224 | 5512 | 0.0003 | 1.0189 | no | 0.0736 | 0.0000 | no |
| batter | B | 224 | 5474 | 0.0000 | 0.0025 | yes | 0.0000 | 0.0000 | no |
| batter | CONS | 224 | 5512 | 0.0014 | 0.2424 | no | 0.1166 | 0.0000 | no |
| bowler | A | 221 | 5721 | 0.0008 | 0.7004 | no | 0.2388 | 0.0633 | no |
| bowler | B | 221 | 5704 | 0.0000 | 0.0019 | yes | 0.0000 | 0.0000 | no |
| bowler | CONS | 221 | 5721 | 0.0038 | 0.2454 | no | 0.2628 | 0.0633 | no |

`mean_B` is the average REML data weight (0 = fully shrunk to the mean, 1 = no shrinkage). The Phase 6 gate (mean data weight >= 0.5) is reported unchanged and was not lowered or used as an input. Between-player variance over noise and ICC(1) per component:

| role | component | icc1 | icc_players | between_over_noise |
|---|---|---|---|---|
| batter | A | 0.0066 | 224 | 0.0836 |
| batter | B | 0.0053 | 224 | 0.0000 |
| batter | CONS | 0.0042 | 224 | 0.1386 |
| bowler | A | 0.0132 | 221 | 0.3630 |
| bowler | B | 0.0319 | 221 | 0.0000 |
| bowler | CONS | 0.0151 | 221 | 0.4047 |

## 4. Reliability of the PRI on held-out matches

| role | metric | n_players | r | spearman_brown | sb_low | sb_high |
|---|---|---|---|---|---|---|
| batter | parity_heldout | 221 | 0.029 | 0.057 | -0.190 | 0.300 |
| batter | time_heldout | 221 | -0.042 | -0.087 | -0.298 | 0.230 |
| batter | out_of_time_heldout | 111 | -0.020 | n/a | -0.197 | 0.166 |
| bowler | parity_heldout | 216 | 0.154 | 0.267 | -0.078 | 0.391 |
| bowler | time_heldout | 216 | 0.096 | 0.175 | -0.195 | 0.289 |
| bowler | out_of_time_heldout | 106 | 0.199 | n/a | 0.027 | 0.352 |

Out-of-time uses the Spearman correlation of TRAIN-HELD matches against VALIDATION (interval from a player bootstrap); the early window needs 4 matches and the late window 4 matches (half the full-sample floor for the early window because HELD holds about 60 % of TRAIN).

### Predeclared status

| role | indicative_list_status | reason | split_half_sb | split_half_sb_low | oot_spearman | oot_low | top10_prob_ge_0_5 | median_rank_interval_width | phase6_gate_passed |
|---|---|---|---|---|---|---|---|---|---|
| batter | EXPLORATORY | split-half 0.06 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0 | 0.057 | -0.190 | -0.020 | -0.197 | 2 | 170.525 | no |
| bowler | EXPLORATORY | split-half 0.27 below 0.5; split-half lower bound not above 0 | 0.267 | -0.078 | 0.199 | 0.027 | 5 | 165.000 | no |

### Side by side with A and B (primary intensity, all matches, same predeclared criteria)

**batters**

| approach | split_half_sb | split_half_sb_low | time_sb | oot_spearman | oot_low | icc1 | floor | top10_prob_ge_0_5 | indicative_status |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.057 | -0.220 | 0.128 | 0.199 | 0.017 | 0.006 | no | 5.000 | EXPLORATORY |
| B | 0.042 | -0.331 | -0.072 | -0.001 | -0.201 | 0.005 | yes | 1.000 | EXPLORATORY |
| C (held-out) | 0.057 | -0.190 | -0.087 | -0.020 | -0.197 | n/a | no | 2.000 | EXPLORATORY |

**bowlers**

| approach | split_half_sb | split_half_sb_low | time_sb | oot_spearman | oot_low | icc1 | floor | top10_prob_ge_0_5 | indicative_status |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.220 | -0.228 | 0.122 | 0.131 | -0.074 | 0.013 | no | 6.000 | EXPLORATORY |
| B | -0.135 | -0.465 | 0.043 | -0.176 | -0.364 | 0.032 | yes | 0.000 | EXPLORATORY |
| C (held-out) | 0.267 | -0.078 | 0.175 | 0.199 | 0.027 | n/a | no | 5.000 | EXPLORATORY |

C's split-half and out-of-time figures use only matches that were not used to fit its weights; A's and B's use all matches (their weights are fixed, not fitted). The comparison is therefore not a contest the predeclared selection rule has resolved: that rule is applied in a later step. None of the approaches meets the PROVISIONAL threshold (split-half >= 0.5 with a lower bound above 0).

## 5. Candidate Top 10 under C (EXPLORATORY; combined IPL + T20I, PRE_TEST matches)

These are the ten highest PRI values, listed so the evidence can be read, not a validated ranking. `top10_prob` is the share of 1000 match-cluster bootstrap draws (full REML refit per draw, weights fixed) in which the player is in the top ten.

**batters**

| rank | player_name | pri | pri_low | pri_high | top10_prob | rank_low | rank_high | evidence_class | n_matches | pressure_matches | z_A | z_B | z_CONS | pos_share | sample_reliability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Heinrich Klaasen | 3.43 | 2.53 | 18.75 | 0.65 | 1.00 | 62.00 | STRONG_SUBSTANTIAL | 55 | 48 | 3.27 | 0.79 | 3.43 | 0.62 | 0.21 |
| 2 | Tim David | 3.15 | 0.82 | 16.00 | 0.37 | 1.00 | 85.00 | STRONG_SUBSTANTIAL | 77 | 74 | 4.29 | 2.09 | 3.15 | 0.55 | 0.29 |
| 3 | Romario Shepherd | 2.42 | -0.02 | 14.82 | 0.28 | 1.00 | 106.02 | STRONG_LIMITED | 54 | 53 | 2.90 | -0.17 | 2.42 | 0.55 | 0.23 |
| 4 | Nicholas Pooran | 2.42 | -0.54 | 13.94 | 0.20 | 2.00 | 109.00 | STRONG_LIMITED | 99 | 70 | 2.42 | 0.78 | 2.42 | 0.53 | 0.28 |
| 5 | Tristan Stubbs | 2.37 | 0.07 | 15.48 | 0.31 | 1.00 | 103.02 | STRONG_SUBSTANTIAL | 52 | 46 | 2.55 | 0.59 | 2.37 | 0.57 | 0.21 |
| 6 | Alzarri Joseph | 2.29 | 2.45 | 18.34 | 0.59 | 1.00 | 66.00 | STRONG_SUBSTANTIAL | 20 | 20 | 0.55 | 0.78 | 2.29 | 0.70 | 0.10 |
| 7 | Akeal Hosein | 2.28 | 0.74 | 17.87 | 0.50 | 1.00 | 94.00 | STRONG_SUBSTANTIAL | 27 | 27 | 0.70 | 0.17 | 2.28 | 0.63 | 0.13 |
| 8 | Suryakumar Yadav | 2.17 | -1.09 | 12.84 | 0.15 | 3.00 | 119.05 | STRONG_LIMITED | 118 | 72 | 5.49 | 0.85 | 2.17 | 0.51 | 0.29 |
| 9 | David Miller | 2.17 | -1.93 | 13.00 | 0.17 | 3.00 | 127.00 | STRONG_LIMITED | 69 | 65 | 2.57 | 0.70 | 2.17 | 0.52 | 0.27 |
| 10 | Patrick Cummins | 2.08 | -0.52 | 16.50 | 0.34 | 1.00 | 108.02 | STRONG_LIMITED | 32 | 32 | 1.17 | 0.80 | 2.08 | 0.59 | 0.15 |

Evidence classes among eligible players: INCONSISTENT 182, STRONG_LIMITED 25, UNCLASSIFIED_LOW 12, STRONG_SUBSTANTIAL 5.

**bowlers**

| rank | player_name | pri | pri_low | pri_high | top10_prob | rank_low | rank_high | evidence_class | n_matches | pressure_matches | z_A | z_B | z_CONS | pos_share | sample_reliability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Matheesha Pathirana | 3.61 | 3.06 | 9.29 | 0.86 | 1.00 | 26.02 | STRONG_SUBSTANTIAL | 48 | 46 | 3.08 | 0.03 | 3.61 | 0.74 | 0.42 |
| 2 | Kuldeep Yadav | 3.03 | 1.81 | 7.54 | 0.56 | 1.00 | 51.02 | INCONSISTENT | 72 | 64 | 4.36 | 0.79 | 3.03 | 0.67 | 0.50 |
| 3 | Jasprit Bumrah | 2.83 | 1.50 | 7.70 | 0.56 | 1.00 | 56.02 | STRONG_SUBSTANTIAL | 53 | 51 | 4.14 | 0.81 | 2.83 | 0.67 | 0.44 |
| 4 | Varun Chakravarthy | 2.82 | 1.33 | 7.18 | 0.45 | 1.00 | 64.00 | STRONG_SUBSTANTIAL | 77 | 69 | 3.32 | 0.71 | 2.82 | 0.64 | 0.52 |
| 5 | Sunil Narine | 2.79 | 1.48 | 7.80 | 0.57 | 1.00 | 58.00 | STRONG_SUBSTANTIAL | 54 | 48 | 3.13 | 0.91 | 2.79 | 0.69 | 0.43 |
| 6 | Akeal Hosein | 2.76 | 1.48 | 7.55 | 0.54 | 1.00 | 56.00 | STRONG_SUBSTANTIAL | 61 | 47 | 1.98 | 0.23 | 2.76 | 0.68 | 0.42 |
| 7 | Rashid Khan | 2.49 | 0.99 | 6.30 | 0.27 | 2.00 | 75.00 | STRONG_SUBSTANTIAL | 93 | 88 | 2.14 | 0.67 | 2.49 | 0.60 | 0.58 |
| 8 | Mohammad Nawaz | 2.43 | 1.06 | 7.53 | 0.49 | 1.00 | 69.05 | STRONG_SUBSTANTIAL | 47 | 40 | 2.04 | 0.99 | 2.43 | 0.65 | 0.38 |
| 9 | Wanindu Hasaranga | 1.93 | -0.03 | 5.81 | 0.14 | 3.00 | 107.02 | STRONG_LIMITED | 80 | 70 | 1.78 | 0.50 | 1.93 | 0.59 | 0.52 |
| 10 | Abbas Afridi | 1.89 | 0.73 | 7.69 | 0.44 | 1.00 | 81.00 | STRONG_SUBSTANTIAL | 21 | 19 | 1.91 | -1.00 | 1.89 | 0.74 | 0.23 |

Evidence classes among eligible players: INCONSISTENT 156, UNCLASSIFIED_LOW 31, STRONG_LIMITED 24, STRONG_SUBSTANTIAL 10.

Intervals are wide: a rank interval of a player in the top ten typically runs from 1 to 25 or more (see rank_low and rank_high) of about 220. The estimate interval uses only draws in which no active component hit the floor (see section 8) and refits the between-player variance in every draw, so its upper end can be long: the PRI scale is fixed at its full-sample value and a draw with a larger variance spreads players further; ranks and Top 10 inclusion use every draw, where a floor draw uses the unshrunk mean by the predeclared rule.

## 6. Sensitivity (overlap of the Top 10 and Spearman correlation with the C order)

| role | comparison | n_common | spearman | top10_overlap | n_eligible |
|---|---|---|---|---|---|
| batter | published_approach_A_rank | 224 | 0.762 | 7 | n/a |
| batter | published_approach_B_rank | 224 | 0.307 | 1 | n/a |
| batter | component_A_only | 224 | 0.767 | 7 | n/a |
| batter | component_B_only | 224 | 0.307 | 1 | n/a |
| batter | component_CONS_only | 224 | 1.000 | 10 | n/a |
| batter | equal_weights_not_data_derived | 224 | 0.833 | 7 | n/a |
| batter | scope_IPL_only | 104 | 0.885 | 6 | n/a |
| batter | scope_T20I_only | 139 | 0.826 | 5 | n/a |
| batter | eligibility_floor_x0.5 | 224 | 0.999 | 7 | 330.000 |
| batter | eligibility_floor_x2.0 | 132 | 0.999 | 10 | 132.000 |
| batter | unshrunk_ordering | 224 | 0.953 | 3 | n/a |
| batter | innings2_units_only | 224 | 0.700 | 4 | n/a |
| bowler | published_approach_A_rank | 221 | 0.776 | 8 | n/a |
| bowler | published_approach_B_rank | 221 | 0.386 | 0 | n/a |
| bowler | component_A_only | 221 | 0.778 | 8 | n/a |
| bowler | component_B_only | 221 | 0.386 | 0 | n/a |
| bowler | component_CONS_only | 221 | 1.000 | 10 | n/a |
| bowler | equal_weights_not_data_derived | 221 | 0.851 | 8 | n/a |
| bowler | scope_IPL_only | 102 | 0.839 | 6 | n/a |
| bowler | scope_T20I_only | 154 | 0.920 | 7 | n/a |
| bowler | eligibility_floor_x0.5 | 221 | 0.998 | 10 | 321.000 |
| bowler | eligibility_floor_x2.0 | 136 | 0.999 | 10 | 136.000 |
| bowler | unshrunk_ordering | 221 | 0.967 | 2 | n/a |
| bowler | hierarchical_format_common_effect | 221 | 0.999 | 10 | n/a |
| bowler | innings2_units_only | 221 | 0.626 | 8 | n/a |

## 7. IPL and T20I combination study

Decision rule (predeclared): combine when the lower 95 % bound of the cross-format Spearman correlation is at least 0.3 and at least 30 players have both formats; otherwise the format-specific results are shown and the combination is flagged `FORMAT_COMBINATION_UNSUPPORTED`. No fixed 70:30 weighting is used anywhere.

| role | series | players_both_formats | spearman | spearman_low | spearman_high | pearson_pw | disattenuated | disattenuation_note | combination_supported |
|---|---|---|---|---|---|---|---|---|---|
| batter | PRI | 85 | -0.105 | -0.318 | 0.116 | -0.023 | n/a | NOT_ESTIMABLE_NONPOSITIVE_RELIABILITY | no |
| batter | A | 85 | 0.100 | -0.136 | 0.290 | 0.168 | n/a |  | no |
| batter | B | 85 | 0.040 | -0.168 | 0.263 | 0.045 | n/a |  | no |
| batter | CONS | 85 | -0.105 | -0.318 | 0.116 | -0.023 | n/a |  | no |
| bowler | PRI | 76 | 0.221 | -0.018 | 0.430 | 0.288 | n/a | OUT_OF_RANGE_RELIABILITY_TOO_NOISY | no |
| bowler | A | 76 | 0.064 | -0.185 | 0.300 | 0.185 | n/a |  | no |
| bowler | B | 76 | -0.174 | -0.378 | 0.061 | -0.106 | n/a |  | no |
| bowler | CONS | 76 | 0.221 | -0.018 | 0.430 | 0.288 | n/a |  | no |

Hierarchical format model per component, `y = mu_format + u_player + v_player_format + e` (REML; `tau_u2` common player effect, `tau_v2` format-specific deviation, `common_share = tau_u2/(tau_u2+tau_v2)`; a variance whose removal changes the REML deviance by less than 1e-6 is reported as 0 with a floor flag):

| role | component | status | tau_u2 | tau_v2 | sigma2 | mu_ipl | mu_t20i | common_share | floor_common | floor_format_dev |
|---|---|---|---|---|---|---|---|---|---|---|
| batter | A | ESTIMATED | 0.00031 | 0.00000 | 1.02393 | -0.00279 | -0.00287 | 1.00000 | no | yes |
| batter | B | ESTIMATED | 0.00000 | 0.00000 | 0.00253 | -0.00032 | 0.00014 | n/a | yes | yes |
| batter | CONS | ESTIMATED | 0.00000 | 0.00258 | 0.24127 | -0.07734 | -0.08687 | 0.00000 | yes | no |
| bowler | A | ESTIMATED | 0.00073 | 0.00022 | 0.69951 | -0.01143 | 0.00454 | 0.76718 | no | no |
| bowler | B | ESTIMATED | 0.00000 | 0.00000 | 0.00190 | 0.00040 | 0.00021 | n/a | yes | yes |
| bowler | CONS | ESTIMATED | 0.00396 | 0.00000 | 0.24571 | -0.04493 | -0.02153 | 1.00000 | no | yes |

The precision each format receives for a player follows from these variance components (`format_w_ipl_A`, `format_w_t20i_A` in `p8_c_estimates`) and from each player's own format counts; `ipl_precision_share` gives the observed share of a player's pressure precision that comes from the IPL.

- batters: PRI cross-format Spearman -0.11 (95 % interval -0.32 to 0.12, 85 players), so the combination is not supported under the predeclared rule (`FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`).
- bowlers: PRI cross-format Spearman 0.22 (95 % interval -0.02 to 0.43, 76 players), so the combination is not supported under the predeclared rule (`FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`).

Where the combination is unsupported the combined list is the pooled estimate with format-centred units, in which each unit is already weighted by its own precision; it is labelled as such, and the IPL-only and T20I-only candidate lists below are the format-specific results.

**batters, IPL only** (PRI within the format; same fixed weights)

| rank | player_name | pri | z_A | z_B | z_CONS | n_matches | n_units |
|---|---|---|---|---|---|---|---|
| 1 | Nicholas Pooran | 2.97 | 3.21 | 1.07 | 2.97 | 56 | 48 |
| 2 | Heinrich Klaasen | 2.75 | 2.56 | 0.60 | 2.75 | 39 | 36 |
| 3 | Tristan Stubbs | 2.28 | 2.06 | 0.34 | 2.28 | 30 | 29 |
| 4 | Mahendra Singh Dhoni | 1.56 | 1.74 | 0.64 | 1.56 | 47 | 46 |
| 5 | David Miller | 1.56 | 1.46 | 0.52 | 1.56 | 48 | 46 |
| 6 | Axar Patel | 1.53 | 0.86 | 0.39 | 1.53 | 46 | 42 |
| 7 | Tim David | 1.53 | 2.24 | 2.24 | 1.53 | 42 | 42 |
| 8 | Shimron Hetmyer | 1.43 | 0.84 | 0.74 | 1.43 | 50 | 49 |
| 9 | Patrick Cummins | 1.38 | 1.06 | 1.55 | 1.38 | 24 | 24 |
| 10 | Trent Boult | 1.29 | -0.06 | -2.20 | 1.29 | 16 | 16 |

**batters, T20I only** (PRI within the format; same fixed weights)

| rank | player_name | pri | z_A | z_B | z_CONS | n_matches | n_units |
|---|---|---|---|---|---|---|---|
| 1 | Romario Shepherd | 2.58 | 1.37 | -0.22 | 2.58 | 42 | 41 |
| 2 | Akeal Hosein | 2.34 | 0.91 | 0.11 | 2.34 | 26 | 26 |
| 3 | Tim David | 2.09 | 1.56 | 1.82 | 2.09 | 35 | 32 |
| 4 | Matthew Wade | 2.08 | 1.83 | 1.63 | 2.08 | 18 | 18 |
| 5 | Alzarri Joseph | 2.01 | 1.40 | 1.88 | 2.01 | 16 | 16 |
| 6 | Suryakumar Yadav | 1.90 | 1.89 | 1.44 | 1.90 | 67 | 33 |
| 7 | Rinku Singh | 1.76 | 1.40 | 0.51 | 1.76 | 24 | 22 |
| 8 | Shivam Dube | 1.75 | 1.33 | 0.98 | 1.75 | 18 | 15 |
| 9 | Mohammad Nawaz | 1.72 | 0.33 | 0.77 | 1.72 | 42 | 41 |
| 10 | Aiden Markram | 1.68 | 1.46 | 0.96 | 1.68 | 27 | 13 |

**bowlers, IPL only** (PRI within the format; same fixed weights)

| rank | player_name | pri | z_A | z_B | z_CONS | n_matches | n_units |
|---|---|---|---|---|---|---|---|
| 1 | Sunil Narine | 3.41 | 3.11 | 1.04 | 3.41 | 54 | 48 |
| 2 | Matheesha Pathirana | 3.25 | 2.65 | 0.39 | 3.25 | 32 | 31 |
| 3 | Jasprit Bumrah | 2.87 | 3.57 | 1.23 | 2.87 | 38 | 37 |
| 4 | Kuldeep Yadav | 2.52 | 2.58 | 0.86 | 2.52 | 53 | 47 |
| 5 | Rashid Khan | 1.66 | 0.27 | 0.79 | 1.66 | 59 | 54 |
| 6 | Sai Kishore | 1.65 | 1.00 | 0.33 | 1.65 | 25 | 19 |
| 7 | Prasidh Krishna | 1.52 | 1.20 | -0.46 | 1.52 | 32 | 30 |
| 8 | Harshit Rana | 1.29 | 0.24 | 0.15 | 1.29 | 32 | 25 |
| 9 | Varun Chakravarthy | 1.24 | 2.10 | 0.37 | 1.24 | 52 | 44 |
| 10 | Naveen ul Haq | 1.02 | 1.23 | 0.71 | 1.02 | 17 | 16 |

**bowlers, T20I only** (PRI within the format; same fixed weights)

| rank | player_name | pri | z_A | z_B | z_CONS | n_matches | n_units |
|---|---|---|---|---|---|---|---|
| 1 | Varun Chakravarthy | 2.94 | 2.45 | 2.10 | 2.94 | 25 | 25 |
| 2 | Akeal Hosein | 2.53 | 1.88 | 0.14 | 2.53 | 60 | 46 |
| 3 | Mohammad Nawaz | 2.37 | 1.98 | 1.88 | 2.37 | 47 | 40 |
| 4 | Wanindu Hasaranga | 2.37 | 1.94 | 2.10 | 2.37 | 45 | 40 |
| 5 | Rashid Khan | 2.18 | 2.82 | 1.28 | 2.18 | 34 | 34 |
| 6 | Nathan Ellis | 2.09 | 0.84 | -1.15 | 2.09 | 23 | 22 |
| 7 | Kuldeep Yadav | 2.01 | 3.68 | 0.94 | 2.01 | 19 | 17 |
| 8 | Abbas Afridi | 1.97 | 2.02 | -1.12 | 1.97 | 21 | 19 |
| 9 | Abrar Ahmed | 1.81 | 2.37 | 0.44 | 1.81 | 28 | 27 |
| 10 | Craig Young | 1.78 | 1.40 | 1.51 | 1.78 | 21 | 18 |

## 8. Bootstrap check

| role | draws | players | mean_draws_present | interval_draws | floor_draw_share | weights_fixed_from |
|---|---|---|---|---|---|---|
| batter | 1000 | 224 | 999.978 | 1000 | {"CONS": 0.0} | FIT matches (TRAIN odd parity) |
| bowler | 1000 | 221 | 999.959 | 1000 | {"CONS": 0.0} | FIT matches (TRAIN odd parity) |

## 9. What this does and does not show

- Components with a non-zero weight after the data-derived rule: batters ['CONS'], bowlers ['CONS']. The others have no between-player signal (REML floor) or a non-positive reliability on the FIT matches. Where only CONS is active the index is close to a ranking by how often a player's pressure units beat expectation.
- Held-out parity reliability: batters 0.06 (lower bound -0.19), bowlers 0.27 (lower bound -0.08). Rank intervals span most of the cohort. No list meets the PROVISIONAL criteria; both are EXPLORATORY.
- The IPL and T20I estimates do not agree well enough to support a combined estimate under the predeclared rule.
- CONS counts a unit as positive whatever its size, so it is not independent of the A residual, and the A residual is itself small relative to ball-level noise. Players with few pressure units can reach the top by a short run of positive units (the `STRONG_LIMITED` class marks them).
- Weights come from FIT only (about 40 % of TRAIN matches), so they use less data than the full-sample estimates; this was chosen so the held-out numbers are not optimistic.
- No test-period (2026) data was used.
