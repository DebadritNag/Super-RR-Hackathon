# Phase 4 shrinkage sensitivity

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking. No final ML model.

Definition `any|q0.75`. Chosen configuration (TRAIN estimates against VALIDATION outcomes, written before any scoring): **`shrink_tau4`**. Rule: non-default only if paired loss difference < -1 bootstrap SE; none/target0 never chosen. TEST outcomes: not used.

## Estimator and assumptions
Phase 4 shrinkage of player pressure residuals towards the pooled mean of OTHER players.

Estimator (one cell = role x format x stream; batter and bowler populations and the IPL and T20I
populations are never mixed; formats are combined only after shrinkage):

    m_i = mu_{-i} + B_i (r_i - mu_{-i}),   B_i = n_eff_i / (n_eff_i + k)

* r_i: player i's mean residual in the scoring window; n_eff_i: Kish effective number of balls
  over the player's matches.
* mu_{-i}: pooled (ball-weighted) mean residual of all other players, from TRAIN rows only, so the
  player's own deliveries never enter the target (leave-one-player-out).
* k = sigma2_within / tau2 from the method of moments in ``analytics.shrinkage.k_from_children``,
  with tau2 floored at ``floor * sigma2_within`` (so k <= 1 / floor), fitted on TRAIN only.

Assumptions: residual means are approximately normal, matches are independent clusters, players
are exchangeable within a cell, noise is homoscedastic after n_eff, tau2 is constant over the
window, tau2 estimation error is not propagated into intervals. A floor hit means the data show
less between-player spread than the floor, so shrinkage is weaker than the data support.

Configurations: ``shrink_none`` (zero shrinkage, sensitivity), ``shrink_eb`` (fitted, default),
``shrink_tau0.5`` / ``shrink_tau2`` / ``shrink_tau4`` (tau2 multiplied after the floor),
``shrink_floor0.001`` (floor 0.001), ``shrink_target0`` (target 0, sensitivity).
Parameters are chosen on TRAIN and VALIDATION only; TEST outcomes are never an input.

Zero shrinkage (`shrink_none`) and target 0 (`shrink_target0`) are retained as sensitivity configurations and cannot be chosen as primary.

## Pooled VALIDATION loss
| config | loss | diff vs shrink_eb | bootstrap SE | choosable |
|---|---|---|---|---|
| shrink_none | 0.15 | 0.08 | 0.02 | no |
| shrink_eb | 0.07 | 0.00 | 0.00 | yes |
| shrink_tau0.5 | 0.07 | 0.00 | 0.00 | yes |
| shrink_tau2 | 0.07 | -0.00106 | 0.000196 | yes |
| shrink_tau4 | 0.07 | -0.00252 | 0.000524 | yes |
| shrink_floor0.001 | 0.07 | 0.00123 | 0.000202 | yes |
| shrink_target0 | 0.07 | 0.00058 | 0.000486 | no |


