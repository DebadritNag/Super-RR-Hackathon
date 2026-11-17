# Backend implementation specification (Phase 4 additions)

Status: experimental. This document covers the classification pipeline, the composition optimiser, the serving tables and the API. The pressure scoring and temporal validation design is in `docs/pressure_framework_v1.md` and the Phase 4 reports.

## 1. Architecture

```
official superr.duckdb (read-only) ----+
ipl squad.csv (read-only) -------------+--> scripts/phase4_classification.py
exploratory.duckdb (p4_* tables) ------+        app/phase4/classification.py, serving.py
                                                writes p4_player_classification(_base), p4_classification_*,
                                                p4_player_stats  (exploratory store only)
exploratory.duckdb (read-only) --> app/repositories/phase4_repo.py --> app/phase4/views.py, profiles.py,
                                   uncapped.py, selection.py --> app/services/phase4_service.py
                                   --> app/api/v1/routes.py --> app/main.py (FastAPI, /api/v1)
```

- Layers: repository (loads tables), views/profiles/uncapped/selection (pure pandas logic), service (shapes responses), API (validation, errors, gating), schemas (`app/schemas/phase4.py`, Pydantic v2).
- The official database and the source CSVs are never written. Only `p4_` tables are written, and only to the exploratory store (`write_p4_table` refuses anything else).
- The API loads the tables into memory read-only. Queries are fixed text; user input never reaches SQL or the filesystem. Sorting is a whitelist mapped to column names.

## 2. Tables (exploratory store)

| table | content |
|---|---|
| `p4_player_classification_base` | classification before overrides (one row per player) |
| `p4_player_classification` | base plus validated overrides (what the API reads) |
| `p4_classification_evidence` | one row per squad row: match type, candidate ids, team corroboration |
| `p4_classification_unresolved` | squad rows not resolved to exactly one player_id |
| `p4_classification_coverage` | counts per nationality x status combination |
| `p4_player_stats` | per player and format descriptive totals (PRE_TEST window, innings 1-2, IPL/T20I) and matches played |
| `p4_pressure_scores_frozen_rules` | experimental scores (Phase 4 Chunk 3); the API reads the carried definition, the frozen shrinkage configuration, window `PRE_TEST` and streams `runs` (batters) and `charged` (bowlers) |
| `p4_ranking_distributions` | bootstrap Top-10 inclusion and rank intervals per scope and role |

`window = TEST` rows are never served; the loader filters on `PRE_TEST` and the TEST lock is untouched.

## 3. Classification pipeline

Input evidence (investigated, not assumed): `ipl squad.csv` has `nationality` (Indian or Overseas) and `designation` (only `Captain` or blank), so it carries no capped/uncapped information. The other CSVs carry no nationality or cap status. Therefore:

1. **Squad resolution.** Each squad row is matched to `players.player_name` by case-insensitive exact name. One id gives `EXACT_UNIQUE`; several give `EXACT_AMBIGUOUS`; spelling-variant matches (`name_variants`) give `VARIANT_CANDIDATE` and are never applied. Name matching only generates candidates.
2. **Team corroboration (id-keyed).** Each squad team group is mapped to a `team_id` by the plurality (at least 80 percent, at least 5 resolved rows, one-to-one) of its uniquely matched players in `competition_team_player_mapping` for the squad competition. A row is applied only when the player's team in that competition equals the inferred team. Team names are never joined as text.
3. **Nationality.** Override, else the corroborated squad value (`DERIVED`, source `ipl squad.csv:NAME_PLUS_TEAM_MATCH`), else derived from T20I national-team appearances (`DERIVED`, source `DERIVED_FROM_T20I_NATIONAL_TEAM:<teams>`; Indian only if every appearance is for India, Overseas only if none is), else `Unknown` with a reason. A disagreement sets `conflict_flag` and keeps the higher-ranked source.
4. **International status.** Override, else `Capped` / `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES` when the player was listed as playing in a T20I on or before the as-of date (default 2025-12-31, end of PRE_TEST), else `Unknown` (`NOT_PROVEN_CAPPED_IN_DATA` or `FIRST_T20I_AFTER_AS_OF_DATE`). `Uncapped` is never derived.
5. **Overrides.** `config/classification_overrides_v1.csv`, columns `player_id, field, value, source, verified_by, verified_date`, header only by default. Validation: exact columns, integer known `player_id`, field in `nationality|international_status`, value in the enum (no `Unknown`), non-empty `source` and `verified_by`, ISO date, no duplicate `(player_id, field)`. All errors are reported together and nothing is applied on failure. An override wins, is labelled `VERIFIED_FROM_SOURCE` with source `MANUAL_OVERRIDE:<source>`, and sets `conflict_flag` when it contradicts a derived value.
6. **Outputs.** Tables above plus `data/reports/phase4_classification.csv`, `phase4_classification_coverage.json`, `phase4_classification_coverage_report.md`, `phase4_unresolved_players.csv`.

