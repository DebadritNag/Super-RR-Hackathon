# Phase 6 final verification

Verdict: PASS. No review file existed (phase6_review.json absent), so full verification was run.

## Commands (real data, PYTHONUTF8=1)
- `python scripts/run_phase6.py`: all steps ok, missing deliverables [], preservation True, prerun byte-identical True.
- `python -m pytest -q`: 1038 passed (793 earlier + Phase 6 tests).
- `python -m ruff check .`: all checks passed. `python -m ruff format --check .`: 306 files formatted.

## Preservation
- Compared 145 files in phase6_prerun_hashes.json (superr.duckdb, all source CSVs, all phase4_*/phase5_* reports) by SHA-256 after the run: 0 mismatches. exploratory.duckdb was excluded because it receives new p6_* tables by design.
- phase5_lock_log.json is `[]`: no TEST-lock events. phase6_gate_guard.json: gate_value 0.5, options use only 0.5, guarded file hashes recorded.

## Deliverables
All brief deliverables exist in data/reports (investigation plan, cleanup, variance floor, split-half, definition comparison, context reliability, eligibility, data-weight options, recent form, season robustness, unresolved issues, retention design, user summary, plus CSV/JSON). 27 p6_* tables exist in exploratory.duckdb, including an empty p6_retention_status_stub.

## Independent spot-checks
1. Split-half: chase|q0.75 IPL batter runs odd/even, r_pearson 0.29324. Spearman-Brown 2r/(1+r) = 0.45350, matching sb_pearson 0.45352.
2. Variance floor: recent-form IPL batter runs 2024-onward, floor hit, k = 25 (tau4 floor, not 100). tau2_used 0.12774 = sigma2 3.19353 / 25. Correct.
3. Recent-form sample count: IPL matches with ball data, 2024-01-01 through 2025-12-31 (pre-test), from raw matches.csv, competitions.csv and updated_ball_by_ball.csv: 71 (IPL 2024) + 74 (IPL 2025) = 145. The report table says 145.
4. Window counts, T20I: 298 T20I matches with balls from 2024 in raw data, minus 70 TEST-period matches = 228. The report says 228. 2025-onward: IPL 74 and T20I 122 agree with the split manifest.
5. Cache isolation: the API tests test_mutating_a_service_response_does_not_change_the_next_response and test_api_responses_are_repeatable_after_a_mutating_client pass, as do key-component, scope, version and concurrency tests.

## Gate and lock
0.5 gate unchanged; fails in 48 of 48 contexts; 0 of 256 applicable option rows pass; no option lowers the gate. No new TEST-lock events.

## Notes
Recent-form "matches" in a cell (e.g. 131) counts matches with pressure observations in that stream, a subset of the 145 window matches.
