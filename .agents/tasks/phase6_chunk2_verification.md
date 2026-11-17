# Phase 6 chunk 2 (variance/floor and split-half) verification

Working directory `d:/Data/backend`, `$env:PYTHONUTF8=1`, interpreter `python` (3.11). The workspace is not a git repository, so nothing was committed.

## What was built
- Config and criteria: `config/phase6_investigation_v1.json`, `config/phase6_selection_criteria_v1.json` (SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851`), `data/reports/phase6_selection_criteria_hash.json`, `data/reports/phase6_investigation_plan.md`. Order is enforced by the append-only `p6_run_log` (seq 1 = `plan`, later steps append rows).
- Modules `app/phase6/`: `constants.py`, `store.py`, `lockguard.py`, `outputs.py`, `criteria.py`, `estimators.py`, `variance_floor.py`, `split_half.py`.
- Scripts: `scripts/phase6_investigation_plan.py`, `scripts/phase6_variance_floor.py`, `scripts/phase6_split_half.py`.
- Tables in `exploratory.duckdb`: `p6_run_log`, `p6_variance_estimators`, `p6_floor_diagnostics`, `p6_floor_arithmetic`, `p6_split_half`, `p6_split_half_ci`, `p6_split_half_pooled`. CSV/JSON/MD under `data/reports/phase6_*`.
- Tests: `test_phase6_variance_estimators.py` (25), `test_phase6_variance_floor.py` (11), `test_phase6_split_half.py` (12), `test_phase6_criteria_hash.py` (10), `test_phase6_variance_guards.py` (6): 64 new tests.

## Commands and results
| command | result |
|---|---|
| `python scripts/phase6_investigation_plan.py` (run twice) | first run wrote criteria + hash + run-log seq 1; second run `already_written: true` |
| `python scripts/phase6_variance_floor.py` | exit 0, ~100 s; 48/48 stored `p5_context_fit` records reproduced (max abs diff 4.9e-11); 3600 estimator rows, 240 diagnostic rows; `all_preserved: true` |
| `python scripts/phase6_split_half.py` | exit 0, ~160 s; 432 rows (428 estimable), 998 interval rows, 108 pooled rows; 128/128 Phase 5 odd/even and early/late rows reproduced (max abs diff 9.7e-17); `all_preserved: true` |
| both scripts run a second time, output CSV hashes compared | all 6 CSV files byte-identical (seeded, deterministic) |
| `python -m pytest -q` | **917 passed** (853 before + 64 new), 3 warnings, 577 s |
| `python -m ruff check .` / `python -m ruff format --check .` | All checks passed / 272 files already formatted |

## Independent spot checks (throwaway script, deleted afterwards)
- Split-half: IPL batter runs, `any|q0.75`, PRE_TEST, odd/even, 6 balls per half. Recomputed from raw ball rows with pandas/numpy: 144 players, r 0.243385, SB 0.391487. Module: 144 players, r 0.243385, SB 0.391487 (abs diff 1.4e-16).
- Variance component: IPL batter ALL/ALL, TRAIN, direct formula from `p5_context_stats`: 244 players, sigma2 3.122743, between (Kish) -1.084302, k under `shrink_tau4` 25.0. Module: sigma2 3.122743, between -1.084302, k 25.0.

## Floor arithmetic (from code)
`k_for` on a floor-hit fit (between -1, sigma2 3): shrink_eb 100, shrink_tau0.5 100, shrink_tau2 50, shrink_tau4 25, shrink_floor0.001 1000, shrink_target0 100, shrink_none 0. Non-finite branch: `1/floor` (100, or 1000 for floor0.001). 14/14 rows agree with the independent hand formula. Stored contexts: 48/48 floor hits, all k = 25.0.

## Key findings (PRE_TEST, 48 contexts; `phase6_variance_floor_investigation.md`)
- Raw Phase 4 (Kish) between variance is negative in 48/48; it is positive in 39/48 on the independent-ball basis and 40/48 on the match-cluster basis. Sign depends on the noise model.
- Model-free split covariance (E7): lower bound above 0 in 5 of 47 estimable contexts, interval contains 0 in 42. E6 positive-draw share is at least 0.9 in 47/47, so `H-A_SUPPORTED` was not reachable; E6 median exceeds its point estimate in 47/47 (upward shift).
- Verdict counts (pre-declared flag table): H-B_SUPPORTED 4, H-C_SUPPORTED 16, MIXED 19, UNIDENTIFIED 8, NOT_ESTIMABLE 1. Noise-model misspecification is supported in 24/48 (H-B overall). Open decision for the user on the noise basis is recorded in the report; nothing was changed.
- Split-half (primary streams, PRE_TEST, nine definitions): SB median 0.301 odd/even, 0.258 early/late, 0.276 random; interval lower bound above 0 in 16/36, 5/36 and 9/36 units. Provisional `any|q0.75` pooled SB over four cells: 0.37 odd/even, 0.32 early/late, 0.32 random.

## Preservation and constraints
- `phase6_prerun_hashes.json` (146 files): 145 unchanged; only `exploratory.duckdb` differs (new `p6_` tables). Both scripts hashed every `p4_` and `p5_` table before and after: unchanged.
- Phase 4 lock log SHA unchanged (`cae1e06c...eb75c`), Phase 5 lock log 0 events, `test_opened: false`. TEST rows are refused by `assert_no_test_rows`, `check_stats` and `Study`; superr.duckdb unchanged (official data snapshot equal). No Cricsheet import or path in any Phase 6 module (AST test).
- The 0.5 data-weight gate and all config/threshold files were not touched.
- Interpretation caveat recorded in the reports: E6 and the match-cluster basis are the weaker evidence; match-bootstrap intervals of split-half reliability are not centred (midpoint below the point estimate in 250/286 units).
