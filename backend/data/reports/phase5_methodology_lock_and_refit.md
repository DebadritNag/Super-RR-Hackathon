# Phase 5 methodology lock and experimental refit

Status: EXPERIMENTAL_NOT_VALIDATED. Label of the lock: `EXPERIMENTAL_LOCK`. The lock freezes choices for an experimental refit. It does not validate the methodology, the pressure definition or the working pools.

## 1. Pre-lock checklist
| item | kind | status | detail |
|---|---|---|---|
| investigation_reports_present | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | 7 present |
| unresolved_issues_present | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | phase5_unresolved_issues.md |
| date_verification_manifest_present | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | test-set manifest and date-verification summary present |
| strict_uncapped_capability_recorded | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | recorded; strict uncapped enabled = False |
| publication_gates_evaluated | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | phase5_publication_gates.json present |
| phase4_outputs_unchanged | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | 56 phase4 report files compared; all identical |
| official_data_unchanged | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | 14 official files compared; all identical |
| phase4_lock_log_intact | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | events ['FREEZE', 'OPEN', 'CLOSE'] (TEST was opened once in Phase 4 and never again) |
| phase5_test_lock_not_opened | REQUIRED_FOR_EXPERIMENTAL_LOCK | PASS | phase5 lock log events [] |
| methodology_validated | PUBLICATION_GATE | FAIL | validated=false: NOT validated |
| gate:data_weight_gate_passed | PUBLICATION_GATE | FAIL | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| gate:methodology_validated | PUBLICATION_GATE | FAIL | methodology not validated |
| gate:strict_classification_available | PUBLICATION_GATE | PASS | not applicable: request uses no strict status filter |
| gate:min_eligible_pool | PUBLICATION_GATE | PASS | not applicable: evaluated per request with rows |
| gate:date_verification | PUBLICATION_GATE | FAIL | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |
| strict_uncapped_enabled | PUBLICATION_GATE | FAIL | no authoritative cap source keyed by player_id; strict uncapped stays disabled |
| decision:official_rankings | USER_DECISION | USER_APPROVAL_PENDING | needs the user: publishing an official Top 10 |
| decision:official_ml_training | USER_DECISION | USER_APPROVAL_PENDING | needs the user: official ML training |
| decision:validate_primary_definition | USER_DECISION | USER_APPROVAL_PENDING | needs the user: calling any|q0.75 validated |
| decision:validate_working_pools | USER_DECISION | USER_APPROVAL_PENDING | needs the user: validating the working-pool thresholds |
| decision:official_t20i_dates | USER_DECISION | USER_APPROVAL_PENDING | needs the user: supplying official match-level T20I dates |
| decision:authoritative_cap_source | USER_DECISION | USER_APPROVAL_PENDING | needs the user: supplying an authoritative cap source with player ids |


Required items all pass: **True**. Methodology validated: **False**. Publication ready: **False**.
Publication checks that fail: ['methodology_validated', 'gate:data_weight_gate_passed', 'gate:methodology_validated', 'gate:date_verification', 'strict_uncapped_enabled'].
Decisions waiting for you: ['decision:official_rankings', 'decision:official_ml_training', 'decision:validate_primary_definition', 'decision:validate_working_pools', 'decision:official_t20i_dates', 'decision:authoritative_cap_source'].

## 2. Lock manifest
- Manifest: `phase5_methodology_lock.json`, label `EXPERIMENTAL_LOCK`, validated `False`.
- Lock hash: `ea50abd44c4152eb1d5597d700f81acdd2d6a40b0a1828964d2e02f133c89595`.
- Code hash (locked modules): `3cde81773a2634eb8f4be2bcb3052054905ede3aada1c644a74bc70c79250fbd`.
- Definition: `any|q0.75` (PROVISIONAL_NOT_VALIDATED); sensitivity alternatives ['chase|q0.9', 'any|q0.9', 'chase|q0.75'].
- Shrinkage: `shrink_tau4`. Working pools: THRESHOLD_NOT_VALIDATED (internal exploratory use only).
- Strict uncapped enabled: False.
- Locked files hashed: 17.
- The lock is created only by `scripts/phase5_methodology_lock.py --confirm-lock`. Any change to a locked file, choice or module makes `verify_lock` raise `LockDriftError` and the refit refuses to run.

## 3. Refit design
- Fit window: TRAIN + VALIDATION. TEST rows are cut at load time and a second check refuses any row whose original period is TEST. The original period is kept as `period_orig`.
- Method: the unchanged Phase 4 functions run with the TRAIN/VALIDATION boundary moved to the end of VALIDATION. Phase 4 code is not edited.
- Locked: definition quantile level (q0.75), working-pool ball thresholds, shrinkage config, streams, restrictions. Refit: the numeric pressure cut-offs, the baseline, the shrinkage parameters.
- Output tables: `p5_refit_trainval_v1_scores`, `_baseline_calibration`, `_thresholds`, `_comparison`, `_manifest`. Every row is labelled EXPERIMENTAL and INTERNAL_EXPERIMENTAL_ONLY.

## 4. Refit results
- Rows 167913, matches 723, dates 2022-01-22 to 2025-12-19; rows by original period {'TRAIN': 120248, 'VALIDATION': 47665}.
- Seed 20260512, bootstrap draws 200. Lock hash used: `ea50abd44c4152eb1d5597d700f81acdd2d6a40b0a1828964d2e02f133c89595`.

| format|role | players | eligible (locked working pool) | matches | shrinkage k |
|---|---|---|---|---|
| IPL|batter | 267 | 134 | 262 | 25.0 |
| IPL|bowler | 184 | 80 | 263 | 25.0 |
| T20I|batter | 538 | 240 | 337 | 25.0 |
| T20I|bowler | 355 | 141 | 338 | 25.0 |


### Comparison with the Phase 4 TRAIN-only scores
| format | role | eligible P4 | eligible refit | Spearman (eligible both) | Top-10 overlap | mean abs change | max abs change |
|---|---|---|---|---|---|---|---|
| IPL | batter | 132 | 134 | 0.990 | 9 of 10 | 0.0206 | 0.0719 |
| IPL | bowler | 80 | 80 | 0.990 | 9 of 10 | 0.0196 | 0.0533 |
| T20I | batter | 243 | 240 | 0.991 | 9 of 10 | 0.0105 | 0.0967 |
| T20I | bowler | 141 | 141 | 0.986 | 10 of 10 | 0.00969 | 0.0671 |


### Preservation (checked before and after the refit)
| check | result |
|---|---|
| phase4_tables_hashed | 24 |
| phase4_tables_byte_identical | yes |
| phase4_report_files_hashed | 56 |
| phase4_report_files_byte_identical | yes |
| phase4_lock_log_sha256_before | cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c |
| phase4_lock_log_sha256_after | cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c |
| phase5_lock_log_events_before | 0 |
| phase5_lock_log_events_after | 0 |
| test_opened | no |
| rows_with_period_orig_test | 0 |
| periods_in_refit_frame | ['TRAIN'] |
| period_orig_in_refit_frame | ['TRAIN', 'VALIDATION'] |
| all_preserved | yes |


TEST was not opened. Phase 4 tables and reports are byte-identical. This refit has no out-of-sample check: VALIDATION was used for fitting. The comparison shows how much the experimental scores move; it does not show that either version is better.
