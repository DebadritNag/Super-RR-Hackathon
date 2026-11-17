# Phase 6 chunk 4 verification

Run from `d:/Data/backend`, `$env:PYTHONUTF8=1`, Python 3.11. Gate file `phase6_chunk4_gate.json` was absent, so the chunk was implemented from scratch.

## Built
- `app/phase6/recent_form.py`, `scripts/phase6_recent_form.py`: 2024-onward and 2025-onward as separate analyses. Tables `p6_recent_form_2024`, `p6_recent_form_2025`, `p6_recent_form_reliability`; reports `phase6_recent_form_analyses.md/json/csv` (+ `_2024`, `_2025`, `_reliability`). Every row has `analysis_label = RECENT_FORM_SEPARATE_ANALYSIS`, `window_start`, `fit_on = WINDOW_IN_SAMPLE`. B0 and pressure thresholds stay TRAIN-fitted. Window `k`, eligibility scaling, bootstrap weights and reliability are fitted on the window's own rows. Frozen thresholds are scaled `ceil(t x window balls / TRAIN balls)` (provisional, OD-2). The script aborts if a primary `p6_` table hash changes.
- `app/phase6/season_robustness.py`, `scripts/phase6_season_robustness.py`: within-season odd/even, adjacent-season Spearman, leave-one-season-out rank and reliability, 60 rows, label `ROBUSTNESS_NOT_VALIDATION`. Report `phase6_robustness_season_checks.md/json/csv` states TEST is not pristine, PRIMARY_RESTRICTED 99 (internal diagnostics), STRICT_OFFICIAL_ONLY 0, no independent validation.
- `app/phase6/retention_stub.py`, `scripts/phase6_retention_stub.py`: empty `p6_retention_status_stub` (status CHECK, default `unknown`) in `exploratory.duckdb` only; design note `phase6_retention_import_design.md`. No data imported; no module outside the stub references the table.
- `app/phase6/reports.py`, `scripts/phase6_reports.py`: `phase6_unresolved_issues.md` (P5-1..P5-10 carried with UNCHANGED/CHANGED, plus new P6 items and OD-1..OD-3) and `phase6_user_summary.md` (copied to `d:/Data/.agents/tasks/`). All numbers read from stored outputs. All 13 deliverables exist.
- `scripts/run_phase6.py`: 12 steps, seeded, `--compare-hashes`, preservation against `phase6_prerun_hashes.json` (145 files, `exploratory.duckdb` excluded), p4/p5 table hashes, lock state, retention stub rows == 0. Creates no lock, opens no TEST.
- README "Phase 6" section.
- Fix made on the way: `phase6_cleanup_checks.py` flagged `exploratory.duckdb` as changed once p6 tables existed (now excluded, p4/p5 tables are compared per table), and wall-clock deep-copy timings moved to `phase6_cleanup_timings.json` (excluded from the hash) so the second run is byte-identical.
- Tests: `tests/test_phase6_recent_form.py`, `test_phase6_retention_stub.py`, `test_phase6_preservation.py`, `test_phase6_reports.py`.

## Commands and results
| command | result |
|---|---|
| `python scripts/run_phase6.py` | exit 0, all 12 steps ok, missing deliverables [], preservation true, prerun byte-identical true |
| `python scripts/run_phase6.py --compare-hashes` (second run) | exit 0, `compare-hashes: 0 differing files []` |
| `python -m pytest -q` | 1038 passed (793 existing + earlier chunks + this chunk), 0 failed |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 306 files already formatted |

Preservation (`phase6_orchestrator_run.json`): `all_preserved` true, `p4_tables_byte_identical` true, `p5_tables_byte_identical` true, prerun files byte-identical, `phase5_lock_log_events` 0, `lock_state_unchanged` true, `retention_stub_rows` 0. No `or True` in `tests/` outside the scanner test.

## Independent spot checks (`_p6c4_spot.py` plus raw CSVs)
| check | recomputed | stored |
|---|---|---|
| Primary window from raw `matches.csv` + both ball files | 723 matches, 2022-01-22 to 2025-12-19 | 723 (report) |
| 2024-onward matches from raw CSV | 403 | 403 (report subset line) |
| 2025-onward matches from raw CSV | 211 | 211 |
| IPL batter 2025-onward matches / pressure observations / players | 63 / 3611 / 139 | 63 / 3611 / 139 |
| IPL batter 2025-onward odd/even Spearman-Brown, from raw per-match sums (alternation within each player's own matches) | 0.4743073061634607, 48 players | 0.4743073061634605, 48 players |
| Within-player residual variance, IPL batter 2025-onward, direct formula | 3.1788522291648404 | 3.1788522291648404 |
| Adjacent-season Spearman IPL batter 2024 vs 2025 (>=12 balls each) | 0.09624547360396415, 54 players | 0.0962454736039641, 54 players |
| Gate in recent-form tables | 0.5 in every estimated row, 0 cells pass | 0.5, 0 |
| Cache isolation on real data (`phase6_cleanup_checks.json`) | mutation safe true, 8 distinct keys | true, 8 |

## Findings reported, not forced
- Recent-form windows: 0 of 4 primary cells pass the 0.5 data-weight gate in either window (best marginal data weight 0.065 for 2024-onward, 0.038 for 2025-onward).
- Season checks: within-season reliability median 0.24 over 16 units, interval lower bound above 0 in 3; adjacent-season correlation median 0.11 over 12 units, interval above 0 in 1.
- No user-visible behavior was changed in this chunk; no warning was needed.
