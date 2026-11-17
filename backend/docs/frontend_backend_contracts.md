# Frontend and backend contracts (Phase 4, experimental)

Status: `EXPERIMENTAL_NOT_VALIDATED`. Every response below is exploratory. There is no official ranking and no validated pressure measure. A frontend must not present any of these numbers as official or final.

Base path: `/api/v1`. All bodies are JSON. The OpenAPI document is served at `/openapi.json` when the app runs (`uvicorn app.main:app`).

## 1. Status and disclaimer fields

Every experimental response (everything except `/health` and the admin endpoints) carries:

| field | value |
|---|---|
| `status` | always `"EXPERIMENTAL_NOT_VALIDATED"` |
| `official_ranking` | always `false` |
| `disclaimer` | fixed text; a frontend must display it near any ranking, score or selection |

Every result row (`ResultRow`, `PlayerRow`) repeats `status` and `official_ranking`. Any request with `official=true` or `publish=true` (query) or `"official": true` (body) is refused with 403 `OFFICIAL_RANKING_NOT_AUTHORIZED`.

## 2. Error model

All errors use one shape: `{"error": {"code": str, "message": str, "details": any|null}}`.

| HTTP | code | meaning |
|---|---|---|
| 401 | `ADMIN_AUTH_FAILED` | admin token missing or wrong |
| 403 | `OFFICIAL_RANKING_NOT_AUTHORIZED` | official publication requested |
| 404 | `NOT_FOUND` | unknown player, preset or route |
| 422 | `VALIDATION_ERROR` | bad query/body value (`details` lists `loc`, `message`, `type`) |
| 422 | `CONFLICTING_FILTERS` | for example `classification=all_uncapped` with `uncapped_mode=exclude_uncapped` |
| 422 | `INVALID_SELECTION_REQUEST` | invalid bounds, repeated ids, total too large for role constraints |
| 422 | `INVALID_CLASSIFICATION_CONFIG` | override file failed validation (nothing is applied) |
| 503 | `ADMIN_DISABLED` | `SUPERR_ADMIN_TOKEN` is not set |
| 503 | `STORE_UNAVAILABLE` | analytical store or a required table is missing |

## 3. Pagination, sorting and filters

- Lists return `page: {items, total, limit, offset}`. `limit` is 1 to 200 (default 50). `offset` is 0 or more.
- `sort_by` is an enum per endpoint (rankings: `rank, score, name, matches, pressure_opportunities, distinct_matches`; players: `player_id, name, matches, distinct_matches`). `order` is `asc` or `desc`. Ties break by `player_id` ascending. Unknown values give 422.
- No endpoint accepts SQL, a file path or a table name. `q` (player name search) is a literal substring of at most 64 characters.
- Classification filters (players and rankings):
  - `classification`: `indian_uncapped`, `overseas_uncapped`, `all_uncapped`, `capped`, `unknown_international_status`.
  - `uncapped_mode`: `include_uncapped` (no change) or `exclude_uncapped` (removes rows whose status is Uncapped; Unknown-status rows stay).
  - `min_matches`: matches played in the format (combined: both formats), from the descriptive stats table.
  - `min_pressure_matches`: distinct matches in the pressure sample of the score row.
  - `basis`: `INCLUDE_DERIVED_CAPPED` (default) or `VERIFIED_ONLY` (derived values are treated as Unknown).
  - `*_uncapped` filters return only players whose Uncapped status is `VERIFIED_FROM_SOURCE`.
- `format`: `IPL` (default), `T20I`, `COMBINED_w70_30` (provisional 70:30 weighting, only players eligible in both formats).

## 4. Classification semantics

> Phase 5 supersedes the `Capped`/`Uncapped`/`Unknown` labels below. See section 8.1 for the explicit migration mapping to the three real values `VERIFIED_CAPPED`, `DERIVED_CAPPED` and `UNKNOWN` (plus the disabled placeholder `VERIFIED_UNCAPPED`, see section 10).

Two independent fields per player. No field is ever inferred from the other.

| field | values | verification values |
|---|---|---|
| `nationality` | `Indian`, `Overseas`, `Unknown` | `VERIFIED_FROM_SOURCE`, `DERIVED`, `UNVERIFIED` |
| `international_status` | `Capped`, `Uncapped`, `Unknown` | `VERIFIED_FROM_SOURCE`, `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES`, `UNVERIFIED` |

