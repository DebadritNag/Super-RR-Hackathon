# Phase 4 pressure eligibility validation

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking. No final ML model.

Definition `any|q0.75`, shrinkage `shrink_tau4`. Thresholds are re-derived per cell from the observed TRAIN distribution of per-player pressure balls and judged on TRAIN and VALIDATION only. The Phase 3 T20I placeholders (batter 24, bowler 36 balls) are SUPERSEDED placeholders and are not validated.

Rule (fixed before the run): (1) marginal-player data weight B(t) = n_t / (n_t + k) >= 0.5; (2) smallest passing candidate unless TRAIN-to-VALIDATION reproducibility is significantly negative; (3) otherwise THRESHOLD_NOT_VALIDATED (a low-data-weight fallback is named only if reproducibility is estimable with its interval above 0 and the marginal data weight is at least 0.1); (4) no threshold is lowered to reach ten players, and fewer than ten is reported as is.
A threshold t is on the TRAIN scale: a PRE_TEST player qualifies with PRE_TEST balls >= t x W (W = PRE_TEST pressure balls / TRAIN pressure balls of the cell).

## Decisions
| format | role | status | selected t | fallback t | label | working-pool t (TRAIN median) | analysis t | analysis label | W | smallest t at other data-weight gates |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | THRESHOLD_NOT_VALIDATED | n/a | n/a | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 20 | 20 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 1.31 | {"0.3": null, "0.1": 72} |
| T20I | batter | THRESHOLD_NOT_VALIDATED | n/a | n/a | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 16 | 16 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 1.47 | {"0.3": null, "0.1": 90} |
| IPL | bowler | THRESHOLD_NOT_VALIDATED | n/a | n/a | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 49 | 49 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 1.31 | {"0.3": 144, "0.1": 48} |
| T20I | bowler | THRESHOLD_NOT_VALIDATED | n/a | n/a | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 29 | 29 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 1.47 | {"0.3": 144, "0.1": 48} |

`analysis t` is the threshold used by the format-weight and ranking experiments. When it comes from the working pool it is NOT a validated eligibility rule; it exists so that the downstream experiments have players to rank, and every output carries its label.

## Candidate thresholds by cell

### IPL batters (k = 25.00, W = 1.31, VAL/TRAIN ball ratio = 0.31)
| t | source | players | balls | matches | median n_eff | marginal B | median B | median interval width | pool 2.5% | pool 97.5% | boot Jaccard top10 | exp. top10 overlap | repro n | repro rho | lo | hi | Phase 3 placeholder value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | P10 | 239 | 15,169 | 260 | 3.06 | 0.04 | 0.11 | 0.14 | 201.00 | 222.00 | 0.33 | 4.88 | 111 | 0.42 | 0.15 | 0.45 | no |
| 6 | ladder | 208 | 14,988 | 260 | 3.83 | 0.04 | 0.13 | 0.14 | 171.00 | 192.00 | 0.34 | 5.00 | 96 | 0.40 | 0.11 | 0.43 | no |
| 8 | P25 | 184 | 14,772 | 260 | 4.27 | 0.04 | 0.15 | 0.15 | 151.00 | 170.00 | 0.35 | 5.10 | 89 | 0.41 | 0.11 | 0.44 | no |
| 12 | ladder | 159 | 14,454 | 260 | 4.96 | 0.04 | 0.17 | 0.15 | 132.97 | 149.00 | 0.36 | 5.18 | 84 | 0.35 | 0.07 | 0.41 | no |
| 18 | ladder | 138 | 14,075 | 260 | 5.57 | 0.06 | 0.18 | 0.15 | 114.00 | 128.02 | 0.37 | 5.27 | 74 | 0.27 | -0.02 | 0.36 | no |
| 20 | P50 | 132 | 13,925 | 260 | 5.73 | 0.06 | 0.19 | 0.15 | 107.00 | 123.00 | 0.36 | 5.24 | 70 | 0.18 | -0.09 | 0.30 | no |
| 24 | ladder | 122 | 13,638 | 260 | 5.83 | 0.06 | 0.19 | 0.15 | 98.00 | 113.00 | 0.36 | 5.19 | 66 | 0.20 | -0.09 | 0.35 | yes |
| 30 | ladder | 116 | 13,424 | 260 | 6.00 | 0.06 | 0.19 | 0.15 | 89.00 | 105.00 | 0.35 | 5.12 | 59 | 0.26 | -0.08 | 0.37 | no |
| 40 | P60 | 89 | 12,199 | 257 | 7.05 | 0.07 | 0.22 | 0.15 | 69.00 | 83.00 | 0.37 | 5.33 | 54 | 0.11 | -0.18 | 0.30 | no |
| 45 | ladder | 82 | 11,807 | 255 | 7.45 | 0.09 | 0.23 | 0.15 | 64.00 | 76.00 | 0.38 | 5.39 | 49 | 0.08 | -0.20 | 0.29 | no |
| 60 | ladder | 67 | 10,799 | 253 | 7.98 | 0.09 | 0.24 | 0.15 | 50.00 | 62.00 | 0.40 | 5.57 | 37 | 0.10 | -0.25 | 0.36 | no |
| 72 | P75 | 54 | 9,663 | 251 | 9.02 | 0.14 | 0.27 | 0.15 | 40.00 | 51.00 | 0.42 | 5.81 | 32 | 0.11 | -0.21 | 0.41 | no |
| 90 | ladder | 43 | 8,482 | 245 | 10.16 | 0.14 | 0.29 | 0.16 | 30.00 | 40.00 | 0.46 | 6.20 | 28 | -0.07 | -0.36 | 0.35 | no |
| 120 | ladder | 29 | 6,584 | 220 | 11.96 | 0.19 | 0.32 | 0.16 | 18.00 | 27.00 | 0.48 | 6.42 | 16 | 0.20 | -0.38 | 0.50 | no |


