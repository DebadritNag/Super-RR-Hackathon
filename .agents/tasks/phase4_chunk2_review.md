# Phase 4 Chunk 2 review (pass 2): baseline calibration, shrinkage, scoring, lock guard

Reviewed `app/phase4/{shrink,lockguard,scoring}.py`, `phase4_chunk2_verification.md` and the regenerated score CSV. Evidence is present: 391 tests passed, ruff check and format clean, official `superr.duckdb` hash unchanged. Spot-check: read the stored CSV (no suites re-run).

The pass-1 blocking item is fixed. Combined rows now carry opportunities (58 to 217), distinct matches (5 to 28), and effective sample size (2.0 to 19.1), with no nulls. Raw, expected and residual are the weight-averaged per-format values, and a schema test was added. Leakage controls, shrinkage math and test isolation hold: the shrinkage target and tau2 come from TRAIN only with the player's own data removed, role and format cells stay separate, thresholds are fitted on TRAIN (a raise enforces it), par is strictly prior with unavailable rows never flagged, and TEST rows are refused by the lock guard and reachable only through `evaluate_on_test`.

Watch for: non-blocking items below (confirmed, documented).

**Verdict**: APPROVED

## High-level view

Leakage: no future information enters thresholds, par, shrinkage target, or shrinkage choice. The choice uses TRAIN estimates against VALIDATION outcomes and is written before scoring.

Shrinkage: the normal-normal estimator `m = mu_-i + B(r - mu_-i)` matches its documentation. `shrink_none` is zero shrinkage and `shrink_target0` is a sensitivity configuration, and neither can be chosen.

Schema: single-format and combined records both populate the required fields. Combined records leave `posterior_sd`, `data_weight`, `shrinkage_k` and `shrinkage_floor_hit` empty (64 rows), which is acceptable because they are per-format quantities.

<details>
<summary>Issues (3)</summary>

1. **Weak shrinkage choice at grid edge** (confirmed) — `shrink_tau2` was chosen with a difference within about 1 SE of `shrink_eb`, and loss keeps falling toward tau4. The note is added to the scoring report. Chunk 3 should treat `shrink_eb` as primary and report the others as sensitivity.
2. **TRAIN/VALIDATION baseline asymmetry** (confirmed) — TRAIN residuals use leave-player-out expectations and VALIDATION residuals use frozen tables including the player. Documented; carry it into the final limitations.
3. **Bowler signal and eligibility are placeholders** (confirmed) — bowlers use the batter state signals and eligibility is the Phase 3 placeholder, both labelled. Chunk 3 must replace them before any recommendation.

</details>

<details>
<summary>File map</summary>

- `app/phase4/baseline.py`: TRAIN-frozen calibrated baseline.
- `app/phase4/shrink.py`: leave-one-player-out shrinkage, configs, bootstrap, choice.
- `app/phase4/scoring.py`: thresholds, flags, records, combination, TEST route.
- `app/phase4/lockguard.py`: TEST frame guard.

</details>
