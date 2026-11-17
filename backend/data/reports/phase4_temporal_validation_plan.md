# Phase 4, Stage A: Temporal Validation Plan

Status: `EXPERIMENTAL_NOT_VALIDATED`. `official_ranking = false`. This document fixes the split, the leakage rules and the lock design **before any scoring, definition comparison or test evaluation has run**. Every number below comes from read-only queries on `superr.duckdb` and `exploratory.duckdb`, using only match dates, competition types and pre-delivery state columns. No outcome column (runs, wickets, residuals) was read to produce this document. Counts that depend on a pressure flag use the TRAIN-only quantile of the pre-delivery chase signal `rrr` and are labelled "state-only, approximate"; Chunk 1 recomputes them with the final code.

## 1. Data coverage by format

Matches with ball-by-ball data (`matches.has_deliveries`):

| competition_type | matches | first date | last date | in pressure scope |
|---|---|---|---|---|
| IPL | 367 | 2022-03-26 | 2026-05-31 | yes |
| T20I | 470 | 2022-01-22 | **2026-11-01** | yes |
| OTHER_T20 | 30 | 2024-10-18 | 2025-11-23 | no (never in any population) |

Matches per calendar year (IPL seasons coincide with calendar years):

| year | IPL | T20I | OTHER_T20 |
|---|---|---|---|
| 2022 | 74 | 106 | 0 |
| 2023 | 74 | 66 | 0 |
| 2024 | 71 | 106 | 15 |
| 2025 | 74 | 122 | 15 |
| 2026 | 74 | 70 | 0 |

Same-date matches exist: 64 IPL dates carry 128 matches (double-headers), 70 T20I dates carry 147 matches, 14 OTHER_T20 dates carry 28 matches. The same-day rule for par (section 5) therefore affects real rows.

**Date observation (open decision O3).** 42 T20I matches with deliveries are dated 2026-06-12 to 2026-11-01, after the last IPL date. They are taken as recorded and are not corrected. If those dates are not real, the T20I TEST period is unreliable. A sensitivity (TEST_CORE = dates up to 2026-05-31: 28 T20I matches, all 74 IPL matches) is specified in section 7.

## 2. Chosen boundaries (fixed now)

| period | rule | IPL matches | T20I matches | OTHER_T20 (out of scope) |
|---|---|---|---|---|
| TRAIN | match_date <= 2024-12-31 | 219 | 278 | 15 |
| VALIDATION | 2025-01-01 to 2025-12-31 | 74 | 122 | 15 |
| TEST | match_date >= 2026-01-01 | 74 | 70 | 0 |

Totals: IPL 367, T20I 470, OTHER_T20 30, which equals 867 matches with deliveries. Each match belongs to exactly one period and all its deliveries follow it. There is no row-level or random assignment. The split applies the same calendar boundaries to both formats so the formats can be combined later without a period mismatch.

Deliveries (innings 1 / innings 2, all rows with innings number 1 or 2):

| format | period | innings-1 rows | innings-2 rows |
|---|---|---|---|
| IPL | TRAIN | 27,352 | 25,523 |
| IPL | VALIDATION | 9,113 | 8,162 |
| IPL | TEST | 9,123 | 8,400 |
| T20I | TRAIN | 33,660 | 30,189 |
| T20I | VALIDATION | 14,461 | 12,446 |
| T20I | TEST | 8,345 | 7,214 |

Why these boundaries: they give three IPL seasons for training and one season each for validation and test, and they keep every IPL season whole. A season-internal cut would put part of an IPL season in two periods. Alternatives considered: (a) a random match split, rejected because it breaks chronology; (b) TRAIN through 2025 with VALIDATION as the first half of 2026, rejected because it cuts IPL 2026 in two; (c) rolling-origin only, kept as a secondary scheme (section 6) because three evaluation folds on thin data are less interpretable than one fixed lock.

## 3. Does the history support a meaningful split? (state-only, approximate)

