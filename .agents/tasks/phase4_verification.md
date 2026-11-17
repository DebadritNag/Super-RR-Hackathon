# Phase 4 final verification

No phase4_review.json existed, so the full run and checks were executed.

## Commands and results
- `python -m pytest -q`: 509 passed, 3 warnings (RuntimeWarning in LOMO par divide, descriptive only), 298 s.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 176 files already formatted.
- `python scripts/run_phase4.py`: all 7 steps exit 0; identity_ok True; deliverables ok True; spot checks ok True; lock log FREEZE -> OPEN -> CLOSE, opened once, 0 READ_DENIED.

## Deliverables
All ten `phase4_*.md` exist in data/reports (temporal_validation_plan, baseline_calibration_report, pressure_scoring_report, definition_comparison, eligibility_validation, shrinkage_sensitivity, format_weight_sensitivity, ranking_stability, data_quality_report, user_summary) plus extra reports, ~50 JSON/CSV outputs, and `frontend_backend_contracts.md` (10,150 bytes). `phase4_user_summary.md` in reports and in .agents/tasks have identical SHA-256 (E0BCE009...A6124).

## Spot checks (from phase4_spot_checks.json, computed by independent methods; all ok)
1. Strictly-prior par, IPL match 40694 (2025-03-22), raw CSV via csv module: stored 83.7627906977 = independent 83.7627906977 (215 prior innings, 0 same-day exclusions).
2. Period match counts from raw matches CSVs: IPL 219/74/74, T20I 278/122/70, OTHER_T20 15/15 (train/val/test); stored equals independent, no differences. Boundaries: train <= 2024-12-31, validation 2025, test >= 2026-01-01.
3. IPL batter 3125 pressure balls via direct SQL: 343 balls, 25 matches, raw outcome 1.5597667638, equal to stored.
4. Shrunk estimate from stored components (2,690 records): B = n_eff/(n_eff+k) max error 0.0; residual identity error 0.0; point estimate inside interval for 100%.
5. Capped count from playing_eleven/matches CSV: 655 equals stored.
6. Top-10 inclusion probabilities sum to 10.0 in each of the four pools.
Selection result: definition any|q0.75 chosen by the pre-written rule on train/validation (PROVISIONAL), shrinkage shrink_tau4; frozen-choices sha256 86f5ce9d...; eligible pools IPL batter 132, T20I batter 243, IPL bowler 80, T20I bowler 141.

## Hashes
`phase4_hash_after.txt` vs `phase4_hash_before.txt` (23 files): 22 identical, including superr.duckdb (CB4077EE...A391D) and every source CSV. The only difference is `exploratory.duckdb`, the experimental store, which the run is meant to write.

No official rankings published, no ML model trained.
