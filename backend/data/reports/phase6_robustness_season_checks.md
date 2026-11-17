# Phase 6 season-by-season robustness checks (ROBUSTNESS_NOT_VALIDATION)

Status: EXPERIMENTAL_NOT_VALIDATED. Label: `ROBUSTNESS_NOT_VALIDATION`. INTERNAL. These checks are robustness analyses, NOT validation. TEST was opened once in Phase 4 (single opening) and is not pristine. `PRIMARY_RESTRICTED` (99 matches) is kept for internal diagnostic comparisons only; `STRICT_OFFICIAL_ONLY` (0 matches) is a separate set. No independent out-of-sample validation is claimed. Cricsheet: not used. TEST outcomes: not used. Seed 20260512, 1000 player-bootstrap draws. Code version `0061c9d62abd2c99`. Criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851`.

## 1. Scope and reading guide
- Definition `any|q0.75` (provisional), primary streams (batter runs, bowler charged runs), IPL and T20I separately, seasons 2022 to 2025 (calendar years) inside the pre-test window.
- `within_season`: odd/even split-half reliability inside one season (Spearman-Brown).
- `adjacent_seasons`: Spearman correlation of individual mean residuals between season s and s+1, individuals with at least 12 pressure balls in both.
- `leave_one_season_out_rank`: the same correlation between season s and all other seasons.
- `leave_one_season_out_reliability`: odd/even reliability of all other seasons pooled, next to the full pre-test value (`reference_value`).
- Consistency across seasons does not show that the measure captures pressure skill. The baseline and thresholds were fitted on TRAIN (to 2024-12-31) and the seasons share the same individuals, so the checks are in-sample and not independent.
- Units with fewer than 10 individuals are `NOT_ESTIMABLE`.

## 2. Counts
- Rows 60; estimable 60; not estimable 0.

## 3. Within-season split-half reliability

| format | role | season | other | matches | players | value | lo | hi | full-window SB | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 2022 |  | 60 | 50 | 0.298 | -0.422 | 0.648 | 0.391 | ESTIMATED |
| IPL | batter | 2023 |  | 69 | 67 | 0.107 | -0.431 | 0.458 | 0.391 | ESTIMATED |
| IPL | batter | 2024 |  | 68 | 64 | 0.290 | -0.229 | 0.580 | 0.391 | ESTIMATED |
| IPL | batter | 2025 |  | 63 | 48 | 0.474 | -0.022 | 0.693 | 0.391 | ESTIMATED |
| IPL | bowler | 2022 |  | 61 | 61 | 0.064 | -0.556 | 0.424 | 0.414 | ESTIMATED |
| IPL | bowler | 2023 |  | 69 | 67 | -0.281 | -0.933 | 0.264 | 0.414 | ESTIMATED |
| IPL | bowler | 2024 |  | 68 | 67 | 0.136 | -0.375 | 0.453 | 0.414 | ESTIMATED |
| IPL | bowler | 2025 |  | 63 | 67 | 0.350 | -0.072 | 0.610 | 0.414 | ESTIMATED |
| T20I | batter | 2022 |  | 87 | 65 | 0.275 | -0.375 | 0.589 | 0.417 | ESTIMATED |
| T20I | batter | 2023 |  | 55 | 47 | 0.377 | 0.043 | 0.608 | 0.417 | ESTIMATED |
| T20I | batter | 2024 |  | 95 | 92 | 0.522 | 0.228 | 0.696 | 0.417 | ESTIMATED |
| T20I | batter | 2025 |  | 103 | 102 | 0.149 | -0.254 | 0.436 | 0.417 | ESTIMATED |
| T20I | bowler | 2022 |  | 88 | 85 | -0.208 | -0.864 | 0.173 | 0.254 | ESTIMATED |
| T20I | bowler | 2023 |  | 55 | 70 | 0.371 | 0.006 | 0.594 | 0.254 | ESTIMATED |
| T20I | bowler | 2024 |  | 95 | 98 | 0.215 | -0.281 | 0.495 | 0.254 | ESTIMATED |
| T20I | bowler | 2025 |  | 103 | 98 | 0.046 | -0.623 | 0.489 | 0.254 | ESTIMATED |


## 4. Adjacent-season rank correlation

| format | role | season | other | matches | players | value | lo | hi | full-window SB | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 2022 | 2023 | 129 | 47 | 0.343 | 0.062 | 0.574 |  | ESTIMATED |
| IPL | batter | 2023 | 2024 | 137 | 52 | 0.019 | -0.256 | 0.290 |  | ESTIMATED |
| IPL | batter | 2024 | 2025 | 131 | 54 | 0.096 | -0.176 | 0.355 |  | ESTIMATED |
| IPL | bowler | 2022 | 2023 | 130 | 47 | 0.199 | -0.093 | 0.460 |  | ESTIMATED |
| IPL | bowler | 2023 | 2024 | 137 | 47 | 0.172 | -0.121 | 0.438 |  | ESTIMATED |
| IPL | bowler | 2024 | 2025 | 131 | 55 | 0.109 | -0.161 | 0.364 |  | ESTIMATED |
| T20I | batter | 2022 | 2023 | 142 | 39 | 0.253 | -0.068 | 0.526 |  | ESTIMATED |
| T20I | batter | 2023 | 2024 | 150 | 47 | 0.048 | -0.243 | 0.330 |  | ESTIMATED |
| T20I | batter | 2024 | 2025 | 198 | 68 | 0.018 | -0.221 | 0.255 |  | ESTIMATED |
| T20I | bowler | 2022 | 2023 | 143 | 57 | 0.113 | -0.152 | 0.363 |  | ESTIMATED |
| T20I | bowler | 2023 | 2024 | 150 | 60 | 0.016 | -0.239 | 0.269 |  | ESTIMATED |
| T20I | bowler | 2024 | 2025 | 198 | 66 | 0.132 | -0.113 | 0.363 |  | ESTIMATED |


## 5. Leave-one-season-out rank correlation

| format | role | season | other | matches | players | value | lo | hi | full-window SB | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 2022 | all_other | 60 | 66 | 0.255 | 0.014 | 0.469 |  | ESTIMATED |
| IPL | batter | 2023 | all_other | 69 | 71 | 0.254 | 0.022 | 0.460 |  | ESTIMATED |
| IPL | batter | 2024 | all_other | 68 | 83 | 0.151 | -0.067 | 0.355 |  | ESTIMATED |
| IPL | batter | 2025 | all_other | 63 | 67 | 0.293 | 0.057 | 0.498 |  | ESTIMATED |
| IPL | bowler | 2022 | all_other | 61 | 61 | 0.192 | -0.062 | 0.424 |  | ESTIMATED |
| IPL | bowler | 2023 | all_other | 69 | 66 | 0.220 | -0.023 | 0.439 |  | ESTIMATED |
| IPL | bowler | 2024 | all_other | 68 | 70 | 0.043 | -0.194 | 0.275 |  | ESTIMATED |
| IPL | bowler | 2025 | all_other | 63 | 66 | 0.189 | -0.056 | 0.412 |  | ESTIMATED |
| T20I | batter | 2022 | all_other | 87 | 69 | 0.407 | 0.188 | 0.587 |  | ESTIMATED |
| T20I | batter | 2023 | all_other | 55 | 65 | 0.320 | 0.082 | 0.523 |  | ESTIMATED |
| T20I | batter | 2024 | all_other | 95 | 100 | 0.213 | 0.018 | 0.393 |  | ESTIMATED |
| T20I | batter | 2025 | all_other | 103 | 92 | 0.265 | 0.063 | 0.445 |  | ESTIMATED |
| T20I | bowler | 2022 | all_other | 88 | 75 | 0.155 | -0.074 | 0.369 |  | ESTIMATED |
| T20I | bowler | 2023 | all_other | 55 | 88 | 0.195 | -0.015 | 0.389 |  | ESTIMATED |
| T20I | bowler | 2024 | all_other | 95 | 93 | 0.171 | -0.034 | 0.362 |  | ESTIMATED |
| T20I | bowler | 2025 | all_other | 103 | 89 | 0.171 | -0.039 | 0.366 |  | ESTIMATED |


## 6. Reliability of the other seasons pooled (leave one season out)

| format | role | season | other | matches | players | value | lo | hi | full-window SB | status |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 2022 | all_other | 200 | 122 | 0.402 | 0.110 | 0.619 | 0.391 | ESTIMATED |
| IPL | batter | 2023 | all_other | 191 | 125 | 0.359 | 0.005 | 0.577 | 0.391 | ESTIMATED |
| IPL | batter | 2024 | all_other | 192 | 126 | 0.416 | 0.094 | 0.627 | 0.391 | ESTIMATED |
| IPL | batter | 2025 | all_other | 197 | 125 | 0.269 | -0.104 | 0.502 | 0.391 | ESTIMATED |
| IPL | bowler | 2022 | all_other | 200 | 118 | 0.268 | -0.037 | 0.496 | 0.414 | ESTIMATED |
| IPL | bowler | 2023 | all_other | 192 | 118 | 0.338 | 0.063 | 0.563 | 0.414 | ESTIMATED |
| IPL | bowler | 2024 | all_other | 193 | 123 | 0.274 | -0.092 | 0.534 | 0.414 | ESTIMATED |
| IPL | bowler | 2025 | all_other | 198 | 119 | 0.141 | -0.228 | 0.410 | 0.414 | ESTIMATED |
| T20I | batter | 2022 | all_other | 253 | 213 | 0.449 | 0.264 | 0.583 | 0.417 | ESTIMATED |
| T20I | batter | 2023 | all_other | 285 | 221 | 0.322 | 0.076 | 0.504 | 0.417 | ESTIMATED |
| T20I | batter | 2024 | all_other | 245 | 193 | 0.333 | 0.093 | 0.516 | 0.417 | ESTIMATED |
| T20I | batter | 2025 | all_other | 237 | 169 | 0.401 | 0.184 | 0.588 | 0.417 | ESTIMATED |
| T20I | bowler | 2022 | all_other | 253 | 193 | 0.343 | 0.129 | 0.512 | 0.254 | ESTIMATED |
| T20I | bowler | 2023 | all_other | 286 | 207 | 0.142 | -0.213 | 0.405 | 0.254 | ESTIMATED |
| T20I | bowler | 2024 | all_other | 246 | 191 | 0.098 | -0.232 | 0.343 | 0.254 | ESTIMATED |
| T20I | bowler | 2025 | all_other | 238 | 186 | 0.176 | -0.090 | 0.389 | 0.254 | ESTIMATED |


## 7. Summary
- Within-season reliability: 16 estimable units, median 0.245, range -0.281 to 0.522; interval lower bound above 0 in 3.
- Adjacent-season correlation: 12 estimable units, median 0.111, range 0.016 to 0.343; interval lower bound above 0 in 1.
- Intervals use a player bootstrap (reliability) or a Fisher-z approximation (rank correlation) and ignore match clustering, so they are narrower than a match-cluster interval.
- Seasons with few matches give wide intervals; a season that disagrees with the rest is descriptive and does not by itself indicate a defect.
- Nothing here changes the primary window, the 0.5 data-weight gate, the thresholds or any restriction.
