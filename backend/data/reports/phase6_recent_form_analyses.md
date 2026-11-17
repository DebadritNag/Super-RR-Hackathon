# Phase 6 recent-form analyses (2024-onward and 2025-onward, separate)

Status: EXPERIMENTAL_NOT_VALIDATED. Label: `RECENT_FORM_SEPARATE_ANALYSIS`. INTERNAL. In-sample (`WINDOW_IN_SAMPLE`). TEST outcomes: not used. TEST was opened once in Phase 4 and is not pristine; nothing here is independent validation. Cricsheet: not used. Seed 20260512, 1000 match-cluster bootstrap draws. Code version `0061c9d62abd2c99`. Criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851`.

## 1. What these analyses are
- The primary analysis keeps the full verified pre-test window (TRAIN + VALIDATION, 723 matches). These two windows are additional recent-form analyses with their own tables (`p6_recent_form_2024`, `p6_recent_form_2025`, `p6_recent_form_reliability`). They are never merged into, or used to replace, a primary table.
- Definition: `any|q0.75` (provisional, unchanged). Shrinkage configuration `shrink_tau4` (frozen). The baseline B0 and the pressure thresholds are the TRAIN-fitted ones, so a match has the same residual in every window.
- Window-specific parts are refitted on the window's own rows, in-sample: variance components and `k`, the eligibility scaling, the bootstrap weights and the split-half reliability. No primary `k`, `tau2` or reliability is borrowed.
- 2024-onward mixes rows that were in the B0 fit window (2024, TRAIN) with rows that were not (2025, VALIDATION). 2025-onward has no TRAIN rows, so its residuals are out of the B0 fit window. The column `share_rows_in_b0_fit_window` shows the mix. Comparing the two windows is confounded by this.
- Eligibility thresholds are the four frozen Phase 4 ball thresholds scaled from the TRAIN scale to the window as `ceil(t x window_balls / TRAIN_balls)`. They are provisional (open decision OD-2) and not validated.
- Data weight is `B = n_eff / (n_eff + k)` for the least-experienced eligible individual. The 0.5 gate is only compared against; it is unchanged and every context that fails it stays restricted. `passes_gate_informational` does not publish or unlock anything.
- No player-level score or rank is produced or stored here.

## 2. Window sample counts (from the pre-test frame)

| window | start | format | matches | delivery rows | first date | last date |
|---|---|---|---|---|---|---|
| 2024 | 2024-01-01 | IPL | 145 | 34,388 | 2024-03-22 | 2025-06-03 |
| 2024 | 2024-01-01 | OTHER_T20 | 30 | 6,985 | 2024-10-18 | 2025-11-23 |
| 2024 | 2024-01-01 | T20I | 228 | 51,087 | 2024-01-11 | 2025-12-19 |
| 2025 | 2025-01-01 | IPL | 74 | 17,285 | 2025-03-22 | 2025-06-03 |
| 2025 | 2025-01-01 | OTHER_T20 | 15 | 3,466 | 2025-11-14 | 2025-11-23 |
| 2025 | 2025-01-01 | T20I | 122 | 26,914 | 2025-01-02 | 2025-12-19 |


Match ids: 2025-onward 211 is a subset of 2024-onward 403, which is a subset of the pre-test window 723: True. Pre-test matches per format: {"IPL": 293, "OTHER_T20": 30, "T20I": 400}.

## 3. 2024-onward cells (`RECENT_FORM_SEPARATE_ANALYSIS`)

| format | role | stream | matches | pressure obs | players | share in B0 fit | k | floor hit | threshold | eligible | marginal n_eff | marginal B | B >= 0.5 | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | runs | 131 | 8,036 | 192 | 0.55 | 25.00 | yes | 14.00 | 120 | 1.00 | 0.038 | no | ESTIMATED |
| T20I | batter | runs | 198 | 12,610 | 412 | 0.47 | 25.00 | yes | 15.00 | 233 | 1.00 | 0.038 | no | ESTIMATED |
| IPL | batter | dismissal | 131 | 8,036 | 192 | 0.55 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| T20I | batter | dismissal | 198 | 12,610 | 412 | 0.47 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| IPL | bowler | charged | 131 | 8,399 | 139 | 0.55 | 25.00 | yes | 34.00 | 79 | 1.74 | 0.065 | no | ESTIMATED |
| T20I | bowler | charged | 198 | 13,099 | 266 | 0.47 | 25.00 | yes | 26.00 | 144 | 1.00 | 0.038 | no | ESTIMATED |
| IPL | bowler | wkt | 131 | 8,399 | 139 | 0.55 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| T20I | bowler | wkt | 198 | 13,099 | 266 | 0.47 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |


Primary-stream cells estimated: 4 of 4; cells passing the 0.5 data-weight gate (informational): 0.

## 4. 2025-onward cells (`RECENT_FORM_SEPARATE_ANALYSIS`)

| format | role | stream | matches | pressure obs | players | share in B0 fit | k | floor hit | threshold | eligible | marginal n_eff | marginal B | B >= 0.5 | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | runs | 63 | 3,611 | 139 | 0.00 | 25.00 | yes | 7.00 | 97 | 1.00 | 0.038 | no | ESTIMATED |
| T20I | batter | runs | 103 | 6,666 | 283 | 0.00 | 25.00 | yes | 8.00 | 194 | 1.00 | 0.038 | no | ESTIMATED |
| IPL | batter | dismissal | 63 | 3,611 | 139 | 0.00 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| T20I | batter | dismissal | 103 | 6,666 | 283 | 0.00 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| IPL | bowler | charged | 63 | 3,753 | 101 | 0.00 | 25.00 | yes | 16.00 | 69 | 1.00 | 0.038 | no | ESTIMATED |
| T20I | bowler | charged | 103 | 6,922 | 179 | 0.00 | 25.00 | yes | 14.00 | 125 | 1.00 | 0.038 | no | ESTIMATED |
| IPL | bowler | wkt | 63 | 3,753 | 101 | 0.00 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |
| T20I | bowler | wkt | 103 | 6,922 | 179 | 0.00 | 25.00 | yes |  | 0 |  |  |  | NO_FROZEN_THRESHOLD |


Primary-stream cells estimated: 4 of 4; cells passing the 0.5 data-weight gate (informational): 0.

## 5. Split-half reliability per window (Spearman-Brown corrected, in-sample)

| window | format | role | stream | mode | players | SB | lo (players) | hi (players) | lo (matches) | hi (matches) | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01-01 | IPL | batter | dismissal | early_late | 94 | 0.292 | 0.008 | 0.556 | -0.250 | 0.566 | ESTIMATED |
| 2024-01-01 | IPL | batter | dismissal | odd_even | 91 | 0.025 | -0.436 | 0.362 | -0.430 | 0.516 | ESTIMATED |
| 2024-01-01 | IPL | batter | runs | early_late | 94 | 0.386 | 0.038 | 0.618 | -0.124 | 0.553 | ESTIMATED |
| 2024-01-01 | IPL | batter | runs | odd_even | 91 | 0.575 | 0.303 | 0.733 | 0.059 | 0.635 | ESTIMATED |
| 2024-01-01 | IPL | bowler | charged | early_late | 89 | 0.042 | -0.459 | 0.433 | -0.385 | 0.356 | ESTIMATED |
| 2024-01-01 | IPL | bowler | charged | odd_even | 96 | 0.420 | 0.208 | 0.590 | -0.071 | 0.480 | ESTIMATED |
| 2024-01-01 | IPL | bowler | wkt | early_late | 89 | -0.410 | -1.366 | 0.145 | -0.690 | 0.252 | ESTIMATED |
| 2024-01-01 | IPL | bowler | wkt | odd_even | 96 | 0.039 | -0.460 | 0.360 | -0.460 | 0.311 | ESTIMATED |
| 2024-01-01 | T20I | batter | dismissal | early_late | 157 | 0.169 | -0.061 | 0.346 | -0.344 | 0.363 | ESTIMATED |
| 2024-01-01 | T20I | batter | dismissal | odd_even | 179 | 0.166 | -0.154 | 0.393 | -0.156 | 0.459 | ESTIMATED |
| 2024-01-01 | T20I | batter | runs | early_late | 157 | 0.253 | -0.057 | 0.473 | -0.083 | 0.454 | ESTIMATED |
| 2024-01-01 | T20I | batter | runs | odd_even | 179 | 0.369 | 0.103 | 0.537 | 0.051 | 0.500 | ESTIMATED |
| 2024-01-01 | T20I | bowler | charged | early_late | 160 | 0.127 | -0.251 | 0.391 | -0.195 | 0.415 | ESTIMATED |
| 2024-01-01 | T20I | bowler | charged | odd_even | 164 | 0.132 | -0.331 | 0.447 | -0.202 | 0.441 | ESTIMATED |
| 2024-01-01 | T20I | bowler | wkt | early_late | 160 | 0.134 | -0.149 | 0.391 | -0.230 | 0.313 | ESTIMATED |
| 2024-01-01 | T20I | bowler | wkt | odd_even | 164 | 0.219 | -0.076 | 0.451 | -0.151 | 0.401 | ESTIMATED |
| 2025-01-01 | IPL | batter | dismissal | early_late | 47 | -0.499 | -2.447 | 0.267 | -1.162 | 0.602 | ESTIMATED |
| 2025-01-01 | IPL | batter | dismissal | odd_even | 48 | -0.508 | -1.647 | 0.159 | -0.913 | 0.647 | ESTIMATED |
| 2025-01-01 | IPL | batter | runs | early_late | 47 | 0.176 | -0.533 | 0.526 | -0.563 | 0.494 | ESTIMATED |
| 2025-01-01 | IPL | batter | runs | odd_even | 48 | 0.474 | -0.054 | 0.694 | -0.220 | 0.670 | ESTIMATED |
| 2025-01-01 | IPL | bowler | charged | early_late | 62 | 0.367 | -0.048 | 0.641 | -0.190 | 0.629 | ESTIMATED |
| 2025-01-01 | IPL | bowler | charged | odd_even | 67 | 0.350 | -0.037 | 0.607 | -0.076 | 0.578 | ESTIMATED |
| 2025-01-01 | IPL | bowler | wkt | early_late | 62 | 0.164 | -0.337 | 0.474 | -0.729 | 0.493 | ESTIMATED |
| 2025-01-01 | IPL | bowler | wkt | odd_even | 67 | -0.009 | -0.600 | 0.365 | -0.663 | 0.348 | ESTIMATED |
| 2025-01-01 | T20I | batter | dismissal | early_late | 87 | 0.388 | 0.136 | 0.585 | -0.258 | 0.621 | ESTIMATED |
| 2025-01-01 | T20I | batter | dismissal | odd_even | 102 | 0.402 | 0.210 | 0.556 | -0.266 | 0.561 | ESTIMATED |
| 2025-01-01 | T20I | batter | runs | early_late | 87 | 0.169 | -0.243 | 0.479 | -0.334 | 0.464 | ESTIMATED |
| 2025-01-01 | T20I | batter | runs | odd_even | 102 | 0.149 | -0.283 | 0.425 | -0.223 | 0.547 | ESTIMATED |
| 2025-01-01 | T20I | bowler | charged | early_late | 98 | -0.226 | -0.870 | 0.202 | -0.542 | 0.332 | ESTIMATED |
| 2025-01-01 | T20I | bowler | charged | odd_even | 98 | 0.046 | -0.578 | 0.527 | -0.248 | 0.528 | ESTIMATED |
| 2025-01-01 | T20I | bowler | wkt | early_late | 98 | 0.195 | -0.486 | 0.576 | -0.452 | 0.515 | ESTIMATED |
| 2025-01-01 | T20I | bowler | wkt | odd_even | 98 | 0.290 | -0.275 | 0.650 | -0.216 | 0.517 | ESTIMATED |


An interval that includes 0 gives no evidence of reliability above 0. Early/late splits also measure drift. Each window has fewer matches than the primary window, so intervals are wider.

## 6. Limits
- All fits are in-sample on the window. A shorter window gives fewer pressure balls per individual, which lowers data weight and reliability; the data cannot show that recent form is more informative.
- Differences between the primary window and these windows are descriptive. They are not a validation of either and not a basis for changing the primary window.
- Thresholds are provisional (OD-2). A user decision is needed before any window gets frozen thresholds of its own.
- Every context that fails the data-weight gate stays restricted in every window.
