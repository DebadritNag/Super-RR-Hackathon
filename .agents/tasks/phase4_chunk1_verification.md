# Phase 4 Chunk 1 verification

Environment: PowerShell, `$env:PYTHONUTF8=1`, Python 3.11, cwd `d:/Data/backend`.

## What was built
- `app/phase4/`: `constants.py`, `config.py`, `store.py` (p4_ tables only, refuses the official DB), `split.py` (Split, assign/attach period, integrity check, rolling folds, TestLock, LockedFrame, SplitFrames, write_frozen_choices, evaluate_on_test), `data.py`, `par.py` (strictly prior par, flag `par_unavailable_insufficient_prior`, descriptive-only LOMO, LeakageGuard, coverage), `phases.py` (boundary table, shortened-innings report, label checks, revision timing, DLS summary).
- `config/phase4_split_v1.json` (boundaries TRAIN <= 2024-12-31, VALIDATION 2025, TEST >= 2026-01-01; fixed before evaluation).
- `scripts/phase4_split.py` writes `data/reports/phase4_split_manifest.json`, `phase4_phase_boundaries.md`, `phase4_chunk1_preservation.json`, appends a generated section 11 to `phase4_temporal_validation_plan.md`, and writes `p4_match_period`, `p4_par_prior`, `p4_phase_boundaries` to `exploratory.duckdb`.
- Tests: `tests/test_phase4_split.py`, `test_phase4_par.py`, `test_phase4_phases.py`, helper `tests/phase4_helpers.py` (53 new tests).

## Commands and results
| command | result |
|---|---|
| `python scripts/phase4_split.py` | matches=867 rows=200999 par_unavailable_rows=7692; official data unchanged: True |
| `python -m pytest -q` | 362 passed (309 existing + 53 new), 2 warnings (division by zero inside the existing LOMO code on a one-match synthetic format) |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 116 files already formatted |

## Real-data findings (from the script output)
- Matches: IPL 219 / 74 / 74 and T20I 278 / 122 / 70 (TRAIN / VALIDATION / TEST), OTHER_T20 15 / 15 / 0; no match in two periods; 0 rows whose period differs from the date rule; periods strictly ordered.
- Strictly prior par: 7,692 innings-1 rows unavailable (IPL 3,737 rows in 30 matches, last 2022-04-18; T20I 3,955 rows in 33 matches, last 2022-07-18), all in TRAIN, none in VALIDATION or TEST. `par_runs_prior` from `app/phase4/par.py` equals the existing column on all 200,999 rows (identical NULL pattern, max abs difference 0.0). Sensitivity unavailable rows: min_prior 15 -> 3,733, 30 -> 7,692, 60 -> 15,491.
- Shortened innings: 50 regulation innings (25 in innings 1, 25 in innings 2) in 34 matches, 3,404 deliveries; limits present 30, 42, 48, 54, 60, 66, 72, 78, 84, 90, 102, 108, 114 (plus 120). Limit constant within every innings. By limit source: REVISED_FIELD 48, CARRIED_FROM_FIRST_INNINGS_UNVERIFIED 2. This reconciles the "48" in the pressure rules note (it counts only the revised-field innings). All 3,404 rows are DLS-excluded; 1,775 chase rows would otherwise be eligible and are masked out; 0 rows deleted; no resources imputed.
- Label checks: stored phase equals the function of (B, L); unchanged when the last 30 percent of each innings is dropped; independent of row order. 1,154 shortened deliveries would take a different label under the original limit of 120 (upper bound on revision-timing sensitivity, all excluded from primary scoring).
- Meaningful split: population level SUPPORTED in every format/period. Player level (>= 15 players with >= 36 pressure balls) SUPPORTED only in IPL bowler TRAIN (27) and T20I bowler TRAIN (20); IPL batter TRAIN is 17 (supported), T20I batter TRAIN is 15 (supported); every VALIDATION and TEST player-level cell is INSUFFICIENT_FOR_PLAYER_LEVEL_TEST.

## Independent spot checks
1. Strictly prior par from raw `updated_ball_by_ball.csv` + `matches.csv` + `competitions.csv` (pandas, a different code path: legal-ball cumulative runs, complete 120-ball T20I first innings with date strictly earlier). T20I matches 36199, 36200, 36201 (VALIDATION), par after 60 balls: raw 78.9167 / 79.0217 / 79.0324 with 276 / 277 / 278 prior innings; stored `p4_par_prior` 78.916667 / 79.021661 / 79.032374 with the same counts. Match.
2. Period boundaries and match counts: recomputed from the state frame (IPL 219/74/74, T20I 278/122/70), equal to the counts in the design plan.
3. Hash check: `superr.duckdb` SHA-256 CB4077EE...391D equals `phase4_hash_before.txt`; `ball_by_ball.csv`, `matches.csv`, `updated_ball_by_ball.csv` hashes equal the recorded values; the script's own before/after snapshot (official tables, CSVs, Cricsheet manifests) reports no differences.

## Notes
- The repository is not a git repository, so no commit was made.
- Plan section 3 counts in `phase4_temporal_validation_plan.md` were approximate; the generated section 11 supersedes them (for example IPL TRAIN pressure deliveries 2,512 vs 2,545 approximate).
- `config/pressure_rules_v1.json` still carries the "48 shortened innings" note; left unchanged (no code reads it) and reconciled in `phase4_phase_boundaries.md`.
