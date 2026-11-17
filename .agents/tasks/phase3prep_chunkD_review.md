# Restriction applier, feature dictionary, orchestrator and README (Phase 3 prep, chunk D)

The register is applied at metric level through a code-enforced rule-to-implementation map. Unknown extras stay separate categories, identity and duplicate-squad rules are guarded, and the official DB is unchanged. All seven deliverables exist under their exact names, and the orchestrator ran all steps with exit 0. **Verdict**: APPROVED

Watch for: the sensitivity scores are unshrunk raw proxy residuals, not the Stage 4 baseline (disclosed in the report). Some tests skip instead of failing when outputs are absent (possible, minor).

## High-level view

`RestrictionApplier` loads the 26-rule register and refuses to construct if any rule lacks an implementation. The register is applied per metric: only `EXCLUDE_ROWS_FROM_METRIC` rules produce row masks. Sensitivity and diagnostic rules become named variants, and field and join rules become guards that raise. Nothing is deleted and no match is excluded globally (`global_exclusion: false`, `records_deleted: 0`).

Counts I spot-checked against DuckDB match the application report. Innings 3/4 hold 25 + 13 rows in 6 matches (confirmed). The exploratory store splits them 16 CONFIRMED_SUPER_OVER_BY_CRICSHEET and 22 UNVERIFIED_INNINGS_ROLE (confirmed). Extras counts reconcile: None 189,167 equals 189,165 plus 2 `None_with_runs`, and `other` is 264 and Penalty is 1 (confirmed). Wicket-flag anomalies are 12 and 1 (confirmed), and the revised-field matches number 34 (confirmed).

The preservation file records an empty diff, so official DB tables and source files are unchanged. All seven required deliverables are present and flagged ok, and the framework spec in `docs/` and `data/reports/` has an identical SHA-256 (confirmed). The orchestrator `scripts/run_phase3_prep.py` runs seven steps, snapshots before and after, and returns non-zero on any step failure, missing deliverable or data change.

<details>
<summary>Issues (3)</summary>

1. **Skip-on-missing deliverable tests** — `test_all_seven_deliverables_exist_and_parse` and `test_application_report_shows_invariants` call `pytest.skip` when outputs are absent. The orchestrator does assert existence, so this is a minor weakness. Consider failing, or marking with an explicit "requires pipeline run" marker (possible).
2. **Unshrunk proxy score in restriction sensitivity** — Stage 7 sensitivity uses a raw residual against a sample-internal cell mean, not the Stage 4 baseline. It is clearly labelled, but the eligibility and Spearman changes are not comparable with Stage 4/5 scores. Re-run the sensitivity on the Stage 4 baseline before any scoring phase (confirmed, disclosed).
3. **DLS rows with reconstructable state not in the primary population** — The report states 0 DLS rows in the primary chase sample, while 4,433 DLS rows exist and 3,404 lack a reconstructable revised state. The remaining roughly 1,029 rows presumably sit in innings 1 or are otherwise masked. State this explicitly in the open decisions (possible; verify the composition).

</details>

<details>
<summary>Details</summary>

## Metric-level application with actual counts

The ledger is a rule × metric table with flagged, in-scope, excluded, match and player counts. Innings 3/4 excludes 38 rows from the bowler and dismissal metrics, and 34 from the batter ball metrics. The difference is wides and Penalty, which are not balls faced under the Phase 2.5 definition, so the scope differs by design. RULE_EXTRAS_OTHER and RULE_CRICSHEET_TOTALS exclude 0 rows from primary and appear only as sensitivity variants (118 and 350 rows dropped in the variants). RULE_DISMISSED_NO_FLAG and RULE_WICKET_NO_DISMISSED are confined to dismissal metrics. Striker dismissals go from 10,594 to 10,603 in the variant, and 9 players change. State metrics drop 0 rows.

## Unknown extras

`extras_category` keeps `other`, `Penalty` and `None_with_runs` as separate categories, and the report records 0 `other`/Penalty rows mapped to None. A field guard blocks `extras_secondary_runs` from bowler economy (36 rows). The unit test asserts the categories are distinct from None.

## Identity and duplicate squads

`assert_no_name_join` raises on name columns, and a player_id-only join is required. The report shows 14 players sharing 7 names, where a name join would turn 958 rows into 968 and merge 10 ids. `safe_squad_join` deduplicates and raises if the join multiplies rows. The report shows 89,589 rows in the pressure sample both without and with the join, per-player counts identical, versus 89,964 for the naive join, and the pipeline does not read `match_squads` at all. Unit tests cover both guards.

## Feature dictionary

99 features, each with availability, formula, inputs, unit, leakage risk, allowed use and derived restriction rules, with the top-level status fields set. A test checks that the registry covers every column of the state store, and that outcome and post-match features are never pre-delivery.

## Tests

The 19 new tests use synthetic frames that check exact masks, and they also test the failure paths (missing implementation, field guard, name join, squad multiplication). They are real tests, not trivial ones. I did not re-run the suites. The evidence file reports 309 passed, ruff check clean and ruff format clean. That is consistent with the exit-0 orchestrator steps in `phase3_preservation.json`.

</details>

<details>
<summary>File map</summary>

- `app/services/restriction_service.py`: rule applier, masks, variants, guards, ledger
- `app/analytics/feature_registry.py`: 99-feature registry
- `scripts/apply_dq_restrictions.py`, `scripts/run_phase3_prep.py`: application and orchestrator
- `tests/test_restriction_service.py`: 19 tests
- `data/reports/`: application report (md and json), feature dictionary, preservation json, framework copy
- `README.md`: Phase 3 preparation section

</details>