Pressure sample = chase innings, `rrr` at or above the TRAIN-only 0.90 quantile of `rrr` per format (IPL 16.17, T20I 15.38). The thresholds are computed on TRAIN rows only. These rows depend on pre-delivery state, never on outcomes.

| format | period | pressure deliveries | distinct matches |
|---|---|---|---|
| IPL | TRAIN | 2,545 | 116 |
| IPL | VALIDATION | 797 | 31 |
| IPL | TEST | 676 | 27 |
| T20I | TRAIN | 2,938 | 134 |
| T20I | VALIDATION | 1,289 | 53 |
| T20I | TEST | 945 | 32 |

Distribution of pressure balls per player (batter side uses the striker, bowler side uses the bowler; the `rrr` flag is used for both as a state-only proxy for counting):

| cell | period | players | P50 balls | P90 balls | players with >= 24 balls | >= 36 balls | >= 60 balls |
|---|---|---|---|---|---|---|---|
| IPL batter | TRAIN | 160 | 9 | 40 | 37 | 18 | 6 |
| IPL batter | VALIDATION | 79 | 6 | 26 | 12 | 1 | 0 |
| IPL bowler | TRAIN | 106 | 15 | 60 | 38 | 27 | 11 |
| IPL bowler | VALIDATION | 59 | 12 | 25 | 9 | 1 | 0 |
| T20I batter | TRAIN | 254 | 7 | 30 | 35 | 15 | 3 |
| T20I batter | VALIDATION | 124 | 7 | 23 | 12 | 4 | 0 |
| T20I bowler | TRAIN | 166 | 12 | 40 | 34 | 20 | 9 |
| T20I bowler | VALIDATION | 98 | 10.5 | 24 | 10 | 6 | 0 |

**Conclusions (limitations, not invented fixes):**
1. The population-level split is supportable: every format/period has at least 676 pressure deliveries and 27 matches. Definition-level discrimination (pressure rows versus non-pressure rows) can be tested on VALIDATION and TEST.
2. The player-level split is thin. A single validation or test period leaves 0 to 6 players per cell with 36 or more pressure balls, and 0 with 60 or more. Player-to-player stability between TRAIN and a single later period will rest on small numbers of players and wide intervals. Stage D reports the number of players behind every stability correlation and marks a cell `INSUFFICIENT_FOR_PLAYER_LEVEL_TEST` when fewer than 15 players qualify in both periods.
3. Scores that are shown to users are therefore computed on the pooled pre-test window (TRAIN + VALIDATION, scope `PRE_TEST`), not on a single period. The TEST period is evaluated at population level and at player level only where enough players qualify; otherwise the report says so.
4. T20I bowlers and IPL bowlers/batters in TEST will most likely not support a player-level correlation. This is documented, not hidden.

## 4. What each period is used for

| step | data used | data forbidden |
|---|---|---|
| Baseline cell means and shrinkage `k` (train-frozen) | TRAIN deliveries | VALIDATION, TEST |
| Pressure-flag quantile thresholds (per format) | TRAIN state | VALIDATION, TEST |
| Definition comparison and rule application | TRAIN and VALIDATION | TEST outcomes |
| Shrinkage tau2, pooled means, strength choice | TRAIN (strength choice judged on VALIDATION) | TEST |
| Eligibility threshold candidates and choice | TRAIN distributions, judged on TRAIN+VALIDATION | TEST |
| Format-weight sensitivity, ranking stability experiments | PRE_TEST window | TEST |
| Final evaluation | TEST, once, via `evaluate_on_test` | none after the lock opens, no reselection |

Rules:
- Normalisation, baseline cells and shrinkage parameters are estimated on TRAIN only. They are applied unchanged to VALIDATION and TEST rows.
- For TRAIN rows, a player's own balls sit inside the baseline cells. Scoring on TRAIN rows uses the existing leave-one-player-out residual (`pressure_eligibility.lpo_residual`). VALIDATION and TEST residuals are out-of-sample with respect to the baseline.
- A secondary refit of the baseline on TRAIN+VALIDATION before TEST is reported as a sensitivity only. The primary TEST evaluation keeps TRAIN-only parameters.

