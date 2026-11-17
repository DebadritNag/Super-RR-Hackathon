# Phase 5 Chunk 1 verification

Chunk: classification migration, strict-uncapped disabling, publication gating. All commands run from `d:/Data/backend` with `$env:PYTHONUTF8=1`, `python` 3.11. The reviewer does not need to re-run the suites.

## Commands and results
| Command | Result |
|---|---|
| `python -m pytest -q` (full suite) | **626 passed**, 0 failed, 0 skipped (3 existing warnings), 5m04s. Baseline was 509; 117 new tests. |
| `python -m pytest -q tests/test_phase5_classification.py tests/test_phase5_strict_uncapped.py tests/test_phase5_gating.py -rs` | 113 passed, no skips (the `realdata` test ran against the real store and CSVs). |
| `python -m pytest -q tests/test_phase4_api.py tests/test_phase4_classification.py tests/test_phase4_selection.py` (after edits) | 70 passed |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 190 files already formatted |
| `python scripts/phase5_classification.py` (real data, run 4 times) | exit 0; official data unchanged (script hashes before/after); outputs byte-identical across two consecutive runs (md, json, csv hashes compared) |
| `python scripts/phase5_gates.py` | exit 0; all three scenarios INTERNAL_EXPERIMENTAL_ONLY |

## Real-data numbers (from running code, in `data/reports/phase5_classification_migration.{md,json}`, `phase5_classification.csv`, `phase5_classification_coverage.csv`)
- 1,217 players: VERIFIED_CAPPED 0, DERIVED_CAPPED 655, VERIFIED_UNCAPPED 0, UNKNOWN 562. Equal to `phase4_classification_coverage.json` (Capped 655, Uncapped 0, Unknown 562); the script asserts this.
- Independent recount of DERIVED_CAPPED with the csv module from `competitions.csv`, `matches.csv`, `playing_eleven.csv` (`check_capped_count`): 655. Also asserted in the realdata test.
- `strict_uncapped_enabled` = false; reasons `NO_AUTHORITATIVE_SOURCE`, `NO_VERIFIED_ROWS`, `COVERAGE_BELOW_MINIMUM` (coverage 0.0 of a scored pool of 403, minimum 0.95 provisional).
- Gates today: `data_weight_gate_passed` fail (cells THRESHOLD_NOT_VALIDATED), `methodology_validated` fail, `date_verification` fail (`NOT_RUN`, the date chunk has not run), `strict_classification_available` fail for strict requests, `min_eligible_pool` per request. Status INTERNAL_EXPERIMENTAL_ONLY everywhere.

## Preservation
- `superr.duckdb` SHA-256 unchanged (`CB4077EE...391D`, equals `phase5_prerun_hashes.json`). All 12 source CSVs, `config/classification_overrides_v1.csv` (still header only) and all 56 Phase 4 report files hashed against `phase5_prerun_hashes.json`: 0 changed. `exploratory.duckdb` changed only by the added `p5_` tables (the `p4_` tables are not written).
- No Phase 4 report or table was overwritten. `p4_player_classification*` stay as the legacy tables.

## Files created
`app/phase5/{__init__,constants,store,classification_v2,gating}.py`, `app/schemas/phase5.py`, `scripts/phase5_classification.py`, `scripts/phase5_gates.py`, `config/{phase5_classification_v2,classification_source_manifest_v1,phase5_gates_v1,phase5_methodology_status_v1}.json`, `tests/test_phase5_{classification,strict_uncapped,gating}.py`, reports `phase5_classification_migration.{md,json}`, `phase5_classification.csv`, `phase5_classification_coverage.csv`, `phase5_publication_gates.{md,json}`. Appended Phase 5 sections to `docs/frontend_backend_contracts.md` (section 8, mapping table) and `docs/backend_implementation_spec.md` (section 10); one supersede note under contracts section 4.

## Files modified (non-test)
`app/phase4/uncapped.py` (new enum; `capped` filter replaced by `capped_any|capped_verified|capped_derived`; `is_strict_uncapped_request`), `app/phase4/selection.py:assign_group` (new enum; legacy `Capped`/`Uncapped` raise), `app/phase4/spotchecks.py:check_capped_count` (counts Capped, DERIVED_CAPPED, VERIFIED_CAPPED), `app/repositories/phase4_repo.py` (requires `p5_player_classification[_base]`, no fallback, capability, v2 override reload), `app/services/phase4_service.py` (single gating function, disabled body, `internal` flag, `group_label`, capabilities and gates endpoints), `app/schemas/phase4.py`, `app/api/{deps,errors}.py`, `app/api/v1/routes.py` (public + `/internal` routers from one factory), `app/main.py` (`create_app(gate_inputs, source_manifest, classification_config)`, version `phase5-experimental`).

## Modified existing tests and why (mapping documented in the contracts doc)
- `tests/phase4_api_helpers.py`: `build_store` also writes `p5_player_classification[_base]` and `p5_classification_coverage` by migrating the synthetic legacy frames through `migrate_classification`; added `base_classification_v2`, `all_pass_gates` (synthetic all-pass `GateInput`, `min_pool=0`), `write_strict_config`.
- `tests/test_phase4_api.py`: `_client` passes `gate_inputs=all_pass_gates()` (Phase 4 logic tests keep exercising the same code) and, with `strict=True`, a synthetic authoritative manifest and zero coverage minimum. Label changes: `Uncapped` -> `VERIFIED_UNCAPPED`, `Unknown` -> `UNKNOWN`, `classification=capped` -> `capped_any`, 9 combinations -> 12, override CSV values `Uncapped` -> `VERIFIED_UNCAPPED`, admin overrides version -> `p5_classification_v2`. Behaviour changes asserted instead: uncapped ranking and presets without a verified source now return `STRICT_UNCAPPED_DISABLED` (was an empty page / `POOL_TOO_SMALL`); reload test now shows disabled -> enabled (after a validated override) -> disabled.
- `tests/test_phase4_classification.py`: effective-classification and filter tests run on the migrated frame (`base_classification_v2`, `c2.migrate_classification`); `capped` filter replaced; unverified candidates are `UNKNOWN`.
- `tests/test_phase4_selection.py`: `assign_group` cases use the new enum; added a test that legacy labels raise.
- `tests/test_phase4_classification_real.py` is unchanged (it tests the preserved legacy table).

## Decisions and open points for the reviewer
1. `GET /selection/presets` (templates, no player rows) stays public and descriptive, with `available`/`unavailable_reason`; the 403 applies to every route that returns player rows. If the reviewer wants the template list gated too, it is a one-line move.
2. A public rows route with an empty or small result (pool below `min_public_pool`) answers 403 (min pool gate); internal routes still return the rows.
3. `include_uncapped` and the uncapped classification filters on `/players` (descriptive) also return the disabled body, following the brief ("every uncapped endpoint/preset/ranking/constraint").
4. The date-verification gate reads `data/reports/phase5_t20i_date_verification.json` key `gate: {passed, detail}`; Chunk 2 must write it. Absent today, so the gate fails with `NOT_RUN` (fail closed).
5. Foundations `data.py`, `lockguard.py`, `pipeline.py` from the plan's section 2 were not created here; they serve Chunks 2 and 3 and nothing in Chunk 1 uses them.
6. Thresholds `min_verified_coverage` 0.95 and `min_public_pool` 10 are provisional config values (labelled so in the config and docs).
