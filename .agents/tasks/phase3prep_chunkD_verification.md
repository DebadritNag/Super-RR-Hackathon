# Phase 3 prep, chunk D verification (restrictions, feature dictionary, orchestrator)
All outputs carry `status: EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`. No official Top 10, no ML, no validated score. 70:30 provisional. Official DuckDB read-only; snapshot before/after reported `official_unchanged=True`. No gate file existed at start (first implementation). No git repo, no commit.

## Files
- `app/services/restriction_service.py`: `RestrictionApplier` (`mask_for`, `apply`, `variants_for`, `variant_drop_mask`, `wicket_label`, `guard_field`, `guard_squad_inference`, `assert_no_name_join`, `require_revised_state`, `dedup_squad`, `safe_squad_join`, `ledger`), `RULE_IMPLEMENTATIONS` (all 26 rule ids; constructor raises if the register has a rule without an entry), `extras_category`, `attach_aux`.
- `app/analytics/feature_registry.py`: `FEATURE_REGISTRY` (99 features), restriction rules derived from each feature's register metrics.
- `scripts/apply_dq_restrictions.py`, `scripts/run_phase3_prep.py`, README "Phase 3 preparation" section, `tests/test_restriction_service.py` (19 tests).
- Outputs in `data/reports/`: `phase3_data_quality_application_report.md` (+ `.json`), `pressure_feature_dictionary.json`, `phase3_preservation.json`; orchestrator copied `docs/pressure_framework_v1.md` to `data/reports/pressure_framework_v1.md`. All seven deliverables exist and parse (checked by the orchestrator and a test).

## Commands and results (raw)
```
python scripts/run_phase3_prep.py     (full defaults, n_boot 1000; log: .agents/tasks/phase3prep_chunkD_orchestrator.log)
 steps: all 7 exit 0; official_unchanged=True; deliverables_ok=True
 distributions: candidates=384 spot_check_all_match=True
 eligibility: definitions=9 selected=chase|q0.9 viable=3
 format sensitivity: combined populations batter=8, bowler=6
 apply_dq_restrictions: rules=26 features=99 ok=True
python -m pytest -q tests/test_restriction_service.py   19 passed
python -m pytest -q                                      309 passed in 301s (290 earlier + 19 new)
python -m ruff check .                                   All checks passed!
python -m ruff format --check .                          101 files already formatted
```

## Key figures (DuckDB, from the application report)
- Innings 3/4: 38 rows (25 + 13) in 6 matches. CONFIRMED_SUPER_OVER 16 rows (34429, 45512, 50359); UNVERIFIED 22 rows (40725, 48027, 48029). Masked from batter and bowler pressure samples: 38 each. 38 source rows still in `deliveries`. None in any pressure population.
- Extras categories: None 189,165; wide 7,714; legbyes 2,748; Overstep 576; byes 529; other 264; None_with_runs 2; Penalty 1. `other` and Penalty mapped to None: 0. Secondary-runs rows 36; guard blocks them for bowler economy.
- Wicket flags: 12 rows dismissed-without-flag, 1 row wicket-without-dismissed (all regulation). State rows where the two wicket counts differ: 739; state features drop 0 rows. Striker dismissals 10,594 primary vs 10,603 with the 12 rows; 9 players change; 1 row removed by RULE_WICKET_NO_DISMISSED.
- DLS: 34 matches (4,433 rows); 3,404 rows lack a reconstructable revised state; 0 DLS rows in the primary chase population. Diagnostic forcing adds 1,763 rows (batter) and changes T20I eligible counts 329 to 333 (batter), 263 to 268 (bowler); Spearman 0.987 to 0.997.
- Names: 14 players share 7 names; a name join would turn 958 rows into 968 and merge 10 ids. Pipeline joins on `player_id` only; guard raises.
- Squad duplicates: 28,381 squad rows, 75 flagged, 28,341 after dedup. Chase batter sample 89,589 rows without join, 89,589 with the deduplicated join (per-player counts identical: True); a naive join gives 89,964 (+375). The pipeline does not use `match_squads`.
- Sensitivity (proxy residual per ball, unshrunk): dropping `other` rows removes 118 rows, Spearman 0.999 to 1.000, eligible counts unchanged; dropping the ten Cricsheet-disagreement innings removes 350 rows, T20I batter eligible 329 to 328, Spearman 0.999.

## Notes
- Feature registry did not exist; created it rather than inferring one. Dictionary availability counts: PRE_DELIVERY 55, PARTIAL 13, OUTCOME 11, DENOMINATOR 10, POST_INNINGS 5, POST_MATCH 5.
- The ledger shows rule-level predicates for FRAME rules and official-table counts for rules without a row predicate (e.g. RULE_UTC_SUFFIX 200,999; RULE_MOM_SENTINEL 119; RULE_XI_COUNT 569).
- Sensitivity scores are raw proxy residuals against a sample-internal cell mean, not the Stage 4 baseline.
- No finding required a user-visible behavior change; no warning was sent.