## 5. Strictly prior par

- Par for a match uses only first-innings source innings from matches with `match_date` strictly before the evaluated match's date, in the same `competition_type`. Matches on the same date are excluded, including the earlier match of a double-header. This is conservative: it ignores some information that was technically available.
- Existing `par_runs_prior` already applies `np.searchsorted(..., side="left")` on dates and `min_prior_innings = 30`; Chunk 1 proves this with a test and reuses it, and adds the missing flag column.
- Insufficient prior history: when fewer than 30 prior source innings exist, par is NULL, `par_unavailable_insufficient_prior = True`, and par-dependent signals are excluded for that row. Nothing is zero-filled and nothing falls back to another format.
- Measured effect on the existing build: IPL first-innings rows with NULL prior par: 3,737 of 45,588 (30 matches, last affected date 2022-04-18). T20I: 3,955 of 56,466 (33 matches, last affected date 2022-07-18). All affected rows lie in TRAIN. VALIDATION and TEST are unaffected.
- Leave-one-match-out par stays available only in the retrospective descriptive table, labelled `DESCRIPTIVE_ONLY_USES_FUTURE_MATCHES`. A guard raises if the scoring pipeline asks for it.
- For TEST matches, strictly prior par includes earlier TEST matches' first innings. That is information a real forecaster would have, but it is TEST outcome data. Decision: TEST par is computed inside `evaluate_on_test` under the open lock. A sensitivity freezes TEST par at 2025-12-31 (no earlier-test information).

## 6. Rolling-origin secondary scheme

Used only for the temporal-stability metric and the baseline-stability check. Origins: 2024-01-01 (train 2022-2023, evaluate 2024) and 2025-01-01 (train 2022-2024, evaluate 2025). At each origin the baseline cells, shrinkage parameters and quantile thresholds are refitted on data before that origin only, so each fold is out-of-sample (the primary TRAIN fit, which includes 2024, is not reused for the 2024 fold). TEST is never used as a fold. The primary TRAIN/VALIDATION/TEST lock is unchanged.

## 7. Test-period lock

- All accessors that return TEST-period outcome columns (`out_*`, `den_*` outcome fields, residuals, per-player outcome aggregates) return a `LockedFrame`. Reading its values before the lock opens raises `TestPeriodLockError` and appends an entry to `data/reports/phase4_lock_log.json` (sequence counter, caller, column set; no wall-clock time so the file is deterministic).
- TEST pre-delivery state columns that do not contain outcomes remain readable because baseline features need them.
- The lock opens only inside `evaluate_on_test(frozen_choices_path)`. That function refuses to run if `phase4_frozen_choices.json` is missing or its recorded SHA-256 differs. Frozen choices hold: pressure definition, TRAIN quantile thresholds, shrinkage configuration, eligibility thresholds, baseline variant, split config hash, rule-file hashes.
- The log must show the lock opened exactly once. After evaluation, no selection step may run.
- TEST_CORE sensitivity (dates up to 2026-05-31) is evaluated in the same single call.

## 8. Leakage checks (automated)

1. Mutating the outcomes of all later matches or all TEST matches leaves TRAIN baselines, par for earlier matches, shrinkage parameters, thresholds and the frozen-choices file byte-identical.
2. Par for a match changes when an earlier match changes and does not change when a same-day or later match changes.
3. No match appears in two periods; every delivery's period equals its match's period; period order is TRAIN < VALIDATION < TEST by date with no overlap.
4. Pressure-flag thresholds computed with VALIDATION or TEST rows removed are identical.
5. The scoring pipeline raises when asked for any LOMO or full-sample par column.
7. Signals: the nine definition flags use only `rrr`, `neg_par_dev_prior`, a TRAIN-fitted expected-remaining curve and TRAIN-fitted percentile maps. `LeakageGuard` rejects `*_lomo` and full-sample rank columns. Mutating all later matches leaves flags for earlier matches unchanged. Rows with no prior par have a NULL flag and are excluded from that candidate's population, with the count reported.
8. Lock audit: the frozen-choices SHA-256 is appended to the lock log as a FREEZE entry (sequence N) before `evaluate_on_test` writes OPEN (N+1); the TEST outcome tables use the prefix `p4_test_locked_`, which only the evaluation module may reference (static test). The lock is a convention-level guard, not a security boundary.
9. Window rules: baseline, `k`, `mu_{-i}` and thresholds are TRAIN-fitted; PRE_TEST eligibility counts use the TRAIN threshold scaled by the window ratio (design notes sections 4 and 6).
6. Leave-one-player-out pooled means exclude the player's own rows (mutating a player's own outcomes leaves their own pooled mean unchanged).

