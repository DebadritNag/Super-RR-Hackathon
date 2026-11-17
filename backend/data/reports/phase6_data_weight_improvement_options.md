# Phase 6 data-weight improvement options

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, in-sample on TRAIN and VALIDATION. TEST outcomes: not used. Cricsheet: not used. **The data-weight gate is `GATE_B` = 0.5 in every row (`gate_used`); it was not lowered, bypassed, re-defined or tuned, and no option below changes it.** No gate state is written: `passes_gate` is informational, and every context that fails stays restricted. Code version `0061c9d62abd2c99`, seed 20260512, 1000 match resamples, 300 REML bootstrap draws. Step run-log seq 93 (criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` verified).

## 1. How to read this
- Data weight is `B = n_eff / (n_eff + k)` of the marginal (least-experienced) eligible individual; the gate needs `B >= 0.5`. On the Phase 4 basis (`KISH_MATCH`) `n_eff` is the Kish count over per-match ball counts and `k = 25` (the shrinkage floor under `shrink_tau4`); B = 0.5 iff `n_eff = k`. On the match-cluster basis (`MATCH_CLUSTER`) `B_i = tau2 / (tau2 + v_i)` with `v_i` the cluster-robust noise variance of the individual's mean; this equals `n_eff_cluster / (n_eff_cluster + k)` with `k = sigma_eff / tau2`. The two bases are never mixed (the validator rejects it).
- `ACTUAL_RE_ESTIMATE`: recomputed from the data under the stated change. `DESCRIPTIVE_PROJECTION`: arithmetic on the observed numbers, not a re-fit.
- Options marked `requires_methodology_decision` change the shrinkage methodology (a data-based `tau2` instead of the floor). A pass under them would still leave the context restricted until the user approves a methodology change. This report changes nothing.
- Everything is in-sample; the match-cluster bootstrap is shifted upward relative to the point estimate (see the variance report), so interval bounds are rough bands.

## 2. Excluded by rule (not options, not in the table)
- lowering the 0.5 gate or changing the 0.5 requirement
- a larger tau multiplier (shrink_tau0.5, shrink_tau2, shrink_tau4 are assumption-driven)
- lowering the frozen eligibility thresholds
- using TEST outcomes
- padding a pool to reach the minimum size

## 3. Summary per option

| option | group | label | scope | rows | with estimate | pass 0.5 | pass on estimable subset | marginal not estimable | best B | median B | needs decision | basis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1_any_q0.75 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.12 | 0.06 | no | KISH_MATCH |
| O1_any_q0.9 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.16 | 0.07 | no | KISH_MATCH |
| O1_any_q0.95 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.19 | 0.10 | no | KISH_MATCH |
| O1_chase_q0.75 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.14 | 0.06 | no | KISH_MATCH |
| O1_chase_q0.9 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.16 | 0.07 | no | KISH_MATCH |
| O1_chase_q0.95 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.24 | 0.14 | no | KISH_MATCH |
| O1_inn1_q0.75 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.10 | 0.06 | no | KISH_MATCH |
| O1_inn1_q0.9 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 4 | 0 | 0 | 0 | 0.13 | 0.07 | no | KISH_MATCH |
| O1_inn1_q0.95 | definition choice | ACTUAL_RE_ESTIMATE | cell | 4 | 3 | 0 | 0 | 0 | 0.10 | 0.04 | no | KISH_MATCH |
| O2_multi_format_pooling | multi-format pooling | ACTUAL_RE_ESTIMATE | role | 2 | 2 | 0 | 0 | 0 | 0.13 | 0.11 | no | KISH_MATCH |
| O3_phases_pooled | partial pooling across contexts | ACTUAL_RE_ESTIMATE | context | 36 | 36 | 0 | 0 | 30 | 0.45 | 0.17 | yes | MATCH_CLUSTER |
| O3_situations_pooled | partial pooling across contexts | ACTUAL_RE_ESTIMATE | context | 32 | 32 | 0 | 0 | 27 | 0.47 | 0.20 | yes | MATCH_CLUSTER |
| O4_window_train_to_pre_test | longer window | ACTUAL_RE_ESTIMATE | context | 48 | 48 | 0 | 0 | 0 | 0.12 | 0.04 | no | KISH_MATCH |
| O5_bowler_death_close_gap | bowler-specific signal (sensitivity) | ACTUAL_RE_ESTIMATE | cell | 2 | 2 | 0 | 0 | 0 | 0.31 | 0.22 | no | KISH_MATCH |
| O5_bowler_death_wickets_in_hand | bowler-specific signal (sensitivity) | ACTUAL_RE_ESTIMATE | cell | 2 | 2 | 0 | 0 | 0 | 0.22 | 0.18 | no | KISH_MATCH |
| O5_bowler_defence_margin | bowler-specific signal (sensitivity) | ACTUAL_RE_ESTIMATE | cell | 2 | 2 | 0 | 0 | 0 | 0.15 | 0.11 | no | KISH_MATCH |
| O6_match_cluster_own_tau2 | match-cluster tau2 | ACTUAL_RE_ESTIMATE | context | 48 | 48 | 0 | 1 | 36 | 0.56 | 0.21 | yes | MATCH_CLUSTER |
| O7_required_sample_projection | required sample | DESCRIPTIVE_PROJECTION | context | 48 | 48 | 0 | 0 | 0 | 0.12 | 0.04 | no | KISH_MATCH |
| O8_pool_restriction_cost | pool restriction | DESCRIPTIVE_PROJECTION | context | 48 | 3 | 0 | 0 | 0 | 0.54 | 0.53 | no | KISH_MATCH |


Scopes that pass the gate under each option (informational):

- `O1_any_q0.75`: none
- `O1_any_q0.9`: none
- `O1_any_q0.95`: none
- `O1_chase_q0.75`: none
- `O1_chase_q0.9`: none
- `O1_chase_q0.95`: none
- `O1_inn1_q0.75`: none
- `O1_inn1_q0.9`: none
- `O1_inn1_q0.95`: none
- `O2_multi_format_pooling`: none
- `O3_phases_pooled`: none
- `O3_situations_pooled`: none
- `O4_window_train_to_pre_test`: none
- `O5_bowler_death_close_gap`: none
- `O5_bowler_death_wickets_in_hand`: none
- `O5_bowler_defence_margin`: none
- `O6_match_cluster_own_tau2`: none
- `O7_required_sample_projection`: none
- `O8_pool_restriction_cost`: none

## 4. Context-level view (48 contexts): data weight of the marginal eligible individual
`stored` is the Phase 5 state (Phase 4 basis, floor `k`). O3 and O6 use the match-cluster basis. O4's comparison column is the TRAIN-only window. O8 is the number of eligible individuals left if the pool were restricted to `n_eff >= k`; it is not applicable.

| format | role | phase | situation | stored B | O3 phases | O3 situations | O6 own | O4 TRAIN-only B | O7 extra matches | O8 pool left |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 0.06 | n/a | n/a | 0.27 | 0.04 | 30.72 | 0 |
| IPL | batter | ALL | chase | 0.04 | n/a | 0.26 | 0.29 | 0.04 | 24.00 | 0 |
| IPL | batter | ALL | first_innings | 0.04 | n/a | 0.46 | 0.41 | 0.04 | 24.00 | 0 |
| IPL | batter | death | ALL | 0.04 | 0.17 | n/a | 0.21 | 0.04 | 24.00 | 0 |
| IPL | batter | death | chase | 0.04 | 0.21 | 0.21 | 0.22 | 0.04 | 24.00 | 0 |
| IPL | batter | death | first_innings | 0.04 | 0.21 | 0.28 | 0.29 | 0.04 | 24.00 | 0 |
| IPL | batter | middle | ALL | 0.04 | 0.24 | n/a | 0.14 | 0.04 | 24.00 | 0 |
| IPL | batter | middle | chase | 0.04 | 0.45 | 0.26 | 0.31 | 0.04 | 24.00 | 0 |
| IPL | batter | middle | first_innings | 0.04 | 0.32 | 0.23 | 0.17 | 0.04 | 24.00 | 0 |
| IPL | batter | powerplay | ALL | 0.04 | 0.27 | n/a | 0.23 | 0.04 | 24.00 | 0 |
| IPL | batter | powerplay | chase | 0.04 | 0.29 | 0.21 | 0.34 | 0.04 | 24.00 | 0 |
| IPL | batter | powerplay | first_innings | 0.04 | 0.14 | 0.13 | 0.19 | 0.04 | 24.00 | 0 |
| IPL | bowler | ALL | ALL | 0.12 | n/a | n/a | 0.26 | 0.10 | 31.39 | 1 |
| IPL | bowler | ALL | chase | 0.07 | n/a | 0.15 | 0.25 | 0.05 | 23.91 | 0 |
| IPL | bowler | ALL | first_innings | 0.07 | n/a | 0.25 | 0.21 | 0.05 | 24.00 | 0 |
| IPL | bowler | death | ALL | 0.09 | 0.13 | n/a | 0.20 | 0.07 | 25.86 | 0 |
| IPL | bowler | death | chase | 0.07 | 0.16 | 0.15 | 0.17 | 0.07 | 24.42 | 0 |
| IPL | bowler | death | first_innings | 0.04 | 0.10 | 0.19 | 0.31 | 0.04 | 24.00 | 0 |
| IPL | bowler | middle | ALL | 0.10 | 0.13 | n/a | 0.13 | 0.06 | 31.38 | 0 |
| IPL | bowler | middle | chase | 0.04 | 0.13 | 0.08 | 0.13 | 0.04 | 24.00 | 0 |
| IPL | bowler | middle | first_innings | 0.04 | 0.14 | 0.17 | 0.17 | 0.04 | 24.00 | 0 |
| IPL | bowler | powerplay | ALL | 0.04 | 0.14 | n/a | 0.46 | 0.04 | 24.00 | 0 |
| IPL | bowler | powerplay | chase | 0.04 | 0.19 | 0.40 | 0.22 | 0.04 | 24.00 | 0 |
| IPL | bowler | powerplay | first_innings | 0.04 | 0.07 | 0.32 | 0.20 | 0.04 | 24.00 | 0 |
| T20I | batter | ALL | ALL | 0.04 | n/a | n/a | 0.28 | 0.04 | 24.00 | 0 |
| T20I | batter | ALL | chase | 0.04 | n/a | 0.19 | 0.25 | 0.04 | 24.00 | 0 |
| T20I | batter | ALL | first_innings | 0.04 | n/a | 0.22 | 0.18 | 0.04 | 24.00 | 0 |
| T20I | batter | death | ALL | 0.04 | 0.22 | n/a | 0.32 | 0.04 | 24.00 | 0 |
| T20I | batter | death | chase | 0.04 | 0.06 | 0.06 | 0.09 | 0.04 | 24.00 | 0 |
| T20I | batter | death | first_innings | 0.04 | 0.24 | 0.41 | 0.33 | 0.04 | 24.00 | 0 |
| T20I | batter | middle | ALL | 0.04 | 0.15 | n/a | 0.13 | 0.04 | 24.00 | 0 |
| T20I | batter | middle | chase | 0.04 | 0.21 | 0.13 | 0.19 | 0.04 | 24.00 | 0 |
| T20I | batter | middle | first_innings | 0.04 | 0.18 | 0.20 | 0.15 | 0.04 | 24.00 | 0 |
| T20I | batter | powerplay | ALL | 0.04 | 0.07 | n/a | 0.14 | 0.04 | 24.00 | 0 |
| T20I | batter | powerplay | chase | 0.04 | 0.10 | 0.14 | 0.27 | 0.04 | 24.00 | 0 |
| T20I | batter | powerplay | first_innings | 0.04 | 0.13 | 0.30 | 0.13 | 0.04 | 24.00 | 0 |
| T20I | bowler | ALL | ALL | 0.07 | n/a | n/a | 0.34 | 0.05 | 23.83 | 1 |
| T20I | bowler | ALL | chase | 0.04 | n/a | 0.23 | 0.28 | 0.04 | 24.00 | 0 |
| T20I | bowler | ALL | first_innings | 0.04 | n/a | 0.19 | 0.09 | 0.04 | 44.56 | 0 |
| T20I | bowler | death | ALL | 0.07 | 0.23 | n/a | 0.20 | 0.04 | 23.04 | 1 |
| T20I | bowler | death | chase | 0.04 | 0.19 | 0.13 | 0.14 | 0.04 | 24.00 | 0 |
| T20I | bowler | death | first_innings | 0.05 | 0.04 | 0.08 | 0.06 | 0.04 | 39.00 | 0 |
| T20I | bowler | middle | ALL | 0.06 | 0.32 | n/a | 0.28 | 0.04 | 30.52 | 0 |
| T20I | bowler | middle | chase | 0.04 | 0.25 | 0.17 | 0.23 | 0.04 | 24.00 | 0 |
| T20I | bowler | middle | first_innings | 0.04 | 0.12 | 0.20 | 0.11 | 0.04 | 24.00 | 0 |
| T20I | bowler | powerplay | ALL | 0.04 | 0.13 | n/a | 0.28 | 0.04 | 24.00 | 0 |
| T20I | bowler | powerplay | chase | 0.04 | 0.31 | 0.47 | 0.56 | 0.04 | 24.00 | 0 |
| T20I | bowler | powerplay | first_innings | 0.04 | 0.06 | 0.30 | 0.19 | 0.04 | 24.00 | 0 |


## 5. Cell-level options (definition, multi-format pooling, bowler signals)

| option | scope | marginal n_eff | k | B | baseline B | passes | eligible | extra matches |
|---|---|---|---|---|---|---|---|---|
| O1_any_q0.75 | cell:IPL\|batter | 1.53 | 25.00 | 0.06 | 0.06 | no | 132 | 30.72 |
| O1_any_q0.75 | cell:IPL\|bowler | 3.44 | 25.00 | 0.12 | 0.12 | no | 80 | 31.39 |
| O1_any_q0.75 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 243 | 24.00 |
| O1_any_q0.75 | cell:T20I\|bowler | 1.94 | 25.00 | 0.07 | 0.07 | no | 141 | 23.83 |
| O1_any_q0.9 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 81 | 24.00 |
| O1_any_q0.9 | cell:IPL\|bowler | 4.63 | 25.00 | 0.16 | 0.12 | no | 38 | 30.80 |
| O1_any_q0.9 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 117 | 24.00 |
| O1_any_q0.9 | cell:T20I\|bowler | 2.56 | 25.00 | 0.09 | 0.07 | no | 68 | 35.04 |
| O1_any_q0.95 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 37 | 24.00 |
| O1_any_q0.95 | cell:IPL\|bowler | 5.91 | 25.00 | 0.19 | 0.12 | no | 7 | 29.09 |
| O1_any_q0.95 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 54 | 24.00 |
| O1_any_q0.95 | cell:T20I\|bowler | 4.62 | 25.00 | 0.16 | 0.07 | no | 20 | 22.03 |
| O1_chase_q0.75 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 94 | 24.00 |
| O1_chase_q0.75 | cell:IPL\|bowler | 3.97 | 25.00 | 0.14 | 0.12 | no | 48 | 26.46 |
| O1_chase_q0.75 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 144 | 24.00 |
| O1_chase_q0.75 | cell:T20I\|bowler | 1.99 | 25.00 | 0.07 | 0.07 | no | 85 | 23.17 |
| O1_chase_q0.9 | cell:IPL\|batter | 1.07 | 25.00 | 0.04 | 0.06 | no | 35 | 44.56 |
| O1_chase_q0.9 | cell:IPL\|bowler | 4.82 | 25.00 | 0.16 | 0.12 | no | 14 | 29.33 |
| O1_chase_q0.9 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 50 | 24.00 |
| O1_chase_q0.9 | cell:T20I\|bowler | 2.82 | 25.00 | 0.10 | 0.07 | no | 24 | 23.62 |
| O1_chase_q0.95 | cell:IPL\|batter | 3.20 | 25.00 | 0.11 | 0.06 | no | 9 | 47.73 |
| O1_chase_q0.95 | cell:IPL\|bowler | 7.94 | 25.00 | 0.24 | 0.12 | no | 2 | 19.35 |
| O1_chase_q0.95 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 19 | 24.00 |
| O1_chase_q0.95 | cell:T20I\|bowler | 4.66 | 25.00 | 0.16 | 0.07 | no | 6 | 26.18 |
| O1_inn1_q0.75 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 87 | 24.00 |
| O1_inn1_q0.75 | cell:IPL\|bowler | 2.92 | 25.00 | 0.10 | 0.12 | no | 47 | 37.81 |
| O1_inn1_q0.75 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 136 | 24.00 |
| O1_inn1_q0.75 | cell:T20I\|bowler | 2.40 | 25.00 | 0.09 | 0.07 | no | 79 | 37.63 |
| O1_inn1_q0.9 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 40 | 24.00 |
| O1_inn1_q0.9 | cell:IPL\|bowler | 3.79 | 25.00 | 0.13 | 0.12 | no | 7 | 22.40 |
| O1_inn1_q0.9 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 54 | 24.00 |
| O1_inn1_q0.9 | cell:T20I\|bowler | 2.66 | 25.00 | 0.10 | 0.07 | no | 25 | 25.14 |
| O1_inn1_q0.95 | cell:IPL\|batter | 1.00 | 25.00 | 0.04 | 0.06 | no | 16 | 24.00 |
| O1_inn1_q0.95 | cell:IPL\|bowler | n/a | 25.00 | n/a | 0.12 | no | 0 | n/a |
| O1_inn1_q0.95 | cell:T20I\|batter | 1.00 | 25.00 | 0.04 | 0.04 | no | 25 | 24.00 |
| O1_inn1_q0.95 | cell:T20I\|bowler | 2.85 | 25.00 | 0.10 | 0.07 | no | 8 | 31.03 |
| O2_multi_format_pooling | role:batter | 2.19 | 25.00 | 0.08 | 0.04 | no | 108 | 31.23 |
| O2_multi_format_pooling | role:bowler | 3.72 | 25.00 | 0.13 | 0.04 | no | 86 | 28.63 |
| O5_bowler_death_close_gap | cell:IPL\|bowler | 11.13 | 25.00 | 0.31 | n/a | no | 1 | 18.70 |
| O5_bowler_death_close_gap | cell:T20I\|bowler | 3.84 | 25.00 | 0.13 | n/a | no | 5 | 27.55 |
| O5_bowler_death_wickets_in_hand | cell:IPL\|bowler | 7.20 | 25.00 | 0.22 | n/a | no | 41 | 24.72 |
| O5_bowler_death_wickets_in_hand | cell:T20I\|bowler | 3.64 | 25.00 | 0.13 | n/a | no | 55 | 23.50 |
| O5_bowler_defence_margin | cell:IPL\|bowler | 4.28 | 25.00 | 0.15 | n/a | no | 81 | 24.17 |
| O5_bowler_defence_margin | cell:T20I\|bowler | 1.98 | 25.00 | 0.07 | n/a | no | 166 | 23.28 |


## 6. Match-cluster `tau2` per context (REML, with bootstrap and a robust MAD check)

| format | role | phase | situation | players | sigma_eff | tau2 REML | lo | hi | share positive | tau2 MAD |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 215 | 2.83 | 0.22 | 0.22 | 0.38 | 1.00 | 0.11 |
| IPL | batter | ALL | chase | 169 | 2.77 | 0.26 | 0.29 | 0.47 | 1.00 | 0.28 |
| IPL | batter | ALL | first_innings | 147 | 2.12 | 0.18 | 0.17 | 0.34 | 1.00 | 0.06 |
| IPL | batter | powerplay | ALL | 66 | 3.29 | 0.17 | 0.18 | 0.50 | 1.00 | 0.05 |
| IPL | batter | powerplay | chase | 25 | 4.44 | 0.33 | 0.11 | 0.60 | 1.00 | 0.05 |
| IPL | batter | powerplay | first_innings | 55 | 2.76 | 0.27 | 0.27 | 0.74 | 1.00 | 0.17 |
| IPL | batter | middle | ALL | 132 | 2.91 | 0.11 | 0.13 | 0.25 | 1.00 | 0.04 |
| IPL | batter | middle | chase | 93 | 2.58 | 0.15 | 0.15 | 0.32 | 1.00 | 0.00111 |
| IPL | batter | middle | first_innings | 90 | 1.93 | 0.08 | 0.08 | 0.30 | 1.00 | 0.00 |
| IPL | batter | death | ALL | 162 | 2.98 | 0.27 | 0.28 | 0.44 | 1.00 | 0.28 |
| IPL | batter | death | chase | 128 | 2.92 | 0.29 | 0.33 | 0.55 | 1.00 | 0.24 |
| IPL | batter | death | first_innings | 89 | 2.67 | 0.29 | 0.23 | 0.46 | 1.00 | 0.06 |
| IPL | bowler | ALL | ALL | 149 | 3.92 | 0.06 | 0.07 | 0.33 | 1.00 | 0.00764 |
| IPL | bowler | ALL | chase | 115 | 4.29 | 0.11 | 0.11 | 0.38 | 1.00 | 0.00 |
| IPL | bowler | ALL | first_innings | 115 | 3.13 | 0.05 | 0.06 | 0.38 | 1.00 | 0.00 |
| IPL | bowler | powerplay | ALL | 69 | 3.32 | 0.33 | 0.16 | 0.89 | 1.00 | 0.00 |
| IPL | bowler | powerplay | chase | 16 | 5.42 | 0.14 | 0.03 | 1.03 | 0.98 | 0.00 |
| IPL | bowler | powerplay | first_innings | 57 | 3.10 | 0.17 | 0.17 | 1.00 | 1.00 | 0.00 |
| IPL | bowler | middle | ALL | 118 | 3.26 | 0.06 | 0.09 | 0.42 | 1.00 | 0.00 |
| IPL | bowler | middle | chase | 89 | 3.69 | 0.11 | 0.15 | 0.60 | 1.00 | 0.00 |
| IPL | bowler | middle | first_innings | 85 | 2.39 | 0.06 | 0.07 | 0.23 | 1.00 | 0.00811 |
| IPL | bowler | death | ALL | 102 | 4.76 | 0.10 | 0.12 | 0.43 | 1.00 | 0.00 |
| IPL | bowler | death | chase | 85 | 4.88 | 0.12 | 0.15 | 0.36 | 1.00 | 0.00 |
| IPL | bowler | death | first_innings | 69 | 3.88 | 0.19 | 0.14 | 0.62 | 1.00 | 0.00 |
| T20I | batter | ALL | ALL | 388 | 2.50 | 0.17 | 0.19 | 0.32 | 1.00 | 0.07 |
| T20I | batter | ALL | chase | 264 | 2.66 | 0.24 | 0.27 | 0.42 | 1.00 | 0.18 |
| T20I | batter | ALL | first_innings | 225 | 2.16 | 0.13 | 0.15 | 0.37 | 1.00 | 0.00 |
| T20I | batter | powerplay | ALL | 96 | 3.50 | 0.34 | 0.21 | 0.81 | 1.00 | 0.00 |
| T20I | batter | powerplay | chase | 33 | 4.50 | 0.78 | 0.23 | 1.53 | 1.00 | 0.14 |
| T20I | batter | powerplay | first_innings | 64 | 3.14 | 0.12 | 0.14 | 0.93 | 1.00 | 0.00 |
| T20I | batter | middle | ALL | 232 | 2.38 | 0.14 | 0.16 | 0.32 | 1.00 | 0.06 |
| T20I | batter | middle | chase | 146 | 2.90 | 0.22 | 0.22 | 0.43 | 1.00 | 0.02 |
| T20I | batter | middle | first_innings | 133 | 2.01 | 0.10 | 0.10 | 0.40 | 1.00 | 0.000288 |
| T20I | batter | death | ALL | 273 | 2.27 | 0.27 | 0.26 | 0.44 | 1.00 | 0.19 |
| T20I | batter | death | chase | 182 | 2.14 | 0.42 | 0.37 | 0.62 | 1.00 | 0.28 |
| T20I | batter | death | first_innings | 135 | 1.99 | 0.19 | 0.20 | 0.37 | 1.00 | 0.09 |
| T20I | bowler | ALL | ALL | 269 | 3.07 | 0.13 | 0.10 | 0.25 | 1.00 | 0.00 |
| T20I | bowler | ALL | chase | 167 | 3.42 | 0.16 | 0.13 | 0.31 | 1.00 | 0.00 |
| T20I | bowler | ALL | first_innings | 182 | 2.87 | 0.05 | 0.09 | 0.37 | 1.00 | 0.00 |
| T20I | bowler | powerplay | ALL | 81 | 3.02 | 0.33 | 0.22 | 0.66 | 1.00 | 0.00952 |
| T20I | bowler | powerplay | chase | 27 | 3.58 | 0.48 | 0.14 | 1.20 | 1.00 | 0.00 |
| T20I | bowler | powerplay | first_innings | 55 | 3.06 | 0.19 | 0.17 | 0.96 | 1.00 | 0.00 |
| T20I | bowler | middle | ALL | 196 | 2.74 | 0.10 | 0.11 | 0.23 | 1.00 | 0.00 |
| T20I | bowler | middle | chase | 104 | 2.81 | 0.15 | 0.15 | 0.49 | 1.00 | 0.00 |
| T20I | bowler | middle | first_innings | 119 | 2.67 | 0.05 | 0.08 | 0.24 | 1.00 | 0.00 |
| T20I | bowler | death | ALL | 185 | 3.38 | 0.10 | 0.12 | 0.27 | 1.00 | 0.00 |
| T20I | bowler | death | chase | 124 | 3.68 | 0.12 | 0.18 | 0.44 | 1.00 | 0.00 |
| T20I | bowler | death | first_innings | 110 | 3.38 | 0.08 | 0.11 | 0.50 | 1.00 | 4.19e-05 |


## 7. Reading the numbers
- Stored Phase 5 state: 0 of 48 contexts pass the gate (marginal n_eff 1.00 to 3.44, k = 25 to 25).
- Rows passing the gate across all options except the pool-restriction cost (O8): 0 of 256. By option: O1_any_q0.75 0, O1_any_q0.9 0, O1_any_q0.95 0, O1_chase_q0.75 0, O1_chase_q0.9 0, O1_chase_q0.95 0, O1_inn1_q0.75 0, O1_inn1_q0.9 0, O1_inn1_q0.95 0, O2_multi_format_pooling 0, O3_phases_pooled 0, O3_situations_pooled 0, O4_window_train_to_pre_test 0, O5_bowler_death_close_gap 0, O5_bowler_death_wickets_in_hand 0, O5_bowler_defence_margin 0, O6_match_cluster_own_tau2 0, O7_required_sample_projection 0.
- O8 (restrict to n_eff >= k): pools left per context range 0 to 1; 0 contexts keep at least 5 individuals. It passes only by removing nearly everyone, so it is not an option.
- Under the Phase 4 basis the gate is a statement about the least-experienced eligible individual having about k = 25 matches' worth of pressure data (n_eff = k). The largest Kish count of any individual in the 48 contexts is 28.9.
- Under the match-cluster basis (O3, O6) the best marginal data weight of any context is 0.562 (O3 and O6 rows with an estimate: 116); 0 of those rows rest on a `tau2` that is zero. 1 O3/O6 rows would pass on the individuals that have a cluster-noise estimate, but 93 rows have eligible individuals with a single match and no such estimate, so the marginal individual is not estimable and they are not counted as passing.
- Robustness of the match-cluster `tau2`: in 24 of 48 contexts the REML estimate is positive while the MAD-based estimate is 0, and the REML bootstrap lower bound is 0 in 0. The `tau2` behind O3 and O6 is therefore not firmly identified (see the variance report), so even a pass would be fragile.

## 8. Limits and open decisions
- No option lowers the gate; none was evaluated. Where no row passes, the finding is that the gate is not reachable by these legitimate means with the data in hand.
- O3 and O6 need a methodology decision (a data-based `tau2` and the match-cluster basis instead of the floor). That decision is the user's; this report does not make it.
- O3 borrows `tau2` from a parent context (phases pooled or situations pooled) and assumes the same between-player variance in the member context. It is an empirical-Bayes hyperparameter pooling, not a full hierarchical model.
- The extra matches in O7 are per marginal individual, not data to be collected for the context; they show the size of the gap.
- A match-cluster `tau2` of zero gives `B = 0` and no finite `k`; this is reported, not repaired.
- In-sample only: TEST was opened once in Phase 4 and is not pristine; nothing here is validation.
