# Phase 5 Implementation Plan (INTERNAL / EXPERIMENTAL ONLY)

Status label for every artifact: `EXPERIMENTAL_NOT_VALIDATED`. No official Top 10, no official model, no TEST read.
All paths are absolute and lower-case `d:/Data`. Python is `python`; set `$env:PYTHONUTF8=1`. Run commands from `d:/Data/backend`.
The user's words (original_user_request) win over `phase5_brief.md` where they differ.

---------------------------------------------------------------------------------------------------

## 0. Facts found in the code and data (record these in the Phase 5 reports; recompute, do not copy)

**Baseline:** 509 tests collected (`python -m pytest --collect-only -q`). No git repository in `d:/Data` (use `app.analytics.reporting.code_version()` for code hashes). Pre-run hashes of `superr.duckdb`, `exploratory.duckdb` and the source CSVs are already in `d:/Data/.agents/tasks/phase5_prerun_hashes.json`.

**Classification counts (source: `d:/Data/backend/data/reports/phase4_classification_coverage.json`, built by `app/phase4/classification.py:build_classification` into `p4_player_classification`):**
1,217 players. Indian/Capped 52, Indian/Unknown 112, Overseas/Capped 603, Overseas/Unknown 3, Unknown/Unknown 447, Uncapped 0. Capped total 655, all with verification `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES` (an `is_played` row in a T20I playing XI dated on or before `as_of_date` 2025-12-31). Status Unknown 562 (498 `NOT_PROVEN_CAPPED_IN_DATA`, 64 `FIRST_T20I_AFTER_AS_OF_DATE`). Nationality verification: DERIVED 770, UNVERIFIED 447. Verified source rows: 0 (`config/classification_overrides_v1.csv` is header only). Scored players (eligible somewhere) 403: Indian/Capped 51, Indian/Unknown 35, Overseas/Capped 288, Overseas/Unknown 1, Unknown/Unknown 28.
Migration target counts: VERIFIED_CAPPED 0, DERIVED_CAPPED 655, VERIFIED_UNCAPPED 0, UNKNOWN 562. The migration must assert these equal the Phase 4 counts and fail loudly otherwise.

**Where the old "Capped"/"Uncapped"/"Unknown" status labels live (all must migrate, explicitly):**
- `app/phase4/classification.py`: `STATUSES`, `_ENUM["international_status"]`, the `"Capped"` assignment in `build_classification`, `coverage()`, `V_T20I`, `V_SOURCE`, `apply_overrides`.
- `app/phase4/uncapped.py`: `effective_classification` (`eff_status`), `verified_uncapped_mask`, `apply_filters`, `ClassificationFilter.capped/indian_uncapped/...`, `unverified_candidates`.
- `app/phase4/selection.py`: `assign_group` (groups `IN_CAPPED, IN_UNCAPPED, OS_CAPPED, OS_UNCAPPED, UNKNOWN`).
- `app/phase4/views.py` (`ranking_frame`, `directory_frame` use `eff_status`), `app/phase4/profiles.py` (uncapped reference set), `app/phase4/spotchecks.py:check_capped_count` (compares `international_status == "Capped"`).
- `app/services/phase4_service.py`, `app/schemas/phase4.py` (`GroupName`, `ClassifiedPlayer`), `app/api/v1/routes.py` (`/rankings/uncapped/{kind}`, `/meta/classification-coverage`), `app/repositories/phase4_repo.py` (`p4_player_classification`, `reload_classification`).
- `scripts/phase4_classification.py` (report text), `app/phase4/serving.py:run_classification`.
- `config/phase4_classification_v1.json` (`status_semantics`), `config/phase4_selection_presets_v1.json` (6 presets, all `depends_on_verified_classification: true`).
- Docs: `d:/Data/backend/docs/frontend_backend_contracts.md` (section 4), `d:/Data/backend/docs/backend_implementation_spec.md` (sections 3, 5, 6, 8). `data/reports/frontend_backend_contracts.md` and `data/reports/pressure_framework_v1.md` are byte-size-identical copies of the docs files (10,150 and 93,300 bytes); do not edit the report copies, write new Phase 5 files.
- Tests that encode the old labels (must be updated, with the mapping documented): `tests/phase4_api_helpers.py:base_classification`, `tests/test_phase4_classification.py`, `tests/test_phase4_classification_real.py`, `tests/test_phase4_selection.py` (assign_group cases), `tests/test_phase4_api.py`.

**The 42 T20I matches dated after 2026-05-31 (verified by query on `superr.duckdb` read-only):**
All 42 have deliveries and real `delivery_ist_time` values (suffix `UTC`, but the clock times look like UTC). `match_id`, `comp_id`, original date:
- comp 3126 (India in England): 45390 (2026-07-01), 45391 (07-04), 45392 (07-07), 45393 (07-09), 45394 (07-11)
- comp 3128 (Sri Lanka in England): 45489 (09-15), 45490 (09-17), 45491 (09-19)
- comp 3446 (India in Ireland): 50340 (06-26), 50341 (06-28)
- comp 3450 (West Indies in India): 50404 (10-06), 50405 (10-09), 50406 (10-11), 50407 (10-14), 50408 (10-17)
- comp 3464 (Sri Lanka in West Indies): 50503 (06-12), 50504 (06-14), 50505 (06-15)
- comp 3465 (India in Zimbabwe): 50507 (07-23), 50508 (07-25), 50509 (07-26)
- comp 3482 (Australia in Bangladesh): 50597 (06-17), 50598 (06-19), 50599 (06-21)
- comp 3568 (Bangladesh in Zimbabwe): 51383 (07-15), 51384 (07-17), 51385 (07-19)
- comp 3690 (India in New Zealand): 54210 (10-22), 54211 (10-24), 54212 (10-27), 54213 (10-30), 54214 (11-01)
- comp 3713 (Afghanistan v India): 54408 (09-13), 54409 (09-15), 54410 (09-17)
- comp 3739 (India in Japan): 54711 (09-22)
- comp 3765 (Sri Lanka in Pakistan): 55078 (10-09), 55079 (10-11), 55080 (10-13)
- comp 3787 (Afghanistan v Zimbabwe): 55559 (10-27), 55560 (10-29), 55561 (11-01)
Evidence already seen: first-ball timestamp date equals `match_date` for 41 of 42 (one is one day earlier). Pre-2026 T20I matches show the same date in 403 of 428, one day off in 22, two days off in 3 (so a plus or minus 1 day tolerance for IST/UTC is empirical; 2+ days is a conflict). Cricsheet (`data/staging/cricsheet_index.parquet`, dirs `t20s_male_json`, `2026_male_json`, `india_male_json`) holds same-team matches on the same dates (e.g. England v India 2026-07-01, 07-04, 07-07, 07-09, 07-11; the index runs to 2026-11-03). `matches 2026.csv` is the IPL 2026 file only, so it has no overlap with these 42 (record as `NOT_APPLICABLE`). `competitions.csv` has only `comp_id, comp_name, match_format, season` (no date windows), so check (c) reduces to a season/year token check and is weak.
TEST period (from `p4_match_period`): IPL 74, T20I 70, total 144, all IPL dates <= 2026-05-31. The `matches` table has 72 T20I matches dated >= 2026-01-01, so 2 T20I TEST matches are absent from the Phase 4 state (find and report them in Chunk 2).

