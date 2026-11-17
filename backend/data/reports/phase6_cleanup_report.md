# Phase 6 cleanup report

Status: `EXPERIMENTAL_NOT_VALIDATED`. INTERNAL only. No official Top 10, no public experimental ranking, no ML training, no change to the methodology, thresholds or the 0.5 data-weight gate. Numbers below come from `scripts/phase6_cleanup_checks.py` run on the real code and data.

## 1. Classification wording (decision 1)
- Real values: `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`. Disabled placeholder (not an established fourth status): `VERIFIED_UNCAPPED`.
- `GET /meta/capabilities` now lists `classification_values` = ['VERIFIED_CAPPED', 'DERIVED_CAPPED', 'UNKNOWN'] and `disabled_placeholder_values` = ['VERIFIED_UNCAPPED']. `strict_uncapped_enabled` = False.
- Real data (1217 players): status counts {'VERIFIED_CAPPED': 0, 'DERIVED_CAPPED': 655, 'UNKNOWN': 562}; placeholder count {'VERIFIED_UNCAPPED': 0}; coverage has 9 combinations (3 nationalities x 3 real statuses).
- Unchanged: the strict-uncapped filter still answers `STRICT_UNCAPPED_DISABLED`, the validated override mechanism still accepts the placeholder value, and verified status is never inferred.
- Wording scan over 8 contract, spec, schema and generator files for a four-valued description: 0 files with hits (none).
- Stored Phase 5 reports (`phase5_*`) are byte-identical and were not rewritten. They still contain the old four-status wording in places. The corrected wording is in the generators and in this Phase 6 output.
- `docs/phase5_design.md` is a historical design record and still describes four values; it is superseded by section 10 of `docs/frontend_backend_contracts.md` and section 12 of `docs/backend_implementation_spec.md`.

## 2. Vacuous assertions (decision 6b)
- Before: 3 always-true assertions, found by grep (the brief named two; the scan found a third).
  - `tests/test_phase5_dynamic_ranking.py:583`: `assert r["interval_low"] <= r["score"] <= r["interval_high"] or True`
  - `tests/test_phase5_dynamic_ranking.py:594`: `assert len(table) == len(specs) == len(set(table["spec_hash"]) | set()) or True`
  - `tests/test_pressure_state.py:45`: `assert s.team_wickets_before.tolist() == [0, 0, 0, 0, 0, 1, 1][:3] + [0, 1, 1, 1][:0] or True`
- After: 0 found by an AST scan of 60 test files. The scanner detects the original three lines: True.
- Replacements: the interval line now asserts both bounds are finite and `interval_low <= interval_high` (containment of the point score is not asserted, see below); the spec-hash line asserts one row per spec and unique hashes; the third line was deleted because the next line already asserts the real list.
- Observed rate at which the bootstrap interval contains the point score (real data, batter COMBINED_w70_30 ALL/ALL): 48 of 48 rows. A rate below 1 is reported here and does not fail a test, because a percentile band of a shrunk score need not bracket the point estimate.
- New guard: `tests/test_phase6_no_vacuous_assertions.py` fails on any `assert ... or True`, `assert True` or `assert <truthy constant>` in `tests/`.

## 3. Public descriptive directory (decision 6c)
- Public models walked recursively; forbidden-name hits: {'PublicPlayerRow': [], 'PublicPlayerListResponse': [], 'PublicPlayerDetailResponse': [], 'PublicDisabled': []}.
- Public directory routes clean: True.
- Fields present only on the internal directory model: ['applicable', 'conflict_flag', 'detail', 'eligible_scopes', 'gate_id', 'gate_results', 'official_ranking', 'passed', 'publication_status'].
- Public `/players` and `/players/{player_id}` return `PublicPlayerListResponse` / `PublicPlayerDetailResponse`: identity, nationality and status with their verification labels, group, squad role and match counts, plus `status`, `disclaimer`, `descriptive_only`. No `official_ranking`, `publication_status` or `gate_results`.
- Removed from the public shape: `eligible_scopes`, `conflict_flag`, the publication and gate fields, and the `min_pressure_matches` query filter (open decision OD-6; an API change visible to any caller that used them). All remain on `/internal/players` and `/internal/players/{player_id}` (admin token).
- Score-bearing routes were already split before this phase: the public twins of rankings, profile, compare, selection and dynamic rankings answer 403 `PUBLICATION_GATE_NOT_SATISFIED` without rows, and `/internal/...` needs the admin token. No route had to be moved.
- Route census (path, scope):
  - `/api/v1/admin/classification/overrides` GET: admin
  - `/api/v1/admin/classification/reload` POST: admin
  - `/api/v1/internal/compare` GET: internal
  - `/api/v1/internal/filters/catalog` GET: internal
  - `/api/v1/internal/players` GET: internal
  - `/api/v1/internal/players/{player_id}` GET: internal
  - `/api/v1/internal/players/{player_id}/profile` GET: internal
  - `/api/v1/internal/rankings/dynamic` POST: internal
  - `/api/v1/internal/rankings/dynamic/context-preview` POST: internal
  - `/api/v1/internal/rankings/dynamic/coverage` GET: internal
  - `/api/v1/internal/rankings/uncapped/{kind}` GET: internal
  - `/api/v1/internal/rankings/{role}` GET: internal
  - `/api/v1/internal/selection/custom` POST: internal
  - `/api/v1/internal/selection/presets/{preset_id}` POST: internal
  - `/api/v1/compare` GET: public
  - `/api/v1/dynamic-rankings` POST: public
  - `/api/v1/dynamic-rankings/context-preview` POST: public
  - `/api/v1/dynamic-rankings/coverage` GET: public
  - `/api/v1/health` GET: public
  - `/api/v1/meta/capabilities` GET: public
  - `/api/v1/meta/classification-coverage` GET: public
  - `/api/v1/meta/publication-gates` GET: public
  - `/api/v1/players` GET: public
  - `/api/v1/players/{player_id}` GET: public
  - `/api/v1/players/{player_id}/profile` GET: public
  - `/api/v1/rankings/uncapped/{kind}` GET: public
  - `/api/v1/rankings/{role}` GET: public
  - `/api/v1/selection/custom` POST: public
  - `/api/v1/selection/presets` GET: public
  - `/api/v1/selection/presets/{preset_id}` POST: public

