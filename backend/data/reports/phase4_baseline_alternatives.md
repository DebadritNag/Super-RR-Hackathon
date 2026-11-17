# Phase 4 baseline alternatives (Stage D)

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking. No final ML model.

Alternatives are fitted on TRAIN only and judged by VALIDATION fit and by agreement of the resulting pressure scores with B0. `B_coarse_L1` drops the wickets-remaining level, `B_coarse_L2` also drops phase, `B_no_format_offset` removes the additive format calibration offset. A season/time offset is not part of B0 and was not tested.

| baseline | format | role | VAL rows | VAL mean residual | VAL RMSE | VAL MAE | pool B0 | pool variant | common | Spearman vs B0 | top-10 overlap | top-10 size | trivial |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | IPL | batter | 16,301 | 0.11 | 1.82 | 1.38 | 132 | 132 | 132 | 1.00 | 10 | 10 | no |
| B0 | T20I | batter | 25,439 | 0.00415 | 1.71 | 1.27 | 243 | 243 | 243 | 1.00 | 10 | 10 | no |
| B0 | IPL | bowler | 16,992 | 0.11 | 1.79 | 1.35 | 80 | 80 | 80 | 1.00 | 10 | 10 | no |
| B0 | T20I | bowler | 26,384 | 0.00548 | 1.68 | 1.24 | 141 | 141 | 141 | 1.00 | 10 | 10 | no |
| B_coarse_L1 | IPL | batter | 16,301 | 0.11 | 1.82 | 1.39 | 132 | 132 | 132 | 1.00 | 9 | 10 | no |
| B_coarse_L1 | T20I | batter | 25,439 | 0.00415 | 1.71 | 1.27 | 243 | 243 | 243 | 1.00 | 10 | 10 | no |
| B_coarse_L1 | IPL | bowler | 16,992 | 0.11 | 1.80 | 1.35 | 80 | 80 | 80 | 1.00 | 9 | 10 | no |
| B_coarse_L1 | T20I | bowler | 26,384 | 0.00558 | 1.68 | 1.24 | 141 | 141 | 141 | 0.99 | 9 | 10 | no |
| B_coarse_L2 | IPL | batter | 16,301 | 0.11 | 1.83 | 1.39 | 132 | 132 | 132 | 0.97 | 8 | 10 | no |
| B_coarse_L2 | T20I | batter | 25,439 | 0.00298 | 1.71 | 1.28 | 243 | 243 | 243 | 0.98 | 10 | 10 | no |
| B_coarse_L2 | IPL | bowler | 16,992 | 0.11 | 1.80 | 1.35 | 80 | 80 | 80 | 0.96 | 8 | 10 | no |
| B_coarse_L2 | T20I | bowler | 26,384 | 0.00451 | 1.69 | 1.25 | 141 | 141 | 141 | 0.96 | 7 | 10 | no |
| B_no_format_offset | IPL | batter | 16,301 | 0.11 | 1.82 | 1.38 | 132 | 132 | 132 | 1.00 | 10 | 10 | no |
| B_no_format_offset | T20I | batter | 25,439 | 0.00518 | 1.71 | 1.27 | 243 | 243 | 243 | 1.00 | 10 | 10 | no |
| B_no_format_offset | IPL | bowler | 16,992 | 0.11 | 1.79 | 1.35 | 80 | 80 | 80 | 1.00 | 10 | 10 | no |
| B_no_format_offset | T20I | bowler | 26,384 | 0.00652 | 1.68 | 1.24 | 141 | 141 | 141 | 1.00 | 10 | 10 | no |

