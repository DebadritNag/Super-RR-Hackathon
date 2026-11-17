# Phase 7 chunk 1 review

Chunk 1 delivers the 12-row final audit, the OD-1..3 decisions, the mock-data audit and a permanent scan test. The evidence is recorded, consistent and, where I re-checked it, reproducible. No blocking concerns remain.

Watch for: the audit says checks were "executed in this run". They were executed by the implementer, not by me. I did not re-run the test suites, as instructed. I took the 1045-passed and ruff results from `phase7_chunk1_verification.md` and `phase7_pytest_chunk1.txt` (confirmed present).

**Verdict**: APPROVED

## High-level view

The audit has all 12 required rows. It states for each row whether the check was executed or only workflow-reported, and it closes with a list of what was not re-executed (the Phase 6 pipeline run, the raw-CSV recounts in spot checks 3 and 4, the historical ruff format count, and the 66 Phase 6 output hashes). Its reported-versus-recomputed table matches the verification record: 0.3656, 0.2538 over 47 contexts, floor hit 48/48, gate 0/48, 18 options with best 0.5619, ladder 2/0/0, season medians 0.2446 and 0.1109, and 1045 tests (1038 plus 7 new). It also corrects the "145 files" claim: the Phase 6 hash file holds 146 entries, and the 146th is the exploratory store, which changed by design.

The decisions file takes OD-1..3 from `phase6_unresolved_issues.md`, where they are the ids P6-1 (primary window pre-test only), P6-2 (recent-form thresholds provisional) and P6-3 (no clean hold-out). It notes that other "OD-n" labels in the design doc mean something else. Each outcome applies D1-D5 or a standing rule. It adds no new methodology or publication decision. The only owner question is optional (a post-submission hold-out), with a recommended default.

Public `/players` takes `PublicFilters`, which has no `min_pressure_matches`. The internal route keeps it. The cache is keyed on spec hash, data, model, gate and lock versions, scope and gate state, with `internal`/`public` as the only scopes, and it deep-copies on put and get. `hardcoded_mock_data_audit.md` and `tests/test_phase7_no_mock_in_production.py` both exist. The test includes a planted-violation self-check.

<details>
<summary>Issues (2)</summary>

1. **Wording "executed in this run" / "by this step"** — the audit should say the implementer executed these checks, so readers do not assume reviewer execution. Non-blocking (confirmed).
2. **Audit date reads 17 Nov 2026** while the brief says about 14 Nov. Cosmetic; align the date when the final audit is regenerated. Non-blocking (possible).

</details>

<details>
<summary>Details</summary>

What I checked myself:

- `app/api/v1/routes.py`: the `min_pressure_matches` parameter appears at line 53 (shared filter builder) and line 153 (an internal ranking route). `public.get("/players")` at line 74 depends on `PublicFilters`. Line 94 is the internal `/players`. This matches the audit.
- `app/services/phase4_service.py`: `_public_player_item` and `public_flags` are selected when `public` is true (lines 255-258). The allow-list claim holds.
- `app/phase5/cache.py`: `SCOPES = ("internal","public")`, scope validation raises `ValueError`, and `copy.deepcopy` is used on lines 82 and 88. The audit's claim holds. The audit also correctly says the `/players` directory is not cached.
- `tests/test_phase7_public_players_openapi.py` asserts that the public OpenAPI parameters exclude `min_pressure_matches` and that the internal ones keep it.
- Narrow data spot-check: `p5_context_fit` in `data/database/exploratory.duckdb` (read-only) returns 48 contexts with 48 floor hits. This matches the audit and the Phase 6 claim.
- Protected files: I re-ran `scripts/phase7_protected_check.py --phase6`. It reported 218 files compared with 0 mismatches, 146 prerun entries with 0 unexpected mismatches (1 expected), lock log sha256 `cae1e06c...eb75c`, events FREEZE/OPEN/CLOSE, and the phase 5 log empty. Result PASS. That is no new TEST event, and no Phase 7 code touches the lock.

Not tested by me: the full pytest suite and ruff (recorded by the implementer), the live endpoint probe (taken from `phase7_endpoint_probe.json` via the verification file), and the raw-CSV recounts.

</details>

## File map

<details>
<summary>Files reviewed</summary>

- `backend/data/reports/phase6_final_audit.md`: 12-row audit plus a reported-versus-recomputed table
- `backend/data/reports/phase6_final_decisions.md`: OD-1..3 and the carried-forward items
- `backend/data/reports/hardcoded_mock_data_audit.md`: backend mock-data audit
- `backend/tests/test_phase7_no_mock_in_production.py`: permanent scan test
- `backend/tests/test_phase7_public_players_openapi.py`: OpenAPI contract test
- `backend/scripts/phase7_*.py`: read-only probes and the protected-file check

</details>