### T20I batters (k = 25.00, W = 1.47, VAL/TRAIN ball ratio = 0.47)
| t | source | players | balls | matches | median n_eff | marginal B | median B | median interval width | pool 2.5% | pool 97.5% | boot Jaccard top10 | exp. top10 overlap | repro n | repro rho | lo | hi | Phase 3 placeholder value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | P10 | 448 | 20,501 | 340 | 2.42 | 0.04 | 0.09 | 0.11 | 356.00 | 398.00 | 0.32 | 4.74 | 162 | 0.44 | 0.18 | 0.44 | no |
| 6 | P25+ladder | 386 | 20,105 | 340 | 2.75 | 0.04 | 0.10 | 0.11 | 301.00 | 340.00 | 0.33 | 4.84 | 146 | 0.40 | 0.15 | 0.43 | no |
| 12 | ladder | 291 | 18,891 | 339 | 3.38 | 0.04 | 0.12 | 0.12 | 220.00 | 252.00 | 0.33 | 4.90 | 106 | 0.33 | 0.03 | 0.40 | no |
| 16 | P50 | 243 | 17,933 | 338 | 3.78 | 0.04 | 0.13 | 0.12 | 183.00 | 211.00 | 0.33 | 4.88 | 93 | 0.27 | 0.00464 | 0.39 | no |
| 18 | ladder | 226 | 17,507 | 335 | 3.96 | 0.04 | 0.14 | 0.12 | 168.00 | 195.00 | 0.33 | 4.87 | 87 | 0.25 | -0.03 | 0.38 | no |
| 23 | P60 | 183 | 16,211 | 328 | 4.68 | 0.04 | 0.16 | 0.13 | 137.00 | 159.00 | 0.34 | 4.94 | 70 | 0.27 | -0.05 | 0.39 | no |
| 24 | ladder | 177 | 16,006 | 328 | 4.69 | 0.04 | 0.16 | 0.12 | 131.00 | 153.00 | 0.34 | 4.96 | 67 | 0.25 | -0.06 | 0.39 | yes |
| 30 | ladder | 147 | 14,822 | 317 | 5.38 | 0.06 | 0.18 | 0.13 | 106.00 | 126.02 | 0.34 | 4.98 | 54 | 0.12 | -0.17 | 0.32 | no |
| 41 | P75 | 101 | 12,465 | 301 | 6.58 | 0.07 | 0.21 | 0.14 | 73.00 | 90.00 | 0.35 | 5.06 | 41 | 0.17 | -0.15 | 0.37 | no |
| 45 | ladder | 95 | 12,089 | 300 | 6.74 | 0.07 | 0.21 | 0.14 | 68.00 | 84.00 | 0.35 | 5.04 | 39 | 0.14 | -0.15 | 0.36 | no |
| 60 | ladder | 66 | 9,871 | 281 | 7.52 | 0.10 | 0.23 | 0.14 | 44.00 | 58.00 | 0.40 | 5.58 | 31 | 0.00484 | -0.23 | 0.34 | no |
| 90 | ladder | 38 | 6,980 | 241 | 8.97 | 0.15 | 0.26 | 0.14 | 21.00 | 33.00 | 0.46 | 6.23 | 12 | n/a | n/a | n/a | no |
| 120 | ladder | 17 | 3,877 | 182 | 9.72 | 0.21 | 0.28 | 0.14 | 8.00 | 15.00 | 0.59 | 7.29 | 7 | n/a | n/a | n/a | no |