- `Capped` with `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES` means the player appeared in a T20I in the data on or before the as-of date. It is derived evidence, not a verified cap list.
- `Uncapped` exists only with `VERIFIED_FROM_SOURCE` (manual override or source file). A player never seen in the data is `Unknown`, never `Uncapped`.
- `DERIVED` nationality comes from the IPL squad file (unique name plus id-keyed team corroboration) or from T20I national-team appearances. Franchise teams never imply nationality.
- Composition groups: `IN_CAPPED`, `IN_UNCAPPED`, `OS_CAPPED`, `OS_UNCAPPED`, `UNKNOWN` (nationality or status Unknown).

## 5. Endpoints

### Players
- `GET /players` : `PlayerListResponse`. Query: filters, `basis`, `q`, `sort_by`, `order`, `limit`, `offset`.
- `GET /players/{player_id}` : `PlayerDetailResponse` (classification sources, unknown reasons, first T20I date, as-of date, version).
- `GET /players/{player_id}/profile?format=&basis=` : `ProfileResponse`. One `SideProfile` per side (batter, bowler) and format with data:
  - `sample_size` (unit, value, minimum for axes), `descriptive` totals (integers),
  - `pressure`: `label` `OK` with score, interval, rank, pool size, opportunities, distinct matches, effective sample size; or `label` `INSUFFICIENT_DATA` with `reason`,
  - `radar.axes[]`: `axis, label, formula, unit, higher_is_better, value, reference_overall_n, reference_uncapped_n, percentile_overall, percentile_uncapped, label_overall, label_uncapped, reason_overall, reason_uncapped`. Percentiles are 0 to 100 within the reference population (the player is included). Reference: all players of the format with at least 60 balls faced or bowled (pressure axis: all eligible experimental players). The uncapped percentile needs at least 5 verified-uncapped players, otherwise `INSUFFICIENT_DATA` with the reason,
  - `strengths[]`: axis, percentile and an evidence sentence built from the stored value (at least 75th percentile and a reference of at least 10),
  - `ranking_status`: rank and pool size, `status`, `official_ranking=false`.
- `GET /compare?player_ids=1,2,3&format=&basis=` : up to five distinct ids; items are profiles for that format.

### Rankings
- `GET /rankings/{role}` (`batter` or `bowler`): `RankingResponse`. Only eligible players unless `include_ineligible=true` (then `rank` is null). `pool_size` is the eligible count. The list is never padded to ten. Score is higher-is-better (bowler scores are the negated shrunk runs-conceded residual).
- `GET /rankings/uncapped/{kind}` with `kind` in `indian_batters, indian_bowlers, overseas_batters, overseas_bowlers, overall`: `UncappedRankingResponse`. A filtered view of the same ranking (same scores, ranks and thresholds). `rank` is the rank in the main pool, `view_rank` the position in this list. `include_unverified_list=true` adds a separate `unverified_candidates` list (matching nationality, Unknown status), clearly labelled not verified. `overall` uses each player's better side.

### Selection
- `POST /selection/custom` (`SelectionRequestModel`): `total` (1 to 50, default 10), `groups` (per group `exact` or `min`/`max`), optional `roles` (squad roles `Batter, Bowler, All Rounder, Wicket Keeper`; total at most 12), `allow_fewer`, `format`, `basis`, `side`, `uncapped_mode`, `min_matches`, `min_pressure_matches`. Response `SelectionResponse`:
  - `selection_status`: `OK`, `PARTIAL` (fewer than requested, `allow_fewer` set), `INFEASIBLE` (nobody returned, `explanations` name the failing constraint with `required` and `available`),
  - `selected[]` rows (`view_rank` is the position in the selection), `available_by_group`, `available_by_role`, `excluded_unknown_role`, `pool_size`.
  - The UNKNOWN group is excluded unless the request names it.
- `GET /selection/presets` : templates (parameters only). `POST /selection/presets/{preset_id}` with optional `{format, basis, min_matches}`: same response. Presets: `best_indian_uncapped_xi`, `top_indian_uncapped_batters`, `top_indian_uncapped_bowlers`, `best_overseas_uncapped_players`, `emerging_domestic_talent`, `mixed_capped_and_uncapped_xi`. A preset whose verified pool is too small answers `selection_status = POOL_TOO_SMALL`, an empty list and a message. No constraint is relaxed.