## 9. Determinism

Seed 20260512 (existing `pressure_rules_v1`). Bootstrap resamples whole matches (cluster = match). Sorting is by (date, match_id, innings_number, innings_ball_num). Two runs must produce identical output hashes.

## 10. Known limitations of the split

- One year each for validation and test is short; IPL has one season per period.
- Player-level pressure samples are small (section 3). Reliability and stability numbers will carry wide intervals.
- The T20I TEST period contains 42 matches dated June to November 2026 (open decision O3).
- Period lengths differ (TRAIN is about three years, VALIDATION and TEST one year each), so eligibility thresholds cannot be applied to each period unchanged. Section 6 of the design notes defines the scaling used for the reproducibility check.
- OTHER_T20 matches (30) are out of pressure scope and are not part of any population.

## 10a. Implementation status at the end of Phase 4 (differences from the design above)
This section records where the code differs from the design text, so the document matches the code.
- **Lock mechanism.** `guard_frame` refuses (and logs `READ_DENIED`) any frame that contains TEST rows while the lock is closed. `LockedFrame` wraps TEST outcome columns for frames built by `split_frames`. Selection code is loaded from TRAIN and VALIDATION rows only. Tables with the prefix `p4_test_locked_` are not created; TEST results are stored as aggregate JSON and Markdown (`phase4_test_evaluation.*`). The lock is a convention-level guard, not a security boundary.
- **Single evaluation.** `scripts/phase4_test_eval.py` calls `evaluate_on_test` once. It recomputes the TRAIN-only thresholds inside the call and compares them with the frozen file. TEST par is strictly prior and includes earlier TEST first innings. The `TEST_CORE` sensitivity runs in the same call. The sensitivity that freezes TEST par at the end of VALIDATION was not run (the `source_cutoff` option of `strictly_prior_par` exists for it).
- **Rolling origins.** The origins are configured and `Split.rolling_folds` exists, but no reported metric uses them. The stability measures compare TRAIN with VALIDATION only.
- **Lock log.** The log is scoped to one run. A full run of `scripts/run_phase4.py` resets it, so a complete log shows one `FREEZE`, one `OPEN` and one `CLOSE` in that order (plus any refused reads). A second `OPEN` on the same log raises.
- **Determinism.** `scripts/run_phase4.py --compare-hashes` compares the SHA-256 of every Phase 4 `.csv`, `.json` and `.md` output with an earlier run (the lock log and the preservation files are excluded).

<!-- CHUNK1_GENERATED -->

## 11. Verified counts from the Chunk 1 code (generated, do not edit)

Generated by `scripts/phase4_split.py` from dates, pre-delivery state and par source
innings only. No pressure outcome (runs, wickets, residuals) was evaluated.
These counts use the final population rules and supersede the approximate state-only
counts in section 3 (small differences come from the exact population definition).

Split config SHA-256: `da12fcd3969361d33b1893186f72af6e021cf9c93d131e5211ae6864ce7e4894`.

### 11.1 Matches by format and period

