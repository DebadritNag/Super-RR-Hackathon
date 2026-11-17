# Phase 4 format weight sensitivity

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking. No final ML model.

70:30 (IPL:T20I) remains the PROVISIONAL default (`PROVISIONAL_NOT_VALIDATED`). It is not described as optimised or validated, and no weighting is selected here. The same frozen eligibility rules apply to all eight configurations. Definition `any|q0.75` and the frozen shrinkage are held fixed; definition sensitivity is reported separately in `phase4_definition_comparison.md` and is not crossed with weights.

Combined pool: players eligible in BOTH formats. A player in one format only is never zero-filled into a combination; single-format scores are reported separately below.

## Eight configurations (reference = w70_30)
| role | config | IPL w | T20I w | pool | top-10 overlap vs 70:30 | top-10 size | trivial full pool | Spearman vs 70:30 | mean |rank change| | max |rank change| | boot exp. overlap | boot mean Spearman | IPL label | T20I label |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| batter | w100_0 | 1.00 | 0.00 | 48 | 9 | 10 | no | 0.95 | 3.00 | 13 | 6.28 | 0.74 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w85_15 | 0.85 | 0.15 | 48 | 9 | 10 | no | 0.98 | 2.12 | 9 | 5.86 | 0.73 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w80_20 | 0.80 | 0.20 | 48 | 9 | 10 | no | 0.99 | 1.38 | 5 | 5.82 | 0.73 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w70_30 | 0.70 | 0.30 | 48 | 10 | 10 | no | 1.00 | 0.00 | 0 | 5.78 | 0.73 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w60_40 | 0.60 | 0.40 | 48 | 8 | 10 | no | 0.99 | 1.58 | 7 | 5.71 | 0.72 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w55_45 | 0.55 | 0.45 | 48 | 8 | 10 | no | 0.97 | 2.38 | 10 | 5.62 | 0.72 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w50_50 | 0.50 | 0.50 | 48 | 7 | 10 | no | 0.95 | 3.21 | 12 | 5.69 | 0.71 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| batter | w0_100 | 0.00 | 1.00 | 48 | 3 | 10 | no | 0.46 | 10.58 | 37 | 5.88 | 0.74 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w100_0 | 1.00 | 0.00 | 39 | 9 | 10 | no | 0.92 | 3.18 | 14 | 6.63 | 0.77 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w85_15 | 0.85 | 0.15 | 39 | 10 | 10 | no | 0.97 | 1.90 | 8 | 6.87 | 0.79 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w80_20 | 0.80 | 0.20 | 39 | 10 | 10 | no | 0.99 | 1.33 | 5 | 6.95 | 0.79 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w70_30 | 0.70 | 0.30 | 39 | 10 | 10 | no | 1.00 | 0.00 | 0 | 7.09 | 0.81 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w60_40 | 0.60 | 0.40 | 39 | 9 | 10 | no | 0.99 | 1.33 | 5 | 7.17 | 0.82 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w55_45 | 0.55 | 0.45 | 39 | 9 | 10 | no | 0.98 | 1.79 | 6 | 7.18 | 0.83 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w50_50 | 0.50 | 0.50 | 39 | 9 | 10 | no | 0.96 | 2.36 | 8 | 7.13 | 0.83 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |
| bowler | w0_100 | 0.00 | 1.00 | 39 | 5 | 10 | no | 0.61 | 7.95 | 28 | 6.88 | 0.79 | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | ELIGIBLE_WORKING_POOL_NOT_VALIDATED |

Top-10 overlap is only meaningful when the pool exceeds ten players; a pool of ten or fewer is marked trivial.

## Single-format ranking stability (separate eligibility pools)
| role | scope | label | threshold | pool | exp. top-10 overlap | mean Spearman | trivial full pool |
|---|---|---|---|---|---|---|---|
| batter | IPL_ONLY | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 20 | 132 | 5.24 | 0.80 | no |
| batter | T20I_ONLY | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 16 | 243 | 4.88 | 0.82 | no |
| bowler | IPL_ONLY | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 49 | 80 | 6.20 | 0.76 | no |
| bowler | T20I_ONLY | ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 29 | 141 | 5.53 | 0.77 | no |


## Pairwise Spearman between configurations (point estimates, combined pool)

### batter
| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.99 | 0.98 | 0.95 | 0.90 | 0.87 | 0.83 | 0.24 |
| w85_15 | 0.99 | 1.00 | 0.99 | 0.98 | 0.94 | 0.91 | 0.88 | 0.32 |
| w80_20 | 0.98 | 0.99 | 1.00 | 0.99 | 0.96 | 0.94 | 0.92 | 0.38 |
| w70_30 | 0.95 | 0.98 | 0.99 | 1.00 | 0.99 | 0.97 | 0.95 | 0.46 |
| w60_40 | 0.90 | 0.94 | 0.96 | 0.99 | 1.00 | 0.99 | 0.98 | 0.56 |
| w55_45 | 0.87 | 0.91 | 0.94 | 0.97 | 0.99 | 1.00 | 0.99 | 0.61 |
| w50_50 | 0.83 | 0.88 | 0.92 | 0.95 | 0.98 | 0.99 | 1.00 | 0.66 |
| w0_100 | 0.24 | 0.32 | 0.38 | 0.46 | 0.56 | 0.61 | 0.66 | 1.00 |


### bowler
| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.98 | 0.96 | 0.92 | 0.86 | 0.83 | 0.79 | 0.30 |
| w85_15 | 0.98 | 1.00 | 1.00 | 0.97 | 0.93 | 0.91 | 0.88 | 0.44 |
| w80_20 | 0.96 | 1.00 | 1.00 | 0.99 | 0.95 | 0.94 | 0.91 | 0.49 |
| w70_30 | 0.92 | 0.97 | 0.99 | 1.00 | 0.99 | 0.98 | 0.96 | 0.61 |
| w60_40 | 0.86 | 0.93 | 0.95 | 0.99 | 1.00 | 1.00 | 0.99 | 0.71 |
| w55_45 | 0.83 | 0.91 | 0.94 | 0.98 | 1.00 | 1.00 | 1.00 | 0.74 |
| w50_50 | 0.79 | 0.88 | 0.91 | 0.96 | 0.99 | 1.00 | 1.00 | 0.78 |
| w0_100 | 0.30 | 0.44 | 0.49 | 0.61 | 0.71 | 0.74 | 0.78 | 1.00 |


## Limitations
- With a small combined pool every ranking statistic is dominated by few players.
- Per-format ranking scores use the primary stream only (runs for batters, runs conceded for bowlers); wickets and dismissals are in the Stage C records but not in this score.
- Weights act on shrunk per-format estimates; no weighting is validated.
