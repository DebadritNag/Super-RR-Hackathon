# SupeRR Phase 5: investigation and internal dynamic ranking engine (final review)

Phase 5 stays within scope. Everything is internal and experimental, and nothing is validated. No Top 10 is published, no official model is trained, and TEST is untouched.

**Watch for:**
- The primary TEST set defaults to `PRIMARY_RESTRICTED` (99 matches), not `STRICT_OFFICIAL_ONLY` (0 matches). It is frozen and listed as an open user decision (confirmed).
- The gate thresholds (min_public_pool 10, min_internal_pool 5, min_verified_coverage 0.95, low-weight warning 0.3) are provisional and unvalidated (confirmed).
- Two vacuous test assertions remain, both ending in `or True` (confirmed, non-blocking).

**Verdict**: APPROVED

## High-level view

The data and classification layer follows the user's decisions. VERIFIED_CAPPED has 0 rows, because no authoritative source exists and the override file is empty. DERIVED_CAPPED is data-proven only: 655 of 1,217 players have an `is_played` flag in a T20I dated on or before the as-of date. UNKNOWN has 562. Nothing is inferred from names, domestic experience or IPL participation. Strict uncapped selection is disabled through every route, preset and constraint, and returns a structured `STRICT_UNCAPPED_DISABLED` response with no rows.

All 42 late T20I dates are preserved unchanged. Each is classified from independent evidence: 36 are DATE_CONSISTENT_ACROSS_SOURCES and 6 are DATE_SINGLE_SOURCE. None is officially verified, and a template CSV is supplied for official verification. The verification step is the only place that touches Cricsheet, and it uses Cricsheet as secondary evidence only. The TEST set definitions are frozen by match-id hash, and the Phase 5 lock log is empty, so there is no new TEST opening.

Publication gating is real. Every internal output carries `publication_status=INTERNAL_EXPERIMENTAL_ONLY` and the failing gates (data_weight_gate_passed, methodology_validated, date_verification). Public routes return 403 `PUBLICATION_GATE_NOT_SATISFIED` with no rows. Internal routes require a token.

There is a single analytical framework with stored component rows. Context filters (phase, chase) re-aggregate the stored delivery-level residuals and recompute n, matches, n_eff, shrinkage and eligibility for that context, using context-specific TRAIN variance. Classification filters only restrict the pool. Nothing is trained per filter. A narrow context returns EMPTY with reasons instead of padding the list. The T20I batter + powerplay + chase + Indian + DERIVED_CAPPED example gives a pool of 3, POOL_TOO_SMALL.

The refit `p5_refit_trainval_v1` ran against an experimental lock manifest, with Phase 4 tables and reports preserved byte-for-byte. The hash comparison shows 0 differing files across 71 checked. The only change is `exploratory.duckdb`, which is the designated store for the new p5_* tables.

<details>
<summary>Issues (5)</summary>

1. **Primary TEST default** — `PRIMARY_RESTRICTED` (99 matches) is the default instead of the brief's strict `STRICT_OFFICIAL_ONLY` (0 matches). The user must decide before any TEST evaluation (confirmed).
2. **Provisional gate constants** — min_public_pool, min_internal_pool, min_verified_coverage and the low-weight warning are unvalidated. Confirm them before any public release (confirmed).
3. **Enum wording** — a placeholder `VERIFIED_UNCAPPED` enum value exists with 0 rows and is disabled everywhere. The summary says "four statuses" while the user specified three. Reword it (likely).
4. **Vacuous assertions** — `test_phase5_dynamic_ranking.py` lines 583 and 594 end in `or True`, so they assert nothing. Replace them with real checks (confirmed).
5. **Ungated directory rows and shared cache payload** — public `/players` rows are descriptive and ungated. The cached payload dict is shared between callers. Decide on gating and add defensive copies (confirmed minor, possible).

</details>

<details>
<summary>Details</summary>

### Capped classification and strict-uncapped disabling

Classification was rebuilt independently from `playing_eleven.csv`, and all 1,217 flags agree with the stored table. The only derivation is "appeared for a national team in a T20I". That label is kept separate from VERIFIED_CAPPED, which can only come from an override row carrying source, verified_by and verified_date. The "not proven capped" group appears only as UNKNOWN, never as uncapped. Every uncapped route returned `STRICT_UNCAPPED_DISABLED` in the API spot checks. These covered the internal uncapped rankings, the six presets, dynamic ranking with `VERIFIED_UNCAPPED`, context-preview, and custom selection with an uncapped group or `uncapped_mode`. The coverage table includes the VERIFIED_UNCAPPED rows with enabled=false and a final pool of 0.

The placeholder `VERIFIED_UNCAPPED` value is the only wording mismatch with the user's three-value specification.

### Date verification and primary TEST exclusion

The independent recomputation matched the stored classification for 42/42 matches, using the documented ±1-day tolerance. The 6 Afghanistan matches are single-source because no Cricsheet fixtures exist for them, and they are excluded from the primary set. The primary set (99 matches) is `PRIMARY_RESTRICTED`: it excludes all 42 late T20I matches plus 3 others, but it admits early matches that are consistent across sources yet not officially verified. The brief's default treats anything other than a user-supplied official verification as unverified. That reading gives `STRICT_OFFICIAL_ONLY` with 0 matches, which is frozen as the alternative. The late-dated matches are excluded either way, so the exclusion requirement holds. The default choice is an open decision rather than a blocker.

### Gating and the TEST lock

The date_verification gate fails closed and reads the verification JSON. Both lock logs support the TEST-untouched claim. `phase4_lock_log.json` is hash-identical, and its three events are Phase 4's single approved opening. `phase5_lock_log.json` is `[]`. `phase5_test_set_manifest.json` records `test_evaluated_in_phase5: false`.

### Dynamic engine and leakage

The spot check on player 152 (IPL batter, death, chase) rebuilt n=106, 11 matches, 183 runs, residual 17.9378 and the shrunk value 0.086536 from the raw state table with independent code. The stored and live-API rows match. The between-player variance and the rrr threshold come from TRAIN rows only. The split-half reliability numbers were reproduced exactly on 4 cells. They show low reliability and, for IPL bowlers, a negative value, so the report's "not validated" framing is honest.

### Tests and Cricsheet isolation

793 tests passed (509 earlier plus 284 new), and ruff check and format are clean. The new suite covers classification, gating, date verification, dynamic ranking, API, lock and refit, and preservation. The vacuous `or True` assertions are minor inside a suite that otherwise asserts concrete values. The suite includes a test that scoring modules do not import the Cricsheet loaders. Cricsheet is read only for date evidence.

### Evidence reviewed, not re-run

I reviewed `phase5_verification.md`, all five chunk gates and reviews, `phase5_final_run.log` (15 steps, 0 differing files, no missing deliverables) and the test file list. I did not re-run the suites. The single spot check was a grep that confirmed the two `or True` assertions are still present.

</details>

<details>
<summary>File map</summary>

- `d:/Data/.agents/tasks/phase5_verification.md`: final verification evidence
- `d:/Data/.agents/tasks/phase5_chunk{1..5}_review.md` and `_gate.json`: per-chunk gates, all APPROVED
- `d:/Data/.agents/tasks/phase5_final_run.log`: orchestrator run
- `d:/Data/backend/data/reports/phase5_*`: the Phase 5 reports
- `d:/Data/backend/tests/test_phase5_*.py`: 10 new test files

</details>
