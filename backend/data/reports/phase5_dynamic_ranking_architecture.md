# Phase 5 dynamic filter-driven ranking: architecture and measured behaviour

Status: EXPERIMENTAL_NOT_VALIDATED, INTERNAL_EXPERIMENTAL_ONLY. The primary pressure definition `any|q0.75` is PROVISIONAL. No official Top 10 exists, no model was trained for any filter, TEST outcomes were not read and Cricsheet is not used. Numbers below come from `scripts/phase5_context_engine.py`, `phase5_context_coverage.py`, `phase5_dynamic_demo.py` and `phase5_context_spotcheck.py` run on the real store (`phase5_context_engine_summary.json`, `phase5_context_coverage_summary.json`, `phase5_dynamic_examples.json`, `phase5_context_spotcheck.json`).

## 1. Three layers

| Layer | What it does | Where | When it runs |
|---|---|---|---|
| 1. Analytics | Delivery-level evidence of the carried definition as additive statistics (`n`, `s` residual sum, `s2`, `e` expected sum) per player, match, competition, role, phase and situation. Per atomic context: TRAIN-only variance fit, own working threshold, per-player raw/expected/residual/shrunk/n/matches/n_eff. | `app/phase5/context_stats.py`, `context_eligibility.py`, table builders in `scripts/phase5_context_engine.py` | once per model version (about 70 s) |
| 2. Classification and filters | nationality (`Indian`/`Overseas`/`Unknown`), international status (`VERIFIED_CAPPED`/`DERIVED_CAPPED`/`UNKNOWN`, strict uncapped disabled), role by actual participation, experience, format, phase, situation | `app/phase5/filters.py`, `classification_v2.py` | validated on every request |
| 3. Dynamic ranking | applies the filters to the eligible pool of the context, recomputes uncertainty for the filtered pool, orders and pages | `app/phase5/ranking_engine.py`, `cache.py`, `coverage.py`, service/routes | per request (cached) |

Filters are classification or context selections over one framework. There is no model per filter combination: `fit_cell` runs once per atomic context at build time (48 fits) and never on the request path (a test patches `shrink.fit_cell` and asserts zero calls while ranking, and asserts exactly 48 calls at build time). Indian, overseas, capped and the other classes are not separate pressure models, so their scores are comparable.

## 2. Stored analytics

| Table | Content |
|---|---|
| `p5_context_stats` | 10,106 rows (723 players), TRAIN and VALIDATION only (SQL join to `p4_match_period` excludes TEST before any frame exists; a check refuses any other period) |
| `p5_context_fit` | per atomic context: TRAIN players, `sigma2`, between-player variance moment, floored `tau2`, `k`, floor flag, TRAIN balls and residual sum |
| `p5_context_eligibility_rules` | per atomic context: derived threshold, label, window ratio, eligible players, marginal and median shrinkage weight, data-weight gate flag |
| `p5_context_scores` | 10,082 player-context rows (4,284 eligible): `n`, `matches`, `n_eff`, mean expected/residual/raw, target, shrinkage weight, `k`, `shrunk`, oriented `score`, eligibility, threshold |
| `p5_context_manifest` | model version, definition, baseline and shrinkage versions, restrictions, config SHA-256 values, classification hash, stats hash, code version |
| `p5_context_coverage` | 3,888 filter combinations with measured counts |
| `p5_filter_catalog` | enabled/disabled filter values with reasons |

Atomic contexts: competition (IPL, T20I) x role (batter, bowler) x phase (ALL, powerplay, middle, death) x situation (ALL, chase, first_innings) = 48. `phase` is the existing phase engine label of the delivery; `situation` is innings 2 (`chase`) or innings 1 (`first_innings`) of the carried definition's pressure rows. `phase=ALL` and `situation=ALL` are plain sums of the stored rows (tested: the phase and situation parts add up to the overall context exactly). The overall context reproduces the Phase 4 stored scores (`shrink_tau4`, PRE_TEST) with a maximum absolute difference of 2.8e-17 over all players, and opportunity counts are equal; the script exits 1 otherwise.

