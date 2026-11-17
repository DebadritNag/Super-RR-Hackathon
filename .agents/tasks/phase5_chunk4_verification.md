# Phase 5 Chunk 4 verification (dynamic filter-driven ranking engine)
All commands run from `d:/Data/backend` with `$env:PYTHONUTF8=1`. Everything is EXPERIMENTAL_NOT_VALIDATED / INTERNAL_EXPERIMENTAL_ONLY. No gate file existed (`phase5_chunk4_gate.json` absent), so the full chunk was implemented.

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_phase5_dynamic_ranking.py tests/test_phase5_api.py tests/test_phase5_dynamic_real.py` | 67 passed (26 engine, 37 API, 4 real-data, about 97 s) |
| `python -m pytest -q` (full) | 757 passed (690 earlier + 67 new), 3 pre-existing warnings, 383 s |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 231 files already formatted |
| `python scripts/phase5_context_engine.py` | exit 0, about 72 s: 48 contexts, 10,106 stored rows, 10,082 score rows, preservation true |
| `python scripts/phase5_context_coverage.py` | exit 0: 3,888 combinations, preservation true |
| `python scripts/phase5_dynamic_demo.py` | exit 0: 10 example filter sets, preservation true |
| `python scripts/phase5_context_spotcheck.py` | exit 0, all agree |
| `python scripts/phase5_gates.py` | exit 0, report now has a dynamic-ranking section |

Preservation (checked by `Preservation.verify()` in every script): official database and source CSV snapshot unchanged, 56+ `phase4_*` report files byte-identical, `phase4_lock_log.json` SHA-256 unchanged, `phase5_lock_log.json` has no OPEN (TEST not opened). `superr.duckdb` was not modified. Only `p5_context_*`/`p5_filter_catalog` tables in `exploratory.duckdb` and new `phase5_*` reports were written. One existing test assertion was updated (`test_phase5_gating.py::test_every_rows_returning_route_carries_the_publication_fields`: internal route count 6 to 10 for the four new internal routes; public `/rankings/*` count stays 2).

## Reproduction precondition (fatal if it fails)
- Phase 4 reproduction before building (`reproduce_phase4_scores`): max abs diff 0.0 over the carried scores.
- The built (ALL, ALL) context equals the stored Phase 4 scores (`shrink_tau4`, PRE_TEST, IPL and T20I, primary streams): max abs diff 2.8e-17, opportunity counts equal for every compared player.

## Independent spot checks
1. Context-specific `n` and residual (the requested check), `scripts/phase5_context_spotcheck.py`, recorded in `data/reports/phase5_context_spotcheck.json`:
   - IPL batter, death overs, chase, top-ranked player 4708 (Rinku Singh). Raw state table (`exp_pre_delivery_state` joined to `p4_match_period`, TEST excluded, SQL with the frozen chase threshold 12.28125): 103 pressure balls, 8 matches, 260 actual runs. Stored `p5_context_stats`: n 103, 8 matches, residual sum 100.86516457857006, expected sum 159.13483542142993 (260 = 100.865 + 159.135). Study second path (baseline refit): n 103, residual sum 100.8651645785701. Engine response: n 103, matches 8, raw mean 2.52427 x 103 = 260.0, residual sum 100.8652. All equal.
   - T20I bowler, middle overs, chase, top-ranked player 5979 (Abrar Ahmed): raw state table 51 balls, 6 matches, 34 runs conceded; stored residual sum -29.627819344709163, expected sum 63.62781934470916 (34 = 63.628 - 29.628); study path equal; engine equal.
2. Unit tests recompute with plain pandas/numpy: context `n`, `matches`, Kish `n_eff`, mean residual; eligibility = `n >= threshold * window_ratio` with the window ratio from TRAIN/total balls; threshold is one of the context's own percentile candidates; shrunk values with a hand-built leave-one-player-out target and the stored `k`; and a bootstrap interval from a pure-Python loop over the global weight matrix (equal to 1e-9).
3. Coverage: sampled combinations' `final_pool` equals the ranking's `pool_size`; the stored table for the example sets equals `resolve_pool` on the real store.
4. Strict uncapped disabled, from the running app (internal token): dynamic ranking and context preview (3 bodies each), all 5 `/internal/rankings/uncapped/{kind}`, all 6 presets, and a custom `IN_UNCAPPED` constraint return `STRICT_UNCAPPED_DISABLED` with no rows; the public twin answers 403 `PUBLICATION_GATE_NOT_SATISFIED`; 432 coverage rows are listed DISABLED.

## What was built
- `app/phase5/`: `context_stats.py`, `context_eligibility.py`, `filters.py`, `ranking_engine.py`, `cache.py`, `coverage.py`; `app/repositories/phase5_repo.py`; `app/services/phase5_service.py`; `app/api/v1/routes_phase5.py`; `app/schemas/phase5_dynamic.py`; `config/phase5_context_rules_v1.json`. Edits: `app/main.py` (router and service wiring), `app/api/deps.py` (`Service5`), `app/schemas/phase5.py` (optional `filter_echo` on the disabled body), `scripts/phase5_gates.py` (dynamic section).
- Scripts: `phase5_context_engine.py`, `phase5_context_coverage.py`, `phase5_dynamic_demo.py`, `phase5_context_spotcheck.py`.
- Tests: `test_phase5_dynamic_ranking.py` (26), `test_phase5_api.py` (37), `test_phase5_dynamic_real.py` (4), helpers `tests/phase5_ctx_helpers.py`.
- Docs and reports: `data/reports/phase5_dynamic_ranking_architecture.md`, `phase5_publication_gates.md` (regenerated with a dynamic section), `phase5_context_coverage.{csv,json}`, `phase5_context_coverage_summary.json`, `phase5_context_engine_summary.json`, `phase5_context_fit.*`, `phase5_context_eligibility_rules.*`, `phase5_dynamic_examples.json`, `phase5_context_spotcheck.json`; `docs/frontend_backend_contracts.md` section 9 and `docs/backend_implementation_spec.md` section 11 (workflow, filter spec schema, gates, error/status model, versioning, caching, future public release, classification enum).
- Plan deviations (documented): internal routes are `/internal/rankings/dynamic`, `.../context-preview`, `.../coverage` (nested to avoid a route clash with `/internal/rankings/{role}`); public twins are under `/dynamic-rankings` so the existing `/rankings/*` route count is unchanged; no `FilterSpecError` class was added (FastAPI validation returns 422 and combination problems are structured results); the context-stats foundation planned in Chunk 3 (`context_stats.py`) did not exist yet and was built here.

## Findings the reports state (all from running code)
- Between-player moment is negative in all 48 contexts, so every context hits the variance floor (`k = 25.0`), the same finding as Phase 4 and Chunk 3. Scores are mostly shrinkage targets; every row carries `fit_floor_hit`.
- All 48 contexts are `THRESHOLD_NOT_VALIDATED`; working thresholds 6 to 49 balls; the marginal shrinkage weight is 0.04 to 0.12 and the median weight 0.05 to 0.29; 0 of 48 pass the 0.5 marginal gate. Rankings carry `CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED` and mostly `LOW_DATA_WEIGHT_CONTEXT`.
- The brief's expectation that death + chase + Indian + DERIVED_CAPPED is empty did not hold: combined pool 7 (IPL batters 28, T20I batters 8); it is reported as a short, low-weight, internal list, not padded. Shown honestly in the architecture report.
- Coverage: 3,888 combinations, 432 disabled (strict uncapped), 1,889 reach the internal minimum of 5, 1,558 reach the public-size rule of 10, 1,567 empty, 331 shorter than ten. No combination is publishable (data-weight, methodology and date gates fail).

## Notes
- No git repository in `d:/Data`, so no commit was made.
- Provisional config values (min pools 5 and 10, `min_train_players_for_fit` 8, low-weight warning 0.3) are open decisions, listed in the architecture report.
- No finding required a user-visible behaviour change, so no warning was sent.
