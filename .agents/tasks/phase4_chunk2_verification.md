# Phase 4 Chunk 2 verification

Environment: PowerShell, `$env:PYTHONUTF8=1`, Python 3.11, cwd `d:/Data/backend`.

## Built
- `app/phase4/baseline.py`: TRAIN-frozen stratified EB baselines (reuses `baseline_engine` levels, `k_from_children`, shrink helpers); TRAIN-only wickets bins; per-format additive offsets (calibration identity); TRAIN rows use leave-player-out expectations, later periods use frozen tables; `calibration_report` (identity, residual distribution, level usage/fallback counts, by format/phase/wickets bin/expected decile/year).
- `app/phase4/shrink.py`: leave-one-player-out pooled target (TRAIN only), TRAIN-only tau2 with floor, role/format cell separation, configs (`shrink_none` zero shrinkage, `shrink_eb`, tau multipliers 0.5/2/4, `floor0.001`, `target0`), match-cluster bootstrap intervals, `choose_shrinkage` (TRAIN estimates vs VALIDATION outcomes, paired bootstrap SE rule, none/target0 not choosable), `record_choice` (written before scoring).
- `app/phase4/scoring.py`: TRAIN-only quantile thresholds, strictly prior par signal, definition flags (`chase|any|inn1` x q), `PressureRecord` full schema (EXPERIMENTAL_NOT_VALIDATED, official_ranking false), single-format and combined (both-format-eligible only, no zero fill) records, Phase 3 placeholder eligibility, `evaluate_test_scores` (only route to TEST, via `evaluate_on_test`).
- `app/phase4/lockguard.py`: `guard_frame` refuses and logs TEST rows while the lock is closed; `drop_test_rows`.
- Scripts `scripts/phase4_baseline.py`, `scripts/phase4_scoring.py` (TEST rows never loaded). Outputs in `data/reports`: `phase4_calibration.json`, `phase4_baseline_calibration_report.md`, `phase4_shrinkage_choice.json`, `phase4_pressure_scores_experimental.{csv,json}`, `phase4_pressure_scoring_report.md`; tables `p4_calibration`, `p4_pressure_scores` in `exploratory.duckdb`.
- Tests: `tests/test_phase4_shrink.py`, `tests/test_phase4_baseline_scoring.py`, helper `tests/phase4_scoring_helpers.py` (28 new).

## Commands and results
| command | result |
|---|---|
| `python scripts/phase4_baseline.py` | identity_ok True; official data unchanged True |
| `python scripts/phase4_scoring.py` | 3380 records; chosen shrinkage `shrink_tau2` (difference to `shrink_eb` is within about 1 SE, so the choice is weak); official data unchanged True |
| `python -m pytest -q` | 390 passed (362 + 28), 2 pre-existing warnings |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 127 files already formatted |

`superr.duckdb` SHA-256 CB4077EE...391D equals `phase4_hash_before.txt`.

## Findings
- Calibration identity on TRAIN holds to about 1e-16 relative per format and stream. VALIDATION IPL runs residual is +0.11 per ball (batter) and the overall VALIDATION residual is +0.05 (scoring drift in 2025), reported in the calibration report.
- Shrinkage: zero shrinkage has VALIDATION loss 0.43 against 0.20 for the EB family. Differences among EB-family configs are tiny.

## Notes
- Bowler pressure uses the same state signals as batters; the bowler-specific signal B is left for Chunk 3 (stated in the module and report).
- Eligibility is the Phase 3 placeholder (24 batter / 36 bowler balls), labelled `PHASE3_PLACEHOLDER`.
- The repository is not a git repository, so no commit was made. TEST was never read.

## Review fixes
Combined records now populate opportunities/matches/ESS and raw/expected/residual; notes on tau grid edge and TRAIN/VALIDATION baseline asymmetry added to phase4_pressure_scoring_report.md; test added. Results: pytest 391 passed; ruff check clean; ruff format --check clean; scores regenerated, official data unchanged.