Wickets-remaining bands are not supported in v1 (they would fragment the contexts further). All-rounder is not a role: a player appears in the batter list and the bowler list independently, from actual participation.

## 3. Context estimation (the same estimator, context-specific parameters)

For each atomic context the Phase 4 code runs unchanged on a `ContextCell` built from the stored rows:

1. `shrink.fit_cell` on TRAIN rows of that context only gives `sigma2` and the between-player moment. VALIDATION rows never enter a fitted parameter (test: perturbing VALIDATION rows leaves every fit row identical while scores change; perturbing TRAIN rows changes the fit). Target = leave-one-player-out pooled TRAIN mean of the context.
2. Shrinkage `shrink_tau4` (the frozen Phase 4 choice), `k = sigma2 / tau2` with the documented floor (`tau2 >= 0.01 * sigma2`, then multiplied by 4). A context with fewer than `min_train_players_for_fit` (8, provisional) TRAIN players, or no variance, is `CONTEXT_NOT_ESTIMABLE` and has no scores; the parent cell's variance is never borrowed.
3. Eligibility: percentile candidate thresholds from the context's own TRAIN ball counts (`eligibility.candidate_thresholds`, `evaluate_cell`, `decide`, `analysis_rule`), applied as `n >= threshold * window_ratio` with the context's own window ratio. Nothing is copied from the overall cell (test: a death/chase context has a different threshold from the overall one and its eligibility is recomputed by hand).

Measured on the real data:

- All 48 contexts were estimable (40 to 439 TRAIN players each). The between-player moment is negative in all 48 contexts, so every context hits the variance floor and `k = 25.0` everywhere. This is the same finding as Phase 4 and the Chunk 3 investigation: the data do not identify a positive between-player spread under the Phase 4 noise model. Scores are therefore mostly the shrinkage target plus a small player-specific part; the engine reports this instead of hiding it (`fit_floor_hit` on every row).
- All 48 contexts have decision status `THRESHOLD_NOT_VALIDATED`; the working thresholds are 6 to 49 balls. The marginal shrinkage weight of the least-sampled eligible player is 0.04 to 0.12 and the median weight of eligible players is 0.05 to 0.29. None of the 48 contexts passes the Phase 4 marginal data-weight gate (0.5). Every ranking therefore carries `CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED`, and most carry `LOW_DATA_WEIGHT_CONTEXT` (median weight below 0.3).
- Caveat: 48 separate threshold derivations were run; the thresholds are data-derived working values, not validated, and a smaller context gives a noisier derivation.

## 4. Filter specification (`FilterSpec`, Pydantic v2, `extra="forbid"`)