Configuration: `config/phase4_classification_v1.json` (version, as-of date, corroboration thresholds, source needed).

## 4. Views and scores

- Score per player and side: the shrunk estimate of the primary stream. Batter: runs per ball above baseline. Bowler: the shrunk runs-charged residual with the sign flipped, so higher is always better. Interval limits follow the same orientation.
- `standardised_score = (score - mean) / sd` over the eligible pool of that side and format (sd with ddof 1; if the pool has fewer than two players the score is centred only). Deviation from the plan: the pool statistics are used instead of TRAIN-only parameters because the score table already contains only PRE_TEST data; no TEST outcome is involved.
- Rank: eligible players ordered by `score` descending, then `player_id` ascending. Ineligible players have no rank.
- A player with both a batter and a bowler score enters selection and the overall uncapped ranking once, under the side with the higher standardised score.

## 5. Composition optimiser (`app/phase4/selection.py`)

Groups: `IN_CAPPED, IN_UNCAPPED, OS_CAPPED, OS_UNCAPPED, UNKNOWN`. Each player is in exactly one group. Constraints: per-group exact/min/max, optional per-role exact/min/max (roles not named collapse into an `OTHER` bucket; players with no known role are excluded when roles are used and counted), and the total size.

Method: dynamic programme over groups whose state is the vector of role-bucket counts (a single bucket without roles). Within a (group, bucket) cell the best `k` players are the top `k` by score (ties by `player_id`); this is optimal for fixed counts by an exchange argument, and the DP enumerates every feasible count vector, so the total is globally optimal. Scores are rounded to 1e-9 and compared as integers. Among all optimal count paths the selection with the lexicographically smallest sorted `player_id` tuple is returned, so the result is deterministic and independent of input order.

Infeasibility: pre-checks name the failing constraint with `required` and `available` (group minimum above availability, role minimum above availability, minimums above the total, total above the maximum reachable size); if none fires but the combination is impossible the explanation says so. `allow_fewer` returns the largest feasible size below the total with status `PARTIAL`. Nothing is padded or relaxed. Limits: total at most 50, at most 12 with role constraints.

Tests prove optimality against brute-force subset enumeration (fixed cases, role constraints and 150 random seeded requests) and cover the 4/3/2/1 example (Indian capped 4, Indian uncapped 3, Overseas capped 2, Overseas uncapped 1).

## 6. Presets

`config/phase4_selection_presets_v1.json` holds parameter templates only. A preset runs the optimiser over the stored scores. If the verified pool cannot satisfy it, the response is `POOL_TOO_SMALL` with the explanations and a pointer to the data request; list-type presets (`top_*`, `best_overseas_*`, `emerging_*`) use `allow_fewer` and return `PARTIAL` with the real count when some players qualify. `emerging_domestic_talent` is defined as Indian verified-Uncapped eligible players with an optional `min_matches`; it depends entirely on verified classification evidence.

## 7. Profiles and radar data

Axes are data only. Batter: pressure residual, strike rate (`100 * runs / balls`), boundary rate (`(fours + sixes) / balls`), balls per dismissal (undefined with zero dismissals). Bowler: pressure residual (sign flipped), economy (`6 * runs / legal balls`, lower is better), balls per wicket (undefined with zero wickets, lower is better), dot-ball rate. Normalisation is a percentile within a reference population (ties count half). Overall reference: players of the format with at least 60 balls; the pressure axis uses all eligible experimental players. The uncapped reference is the verified-uncapped subset and needs at least five players. Sparse cases return `INSUFFICIENT_DATA` with the reason. Strength sentences are templates over stored values (percentile at least 75 and reference at least 10). Descriptive totals use innings 1 and 2 of IPL and T20I matches in TRAIN and VALIDATION; DLS rows are not excluded from these descriptive totals (stated in `restrictions`).

## 8. API gating

