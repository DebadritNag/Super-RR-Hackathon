# Phase 3 prep, Chunk A verification (pre-delivery match-state engine)

Status: EXPLORATORY_NOT_VALIDATED. No ranking, no ML, no validated pressure score. The workspace is not a git repository, so nothing was committed.

## Files added
- `backend/app/analytics/pressure_engine.py` (state engine, build checks), `cricket_calculations.py` (legal ball, faced, CRR, RRR, resource proxy), `phase_engine.py` (ball-based phase bounds)
- `backend/app/services/pressure_service.py` (writes the separate store; refuses the official DB path)
- `backend/config/pressure_rules_v1.json` (21 parameters with value, basis, sensitivity; restricted-innings reason codes)
- `backend/scripts/build_pre_delivery_state.py`, `backend/scripts/spot_check_pre_delivery_state.py`
- `backend/tests/test_pressure_state.py` (64 tests), `test_pressure_leakage.py` (17 tests), `pressure_helpers.py`
- Outputs: `backend/data/database/exploratory.duckdb` (table `exp_pre_delivery_state`, 200,999 rows, 89 columns), `backend/data/reports/pre_delivery_state_manifest.json`, `pre_delivery_state_spot_check.json`

Official `superr.duckdb` is opened only with `connect(..., read_only=True)` inside `app/analytics`; the only write path is in `app/services`. Engine modules contain no SQL write and no Cricsheet path (tests assert both). Cricsheet-derived values (3 confirmed Super Over match ids, 10 disagreeing innings) are read from the Phase 2.5 JSON reports only, and the confirmed ids are cross-checked against the config at build time.

## Commands run and results
| Command | Result |
|---|---|
| `python scripts/build_pre_delivery_state.py` | rows=200999, regulation_rows=200961, restricted=38, official data unchanged: True |
| `python scripts/spot_check_pre_delivery_state.py` | PASS (details below) |
| `python -m pytest tests/test_pressure_state.py tests/test_pressure_leakage.py tests/test_no_contamination.py -q` | 92 passed |
| `python -m pytest -q` (full suite, run once at the end) | 223 passed (142 existing + 81 new) |
| `python -m ruff check .` / `python -m ruff format --check .` | All checks passed / 75 files already formatted |

## Build checks (from the manifest, actual DuckDB figures)
- Rows by innings 1/2/3/4: 105,727 / 95,234 / 25 / 13. Regulation innings: 1,712. Matches: 867 (OTHER_T20: 30 matches, 6,985 rows, kept with state columns and flagged `format_out_of_scope`).
- Restricted (RULE_INNINGS_3_4, source rows preserved, state labels NULL): 38 rows. CONFIRMED_SUPER_OVER_BY_CRICSHEET: matches 34429, 45512, 50359, 16 rows. UNVERIFIED_INNINGS_ROLE: matches 40725, 48027, 48029, 22 rows.
- Legal balls: 192,444 rows (Penalty counted 0). `other` rows 264, flagged `den_extras_label_unverified` (265 with Penalty), never merged into Overstep. Unknown extras categories: 0. `extras_type = 'None'` with nonzero extras runs: 2 rows, kept in the total and flagged.
- CRR NULL on exactly the 1,830 regulation rows with zero legal balls before.
- Runs required <= 0: 12 rows, all match 48610 innings 2 (RRR NULL, `req_nonpositive_flag`).
- Targets: 822 innings `INNINGS1_TOTAL_PLUS_1`, 23 `REVISED_TARGET`, none without target. `target_basis_unverified`: 6 innings (primary chase population excludes them in later chunks).
- DLS: 34 matches with any revised field (25 first-innings, 25 second-innings, 23 revised targets, reconciled). `dls_flag` innings 25 + 23 = 48; `innings_limit_unstated` 2 (matches 16753, 19959, limit carried and flagged); `dls_exclude_primary` 50 innings; `resource_status = NOT_RECONSTRUCTED` on 3,404 rows. Residual finding 4 applied: `post_innings_ended_short_of_stated_limit` is true for 8 innings 1 (15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408) and 1 innings 2; `post_dls_state_reliable` true 39, false 11 (replaces the superseded 48).
- Wicket-flag disagreement: 12 rows `dismissed_player_id` set with `is_wicket` false, 1 `is_wicket` true without dismissed player; 739 later rows carry `state_wicket_flag_disagreement`, with `wickets_remaining_alt` as the sensitivity.
- Regulation phase rows: powerplay 63,366, middle 92,596, death 44,999. Rows with 90+ legal balls bowled: 44,452 (matches the spec figure); death label restricted to L=120 innings: 44,285.
- Distinct limits (balls, innings): 30:4, 42:3, 48:4, 54:4, 60:3, 66:6, 72:2, 78:2, 84:4, 90:7, 102:4, 108:2, 114:5, 120:1,662. The spec lists 66:4 and 120:1,664 because it counts the two `innings_limit_unstated` innings as 120; the engine records them at the carried 66 with the `CARRIED_FROM_FIRST_INNINGS_UNVERIFIED` flag, as spec 7.6 requires.
- Manifest: official DB sha256 `cb4077ee...a391d`, table content hashes for deliveries, matches, competitions, config hashes, engine sha256 `bfbe885f...5ae2f`, `cricsheet_files_opened: 0`, preservation `official_data_unchanged: true` (CSV, table, DB-file and Cricsheet-directory snapshots before and after).

## Independent spot-check (stdlib `csv` on updated_ball_by_ball.csv and matches.csv, no engine, pandas or DuckDB)
- All 200,999 rows: runs-before, wickets-before and legal-balls-before recomputed independently: 0 mismatches.
- 845 chase targets: innings-1 total + 1 from the raw CSV, or `revised_target` from matches.csv for 23 DLS chases: 0 mismatches.
- Hand recomputation at balls 30, 60 and 100 of innings 2 of matches 13511, 13512, 13513 (runs required, legal balls remaining, RRR, wickets remaining): all 9 match. Example: match 13511 ball 100, 4 runs required, 21 balls remaining, RRR 1.142857, 9 wickets remaining.
- Death-label rows (L=120): independent 44,285 equals store 44,285.

## Test coverage map
- State, legal balls and extras: hand-checked innings, wide/Overstep/other/byes/legbyes/Penalty/None parametrised, unknown category kept, NULL runs rejected (never zero), over index by legal balls.
- Runs required, revised targets, DLS: chase table, Req <= 0, no innings 1, target basis, revised limit and target, unstated limit, ended-short, all-out, resource NOT_RECONSTRUCTED, 14-row phase table.
- First innings versus chase: innings-1 target columns NULL; chase columns by hand.
- Super Over: reason codes, preserved rows, NULL state, config ids; real data reproduces both id sets.
- Leakage: truncation at every k (synthetic) and at several cut points over a real-match sample (more than 100 innings cuts), innings-2 target independent of later innings-2 rows, future-row mutation, mutation of every outcome column of row k, mutation of row k's `extras_type` (the required mutation test), result-column mutation, static scans for forbidden columns, Cricsheet paths and SQL writes.
- Store: refuses the official path, round trip in a separate file, a full real build to a temporary store leaves official data hashes unchanged.

## Not in this chunk
Par curves, expectation cells, rank percentiles, distributions, baseline, eligibility, format sensitivity and the restriction applier belong to later chunks. State columns for them are not present. Nothing here is a pressure score, a ranking or a model.