| Field | Values | Default | Notes |
|---|---|---|---|
| `role` | `batter`, `bowler` | required | rankings are always separate |
| `format` | `IPL`, `T20I`, `COMBINED_w70_30` | `COMBINED_w70_30` | combined needs eligibility in both formats in the context; score = 0.7 IPL + 0.3 T20I |
| `nationality` | `Indian`, `Overseas`, `Unknown`, null | null | |
| `status` | `CAPPED_ANY`, `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `VERIFIED_UNCAPPED`, `UNKNOWN_STATUS`, null | null | `VERIFIED_UNCAPPED` returns `STRICT_UNCAPPED_DISABLED`; `UNKNOWN_STATUS` is a labelled group, never "uncapped" |
| `phase` | `ALL`, `powerplay`, `middle`, `death` | `ALL` | |
| `situation` | `ALL`, `chase`, `first_innings` | `ALL` | |
| `min_matches` | 0..200 | 0 | career matches in the format window (sum for combined) |
| `min_context_matches` | 0..200 | 0 | pressure matches in the context |
| `include_unknown_nationality`, `include_unknown_status` | bool | false | act only on a filtered axis |
| `limit`, `offset` | 1..50, 0..10000 | 10, 0 | |
| `sort`, `order` | `rank`,`score`,`name`,`matches`,`n`,`n_eff`; `asc`,`desc` | `rank` | display order only; ranks stay canonical |

There is no free text, SQL, path or column-name parameter. All selected filters are ANDed. The spec hash covers the ranking-defining fields only (canonical JSON with defaults explicit and sorted keys), so omitted and explicit-default specs hash equally and paging does not change the cache key.

## 5. Request flow and reason codes

1. `STRICT_UNCAPPED_DISABLED` (no rows) when `status=VERIFIED_UNCAPPED` and the capability flag is false.
2. Context lookup; `CONTEXT_NOT_ESTIMABLE` / `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT` give an empty result; combined adds `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS`.
3. Context eligibility: players with context data below the context's own threshold are excluded and counted (`INSUFFICIENT_SAMPLE_FOR_CONTEXT`). A player eligible overall can therefore be absent from a death-overs list (tested).
4. Classification filters with excluded counts: `CLASSIFICATION_UNKNOWN_EXCLUDED` (default), mismatch counts, `CLASS_EMPTY` for a valid class nobody has (for example `VERIFIED_CAPPED` today), `UNKNOWN_INCLUDED` flag when the toggle is on.
5. Experience filters (`BELOW_MIN_MATCHES`, `BELOW_MIN_CONTEXT_MATCHES`).
6. Pool rule: fewer than `min_internal_pool` (5, provisional) gives no rows (`POOL_TOO_SMALL`); 5 to 9 gives a shorter list (`FEWER_THAN_LIST_SIZE`). Nothing is padded or borrowed from a wider context.
7. Seeded match-cluster bootstrap (1,000 draws, seed 20260512) over the context's matches with `k` and the targets held fixed; the filtered pool gives the 95% score interval, rank interval and Top-10 inclusion probability for that pool. Draws come from one weight matrix over every stored match, so they are identical in the build and the API.
8. Canonical order: score descending, `player_id` ascending (tested with forced ties).

Every row carries raw, expected, residual, shrunk, score (oriented: bowler score is negated runs conceded so higher is better), interval, rank interval, Top-10 inclusion probability, `n`, matches, `n_eff`, shrinkage weight, `fit_floor_hit`, eligibility status and threshold, restrictions applied, nationality and status with their verification labels, `classification_match`, per-format components, plus the response-level filter echo, spec hash, reasons, stage and exclusion counts, definition/baseline/shrinkage/model/data versions and config SHA-256 values.

## 6. Endpoints (all under `/api/v1`)

| Route | Access | Purpose |
|---|---|---|
| `GET /internal/filters/catalog` | admin token | valid values, enabled/disabled with reasons, capability flag, cache counters |
| `POST /internal/rankings/dynamic` | admin token | ranking with pagination and explanations |
| `POST /internal/rankings/dynamic/context-preview` | admin token | qualifying players and exclusion reasons before ranking; no rows |
| `GET /internal/rankings/dynamic/coverage` | admin token | paginated coverage table with whitelisted filters |
| `POST /dynamic-rankings`, `POST /dynamic-rankings/context-preview`, `GET /dynamic-rankings/coverage` | public | 403 `PUBLICATION_GATE_NOT_SATISFIED` with the failing gates and no rows while any gate fails |

Missing or wrong token: 401; no token configured: 503. Invalid body: 422 `VALIDATION_ERROR` (unknown field, enum, range). Missing context tables: 503 `STORE_UNAVAILABLE`. Every response has `publication_status` and `gate_results`; the strict-uncapped body is the same `STRICT_UNCAPPED_DISABLED` structure as the earlier uncapped routes and presets.

## 7. Cache and versioning

In-memory LRU (256 entries) of full unsliced rankings keyed by SHA-256 of spec hash, data version, model version and gate-config version. Data version = hash of the stored context tables, the context-rules config, the model version and the classification table in force. Any version change drops every entry; a cached value equals a recomputed one (tested). Gates are not cached. Hit/miss/eviction counters are on the catalog endpoint.

## 8. Context coverage (measured)

3,888 valid combinations (format 3 x role 2 x nationality 4 x status 6 x phase 4 x situation 3, with the unknown toggles varied only where they can change the result). 432 are `VERIFIED_UNCAPPED` and listed as DISABLED. Of the other 3,456, 1,889 reach the internal minimum pool of 5 and 1,558 reach the public-size rule of 10; 1,567 have an empty pool and 331 are shorter than ten. Reaching the pool-size rule is one of five gates; the others still fail, so none is publishable.

| format | role | combinations | internal min | public-size min | empty |
|---|---|---|---|---|---|
| COMBINED_w70_30 | batter | 576 | 220 | 135 | 286 |
| COMBINED_w70_30 | bowler | 576 | 235 | 195 | 286 |
| IPL | batter | 576 | 443 | 383 | 104 |
| IPL | bowler | 576 | 421 | 365 | 100 |
| T20I | batter | 576 | 280 | 220 | 276 |
| T20I | bowler | 576 | 290 | 260 | 276 |

Example sets (from `phase5_dynamic_examples.json`; all INTERNAL_EXPERIMENTAL_ONLY): All batters: 48 players; All bowlers: 39; Overseas + capped batters: 33; Indian batters: 15; death-over bowlers: 36; chase batters: 42; Indian + DERIVED_CAPPED + death + chase batters: 7 (shorter than ten, not empty); IPL powerplay chase Indian DERIVED_CAPPED bowlers: 6; Indian + Uncapped and Uncapped + Bowler: `STRICT_UNCAPPED_DISABLED`, no rows. The expectation that "death + chase + Indian + DERIVED_CAPPED" is empty did not hold under the working-pool thresholds: the contexts' own thresholds are low (6 to 49 balls), so a small pool survives. It is reported with `CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED` and `LOW_DATA_WEIGHT_CONTEXT`; the low reliability, not an empty list, is what the data show.

## 9. Verification highlights

- Overall context equals the Phase 4 stored scores (max abs diff 2.8e-17); phases and situations partition the stored rows exactly.
- Independent spot check (`phase5_context_spotcheck.json`): Rinku Singh in IPL batter death chase: 103 pressure balls, 8 matches, 260 actual runs from the raw state table equal the stored rows and the engine response; residual sum 100.8652 equals the study's second path. Abrar Ahmed in T20I bowler middle chase: 51 balls, 6 matches, 34 runs conceded, residual sum -29.6278.
- Hand-computed context `n`, `matches`, Kish `n_eff`, mean residual, threshold candidates, window ratio, shrunk values (leave-one-out target) and a bootstrap interval from an independent loop equal the engine values.

## 10. Limits and open decisions

- Every context hits the variance floor; scores are mostly shrinkage targets and rankings are fragile (Chunk 3 stability: expected Top-10 overlap 4.9 to 6.2 of 10 for the overall cells). Filters cannot repair that and the engine never claims otherwise.
- Pool minimums (5 internal, 10 public), `min_train_players_for_fit` (8) and the `0.3` low-weight warning are provisional config values without a data basis.
- Context bootstrap holds `k` and targets fixed: intervals reflect sampling of matches, not estimation error of the variance.
- The coverage table is a snapshot; it is served only while the classification hash in the manifest matches the table in force, otherwise it is recomputed (`coverage_source` says which).
- A refit on TRAIN+VALIDATION (Chunk 5) would rebuild these tables under a separate model version; the API serves `p5_context_v1_train` only.
- Future public release: only after `data_weight_gate_passed`, `methodology_validated` (human edit with evidence), `date_verification`, strict classification (when a verified filter is used) and the public minimum pool all pass. No code path sets them; the same handlers then return rows with `PUBLIC_ALLOWED`.
