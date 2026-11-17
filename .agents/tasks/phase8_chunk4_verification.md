# Phase 8 chunk 4 verification (Approach C, PRI, combination study)

Environment: Windows, PowerShell, `PYTHONUTF8=1`, `PYTHONPATH=d:/Data/backend`, cwd `d:/Data/backend`.

## Commands and results
- `python scripts/phase8_approach_c.py all`: exit 0. Stages `estimate` (run-log step `approach_c_estimate`, criteria hash verified, protected files and TEST lock state checked before and after) and `report` (writes `data/reports/phase8_approach_c_results.md` from `p8_c_*` tables only).
- `python -m pytest tests/test_phase8_approach_c.py -q`: 15 passed.
- `python -m pytest -q` (full suite): **1373 passed, 4 warnings in 1123.52 s**.
- `ruff check .`: All checks passed. `ruff format --check app scripts tests`: 329 files already formatted.

## Outputs
- Code: `backend/app/phase8/approach_c.py`, `backend/app/phase8/report_c.py`, `backend/scripts/phase8_approach_c.py`.
- Tests: `backend/tests/test_phase8_approach_c.py` (weight rules, PCA with non-negative loadings, FIT/HELD split, PRI recovery and centring, seeded bootstrap, held-out split-half, format hierarchy recovery, combination rule).
- Tables in `phase8.duckdb`: `p8_c_estimates`, `p8_c_weights`, `p8_c_component_corr`, `p8_c_component_reml`, `p8_c_component_reliability`, `p8_c_reliability`, `p8_c_status`, `p8_c_sensitivity`, `p8_c_format_study`, `p8_c_format_hierarchy`, `p8_c_boot_check`, `p8_c_fit_split`.
- Report: `backend/data/reports/phase8_approach_c_results.md`.

## Key results (all EXPERIMENTAL_NOT_VALIDATED)
- Eligible players (A and B floors): 224 batters, 221 bowlers. FIT = 243 TRAIN odd-position matches; HELD = 432 matches (244 TRAIN even, 188 VALIDATION).
- Data-derived weights (FIT only): only CONS is active for both roles. Batters: A and B at the REML floor (`NO_SIGNAL_FLOOR`). Bowlers: A split-half -0.23 (`NO_SIGNAL_NONPOSITIVE_RELIABILITY`), B at the floor. PCA not triggered (one active component).
- Held-out reliability: batters parity SB 0.057 [-0.19, 0.30], time -0.087, out-of-time rho -0.02 (lower -0.20); bowlers parity SB 0.267 [-0.08, 0.39], time 0.175, out-of-time rho 0.199 (lower 0.027). Both lists EXPLORATORY; no PROVISIONAL threshold met. Phase 6 gate (mean data weight >= 0.5) not passed by any component, reported unchanged.
- Combination study: PRI cross-format Spearman batters -0.11 [-0.32, 0.12] (85 players), bowlers 0.22 [-0.02, 0.43] (76 players). Rule (lower bound >= 0.3, >= 30 players) not met, so `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`; IPL-only and T20I-only candidate lists are in the report and `p8_c_estimates`. Hierarchical format model fitted per component; no fixed 70:30 weights.

## Not done in this chunk
- Applying the predeclared approach-selection rule (A vs B vs C) and `methodology_comparison.md`: the chunk-4 instruction did not include them; the report states selection is a later step.
- No Top 10 submission CSV was written (chunk 5).
