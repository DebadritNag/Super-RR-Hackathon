# Phase 4 Chunk 5 verification
Environment: PowerShell, `$env:PYTHONUTF8=1`, Python 3.11, cwd `d:/Data/backend`. The repository is not a git repository, so no commit was made. No frontend code.

## Built
- `app/phase4/test_eval.py`: the single TEST evaluation of the frozen configuration (population-level pressure effect with seeded match-cluster bootstrap, B0 calibration on TEST, player-level shrunk/raw/zero loss only when at least 15 players qualify, `TEST_CORE` sensitivity). The frozen file is read only after `evaluate_on_test` has verified its hash against the FREEZE entry.
- `app/phase4/reports.py`: generators that read stored results only (final `phase4_pressure_scoring_report.md`, `phase4_data_quality_report.md`, `phase4_user_summary.md`, `phase4_test_evaluation.md`). Eligibility, signal-to-noise, selection-weakness and TEST-support statements are computed, not typed.
- `app/phase4/spotchecks.py`: seven independent checks (raw CSV par, raw CSV period counts, direct SQL player pressure balls, shrunk-estimate components, capped count from `playing_eleven.csv`, inclusion-probability sums, SHA-256 of `superr.duckdb` and sources against `phase4_hash_before.txt`).
- `scripts/phase4_test_eval.py`, `scripts/phase4_reports.py`, `scripts/run_phase4.py` (orchestrator: integrity snapshot, seven steps, deliverable check, lock-order check, output hashes, `--compare-hashes`).
- `phase4_temporal_validation_plan.md` section 10a records where the code differs from the design text (lock mechanism, rolling origins not used in a metric, TEST-par-frozen sensitivity not run). README Phase 4 section added.
- Tests: `tests/test_phase4_stage_f.py` (21).
Reports from earlier chunks (baseline calibration, definition comparison, eligibility, shrinkage, format weights, ranking stability) keep their generators in `scripts/phase4_baseline.py` and `scripts/phase4_sensitivity.py`; the orchestrator reruns them.

## Commands and results
| command | result |
|---|---|
| `python scripts/run_phase4.py` | exit 0, about 3 minutes, seven steps 0, official data unchanged, deliverables ok |
| `python scripts/run_phase4.py --compare-hashes <earlier hashes>` | exit 0, hash differences versus earlier run: none (every Phase 4 csv, json and md output identical) |
| `python -m pytest -q` | 509 passed (488 + 21), 3 pre-existing warnings, 4 min 36 s |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 176 files already formatted |
`superr.duckdb` SHA-256 `CB4077EE...391D` equals `phase4_hash_before.txt`; the 22 non-exploratory files in that list are unchanged (`phase4_spot_checks.json`, `phase4_preservation.json`). Writes went only to `p4_*` tables in `exploratory.duckdb`, `data/reports`, and the copy of the user summary in `.agents/tasks`.

## Lock audit (from `phase4_lock_log.json` after the final run)
FREEZE 1, OPEN 1, CLOSE 1, READ_DENIED 0. The FREEZE precedes OPEN and the hash at OPEN equals the hash at FREEZE. A second `evaluate_frozen` on the same log raises `TestPeriodLockError` (observed during development). A full orchestrator run resets the run-scoped log first.

## Spot checks (7 of 7 agree)
1. Strictly prior par for IPL match 40694 at legal ball 60: stored 83.76279069767442, raw CSV recomputation 83.76279069767442 (215 prior source innings).
2. Matches per format and period from raw `matches.csv` and `matches 2026.csv` equal the manifest in all eight cells.
3. IPL batter 3125 pressure balls 343, matches 25, runs per ball 1.5597667638 by direct SQL equal the stored record.
4. 2,690 stored records: B = n_eff / (n_eff + k) holds to 1.1e-16, residual = raw minus expected to 8.9e-16, implied shrink target range within a cell at most 0.0147.
5. Capped players recounted from `playing_eleven.csv`: 655, stored 655.
6. Top-10 inclusion probabilities sum to 10 in all four pools.
7. Hashes: 22 files unchanged.

## Findings reported in the deliverables
- Rule winner `any|q0.75` (selection share 0.33, three candidates within the tie margin); `chase|q0.9` is rankable but outside the top group. All four eligibility cells are `THRESHOLD_NOT_VALIDATED`; the labelled working pool is used.
- TEST: B0 under-predicts run scoring in the TEST year (mean residual 0.12 to 0.14 runs per ball). The pressure effect on runs is negative in all four run cells (T20I intervals include 0). Player level, 4 of 4 cells had at least 15 qualifying players; the shrunk-minus-raw loss interval excludes 0 only for T20I bowlers (negative).
- 42 T20I matches are dated 2026-06-12 to 2026-11-01 and sit in TEST; they need the user's confirmation (open decision).

## Deliberate deviations and open items
- The TEST-par-frozen-at-2025-12-31 sensitivity and rolling-origin folds were not run (documented in plan section 10a).
- `p4_test_locked_*` tables are not created; TEST results are aggregate JSON and Markdown only.
- The frozen-choices file still contains the Chunk 3 text `test_evaluation: NOT_RUN_IN_CHUNK3_LOCK_REMAINS_CLOSED` because its hash is fixed at freeze time; the TEST results are in `phase4_test_evaluation.json`.
- Bowler pressure still uses batter state signals (documented limitation in the scoring report).
- The scoring-report scan for `cricsheet` string literals excludes the two report-writer files (they print the word); 0 hits in the remaining files.
