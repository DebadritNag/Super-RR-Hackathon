# Phase 6 design review

Reviewed: `d:/Data/backend/docs/phase6_design.md` against `d:/Data/.agents/tasks/phase6_brief.md` and the code under `d:/Data/backend`.

**Verdict: CHANGES_REQUESTED** (3 HIGH, 8 MEDIUM, 3 LOW/NIT-level items; any HIGH or MEDIUM blocks).

No TEST outcome leakage path exists in the design as written: the data entry is `load_study()` (drops TEST rows), plus a row guard, an import guard and lock-log snapshots. The leakage risk that remains is selection by outcome: the selection rule is not specified tightly enough to be mechanical, and the "criteria came first" check cannot be enforced as written (findings 1 and 2).

## Findings

### HIGH

**1. The pre-declared selection rule is not mechanical (4.1).** Several points leave room for post-hoc choice, which is the exact failure the brief forbids.
- M1 is "pooled Spearman-Brown across four cells", but the PASS rule requires an M1 bootstrap lower bound "in at least three of four cells". Pooled and per-cell values are mixed.
- "Within one bootstrap SE of the best M1" does not say which SE (pooled M1 or per-cell), nor which bootstrap (player or match). 4.6 defines both.
- M4 is "median pressure balls per player and players meeting the minimum" (two numbers) and is the first tie-breaker. No single scalar is named.
- M2 and M3 are declared as "exactly these metrics" but never enter the rule. Unused metrics invite later use.
- TRAIN-only repeat: nothing says what happens if the TRAIN ordering disagrees with PRE_TEST.
- The intersection fallback ("rule is not applied") leaves no defined outcome.
Fix (replace the `rule` block with):
```
rule: per definition d, cell c: R(d,c)= SB split-half, odd/even, stream=primary, window=PRE_TEST,
 match-cluster bootstrap 1000 draws (Study.W), lo(d,c)=2.5th percentile.
PASS(d) iff R estimable in all 4 cells AND lo(d,c)>0 in >=3 cells.
M1(d)=Fisher-z pooled R (weights n-3, clip 0.99); SE1(d)=SD over bootstrap draws of pooled M1.
TOP(d) iff PASS and M1(d) >= max_pass M1 - SE1(best).
Order inside TOP: M4(d)=median over players of pressure balls, pooled across the 4 cells, desc; then M5 median desc; then id asc.
M2, M3 are reported descriptively and have no role in the rule.
TRAIN-only repeat: if TOP set differs from PRE_TEST, report DEFINITION_ORDER_NOT_STABLE and no top group is named.
Intersection <30 players in any cell: report COMPARISON_CONFOUNDED; the output is a pass list only, no top group.
```

**2. "Criteria precede results" is not enforceable as specified (4.1, Delivery step 3).**
- "fails if the hash file's timestamp is after the timestamp of any existing `p6_*` result table": DuckDB tables carry no creation timestamp, so this check cannot be implemented.
- `verify_criteria(results_started_at=None)` takes the caller's own timestamp, and the hash file is written by the same script that could rewrite it after deleting it.
Fix: add a `p6_run_log` table (append-only, one row per step: `seq`, `step`, `started_utc`, `criteria_sha256`, `config_sha256`). The plan step inserts seq 1 with the criteria hash. Every later step inserts a row and `verify_criteria` requires seq 1 to exist with a matching hash and `started_utc` earlier than the current step. Also commit the criteria file and hash file before the first estimator run and record the git blob hash in `phase6_investigation_plan.md`. Delete the timestamp-vs-table check.

**3. The classification change breaks existing code the design does not enumerate (3.1).** Verified in code:
- `classification_v2.py:124` rejects any status outside `STATUS_VALUES`; `:301` and `:307` build `by_status` over `STATUS_VALUES`, and `:323` reads `by_status[VERIFIED_UNCAPPED]`, which raises `KeyError` once the tuple has three values.
- `OVERRIDE_STATUS_VALUES` (line 54) includes `VERIFIED_UNCAPPED` and line 220 handles it. The brief says keep the override mechanism, so an override can still write the placeholder into the table, and line 124 would then reject it.
- `phase4_service.py:570` emits `classification_values` from `STATUS_VALUES`; `routes_phase5.py:43`, `filters.py:20,45,130` and `phase4/uncapped.py`, `phase4/selection.py:45` use the string.
Fix: state that `STATUS_VALUES` (three) is used only for the public enum and the reported counts; add `ACCEPTED_STORED_VALUES = STATUS_VALUES + (VERIFIED_UNCAPPED,)` for line 124 and the override path; make line 323 `by_status.get(VERIFIED_UNCAPPED, 0)`. List the files above in the cleanup work, and add a test that an override of `VERIFIED_UNCAPPED` is still accepted and that the strict filter still returns `STRICT_UNCAPPED_DISABLED`.