## Per cell and configuration (pool = frozen analysis eligibility; other factors fixed)
| format | role | config | k | floor hit | pool | median B (pool) | mean |shift| from raw | Spearman vs eb | top-10 overlap vs eb | trivial full pool | median interval width | exp. top-10 overlap (boot) | VAL loss | diff vs eb | SE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | shrink_none | 0.00 | no | 132 | 1.00 | 5.21e-19 | 0.96 | 3 | no | 0.77 | 4.79 | 0.22 | 0.07 | 0.03 |
| IPL | batter | shrink_eb | 100.00 | yes | 132 | 0.05 | 0.26 | 1.00 | 10 | no | 0.05 | 5.07 | 0.15 | 0.00 | 0.00 |
| IPL | batter | shrink_tau0.5 | 100.00 | yes | 132 | 0.05 | 0.26 | 1.00 | 10 | no | 0.05 | 5.07 | 0.15 | 0.00 | 0.00 |
| IPL | batter | shrink_tau2 | 50.00 | yes | 132 | 0.10 | 0.24 | 1.00 | 10 | no | 0.09 | 5.20 | 0.15 | -0.00294 | 0.000864 |
| IPL | batter | shrink_tau4 | 25.00 | yes | 132 | 0.19 | 0.22 | 1.00 | 9 | no | 0.15 | 5.24 | 0.14 | -0.00732 | 0.00231 |
| IPL | batter | shrink_floor0.001 | 1000.00 | yes | 132 | 0.0057 | 0.27 | 0.19 | 3 | no | 0.00516 | 4.11 | 0.16 | 0.00324 | 0.00089 |
| IPL | batter | shrink_target0 | 100.00 | yes | 132 | 0.05 | 0.26 | 1.00 | 10 | no | 0.05 | 5.36 | 0.15 | 0.000116 | 0.000936 |
| T20I | batter | shrink_none | 0.00 | no | 243 | 1.00 | 3.15e-18 | 0.95 | 4 | no | 0.83 | 5.55 | 0.56 | 0.40 | 0.13 |
| T20I | batter | shrink_eb | 100.00 | yes | 243 | 0.04 | 0.25 | 1.00 | 10 | no | 0.04 | 4.69 | 0.15 | 0.00 | 0.00 |
| T20I | batter | shrink_tau0.5 | 100.00 | yes | 243 | 0.04 | 0.25 | 1.00 | 10 | no | 0.04 | 4.69 | 0.15 | 0.00 | 0.00 |
| T20I | batter | shrink_tau2 | 50.00 | yes | 243 | 0.07 | 0.24 | 1.00 | 10 | no | 0.07 | 4.80 | 0.15 | -0.00291 | 0.000797 |
| T20I | batter | shrink_tau4 | 25.00 | yes | 243 | 0.13 | 0.22 | 1.00 | 9 | no | 0.12 | 4.88 | 0.15 | -0.00702 | 0.00218 |
| T20I | batter | shrink_floor0.001 | 1000.00 | yes | 243 | 0.00377 | 0.26 | 0.41 | 3 | no | 0.00373 | 3.82 | 0.16 | 0.00328 | 0.0008 |
| T20I | batter | shrink_target0 | 100.00 | yes | 243 | 0.04 | 0.25 | 1.00 | 10 | no | 0.03 | 4.87 | 0.16 | 0.00118 | 0.00153 |
| IPL | bowler | shrink_none | 0.00 | no | 80 | 1.00 | 1.53e-18 | 0.96 | 9 | no | 0.62 | 6.24 | 0.20 | 0.04 | 0.02 |
| IPL | bowler | shrink_eb | 100.00 | yes | 80 | 0.09 | 0.15 | 1.00 | 10 | no | 0.06 | 6.03 | 0.16 | 0.00 | 0.00 |
| IPL | bowler | shrink_tau0.5 | 100.00 | yes | 80 | 0.09 | 0.15 | 1.00 | 10 | no | 0.06 | 6.03 | 0.16 | 0.00 | 0.00 |
| IPL | bowler | shrink_tau2 | 50.00 | yes | 80 | 0.17 | 0.14 | 1.00 | 10 | no | 0.11 | 6.17 | 0.16 | -0.00138 | 0.00108 |
| IPL | bowler | shrink_tau4 | 25.00 | yes | 80 | 0.29 | 0.12 | 1.00 | 9 | no | 0.18 | 6.20 | 0.16 | -0.00284 | 0.00282 |
| IPL | bowler | shrink_floor0.001 | 1000.00 | yes | 80 | 0.00998 | 0.17 | 0.30 | 6 | no | 0.00691 | 4.99 | 0.16 | 0.00187 | 0.00116 |
| IPL | bowler | shrink_target0 | 100.00 | yes | 80 | 0.09 | 0.15 | 1.00 | 9 | no | 0.06 | 6.22 | 0.16 | 0.000102 | 0.000808 |
| T20I | bowler | shrink_none | 0.00 | no | 141 | 1.00 | 2.75e-18 | 0.94 | 4 | no | 0.70 | 5.05 | 0.17 | 0.07 | 0.02 |
| T20I | bowler | shrink_eb | 100.00 | yes | 141 | 0.07 | 0.18 | 1.00 | 10 | no | 0.05 | 5.44 | 0.10 | 0.00 | 0.00 |
| T20I | bowler | shrink_tau0.5 | 100.00 | yes | 141 | 0.07 | 0.18 | 1.00 | 10 | no | 0.05 | 5.44 | 0.10 | 0.00 | 0.00 |
| T20I | bowler | shrink_tau2 | 50.00 | yes | 141 | 0.12 | 0.17 | 1.00 | 9 | no | 0.08 | 5.52 | 0.10 | -0.00135 | 0.00054 |
| T20I | bowler | shrink_tau4 | 25.00 | yes | 141 | 0.22 | 0.16 | 1.00 | 9 | no | 0.14 | 5.53 | 0.10 | -0.00318 | 0.00146 |
| T20I | bowler | shrink_floor0.001 | 1000.00 | yes | 141 | 0.00708 | 0.20 | 0.57 | 5 | no | 0.00499 | 4.83 | 0.11 | 0.00158 | 0.000548 |
| T20I | bowler | shrink_target0 | 100.00 | yes | 141 | 0.07 | 0.19 | 1.00 | 10 | no | 0.05 | 5.61 | 0.11 | 0.00209 | 0.00146 |


## Limitations
- Intervals hold k and the pooled target fixed; tau2 estimation error is not propagated.
- The pooled target uses TRAIN rows only; the PRE_TEST-window target (`shrink_mu_window`) sensitivity was not run.
- A tau2 at the floor means stronger shrinkage than a larger tau2 would give; compare `shrink_floor0.001` and `shrink_tau4`.
