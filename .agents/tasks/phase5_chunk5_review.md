# Methodology lock, TRAIN+VALIDATION refit, reports and orchestrator (Phase 5 chunk 5)

The change adds an experimental methodology lock written only by an explicit script, a refit that verifies the lock before fitting on TRAIN+VALIDATION, report generation, an orchestrator and a README section. Every output is labelled EXPERIMENTAL_NOT_VALIDATED / INTERNAL_EXPERIMENTAL_ONLY, and the user summary claims no validation and publishes no Top 10. The workspace is not a git repository, so the review is of the files as they stand, backed by the verification record (793 tests passed, ruff clean, second orchestrator run with 0 hash differences). I did not re-run the suites.

Watch for: the lock freezes choices and does not validate them (confirmed, stated in the manifest). The refit has no out-of-sample check (confirmed, stated in its note and in the summary).

**Verdict**: APPROVED

## High-level view

The lock hash covers the config files, the choices, and the code of the modules that fit the refit. The checklist separates items required for the experimental lock from publication gates and from user decisions. The publication gates and user decisions are recorded as failing or pending, so the lock cannot be read as a validation.

The refit calls `verify_lock` first and raises on a missing or drifted lock. It loads only TRAIN and VALIDATION rows, with the test rows dropped at load time. Phase 4 code is reused by moving the split boundary, and `period_orig` is kept on every row. Phase 4 tables, reports and lock logs are hashed before and after.

The orchestrator creates a lock only when `--create-lock` is passed. If a lock already exists from an earlier explicit run, the orchestrator refits against it. Otherwise it reports SKIPPED_NO_LOCK.

<details>
<summary>Issues (2)</summary>

1. **Script and test names differ from the plan** (confirmed, non-blocking) — the names follow the task text (`phase5_methodology_lock.py`, `test_phase5_preservation.py`) instead of the plan. The verification file records this. No action needed.
2. **Orchestrator refits whenever a lock file exists** (confirmed, non-blocking) — it is not told which lock was created when. This is acceptable because `verify_lock` still rejects drift. Optionally log the lock hash in the run record, which `phase5_orchestrator_run.json` partly does through `lock_manifest_present`.

</details>

<details>
<summary>Details</summary>

### Explicit lock creation and the checklist

`write_lock` has exactly one production caller, `scripts/phase5_methodology_lock.py`, and only after `--confirm-lock`. A test scans the app and scripts for other callers. The script refuses to lock when any required item fails. The checklist records `methodology_validated`, `data_weight_gate_passed`, `date_verification` and `strict_uncapped_enabled` as FAIL, and the six user decisions as USER_APPROVAL_PENDING. `publication_ready` is false. The required items are checks on artefacts, such as report presence and unchanged official data, and none of them asserts quality. The manifest carries `validated: False` and the statement from the lock config.

### Refit isolation

Two guards (`assert_no_test` on the raw frame and again after relabelling) refuse any row whose `period_orig` is TEST. The relabelled frame must contain only TRAIN. `TestLock` is pointed at the Phase 5 lock log, which stays empty, and `assert_phase5_lock_not_opened` is called before and after. The preservation block feeds `all_preserved`, and the refit outputs are written only to `p5_refit_trainval_v1_*` tables and files. The comparison with Phase 4 is described as "not a validation". The summary states that no out-of-sample check exists, which is the honest framing.

### Summary and README

The user summary opens with "Nothing is validated. No Top 10 is published" and lists the failing gates by id. It lists the unresolved issues and the six decisions the user still has to take, and it stops for review. The README section carries the same labels and documents the commands, including that `--create-lock` is the only way the orchestrator writes a lock.

### Test coverage

The tests cover hash stability, drift detection, tampering, refusal without a lock or with a drifted one, the TEST guards, reproducibility with the same seed, byte-identical Phase 4 tables and reports, the experimental labels, write confinement to p5 tables, and the explicit-only lock. A `need_store` marker skips the store-dependent tests when no store exists, but the verification file shows them running (36 passed).

Not tested: the orchestrator's `--compare-hashes` path inside the test suite. It was verified only by running it once (0 differences).

</details>

<details>
<summary>File map</summary>

- `app/phase5/lock_manifest.py`: lock content, checklist, verify
- `app/phase5/refit.py`: guarded TRAIN+VALIDATION refit
- `app/phase5/reports.py`: lock, refit and summary reports
- `app/phase5/store.py`: `table_hashes`
- `config/phase5_methodology_lock_v1.json`: locked file list
- `scripts/phase5_methodology_lock.py`, `phase5_refit.py`, `phase5_reports.py`, `run_phase5.py`
- `tests/test_phase5_lock_refit.py`, `tests/test_phase5_preservation.py`
- `README.md`: Phase 5 section

</details>
</text>