## 4. Cache isolation (decision 6d)
- Key: SHA-256 of the JSON list `[spec hash, data version, model version, gate-config version, scope, lock version, gate-state hash]`. `scope` is `internal` or `public`; `lock version` is the SHA-256 of `config/phase5_methodology_lock_v1.json`; `gate-state hash` hashes the sorted ids of failing gates.
- Eight single-component variants of one key give 8 distinct keys.
- Entries are stored as deep copies and returned as deep copies (hit and miss). The paged payload is also copied.
- Mutating a real-data response (score, versions, item list) did not change the next response: True.
- Deep-copy cost on the real full rankings (six broad contexts) is within the 50 ms budget: True. The pickled-bytes fallback of open decision OD-10 is therefore not needed. The measured milliseconds are machine dependent and are written to `phase6_cleanup_timings.json` (excluded from the reproducibility hash).

## 5. Existing tests edited (reason for each)
- `tests/test_phase5_dynamic_ranking.py`: two vacuous asserts replaced; cache tests use the new cache_key / get_or_compute signature and assert copies (`is not`) instead of identity.
- `tests/test_pressure_state.py`: always-true line deleted (the next line asserts the real list).
- `tests/test_phase5_classification.py`: STATUS_VALUES now three real values; coverage has 9 combinations and a separate placeholder count; mapping test uses ACCEPTED_STORED_VALUES.
- `tests/test_phase4_api.py`: public /players has its own descriptive flags; coverage has 9 combinations (stored placeholder rows counted separately).
- `tests/test_phase5_gating.py`: public directory carries descriptive_only and no publication fields; route census counts the two new /internal/players routes (10 -> 12).
- `tests/test_phase5_strict_uncapped.py`: directory strict-uncapped checks: internal route keeps the full disabled body, public route returns the minimal PublicDisabled body.

## 6. Files
- Changed: `app/phase5/classification_v2.py`, `app/phase5/cache.py`, `app/phase5/filters.py`, `app/phase5/reports.py`, `app/phase4/uncapped.py`, `app/schemas/phase4.py`, `app/schemas/phase5.py`, `app/services/phase4_service.py`, `app/services/phase5_service.py`, `app/api/v1/routes.py`, `app/api/v1/routes_phase5.py`, `scripts/phase5_classification.py`, `scripts/phase5_gates.py`, `docs/frontend_backend_contracts.md`, `docs/backend_implementation_spec.md`.
- Added: `app/phase6/__init__.py`, `app/phase6/cleanup_scans.py`, `scripts/phase6_cleanup_checks.py`, `tests/test_phase6_classification_wording.py`, `tests/test_phase6_no_vacuous_assertions.py`, `tests/test_phase6_public_schema.py`, `tests/test_phase6_cache_isolation.py`, `tests/test_phase6_cleanup.py`.

## 7. Preservation
- Official data, Phase 4 reports and the TEST lock log: all preserved = True; Phase 5 lock log events = 0; TEST opened = False.
- 145 files hashed before Phase 6 (databases, source CSVs, Phase 4 and Phase 5 reports) compared now: 0 changed .

## 8. What this does not do
- No methodology, threshold, gate or ranking value changed. The 0.5 data-weight gate is untouched. The 42 late-dated T20I matches stay excluded. TEST stays unopened and is not pristine.
- Public rankings stay gated: every publication gate except the per-request pool gate still fails.