- Rankings, selection and profiles read only experimental `p4_` tables and always return `status = EXPERIMENTAL_NOT_VALIDATED` and `official_ranking = false`.
- `official=true` or `publish=true` (query) and `official: true` (body) return 403 `OFFICIAL_RANKING_NOT_AUTHORIZED`.
- Admin endpoints need `X-Admin-Token` equal to `SUPERR_ADMIN_TOKEN` (constant-time compare). Without the variable they answer 503. This is a minimal mechanism because the repository has no authentication system (open decision).
- Configuration: `SUPERR_P4_STORE` selects the analytical store (default `data/database/exploratory.duckdb`). Start with `uvicorn app.main:app`.

## 9. Open decisions

- Default `format` is `IPL` for rankings and selection (classification evidence is IPL-squad based); the 70:30 combined estimate stays provisional.
- `basis` defaults to `INCLUDE_DERIVED_CAPPED`; `VERIFIED_ONLY` treats every derived value as Unknown.
- UNKNOWN is a single composition group (nationality or status Unknown).
- Real authentication is out of scope.
- A verified cap source is required before any uncapped list or preset can contain players.


## 10. Phase 5 changes (Chunk 1): classification, strict uncapped, gating

- New package `app/phase5/`: `classification_v2.py` (enum, explicit `MIGRATION_MAP`, `migrate_classification`, `validate_overrides_v2`, `apply_overrides_v2`, `coverage_v2`, `strict_uncapped_capability`), `gating.py` (`GateInput`, `evaluate_gates`, `publication_status`, `apply_gates`, `PublicationGateError`), `store.py` (`write_p5_table`), `constants.py`.
- Tables written by `scripts/phase5_classification.py` and `scripts/phase5_gates.py` to the exploratory store: `p5_player_classification`, `p5_player_classification_base`, `p5_classification_migration_map`, `p5_classification_coverage`, `p5_strict_uncapped_capability`, `p5_publication_gates`. The `p4_*` tables are unchanged. The API reads the `p5_` classification tables only.
- Configs: `config/phase5_classification_v2.json`, `config/classification_source_manifest_v1.json` (`{"sources": []}`), `config/phase5_gates_v1.json`, `config/phase5_methodology_status_v1.json`. `config/classification_overrides_v1.csv` is unchanged (header only).
- API: `create_app(..., gate_inputs=None, source_manifest=None, classification_config=None)`. `gate_inputs` is a function argument only (tests supply synthetic pass or fail fixtures); it is never an environment variable or request field.
- Admin reload (`POST /admin/classification/reload`) validates the override file with the v2 rules, rebuilds `p5_player_classification` from `p5_player_classification_base`, recomputes the capability and resets cached gate inputs.
- Status model: `result_status` `STRICT_UNCAPPED_DISABLED` (HTTP 200 on internal and descriptive routes), error code `PUBLICATION_GATE_NOT_SATISFIED` (HTTP 403 on public rows routes). The full enum mapping, gate table and disabled body are in `docs/frontend_backend_contracts.md` section 8.
- Unresolved in this chunk: date verification of the 42 late T20I matches (gate `date_verification` fails with `NOT_RUN`), methodology validation, data-weight thresholds, and an authoritative id-keyed cap source. Official rankings and model training are not approved.
## 11. Phase 5 dynamic filter-driven ranking engine (Chunk 4, INTERNAL / EXPERIMENTAL)

