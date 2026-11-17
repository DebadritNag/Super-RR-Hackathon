# Dynamic filter-driven ranking engine (Phase 5 Chunk 4)

The change adds a stored-analytics ranking layer: 48 atomic contexts (competition x role x phase x situation) are fitted once on TRAIN rows, and each request only resolves a pool by AND-ed filters, re-ranks it and bootstraps intervals from fixed parameters. Internal routes sit behind the admin token, public twins answer the gate response with no rows, and every response goes through the single gating function. No git repository exists, so the review reads the files directly and relies on the verification file for suite results (not re-run).

Watch for: (1) a vacuous assertion in a row-explanation test (`... or True`), confirmed; (2) the working-pool thresholds and minimum pool sizes (5 and 10) are provisional config values with no validation, confirmed and already documented; (3) all 48 contexts sit on the variance floor (k = 25), so scores are mostly shrinkage targets, confirmed from the report and surfaced on every row via `fit_floor_hit`.

**Verdict**: APPROVED

## High-level view

Eligibility, `n`, `n_eff`, residual means and thresholds are computed per atomic context from stored delivery-level aggregates (`context_eligibility.build_context`). Phase and situation filters therefore genuinely re-aggregate rows rather than slicing an overall score. `tau2` and `k` come from `fit_cell` on TRAIN players of that context only, thresholds are the context's own percentile candidates, and a context with too few TRAIN players is `CONTEXT_NOT_ESTIMABLE` instead of borrowing the parent cell's variance. There is no per-filter model.

Pool resolution applies classification filters with AND semantics, counts unknown-classification exclusions, then experience filters. Below the internal minimum there are no rows, below ten the list is short with `FEWER_THAN_LIST_SIZE`, and nothing is padded or borrowed from a wider context. Batter and bowler are a required, separate `role`. Ordering is score descending then `player_id` ascending, and display sorting does not change rank values.

The cache key is the SHA-256 of spec hash, data version (context tables plus classification table hash), model version and gate config version. Gates are recomputed on each read and never cached. Public routes use `precheck` before rows are computed. Strict uncapped returns the structured disabled body before any score table is read. The route module has no SQL or filesystem access, and a test enforces that by AST.

<details>
<summary>Issues (3)</summary>

1. **Vacuous interval assertion** (confirmed) — `test_every_row_carries_the_full_explanation` ends its interval check with `or True`, so it asserts nothing. Replace it with `interval_low <= interval_high` or a real containment check, or drop it.
2. **Provisional pool and weight constants** (confirmed) — `min_internal_pool` 5, `min_public_pool` 10, `min_train_players_for_fit` 8 and the 0.3 low-weight warning are unvalidated config values. They are listed as open decisions; confirm them at the stop-for-review.
3. **Shared mutable cached payload** (possible) — the cache returns the same dict to every caller, and `paginate_ranked` copies only the row list, not the row dicts. No current code path mutates rows; add a defensive copy if a handler ever edits them.

</details>

<details>
<summary>Details</summary>

## Context fits and eligibility are recomputed from stored rows

`build_artifacts` runs once per atomic context. `ContextEngine.rank` never calls `fit_cell`, and the `fit_calls` counter is asserted to stay at zero in tests. The test `test_context_variance_is_fitted_on_train_rows_only` perturbs TRAIN rows of IPL and shows that IPL fits change while T20I fits do not. The verification file reports an independent raw-table spot check for two top-ranked players (IPL batter death/chase, T20I bowler middle/chase), where `n`, matches and the residual sum agree across the raw table, the stored table, the study path and the engine response. The (ALL, ALL) context reproduces the stored Phase 4 scores to 2.8e-17.

## Combined format and gating behaviour

The combined format requires an eligible context in both formats; players eligible in one format are counted under `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS` rather than scored on one leg. `n_eff` for the 70:30 blend uses the variance-weighted harmonic form, and a test recomputes it by hand. Every payload passes through `apply_gates`, so `publication_status` and `gate_results` are always present, and a route-enumeration test fails if a route lacks them. Strict uncapped is refused on the dynamic ranking, context preview, the five uncapped routes, presets and a custom constraint, with the public twin answering 403.

## Floor-hit and low data weight

Every context hits the variance floor, and none passes the 0.5 marginal-weight gate. Rankings carry `CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED` and mostly `LOW_DATA_WEIGHT_CONTEXT`, and the architecture report states the finding. Because no combination can pass the publication gates, nothing publishable is produced.

## Documentation

`docs/frontend_backend_contracts.md` section 9 and `docs/backend_implementation_spec.md` section 11 cover workflow, filter schema, gates, error and status model, versioning, caching and the future public release. Route-path deviations from the design (nested internal paths, `/dynamic-rankings` public twins) are documented.

</details>

<details>
<summary>File map</summary>

- `app/phase5/context_stats.py`, `context_eligibility.py`: stored aggregates, per-context fit, rules and scores.
- `app/phase5/filters.py`, `ranking_engine.py`, `cache.py`, `coverage.py`: filter spec, pool/ranking, cache, coverage table.
- `app/repositories/phase5_repo.py`, `app/services/phase5_service.py`, `app/api/v1/routes_phase5.py`, `app/schemas/phase5_dynamic.py`: wiring and routes.
- `tests/test_phase5_dynamic_ranking.py`, `test_phase5_api.py`, `test_phase5_dynamic_real.py`: 67 tests.
- `docs/` and `data/reports/phase5_*`: contracts, spec, architecture, coverage and spot-check reports.

</details>