### Meta and admin
- `GET /meta/classification-coverage` : counts per nationality and status combination (all nine), verification counts, unknown reasons, unresolved squad rows.
- Admin (header `X-Admin-Token`, compared in constant time with `SUPERR_ADMIN_TOKEN`): `GET /admin/classification/overrides`, `POST /admin/classification/reload` (re-applies the validated override file to the stored base classification).
- `GET /health` : liveness.

## 6. Result row (requirement fields)

`player_id, name, nationality, nationality_verification, international_status, international_status_verification, side, format, group, squad_role, eligibility, score, standardised_score, rank, view_rank, pressure_opportunities, distinct_matches, effective_sample_size, interval_low, interval_high, top10_inclusion_prob, rank_lo, rank_hi, matches, restrictions_applied, status, official_ranking`.

`interval_*` is the bootstrap interval of the score (orientation matches `score`). `top10_inclusion_prob`, `rank_lo`, `rank_hi` are null where no bootstrap distribution exists (combined format).

## 7. How a frontend must display values

- `Unknown` nationality or status: show the word "Unknown" with a neutral style, never a default such as "Uncapped" or "Overseas". Show the verification label (for example "derived from T20I appearances") as a tooltip or badge.
- `INSUFFICIENT_DATA`: show the label and the `reason` text; never draw a value, a zero or an empty radar spoke as if it were measured.
- `EXPERIMENTAL_NOT_VALIDATED`: show a persistent experimental banner on every ranking, selection, profile and comparison view, with the `disclaimer` text. Do not use the words "official", "best" or "final" for experimental results.
- Fewer than ten rows is a valid result. Display the real count and the `note` or `message`; do not pad or auto-relax filters.
- `POOL_TOO_SMALL` and `INFEASIBLE`: display the explanations (required versus available) and offer the user a way to change the request.
- Intervals and `top10_inclusion_prob` should be shown next to scores; ranks within the same interval are not distinguishable.
- Derived Capped (`DERIVED_FROM_OFFICIAL_T20I_APPEARANCES`) must be visually distinct from a verified cap.


## 8. Phase 5 changes: classification enum, strict-uncapped, publication gating (INTERNAL / EXPERIMENTAL)

This section supersedes sections 1, 4 and 5 where they differ. Everything is still `EXPERIMENTAL_NOT_VALIDATED`.

### 8.1 International status enum and explicit migration

`international_status` now has three real, **separate** values (`VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`) and one disabled placeholder (`VERIFIED_UNCAPPED`, not an established status; section 10.1). The Phase 4 values `Capped`, `Uncapped`, `Unknown` are migrated by this mapping (no other combination is accepted; an unmapped combination is a fatal `ClassificationMigrationError`, never a silent relabel):

| Phase 4 `international_status` | Phase 4 verification label | Phase 5 `international_status` |
|---|---|---|
| Capped | DERIVED_FROM_OFFICIAL_T20I_APPEARANCES | `DERIVED_CAPPED` |
| Capped | VERIFIED_FROM_SOURCE | `VERIFIED_CAPPED` |
| Uncapped | VERIFIED_FROM_SOURCE | `VERIFIED_UNCAPPED` |
| Unknown | UNVERIFIED | `UNKNOWN` |

