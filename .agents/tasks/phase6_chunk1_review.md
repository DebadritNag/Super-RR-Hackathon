# Phase 6 chunk 1 (cleanup) review

**Verdict**: APPROVED

Chunk 1 meets decisions 1 and 6. Evidence in `phase6_chunk1_verification.md` is present: baseline 793 passed, final 853 passed (60 new tests), ruff check and format clean, and `phase6_cleanup_checks.py` exited 0 with `all_checks_passed: true`. I did not re-run the suites. I made one narrow source spot-check of the cache module, the schemas and the repository for remaining `or True` patterns.

Watch for: none blocking. Phase 5 stored reports still use the old four-status wording (confirmed by the verification file). This is deliberate, because the brief requires phase4_* and phase5_* files to stay byte-identical, and the generators were corrected.

## High-level view

Classification wording now has three real values (VERIFIED_CAPPED, DERIVED_CAPPED, UNKNOWN). VERIFIED_UNCAPPED appears only as a disabled placeholder (`phase5.py` comment and `disabled_placeholder_values`). Strict uncapped stays disabled, and nothing infers verified status. The real-data counts are 0 / 655 / 562 and the placeholder count is 0.

The three vacuous assertions (`test_phase5_dynamic_ranking.py:583` and `:594`, plus `test_pressure_state.py:45`) are fixed. A lint-style test now guards against new ones. The only remaining `or True` strings in `tests/` are the intentional fixture strings inside that lint test (confirmed).

The public `/players` routes are now descriptive-only. They carry no score, rank, eligibility or gate fields, and the full former shape moved to token-protected `/internal/players`. Schema tests cover this.

The ranking cache key is a SHA-256 over spec hash, data, model, gate-config and lock versions, visibility scope and gate-state hash. Scope is validated (`internal` or `public`), and the two scopes never share an entry. `put`, `get` and miss paths all return deep copies. Version changes invalidate the whole cache.

<details>
<summary>Issues (1)</summary>

1. **Stale four-status wording in stored Phase 5 reports** (confirmed, non-blocking) — left byte-identical by design. Note this in the unresolved-issues register and the cleanup report, and do not edit the files.

</details>

<details><summary>Details</summary>

The infrastructure items (constants, store, lockguard, outputs and their tests) were deferred to later chunks and are outside the chunk 1 scope for decisions 1 and 6. The cache and public-schema changes are behavior changes for callers. They are listed in `phase6_cleanup_report.md`, which the brief anticipates through decision 6c and OD-6.

</details>
