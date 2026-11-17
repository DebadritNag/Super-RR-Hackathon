# Chunk 5: Phase 4 report generators, orchestrator, TEST evaluation

Chunk 5 adds a single frozen-configuration TEST evaluation, report writers that read stored results, seven independent spot checks, and a seeded orchestrator with a hash-compare mode. The verification file covers a full orchestrator run, a hash-identical rerun, 509 passing tests, and clean Ruff check and format. The lock log shows FREEZE, OPEN (same hash), CLOSE, with no denied reads. All reports carry EXPERIMENTAL_NOT_VALIDATED and say official rankings and ML training await approval.

Watch for: TEST evaluation shows B0 under-predicting runs in the TEST year (confirmed, disclosed). The 42 T20I matches dated 2026-06-12 to 2026-11-01 need user confirmation (open decision, disclosed). Two planned sensitivities were not run (confirmed, documented in plan section 10a).

**Verdict**: APPROVED

## High-level view

Reports are rendered from stored JSON/CSV results. Eligibility status, selection weakness and TEST support statements are computed from those results. In `reports.py` the only fixed prose is the status and disclaimer wording. The user summary says no pressure definition, threshold, shrinkage or format weight is validated, and that 70:30 is not shown to be optimal. Seeding is centralised (`SEED` constant, seeded match-cluster bootstrap in `test_eval.py`, seeds from config in the orchestrator), and the rerun produced identical hashes for every Phase 4 output. The TEST lock is ordered correctly and the frozen file hash was verified before reading.

<details>
<summary>Issues (3)</summary>

1. **TEST-par-frozen and rolling-origin sensitivities not run** (confirmed) — documented deviation; list as limitations in the next phase. Not blocking.
2. **Frozen-choices file keeps stale `NOT_RUN_IN_CHUNK3_LOCK_REMAINS_CLOSED` text** (confirmed) — a fixed hash is the stated reason. The user summary should point readers to `phase4_test_evaluation.json`, which it does. Not blocking.
3. **Bowler pressure uses batter state signals** (confirmed) — a documented limitation; carry it into the approval decisions.

</details>

<details>
<summary>Details</summary>

### Honesty of reports and the lock

The user summary and scoring report state that all four eligibility cells are THRESHOLD_NOT_VALIDATED. The summary does not present the working pool as validated. The rule winner `any|q0.75` is reported with a selection share of 0.33 and three candidates inside the tie margin, so `chase|q0.9` is shown as outside the top group instead of being forced in. The `TEST_CORE` sensitivity and the shrunk-versus-raw loss are only evaluated when at least 15 players qualify. All four cells met that bar, and only T20I bowlers have a shrunk-minus-raw interval excluding 0.

### Determinism

The rerun hash comparison reported no differences. The bootstrap uses `SEED` with `match_weights(n, B, seed)`. Narrow spot-check on my side: the user summary copy in `.agents/tasks` is byte-identical to the one in `data/reports` (same SHA-256). The contracts and spec docs exist in both `docs` and `data/reports`, and the lock log matches the verification file.

### Evidence accepted without rerun

Test counts, Ruff results and the seven spot checks were taken from the verification file as instructed. No full suites were rerun.

</details>

<details>
<summary>File map</summary>

app/phase4/test_eval.py (single TEST evaluation), app/phase4/reports.py (report renderers), app/phase4/spotchecks.py (seven checks), scripts/phase4_test_eval.py, scripts/phase4_reports.py, scripts/run_phase4.py (orchestrator), README (Phase 4 section), tests/test_phase4_stage_f.py (21 tests).

</details>