### 11.1 Workflow
Build once, serve many: `scripts/phase5_context_engine.py` loads the pre-test study (TEST rows dropped before any frame exists), asserts that the Phase 4 scores reproduce, builds `p5_context_stats` (additive per-player-match-phase-situation statistics of the carried definition's pressure rows), fits each of the 48 atomic contexts on TRAIN rows only, derives each context's own working threshold, writes `p5_context_fit`, `p5_context_eligibility_rules`, `p5_context_scores`, `p5_context_manifest`, `p5_filter_catalog` and `p5_context_coverage`, and exits 1 unless the overall context equals the stored Phase 4 scores and the official data, Phase 4 reports and TEST lock are unchanged. `scripts/phase5_context_coverage.py` rebuilds only the coverage table and its summary, `scripts/phase5_dynamic_demo.py` runs the example filter sets, `scripts/phase5_context_spotcheck.py` recomputes two context values from the raw state table.

### 11.2 Modules
`app/phase5/context_stats.py` (stored rows, `ContextCell`), `context_eligibility.py` (per-context fit, threshold, scores), `filters.py` (`FilterSpec`, canonical hash, catalog), `ranking_engine.py` (`ContextEngine.resolve_pool` / `rank`, pagination), `cache.py` (`RankingCache`), `coverage.py`; `app/repositories/phase5_repo.py` (read-only loads, data version); `app/services/phase5_service.py` (catalog, preview, ranking, coverage, gating through `Phase4Service.precheck`/`_gate`); `app/api/v1/routes_phase5.py`; `app/schemas/phase5_dynamic.py`; `config/phase5_context_rules_v1.json`. Phase 4 code (`shrink`, `eligibility`, `engine`) is reused unchanged.

### 11.3 Invariants
- No model per filter combination: `fit_cell` runs once per atomic context at build time and never on the request path (test).
- A filter cannot create reliability: `k`, targets and thresholds are fixed per context; a player below the context's threshold is excluded (`INSUFFICIENT_SAMPLE_FOR_CONTEXT`) even if eligible overall.
- Context variance uses TRAIN rows only (test: VALIDATION perturbation leaves the fit unchanged).
- No padding: a pool below 5 returns no rows, 5 to 9 a shorter list; all reasons are returned.
- Deterministic order (score descending, `player_id` ascending) and seeded bootstrap (one weight matrix derived from the stored rows).
- The API has no SQL, path or column parameter; the route, service and filter modules import no database or filesystem module (AST test).
- Gates: every response passes `apply_gates`; public twins return 403 without rows.

### 11.4 Versioning and caching
`model_version` from `config/phase5_context_rules_v1.json`; `data_version` = SHA-256 over the context tables, the config, the model version and the classification table in force. Cache key: see section 12.3 (Phase 6 adds scope, lock version and gate state); bounded LRU; invalidated on any data, model or lock version change; the catalog endpoint exposes hit/miss counters. The coverage table is served while its manifest classification hash matches, otherwise recomputed (`coverage_source`).

### 11.5 Open decisions
`min_internal_pool` 5, `min_public_pool` 10, `min_train_players_for_fit` 8 and the low-weight warning 0.3 are provisional. All 48 contexts hit the variance floor and none passes the marginal data-weight gate; the noise model of the shrinkage estimator needs a methodology decision (see the Chunk 3 reports) before any lock. A TRAIN+VALIDATION refit would build separate tables under another model version.
## 12. Phase 6 cleanup (INTERNAL / EXPERIMENTAL)

### 12.1 Classification wording
`app/phase5/classification_v2.py` defines `STATUS_VALUES` (three real values: `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`), `DISABLED_PLACEHOLDER_VALUES` (`VERIFIED_UNCAPPED`, not an established status) and `ACCEPTED_STORED_VALUES` (the union, used wherever a stored or overridden value is validated). `ClassificationStatus` in `app/schemas/phase5.py` has the three real values. `coverage_v2` reports 3 x 3 combinations, `status_counts` for the real values and `disabled_placeholder_counts` separately. The override mechanism and the strict-uncapped filter (`STRICT_UNCAPPED_DISABLED`) are unchanged. No source or document may describe the classification as four-valued; a test scans the contract and spec documents.

### 12.2 Public descriptive directory
`/players` and `/players/{player_id}` return `PublicPlayerListResponse` / `PublicPlayerDetailResponse` (`app/schemas/phase4.py`). `Phase4Service.players(..., public=True)` and `player_detail(..., public=True)` build rows with an explicit allow-list (`_public_player_item`), never by deleting keys from the internal row. The internal twins `/internal/players` and `/internal/players/{player_id}` use the previous models and need the admin token. The public directory flags are `status`, `disclaimer`, `descriptive_only`. The public `min_pressure_matches` query filter is removed (`public_filter_params`). Invariant: no public response model has a field matching `score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict` (test walks the models and the JSON).

### 12.3 Ranking cache
`app/phase5/cache.py`: `cache_key(spec_hash, data_version, model_version, gate_version, scope, lock_version, gate_state)` is the SHA-256 of the JSON-encoded list; all seven parts are required and `scope` must be `internal` or `public`. `gate_state_hash` hashes the sorted ids of failing gates. `RankingCache.put` stores a deep copy; `get` and `get_or_compute` return deep copies on hit and miss; `invalidate_if_version_changed(data, model, lock)` clears the cache when any differs. `Phase5Service._full(spec, internal)` supplies the scope, the SHA-256 of `config/phase5_methodology_lock_v1.json` and the gate-state hash, and `ranking()` deep-copies the page before building the payload. Gates are still evaluated on every read.

### 12.4 Test hygiene
`app/phase6/cleanup_scans.py` holds the AST scanner for always-true assertions. `tests/test_phase6_no_vacuous_assertions.py` fails on `assert ... or True`, `assert True` and `assert <truthy constant>` in any test file.