### MEDIUM

**4. Public-schema scan contradicts the schema it checks (3.3).** `PublicDescriptiveFlags` has `official_ranking`, and the forbidden-name regex contains `rank`, so the design's own test fails. `status` is also a field there. Fix: rename to `descriptive_only: Literal[True]` plus `disclaimer`, drop `official_ranking` from the public model, or add an explicit allow-list `{"official_ranking"}` to the test with the reason. Also state how the `PlayerListResponse | Disabled` response_model on `/players` (routes.py:64) is handled; the public route must keep a `Disabled` branch or the design must say it is removed.

**5. Variance-verdict rule is partly undefined (4.3, 4.4).**
- "E1c/E2 ... at least 90% of bootstrap draws positive": E6 bootstraps E1c only, so no E2 draw share exists. Choose E1c only, or add REML per draw.
- E4 and E5 never enter the verdict; say they are sensitivity only.
- H-B tests (i) "near the mean balls per match" and (iii) tercile ratio have no numeric cut, and the rules that map flags to "H-A supported / H-B supported / H-C supported / mixed / unidentified" are not written. "Generated from flags" needs the table.
Fix: add a flag table with numbers, for example H-B(i) supported if ratio is within 25% of mean balls per match; H-B(ii) supported if the sign differs between kish basis and match-cluster basis in the same cell; H-B(iii) supported if tercile variance ratio > 1.5 or < 0.67; verdict = H-A only if power >= 0.8 and H-B flags all unsupported; "mixed" if two or more supported; otherwise "unidentified".

**6. Recent-form residuals are not comparable across windows (4.2, 4.11).** B0 is fitted on TRAIN, so 2024-onward mixes 192 in-sample TRAIN matches with 211 out-of-sample VALIDATION matches, while 2025-onward is VALIDATION only. Reliability and `tau2` in these windows are computed on residuals of different character. Also, `el.window_ratio(cell, windows, "TRAIN")` is called with a reference window that has no rows in 2025-onward; the design does not say what the ratio is. Fix: state the ratio formula for a window without TRAIN rows (for example window balls / PRE_TEST balls, applied to the frozen thresholds), and add a column `share_rows_in_b0_fit_window` to every recent-form row plus a note in the report that cross-window comparison is confounded. Also run the 2024 window on VALIDATION rows only as a clean-residual sensitivity.

**7. Reliability is not tied to pressure (4.1, 4.6, 4.7).** Split-half reliability of pressure-ball residuals can be high because a definition picks balls where stable player traits (role, batting position, style) show, not because players differ in pressure response. The criteria never compare against non-pressure balls. Fix: add a control metric M6 per definition and cell: split-half reliability on a non-pressure ball sample matched on number of balls per player; report pressure minus control reliability. Not a selection input unless declared in the rule; if it is used, it must be added to the criteria file before the hash is written.

**8. O3 and O6 mix noise bases in the data weight (4.10).** `B = n_eff/(n_eff+k)` uses Kish match-equivalent `n_eff` and `k = sigma2/tau2` on the same basis (F6). O6 and O3 take `tau2` from a match-cluster model whose noise unit is the match, so `k_used` must be paired with a match-count `n_eff`, not the Kish ball-weighted value. The design does not say which `n_eff` goes into `data_weight` for these options. Fix: add a column `n_eff_basis` (`KISH_MATCH` or `MATCH_CLUSTER`) and specify that O3/O6 use the match-cluster effective count `m / (1 + (m_bar - 1) * ICC)`, and that the 48-context regression in 4.8 is only run for the Phase 4 basis.

**9. Tests required by the brief are missing from the test plan (10).** Not listed: (a) no Cricsheet import or reference in scoring/Phase 6 modules; (b) classification enum/wording test over schemas, docs and report text (only 3.1 describes the change); (c) retention stub not referenced by scoring is listed in 4.14 but not in section 10; (d) a recent-form test that primary tables are not modified; (e) the internal `/internal/players` routes token test. Fix: add these to 10 with the assertion for each.

**10. Replacement of the `or True` assertion at test_phase5_dynamic_ranking.py:583 is conditional (3.2).** "if the score is the shrunk estimate ... only if it holds ... if it does not hold ... assert the actual invariant" leaves the choice to the implementer, the same weakness being removed. Fix: read the test world first and write the final assertion in the design. If unsure, specify the fallback as `assert r["interval_low"] <= r["interval_high"]` and one explicit documented check of whether the score lies inside the interval, recorded as a finding if it does not. Line 594: `len(table) == len(specs) == len(set(table["spec_hash"]))` is correct; note the duplicate-spec case (two specs with equal hash) must be excluded by construction.

