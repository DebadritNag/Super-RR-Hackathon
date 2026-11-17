# Phase 5 investigation: why signal-to-noise is at or below zero

Status: EXPERIMENTAL_NOT_VALIDATED. PROVISIONAL and descriptive. Not an official ranking, no ML model, nothing here is validated. TEST outcomes: not used. Cricsheet: not used.

Primary definition `any|q0.75` is PROVISIONAL: the Phase 4 rule winner among nine candidates, not shown valid or superior. Alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75` are kept as sensitivity runs. Data: TRAIN and VALIDATION (pre-test) rows only, baseline B0 fitted on TRAIN, match-cluster bootstrap with 1000 draws, seed 20260512. Code version `0061c9d62abd2c99`.

## 0. Preconditions checked before any number below was computed
- Phase 4 scores reproduced from the unchanged code: max abs difference 0.00e+00 over 1345 players (tolerance 1e-9, reproduces = True).
- Phase 4 SNR (TRAIN, `any|q0.75`) reproduced from the stored definition table: max abs difference 2.22e-16 (reproduces = True).

## 1. Finding in one paragraph
On the Phase 4 noise basis the between-player variance is not positive in 4 of 4 cells (SNR -0.74 to -0.65), which reproduces the Phase 4 finding. That estimator divides a per-ball residual variance by a Kish count of equally sized MATCHES, so its noise term is larger than the sampling variance of a player mean by roughly the number of pressure balls per match. With the noise estimated as independent balls the estimate is positive in 4 of 4 cells and with match-cluster noise in 4 of 4. Those two bases bracket the truth (independent balls understate noise when balls inside a match are dependent, the cluster estimator is biased low with few matches per player), so the data cannot pin the size of tau2.

A model-free check agrees that some between-player signal exists: odd/even split-half reliability on the full pre-test window is estimable in 4 of 4 cells, with Spearman-Brown values from 0.25 to 0.42 (intervals in section 3). These are modest, and the intervals of several cells reach or cross zero. The statement 'signal-to-noise is at or below zero' is therefore mainly a property of the Phase 4 noise estimator, not proof that players do not differ under pressure. It is also not proof that the ranking is reliable. This is an open issue for review: the Phase 4 estimator is NOT changed here (methodology is not locked).

## 2. Variance decomposition of the primary definition (TRAIN window, primary streams)
tau2 is the estimated between-player variance of the mean residual, noise is the mean sampling variance of a player mean, SNR = tau2 / noise, ICC = max(tau2, 0) / (max(tau2, 0) + noise). The Phase 4 basis reproduces the Phase 4 figure. The other bases change only how the sampling noise of a player mean is estimated. 'share tau2>0' is the share of match-bootstrap draws with a positive estimate.

| format | role | noise basis | players | tau2 | tau2 boot lo | tau2 boot hi | noise | SNR | ICC | REML tau2 | share tau2>0 | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | Phase 4 (sigma2 / n_eff_kish) | 244 | -1.08 | -0.93 | -0.61 | 1.51 | -0.72 | 0.00 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | batter | independent balls (sigma2 / n) | 244 | 0.04 | 0.06 | 0.27 | 0.38 | 0.11 | 0.10 | 0.07 | 1.00 | ESTIMATED |
| IPL | batter | match-cluster robust | 193 | 0.22 | 0.25 | 0.49 | 0.10 | 2.16 | 0.68 | 0.19 | 1.00 | ESTIMATED |
| IPL | batter | split-half covariance | 193 | 0.23 | 0.07 | 0.27 | 0.30 | 0.75 | 0.60 | nan | 1.00 | ESTIMATED |
| T20I | batter | Phase 4 (sigma2 / n_eff_kish) | 439 | -1.06 | -0.88 | -0.48 | 1.63 | -0.65 | 0.00 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | batter | independent balls (sigma2 / n) | 439 | 0.16 | 0.15 | 0.44 | 0.41 | 0.39 | 0.28 | 0.07 | 1.00 | ESTIMATED |
| T20I | batter | match-cluster robust | 306 | 0.12 | 0.27 | 0.61 | 0.14 | 0.84 | 0.46 | 0.17 | 1.00 | ESTIMATED |
| T20I | batter | split-half covariance | 306 | 0.11 | 0.05 | 0.20 | 0.52 | 0.22 | 0.30 | nan | 1.00 | ESTIMATED |
| IPL | bowler | Phase 4 (sigma2 / n_eff_kish) | 163 | -0.95 | -0.83 | -0.26 | 1.28 | -0.74 | 0.00 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | bowler | independent balls (sigma2 / n) | 163 | 0.13 | 0.10 | 0.58 | 0.20 | 0.67 | 0.40 | 0.03 | 1.00 | ESTIMATED |
| IPL | bowler | match-cluster robust | 130 | 0.00511 | 0.08 | 0.52 | 0.09 | 0.05 | 0.05 | 0.03 | 1.00 | ESTIMATED |
| IPL | bowler | split-half covariance | 130 | 0.04 | -0.04 | 0.10 | 0.47 | 0.08 | 0.14 | nan | 0.81 | ESTIMATED |
| T20I | bowler | Phase 4 (sigma2 / n_eff_kish) | 296 | -0.99 | -0.89 | -0.50 | 1.40 | -0.71 | 0.00 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | bowler | independent balls (sigma2 / n) | 296 | 0.21 | 0.17 | 0.45 | 0.20 | 1.04 | 0.51 | 0.02 | 1.00 | ESTIMATED |
| T20I | bowler | match-cluster robust | 216 | 0.08 | 0.15 | 0.48 | 0.08 | 0.91 | 0.48 | 0.14 | 1.00 | ESTIMATED |
| T20I | bowler | split-half covariance | 216 | 0.06 | -0.04 | 0.11 | 0.36 | 0.17 | 0.26 | nan | 0.80 | ESTIMATED |


### Same, players with at least 12 pressure balls (TRAIN)

| format | role | noise basis | players | tau2 | noise | SNR | ICC | REML tau2 | status |
|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | Phase 4 (sigma2 / n_eff_kish) | 161 | -0.78 | 1.00 | -0.78 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | batter | independent balls (sigma2 / n) | 161 | 0.13 | 0.09 | 1.44 | 0.59 | 0.06 | ESTIMATED |
| IPL | batter | match-cluster robust | 158 | 0.11 | 0.08 | 1.47 | 0.59 | 0.15 | ESTIMATED |
| IPL | batter | split-half covariance | 125 | 0.03 | 0.19 | 0.18 | 0.27 | nan | ESTIMATED |
| T20I | batter | Phase 4 (sigma2 / n_eff_kish) | 266 | -1.08 | 1.25 | -0.87 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | batter | independent balls (sigma2 / n) | 266 | 0.07 | 0.10 | 0.69 | 0.41 | 0.06 | ESTIMATED |
| T20I | batter | match-cluster robust | 241 | 0.09 | 0.08 | 1.09 | 0.52 | 0.11 | ESTIMATED |
| T20I | batter | split-half covariance | 169 | 0.05 | 0.16 | 0.33 | 0.40 | nan | ESTIMATED |
| IPL | bowler | Phase 4 (sigma2 / n_eff_kish) | 139 | -0.90 | 1.00 | -0.90 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | bowler | independent balls (sigma2 / n) | 139 | 0.02 | 0.08 | 0.30 | 0.23 | 0.02 | ESTIMATED |
| IPL | bowler | match-cluster robust | 126 | 0.00321 | 0.08 | 0.04 | 0.04 | 0.03 | ESTIMATED |
| IPL | bowler | split-half covariance | 119 | 0.01 | 0.15 | 0.08 | 0.14 | nan | ESTIMATED |
| T20I | bowler | Phase 4 (sigma2 / n_eff_kish) | 238 | -1.01 | 1.12 | -0.90 | 0.00 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | bowler | independent balls (sigma2 / n) | 238 | 0.03 | 0.09 | 0.31 | 0.24 | 0.02 | ESTIMATED |
| T20I | bowler | match-cluster robust | 207 | 0.02 | 0.07 | 0.27 | 0.22 | 0.07 | ESTIMATED |
| T20I | bowler | split-half covariance | 186 | 0.02 | 0.16 | 0.11 | 0.17 | nan | ESTIMATED |


### Primary definition, full pre-test window (TRAIN + VALIDATION), at least 12 balls

| format | role | noise basis | players | tau2 | noise | SNR | ICC | status |
|---|---|---|---|---|---|---|---|---|
| IPL | batter | Phase 4 (sigma2 / n_eff_kish) | 176 | -0.72 | 0.93 | -0.78 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | batter | independent balls (sigma2 / n) | 176 | 0.12 | 0.08 | 1.47 | 0.59 | ESTIMATED |
| IPL | batter | match-cluster robust | 171 | 0.10 | 0.07 | 1.47 | 0.59 | ESTIMATED |
| IPL | batter | split-half covariance | 144 | 0.05 | 0.16 | 0.32 | 0.39 | ESTIMATED |
| T20I | batter | Phase 4 (sigma2 / n_eff_kish) | 348 | -1.00 | 1.16 | -0.86 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | batter | independent balls (sigma2 / n) | 348 | 0.07 | 0.09 | 0.78 | 0.44 | ESTIMATED |
| T20I | batter | match-cluster robust | 315 | 0.09 | 0.06 | 1.46 | 0.59 | ESTIMATED |
| T20I | batter | split-half covariance | 247 | 0.06 | 0.16 | 0.36 | 0.42 | ESTIMATED |
| IPL | bowler | Phase 4 (sigma2 / n_eff_kish) | 155 | -0.83 | 0.94 | -0.88 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| IPL | bowler | independent balls (sigma2 / n) | 155 | 0.04 | 0.08 | 0.51 | 0.34 | ESTIMATED |
| IPL | bowler | match-cluster robust | 145 | 0.03 | 0.08 | 0.35 | 0.26 | ESTIMATED |
| IPL | bowler | split-half covariance | 135 | 0.05 | 0.13 | 0.34 | 0.40 | ESTIMATED |
| T20I | bowler | Phase 4 (sigma2 / n_eff_kish) | 291 | -0.98 | 1.08 | -0.90 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| T20I | bowler | independent balls (sigma2 / n) | 291 | 0.03 | 0.08 | 0.33 | 0.25 | ESTIMATED |
| T20I | bowler | match-cluster robust | 257 | 0.03 | 0.07 | 0.39 | 0.28 | ESTIMATED |
| T20I | bowler | split-half covariance | 231 | 0.03 | 0.15 | 0.17 | 0.25 | ESTIMATED |


## 3. Split-half reliability (Spearman-Brown corrected, minimum 6 balls in each half)
Odd/even splits each player's matches by chronological parity. Early/late compares the first and second half of a player's matches (it mixes noise with real change in form, so it is a lower bound). Random averages 200 seeded random splits. Intervals are match-cluster bootstrap 2.5% and 97.5% percentiles. A cell with fewer than 10 qualifying players is `NOT_ESTIMABLE`.

| format | role | window | mode | players | r (Pearson) | SB Pearson | SB lo | SB hi | SB Spearman | SD across random splits | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | PRE_TEST | early_late | 138 | 0.19 | 0.33 | 0.10 | 0.54 | 0.47 | n/a | ESTIMATED |
| IPL | batter | PRE_TEST | odd_even | 144 | 0.24 | 0.39 | 0.18 | 0.59 | 0.38 | n/a | ESTIMATED |
| IPL | batter | PRE_TEST | random | 140 | 0.21 | 0.35 | n/a | n/a | 0.36 | 0.07 | ESTIMATED |
| IPL | batter | TRAIN | early_late | 122 | 0.09 | 0.16 | -0.17 | 0.42 | 0.23 | n/a | ESTIMATED |
| IPL | batter | TRAIN | odd_even | 125 | 0.16 | 0.27 | 0.09 | 0.57 | 0.29 | n/a | ESTIMATED |
| IPL | batter | TRAIN | random | 124 | 0.17 | 0.28 | n/a | n/a | 0.30 | 0.08 | ESTIMATED |
| T20I | batter | PRE_TEST | early_late | 227 | 0.32 | 0.48 | 0.20 | 0.55 | 0.53 | n/a | ESTIMATED |
| T20I | batter | PRE_TEST | odd_even | 247 | 0.26 | 0.42 | 0.18 | 0.49 | 0.38 | n/a | ESTIMATED |
| T20I | batter | PRE_TEST | random | 231 | 0.28 | 0.44 | n/a | n/a | 0.44 | 0.06 | ESTIMATED |
| T20I | batter | TRAIN | early_late | 164 | 0.22 | 0.36 | 0.04 | 0.49 | 0.43 | n/a | ESTIMATED |
| T20I | batter | TRAIN | odd_even | 169 | 0.25 | 0.40 | 0.05 | 0.49 | 0.38 | n/a | ESTIMATED |
| T20I | batter | TRAIN | random | 161 | 0.24 | 0.39 | n/a | n/a | 0.41 | 0.07 | ESTIMATED |
| IPL | bowler | PRE_TEST | early_late | 125 | 0.09 | 0.17 | -0.35 | 0.39 | 0.13 | n/a | ESTIMATED |
| IPL | bowler | PRE_TEST | odd_even | 135 | 0.26 | 0.41 | -0.10 | 0.49 | 0.46 | n/a | ESTIMATED |
| IPL | bowler | PRE_TEST | random | 128 | 0.13 | 0.24 | n/a | n/a | 0.23 | 0.09 | ESTIMATED |
| IPL | bowler | TRAIN | early_late | 111 | -0.07 | -0.16 | -0.58 | 0.30 | -0.19 | n/a | ESTIMATED |
| IPL | bowler | TRAIN | odd_even | 119 | 0.08 | 0.14 | -0.30 | 0.40 | 0.27 | n/a | ESTIMATED |
| IPL | bowler | TRAIN | random | 113 | -0.02 | -0.04 | n/a | n/a | 0.02 | 0.15 | ESTIMATED |
| T20I | bowler | PRE_TEST | early_late | 227 | 0.10 | 0.18 | -0.09 | 0.39 | 0.20 | n/a | ESTIMATED |
| T20I | bowler | PRE_TEST | odd_even | 231 | 0.15 | 0.25 | -0.08 | 0.42 | 0.25 | n/a | ESTIMATED |
| T20I | bowler | PRE_TEST | random | 226 | 0.10 | 0.19 | n/a | n/a | 0.20 | 0.08 | ESTIMATED |
| T20I | bowler | TRAIN | early_late | 177 | -0.03 | -0.06 | -0.36 | 0.27 | -0.02 | n/a | ESTIMATED |
| T20I | bowler | TRAIN | odd_even | 186 | 0.10 | 0.18 | -0.23 | 0.35 | 0.07 | n/a | ESTIMATED |
| T20I | bowler | TRAIN | random | 178 | 0.05 | 0.10 | n/a | n/a | 0.07 | 0.08 | ESTIMATED |


### All four definitions, odd/even, full pre-test window, primary streams

| definition | format | role | players | SB Pearson | SB lo | SB hi | status |
|---|---|---|---|---|---|---|---|
| any\|q0.75 | IPL | batter | 144 | 0.39 | 0.18 | 0.59 | ESTIMATED |
| any\|q0.9 | IPL | batter | 90 | 0.37 | 0.03 | 0.60 | ESTIMATED |
| chase\|q0.75 | IPL | batter | 103 | 0.45 | 0.11 | 0.63 | ESTIMATED |
| chase\|q0.9 | IPL | batter | 48 | 0.13 | -0.34 | 0.61 | ESTIMATED |
| any\|q0.75 | T20I | batter | 247 | 0.42 | 0.18 | 0.49 | ESTIMATED |
| any\|q0.9 | T20I | batter | 132 | 0.51 | 0.08 | 0.59 | ESTIMATED |
| chase\|q0.75 | T20I | batter | 140 | 0.41 | 0.17 | 0.56 | ESTIMATED |
| chase\|q0.9 | T20I | batter | 52 | 0.68 | 0.05 | 0.72 | ESTIMATED |
| any\|q0.75 | IPL | bowler | 135 | 0.41 | -0.10 | 0.49 | ESTIMATED |
| any\|q0.9 | IPL | bowler | 90 | 0.04 | -0.42 | 0.42 | ESTIMATED |
| chase\|q0.75 | IPL | bowler | 107 | 0.39 | -0.08 | 0.49 | ESTIMATED |
| chase\|q0.9 | IPL | bowler | 66 | -0.20 | -0.72 | 0.40 | ESTIMATED |
| any\|q0.75 | T20I | bowler | 231 | 0.25 | -0.08 | 0.42 | ESTIMATED |
| any\|q0.9 | T20I | bowler | 148 | 0.31 | -0.15 | 0.44 | ESTIMATED |
| chase\|q0.75 | T20I | bowler | 145 | 0.23 | -0.31 | 0.43 | ESTIMATED |
| chase\|q0.9 | T20I | bowler | 86 | 0.29 | -0.38 | 0.49 | ESTIMATED |


### Alternatives: variance decomposition (PRE_TEST, at least 12 balls, match-cluster and Phase 4 bases)

| definition | format | role | noise basis | players | tau2 | SNR | ICC | status |
|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | IPL | batter | match_cluster | 171 | 0.10 | 1.47 | 0.59 | ESTIMATED |
| any\|q0.75 | IPL | batter | phase4_kish | 176 | -0.72 | -0.78 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.75 | IPL | batter | split_half_covariance | 144 | 0.05 | 0.32 | 0.39 | ESTIMATED |
| any\|q0.9 | IPL | batter | match_cluster | 118 | 0.11 | 1.40 | 0.58 | ESTIMATED |
| any\|q0.9 | IPL | batter | phase4_kish | 124 | -0.99 | -0.84 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.9 | IPL | batter | split_half_covariance | 90 | 0.06 | 0.29 | 0.37 | ESTIMATED |
| chase\|q0.75 | IPL | batter | match_cluster | 134 | 0.12 | 1.27 | 0.56 | ESTIMATED |
| chase\|q0.75 | IPL | batter | phase4_kish | 142 | -1.08 | -0.80 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.75 | IPL | batter | split_half_covariance | 103 | 0.08 | 0.41 | 0.45 | ESTIMATED |
| chase\|q0.9 | IPL | batter | match_cluster | 79 | 0.15 | 1.13 | 0.53 | ESTIMATED |
| chase\|q0.9 | IPL | batter | phase4_kish | 86 | -1.38 | -0.83 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.9 | IPL | batter | split_half_covariance | 48 | 0.03 | 0.08 | 0.13 | ESTIMATED |
| any\|q0.75 | T20I | batter | match_cluster | 315 | 0.09 | 1.46 | 0.59 | ESTIMATED |
| any\|q0.75 | T20I | batter | phase4_kish | 348 | -1.00 | -0.86 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.75 | T20I | batter | split_half_covariance | 247 | 0.06 | 0.36 | 0.42 | ESTIMATED |
| any\|q0.9 | T20I | batter | match_cluster | 186 | 0.14 | 1.57 | 0.61 | ESTIMATED |
| any\|q0.9 | T20I | batter | phase4_kish | 207 | -1.07 | -0.83 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.9 | T20I | batter | split_half_covariance | 132 | 0.11 | 0.52 | 0.51 | ESTIMATED |
| chase\|q0.75 | T20I | batter | match_cluster | 200 | 0.11 | 1.19 | 0.54 | ESTIMATED |
| chase\|q0.75 | T20I | batter | phase4_kish | 231 | -1.37 | -0.87 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.75 | T20I | batter | split_half_covariance | 140 | 0.08 | 0.34 | 0.41 | ESTIMATED |
| chase\|q0.9 | T20I | batter | match_cluster | 89 | 0.18 | 1.60 | 0.61 | ESTIMATED |
| chase\|q0.9 | T20I | batter | phase4_kish | 110 | -1.58 | -0.85 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.9 | T20I | batter | split_half_covariance | 52 | 0.23 | 1.08 | 0.68 | ESTIMATED |
| any\|q0.75 | IPL | bowler | match_cluster | 145 | 0.03 | 0.35 | 0.26 | ESTIMATED |
| any\|q0.75 | IPL | bowler | phase4_kish | 155 | -0.83 | -0.88 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.75 | IPL | bowler | split_half_covariance | 135 | 0.05 | 0.34 | 0.40 | ESTIMATED |
| any\|q0.9 | IPL | bowler | match_cluster | 101 | 0.03 | 0.21 | 0.17 | ESTIMATED |
| any\|q0.9 | IPL | bowler | phase4_kish | 110 | -0.90 | -0.84 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.9 | IPL | bowler | split_half_covariance | 90 | 0.00382 | 0.02 | 0.04 | ESTIMATED |
| chase\|q0.75 | IPL | bowler | match_cluster | 111 | 0.04 | 0.42 | 0.30 | ESTIMATED |
| chase\|q0.75 | IPL | bowler | phase4_kish | 123 | -1.08 | -0.88 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.75 | IPL | bowler | split_half_covariance | 107 | 0.06 | 0.32 | 0.39 | ESTIMATED |
| chase\|q0.9 | IPL | bowler | match_cluster | 76 | -0.01 | -0.07 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.9 | IPL | bowler | phase4_kish | 81 | -1.14 | -0.84 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.9 | IPL | bowler | split_half_covariance | 66 | -0.03 | -0.08 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.75 | T20I | bowler | match_cluster | 257 | 0.03 | 0.39 | 0.28 | ESTIMATED |
| any\|q0.75 | T20I | bowler | phase4_kish | 291 | -0.98 | -0.90 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.75 | T20I | bowler | split_half_covariance | 231 | 0.03 | 0.17 | 0.25 | ESTIMATED |
| any\|q0.9 | T20I | bowler | match_cluster | 172 | 0.03 | 0.30 | 0.23 | ESTIMATED |
| any\|q0.9 | T20I | bowler | phase4_kish | 198 | -1.00 | -0.86 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| any\|q0.9 | T20I | bowler | split_half_covariance | 148 | 0.04 | 0.22 | 0.31 | ESTIMATED |
| chase\|q0.75 | T20I | bowler | match_cluster | 159 | 0.05 | 0.50 | 0.33 | ESTIMATED |
| chase\|q0.75 | T20I | bowler | phase4_kish | 189 | -1.22 | -0.88 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.75 | T20I | bowler | split_half_covariance | 145 | 0.03 | 0.15 | 0.23 | ESTIMATED |
| chase\|q0.9 | T20I | bowler | match_cluster | 105 | 0.07 | 0.53 | 0.35 | ESTIMATED |
| chase\|q0.9 | T20I | bowler | phase4_kish | 121 | -1.21 | -0.83 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| chase\|q0.9 | T20I | bowler | split_half_covariance | 86 | 0.05 | 0.19 | 0.28 | ESTIMATED |


## 4. Reliability against pressure opportunities (primary streams, full pre-test window)
Players with at least t pressure balls in the window; odd/even Spearman-Brown reliability and the match-cluster SNR/ICC inside that group. The group changes with t, so rows are not independent.

| format | role | min balls | players | SB odd/even | SB lo | SB hi | SNR (cluster) | ICC (cluster) | SNR (Phase 4) | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 12 | 176 | 0.39 | 0.13 | 0.57 | 1.47 | 0.59 | -0.78 | ESTIMATED |
| IPL | batter | 18 | 149 | 0.46 | 0.14 | 0.58 | 1.66 | 0.62 | -0.82 | ESTIMATED |
| IPL | batter | 24 | 138 | 0.46 | 0.12 | 0.57 | 1.46 | 0.59 | -0.82 | ESTIMATED |
| IPL | batter | 30 | 126 | 0.53 | 0.17 | 0.59 | 1.68 | 0.63 | -0.82 | ESTIMATED |
| IPL | batter | 45 | 106 | 0.43 | 0.07 | 0.53 | 0.97 | 0.49 | -0.86 | ESTIMATED |
| IPL | batter | 60 | 80 | 0.32 | -0.11 | 0.49 | 0.72 | 0.42 | -0.89 | ESTIMATED |
| IPL | batter | 90 | 58 | 0.17 | -0.49 | 0.43 | 0.22 | 0.18 | -0.93 | ESTIMATED |
| IPL | batter | 120 | 42 | 0.42 | -0.43 | 0.56 | 0.73 | 0.42 | -0.90 | ESTIMATED |
| T20I | batter | 12 | 348 | 0.42 | 0.16 | 0.50 | 1.46 | 0.59 | -0.86 | ESTIMATED |
| T20I | batter | 18 | 291 | 0.38 | 0.11 | 0.47 | 1.34 | 0.57 | -0.87 | ESTIMATED |
| T20I | batter | 24 | 243 | 0.33 | 0.07 | 0.45 | 0.99 | 0.50 | -0.88 | ESTIMATED |
| T20I | batter | 30 | 208 | 0.28 | 0.04 | 0.44 | 0.92 | 0.48 | -0.89 | ESTIMATED |
| T20I | batter | 45 | 147 | 0.28 | -0.00656 | 0.43 | 1.08 | 0.52 | -0.87 | ESTIMATED |
| T20I | batter | 60 | 104 | 0.41 | 0.00937 | 0.50 | 1.35 | 0.57 | -0.85 | ESTIMATED |
| T20I | batter | 90 | 66 | 0.21 | -0.26 | 0.44 | 0.68 | 0.41 | -0.89 | ESTIMATED |
| T20I | batter | 120 | 41 | 0.33 | -0.21 | 0.55 | 0.50 | 0.33 | -0.90 | ESTIMATED |
| IPL | bowler | 12 | 155 | 0.41 | -0.10 | 0.49 | 0.35 | 0.26 | -0.88 | ESTIMATED |
| IPL | bowler | 18 | 136 | 0.43 | -0.13 | 0.50 | 0.50 | 0.33 | -0.87 | ESTIMATED |
| IPL | bowler | 24 | 123 | 0.24 | -0.21 | 0.45 | 0.17 | 0.15 | -0.89 | ESTIMATED |
| IPL | bowler | 36 | 102 | 0.36 | -0.24 | 0.45 | 0.12 | 0.11 | -0.89 | ESTIMATED |
| IPL | bowler | 48 | 94 | 0.39 | -0.24 | 0.47 | 0.21 | 0.17 | -0.88 | ESTIMATED |
| IPL | bowler | 72 | 73 | 0.55 | -0.03 | 0.58 | 0.62 | 0.38 | -0.85 | ESTIMATED |
| IPL | bowler | 96 | 59 | 0.50 | -0.12 | 0.58 | 0.49 | 0.33 | -0.86 | ESTIMATED |
| IPL | bowler | 144 | 43 | 0.47 | -0.26 | 0.61 | 0.61 | 0.38 | -0.86 | ESTIMATED |
| T20I | bowler | 12 | 291 | 0.25 | -0.10 | 0.40 | 0.39 | 0.28 | -0.90 | ESTIMATED |
| T20I | bowler | 18 | 253 | 0.27 | -0.10 | 0.40 | 0.44 | 0.31 | -0.90 | ESTIMATED |
| T20I | bowler | 24 | 217 | 0.33 | -0.04 | 0.45 | 0.55 | 0.36 | -0.89 | ESTIMATED |
| T20I | bowler | 36 | 162 | 0.35 | -0.10 | 0.45 | 0.50 | 0.34 | -0.89 | ESTIMATED |
| T20I | bowler | 48 | 128 | 0.44 | -0.05 | 0.49 | 0.80 | 0.44 | -0.86 | ESTIMATED |
| T20I | bowler | 72 | 97 | 0.33 | -0.19 | 0.44 | 0.51 | 0.34 | -0.87 | ESTIMATED |
| T20I | bowler | 96 | 74 | 0.29 | -0.21 | 0.45 | 0.27 | 0.21 | -0.89 | ESTIMATED |
| T20I | bowler | 144 | 45 | 0.47 | -0.14 | 0.58 | 0.82 | 0.45 | -0.85 | ESTIMATED |


## 5. Sample size needed for reliability targets (DESCRIPTIVE_PROJECTION, not a threshold)
n* = R / (1 - R) x sigma_eff / tau2, per noise basis, using the full pre-test window and all players (`min_balls` = 1). For the Phase 4 basis the unit is Kish effective units, for the others it is balls. `NOT_ESTIMABLE` appears where tau2 is not positive. The last column re-computes n* with tau2 at its bootstrap 90th percentile (an optimistic bound). None of these numbers is an eligibility threshold.

| format | role | noise basis | target R | unit | n* (point) | n* (tau2 at boot p90) | median player balls | P90 player balls | share of players >= n* |
|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ball_independent | 0.50 | balls | 39.38 | 13.21 | 26.00 | 163.00 | 0.43 |
| IPL | batter | ball_independent | 0.70 | balls | 91.89 | 30.82 | 26.00 | 163.00 | 0.21 |
| IPL | batter | ball_independent | 0.80 | balls | 157.53 | 52.84 | 26.00 | 163.00 | 0.11 |
| IPL | batter | match_cluster | 0.50 | balls | 11.97 | 6.90 | 26.00 | 163.00 | 0.66 |
| IPL | batter | match_cluster | 0.70 | balls | 27.92 | 16.11 | 26.00 | 163.00 | 0.49 |
| IPL | batter | match_cluster | 0.80 | balls | 47.87 | 27.61 | 26.00 | 163.00 | 0.36 |
| IPL | batter | phase4_kish | 0.50 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 26.00 | 163.00 | n/a |
| IPL | batter | phase4_kish | 0.70 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 26.00 | 163.00 | n/a |
| IPL | batter | phase4_kish | 0.80 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 26.00 | 163.00 | n/a |
| IPL | batter | split_half_covariance | 0.50 | balls | 38.65 | 38.45 | 26.00 | 163.00 | 0.44 |
| IPL | batter | split_half_covariance | 0.70 | balls | 90.17 | 89.72 | 26.00 | 163.00 | 0.21 |
| IPL | batter | split_half_covariance | 0.80 | balls | 154.58 | 153.80 | 26.00 | 163.00 | 0.11 |
| T20I | batter | ball_independent | 0.50 | balls | 33.02 | 9.23 | 19.00 | 97.00 | 0.34 |
| T20I | batter | ball_independent | 0.70 | balls | 77.05 | 21.54 | 19.00 | 97.00 | 0.14 |
| T20I | batter | ball_independent | 0.80 | balls | 132.09 | 36.93 | 19.00 | 97.00 | 0.07 |
| T20I | batter | match_cluster | 0.50 | balls | 21.71 | 5.45 | 19.00 | 97.00 | 0.47 |
| T20I | batter | match_cluster | 0.70 | balls | 50.67 | 12.73 | 19.00 | 97.00 | 0.23 |
| T20I | batter | match_cluster | 0.80 | balls | 86.86 | 21.81 | 19.00 | 97.00 | 0.13 |
| T20I | batter | phase4_kish | 0.50 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 19.00 | 97.00 | n/a |
| T20I | batter | phase4_kish | 0.70 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 19.00 | 97.00 | n/a |
| T20I | batter | phase4_kish | 0.80 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 19.00 | 97.00 | n/a |
| T20I | batter | split_half_covariance | 0.50 | balls | 98.35 | 73.30 | 19.00 | 97.00 | 0.10 |
| T20I | batter | split_half_covariance | 0.70 | balls | 229.49 | 171.02 | 19.00 | 97.00 | 0.01 |
| T20I | batter | split_half_covariance | 0.80 | balls | 393.41 | 293.18 | 19.00 | 97.00 | 0.00186 |
| IPL | bowler | ball_independent | 0.50 | balls | 13.49 | 5.75 | 50.50 | 235.90 | 0.79 |
| IPL | bowler | ball_independent | 0.70 | balls | 31.48 | 13.42 | 50.50 | 235.90 | 0.58 |
| IPL | bowler | ball_independent | 0.80 | balls | 53.96 | 23.01 | 50.50 | 235.90 | 0.49 |
| IPL | bowler | match_cluster | 0.50 | balls | 132.03 | 8.81 | 50.50 | 235.90 | 0.26 |
| IPL | bowler | match_cluster | 0.70 | balls | 308.07 | 20.57 | 50.50 | 235.90 | 0.03 |
| IPL | bowler | match_cluster | 0.80 | balls | 528.12 | 35.26 | 50.50 | 235.90 | 0.00 |
| IPL | bowler | phase4_kish | 0.50 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 50.50 | 235.90 | n/a |
| IPL | bowler | phase4_kish | 0.70 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 50.50 | 235.90 | n/a |
| IPL | bowler | phase4_kish | 0.80 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 50.50 | 235.90 | n/a |
| IPL | bowler | split_half_covariance | 0.50 | balls | 475.26 | 328.66 | 50.50 | 235.90 | 0.00 |
| IPL | bowler | split_half_covariance | 0.70 | balls | 1108.94 | 766.87 | 50.50 | 235.90 | 0.00 |
| IPL | bowler | split_half_covariance | 0.80 | balls | 1901.04 | 1314.63 | 50.50 | 235.90 | 0.00 |
| T20I | bowler | ball_independent | 0.50 | balls | 13.41 | 7.26 | 31.00 | 152.20 | 0.76 |
| T20I | bowler | ball_independent | 0.70 | balls | 31.28 | 16.94 | 31.00 | 152.20 | 0.48 |
| T20I | bowler | ball_independent | 0.80 | balls | 53.63 | 29.04 | 31.00 | 152.20 | 0.32 |
| T20I | bowler | match_cluster | 0.50 | balls | 38.77 | 8.40 | 31.00 | 152.20 | 0.43 |
| T20I | bowler | match_cluster | 0.70 | balls | 90.46 | 19.61 | 31.00 | 152.20 | 0.23 |
| T20I | bowler | match_cluster | 0.80 | balls | 155.08 | 33.61 | 31.00 | 152.20 | 0.09 |
| T20I | bowler | phase4_kish | 0.50 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 31.00 | 152.20 | n/a |
| T20I | bowler | phase4_kish | 0.70 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 31.00 | 152.20 | n/a |
| T20I | bowler | phase4_kish | 0.80 | kish_effective_units | NOT_ESTIMABLE | NOT_ESTIMABLE | 31.00 | 152.20 | n/a |
| T20I | bowler | split_half_covariance | 0.50 | balls | 178.94 | 139.34 | 31.00 | 152.20 | 0.07 |
| T20I | bowler | split_half_covariance | 0.70 | balls | 417.54 | 325.14 | 31.00 | 152.20 | 0.00279 |
| T20I | bowler | split_half_covariance | 0.80 | balls | 715.78 | 557.38 | 31.00 | 152.20 | 0.00 |


## 6. Could samples like these detect a between-player variance? (parametric simulation)
Players receive a true effect with variance tau2 = ratio x sigma2 plus noise with the observed per-player noise variance (at least 12 balls, full pre-test window). 'positive' is the share of 400 replications in which the moment estimator is above zero; 'within 50%' is the share within 50% of the truth. The simulation assumes the noise model is right, which is the open question.

| format | role | tau2 / sigma2 | true ICC | share positive | share within 50% | players |
|---|---|---|---|---|---|---|
| IPL | batter | 0.0005 | 0.02 | 0.51 | 0.06 | 171 |
| IPL | batter | 0.001 | 0.04 | 0.52 | 0.07 | 171 |
| IPL | batter | 0.0025 | 0.10 | 0.69 | 0.24 | 171 |
| IPL | batter | 0.005 | 0.19 | 0.85 | 0.35 | 171 |
| IPL | batter | 0.01 | 0.31 | 0.99 | 0.69 | 171 |
| IPL | batter | 0.03 | 0.53 | 1.00 | 0.96 | 171 |
| T20I | batter | 0.0005 | 0.02 | 0.58 | 0.08 | 315 |
| T20I | batter | 0.001 | 0.04 | 0.64 | 0.12 | 315 |
| T20I | batter | 0.0025 | 0.10 | 0.76 | 0.28 | 315 |
| T20I | batter | 0.005 | 0.18 | 0.95 | 0.53 | 315 |
| T20I | batter | 0.01 | 0.30 | 0.99 | 0.84 | 315 |
| T20I | batter | 0.03 | 0.52 | 1.00 | 1.00 | 315 |
| IPL | bowler | 0.0005 | 0.02 | 0.49 | 0.04 | 145 |
| IPL | bowler | 0.001 | 0.04 | 0.56 | 0.09 | 145 |
| IPL | bowler | 0.0025 | 0.09 | 0.69 | 0.18 | 145 |
| IPL | bowler | 0.005 | 0.17 | 0.83 | 0.40 | 145 |
| IPL | bowler | 0.01 | 0.29 | 0.98 | 0.67 | 145 |
| IPL | bowler | 0.03 | 0.50 | 1.00 | 0.92 | 145 |
| T20I | bowler | 0.0005 | 0.02 | 0.53 | 0.06 | 257 |
| T20I | bowler | 0.001 | 0.04 | 0.55 | 0.12 | 257 |
| T20I | bowler | 0.0025 | 0.09 | 0.73 | 0.27 | 257 |
| T20I | bowler | 0.005 | 0.16 | 0.92 | 0.50 | 257 |
| T20I | bowler | 0.01 | 0.28 | 0.99 | 0.71 | 257 |
| T20I | bowler | 0.03 | 0.49 | 1.00 | 0.97 | 257 |


## 7. Bowler-specific pressure signals (SENSITIVITY_ONLY)
The primary definition applies batter-state signals to bowlers: its innings-1 rows are states in which the batting side is BEHIND the prior par, which are easy states for a bowler. Three candidates, declared in `config/phase5_investigation_v1.json` before any run, flag states in which the bowling side is under pressure. Thresholds are TRAIN-only per format. They do not replace the primary definition, nothing is selected on these numbers, and all four signals are reported. Thresholds: `{'bowler_defence_margin': {'chase_surplus|IPL': 4.400000000000022, 'inn1_par_dev|IPL': 12.3125, 'chase_surplus|T20I': 5.347826086956516, 'inn1_par_dev|T20I': 10.3739837398374}, 'bowler_death_close_gap': {'abs_gap_q0.25|IPL': 2.988006853226727, 'abs_gap_q0.25|T20I': 2.6060606060606055}, 'bowler_death_wickets_in_hand': {'wickets_remaining|IPL': 6.0, 'wickets_remaining|T20I': 6.0}}`. Not buildable: none.

| signal | format | mode | pressure balls | players >= 18 balls (TRAIN) | qualifying players | SB | SB lo | SB hi | status |
|---|---|---|---|---|---|---|---|---|---|
| bowler_death_close_gap | IPL | early_late | 1,817 | 25 | 42 | 0.21 | -1.10 | 0.47 | ESTIMATED |
| bowler_death_wickets_in_hand | IPL | early_late | 7,238 | 85 | 109 | -0.16 | -0.58 | 0.27 | ESTIMATED |
| bowler_defence_margin | IPL | early_late | 18,095 | 133 | 141 | -0.26 | -0.63 | 0.27 | ESTIMATED |
| primary_batter_state_signals | IPL | early_late | 15,939 | 123 | 125 | 0.17 | -0.35 | 0.39 | ESTIMATED |
| bowler_death_close_gap | IPL | odd_even | 1,817 | 25 | 48 | 0.13 | -0.95 | 0.53 | ESTIMATED |
| bowler_death_wickets_in_hand | IPL | odd_even | 7,238 | 85 | 110 | -0.23 | -0.52 | 0.34 | ESTIMATED |
| bowler_defence_margin | IPL | odd_even | 18,095 | 133 | 143 | 0.03 | -0.42 | 0.37 | ESTIMATED |
| primary_batter_state_signals | IPL | odd_even | 15,939 | 123 | 135 | 0.41 | -0.10 | 0.49 | ESTIMATED |
| bowler_death_close_gap | T20I | early_late | 1,867 | 24 | 44 | 0.14 | -0.88 | 0.56 | ESTIMATED |
| bowler_death_wickets_in_hand | T20I | early_late | 6,949 | 108 | 157 | 0.30 | -0.26 | 0.42 | ESTIMATED |
| bowler_defence_margin | T20I | early_late | 22,154 | 209 | 233 | 0.17 | -0.19 | 0.33 | ESTIMATED |
| primary_batter_state_signals | T20I | early_late | 21,544 | 199 | 227 | 0.18 | -0.09 | 0.39 | ESTIMATED |
| bowler_death_close_gap | T20I | odd_even | 1,867 | 24 | 43 | 0.12 | -0.82 | 0.52 | ESTIMATED |
| bowler_death_wickets_in_hand | T20I | odd_even | 6,949 | 108 | 159 | 0.32 | -0.21 | 0.40 | ESTIMATED |
| bowler_defence_margin | T20I | odd_even | 22,154 | 209 | 235 | 0.29 | -0.13 | 0.38 | ESTIMATED |
| primary_batter_state_signals | T20I | odd_even | 21,544 | 199 | 231 | 0.25 | -0.08 | 0.42 | ESTIMATED |


Variance decomposition of the same signals (PRE_TEST, at least 12 balls):

| signal | format | noise basis | players | tau2 | SNR | ICC | status |
|---|---|---|---|---|---|---|---|
| bowler_death_close_gap | IPL | match_cluster | 55 | 0.03 | 0.25 | 0.20 | ESTIMATED |
| bowler_death_close_gap | IPL | phase4_kish | 58 | -0.98 | -0.85 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_close_gap | IPL | split_half_covariance | 48 | 0.02 | 0.07 | 0.13 | ESTIMATED |
| bowler_death_wickets_in_hand | IPL | match_cluster | 116 | -0.01 | -0.09 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_wickets_in_hand | IPL | phase4_kish | 119 | -0.71 | -0.85 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_wickets_in_hand | IPL | split_half_covariance | 110 | -0.03 | -0.09 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_defence_margin | IPL | match_cluster | 156 | -0.01 | -0.14 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_defence_margin | IPL | phase4_kish | 171 | -0.90 | -0.90 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_defence_margin | IPL | split_half_covariance | 143 | 0.00252 | 0.01 | 0.03 | ESTIMATED |
| primary_batter_state_signals | IPL | match_cluster | 145 | 0.03 | 0.35 | 0.26 | ESTIMATED |
| primary_batter_state_signals | IPL | phase4_kish | 155 | -0.83 | -0.88 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| primary_batter_state_signals | IPL | split_half_covariance | 135 | 0.05 | 0.34 | 0.40 | ESTIMATED |
| bowler_death_close_gap | T20I | match_cluster | 57 | -0.000388 | -0.00202 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_close_gap | T20I | phase4_kish | 61 | -0.83 | -0.81 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_close_gap | T20I | split_half_covariance | 43 | 0.02 | 0.07 | 0.12 | ESTIMATED |
| bowler_death_wickets_in_hand | T20I | match_cluster | 169 | 0.05 | 0.34 | 0.25 | ESTIMATED |
| bowler_death_wickets_in_hand | T20I | phase4_kish | 177 | -0.86 | -0.80 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_death_wickets_in_hand | T20I | split_half_covariance | 159 | 0.06 | 0.24 | 0.32 | ESTIMATED |
| bowler_defence_margin | T20I | match_cluster | 266 | 0.04 | 0.45 | 0.31 | ESTIMATED |
| bowler_defence_margin | T20I | phase4_kish | 306 | -1.01 | -0.87 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| bowler_defence_margin | T20I | split_half_covariance | 235 | 0.04 | 0.20 | 0.29 | ESTIMATED |
| primary_batter_state_signals | T20I | match_cluster | 257 | 0.03 | 0.39 | 0.28 | ESTIMATED |
| primary_batter_state_signals | T20I | phase4_kish | 291 | -0.98 | -0.90 | 0.00 | BETWEEN_VARIANCE_NOT_POSITIVE |
| primary_batter_state_signals | T20I | split_half_covariance | 231 | 0.03 | 0.17 | 0.25 | ESTIMATED |


## 8. Pooling IPL and T20I for players who appear in both (descriptive)
Same players, same odd/even rule, each format baseline-adjusted separately, matches pooled chronologically. Only players qualifying (6 balls per half) in all three analyses are compared. No bootstrap interval is computed here.

| role | window | players in both | qualifying in all three | SB IPL only | SB T20I only | SB pooled | ICC cluster IPL | ICC cluster T20I | ICC cluster pooled | status |
|---|---|---|---|---|---|---|---|---|---|---|
| batter | PRE_TEST | 136 | 50 | 0.54 | 0.18 | 0.72 | 0.64 | 0.38 | 0.76 | ESTIMATED |
| batter | TRAIN | 118 | 36 | -0.05 | -0.19 | 0.25 | 0.30 | 0.00 | 0.39 | ESTIMATED |
| bowler | PRE_TEST | 102 | 73 | 0.57 | 0.16 | 0.46 | 0.47 | 0.28 | 0.40 | ESTIMATED |
| bowler | TRAIN | 89 | 64 | 0.15 | 0.19 | 0.45 | 0.00 | 0.33 | 0.37 | ESTIMATED |


## 9. What the data can and cannot support
- Between-player variance cannot be pinned: its estimate depends on the noise model (section 2) and the noise model cannot be tested with these data alone. Treat every tau2, SNR and ICC as a bracket, not a value.
- The cluster-robust noise is biased low for players with few matches; the independent-ball noise is biased low when balls inside a match are dependent; the Phase 4 noise is biased high. REML and the split-half covariance are cross-checks, not the truth.
- Projections in section 5 inherit that uncertainty and use the pre-test sample only. They say how many pressure balls a stable estimate would need under each noise model, not how many a validated eligibility rule should require.
- Early/late split-half is a lower bound on reliability because form changes over time.
- Bootstrap percentile intervals are not bias-corrected and can sit off the point value (duplicated matches in a resample change the half-sample noise); read them as spread, not as a confidence statement.
- Alternative definitions are NOT ranked against each other here and no definition is shown to be better.
- No outcome of the TEST period is used or inferable from this report.

## 10. Unresolved issues
1. Noise model of the shrinkage estimator: the Phase 4 `n_eff` is a Kish count of equally sized matches but is divided into a per-ball variance. This drives the negative Phase 4 SNR and the strong shrinkage (floor hits, `shrink_tau4`). Choosing a different noise model changes every shrunk score and needs a decision before the methodology is locked.
2. The size of the between-player variance remains unidentified (brackets in section 2). Until it is identified, ranking reliability claims are not supportable.
3. Bowler pressure uses batter-state signals. Section 7 shows how three bowler-specific candidates behave; no candidate is adopted. Adopting one is a methodology decision.
4. Every eligibility threshold is still the unvalidated TRAIN-median working pool (20 / 16 / 49 / 29 balls).
5. Sample sizes are small in several cells (see player counts); intervals are wide and some cells are NOT_ESTIMABLE.
6. Date verification, strict capped/uncapped classification and the methodology-validation gate are unresolved (section 11). A later TEST evaluation is not a pristine hold-out because Phase 4 aggregate TEST results were shown.

## 11. Gates still failing (from `phase5_publication_gates.json`)
Publication status of any ranking today: `INTERNAL_EXPERIMENTAL_ONLY`.
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | yes | no | not applicable: request uses no strict status filter |
| min_eligible_pool | yes | no | not applicable: evaluated per request with rows |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## 12. Independent spot checks
- Split-half (IPL batter runs, `any|q0.75`, PRE_TEST, odd/even): independent pandas loop r = 0.243385 (144 players) vs module r = 0.243385 (144 players), abs diff 8.3e-17.
- Phase 4 SNR (T20I bowler, TRAIN) recomputed from raw rows: -0.706396 vs module -0.706396.

## 13. Preservation
`{'official_data_unchanged': True, 'phase4_report_files_hashed': 56, 'phase4_report_files_changed': [], 'phase4_lock_log_sha256_before': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase4_lock_log_sha256_after': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase5_lock_log_events': 0, 'test_opened': False, 'all_preserved': True}`