| format | period | matches | first date | last date |
|---|---|---|---|---|
| IPL | TEST | 74 | 2026-03-28 | 2026-05-31 |
| IPL | TRAIN | 219 | 2022-03-26 | 2024-05-26 |
| IPL | VALIDATION | 74 | 2025-03-22 | 2025-06-03 |
| OTHER_T20 | TRAIN | 15 | 2024-10-18 | 2024-10-27 |
| OTHER_T20 | VALIDATION | 15 | 2025-11-14 | 2025-11-23 |
| T20I | TEST | 70 | 2026-01-07 | 2026-11-01 |
| T20I | TRAIN | 278 | 2022-01-22 | 2024-12-30 |
| T20I | VALIDATION | 122 | 2025-01-02 | 2025-12-19 |

### 11.2 Integrity checks

| check | result |
|---|---|
| matches_in_more_than_one_period | 0 |
| rows_with_period_not_equal_to_date_rule | 0 |
| periods_strictly_ordered_by_date | yes |
| periods_present | ['TEST', 'TRAIN', 'VALIDATION'] |
| matches_total | 867 |
| delivery_rows_total | 200,999 |
| same_date_groups | {'IPL': {'dates': 64, 'matches': 128}, 'OTHER_T20': {'dates': 14, 'matches': 28}, 'T20I': {'dates': 70, 'matches': 147}} |

### 11.3 State-only pressure counts (TRAIN-only rrr q0.90 per format)

| format | period | rrr threshold | pressure deliveries | distinct matches |
|---|---|---|---|---|
| IPL | TRAIN | 16.19 | 2,512 | 115 |
| IPL | VALIDATION | 16.19 | 796 | 31 |
| IPL | TEST | 16.19 | 673 | 27 |
| T20I | TRAIN | 15.41 | 2,922 | 134 |
| T20I | VALIDATION | 15.41 | 1,283 | 53 |
| T20I | TEST | 15.41 | 936 | 31 |

### 11.4 Meaningful-split verdicts

| level | cell | period | players >= 36 balls | verdict |
|---|---|---|---|---|
| population | IPL | TRAIN | n/a | SUPPORTED |
| population | IPL | VALIDATION | n/a | SUPPORTED |
| population | IPL | TEST | n/a | SUPPORTED |
| population | T20I | TRAIN | n/a | SUPPORTED |
| population | T20I | VALIDATION | n/a | SUPPORTED |
| population | T20I | TEST | n/a | SUPPORTED |
| player | IPL batter | TRAIN | 17 | SUPPORTED |
| player | IPL bowler | TRAIN | 27 | SUPPORTED |
| player | IPL batter | VALIDATION | 1 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | IPL bowler | VALIDATION | 1 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | IPL batter | TEST | 1 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | IPL bowler | TEST | 3 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | T20I batter | TRAIN | 15 | SUPPORTED |
| player | T20I bowler | TRAIN | 20 | SUPPORTED |
| player | T20I batter | VALIDATION | 4 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | T20I bowler | VALIDATION | 6 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | T20I batter | TEST | 3 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |
| player | T20I bowler | TEST | 0 | INSUFFICIENT_FOR_PLAYER_LEVEL_TEST |

### 11.5 Strictly prior par: rows without enough prior history

| format | period | innings-1 rows | unavailable rows | innings | last date |
|---|---|---|---|---|---|
| IPL | TEST | 9,123 | 0 | 0 | n/a |
| IPL | TRAIN | 27,352 | 3,737 | 30 | 2022-04-18 |
| IPL | VALIDATION | 9,113 | 0 | 0 | n/a |
| T20I | TEST | 8,345 | 0 | 0 | n/a |
| T20I | TRAIN | 33,660 | 3,955 | 33 | 2022-07-18 |
| T20I | VALIDATION | 14,461 | 0 | 0 | n/a |

Equivalence with the existing `par_runs_prior`: {'rows_compared': 200999, 'rows_only_in_one_table': 0, 'null_pattern_identical': True, 'max_abs_difference_where_both_present': 0.0}. Sensitivity (min prior innings -> unavailable innings-1 rows): {'30': 7692, '15': 3733, '60': 15491}.