### IPL bowlers (k = 25.00, W = 1.31, VAL/TRAIN ball ratio = 0.31)
| t | source | players | balls | matches | median n_eff | marginal B | median B | median interval width | pool 2.5% | pool 97.5% | boot Jaccard top10 | exp. top10 overlap | repro n | repro rho | lo | hi | Phase 3 placeholder value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | ladder | 163 | 15,847 | 261 | 4.25 | 0.04 | 0.15 | 0.14 | 138.00 | 153.00 | 0.43 | 5.95 | 79 | 0.19 | -0.12 | 0.28 | no |
| 7 | P10 | 160 | 15,822 | 261 | 4.32 | 0.04 | 0.15 | 0.14 | 134.00 | 149.00 | 0.43 | 5.95 | 78 | 0.16 | -0.14 | 0.26 | no |
| 12 | ladder | 140 | 15,578 | 261 | 5.61 | 0.04 | 0.18 | 0.15 | 117.00 | 132.00 | 0.44 | 6.03 | 76 | 0.17 | -0.14 | 0.27 | no |
| 18 | P25+ladder | 123 | 15,241 | 261 | 6.56 | 0.04 | 0.21 | 0.16 | 103.00 | 117.00 | 0.44 | 6.02 | 72 | 0.20 | -0.13 | 0.28 | no |
| 24 | ladder | 106 | 14,780 | 260 | 8.12 | 0.07 | 0.25 | 0.17 | 90.00 | 101.00 | 0.44 | 6.05 | 63 | 0.17 | -0.15 | 0.27 | no |
| 36 | ladder | 94 | 14,327 | 260 | 9.36 | 0.09 | 0.27 | 0.18 | 77.00 | 90.00 | 0.45 | 6.08 | 56 | 0.16 | -0.16 | 0.28 | yes |
| 48 | ladder | 81 | 13,609 | 259 | 10.06 | 0.12 | 0.29 | 0.18 | 65.00 | 77.00 | 0.46 | 6.20 | 48 | 0.19 | -0.13 | 0.30 | no |
| 49 | P50 | 80 | 13,545 | 259 | 10.08 | 0.12 | 0.29 | 0.18 | 64.97 | 76.00 | 0.46 | 6.20 | 47 | 0.17 | -0.14 | 0.29 | no |
| 69 | P60 | 63 | 12,250 | 256 | 11.72 | 0.15 | 0.32 | 0.19 | 50.00 | 60.00 | 0.46 | 6.22 | 37 | 0.15 | -0.15 | 0.30 | no |
| 72 | ladder | 60 | 11,972 | 256 | 12.10 | 0.19 | 0.33 | 0.19 | 48.00 | 57.02 | 0.47 | 6.33 | 36 | 0.16 | -0.15 | 0.31 | no |
| 96 | ladder | 49 | 10,817 | 252 | 13.65 | 0.24 | 0.35 | 0.19 | 37.00 | 47.00 | 0.48 | 6.44 | 26 | -0.00991 | -0.30 | 0.28 | no |
| 100 | P75 | 49 | 10,817 | 252 | 13.65 | 0.24 | 0.35 | 0.19 | 36.00 | 46.00 | 0.48 | 6.43 | 24 | 0.03 | -0.29 | 0.31 | no |
| 144 | ladder | 32 | 8,270 | 246 | 16.69 | 0.31 | 0.40 | 0.19 | 20.00 | 30.00 | 0.48 | 6.38 | 13 | n/a | n/a | n/a | no |