- `VERIFIED_CAPPED` exists only through an authoritative source or a validated override row. `VERIFIED_UNCAPPED` is the disabled placeholder: it could only ever be stored through the same route, no such source exists, and nothing treats it as an established status.
- `DERIVED_CAPPED` is data-proven: the player appeared for a national team in an official T20I in the data on or before the as-of date (2025-12-31). Its evidence label stays `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES`.
- `UNKNOWN` means not proven capped. It is displayed only as the group `UNKNOWN_STATUS` (`group_label`) with the banner `NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED`. It is never uncapped.
- Capped status is never inferred from names, domestic experience or IPL participation.
- Real-data counts: VERIFIED_CAPPED 0, DERIVED_CAPPED 655, UNKNOWN 562 (1,217 players; the placeholder count is 0); see `data/reports/phase5_classification_migration.md`.
- Group ids are unchanged (`IN_CAPPED`, `IN_UNCAPPED`, `OS_CAPPED`, `OS_UNCAPPED`, `UNKNOWN`); `VERIFIED_CAPPED` and `DERIVED_CAPPED` both map to `*_CAPPED`.
- Filter value `capped` is replaced by `capped_any`, `capped_verified`, `capped_derived`. `unknown_international_status` selects `UNKNOWN`.
- Coverage returns 9 combinations (3 nationalities x 3 real statuses); stored placeholder rows, if any, are counted separately in `disabled_placeholder_counts`. Player rows gain `group_label`; player detail gains `derived_evidence`.
- Override file (`config/classification_overrides_v1.csv`, header only): columns `player_id,field,value,source,verified_by,verified_date`. `international_status` override values are `VERIFIED_CAPPED` or the placeholder `VERIFIED_UNCAPPED` (the override mechanism is unchanged); the legacy `Capped`/`Uncapped` are rejected with the mapping named. Error codes: `UNKNOWN_PLAYER_ID`, `INVALID_FIELD`, `INVALID_VALUE`, `LEGACY_STATUS_VALUE`, `MISSING_SOURCE` (blank or placeholder), `MISSING_VERIFIED_BY`, `MISSING_OR_BAD_VERIFIED_DATE` (ISO, not in the future), `DUPLICATE_OVERRIDE`, `CONTRADICTS_DERIVED_EVIDENCE` (`VERIFIED_UNCAPPED` for a `DERIVED_CAPPED` player). All row errors are returned together (HTTP 422 `INVALID_CLASSIFICATION_CONFIG` on reload; the previous table stays).
- The API reads `p5_player_classification` only. There is no fallback to the legacy `p4_player_classification`, which stays unchanged.

### 8.2 `strict_uncapped_enabled` and `STRICT_UNCAPPED_DISABLED`

`GET /api/v1/meta/capabilities` reports `strict_uncapped_enabled`. The flag is computed, never stored or hand-set. It is true only if (a) `config/classification_source_manifest_v1.json` declares a source with `authoritative: true` and `id_keyed: true`, (b) at least one validated `VERIFIED_*` row exists, and (c) the share of the scored pool with a `VERIFIED_*` status is at least `min_verified_coverage` (`config/phase5_classification_v2.json`, provisional 0.95). A missing or malformed manifest gives false. Today: false (`NO_AUTHORITATIVE_SOURCE`, `NO_VERIFIED_ROWS`, `COVERAGE_BELOW_MINIMUM`).

While false, these return HTTP 200 and this body, with no rows and no approximation: every `/rankings/uncapped/{kind}`, all six presets, a custom selection with `IN_UNCAPPED` or `OS_UNCAPPED` `min>0` or `exact>0`, `uncapped_mode=include_uncapped`, and the classification filters `indian_uncapped`, `overseas_uncapped`, `all_uncapped` on `/players` and `/rankings/{role}`. `exclude_uncapped`, `max=0` and `exact=0` stay allowed.

```json
{"result_status": "STRICT_UNCAPPED_DISABLED", "reason": "...", "source_needed": "...",
 "capability": {"enabled": false, "reasons": ["NO_AUTHORITATIVE_SOURCE", "NO_VERIFIED_ROWS", "COVERAGE_BELOW_MINIMUM"],
                "verified_coverage": 0.0, "min_verified_coverage": 0.95},
 "request_kind": "preset", "rows": [], "publication_status": "INTERNAL_EXPERIMENTAL_ONLY",
 "gate_results": [], "failing_gates": ["strict_classification_available"]}
```

`GET /selection/presets` lists the templates (no player rows) with `available` and `unavailable_reason` (`STRICT_UNCAPPED_DISABLED`).

### 8.3 Publication status and gates

Every response carries `publication_status` (`INTERNAL_EXPERIMENTAL_ONLY` or `PUBLIC_ALLOWED`) and `gate_results` (`gate_id`, `passed`, `applicable`, `detail`). `PUBLIC_ALLOWED` only if every applicable gate passes. A missing or malformed gate input fails its gate (`INPUT_UNAVAILABLE`).

