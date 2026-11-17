# Phase 5 final verification

Status: EXPERIMENTAL_NOT_VALIDATED. No official ranking, no official model, TEST not opened.
`phase5_review.json` did not exist at the start of this step, so the full verification was run.

## 1. Orchestrator run on real data
- Command: `python scripts/run_phase5.py --compare-hashes` (PYTHONUTF8=1). Log: `d:/Data/.agents/tasks/phase5_final_run.log`.
- `--create-lock` was NOT passed. The orchestrator does not create a lock implicitly. A lock manifest (`phase5_methodology_lock.json`, label EXPERIMENTAL_LOCK, validated false) already existed from chunk 5, so the refit step ran against it. No new lock was written; the pre-lock checklist step printed "no lock written".
- All 15 steps exited 0. Output: `compare-hashes: 0 differing files`, `missing deliverables: []`, `preservation: True`.

## 2. Tests and lint
- `python -m pytest -q`: **793 passed**, 3 warnings (a numpy divide RuntimeWarning in `pressure_features.py`, already present before Phase 5), 0 failed. That is the 509 earlier tests plus 284 new ones.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 243 files already formatted.

## 3. Outputs present
All `phase5_*` reports exist under `d:/Data/backend/data/reports`. That covers the nine required markdown reports (investigation, t20i_date_verification, classification_migration, sensitivity, ranking_stability, publication_gates, methodology_lock_and_refit, dynamic_ranking_architecture, user_summary) plus `phase5_unresolved_issues.md`. It also covers the CSV/JSON companions, `phase5_t20i_official_verification_template.csv`, the context coverage table (`phase5_context_coverage.csv/json`, 3,888 combinations), the lock manifest, the pre-lock checklist, `phase5_test_set_manifest.json` and `phase5_output_hashes.json`. The refit artifacts are in exploratory.duckdb: `p5_refit_trainval_v1_{scores,manifest,thresholds,baseline_calibration,comparison}`.

## 4. Preservation (re-hashed against `phase5_prerun_hashes.json`)
- I checked 71 files independently with SHA-256.
- `superr.duckdb`, every source CSV, the config CSVs and every `phase4_*` report (including `phase4_lock_log.json`) are **identical**.
- The only difference is `exploratory.duckdb`. This is expected: it is the designated analytical store where the p5_* tables are written. The p4_* tables in it are covered by the refit's own preservation check ("Phase 4 tables and reports byte-identical after the refit: True").

## 5. TEST lock guard
- `phase4_lock_log.json` is byte-identical to the pre-run hash. Its only events (FREEZE, OPEN, CLOSE) are Phase 4's single approved opening.
- `phase5_lock_log.json` is `[]`, so it has 0 events and no OPEN. `assert_phase5_lock_not_opened` passed in the orchestrator.
- `phase5_test_set_manifest.json` has `test_evaluated_in_phase5: false`. The three TEST sets are frozen by match-id hash only.