**11. Cache change compatibility is unspecified (3.4).** `cache_key`, `invalidate_if_version_changed` and `get_or_compute` get new arguments. Existing callers (`phase5_service.py::_full`) and the existing cache tests call the 4-argument forms. The source of `gate_state_hash` (which service call produces the failing-gate ids, and whether it is computed per request) is not named, and the module docstring says gates are not cached. Fix: list the callers and tests to update, give new parameters defaults only if the default preserves isolation (`scope` must have no default), and name the function that supplies the failing-gate ids. Update the module docstring.

### LOW / NIT

**12. SciPy statement (1).** `scipy` is already in the requirements, so the "only if already a dependency" condition is met. State that `scipy.special.gammaln` is permitted for E4/E5; hand-written lgamma in numpy is not needed. NIT.

**13. 4.1 criteria unit says "primary stream" but 4.6 uses four streams.** State that the selection rule uses the primary stream per role only (`en.PRIMARY`) and other streams are descriptive. LOW.

**14. Runtime not estimated (4.6, 4.7).** 9 definitions x 4 streams x 3 modes x windows x 1000 bootstrap draws plus 200 random splits. Add an expected run time and a cap (for example `--quick` using 200 draws for tests only). LOW.

**15. Deliverable mapping is incomplete (11).** The brief lists 12 reports, the `phase6_user_summary.md` copy to `.agents/tasks/`, and the carry-forward of Phase 5 items with status changes in `phase6_unresolved_issues.md`. The design names only the register and user summary in step 7. Add a table mapping each deliverable to the script that writes it, and say that every Phase 5 register item gets an explicit status (unchanged, changed, closed). LOW.

## Verified assumptions

- `GATE_B = 0.5` at `app/phase4/eligibility.py:36`; `data_weight_gate_passed = marginal_b >= el.GATE_B` at `context_eligibility.py:132`; `marginal_b = ne_min/(ne_min+k)` at line 114.
- `k_for` arithmetic and `CONFIGS`: floor 0.01 with mult 1/0.5/2/4 gives 100/100/50/25, `shrink_floor0.001` gives 1000, `shrink_target0` gives 100, non-finite branch returns `1/floor`, `shrink_none` returns 0. The hand formula in 4.5 is valid for `between <= floor_abs`, which holds for `between = -1`.
- Three vacuous assertions exist: `test_phase5_dynamic_ranking.py:583`, `:594`, and `test_pressure_state.py:45`; the line after the last one asserts the real list, so deleting it is safe.
- `RankingCache` key is a `"|".join` hash and returns stored objects without copying (`cache.py`).
- `load_study` drops TEST rows (`drop_test_rows`) and raises if any TEST period remains; `Study.thresholds` fits on TRAIN; `Study.W` shared weights; `all_cells(defn)` exists.
- Reusable Phase 5 API names in F8 exist in `reliability.py` (`CellData`, `from_cell`, `window_cols` with only TRAIN/PRE_TEST, `boot_moments`, `reml_tau2`, `split_half`, `sb`, `required_sample`, `simulate_detectability`, `multi_format_pooling`).
- `phase5/lockguard.py` has read-only helpers (`file_sha256`, `assert_phase5_lock_not_opened`, `LockGuardError`); `snapshot`/`assert_unchanged` are new, as the design says.
- Late-date cutoff in `config/phase5_date_verification_v1.json` is 2026-05-31, later than the TEST start, so the 42 late-dated T20I matches fall in TEST by date and are not loaded.
- Public `/players` is registered with `response_model=PlayerListResponse | Disabled`; `ClassifiedPlayer` carries no score fields.

## Unverified / wrong assumptions

- Claim that `STATUS_VALUES` can become a three-tuple without other changes: wrong (finding 3).
- Claim that a hash-file timestamp can be compared with `p6_*` table timestamps: not implementable (finding 2).
- Window counts (723 / 403 / 211) and the 48-context table values were not re-queried in this review (the shell query failed on quoting); they are taken from the design and Phase 5 reports. The implementer must assert them from the store, as section 10 already plans.
- Claim that the public Pydantic allow-list alone guarantees no leakage: depends on `response_model` being a single model; the `| Disabled` union on `/players` is not handled (finding 4).
- Whether `p5_player_classification` contains any `VERIFIED_UNCAPPED` row was not checked here; the design plans a count.
