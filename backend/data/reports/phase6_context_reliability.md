# Phase 6 context-specific reliability (phase, chase, innings)

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not used. Cricsheet: not used. The 0.5 data-weight gate is read from `app.phase4.eligibility.GATE_B` (= 0.5) and was not changed, lowered or bypassed; this report never sets a gate state. Contexts that fail the gate stay restricted. Code version `0061c9d62abd2c99`, seed 20260512, 1000 bootstrap draws, 200 random splits. Step run-log seq 91 (criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` verified).

## 1. Preconditions
- Recomputed marginal data weight and eligible counts against `p5_context_eligibility_rules`: 48/48 contexts compared, max abs difference in B 0.00e+00, gate-state differences 0, eligible-count differences 0, reproduces = True.
- ALL/ALL context against the primary format x role cell of `any|q0.75` (odd/even, PRE_TEST): equal in 4/4 cells.

## 2. Data weight of the marginal eligible player (copied gate state, recomputed number)
`B = n_eff / (n_eff + k)` with `n_eff` the Kish count over per-match ball counts of the least-experienced eligible player and `k` from the TRAIN fit under `shrink_tau4` (the floor decides k in every context). B reaches the gate only when `n_eff >= k` (B = 0.5 iff n_eff = k). The stored eligibility threshold of each context is used unchanged.

| format | role | phase | situation | matches | eligible | marginal n_eff | k | B | gate | gate passed | n_eff needed | gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 260 | 132 | 1.53 | 25.00 | 0.06 | 0.50 | no | 25.00 | 23.47 |
| IPL | batter | ALL | chase | 169 | 111 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | ALL | first_innings | 158 | 94 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | powerplay | ALL | 134 | 42 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | powerplay | chase | 30 | 19 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | powerplay | first_innings | 108 | 38 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | middle | ALL | 224 | 91 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | middle | chase | 125 | 68 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | middle | first_innings | 125 | 64 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | death | ALL | 242 | 103 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | death | chase | 164 | 89 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | batter | death | first_innings | 110 | 69 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | ALL | ALL | 261 | 80 | 3.44 | 25.00 | 0.12 | 0.50 | no | 25.00 | 21.56 |
| IPL | bowler | ALL | chase | 170 | 74 | 1.93 | 25.00 | 0.07 | 0.50 | no | 25.00 | 23.07 |
| IPL | bowler | ALL | first_innings | 158 | 68 | 1.92 | 25.00 | 0.07 | 0.50 | no | 25.00 | 23.08 |
| IPL | bowler | powerplay | ALL | 134 | 42 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | powerplay | chase | 30 | 21 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | powerplay | first_innings | 108 | 41 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | middle | ALL | 224 | 69 | 2.83 | 25.00 | 0.10 | 0.50 | no | 25.00 | 22.17 |
| IPL | bowler | middle | chase | 125 | 67 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | middle | first_innings | 125 | 57 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| IPL | bowler | death | ALL | 243 | 70 | 2.60 | 25.00 | 0.09 | 0.50 | no | 25.00 | 22.40 |
| IPL | bowler | death | chase | 165 | 60 | 1.89 | 25.00 | 0.07 | 0.50 | no | 25.00 | 23.11 |
| IPL | bowler | death | first_innings | 110 | 52 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | ALL | ALL | 340 | 243 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | ALL | chase | 217 | 199 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | ALL | first_innings | 212 | 172 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | powerplay | ALL | 164 | 64 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | powerplay | chase | 44 | 36 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | powerplay | first_innings | 121 | 48 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | middle | ALL | 292 | 179 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | middle | chase | 162 | 122 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | middle | first_innings | 170 | 114 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | death | ALL | 311 | 171 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | death | chase | 203 | 159 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | batter | death | first_innings | 167 | 105 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | ALL | ALL | 341 | 141 | 1.94 | 25.00 | 0.07 | 0.50 | no | 25.00 | 23.06 |
| T20I | bowler | ALL | chase | 218 | 121 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | ALL | first_innings | 212 | 121 | 1.07 | 25.00 | 0.04 | 0.50 | no | 25.00 | 23.93 |
| T20I | bowler | powerplay | ALL | 164 | 61 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | powerplay | chase | 44 | 19 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | powerplay | first_innings | 121 | 48 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | middle | ALL | 292 | 113 | 1.54 | 25.00 | 0.06 | 0.50 | no | 25.00 | 23.46 |
| T20I | bowler | middle | chase | 162 | 72 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | middle | first_innings | 170 | 85 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | death | ALL | 312 | 110 | 2.00 | 25.00 | 0.07 | 0.50 | no | 25.00 | 23.00 |
| T20I | bowler | death | chase | 204 | 92 | 1.00 | 25.00 | 0.04 | 0.50 | no | 25.00 | 24.00 |
| T20I | bowler | death | first_innings | 167 | 68 | 1.22 | 25.00 | 0.05 | 0.50 | no | 25.00 | 23.78 |


Contexts passing the gate: 0/48. Every context that fails stays restricted: it is excluded from any public output and no ranking is published from it.

## 3. Split-half reliability per context (PRE_TEST)
Odd/even Spearman-Brown reliability with a bootstrap over individuals and a bootstrap over matches, the median of 200 random splits, and the model-free signal share (cov of half means over variance of individual means). Individuals are those with at least 6 balls in each half.

| format | role | phase | situation | indiv. | SB odd/even | lo (indiv.) | hi (indiv.) | lo (matches) | hi (matches) | SB random | signal share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | 144 | 0.39 | 0.11 | 0.60 | 0.17 | 0.59 | 0.35 | 0.38 |
| IPL | batter | ALL | chase | 103 | 0.45 | 0.17 | 0.67 | 0.11 | 0.61 | 0.39 | 0.44 |
| IPL | batter | ALL | first_innings | 96 | 0.52 | 0.21 | 0.71 | -4.79e-05 | 0.64 | 0.33 | 0.55 |
| IPL | batter | powerplay | ALL | 35 | 0.05 | -1.23 | 0.63 | -0.78 | 0.58 | 0.28 | 0.05 |
| IPL | batter | powerplay | chase | 8 | n/a | n/a | n/a | n/a | n/a | n/a | -0.72 |
| IPL | batter | powerplay | first_innings | 20 | 0.64 | -0.07 | 0.93 | -0.57 | 0.87 | 0.64 | 0.66 |
| IPL | batter | middle | ALL | 95 | -0.23 | -0.91 | 0.24 | -0.52 | 0.39 | -0.14 | -0.24 |
| IPL | batter | middle | chase | 59 | 0.38 | -0.15 | 0.69 | -0.61 | 0.56 | 0.24 | 0.46 |
| IPL | batter | middle | first_innings | 59 | 0.04 | -0.62 | 0.45 | -0.43 | 0.54 | -0.06 | 0.05 |
| IPL | batter | death | ALL | 92 | 0.31 | -0.14 | 0.59 | -0.00189 | 0.61 | 0.32 | 0.32 |
| IPL | batter | death | chase | 63 | 0.30 | -0.12 | 0.58 | -0.16 | 0.59 | 0.36 | 0.29 |
| IPL | batter | death | first_innings | 44 | 0.36 | -0.33 | 0.70 | -0.47 | 0.68 | 0.19 | 0.38 |
| IPL | bowler | ALL | ALL | 135 | 0.41 | 0.15 | 0.59 | -0.08 | 0.49 | 0.23 | 0.46 |
| IPL | bowler | ALL | chase | 107 | 0.39 | 0.02 | 0.62 | -0.13 | 0.49 | 0.26 | 0.43 |
| IPL | bowler | ALL | first_innings | 96 | 0.36 | 0.05 | 0.58 | -0.20 | 0.48 | 0.26 | 0.42 |
| IPL | bowler | powerplay | ALL | 35 | 0.18 | -0.67 | 0.59 | -0.93 | 0.54 | 0.33 | 0.18 |
| IPL | bowler | powerplay | chase | 12 | -0.70 | -3.49 | 0.25 | -10.90 | 0.77 | -0.42 | -0.82 |
| IPL | bowler | powerplay | first_innings | 22 | 0.07 | -1.33 | 0.65 | -1.11 | 0.67 | 0.29 | 0.08 |
| IPL | bowler | middle | ALL | 103 | 0.19 | -0.22 | 0.45 | -0.21 | 0.39 | 0.07 | 0.22 |
| IPL | bowler | middle | chase | 74 | -0.29 | -1.13 | 0.23 | -0.75 | 0.40 | -0.34 | -0.30 |
| IPL | bowler | middle | first_innings | 72 | 0.34 | -0.05 | 0.60 | -0.24 | 0.55 | 0.25 | 0.36 |
| IPL | bowler | death | ALL | 92 | -0.09 | -0.86 | 0.37 | -0.57 | 0.33 | -0.03 | -0.10 |
| IPL | bowler | death | chase | 77 | 0.07 | -0.56 | 0.49 | -0.43 | 0.48 | -0.03 | 0.08 |
| IPL | bowler | death | first_innings | 61 | 0.26 | -0.44 | 0.60 | -0.55 | 0.56 | 0.28 | 0.29 |
| T20I | batter | ALL | ALL | 247 | 0.42 | 0.21 | 0.56 | 0.17 | 0.48 | 0.44 | 0.42 |
| T20I | batter | ALL | chase | 140 | 0.41 | 0.20 | 0.57 | 0.14 | 0.55 | 0.33 | 0.45 |
| T20I | batter | ALL | first_innings | 126 | 0.31 | -0.15 | 0.57 | -0.32 | 0.50 | 0.29 | 0.33 |
| T20I | batter | powerplay | ALL | 37 | 0.11 | -0.72 | 0.57 | -0.91 | 0.63 | 0.06 | 0.11 |
| T20I | batter | powerplay | chase | 10 | -3.12 | -18.05 | -0.91 | -31.73 | 0.74 | n/a | -4.58 |
| T20I | batter | powerplay | first_innings | 16 | 0.83 | 0.36 | 0.95 | -1.81 | 0.87 | 0.55 | 0.77 |
| T20I | batter | middle | ALL | 143 | -0.02 | -0.55 | 0.32 | -0.43 | 0.35 | 0.15 | -0.02 |
| T20I | batter | middle | chase | 81 | 0.03 | -0.68 | 0.40 | -0.78 | 0.49 | -0.11 | 0.03 |
| T20I | batter | middle | first_innings | 83 | 0.09 | -0.42 | 0.45 | -0.49 | 0.47 | 0.17 | 0.10 |
| T20I | batter | death | ALL | 144 | 0.58 | 0.44 | 0.71 | 0.21 | 0.66 | 0.51 | 0.60 |
| T20I | batter | death | chase | 57 | 0.49 | 0.07 | 0.72 | -0.05 | 0.69 | 0.54 | 0.43 |
| T20I | batter | death | first_innings | 60 | 0.26 | -0.27 | 0.57 | -0.43 | 0.52 | 0.17 | 0.28 |
| T20I | bowler | ALL | ALL | 231 | 0.25 | 0.01 | 0.44 | -0.07 | 0.40 | 0.20 | 0.28 |
| T20I | bowler | ALL | chase | 145 | 0.23 | -0.09 | 0.46 | -0.28 | 0.42 | 0.22 | 0.25 |
| T20I | bowler | ALL | first_innings | 140 | 0.24 | -0.05 | 0.45 | -0.11 | 0.43 | 0.17 | 0.27 |
| T20I | bowler | powerplay | ALL | 48 | 0.23 | -0.19 | 0.50 | -0.54 | 0.61 | 0.33 | 0.23 |
| T20I | bowler | powerplay | chase | 18 | 0.28 | -1.15 | 0.63 | -3.30 | 0.79 | 0.12 | 0.28 |
| T20I | bowler | powerplay | first_innings | 27 | 0.33 | -0.18 | 0.73 | -0.71 | 0.77 | 0.38 | 0.37 |
| T20I | bowler | middle | ALL | 167 | 0.21 | -0.13 | 0.47 | -0.24 | 0.40 | 0.23 | 0.22 |
| T20I | bowler | middle | chase | 87 | 0.28 | -0.19 | 0.57 | -0.52 | 0.49 | 0.14 | 0.28 |
| T20I | bowler | middle | first_innings | 101 | 0.20 | -0.23 | 0.51 | -0.21 | 0.50 | 0.25 | 0.20 |
| T20I | bowler | death | ALL | 163 | 0.06 | -0.27 | 0.27 | -0.31 | 0.33 | -0.01 | 0.06 |
| T20I | bowler | death | chase | 107 | -0.03 | -0.56 | 0.31 | -0.51 | 0.40 | 0.08 | -0.04 |
| T20I | bowler | death | first_innings | 93 | -0.03 | -0.63 | 0.32 | -0.72 | 0.30 | 0.09 | -0.03 |


## 4. By dimension (the 48 contexts overlap: ALL rows contain the specific ones)

| dimension | value | estimable | of | SB median | min | max | player lo > 0 | match lo > 0 | median indiv. | median balls |
|---|---|---|---|---|---|---|---|---|---|---|
| phase | ALL | 12 | 12 | 0.39 | 0.23 | 0.52 | 9 | 4 | 137.50 | 10591.50 |
| phase | death | 12 | 12 | 0.26 | -0.09 | 0.58 | 2 | 1 | 84.50 | 4090.50 |
| phase | middle | 12 | 12 | 0.14 | -0.29 | 0.38 | 0 | 0 | 85.00 | 5363.50 |
| phase | powerplay | 11 | 12 | 0.18 | -3.12 | 0.83 | 1 | 0 | 22.00 | 1265.00 |
| situation | ALL | 16 | 16 | 0.20 | -0.23 | 0.58 | 5 | 3 | 119.00 | 7780.50 |
| situation | chase | 15 | 16 | 0.28 | -3.12 | 0.49 | 4 | 2 | 77.00 | 4158.00 |
| situation | first_innings | 16 | 16 | 0.29 | -0.03 | 0.83 | 3 | 0 | 66.50 | 3902.50 |
| format | IPL | 23 | 24 | 0.30 | -0.70 | 0.64 | 6 | 2 | 74.00 | 3956.00 |
| format | T20I | 24 | 24 | 0.23 | -3.12 | 0.83 | 6 | 3 | 97.00 | 5363.50 |
| role | batter | 23 | 24 | 0.31 | -3.12 | 0.83 | 8 | 5 | 81.00 | 4679.00 |
| role | bowler | 24 | 24 | 0.22 | -0.70 | 0.41 | 4 | 0 | 92.50 | 4631.00 |


## 5. ALL/ALL check against the primary cells

| format | role | context indiv. | cell indiv. | context SB | cell SB | equal |
|---|---|---|---|---|---|---|
| IPL | batter | 144 | 144 | 0.39 | 0.39 | yes |
| IPL | bowler | 135 | 135 | 0.41 | 0.41 | yes |
| T20I | batter | 247 | 247 | 0.42 | 0.42 | yes |
| T20I | bowler | 231 | 231 | 0.25 | 0.25 | yes |


## 6. Reading the numbers
- 47 of 48 contexts are estimable for odd/even reliability. The SB median is 0.25; the lower bound of the individual-bootstrap interval is above 0 in 12 contexts and that of the match-bootstrap interval in 5. The match-bootstrap interval is not centred on the point estimate (about 37% of matches are dropped in each draw, which adds noise to the half means), so its lower bound is conservative.
- Reliability by phase and situation is read from section 4. Because the specific contexts hold fewer balls, their intervals are wider; a lower SB there is not by itself evidence that the pressure signal differs by phase.
- The data-weight failure is structural under the Phase 4 basis: B reaches 0.5 only for an eligible player whose match-equivalent count `n_eff` is at least `k` = 25, that is 25 matches of equal ball counts, while the least-experienced eligible player has `n_eff` between 1.00 and 3.44 across the contexts.

## 7. Limits
- In-sample on TRAIN and VALIDATION; the thresholds and k come from TRAIN. Nothing here is validation, and TEST (opened once in Phase 4, not pristine) is not used.
- 48 contexts are examined without multiplicity correction. Stored thresholds are working values and are not validated.
- Stored rows hold match-level sums, so within-innings dependence cannot be modelled.
