# Phase 6 eligibility thresholds under the reliability lens

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, descriptive, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not used. Cricsheet: not used. **No threshold was changed and the 0.5 data-weight gate (read from `GATE_B` = 0.5) was not lowered, bypassed or re-defined.** The frozen thresholds stay as they are; this report only shows what reliability and data weight look like at other thresholds. Code version `0061c9d62abd2c99`, seed 20260512, 1000 bootstrap draws. Definition `any|q0.75`, primary streams. Step run-log seq 92 (criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` verified).

## 1. Preconditions
- SHA-256 of the eligibility rules, the gate configuration and the frozen choices is unchanged: equal before and after (eligibility_rules, frozen, gates).
- Ladder reliability reproduces `reliability_by_opportunity` of Phase 5 (PRE_TEST odd/even, 32 steps compared, max abs difference 0.00e+00).
- `k` from the TRAIN fit under `shrink_tau4`: {"IPL|batter": 25.0, "IPL|bowler": 25.0, "T20I|batter": 25.0, "T20I|bowler": 25.0} (floor hit in every cell).

## 2. Reliability by minimum pressure balls (PRE_TEST, Phase 5 ladders)
Each row is the pool of individuals with at least `t` pressure balls in the window. `B marg.` is the data weight of the least-experienced individual in the pool (Kish `n_eff` over match ball counts, `k` as above); `B med.` is the median individual's. Pools shrink as `t` rises, so the figures describe different individuals at each row (a selection effect, not a pure effect of sample size).

### IPL batter

| t balls | pool | estimable | SB | lo (indiv.) | hi (indiv.) | lo (matches) | hi (matches) | marg. n_eff | median n_eff | B marg. | B med. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12.00 | 176 | 144 | 0.39 | 0.11 | 0.59 | 0.13 | 0.57 | 1.00 | 4.50 | 0.04 | 0.15 |
| 18.00 | 149 | 139 | 0.46 | 0.16 | 0.64 | 0.14 | 0.58 | 1.00 | 5.15 | 0.04 | 0.17 |
| 24.00 | 138 | 134 | 0.46 | 0.18 | 0.65 | 0.12 | 0.57 | 1.53 | 5.57 | 0.06 | 0.18 |
| 30.00 | 126 | 125 | 0.53 | 0.29 | 0.69 | 0.17 | 0.59 | 1.69 | 5.81 | 0.06 | 0.19 |
| 45.00 | 106 | 106 | 0.43 | 0.10 | 0.65 | 0.07 | 0.53 | 1.89 | 6.44 | 0.07 | 0.20 |
| 60.00 | 80 | 80 | 0.32 | -0.41 | 0.65 | -0.11 | 0.49 | 2.46 | 7.48 | 0.09 | 0.23 |
| 90.00 | 58 | 58 | 0.17 | -0.79 | 0.62 | -0.49 | 0.43 | 2.46 | 8.10 | 0.09 | 0.24 |
| 120.00 | 42 | 42 | 0.42 | -0.54 | 0.76 | -0.43 | 0.56 | 4.15 | 10.08 | 0.14 | 0.29 |


### IPL bowler

| t balls | pool | estimable | SB | lo (indiv.) | hi (indiv.) | lo (matches) | hi (matches) | marg. n_eff | median n_eff | B marg. | B med. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12.00 | 155 | 135 | 0.41 | 0.17 | 0.60 | -0.10 | 0.49 | 1.00 | 4.50 | 0.04 | 0.15 |
| 18.00 | 136 | 128 | 0.43 | 0.17 | 0.62 | -0.13 | 0.50 | 1.00 | 5.93 | 0.04 | 0.19 |
| 24.00 | 123 | 119 | 0.24 | -0.09 | 0.48 | -0.21 | 0.45 | 1.00 | 6.56 | 0.04 | 0.21 |
| 36.00 | 102 | 102 | 0.36 | 0.05 | 0.59 | -0.24 | 0.45 | 1.85 | 8.71 | 0.07 | 0.26 |
| 48.00 | 94 | 94 | 0.39 | 0.08 | 0.60 | -0.24 | 0.47 | 2.51 | 9.36 | 0.09 | 0.27 |
| 72.00 | 73 | 73 | 0.55 | 0.22 | 0.74 | -0.03 | 0.58 | 3.76 | 10.77 | 0.13 | 0.30 |
| 96.00 | 59 | 59 | 0.50 | 0.13 | 0.70 | -0.12 | 0.58 | 6.00 | 12.25 | 0.19 | 0.33 |
| 144.00 | 43 | 43 | 0.47 | 0.08 | 0.70 | -0.26 | 0.61 | 7.71 | 13.71 | 0.24 | 0.35 |


### T20I batter

| t balls | pool | estimable | SB | lo (indiv.) | hi (indiv.) | lo (matches) | hi (matches) | marg. n_eff | median n_eff | B marg. | B med. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12.00 | 348 | 247 | 0.42 | 0.23 | 0.56 | 0.16 | 0.50 | 1.00 | 2.92 | 0.04 | 0.10 |
| 18.00 | 291 | 233 | 0.38 | 0.14 | 0.53 | 0.11 | 0.47 | 1.00 | 3.38 | 0.04 | 0.12 |
| 24.00 | 243 | 210 | 0.33 | 0.09 | 0.51 | 0.07 | 0.45 | 1.00 | 3.78 | 0.04 | 0.13 |
| 30.00 | 208 | 186 | 0.28 | 0.00211 | 0.48 | 0.04 | 0.44 | 1.00 | 4.17 | 0.04 | 0.14 |
| 45.00 | 147 | 143 | 0.28 | 0.01 | 0.49 | -0.00656 | 0.43 | 1.55 | 5.38 | 0.06 | 0.18 |
| 60.00 | 104 | 103 | 0.41 | 0.14 | 0.61 | 0.00937 | 0.50 | 1.99 | 6.56 | 0.07 | 0.21 |
| 90.00 | 66 | 66 | 0.21 | -0.19 | 0.47 | -0.26 | 0.44 | 2.67 | 7.52 | 0.10 | 0.23 |
| 120.00 | 41 | 41 | 0.33 | -0.19 | 0.64 | -0.21 | 0.55 | 4.51 | 8.71 | 0.15 | 0.26 |


### T20I bowler

| t balls | pool | estimable | SB | lo (indiv.) | hi (indiv.) | lo (matches) | hi (matches) | marg. n_eff | median n_eff | B marg. | B med. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 12.00 | 291 | 231 | 0.25 | 0.03 | 0.43 | -0.10 | 0.40 | 1.00 | 2.97 | 0.04 | 0.11 |
| 18.00 | 253 | 220 | 0.27 | 0.03 | 0.44 | -0.10 | 0.40 | 1.00 | 3.53 | 0.04 | 0.12 |
| 24.00 | 217 | 204 | 0.33 | 0.14 | 0.48 | -0.04 | 0.45 | 1.00 | 3.89 | 0.04 | 0.13 |
| 36.00 | 162 | 158 | 0.35 | 0.10 | 0.53 | -0.10 | 0.45 | 1.68 | 5.99 | 0.06 | 0.19 |
| 48.00 | 128 | 127 | 0.44 | 0.22 | 0.62 | -0.05 | 0.49 | 2.08 | 7.57 | 0.08 | 0.23 |
| 72.00 | 97 | 97 | 0.33 | 0.03 | 0.53 | -0.19 | 0.44 | 3.71 | 8.89 | 0.13 | 0.26 |
| 96.00 | 74 | 74 | 0.29 | -0.05 | 0.52 | -0.21 | 0.45 | 4.42 | 10.49 | 0.15 | 0.30 |
| 144.00 | 45 | 45 | 0.47 | 0.11 | 0.70 | -0.14 | 0.58 | 6.91 | 12.77 | 0.22 | 0.34 |


## 3. Smallest ladder step at which reliability reaches the target
Point estimate, and the step at which the interval lower bound reaches the target (individual bootstrap, match bootstrap). 'none' means the target is not reached within the ladder. A lower bound is the conservative reading; the match-bootstrap interval is not centred on the point estimate.

| format | role | window | target | status | point | lo (indiv.) | lo (matches) |
|---|---|---|---|---|---|---|---|
| IPL | batter | PRE_TEST | 0.50 | TARGET_REACHED | 30.00 | n/a | n/a |
| IPL | batter | PRE_TEST | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | batter | PRE_TEST | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | batter | TRAIN | 0.50 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | batter | TRAIN | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | batter | TRAIN | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | bowler | PRE_TEST | 0.50 | TARGET_REACHED | 72.00 | n/a | n/a |
| IPL | bowler | PRE_TEST | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | bowler | PRE_TEST | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | bowler | TRAIN | 0.50 | TARGET_REACHED | 72.00 | n/a | n/a |
| IPL | bowler | TRAIN | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| IPL | bowler | TRAIN | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | PRE_TEST | 0.50 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | PRE_TEST | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | PRE_TEST | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | TRAIN | 0.50 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | TRAIN | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | batter | TRAIN | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | PRE_TEST | 0.50 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | PRE_TEST | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | PRE_TEST | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | TRAIN | 0.50 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | TRAIN | 0.70 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |
| T20I | bowler | TRAIN | 0.80 | TARGET_NOT_REACHED_WITHIN_LADDER | n/a | n/a | n/a |


## 4. Frozen thresholds and Phase 4 candidates under the same lens (PRE_TEST)
The frozen thresholds are scaled by the window ratio exactly as in Phase 4 and 5. Candidate rows come from `p4_eligibility_candidates`; each is evaluated at its stored scaled threshold.

| format | role | source | threshold (TRAIN scale) | scaled t | pool | estimable | SB | lo (indiv.) | lo (matches) | marg. n_eff | B marg. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | phase4_candidate:P10 | 3.00 | 3.93 | 239 | 144 | 0.39 | 0.11 | 0.18 | 1.00 | 0.04 |
| IPL | batter | phase4_candidate:ladder | 6.00 | 7.86 | 208 | 144 | 0.39 | 0.10 | 0.17 | 1.00 | 0.04 |
| IPL | batter | phase4_candidate:P25 | 8.00 | 10.49 | 184 | 144 | 0.39 | 0.11 | 0.17 | 1.00 | 0.04 |
| IPL | batter | phase4_candidate:ladder | 12.00 | 15.73 | 159 | 143 | 0.41 | 0.14 | 0.13 | 1.00 | 0.04 |
| IPL | batter | phase4_candidate:ladder | 18.00 | 23.59 | 138 | 134 | 0.46 | 0.15 | 0.12 | 1.53 | 0.06 |
| IPL | batter | frozen | 20.00 | 26.22 | 132 | 131 | 0.47 | 0.17 | 0.13 | 1.53 | 0.06 |
| IPL | batter | phase4_candidate:P50 | 20.00 | 26.22 | 132 | 131 | 0.47 | 0.17 | 0.13 | 1.53 | 0.06 |
| IPL | batter | phase4_candidate:ladder | 24.00 | 31.46 | 122 | 121 | 0.45 | 0.15 | 0.11 | 1.69 | 0.06 |
| IPL | batter | phase4_candidate:ladder | 30.00 | 39.32 | 116 | 115 | 0.39 | 0.10 | 0.06 | 1.69 | 0.06 |
| IPL | batter | phase4_candidate:P60 | 40.00 | 52.43 | 89 | 89 | 0.26 | -0.33 | -0.12 | 1.89 | 0.07 |
| IPL | batter | phase4_candidate:ladder | 45.00 | 58.99 | 82 | 82 | 0.28 | -0.46 | -0.15 | 2.46 | 0.09 |
| IPL | batter | phase4_candidate:ladder | 60.00 | 78.65 | 67 | 67 | 0.44 | -0.08 | -0.12 | 2.46 | 0.09 |
| IPL | batter | phase4_candidate:P75 | 72.00 | 94.38 | 54 | 54 | 0.24 | -0.73 | -0.51 | 4.15 | 0.14 |
| IPL | batter | phase4_candidate:ladder | 90.00 | 117.97 | 43 | 43 | 0.38 | -0.60 | -0.42 | 4.15 | 0.14 |
| IPL | batter | phase4_candidate:ladder | 120.00 | 157.30 | 29 | 29 | -0.53 | -2.14 | -1.62 | 5.81 | 0.19 |
| IPL | bowler | phase4_candidate:ladder | 6.00 | 7.85 | 163 | 135 | 0.41 | 0.15 | -0.10 | 1.00 | 0.04 |
| IPL | bowler | phase4_candidate:P10 | 7.00 | 9.16 | 160 | 135 | 0.41 | 0.15 | -0.10 | 1.00 | 0.04 |
| IPL | bowler | phase4_candidate:ladder | 12.00 | 15.70 | 140 | 129 | 0.44 | 0.18 | -0.10 | 1.00 | 0.04 |
| IPL | bowler | phase4_candidate:P25+ladder | 18.00 | 23.54 | 123 | 119 | 0.24 | -0.09 | -0.21 | 1.00 | 0.04 |
| IPL | bowler | phase4_candidate:ladder | 24.00 | 31.39 | 106 | 106 | 0.35 | 0.08 | -0.23 | 1.85 | 0.07 |
| IPL | bowler | phase4_candidate:ladder | 36.00 | 47.09 | 94 | 94 | 0.39 | 0.07 | -0.24 | 2.51 | 0.09 |
| IPL | bowler | phase4_candidate:ladder | 48.00 | 62.78 | 81 | 81 | 0.37 | -0.04 | -0.20 | 3.44 | 0.12 |
| IPL | bowler | frozen | 49.00 | 64.09 | 80 | 80 | 0.45 | 0.06 | -0.09 | 3.44 | 0.12 |
| IPL | bowler | phase4_candidate:P50 | 49.00 | 64.09 | 80 | 80 | 0.45 | 0.03 | -0.09 | 3.44 | 0.12 |
| IPL | bowler | phase4_candidate:P60 | 69.00 | 90.25 | 63 | 63 | 0.52 | 0.20 | -0.09 | 4.25 | 0.15 |
| IPL | bowler | phase4_candidate:ladder | 72.00 | 94.17 | 60 | 60 | 0.51 | 0.13 | -0.11 | 6.00 | 0.19 |
| IPL | bowler | phase4_candidate:ladder | 96.00 | 125.57 | 49 | 49 | 0.42 | 0.00859 | -0.33 | 7.71 | 0.24 |
| IPL | bowler | phase4_candidate:P75 | 100.00 | 130.80 | 49 | 49 | 0.42 | -0.03 | -0.33 | 7.71 | 0.24 |
| IPL | bowler | phase4_candidate:ladder | 144.00 | 188.35 | 32 | 32 | 0.54 | 0.06 | -0.23 | 11.08 | 0.31 |
| T20I | batter | phase4_candidate:P10 | 3.00 | 4.42 | 448 | 247 | 0.42 | 0.21 | 0.18 | 1.00 | 0.04 |
| T20I | batter | phase4_candidate:P25+ladder | 6.00 | 8.85 | 386 | 247 | 0.42 | 0.23 | 0.17 | 1.00 | 0.04 |
| T20I | batter | phase4_candidate:ladder | 12.00 | 17.69 | 291 | 233 | 0.38 | 0.16 | 0.11 | 1.00 | 0.04 |
| T20I | batter | frozen | 16.00 | 23.59 | 243 | 210 | 0.33 | 0.10 | 0.07 | 1.00 | 0.04 |
| T20I | batter | phase4_candidate:P50 | 16.00 | 23.59 | 243 | 210 | 0.33 | 0.10 | 0.07 | 1.00 | 0.04 |
| T20I | batter | phase4_candidate:ladder | 18.00 | 26.54 | 226 | 201 | 0.33 | 0.09 | 0.07 | 1.00 | 0.04 |
| T20I | batter | phase4_candidate:P60 | 23.00 | 33.91 | 183 | 174 | 0.28 | -0.02 | 0.04 | 1.06 | 0.04 |
| T20I | batter | phase4_candidate:ladder | 24.00 | 35.38 | 177 | 168 | 0.32 | 0.05 | 0.05 | 1.06 | 0.04 |
| T20I | batter | phase4_candidate:ladder | 30.00 | 44.23 | 147 | 143 | 0.28 | 0.02 | -0.00656 | 1.55 | 0.06 |
| T20I | batter | phase4_candidate:P75 | 41.00 | 60.44 | 101 | 100 | 0.45 | 0.19 | 0.04 | 1.99 | 0.07 |
| T20I | batter | phase4_candidate:ladder | 45.00 | 66.34 | 95 | 94 | 0.47 | 0.23 | 0.05 | 1.99 | 0.07 |
| T20I | batter | phase4_candidate:ladder | 60.00 | 88.45 | 66 | 66 | 0.21 | -0.22 | -0.26 | 2.67 | 0.10 |
| T20I | batter | phase4_candidate:ladder | 90.00 | 132.68 | 38 | 38 | 0.39 | -0.15 | -0.19 | 4.51 | 0.15 |
| T20I | batter | phase4_candidate:ladder | 120.00 | 176.91 | 17 | 17 | 0.50 | -0.06 | -0.59 | 6.67 | 0.21 |
| T20I | bowler | phase4_candidate:P10+ladder | 6.00 | 8.84 | 303 | 231 | 0.25 | 0.02 | -0.08 | 1.00 | 0.04 |
| T20I | bowler | phase4_candidate:ladder | 12.00 | 17.68 | 253 | 220 | 0.27 | 0.02 | -0.10 | 1.00 | 0.04 |
| T20I | bowler | phase4_candidate:P25 | 13.00 | 19.15 | 234 | 209 | 0.33 | 0.11 | -0.07 | 1.00 | 0.04 |
| T20I | bowler | phase4_candidate:ladder | 18.00 | 26.52 | 195 | 189 | 0.34 | 0.15 | -0.04 | 1.42 | 0.05 |
| T20I | bowler | phase4_candidate:ladder | 24.00 | 35.36 | 162 | 158 | 0.35 | 0.11 | -0.10 | 1.68 | 0.06 |
| T20I | bowler | frozen | 29.00 | 42.73 | 141 | 140 | 0.41 | 0.20 | -0.06 | 1.94 | 0.07 |
| T20I | bowler | phase4_candidate:P50 | 29.00 | 42.73 | 141 | 140 | 0.41 | 0.18 | -0.06 | 1.94 | 0.07 |
| T20I | bowler | phase4_candidate:ladder | 36.00 | 53.04 | 116 | 116 | 0.31 | 0.07 | -0.16 | 2.69 | 0.10 |
| T20I | bowler | phase4_candidate:P60 | 38.00 | 55.99 | 113 | 113 | 0.29 | 0.03 | -0.19 | 2.69 | 0.10 |
| T20I | bowler | phase4_candidate:ladder | 48.00 | 70.72 | 99 | 99 | 0.34 | 0.04 | -0.17 | 2.92 | 0.10 |
| T20I | bowler | phase4_candidate:P75 | 69.00 | 101.66 | 70 | 70 | 0.22 | -0.19 | -0.29 | 4.42 | 0.15 |
| T20I | bowler | phase4_candidate:ladder | 72.00 | 106.08 | 64 | 64 | 0.23 | -0.17 | -0.31 | 6.42 | 0.20 |
| T20I | bowler | phase4_candidate:ladder | 96.00 | 141.45 | 46 | 46 | 0.47 | 0.13 | -0.14 | 6.91 | 0.22 |
| T20I | bowler | phase4_candidate:ladder | 144.00 | 212.17 | 17 | 17 | 0.40 | -0.46 | -0.75 | 11.73 | 0.32 |


## 5. Required balls per individual for reliability targets (descriptive projection)
`n* = R / (1 - R) * sigma_eff / tau2`. E7 is the model-free split-half covariance; E1b assumes independent balls. The range comes from the bootstrap bounds of `tau2`; when the lower bound is not above 0 there is no upper bound on the requirement.

| format | role | source | target | tau2 | tau2 lo | tau2 hi | n* balls | n* lo | n* hi | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | E7_split_half_covariance | 0.50 | 0.05 | 0.03 | 0.13 | 153.79 | 60.74 | 291.88 | ESTIMATED |
| IPL | batter | E7_split_half_covariance | 0.70 | 0.05 | 0.03 | 0.13 | 358.83 | 141.72 | 681.06 | ESTIMATED |
| IPL | batter | E7_split_half_covariance | 0.80 | 0.05 | 0.03 | 0.13 | 615.14 | 242.95 | 1167.53 | ESTIMATED |
| IPL | batter | E1b_ball_independent | 0.50 | 0.08 | 0.08 | 0.27 | 39.38 | 11.49 | 39.85 | ESTIMATED |
| IPL | batter | E1b_ball_independent | 0.70 | 0.08 | 0.08 | 0.27 | 91.89 | 26.82 | 92.99 | ESTIMATED |
| IPL | batter | E1b_ball_independent | 0.80 | 0.08 | 0.08 | 0.27 | 157.53 | 45.97 | 159.41 | ESTIMATED |
| IPL | bowler | E7_split_half_covariance | 0.50 | 0.05 | -0.0097 | 0.08 | 168.33 | 102.45 | n/a | ESTIMATED |
| IPL | bowler | E7_split_half_covariance | 0.70 | 0.05 | -0.0097 | 0.08 | 392.78 | 239.06 | n/a | ESTIMATED |
| IPL | bowler | E7_split_half_covariance | 0.80 | 0.05 | -0.0097 | 0.08 | 673.34 | 409.82 | n/a | ESTIMATED |
| IPL | bowler | E1b_ball_independent | 0.50 | 0.23 | 0.14 | 0.61 | 13.49 | 5.02 | 21.89 | ESTIMATED |
| IPL | bowler | E1b_ball_independent | 0.70 | 0.23 | 0.14 | 0.61 | 31.48 | 11.70 | 51.08 | ESTIMATED |
| IPL | bowler | E1b_ball_independent | 0.80 | 0.23 | 0.14 | 0.61 | 53.96 | 20.07 | 87.56 | ESTIMATED |
| T20I | batter | E7_split_half_covariance | 0.50 | 0.06 | 0.03 | 0.10 | 98.98 | 56.89 | 203.65 | ESTIMATED |
| T20I | batter | E7_split_half_covariance | 0.70 | 0.06 | 0.03 | 0.10 | 230.96 | 132.75 | 475.18 | ESTIMATED |
| T20I | batter | E7_split_half_covariance | 0.80 | 0.06 | 0.03 | 0.10 | 395.94 | 227.57 | 814.59 | ESTIMATED |
| T20I | batter | E1b_ball_independent | 0.50 | 0.08 | 0.10 | 0.35 | 33.02 | 7.93 | 27.55 | ESTIMATED |
| T20I | batter | E1b_ball_independent | 0.70 | 0.08 | 0.10 | 0.35 | 77.05 | 18.49 | 64.27 | ESTIMATED |
| T20I | batter | E1b_ball_independent | 0.80 | 0.08 | 0.10 | 0.35 | 132.09 | 31.70 | 110.18 | ESTIMATED |
| T20I | bowler | E7_split_half_covariance | 0.50 | 0.03 | -0.00976 | 0.06 | 258.01 | 102.58 | n/a | ESTIMATED |
| T20I | bowler | E7_split_half_covariance | 0.70 | 0.03 | -0.00976 | 0.06 | 602.02 | 239.35 | n/a | ESTIMATED |
| T20I | bowler | E7_split_half_covariance | 0.80 | 0.03 | -0.00976 | 0.06 | 1032.03 | 410.31 | n/a | ESTIMATED |
| T20I | bowler | E1b_ball_independent | 0.50 | 0.20 | 0.19 | 0.42 | 13.41 | 6.47 | 14.64 | ESTIMATED |
| T20I | bowler | E1b_ball_independent | 0.70 | 0.20 | 0.19 | 0.42 | 31.28 | 15.10 | 34.17 | ESTIMATED |
| T20I | bowler | E1b_ball_independent | 0.80 | 0.20 | 0.19 | 0.42 | 53.63 | 25.88 | 58.58 | ESTIMATED |


The bootstrap interval of `tau2` is not centred on the point estimate (the resampled estimate is shifted upward, as noted for E6 in the variance report). In 3 of 18 projection rows that have both bounds, the point requirement lies outside its own interval; read the range as a rough sensitivity band, not a confidence interval.

## 6. Balls at which the Phase 4 data weight reaches 0.5 (measured)
Under the Phase 4 basis B = 0.5 iff the Kish count `n_eff` equals `k`. `n_eff` cannot exceed the number of matches played, so an individual needs at least `k` matches. Counts below are measured in the cell, not assumed.

| format | role | window | k | individuals | n_eff >= k | min balls among them | median balls among them | max n_eff |
|---|---|---|---|---|---|---|---|---|
| IPL | batter | PRE_TEST | 25.00 | 267 | 0 | n/a | n/a | 16.66 |
| IPL | batter | TRAIN | 25.00 | 244 | 0 | n/a | n/a | 14.60 |
| IPL | bowler | PRE_TEST | 25.00 | 182 | 1 | 434.00 | 434.00 | 25.45 |
| IPL | bowler | TRAIN | 25.00 | 163 | 0 | n/a | n/a | 21.66 |
| T20I | batter | PRE_TEST | 25.00 | 537 | 0 | n/a | n/a | 17.62 |
| T20I | batter | TRAIN | 25.00 | 439 | 0 | n/a | n/a | 14.84 |
| T20I | bowler | PRE_TEST | 25.00 | 359 | 1 | 425.00 | 425.00 | 28.89 |
| T20I | bowler | TRAIN | 25.00 | 296 | 0 | n/a | n/a | 23.64 |


## 7. Reading the numbers
- Within the ladders the point estimate of the odd/even reliability reaches 0.5 in 2 of 4 cells, 0.7 in 0 and 0.8 in 0 (PRE_TEST).
- Across the 32 estimable ladder pools the SB runs from 0.17 to 0.55; the individual-bootstrap lower bound is above 0 in 25 and the match-bootstrap lower bound in 10 of them.
- Individuals whose Kish count reaches k (data weight 0.5): 2 of 1345 across the four cells. A threshold on balls alone does not lift the marginal individual to B = 0.5; that needs at least k distinct matches.
- At the frozen thresholds (scaled), odd/even SB: IPL batter 0.47, IPL bowler 0.45, T20I batter 0.33, T20I bowler 0.41.
- Interval lower bound at or above the target within the ladder (PRE_TEST, cells of 4): individual bootstrap R 0.5: 0, R 0.7: 0, R 0.8: 0; match bootstrap R 0.5: 0, R 0.7: 0, R 0.8: 0. 'n/a' in section 3 means the target is not reached.
- This is descriptive; no threshold is changed here.

## 8. Limits
- In-sample on TRAIN and VALIDATION; the baseline and the frozen thresholds were fitted there. Nothing here validates a threshold. Thresholds stay `THRESHOLD_NOT_VALIDATED`.
- Raising `t` selects heavier-usage individuals, which changes who is in the pool as well as how much data each has.
- The projections inherit the identification problem of the variance estimates (`phase6_variance_floor_investigation.md`): where `tau2` is not distinguishable from 0 the requirement has no upper bound.
- The ladder stops at 120 (batters) and 144 (bowlers) balls; a target not reached inside it may still be reached beyond it.