## 6. Independent spot checks (my own pandas code, not the project functions)
1. **Context n and residual (IPL batter, death, chase, player 152 Ravindra Jadeja).** I rebuilt the population from `exp_pre_delivery_state` using the regulation, scope, DLS, chase, target and rrr filters, plus a TRAIN-only q0.75 rrr threshold (12.28125, from 25,105 IPL TRAIN chase rows), restricted to TRAIN+VALIDATION death-phase balls faced. Results: n=106, matches=11, actual runs 183. Raw mean 183/106 = 1.726415 and residual 183 − 165.0622 = 17.9378 (mean 0.169225). The stored `p5_context_scores` row matches, and so does the live internal API row (n 106, matches 11, raw 1.7264150943, residual 0.1692246946). Player 2876 also matches (n 88, 9 matches, 131 runs, residual −6.0154). I also recomputed n_eff = (Σn)²/Σn² = 9.28595. With k=25 the weight is 9.286/(9.286+25) = 0.270838, and shrunk = target + w·(residual − target) = 0.086536. All match.
2. **Date-verification classification from raw CSVs.** From `matches.csv` + `competitions.csv` I got 42 T20I matches after 2026-05-31 (last 2026-11-01). I compared the `ball_by_ball.csv` `delivery_ist_time` date part within ±1 day (the documented tolerance) and searched the Cricsheet JSON folders (`it20s`, `t20s`, `2026_male_json`) by date ±1 and team pair. Result: 36 DATE_CONSISTENT_ACROSS_SOURCES and 6 DATE_SINGLE_SOURCE. This agrees with the stored class for **42/42** matches, and every original date is unchanged. My first pass gave 39/42 because I used exact-day matching and missed the `2026_male_json` folder; the stored ±1-day rule is documented in the report, so the 3 differences came from my check, not the stored table. 0 of 42 are officially verified.
3. **Classification counts from raw files.** Players with `is_played=true` in `playing_eleven.csv` for T20I matches dated on or before 2025-12-31 (the as_of date) give 655 of the 1,217 players. This set equals the stored DERIVED_CAPPED set exactly (all 1,217 flags agree). VERIFIED_CAPPED = 0, any UNCAPPED label = 0, UNKNOWN = 562. The override file holds 0 rows.
4. **Split-half reliability (independent implementation).** I wrote my own player-match aggregation from `p5_context_stats`, with chronological odd/even and early/late halves, at least 6 balls per half, Pearson and Spearman-Brown. All 4 rows checked reproduce the stored values exactly:

   | Format | Role | Window | Split | Players | r | SB |
   |---|---|---|---|---|---|---|
   | IPL | batter | TRAIN | odd/even | 125 | 0.155080 | 0.268518 |
   | T20I | bowler | PRE_TEST | odd/even | 231 | 0.145352 | 0.253811 |
   | T20I | batter | PRE_TEST | early/late | 227 | 0.318237 | 0.482822 |
   | IPL | bowler | TRAIN | early/late | 111 | −0.073237 | −0.158050 |

5. **Strict-uncapped and gating via the API (TestClient on the real store).**
   - These all return 200 `STRICT_UNCAPPED_DISABLED` with a reason, the source needed, and no rows: internal `/rankings/uncapped/{indian_batters, overall}`; all six uncapped/emerging presets; dynamic ranking with `status=VERIFIED_UNCAPPED`; Indian + VERIFIED_UNCAPPED; context-preview with VERIFIED_UNCAPPED; custom selection with an `IN_UNCAPPED` group constraint or `uncapped_mode`.
   - Public `/rankings/uncapped/*`, `/rankings/batter` and `/dynamic-rankings` return 403 `PUBLICATION_GATE_NOT_SATISFIED` with the gate list and no rows.
   - An internal route without a token returns 401.
   - Internal rankings carry `publication_status=INTERNAL_EXPERIMENTAL_ONLY`. Failing gates: data_weight_gate_passed, methodology_validated, date_verification.
   - T20I batter + powerplay + chase + Indian + DERIVED_CAPPED returns EMPTY (pool 3, POOL_TOO_SMALL, 60 INSUFFICIENT_SAMPLE_FOR_CONTEXT). No padding.

## 7. Honesty of the summary
`phase5_user_summary.md` is byte-identical in `data/reports` and `.agents/tasks` (SHA-256 ED6ADF4D…). It states:
- no Top 10 published;
- nothing validated;
- the exact failing gates (data_weight_gate_passed, methodology_validated, date_verification, plus request-level strict classification and minimum pool);
- the open decisions;
- stop for review.

A scan of all phase5 markdown found no unqualified "validated" claim and no published Top 10.

## 8. Observations for the reviewer (no changes made)
- **Primary TEST set.** The primary TEST set is `PRIMARY_RESTRICTED`: 99 matches, which excludes all 42 late T20I matches and 3 other matches. It does not use the brief's strict default (`STRICT_OFFICIAL_ONLY`, 0 matches). Both sets are frozen, TEST is not evaluated, and the choice is listed as an open decision (unresolved issue 7, user decision 3). Changing the default would change what a future TEST evaluation uses, so I left it for the user.
- **Classification enum.** The enum includes a placeholder `VERIFIED_UNCAPPED` value next to the user's three statuses. It has 0 rows and is disabled everywhere, but the summary's wording "four separate statuses" may read differently from the user's "three values".