| gate_id | passes when |
|---|---|
| `data_weight_gate_passed` | none of the four format-role cells is `THRESHOLD_NOT_VALIDATED` in `phase4_frozen_choices.json` |
| `methodology_validated` | `config/phase5_methodology_status_v1.json` has `validated: true` and non-blank `validated_by`, `validated_date`, `evidence_path` (only a human edit can set it) |
| `strict_classification_available` | applicable only to uncapped/verified requests; passes when `strict_uncapped_enabled` |
| `min_eligible_pool` | rows after all filters >= `min_public_pool` (`config/phase5_gates_v1.json`, provisional 10); per request |
| `date_verification` | the date-verification summary reports its gate as passed (fails with `NOT_RUN` until that summary exists) |

Today every public-relevant gate except the per-request pool fails, so everything is `INTERNAL_EXPERIMENTAL_ONLY`.

### 8.4 Routes

- Public rows-returning paths (`/rankings/*`, `/selection/custom`, `/selection/presets/{id}`, `/compare`, `/players/{id}/profile`) answer HTTP 403, error code `PUBLICATION_GATE_NOT_SATISFIED`, `details = {publication_status, gate_results}` and no rows, unless every gate passes.
- Internal paths `/api/v1/internal/...` mirror those routes, require the admin token (`X-Admin-Token`; 401 wrong or missing, 503 none configured) and always return rows labelled with the status and gate results.
- Public descriptive paths: `/selection/presets`, `/meta/classification-coverage`, `/meta/capabilities`, `/meta/publication-gates` carry the same fields. `/players` and `/players/{id}` are descriptive-only and use their own flags (section 10.2).
- The single enforcement point is `app.phase5.gating.apply_gates`, called from the service (`precheck` before rows are computed, `_gate` after). A test enumerates all routes and fails if a route's response model lacks the two fields.
- How a future public release works: when a human sets `validated: true` with evidence, the data-weight gate passes on validated thresholds, the date summary passes and (for strict requests) the capability is enabled, the same public handlers return rows with `PUBLIC_ALLOWED`. No code change is needed.
## 9. Phase 5 dynamic filter-driven ranking (INTERNAL / EXPERIMENTAL, Chunk 4)

Everything here is `EXPERIMENTAL_NOT_VALIDATED` and `INTERNAL_EXPERIMENTAL_ONLY`. The pressure definition `any|q0.75` is PROVISIONAL (`versions.definition_label`). Architecture and measured counts: `data/reports/phase5_dynamic_ranking_architecture.md`.

### 9.1 Workflow
1. `GET /api/v1/internal/filters/catalog` lists every filter value with `enabled` and `reason`. Disabled: `VERIFIED_UNCAPPED` (until strict uncapped is enabled), wickets-remaining bands, an all-rounder role.
2. `POST /api/v1/internal/rankings/dynamic/context-preview` with a `FilterSpec` returns how many players qualify and why others do not, before ranking (no rows).
3. `POST /api/v1/internal/rankings/dynamic` returns the ranking (pagination, full per-row explanation).
4. `GET /api/v1/internal/rankings/dynamic/coverage` returns the precomputed table of qualifying counts for every valid combination, with the minimum pool rule.
Public twins (`POST /api/v1/dynamic-rankings`, `.../context-preview`, `GET .../coverage`) answer 403 `PUBLICATION_GATE_NOT_SATISFIED` with the failing gates and no rows until every gate passes.

### 9.2 Filter spec schema (request body, strict: unknown fields are 422)
```json
{"role": "batter | bowler (required)",
 "format": "IPL | T20I | COMBINED_w70_30 (default COMBINED_w70_30)",
 "nationality": "Indian | Overseas | Unknown | null",
 "status": "CAPPED_ANY | VERIFIED_CAPPED | DERIVED_CAPPED | UNKNOWN_STATUS | null (VERIFIED_UNCAPPED is a disabled placeholder: accepted, always answered with STRICT_UNCAPPED_DISABLED)",
 "phase": "ALL | powerplay | middle | death", "situation": "ALL | chase | first_innings",
 "min_matches": 0, "min_context_matches": 0,
 "include_unknown_nationality": false, "include_unknown_status": false,
 "limit": 10, "offset": 0, "sort": "rank | score | name | matches | n | n_eff", "order": "asc | desc"}
```
All selected filters are ANDed. `limit` 1..50, `offset` 0..10000, `min_*` 0..200. Unknown handling is explicit: with a nationality or capped-status filter set, unknown players are excluded by default and counted (`excluded_counts`, reason `CLASSIFICATION_UNKNOWN_EXCLUDED`); `include_*` adds them flagged `classification_match = UNKNOWN_INCLUDED`. Unknown values on an unfiltered axis never exclude anyone. `status=UNKNOWN_STATUS` is the labelled group of players not proven capped; it is never called uncapped.

