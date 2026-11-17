# Phase 6 chunk 1 (cleanup) verification

Working directory `d:/Data/backend`, `$env:PYTHONUTF8=1`, interpreter `python` (3.11). The workspace is not a git repository, so nothing was committed.

## Commands and results

| step | command | result |
|---|---|---|
| baseline (before edits) | `python -m pytest -q` | 793 passed, 3 warnings (481 s) |
| baseline | `python -m ruff check .` / `python -m ruff format --check .` | All checks passed / 244 files already formatted |
| final | `python -m pytest -q` | **853 passed**, 3 warnings (508 s): 793 existing + 60 new |
| final | `python -m ruff check .` | All checks passed |
| final | `python -m ruff format --check .` | 253 files already formatted |
| real-data checks | `python scripts/phase6_cleanup_checks.py` | exit 0, `all_checks_passed: true`, `preserved: True []` |

New tests: `tests/test_phase6_classification_wording.py` (19), `tests/test_phase6_no_vacuous_assertions.py` (4), `tests/test_phase6_public_schema.py` (17), `tests/test_phase6_cache_isolation.py` (15), `tests/test_phase6_cleanup.py` (5).

An earlier full run had one failure (my own new test used an arbitrary file-count threshold); it was fixed and the full suite rerun as above.

## Numbers from the real data (`data/reports/phase6_cleanup_checks.json`)

- Classification: status counts VERIFIED_CAPPED 0, DERIVED_CAPPED 655, UNKNOWN 562 (1,217 players); placeholder VERIFIED_UNCAPPED count 0; coverage 9 combinations; `strict_uncapped_enabled` false.
- Vacuous assertions: 3 found before (`tests/test_phase5_dynamic_ranking.py:583`, `:594`, `tests/test_pressure_state.py:45`), 0 after, over 47 test files.
- Public directory models: no field matching `score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict`.
- Cache: 8 single-component key variants give 8 distinct keys; mutating a real-data response did not change the next response; worst deep-copy cost 6.46 ms (T20I batter, 243 rows) against a 50 ms budget.
- Interval contains the point score in 48 of 48 rows (batter COMBINED_w70_30, real data).

## Preservation

- `phase6_prerun_hashes.json`: 146 files (databases, source CSVs, Phase 4 and Phase 5 reports) compared after the work: 0 changed.
- `Preservation.verify()`: official data unchanged, Phase 4 reports unchanged, TEST lock log unchanged, Phase 5 lock log events 0, TEST opened false.
- No `phase4_*` or `phase5_*` file was written. Phase 5 stored reports still contain the old four-status wording; the generators were corrected, the stored files were left byte-identical on purpose.

## Behavior changes visible to callers (all listed in `data/reports/phase6_cleanup_report.md`)

1. Public `/players` and `/players/{id}` no longer return `eligible_scopes`, `conflict_flag`, `official_ranking`, `publication_status`, `gate_results`; they return `descriptive_only: true`. The public `min_pressure_matches` query filter is removed. The full former shape is on `/internal/players` and `/internal/players/{id}` (admin token). These were specified in the brief (decision 6c) and the design (OD-6).
2. `GET /meta/capabilities` lists three `classification_values` and a new `disabled_placeholder_values`.
3. `GET /meta/classification-coverage` summary has 9 combinations (was 12) and a new `disabled_placeholder_counts`.
4. Public strict-uncapped directory requests return a minimal `PublicDisabled` body (no gate fields).

## Existing tests edited

`tests/test_phase5_dynamic_ranking.py`, `tests/test_pressure_state.py`, `tests/test_phase5_classification.py`, `tests/test_phase4_api.py`, `tests/test_phase5_gating.py`, `tests/test_phase5_strict_uncapped.py`. Reasons are listed per file in the cleanup report, section 5.

## Files

Changed: `app/phase5/{classification_v2,cache,filters,reports}.py`, `app/phase4/uncapped.py`, `app/schemas/{phase4,phase5}.py`, `app/services/{phase4_service,phase5_service}.py`, `app/api/v1/{routes,routes_phase5}.py`, `scripts/phase5_classification.py`, `scripts/phase5_gates.py`, `docs/frontend_backend_contracts.md` (new section 10 plus wording fixes), `docs/backend_implementation_spec.md` (new section 12 plus the 11.4 cache line).
Added: `app/phase6/{__init__,cleanup_scans}.py`, `scripts/phase6_cleanup_checks.py`, the five test files above, `data/reports/phase6_cleanup_report.md`, `data/reports/phase6_cleanup_checks.json`.

## Not done in this chunk (belongs to later plan items)

Plan item 2 (`app/phase6/constants.py`, `store.py`, `lockguard.py`, `outputs.py`, and `tests/test_phase6_lock_guard.py`, `tests/test_phase6_preservation.py`) is infrastructure for the investigation chunks and was not built here. Chunk gate file `phase6_chunk1_gate.json` is for the reviewer to write.