### T20I bowlers (k = 25.00, W = 1.47, VAL/TRAIN ball ratio = 0.47)
| t | source | players | balls | matches | median n_eff | marginal B | median B | median interval width | pool 2.5% | pool 97.5% | boot Jaccard top10 | exp. top10 overlap | repro n | repro rho | lo | hi | Phase 3 placeholder value |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | P10+ladder | 303 | 21,263 | 340 | 2.86 | 0.04 | 0.10 | 0.11 | 243.00 | 276.00 | 0.38 | 5.37 | 112 | 0.22 | -0.08 | 0.30 | no |
| 12 | ladder | 253 | 20,604 | 339 | 3.53 | 0.04 | 0.12 | 0.11 | 199.00 | 226.00 | 0.38 | 5.40 | 101 | 0.18 | -0.10 | 0.31 | no |
| 13 | P25 | 234 | 20,254 | 339 | 3.76 | 0.04 | 0.13 | 0.11 | 183.00 | 209.00 | 0.38 | 5.44 | 93 | 0.26 | -0.07 | 0.37 | no |
| 18 | ladder | 195 | 19,345 | 332 | 4.52 | 0.05 | 0.15 | 0.12 | 151.00 | 174.00 | 0.39 | 5.47 | 82 | 0.25 | -0.07 | 0.38 | no |
| 24 | ladder | 162 | 18,338 | 330 | 5.99 | 0.06 | 0.19 | 0.14 | 128.00 | 147.00 | 0.39 | 5.52 | 77 | 0.22 | -0.09 | 0.38 | no |
| 29 | P50 | 141 | 17,529 | 329 | 7.13 | 0.07 | 0.22 | 0.14 | 112.00 | 128.00 | 0.39 | 5.53 | 65 | 0.27 | -0.09 | 0.38 | no |
| 36 | ladder | 116 | 16,345 | 323 | 7.89 | 0.10 | 0.24 | 0.15 | 94.00 | 108.00 | 0.40 | 5.66 | 59 | 0.25 | -0.14 | 0.37 | yes |
| 38 | P60 | 113 | 16,182 | 321 | 7.99 | 0.10 | 0.24 | 0.15 | 91.00 | 105.00 | 0.41 | 5.70 | 58 | 0.27 | -0.13 | 0.39 | no |
| 48 | ladder | 99 | 15,325 | 319 | 8.88 | 0.10 | 0.26 | 0.16 | 77.00 | 92.00 | 0.41 | 5.68 | 44 | 0.22 | -0.19 | 0.39 | no |
| 69 | P75 | 70 | 12,818 | 302 | 11.09 | 0.15 | 0.31 | 0.16 | 51.00 | 65.00 | 0.43 | 5.94 | 32 | 0.16 | -0.25 | 0.43 | no |
| 72 | ladder | 64 | 12,197 | 298 | 11.32 | 0.20 | 0.31 | 0.17 | 47.00 | 60.00 | 0.44 | 5.98 | 30 | 0.23 | -0.21 | 0.47 | no |
| 96 | ladder | 46 | 9,960 | 277 | 12.53 | 0.22 | 0.33 | 0.17 | 29.98 | 41.00 | 0.44 | 6.01 | 21 | 0.37 | -0.19 | 0.56 | no |
| 144 | ladder | 17 | 5,113 | 213 | 17.60 | 0.32 | 0.41 | 0.19 | 11.00 | 17.00 | 0.58 | 7.22 | 9 | n/a | n/a | n/a | no |


## Limitations
- Marginal-player data weight depends on k, which is estimated from few players and frequently sits at its floor; a floor hit means the data show little between-player spread, not that the spread is zero.
- Reproducibility is estimable only with at least 15 players in both periods; otherwise it does not block a candidate and is reported as not estimable.
- The candidate with the best reproducibility among many noisy values is a maximum with no multiplicity correction.