### 9.3 Response
`result_status` is `RANKED` (10 or more), `FEWER_THAN_LIST_SIZE` (5 to 9 rows), `EMPTY` (reasons explain) or `STRICT_UNCAPPED_DISABLED` (same body as section 8.2 plus `filter_echo`). Fields: `spec_hash`, `filter_echo`, `pool_size`, `reasons[{code,count,detail}]`, `stage_counts`, `excluded_counts`, `context_status` (per format), `context_data_weight` (Phase 4 marginal data-weight gate per context), `versions` (definition id and label, baseline, shrinkage, `model_version`, `data_version`, `config_hashes`, `interval_level`, `n_boot`, `seed`), `cache_hit`, `low_data_weight`, `page{items,total,limit,offset}`, `publication_status`, `gate_results`. Each item: `rank, player_id, name, score, raw, expected, residual, shrunk, interval_low, interval_high, rank_lo, rank_median, rank_hi, top10_inclusion_prob, n, matches, n_eff, shrinkage_weight, fit_floor_hit, eligibility_status, eligibility_label, eligibility_thresholds, components{format}, restrictions_applied, nationality(+verification), international_status(+verification), classification_match, career_matches`. Bowler `score` is the negated runs-conceded residual (higher is better); `residual` and `shrunk` keep their natural sign for bowlers' runs (`shrunk = -score`). `rank` is canonical (score descending, `player_id` ascending) and does not change with `sort`.

### 9.4 Reason codes
`INSUFFICIENT_SAMPLE_FOR_CONTEXT`, `POOL_TOO_SMALL` (below `min_internal_pool` 5, no rows), `FEWER_THAN_LIST_SIZE`, `STRICT_UNCAPPED_DISABLED`, `CLASSIFICATION_UNKNOWN_EXCLUDED`, `CLASS_EMPTY`, `CONTEXT_NOT_ESTIMABLE`, `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT`, `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS`, `BELOW_MIN_MATCHES`, `BELOW_MIN_CONTEXT_MATCHES`, `CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED`, `LOW_DATA_WEIGHT_CONTEXT`. A list is never padded and slots are never filled from a wider context.

### 9.5 Error and status model
401 `ADMIN_AUTH_FAILED`, 503 `ADMIN_DISABLED` (internal routes); 422 `VALIDATION_ERROR` (unknown field, bad enum or range, SQL/path-like extra keys); 403 `PUBLICATION_GATE_NOT_SATISFIED` (public twins; `details` holds the gates, no rows); 403 `OFFICIAL_RANKING_NOT_AUTHORIZED` (`official=true`); 503 `STORE_UNAVAILABLE` (context tables missing: run `scripts/phase5_context_engine.py`). Empty or short pools are normal 200 responses with reasons.

### 9.6 Versioning and caching
`model_version` `p5_context_v1_train` (baseline, thresholds, variances fitted on TRAIN only; VALIDATION rows receive scores). `data_version` hashes the stored context tables, the context-rules config, the model version and the classification in force. The server caches full rankings; the key is described in section 10.3. Any data, model or lock version change invalidates all entries; paging and display order are not part of the key; gates are recomputed on every read. A frontend can rely on `spec_hash` and `versions.data_version` to detect stale pages.

### 9.7 Classification enum changes touching this surface
`status` filter values use the Phase 5 enum (section 8.1): `CAPPED_ANY` = `VERIFIED_CAPPED` or `DERIVED_CAPPED`; `UNKNOWN_STATUS` = `UNKNOWN`. The Phase 4 value `Capped` is not accepted anywhere in the dynamic API.

