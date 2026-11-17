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
