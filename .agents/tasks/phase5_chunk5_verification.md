# Phase 5 Chunk 5 verification (methodology lock, refit, reports, orchestrator, README)
All commands run from `d:/Data/backend` with `$env:PYTHONUTF8=1`. No `phase5_chunk5_gate.json` existed, so the full chunk was implemented. The workspace is not a git repository, so nothing was committed. Everything is EXPERIMENTAL_NOT_VALIDATED / INTERNAL_EXPERIMENTAL_ONLY.
| Command | Result |
|---|---|
| `python -m pytest -q tests/test_phase5_lock_refit.py tests/test_phase5_preservation.py` | 36 passed (about 40 s) |
| `python -m pytest -q` (full) | 793 passed (757 earlier + 36 new), 3 pre-existing warnings, 425 s |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 243 files already formatted |
| `python scripts/phase5_methodology_lock.py` | checklist only, no lock written; 9 required items PASS |
| `python scripts/phase5_methodology_lock.py --confirm-lock` | lock written, hash `ea50abd44c4152eb1d5597d700f81acdd2d6a40b0a1828964d2e02f133c89595` |
| `python scripts/phase5_refit.py` | exit 0, 16 s; 167,913 rows, 723 matches, 2022-01-22 to 2025-12-19; preservation true |
| `python scripts/run_phase5.py` (first run, no `--create-lock`) | exit 0; all 15 steps ok, no deliverable missing, preservation true |
| `python scripts/run_phase5.py --compare-hashes` (second run) | exit 0; 0 differing phase5_* files |
| `verify_lock()` after the last edit | passes (lock hash unchanged) |
## Checklist as recorded (honest)
- Required for the experimental lock, all PASS: investigation reports present, unresolved issues present, date-verification manifest present, strict-uncapped capability recorded, gates evaluated, Phase 4 outputs unchanged (56 files), official data unchanged (14 files), Phase 4 lock log intact (FREEZE, OPEN, CLOSE), Phase 5 lock log has no OPEN.
- Publication checks, FAIL: `methodology_validated`, `gate:data_weight_gate_passed`, `gate:methodology_validated`, `gate:date_verification`, `strict_uncapped_enabled`. `publication_ready` false, `methodology_validated` false.
- User decisions, all USER_APPROVAL_PENDING: official rankings, official ML training, validate primary definition, validate working pools, official T20I dates, authoritative cap source.
## Refit results (experimental, no out-of-sample check)
Top-10 overlap with Phase 4 scores: IPL batter 9/10, IPL bowler 9/10, T20I batter 9/10, T20I bowler 10/10. Spearman (eligible in both) 0.986 to 0.991. Phase 4 `p4_*` tables (hash per table) and 56 `phase4_*` report files byte-identical before/after; `phase4_lock_log.json` SHA-256 unchanged; `phase5_lock_log.json` is `[]`; rows with original period TEST in the refit frame: 0.
## Built
- `app/phase5/lock_manifest.py`, `refit.py`, `reports.py`; `store.table_hashes`; `config/phase5_methodology_lock_v1.json`.
- Scripts: `phase5_methodology_lock.py` (the only caller of `write_lock`; needs `--confirm-lock`), `phase5_refit.py` (exit 2 without a valid lock), `phase5_reports.py`, `run_phase5.py` (`--create-lock` is the only way it creates a lock; `--compare-hashes`).
- Tables: `p5_methodology_lock`, `p5_refit_trainval_v1_{scores,baseline_calibration,thresholds,comparison,manifest}`, `p5_output_hashes`.
- Reports: `phase5_methodology_lock_and_refit.md`, `phase5_user_summary.md` (copied to `.agents/tasks/`), `phase5_unresolved_issues.md`, `phase5_pre_lock_checklist.json`, `p5_refit_trainval_v1_*.csv/json`, `phase5_orchestrator_run.json`, `phase5_output_hashes.json`. README Phase 5 section added.
- Tests: `test_phase5_lock_refit.py` (hash stability, drift, refusal without lock, TEST guards, reproducibility, byte-identical originals, lock only via explicit script) and `test_phase5_preservation.py` (official data and Phase 4 hashes against the pre-run record, lock logs, AST scan for Cricsheet imports and directory literals in scoring modules).
## Deviations
- Script and test names follow the task text (`phase5_methodology_lock.py`, `test_phase5_preservation.py`), not the plan (`phase5_lock.py`, `test_phase5_contamination.py`, `test_phase5_orchestrator.py`); orchestrator checks live in the lock/refit test file.
- The locked code hash covers the modules that fit the refit (listed in the lock config). Editing one of them requires re-running the lock script on purpose.
- The orchestrator re-runs chunks 1-4 scripts (about 6 min); they are deterministic (second run: 0 differences).