### 9.8 Future public release
Public handlers return rows with `PUBLIC_ALLOWED` only when `data_weight_gate_passed`, `methodology_validated`, `date_verification`, `strict_classification_available` (for verified-status requests) and `min_eligible_pool` (10, provisional) all pass. No code path sets them; the methodology flag changes only by a human edit with evidence. Today none passes, so every dynamic output is `INTERNAL_EXPERIMENTAL_ONLY`.

## 10. Phase 6 cleanup: classification wording, descriptive vs gated routes, cache scoping (INTERNAL / EXPERIMENTAL)

This section supersedes sections 4, 5, 8 and 9 where they differ. Everything is still `EXPERIMENTAL_NOT_VALIDATED`. Nothing here publishes a ranking or changes the methodology.

### 10.1 Classification: three real values and one disabled placeholder

- `international_status` has exactly three real values: `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`. `ClassificationStatus` in the schema, `classification_values` in `GET /meta/capabilities` and the status counts list these three.
- `VERIFIED_UNCAPPED` is a **disabled placeholder**, not an established status. It is returned separately as `disabled_placeholder_values: ["VERIFIED_UNCAPPED"]` in `GET /meta/capabilities`. Strict uncapped selection stays disabled; a filter on it still answers `STRICT_UNCAPPED_DISABLED`. The validated override mechanism is unchanged. Verified status is never inferred.
- Coverage (`/meta/classification-coverage`) returns 9 combinations (3 nationalities x 3 real statuses). A stored placeholder value, if one is ever applied by a validated override, is counted in `disabled_placeholder_counts`. The real data has none.

### 10.2 Descriptive `/players` versus gated outputs

| route | access | content |
|---|---|---|
| `GET /players`, `GET /players/{player_id}` | public | descriptive directory only |
| `GET /internal/players`, `GET /internal/players/{player_id}` | admin token | the previous directory shape (adds `eligible_scopes`, `conflict_flag`, `publication_status`, `gate_results`) |
| rankings, profile, compare, selection, dynamic rankings | public twin answers 403 `PUBLICATION_GATE_NOT_SATISFIED` without rows; `/internal/...` needs the token | scores, ranks, intervals |

Public directory response (`PublicPlayerListResponse`, `PublicPlayerDetailResponse`):

- Flags: `status` (`EXPERIMENTAL_NOT_VALIDATED`), `disclaimer`, `descriptive_only` (always `true`). There is no `official_ranking`, `publication_status` or `gate_results`.
- Row fields: `player_id, name, nationality, nationality_verification, international_status, international_status_verification, group, group_label, squad_role, matches, distinct_matches`.
- Detail adds the classification provenance fields (`nationality_source`, `nationality_unknown_reason`, `international_status_source`, `international_status_unknown_reason`, `derived_evidence`, `first_t20i_date`, `t20i_appearances_to_as_of`, `as_of_date`, `classification_version`).
- Removed from the public shape: `eligible_scopes` (implies which formats a player could be ranked in), `conflict_flag`, the publication and gate fields, and the `min_pressure_matches` query filter (it filters on an experimental count). They stay on `/internal/players`.
- A strict-uncapped directory request (`classification=all_uncapped` etc.) answers `PublicDisabled`: `status, disclaimer, descriptive_only, result_status = STRICT_UNCAPPED_DISABLED, reason, source_needed, request_kind`. No rows.
- Tests walk the response models and the JSON for any key matching `score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict`.
- A frontend must not rank, sort by merit or imply eligibility from the public directory.

### 10.3 Ranking-cache key and isolation

- Key = SHA-256 of the JSON list `[spec hash, data version, model version, gate-config version, scope, lock version, gate-state hash]`. JSON encoding removes delimiter collisions.
- `scope` is `internal` or `public`; the two never share an entry. `lock version` is the SHA-256 of `config/phase5_methodology_lock_v1.json`. `gate-state hash` is the SHA-256 of the sorted ids of the gates failing at request time (request-independent gates only; the per-request pool gate is evaluated after the cache).
- A change of data, model or lock version drops all entries. Paging and display order are not part of the key. Gates are still recomputed on every read.
- Entries are stored as deep copies and returned as deep copies on hit and on miss. The paged payload is also copied, so mutating a response (rows, nested dicts, `versions`) never changes a later response.
- `cache_hit` in the response says whether the full ranking came from the cache. It is not a stability or validity statement.