**TEST lock facts (code read):** `app/phase4/split.py:TestLock._open_for_evaluation` raises `TestPeriodLockError("the test lock has already been opened once")` if the log has any `OPEN` event. `d:/Data/backend/data/reports/phase4_lock_log.json` already holds `FREEZE`(seq 1), `OPEN`(seq 2), `CLOSE`(seq 3), sha256 `86f5ce9d588dba715c18e4f3f60b5e8a328c03c2f24c73db73614b2e4d101e42`. The only way to open again is to reset that log, which `scripts/run_phase4.py` does on a full run (`write_text("[]")`). `app/phase4/test_eval.py:evaluate_frozen` is the single evaluator and it already ran on all 144 TEST matches including the 42 unverified-date matches.

**Reusable Phase 4 code (do not duplicate):** `app/phase4/engine.py` (`base_rows`, `tag_rows`, `build_cell`, `Cell`, `global_weights`, `cell_weights`, `point_estimates`, `draws`, `rank_summary`, `summarize_ranking`, `player_ranking_table`, `PRIMARY`), `shrink.py` (`CONFIGS`, `match_stats`, `player_table`, `fit_cell`, `k_for`, `estimate`, `bootstrap_draws`, `match_weights`), `scoring.py` (`parse_definition`, `add_signals`, `fit_thresholds`, `pressure_flag`, `combine_formats`), `baseline.py` (`prepare_frame`, `fit_baseline_set`, `role_frame`, `STREAMS`), `eligibility.py` (`candidate_thresholds`, `window_ratio`, `evaluate_cell`, `decide`, `analysis_rule`, `eligible_mask`), `definitions.py` (`rs_stats`, `evaluate_definitions`), `sensitivity.py` (`shrinkage_sensitivity`, `ranking_stability`, `format_weight_analysis`, `baseline_alternatives`), `lockguard.py` (`guard_frame`, `drop_test_rows`), `split.py` (`Split`, `TestLock`), `selection.py` (composition DP), `views.py`, `profiles.py`, `reports.py` (`lock_facts`, `nonoutcome_literals`), `spotchecks.py`, `store.py` (pattern for `write_p5_table`), `app/analytics/integrity.py` (`snapshot_from_settings`, `assert_unchanged`), `app/analytics/reporting.py` (`write_json_deterministic`, `write_text`, `md_table`, `fmt`, `code_version`), `app/api/errors.py` (`ApiError`), `app/api/deps.py` (`require_admin`), `scripts/run_phase4.py` (orchestrator pattern).

---------------------------------------------------------------------------------------------------

## 1. Decisions recorded (each with rationale)

**D1. TEST lock: do NOT re-open TEST. Freeze the restricted TEST set in a manifest.**
Justification from the lock code: the lock is single-use by construction (`opened_before()` check) and has been used. Re-opening needs a log reset, which would erase the evidence that Phase 4 opened TEST once and break the user's rule "keep TEST completely untouched". The methodology and data-weight gate are not locked, so a second evaluation now would be premature. Phase 5 therefore (a) never calls `evaluate_on_test`, `evaluate_frozen`, `run_phase4.py` (full run) or writes `phase4_lock_log.json`; (b) loads pre-test data only (SQL filter on `p4_match_period.period <> 'TEST'`), and loads TEST match-level non-outcome state columns only for the date-verification counts; (c) writes `phase5_test_set_manifest.json` (PRIMARY, STRICT_OFFICIAL_ONLY and SENSITIVITY_ALL sets, with hash) for one future evaluation under a new `phase5_lock_log.json` that Phase 5 leaves empty; (d) reports honestly that Phase 4's existing TEST evaluation covered all 144 matches including the 42 unverified dates, is preserved byte-identical, and is labelled "includes unverified dates; sensitivity-only" in the Phase 5 reports (not by editing Phase 4 files). Open decision for the user: because aggregate TEST results were already shown in `phase4_user_summary.md`, a later TEST evaluation is not a pristine hold-out.

**D2. Primary TEST set rule.** The brief's strict default (anything other than a user-supplied OFFICIAL verification is unverified) would exclude all 144 matches. Chosen: three sets in the manifest.
- `PRIMARY_RESTRICTED` (default): OFFICIAL_VERIFIED rows, plus matches dated <= `test_core_end` (2026-05-31) whose date class is `DATE_CONSISTENT_ACROSS_SOURCES`. Excludes all 42 late matches until officially verified.
- `STRICT_OFFICIAL_ONLY`: only rows in the user-supplied official verification CSV (empty today; count reported as 0).
- `SENSITIVITY_ALL`: all TEST matches, as Phase 4 evaluated them.
Counts of matches, deliveries and distinct players affected are reported for each. Record the choice as an open decision.

