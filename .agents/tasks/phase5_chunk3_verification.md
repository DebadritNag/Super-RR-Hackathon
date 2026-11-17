# Phase 5 Chunk 3 verification (investigations: reliability, sensitivity, ranking stability)
All commands run from `d:/Data/backend` with `$env:PYTHONUTF8=1`. Everything is EXPERIMENTAL_NOT_VALIDATED / PROVISIONAL.

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_phase5_investigation.py` | 39 passed |
| `python scripts/phase5_investigation.py` | exit 0, about 95 s, preservation true, both spot checks agree |
| `python scripts/phase5_sensitivity.py` | exit 0, about 45 s, preservation true |
| `python scripts/phase5_ranking_stability.py` | exit 0, about 25 s, preservation true |
| `python -m pytest -q` (full) | 690 passed (651 earlier + 39 new), 3 pre-existing warnings |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 212 files already formatted |

## Preconditions enforced by every script (fatal on failure)
- `reproduce_phase4_scores`: shrunk estimates of `any|q0.75` / `shrink_tau4` equal the stored `p4_pressure_scores_frozen_rules` (max abs diff 0.0 over 1,345 players, opportunity counts equal).
- Investigation only: Phase 4 TRAIN SNR from the stored `p4_definition_comparison` reproduced (max abs diff 2.2e-16).
- `Preservation` guard: official DB and source CSV snapshot unchanged, 56 `phase4_*` report files byte-identical, `phase4_lock_log.json` SHA-256 `cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c` before and after, `phase5_lock_log.json` has 0 events (TEST not opened). `superr.duckdb`, source CSVs and Phase 4 files were not modified; only `p5_*` tables in `exploratory.duckdb` and new `phase5_*` reports were written.

## Independent spot check (separate pandas/numpy implementation)
- Split-half, IPL batter runs, `any|q0.75`, PRE_TEST, odd/even, 6 balls per half: independent groupby/loop r = 0.243385 on 144 players; module r = 0.243385 on 144 players; abs diff 8.3e-17 (Spearman-Brown 0.391). Recorded in `data/reports/phase5_investigation_spotcheck.json`.
- Phase 4 SNR, T20I bowler charged runs, TRAIN, recomputed from raw rows: -0.706396 vs module -0.706396.
- Unit tests also compare `half_stats` with a plain Python loop (including sparse players with uneven halves, agreement to 1e-12) and recover known variance components on simulated ball-level data (tau2 0.04, sigma2 1.0, true ICC 0.8, split-half SB about 0.8).

## What was built
- `app/phase5/`: `pipeline.py` (pre-test study, frozen rules, reproduction), `reliability.py`, `investigation.py`, `pressure_signals.py` (3 bowler-specific candidates, SENSITIVITY_ONLY, TRAIN thresholds), `sensitivity.py`, `stability.py`, `outputs.py`, `spotchecks.py`; `config/phase5_investigation_v1.json` (declared before runs).
- Scripts: `scripts/phase5_investigation.py`, `phase5_sensitivity.py`, `phase5_ranking_stability.py` (seed 20260512, 1000 match-cluster draws, deterministic).
- Reports in `data/reports/`: `phase5_investigation_report.md`, `phase5_sensitivity_report.md`, `phase5_ranking_stability.md`, plus `*_summary.json` and CSV/JSON per table (variance decomposition, split-half, by-opportunity, required-sample projection, pooling, bowler signals, detectability, sensitivity grids, stability cells/contexts/distributions/cross-definition). Tables written to `exploratory.duckdb` with the `p5_` prefix.
- Tests: `tests/test_phase5_investigation.py` (variance components and ICC on synthetic data, split-half vs independent loop, bootstrap determinism, projection hand values, pooling, sensitivity grid composition, compare/Kendall hand values, stability metrics and no-padding, AST checks that chunk 3 code never imports Cricsheet or opens TEST, report labelling).

## Findings the reports state (all from running code)
- Phase 4 noise basis: tau2 not positive in 4 of 4 cells (SNR -0.74 to -0.65), reproduced. The Phase 4 noise divides a per-ball variance by a Kish count of matches, which inflates noise. With independent-ball or match-cluster noise, tau2 is positive in 4 of 4 cells; model-free odd/even split-half Spearman-Brown reliability on PRE_TEST is 0.25 to 0.42 (some intervals reach zero). The size of between-player variance is not identified by these data; the Phase 4 estimator was NOT changed (methodology not locked).
- Primary-definition rankings are unstable: expected overlap of the point Top 10 with a resampled Top 10 is 4.9 to 6.2 of 10 across the four cells; two independent resamples agree on 3.1 to 5.3.
- Definition axis moves the Top 10 strongly (overlap 0 to 8 of 10, median 4); shrinkage and format-weight axes move it less; baseline alternatives least (7 to 10).

## Unresolved issues and gates still failing (documented in all three reports)
- Gates failing (`phase5_publication_gates.json`): `data_weight_gate_passed` (4 of 4 cells THRESHOLD_NOT_VALIDATED), `methodology_validated`, `date_verification` (0 of 42 late T20I matches officially verified). Publication status of every ranking: INTERNAL_EXPERIMENTAL_ONLY.
- Noise model of the shrinkage estimator needs a methodology decision before any lock; bowler-specific pressure signal adoption is undecided; thresholds remain unvalidated working pools; TEST sensitivity is set composition only; a later TEST evaluation is not a pristine hold-out.

## Notes
- No git repository in `d:/Data`, so no commit was made.
- Bootstrap percentile intervals are not bias-corrected and can sit off the point value (stated in the investigation report); one test was relaxed accordingly.
- No finding required a change to user-visible behaviour, so no warning was sent.
