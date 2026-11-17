# Phase 3 prep final verification (raw outputs)
Run from d:/Data/backend, Python 3.11, PYTHONUTF8=1. Review file phase3prep_review.json absent at start; full verification performed.

## 1. python scripts/run_phase3_prep.py (exit 0), tail
```
{'match_id': 13513, 'ball': 100, 'runs_required': 71, 'legal_balls_remaining': 27, 'rrr': 15.777777777777779, 'wickets_remaining': 5, 'matches_store': True}
PASS
== run_pressure_distributions
candidates=384 spot_check_all_match=True official_unchanged=True
== run_baseline_exploration
calibration_identity_holds=True reproducible=True official_unchanged=True
== run_pressure_eligibility
chase|q0.75: done
inn1|q0.75: done
any|q0.75: done
chase|q0.9: done
inn1|q0.9: done
any|q0.9: done
chase|q0.95: done
inn1|q0.95: done
any|q0.95: done
definitions=9 selected=chase|q0.9 viable=3 official_unchanged=True
== run_pressure_format_sensitivity
combined populations: batter=8, bowler=6; official_unchanged=True
== apply_dq_restrictions
rules=26 features=99 ok=True official_unchanged=True
official_unchanged=True; steps={'build_pre_delivery_state': 0, 'spot_check_pre_delivery_state': 0, 'run_pressure_distributions': 0, 'run_baseline_exploration': 0, 'run_pressure_eligibility': 0, 'run_pressure_format_sensitivity': 0, 'apply_dq_restrictions': 0}; deliverables_ok=True
```

## 2. python -m pytest -q
```
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 93%]
.....................                                                    [100%]
309 passed in 231.76s (0:03:51)
```

## 3. python -m ruff check .
```
All checks passed!
```

## 4. python -m ruff format --check .
```
101 files already formatted
```

## 5. Independent spot-checks (csv module recomputation from d:/Data/updated_ball_by_ball.csv and matches.csv, script _spot.py)
```
non-DLS chase innings 820
chase (30063, 2) ball 106 indep {'rr': 75, 'lb': 20, 'wr': 6} rrr 22.5 db (75, 20, 6, 203, 22.5) OK
chase (17559, 2) ball 69 indep {'rr': 137, 'lb': 52, 'wr': 7} rrr 15.807692307692307 db (137, 52, 7, 73, 15.807692307692307) OK
chase (31711, 2) ball 13 indep {'rr': 165, 'lb': 108, 'wr': 9} rrr 9.166666666666666 db (165, 108, 9, 14, 9.166666666666666) OK
chase (47260, 2) ball 47 indep {'rr': 140, 'lb': 78, 'wr': 5} rrr 10.76923076923077 db (140, 78, 5, 41, 10.76923076923077) OK
chase (14131, 2) ball 75 indep {'rr': 104, 'lb': 49, 'wr': 7} rrr 12.73469387755102 db (104, 49, 7, 84, 12.73469387755102) OK
chase (14157, 2) ball 15 indep {'rr': 164, 'lb': 107, 'wr': 9} rrr 9.19626168224299 db (164, 107, 9, 15, 9.19626168224299) OK
target check [(40708, 201, 201), (20213, 236, 236), (14120, 190, 190), (15408, 180, 180), (36562, 180, 180), (34427, 214, 214), (14154, 210, 210), (20241, 145, 145)] True
DLS [(13612, 143, (143, 'REVISED_TARGET')), (16754, 56, (56, 'REVISED_TARGET')), (17395, 91, (91, 'REVISED_TARGET')), (17765, 130, (130, 'REVISED_TARGET')), (21586, 171, (171, 'REVISED_TARGET')), (21070, 104, (104, 'REVISED_TARGET')), (21071, 203, (203, 'REVISED_TARGET')), (28046, 152, (152, 'REVISED_TARGET')), (29984, 126, (126, 'REVISED_TARGET')), (37354, 94, (94, 'REVISED_TARGET'))]
inn1 legal-ball totals mismatches 0 of 25
row count csv 200999 db state rows (200999,)
['match_id', 'innings_number', 'innings_ball_num', 'wbin', 'par_runs_lomo', 'par_deviation_lomo', 'par_runs_prior', 'par_deviation_prior', 'exp_remaining', 'exp_cell_level_used', 'shrinkage_floor_hit', 'req_to_exp', 'proj_total_gap_lomo', 'bowl_signal_B', 'rank_bat_pressure_rel', 'bowl_rel_A', 'rank_bowl_rel_B', 'bowl_B_early_flag', 'state_version', 'status']
SUMMARY 8 / 8
```
Additional independent check: innings>=3 rows from the raw CSV = 25 (innings 3) + 13 (innings 4), matches 34429, 40725, 45512, 48027, 48029, 50359; state table: CONFIRMED_SUPER_OVER_BY_CRICSHEET 16 rows/3 matches, UNVERIFIED_INNINGS_ROLE 22 rows/3 matches (total 38). Residual finding 4: 8 DLS innings-1 ended short of limit (15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408) match the finding list.

## 6. Preservation
```
Source CSV SHA-256 (all 12 files) equal to phase25_preservation.json before-values: True for every file.
superr.duckdb sha256 cb4077eebbd811534f9b1ee434bd92a385849e5b99a0955d48fb2dc5164a391d == Phase 2.5 recorded value (file byte-identical).
phase3_preservation.json: official_unchanged=true, diff={}, tables before==after, csv before==after.
Get-FileHash comparison of all data/**/*.csv + superr.duckdb before vs after the final run: no differences.
Exploratory store is separate: data/database/exploratory.duckdb (tables exp_pre_delivery_state 200,999 rows, exp_pre_delivery_state_manifest, exp_pressure_signals).
```
