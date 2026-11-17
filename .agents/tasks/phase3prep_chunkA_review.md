# Review: Pre-delivery match-state engine (Phase 3 prep, chunk A)

The engine computes match state for 200,999 deliveries from strictly earlier rows of the same innings, plus match context fixed before the delivery. It writes the result to a separate `exploratory.duckdb` and leaves `superr.duckdb` unchanged. I read the engine source, the manifest and the coder's evidence file. I did not re-run the suites (the coder reports 223 passed, ruff clean). The workspace is not a git repository, so I reviewed the files directly.

Watch for: three unverified assumptions, all flagged in the data rather than hidden. The revised-overs limit is assumed to apply from the start of the innings. Resource state for DLS is `NOT_RECONSTRUCTED`. The 70:30 default is untouched. Confidence: confirmed on the leakage and extras reading, likely on the DLS flags.

**Verdict**: APPROVED

## High-level view

State counters are exclusive cumulative sums grouped by match and innings, so row k sees only rows before k. Outcome columns (`out_*`) and outcome-conditioned denominators (`den_*`) are separated by prefix from state columns. Selection-only fields that need the finished innings carry a `post_*` prefix and are excluded from the pre-delivery column list.

Legal-ball and extras handling follows the verified semantics. Penalty adds 0 legal balls. `other` extras are flagged `den_extras_label_unverified` and never merged into Overstep. NULL run inputs make the build fail, so an unknown value never becomes zero. Zero unknown categories were found.

Innings 3 and 4 are restricted with reason codes. Confirmed Super Over matches (34429, 45512, 50359) get `CONFIRMED_SUPER_OVER_BY_CRICSHEET`. Unverified matches (40725, 48027, 48029) get `UNVERIFIED_INNINGS_ROLE`. Source rows are kept (38 rows) and state labels are NULL. The Cricsheet-derived ids come from the Phase 2.5 reports only, with no Cricsheet file opened.

The revised target comes from `matches.revised_target`. The revised limit comes from the revised-overs fields, with a carried-limit fallback flagged `CARRIED_FROM_FIRST_INNINGS_UNVERIFIED`. DLS innings are flagged `dls_exclude_primary`, and resource state is explicitly not reconstructed.

<details>
<summary>Issues (3)</summary>

1. **Revised limit and target applied from innings start (likely)** — `limit_applied_from_start_assumed` flags this, but if a revision happened mid-innings, early-ball RRR is computed against information that was not known then. Keep DLS innings out of the primary chase population in later chunks, as the flag already does.
2. **`target_basis_unverified` depends on whole-innings-1 totals (confirmed, minor)** — this uses finished innings 1, which is legitimate for innings 2 because innings 1 is complete. Later chunks must not use this flag or any `post_*` field as a feature. They should select populations only.
3. **Unverified 'other' extras type (confirmed, informational)** — 264 rows are flagged and kept in the totals. Later chunks must apply the register restriction to ball-faced and bowler-charged metrics that use these rows.

</details>

<details>
<summary>Details</summary>

### Leakage boundary

The `row k` mutation test (extras_type, every outcome column, results) and the truncation tests cover the claim that state does not change when row k or later rows change. Static scans forbid result and margin columns, Cricsheet paths and SQL writes in engine modules. The independent stdlib spot-check found 0 mismatches over all 200,999 rows for runs, wickets and legal balls before, 0 on 845 targets, and 9 of 9 on hand-recomputed chase states. A mutation test on real rows exists, so the tests are not synthetic only.

### Official data and store separation

`load_inputs` opens the official DB with `read_only=True`. `write_store` raises if the store path resolves to the official DB path. The manifest preservation block reports `official_data_unchanged: true` with no differences. `superr.duckdb` has an earlier modification time (01:19) than the exploratory store (11:57).

### Wicket-flag disagreement

12 rows have a dismissed player with `is_wicket` false, and 1 row has the reverse. Primary `wickets_remaining` uses `is_wicket`. `wickets_remaining_alt` is provided as the sensitivity, and the `state_wicket_flag_disagreement` flag propagates to 739 later rows. This matches the restriction register.

</details>

<details>
<summary>File map</summary>

- `app/analytics/pressure_engine.py`: state engine and build checks
- `app/analytics/cricket_calculations.py`, `phase_engine.py`: primitives and phase bounds
- `app/services/pressure_service.py`: separate store writer, refuses the official path
- `config/pressure_rules_v1.json`: parameters and reason codes
- `scripts/build_pre_delivery_state.py`, `spot_check_pre_delivery_state.py`: build and independent check
- `tests/test_pressure_state.py`, `test_pressure_leakage.py`, `pressure_helpers.py`: 81 new tests

</details>