**D3. Classification enum.** `international_status` becomes one of `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `VERIFIED_UNCAPPED`, `UNKNOWN`. Evidence label kept per row (`DERIVED_FROM_OFFICIAL_T20I_APPEARANCES`, `VERIFIED_FROM_SOURCE`, `UNVERIFIED`). Explicit mapping (documented in the contracts doc and stored as `p5_classification_migration_map`):
| Phase 4 status | Phase 4 verification | Phase 5 status |
|---|---|---|
| Capped | DERIVED_FROM_OFFICIAL_T20I_APPEARANCES | DERIVED_CAPPED |
| Capped | VERIFIED_FROM_SOURCE | VERIFIED_CAPPED |
| Uncapped | VERIFIED_FROM_SOURCE | VERIFIED_UNCAPPED |
| Unknown | UNVERIFIED | UNKNOWN |
Any other combination raises `ClassificationMigrationError` (no silent relabel). Override file `value` for `international_status` becomes `VERIFIED_CAPPED|VERIFIED_UNCAPPED`; the legacy `Capped|Uncapped` values are rejected with an error that names the mapping. Existing validation (`source`, `verified_by`, ISO `verified_date` non-empty) is kept and tested. Nationality values stay `Indian|Overseas|Unknown`. The "not proven capped" pool may appear only as group `UNKNOWN_STATUS` (a display label of the `UNKNOWN` group), never as uncapped. The 42 late T20I matches are after `as_of_date` (2025-12-31), so DERIVED_CAPPED counts do not depend on the disputed dates (state this in the report).

**D4. Strict uncapped capability.** `strict_uncapped_enabled` is computed, default false, true only when all hold: (a) `config/classification_source_manifest_v1.json` declares an authoritative source keyed by `player_id` (`authoritative: true`, `id_keyed: true`), (b) at least one `VERIFIED_*` override or source row is loaded and validated, (c) share of the scored pool with a VERIFIED_* status >= `min_verified_coverage` (config, provisional 0.95). Today all fail. Disabled behaviour: HTTP 200 with body `{"result_status": "STRICT_UNCAPPED_DISABLED", "reason": ..., "source_needed": ..., "capability": {...}, "rows": []}` on every uncapped ranking, uncapped preset (all 6 presets) and any selection request that names `IN_UNCAPPED`/`OS_UNCAPPED` with `exact>0` or `min>0`, or `uncapped_mode=include_uncapped`. `exclude_uncapped` and `max=0`/`exact=0` stay allowed (they select nothing uncapped). Public routes answer with the publication-gate error first (D5); internal routes return the disabled body.

**D5. Gating layer.** Every ranking, selection, score, profile and compare output carries `publication_status` in `{INTERNAL_EXPERIMENTAL_ONLY, PUBLIC_ALLOWED}` and `gate_results` (list of `{gate_id, passed, detail}`): `data_weight_gate_passed` (from `phase4_frozen_choices.json`: all four cells `THRESHOLD_NOT_VALIDATED`, so false), `methodology_validated` (from `config/phase5_methodology_status_v1.json`, `validated:false`; only a human edit can change it), `strict_classification_available` (only required when the request uses uncapped or verified filters), `min_eligible_pool` (provisional 10 for public output), `date_verification` (no unverified-date match inside any window used, or full OFFICIAL coverage; false today). `PUBLIC_ALLOWED` only if all applicable gates pass. Internal routes live under `/api/v1/internal/...` behind the admin/internal token and return the status. The existing Phase 4 public paths (`/rankings/*`, `/selection/*`, `/compare`, `/players/{id}/profile`) return HTTP 403 with the error envelope code `PUBLICATION_GATE_NOT_SATISFIED`, `details = {publication_status, gate_results}` and no player rows. Descriptive directory routes (`/players`, `/players/{id}`) stay public and carry the flags. For old tests, `create_app(gate_inputs=...)` accepts a synthetic all-pass fixture so Phase 4 logic tests can keep exercising the same code (list every modified test in the verification file).

**D6. Pressure definition.** Primary `any|q0.75` (label PROVISIONAL), sensitivity alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75`, always run together. No text may say validated or superior.

**D7. Dynamic engine design.** One analytic model; filters never train models.
- Layer 1: `p5_context_stats` holds sufficient statistics per (player, match, comp, role, stream, period, phase, situation) for the carried definition's pressure rows: `n, s, s2` of the B0 residual. Any context is a re-aggregation (sum) of these rows.
- Layer 2 (classification/filter): nationality, status (D3), role (= ranking side, from actual participation; "all-rounder" is not a role, a player simply appears in both batter and bowler lists if eligible in both; `squad_role` is shown as display text only), experience (`matches_played` from `p4_player_stats`, pressure matches in the context), format (IPL, T20I, COMBINED_w70_30 only for players eligible in both formats in that context), phase (powerplay/middle/death from `innings_phase`, plus ALL), situation (`chase` = innings 2, `first_innings` = innings 1, plus ALL). Wickets-remaining bands: NOT supported in v1 (catalog shows disabled with the reason "sample fragments below usable size", numbers from the coverage run).
- Layer 3 (ranking): per context recompute `n`, matches, Kish `n_eff`, shrinkage `k`/target with a context-specific between-player variance estimated on TRAIN rows of that context (`shrink.fit_cell`); documented floor/fallback: if TRAIN players < 2, or sigma2 is NaN, or between-variance <= floor, use `k_for`'s floor behaviour (k = sigma2/(0.01*sigma2) = 100, max shrinkage), flag `fit_floor_hit`/`fit_not_estimable`; never borrow the parent context's variance. Intervals and rank statistics by seeded match-cluster bootstrap (`engine.global_weights`, seed 20260512, 1000 draws) restricted to the filtered pool. Context eligibility thresholds are derived per context with `eligibility.evaluate_cell` + `decide` + `analysis_rule` on the context cell (same data-derived method, TRAIN percentile and ladder candidates from `config/pressure_eligibility_rules_v1.json`), never borrowed from the overall cell. Eligibility is never inherited: a player eligible overall but short in the context is `INSUFFICIENT_SAMPLE_FOR_CONTEXT`.
- Minimum pool: engine lists a context with pool >= 5 (config `min_internal_pool`, provisional), pool < 5 returns empty rows with `POOL_TOO_SMALL`. Public gate needs >= 10. Never pad.
- Reason codes: `INSUFFICIENT_SAMPLE_FOR_CONTEXT`, `POOL_TOO_SMALL`, `STRICT_UNCAPPED_DISABLED`, `CLASSIFICATION_UNKNOWN_EXCLUDED`, `CONTEXT_NOT_ESTIMABLE`, `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT`, `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS`.
- Unknown toggles: `include_unknown_nationality` and `include_unknown_status` default false; the excluded counts are returned.

**D8. Refit.** The refit works on a copy of the pre-test frame in which VALIDATION rows are relabelled `TRAIN` (original label kept in `period_orig`), so the unchanged Phase 4 functions (`prepare_frame`, `fit_baseline_set`, `fit_thresholds`, `fit_cell`) fit on TRAIN + VALIDATION without editing Phase 4 code. TEST rows are never loaded. Output tables `p5_refit_trainval_v1_*`. Phase 4 TRAIN-only tables stay byte-identical.

---------------------------------------------------------------------------------------------------

## 2. Shared conventions and foundations (build first; part of Chunk 1)

New package `d:/Data/backend/app/phase5/`:
- `__init__.py`, `constants.py` (`STATUS = "EXPERIMENTAL_NOT_VALIDATED"`, `TABLE_PREFIX = "p5_"`, `SEED = 20260512`, `PHASE5_LOCK_LOG`, `PROVISIONAL_DEFINITION = "any|q0.75"`, `SENSITIVITY_DEFINITIONS = ("chase|q0.9", "any|q0.9", "chase|q0.75")`, versions).
- `store.py`: `write_p5_table` (regex `^p5_[a-z0-9_]+$`, refuses the official DB path, same pattern as `app/phase4/store.py`) and `table_hashes(store, prefix)` (content hash per table, used for preservation of `p4_*`).
- `data.py`: `load_pre_test_state(store)`: SQL joins `exp_pre_delivery_state` to `p4_match_period` with `period <> 'TEST'`, so TEST outcomes are never loaded; `load_test_match_state_nonoutcome(store)` selects only columns not starting with `out_`, `den_`, `post_innings_` (use `Split.outcome_prefixes`) for date-verification counts.
- `lockguard.py`: `Phase5Lock` wrapper that opens a closed `TestLock` on `phase5_lock_log.json`, plus `assert_phase4_lock_untouched(sha256)` comparing `phase4_lock_log.json` to the recorded hash.
- `pipeline.py`: `build_pretest_rows(store, definition)` = `load_pre_test_state` -> `prepare_frame` -> `add_signals` -> `fit_baseline_set` -> `en.base_rows` -> `en.tag_rows`, with `thr = sc.fit_thresholds(TRAIN, q)`. Includes `reproduce_phase4_scores(...)` that must match `p4_pressure_scores_frozen_rules` (any|q0.75, shrink_tau4, PRE_TEST) to 1e-9 before any investigation runs.
Reports go to `d:/Data/backend/data/reports/phase5_*` through `write_json_deterministic`/`write_text`. Seeds from `constants.SEED`. Scripts follow the `scripts/phase4_*.py` shape (`main(argv)`, `--store`, `--reports`, official-data snapshot before/after, exit 1 on change).

---------------------------------------------------------------------------------------------------

## CHUNK 1: classification migration + strict-uncapped disabling + publication gating layer

**Depends on:** nothing new. Foundations of section 2 are created here.
**Reuses:** `classification.py` (validate_overrides, apply_overrides, coverage), `serving.run_classification`, `uncapped.py`, `selection.assign_group`, `routes.py`, `deps.py`, `errors.py`, `schemas/phase4.py`, `spotchecks.check_capped_count`.

**Create**
- `d:/Data/backend/app/phase5/__init__.py`, `constants.py`, `store.py`, `lockguard.py`, `data.py`, `pipeline.py` (section 2; pipeline can be finished in Chunk 3 but its reproduce check is used from Chunk 3).
- `d:/Data/backend/app/phase5/classification_v2.py`: `STATUS_VALUES`, `MIGRATION_MAP`, `migrate_classification(df)` (raises on unmapped combos, asserts row count and counts), `validate_overrides_v2` (enum `VERIFIED_CAPPED|VERIFIED_UNCAPPED`, rejects legacy values, requires source/verified_by/verified_date), `apply_overrides_v2`, `coverage_v2` (counts for nationality x status including UNKNOWN_STATUS group), `strict_uncapped_capability(classification, overrides, source_manifest, scored_ids, cfg)` returning `{enabled, reasons, source_needed, verified_coverage}`.
- `d:/Data/backend/app/phase5/gating.py`: `GateInput`, `GateResult`, `evaluate_gates(inputs, request_needs)`, `publication_status(gates)`, `load_gate_inputs(repo)` (reads `phase4_frozen_choices.json`, `config/phase5_methodology_status_v1.json`, date-verification summary JSON when present, otherwise reports `date_verification` as failed with reason `NOT_RUN`).
- `d:/Data/backend/app/schemas/phase5.py` (Pydantic v2): `GateResultModel`, `PublicationFlags` (mixed into `Flags`), `StrictUncappedDisabledResponse`, `CapabilitiesResponse`, `PublicationGatesResponse`.
- `d:/Data/backend/scripts/phase5_classification.py`: runs migration against the stored `p4_player_classification` and `p4_player_classification_base`, writes `p5_player_classification`, `p5_player_classification_base`, `p5_classification_migration_map`, `p5_classification_coverage`, `p5_strict_uncapped_capability`; writes reports.
- `d:/Data/backend/scripts/phase5_gates.py`: evaluates gates, writes `p5_publication_gates` and `phase5_publication_gates.json`/`.md`.
- Configs: `d:/Data/backend/config/phase5_classification_v2.json` (version `p5_classification_v2`, mapping, `min_verified_coverage: 0.95` provisional, `source_needed` text), `d:/Data/backend/config/classification_source_manifest_v1.json` (`{"sources": []}`), `d:/Data/backend/config/phase5_gates_v1.json` (`min_public_pool: 10`, gate list), `d:/Data/backend/config/phase5_methodology_status_v1.json` (`validated: false`, reasons).

**Modify**
- `app/phase4/classification.py`: keep as the Phase 4 builder (its output is the preserved legacy table). Only change: nothing that alters `p4_*` output. Add a pointer docstring to `classification_v2`.
- `app/phase4/uncapped.py`: `effective_classification` reads the new enum (`eff_status` in the four-value enum; `VERIFIED_ONLY` basis maps `DERIVED_CAPPED` to `UNKNOWN`); `ClassificationFilter.capped` becomes `capped_any`, `capped_verified`, `capped_derived`; uncapped filters stay but raise `StrictUncappedDisabled` when the capability is false.
- `app/phase4/selection.py:assign_group`: map the new enum (`VERIFIED_CAPPED`/`DERIVED_CAPPED` -> `*_CAPPED`, `VERIFIED_UNCAPPED` -> `*_UNCAPPED`, otherwise `UNKNOWN`).
- `app/phase4/views.py`, `profiles.py`: use the new enum; pass `publication_status`/`gate_results` through result rows.
- `app/phase4/spotchecks.py:check_capped_count`: compare against `DERIVED_CAPPED + VERIFIED_CAPPED`.
- `app/repositories/phase4_repo.py`: require `p5_player_classification` (no fallback to the legacy table); `reload_classification` rebuilds from `p5_player_classification_base` with v2 override validation; expose `capability()`.
- `app/services/phase4_service.py`: `flags()` returns `status`, `official_ranking`, `disclaimer`, `publication_status`, `gate_results`; `uncapped_ranking`, `run_preset`, `compose` return the `STRICT_UNCAPPED_DISABLED` body when D4 applies; coverage endpoint reports the three separate values and `UNKNOWN_STATUS`.
- `app/api/deps.py`: add `require_internal` (alias of the admin token check, header `X-Admin-Token`); `app/api/errors.py`: map `StrictUncappedDisabled`/`PublicationGateError`.
- `app/api/v1/routes.py`: add `internal` router (`/internal`, token required) mounting the ranking, selection, profile, compare and uncapped handlers; the public paths for those return 403 `PUBLICATION_GATE_NOT_SATISFIED` with gate details and no rows; add public `GET /meta/capabilities` and `GET /meta/publication-gates`.
- `app/schemas/phase4.py`: `GroupName` unchanged ids; `ClassifiedPlayer.international_status` literal becomes the four-value enum; `Flags` gains the two publication fields; add `group_label` (`UNKNOWN_STATUS`).
- `app/main.py`: `create_app(..., gate_inputs=None)`; version string `phase5-experimental`.
- `config/phase4_selection_presets_v1.json`: untouched (preserved); the service reads the capability instead. `config/classification_overrides_v1.csv`: stays header-only and byte-identical.
- Docs: add sections to `docs/frontend_backend_contracts.md` (classification enum change and mapping table, `STRICT_UNCAPPED_DISABLED`, `PUBLICATION_GATE_NOT_SATISFIED`, publication fields) and `docs/backend_implementation_spec.md`. Final doc pass is in Chunk 4/5; Chunk 1 writes the classification and gating parts.

**Tables:** `p5_player_classification`, `p5_player_classification_base`, `p5_classification_migration_map`, `p5_classification_coverage`, `p5_strict_uncapped_capability`, `p5_publication_gates`.

**Tests (`d:/Data/backend/tests/`)**
- `test_phase5_classification.py`: three separate values stay separate; migration of every mapped combination and failure on unmapped combos; migrated counts equal Phase 4 counts on synthetic data; no inference from names, domestic experience or IPL participation (a player with an IPL squad row and 50 IPL matches but no T20I stays UNKNOWN; a name like "Uncapped" is ignored); override validation (missing source, missing verified_by, bad date, legacy `Capped` value, duplicate, unknown player_id); a `VERIFIED_CAPPED` override changes only that player; derived rows unaffected; real-data test (`@pytest.mark.realdata`) recomputes the 655/562 counts from `playing_eleven.csv`, `matches.csv`, `competitions.csv`.
- `test_phase5_strict_uncapped.py`: capability false with empty overrides; true only with a validated authoritative source + coverage; every uncapped endpoint (`/internal/rankings/uncapped/{kind}` all 5 kinds), all 6 presets, a custom selection naming `IN_UNCAPPED min 1`, and `uncapped_mode=include_uncapped` return `STRICT_UNCAPPED_DISABLED` with `rows == []`; `exclude_uncapped` still works.
- `test_phase5_gating.py`: all gates failing -> every output `INTERNAL_EXPERIMENTAL_ONLY`; each single gate failing blocks PUBLIC_ALLOWED; all-pass synthetic fixture -> `PUBLIC_ALLOWED`; public routes return 403 `PUBLICATION_GATE_NOT_SATISFIED` with failing gates and no rows; internal routes need the token (401/503 otherwise) and return the status; descriptive routes carry flags.
- Update the Phase 4 tests listed in section 0 with the explicit mapping; run the whole suite, record every modified test and why in the verification file.

**Reports:** `phase5_classification_migration.md` (+ `.json`/`.csv` coverage), `phase5_publication_gates.md` (+ `.json`).

**Verify:** `python -m pytest -q tests/test_phase5_classification.py tests/test_phase5_strict_uncapped.py tests/test_phase5_gating.py tests/test_phase4_api.py tests/test_phase4_classification.py tests/test_phase4_selection.py`; `python scripts/phase5_classification.py`; `python scripts/phase5_gates.py`; `python -m ruff check .` and `python -m ruff format --check .`. Counts in the report equal 655 / 562 / 0 / 0.

---------------------------------------------------------------------------------------------------

## CHUNK 2: T20I date verification + restricted TEST set manifest (lock respected)

**Depends on:** Chunk 1 foundations (`store.py`, `data.py`, `lockguard.py`, `gating.py` for the `date_verification` gate input).
**Reuses:** `app/data_pipeline/cricsheet_auditor.py` (`normalise_team`, `build_index`), `app/validation/cricsheet_super_over.py` (`map_official_match` idea; the staged `data/staging/cricsheet_index.parquet`), `Split`, `p4_match_period`, `app/phase4/reports.py:late_t20i_dates`.

**Create**
- `d:/Data/backend/app/phase5/date_verification.py` (the only Phase 5 module allowed to touch Cricsheet; validation-only evidence, secondary, not an official record):
  - `collect_evidence(match_row, ...)` for each of 42 matches (and, for context, all 144 TEST matches): (a) first/last `delivery_ist_time` date part from `raw_ball_by_ball_updated` (read-only), flag `timestamp_informative` (false if all times are `00:00:00` placeholders), agree if within +-1 day, conflict at 2+ days; (b) `ordering_consistent` (date non-decreasing with `match_number` within the comp, spacing, no team playing twice on one date), internal only; (c) `season_token_consistent` (season 2026 vs date year), weak and internal; (d) `matches 2026.csv` overlap, `NOT_APPLICABLE` for T20I; (e) Cricsheet: candidates are same normalised team pair within +-3 days and in the T20I directories, identity confirmed by non-date facts (winner and first-innings total from `innings_json`; `match_number`/event if present), then compare dates; (f) `internal_conflicts`.
  - `classify(evidence)`: `DATE_CONSISTENT_ACROSS_SOURCES` when >= 2 independent informative sources (timestamps from the ball-by-ball file and Cricsheet; the ordering and season checks are internal and cannot add to the count) agree and none conflicts; `DATE_SINGLE_SOURCE`; `DATE_CONFLICT` (any source disagrees or an internal check fails); `DATE_UNVERIFIED`. Output also `official_verified: false` for every row (no authoritative record is supplied) with the statement that none is official-verified.
  - `load_official_verification(csv)` validates the user template (`match_id, verified_date, source, verified_by, date_of_verification`; ISO dates; known T20I match ids) and returns `OFFICIAL_VERIFIED` rows; a user-supplied date that differs from the original is recorded as a conflict and the original is NOT changed.
  - Originals are never modified: output keeps `original_match_date` and a SHA-256 of the `matches` table date column before and after.
- `d:/Data/backend/app/phase5/test_manifest.py`: builds `PRIMARY_RESTRICTED`, `STRICT_OFFICIAL_ONLY`, `SENSITIVITY_ALL` (D2); counts matches, deliveries and distinct players (striker/bowler ids from non-outcome state columns only) per set and per competition; writes the manifest with its own SHA-256; includes the 2 T20I TEST-period matches present in `matches` but absent from the state (find the ids, explain, count them).
- `d:/Data/backend/scripts/phase5_date_verification.py`: runs the checks, writes tables and reports, asserts the lock log is unchanged, prints the 42-row class distribution.
- `d:/Data/backend/config/phase5_date_verification_v1.json` (tolerance days 1, Cricsheet window 3 days, independence rules, `test_core_end` from the split config, primary-set rule D2). `d:/Data/backend/config/t20i_official_date_verification_template.csv` (header + one commented example is NOT allowed; header only) and a copy at `d:/Data/backend/data/reports/phase5_t20i_official_verification_template.csv`.

**Modify:** `app/phase5/gating.py` reads the summary JSON for the `date_verification` gate; `app/phase4/reports.py` is NOT edited (Phase 4 reports preserved).

**Tables:** `p5_t20i_date_verification` (42 rows), `p5_test_match_date_check` (all TEST matches), `p5_test_set_manifest`, `p5_test_set_membership` (match_id, set name, member flag).

**Tests:** `test_phase5_date_verification.py`: synthetic cases for each of the four classes (two agreeing sources; one source; timestamp conflict of 2+ days; no source); internal ordering violation yields conflict; internal checks never raise a single-source row to consistent; +-1 day tolerance; placeholder timestamps (`00:00:00`) not informative; originals never modified (hash before/after, function never writes `matches`); primary set excludes every non-consistent late match and includes OFFICIAL_VERIFIED rows; strict set is empty with an empty template and populated with a synthetic valid template; template validation errors; the TEST lock is respected (`phase4_lock_log.json` bytes unchanged, no `OPEN` in `phase5_lock_log.json`, test-state loader never selects `out_/den_/post_innings_` columns); recompute-from-raw check (`@pytest.mark.realdata`): the 42 ids and class of 3 matches recomputed with the `csv` module from `matches.csv` and `updated_ball_by_ball.csv`.

**Reports:** `phase5_t20i_date_verification.md` + `.csv` + `.json` (per-match table of all 42 with evidence columns), `phase5_test_set_manifest.json`, section on the lock option D1 and the open decision on set strictness; unresolved issues list.

**Verify:** `python -m pytest -q tests/test_phase5_date_verification.py`; `python scripts/phase5_date_verification.py`; compare `phase4_lock_log.json` SHA-256 before/after (must equal `86f5ce9d...`); confirm the 42 originals unchanged by comparing to `matches.csv`.

---------------------------------------------------------------------------------------------------

## CHUNK 3: investigations (reliability/variance decomposition, sensitivity, ranking stability) + context-stats foundation

**Depends on:** Chunk 1 (`pipeline.py`, `data.py`, `lockguard.py`), Chunk 2 (test-set manifest for the date-restricted sensitivity counts).
**Reuses:** `engine.py`, `shrink.py`, `definitions.py:rs_stats`, `eligibility.py`, `sensitivity.py`, `scoring.py`, `config/format_weights_v1.json` (8 configs), `config/phase4_definition_rule_v1.json`.

**Create**
- `d:/Data/backend/app/phase5/reliability.py`:
  - `variance_decomposition(cell)`: between-player variance (`shrink.fit_cell` moment), within-noise variance, mean noise, SNR, ICC = tau2 / (tau2 + sigma2 / mean n_eff); report when tau2 <= 0 as `BETWEEN_VARIANCE_NOT_POSITIVE`.
  - `split_half(cell, mode)`: odd/even match rank and early/late halves, Spearman-Brown corrected, players with a minimum balls count; `bootstrap_by_match` CIs (`engine.global_weights`).
  - `reliability_by_opportunity(cell, bins)`: reliability inside balls bins.
  - `required_sample(tau2, sigma2, targets=(0.5, 0.7, 0.8))`: n_eff = R/(1-R) * sigma2/tau2, labelled `DESCRIPTIVE_PROJECTION`; `NOT_ESTIMABLE` when tau2 <= 0 (never a fabricated number).
  - `multi_format_pooling(cell_ipl, cell_t20i)`: players present in both; pooled versus single-format split-half and SNR (descriptive, baselines differ by competition).
- `d:/Data/backend/app/phase5/pressure_signals.py`: pre-declared bowler-specific pressure candidates (3, written to config before any run, SENSITIVITY_ONLY): fielding-side defence margin (`gap`/`projected_surplus` TRAIN-quantile), death phase with close gap, batting side wickets-remaining <= bin. Thresholds TRAIN only; same residual/shrink pipeline; clear label "does not replace the primary definition".
- `d:/Data/backend/app/phase5/sensitivity.py`: runs (b) over definitions {any|q0.75, chase|q0.9, any|q0.9, chase|q0.75} x thresholds (q grid from the rule file) x 7 shrinkage configs (`shrink.CONFIGS`) x baseline alternatives (`phase4.sensitivity.baseline_alternatives`) x 8 format weights (primary definition; the same frozen working-pool ball thresholds 20/16/49/29 for every run; independent of the definition axis) with Top-10 overlap, Spearman and pool size against the primary; date-restricted TEST sensitivity reported as set composition and affected-coverage counts only (no outcomes, because TEST stays closed; state this limit).
- `d:/Data/backend/app/phase5/stability.py`: bootstrap Top-10 inclusion probabilities, rank intervals, expected overlap, Spearman (via `engine.rank_summary`/`summarize_ranking`), for overall and for each atomic context (below), and across definitions.
- `d:/Data/backend/app/phase5/context_stats.py` (foundation reused by Chunk 4): `build_context_stats(rows_tagged, d)` -> one row per (player_id, match_id, comp, role, stream, period, phase, situation) with `n, s, s2` for pressure rows of the carried definition (`phase` from `innings_phase`, `situation` from `innings_number`); `aggregate(stats, filters)`; `context_cell(stats, comp, role, phase, situation)` -> `engine.Cell` equivalent so the Phase 4 eligibility and shrink code can run on it. Pre-test periods only.
- Scripts: `scripts/phase5_investigate_reliability.py`, `scripts/phase5_sensitivity.py`, `scripts/phase5_stability.py`, `scripts/phase5_context_stats.py`.
- Config: `d:/Data/backend/config/phase5_investigation_v1.json` (definitions, split-half modes, min balls, reliability targets, bowler-signal candidates with their parameter names, `n_boot 1000`, seed).

**Tables:** `p5_variance_decomposition`, `p5_split_half_reliability`, `p5_reliability_by_opportunity`, `p5_required_sample_projection`, `p5_multiformat_pooling`, `p5_bowler_signal_sensitivity`, `p5_sensitivity_results`, `p5_sensitivity_pairwise`, `p5_ranking_stability`, `p5_ranking_distributions`, `p5_context_stats`.

**Tests**
- `test_phase5_reliability.py`: split-half and ICC on synthetic data with known variance components (simulate tau2, sigma2, n; recovered ICC and Spearman-Brown reliability within tolerance); an independent implementation (plain numpy loops) agrees with `reliability.py`; tau2 <= 0 case returns `NOT_ESTIMABLE`; required-sample formula against hand values; bowler-signal thresholds use TRAIN rows only (perturbing VALIDATION rows leaves thresholds unchanged); pooling function only uses players in both formats.
- `test_phase5_sensitivity_stability.py`: seeded determinism (same hash on two runs); `reproduce_phase4_scores` equals the stored Phase 4 scores (realdata); primary and three alternatives all present in outputs; labels contain PROVISIONAL and never "validated"; stability pool never padded when fewer than 10 players; no TEST rows enter any frame (`drop_test_rows`/SQL filter asserted; a synthetic store with TEST sentinels never leaks).
- `test_phase5_context_stats.py`: sums of context rows over all contexts equal the overall pressure player-match stats (n, s); phases partition the rows; sentinel TEST rows excluded.

**Reports:** `phase5_investigation_report.md` (why signal-to-noise is at or below zero in all four format-role cells for `any|q0.75`: tau2 estimates, sigma2, ICC, split-half by format/role/stream and by definition; required sample projections; bowler-signal sensitivity; multi-format pooling; honest "cannot be supported" statements), `phase5_sensitivity_report.md`, `phase5_ranking_stability.md` (new files; Phase 4 `phase4_ranking_stability.md` untouched), each with JSON/CSV; unresolved-issues section.

**Verify:** `python -m pytest -q tests/test_phase5_reliability.py tests/test_phase5_sensitivity_stability.py tests/test_phase5_context_stats.py`; run the four scripts; confirm `phase4_*` report hashes unchanged and `phase4_lock_log.json` hash unchanged; independent spot check: split-half reliability of one cell recomputed with a separate numpy implementation (recorded in the spot-check JSON).

---------------------------------------------------------------------------------------------------

## CHUNK 4: dynamic ranking engine + context eligibility + coverage + API + caching + docs

**Depends on:** Chunk 1 (enum, capability, gates, internal router), Chunk 3 (`p5_context_stats`, `context_stats.py`, stability helpers).
**Reuses:** `shrink.py`, `engine.py` (draws, rank_summary, player_ranking_table), `eligibility.py` (derivation), `scoring.combine_formats` (COMBINED_w70_30), `views.py` column conventions (bowler score negated so higher is better), `selection.py` and presets (integration), `phase4_service.paginate`.

**Create**
- `d:/Data/backend/app/phase5/filters.py`: `FilterSpec` (Pydantic v2, `extra="forbid"`): `format` (IPL|T20I|COMBINED_w70_30), `role` (batter|bowler, required), `nationality` (Indian|Overseas|None), `status` (`CAPPED_ANY|VERIFIED_CAPPED|DERIVED_CAPPED|VERIFIED_UNCAPPED|UNKNOWN_STATUS|None`), `phase` (ALL|powerplay|middle|death), `situation` (ALL|chase|first_innings), `min_matches`, `min_context_matches`, `include_unknown_nationality`, `include_unknown_status` (default false), `limit`, `offset`, `sort` whitelist (`rank|score|name|matches|n|n_eff`) with `order`. `canonical_json(spec)`; `spec_hash(spec, versions)`; `validate_combination(spec, capability)` -> reason codes; AND semantics across all selected filters.
- `d:/Data/backend/app/phase5/context_eligibility.py`: for each atomic context (comp x role x phase x situation = 48 cells incl. ALL) run `evaluate_cell` + `decide` + `analysis_rule` on the TRAIN/VALIDATION context cell; context-specific `window_ratio`; statuses `ELIGIBLE_WORKING_POOL_NOT_VALIDATED`, `INSUFFICIENT_SAMPLE_FOR_CONTEXT`, `CONTEXT_NOT_ESTIMABLE`, `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT`; rules and fits stored (`p5_context_eligibility_rules`, `p5_context_fit`); pre-declared minimum TRAIN players for a fit (config) with documented floor behaviour.
- `d:/Data/backend/app/phase5/ranking_engine.py`: `ContextScoreTable` (precomputed per atomic context: n, matches, n_eff, mean residual, expected, raw, shrunk, k, tau2, floor flags) and `rank(spec, tables, capability, gates)`: capability check -> context lookup -> eligibility -> classification filter with excluded counts -> pool-size rule -> seeded bootstrap on the filtered pool (intervals, rank interval, Top-10 inclusion probability) -> sort (score desc, `player_id` asc) -> paginate. Per-row explanation: raw, expected, residual, shrunk, interval, rank interval, Top-10 inclusion probability, `n`, matches, `n_eff`, eligibility status and threshold, restrictions applied, classification fields with verification status, definition/baseline/shrinkage versions, filter echo, config hashes, `publication_status`, `gate_results`. Empty or short results carry `reasons` with codes and counts. COMBINED_w70_30 requires eligibility in both formats in that context.
- `d:/Data/backend/app/phase5/cache.py`: in-memory deterministic cache keyed by `spec_hash` + `data_version` (hash of the p5 tables and lock/config hashes) + `model_version`; `get/put/invalidate_if_version_changed`; hit/miss counters; cached value equals recomputed value.
- `d:/Data/backend/app/phase5/coverage.py`: enumerates every valid filter combination (format x role x nationality x status x phase x situation, only enabled values; strict-uncapped values listed as `DISABLED`) and records eligible player counts, reason and whether the minimum pool rule is met; actual counts (no estimate).
- `d:/Data/backend/app/repositories/phase5_repo.py` (loads p5 tables read-only, one place for versions), `d:/Data/backend/app/services/phase5_service.py` (catalog, preview, ranking, coverage), `d:/Data/backend/app/api/v1/routes_phase5.py`:
  - `GET  /api/v1/internal/filters/catalog` (valid values, enabled/disabled and why, the capability flag, wickets bands disabled).
  - `POST /api/v1/internal/rankings/context-preview` (qualifying player count, per-reason exclusion counts, before ranking).
  - `POST /api/v1/internal/rankings/dynamic` (ranking with pagination and explanations).
  - `GET  /api/v1/internal/rankings/coverage` (paginated coverage table).
  - Public stubs of the same capability return 403 `PUBLICATION_GATE_NOT_SATISFIED`.
- Scripts: `scripts/phase5_context_engine.py` (builds `p5_context_eligibility_rules`, `p5_context_fit`, `p5_context_scores`, `p5_context_coverage`), `scripts/phase5_dynamic_demo.py` (runs the example filter sets and writes `phase5_dynamic_examples.json`).
- Config: `d:/Data/backend/config/phase5_context_rules_v1.json` (`min_internal_pool: 5`, `min_public_pool: 10`, `min_train_players_for_fit`, atomic context lists, floor 0.01, `n_boot 1000`, seed, sort whitelist, page size caps, disabled features with reasons).
- Docs: `d:/Data/backend/docs/frontend_backend_contracts.md` and `docs/backend_implementation_spec.md` updated (workflow, filter spec schema, gates, error/status model, versioning, caching, how a future public release works once gates pass, classification enum change). New `d:/Data/backend/data/reports/phase5_dynamic_ranking_architecture.md`.

**Modify:** `app/main.py` includes the Phase 5 router; `app/api/errors.py` maps `FilterSpecError`; `phase4_service.run_preset`/`compose` integration already done in Chunk 1 (strict-uncapped presets return the disabled body; non-uncapped selection still works over the stored scores).

**Tables:** `p5_context_eligibility_rules`, `p5_context_fit`, `p5_context_scores`, `p5_context_coverage`, `p5_filter_catalog`.

**Tests (`tests/test_phase5_dynamic_ranking.py`, `tests/test_phase5_context_api.py`)**
- Synthetic pools: AND semantics for combined filters; batter and bowler lists are separate; classification exclusion counts reported (`CLASSIFICATION_UNKNOWN_EXCLUDED`) and `include_unknown_*` toggles; context recomputation of `n`, `n_eff`, matches, uncertainty and eligibility (hand-computed from the stats rows); no padding and fewer-than-10 results; empty result reasons (`POOL_TOO_SMALL`, `INSUFFICIENT_SAMPLE_FOR_CONTEXT`); deterministic tie-break by `player_id`; cache key stable for equal specs (key order irrelevant), changes with any filter, version bump invalidates; cached equals recomputed.
- "No separate model": the same stored `p5_context_stats` rows reproduce the overall result and every context result, and the engine imports no estimator trained per filter (assert a single `fit_cell` call path per atomic context and none per filter combination).
- "A filter cannot create reliability": a player eligible overall with a context sample below the context threshold is `INSUFFICIENT_SAMPLE_FOR_CONTEXT`; a context with zero eligible players returns an empty result with reasons; death + chase + Indian + DERIVED_CAPPED is empty on the real data (assert from the stored coverage table, not an invented expectation).
- No future leakage: context-specific tau2 is computed from TRAIN rows only (perturb VALIDATION rows in a synthetic store and the context fit is unchanged; perturb TRAIN rows and it changes).
- API via HTTPX `TestClient`: catalog, preview, ranking, coverage schemas validate; unknown fields rejected (422); invalid enum rejected; `limit`/`offset` bounds; internal token required (401/503); public stubs 403 with gate details and no rows; strict-uncapped filters return `STRICT_UNCAPPED_DISABLED`; responses carry `publication_status` and `gate_results`; no raw SQL or path accepted.
- Example filter sets from the user: All players, Indian + Batter, Overseas + Capped (DERIVED/VERIFIED), Death overs, Chase situations, custom combination, Indian + Uncapped (disabled), Uncapped + Bowler (disabled).

**Reports:** `phase5_dynamic_ranking_architecture.md`; `phase5_context_coverage.csv/.json` (real counts per combination and the minimum pool rule).

**Verify:** `python -m pytest -q tests/test_phase5_dynamic_ranking.py tests/test_phase5_context_api.py`; `python scripts/phase5_context_engine.py`; `python scripts/phase5_dynamic_demo.py`; independent spot check: one player's context-specific `n` and residual sum recomputed with pandas from `p5_context_stats` and again from `exp_pre_delivery_state` joined to the stored baseline expectations, equal to the engine output; strict-uncapped disabled responses captured from the running app.

---------------------------------------------------------------------------------------------------

## CHUNK 5: methodology lock + refit + reports + orchestrator + README

**Depends on:** Chunks 1 to 4.
**Reuses:** Phase 4 pipeline functions via the relabelling approach (D8), `analytics.reporting.code_version`, `integrity.snapshot_from_settings`, `run_phase4.py` structure (not its lock-log reset).

**Create**
- `d:/Data/backend/app/phase5/lock_manifest.py`: `pre_lock_checklist()` (auto-checked items: Phase 5 investigation reports exist and are non-empty; unresolved issues file present; date-verification manifest present; strict-uncapped capability recorded; gates evaluated; Phase 4 outputs and `phase4_lock_log.json` unchanged; items needing a human decision are listed as `USER_APPROVAL_PENDING` and do not turn into validation claims), `build_lock_manifest()` (SHA-256 of config files, restrictions register `data_quality_restrictions_v1.json`, `pressure_rules_v1.json`, split config, definition (`any|q0.75` with the three alternatives), working-pool thresholds, shrinkage choice `shrink_tau4`, features/streams, classification version, test-set manifest hash, code version), `verify_lock()` (recomputes and compares; any drift raises `LockDriftError`).
- `d:/Data/backend/app/phase5/refit.py`: `run_refit(manifest)`: refuses without a valid lock; builds the TRAIN+VALIDATION relabelled frame from `load_pre_test_state`; asserts no row has `period_orig == "TEST"`; fits baseline, thresholds, shrinkage; scores all four cells with the locked definition and locked ball thresholds; compares with the original Phase 4 scores (Top-10 overlap, Spearman, mean absolute change per cell); writes `p5_refit_trainval_v1_scores`, `_baseline_calibration`, `_thresholds`, `_comparison`, `_manifest`; never modifies `p4_*` tables.
- `d:/Data/backend/app/phase5/reports.py`: renderers for every Phase 5 report (numbers read from the stored JSON/tables, templates only).
- Scripts: `scripts/phase5_lock.py` (explicit; requires `--confirm-lock`; writes `phase5_methodology_lock.json`, labelled `EXPERIMENTAL_LOCK` (it locks choices for the experimental refit, it does not validate the methodology)), `scripts/phase5_refit.py` (reads the lock, refuses otherwise), `scripts/phase5_reports.py`, `scripts/run_phase5.py` (orchestrator: steps `phase5_classification, phase5_gates, phase5_date_verification, phase5_context_stats, phase5_investigate_reliability, phase5_sensitivity, phase5_stability, phase5_context_engine, phase5_lock, phase5_refit, phase5_reports, phase5_spotchecks`; official-data snapshot before and after with `assert_unchanged`; hashes of all `phase4_*` reports, the `p4_*` table contents and `phase4_lock_log.json` before and after; `phase5_lock_log.json` must have no `OPEN`; deliverables check; `output_hashes` and `--compare-hashes` for determinism; exit 1 on any failure; it never imports or invokes `run_phase4.py` and never writes `phase4_lock_log.json`).
- `scripts/phase5_spotchecks.py` + `app/phase5/spotchecks.py`: at least 5 independent checks recorded in `phase5_spot_checks.json`: (1) a context-specific player `n` and residual recomputed with pandas from `p5_context_stats`; (2) one date-verification classification recomputed from raw CSVs; (3) classification counts (655/562) from raw files; (4) split-half reliability recomputed with an independent numpy implementation; (5) strict-uncapped disabled responses from a live `TestClient` app; (6) official hash equality; (7) refit does not touch TEST (frame period set check).
- Config: `d:/Data/backend/config/phase5_methodology_lock_v1.json` (items to hash, checklist definition, label `EXPERIMENTAL_LOCK`).
- Reports (all in `d:/Data/backend/data/reports/`): `phase5_investigation_report.md`, `phase5_t20i_date_verification.md` (+CSV/JSON + template), `phase5_classification_migration.md`, `phase5_sensitivity_report.md`, `phase5_ranking_stability.md`, `phase5_publication_gates.md`, `phase5_methodology_lock_and_refit.md`, `phase5_dynamic_ranking_architecture.md`, `phase5_user_summary.md` (copy also to `d:/Data/.agents/tasks/phase5_user_summary.md`), `phase5_unresolved_issues.md` (exact failing gates and open decisions: strict-uncapped source, 42 dates, data-weight gate, methodology validation, primary TEST strictness, lock/pristine hold-out caveat, minimum pool values, unvalidated pressure definition).
- `d:/Data/backend/README.md`: new "Phase 5" section (commands, tables, endpoints, how to supply official dates and cap sources, what is blocked).

**Tables:** `p5_methodology_lock`, `p5_refit_trainval_v1_scores`, `p5_refit_trainval_v1_baseline_calibration`, `p5_refit_trainval_v1_thresholds`, `p5_refit_trainval_v1_comparison`, `p5_refit_trainval_v1_manifest`, `p5_output_hashes`.

**Tests (`tests/test_phase5_lock_refit.py`, `tests/test_phase5_contamination.py`, `tests/test_phase5_orchestrator.py`)**
- Lock manifest hash is stable across runs and changes when any locked config byte changes; `verify_lock` raises on drift; refit refuses to run without a lock or with a drifted lock; refit frame contains no TEST rows (synthetic store with TEST sentinel rows); original TRAIN-only tables and the Phase 4 reports are byte-identical after the refit (hash before/after); `phase4_lock_log.json` unchanged and `phase5_lock_log.json` has no `OPEN`; refit reproducible (two runs, identical hashes); relabelling approach leaves the original `period` available as `period_orig`.
- Contamination: AST scan shows no scoring/baseline/ranking module (`app/phase4/*`, `app/phase5/*` except `date_verification.py`, `app/services/*`, `app/repositories/*`) imports `app.data_pipeline.cricsheet_auditor`, `app.validation.cricsheet_super_over` or contains a Cricsheet directory literal; `date_verification.py` is the only importer and its output table name contains `date_verification`; no `p5_` scoring table has a Cricsheet-derived column.
- Orchestrator: step list, deliverable check, preservation fields, no reference to `run_phase4` or writes to the Phase 4 lock log (AST/text scan).
- Whole-suite expectation: all 509 original tests pass except tests deliberately updated for the classification/gating migration (listed one by one in the verification file).

**Verify:** `python -m pytest -q tests/test_phase5_lock_refit.py tests/test_phase5_contamination.py tests/test_phase5_orchestrator.py`; `python scripts/phase5_lock.py --confirm-lock`; `python scripts/phase5_refit.py`; `python scripts/run_phase5.py` twice with `--compare-hashes` (second run must show no differences).

---------------------------------------------------------------------------------------------------

## FINAL VERIFICATION (after Chunk 5; feeds the semantic review `d:/Data/.agents/tasks/phase5_review.json {verdict, findings, reviewDoc}`)

1. `python -m pytest -q` (all tests; count >= 509 + new Phase 5 tests; list every Phase 4 test modified and why).
2. `python -m ruff check .` and `python -m ruff format --check .` (no errors).
3. `python scripts/run_phase5.py` end to end on real data, twice, with `--compare-hashes`; `official data unchanged: True`; deliverables all present and non-empty.
4. Preservation: SHA-256 of `superr.duckdb` and every source CSV equal `phase5_prerun_hashes.json`; `phase4_*` reports and `p4_*` tables unchanged; `phase4_lock_log.json` equals the recorded hash with exactly FREEZE, OPEN, CLOSE; `phase5_lock_log.json` has no OPEN.
5. At least 5 independent spot checks recorded in `phase5_spot_checks.json` (list in Chunk 5).
6. Review checklist (each item answered with evidence in `phase5_verification.md`): scope limits respected (no official Top 10, no official model, no validation claims); capped status never inferred; three values separate; strict uncapped disabled everywhere (endpoints, presets, constraints); original dates untouched; unverified dates excluded from the primary TEST set and counts reported; gating real (public routes return no rows); no separate models per filter; context eligibility genuinely recomputed from the stored rows; no padding; TEST untouched; no leakage (TRAIN-only fits and thresholds); honest labelling (EXPERIMENTAL, PROVISIONAL); official data preserved; Cricsheet used only as date-verification evidence; tests exercise real behaviour (no tautologies).
7. Stop and request user review. Do not start official rankings or model training.

---------------------------------------------------------------------------------------------------

## Open decisions and risks to record (do not resolve silently)

1. Primary TEST strictness (D2) and whether a later TEST evaluation is still a clean hold-out (Phase 4 aggregates were already shown).
2. Minimum pools: internal 5, public 10 (provisional config values).
3. `min_verified_coverage` 0.95 for enabling strict uncapped (provisional).
4. Whether the refit keeps `shrink_tau4` (chosen on VALIDATION in Phase 4) or the investigation suggests a change; Phase 5 keeps it and reports the sensitivity.
5. Phase 4 test updates are unavoidable for the label migration and the public-route gating; each is listed. Keep the count of tests from decreasing.
6. Unknown nationality (447 players) is a large share of the pool; the default exclusion will shrink every classification-filtered list. Report excluded counts.
7. 2 T20I TEST-period matches present in `matches` but absent from the Phase 4 state need an explanation in Chunk 2.
8. If signal-to-noise stays at or below zero, rankings are fragile regardless of filters; the reports must say so and not suggest filters fix it.
