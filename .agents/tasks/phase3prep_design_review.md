# Design review: pressure framework v1 (Phase 3 prep)

Reviewed: `backend/docs/pressure_framework_v1.md` (revision 3) and `.agents/tasks/phase3prep_design_notes.md` against `phase3prep_brief.md`.
Method: read both documents in full, re-ran read-only DuckDB and file checks on the claims listed under "Verified assumptions".

Verdict: **CHANGES_REQUESTED** (0 HIGH, 6 MEDIUM, 3 NIT).

The leakage controls are largely sound: innings-1 total is barred from innings-1 rows, the innings-2 target uses only the completed first innings, par and rank cells exclude the own match, season and player statistics are labelled FULL_SAMPLE/LOMO/PARTIAL, no DLS resource table is invented, and Cricsheet is a mask source only. The findings below are gaps and contradictions that would make the coder guess.

## Findings

### 1. MEDIUM: Outcome-derived opportunity flags are used but not classified in the availability matrix (section 5.3, 7.3, 7.4)
`counts_as_ball_faced` (depends on `extras_type` of row k) and `legal_inc` of row k (depends on `is_legal_ball`/`extras_type` of row k) define the batter and bowler opportunity unit (7.3: "delivery with `counts_as_ball_faced`"; 7.4: "legal delivery (`legal_inc = 1`)"). Section 5.3 and 5.4 item 1 list `extras_type` and `is_legal_ball` of delivery k as outcome-only and forbidden for the row concerned, yet the membership of a delivery in a pressure sample depends on them. The matrix has no row for these two flags. Consequence: a bowler's wides and no-balls are dropped from his pressure opportunities by the outcome itself, while "extras rates" are also an outcome compared with expectation. This is selection on the outcome and is never stated.
Fix: add two matrix rows, `counts_as_ball_faced` and `legal_inc` (row k): Pre-delivery = NO, state label = no, outcome label = no, role = "outcome-conditioned denominator flag, may select rows for a per-ball or per-legal-ball rate, never enters a state, par or rank cell". State the rule for bowler extras: pressure membership for bowler outcomes is evaluated on ALL deliveries by the bowler in the state (including wide/Overstep/other), and the legal-ball filter applies only to the denominator of per-legal-ball rates. Add a test that the state columns are identical when row k's `extras_type` is mutated.

### 2. MEDIUM: Chase target built from an unexplained incomplete innings 1 is not flagged, though it is knowable before innings 2 (section 7.2, 7.6, open decision 13)
Read-only check: 42 IPL/T20I innings 1 end with fewer than 120 legal balls and fewer than 10 wickets; 23 of these carry `first_inn_revised_overs`, leaving 19 with no revised field (consistent with the 19 "not complete" source innings in section 2). Match 23674 is one (102 balls, 7 wickets, `result` mentions DLS). For these matches innings-2 `T = innings-1 total + 1` is a target of unverified validity. Innings-1 completeness is known when innings 2 starts, so a pre-delivery flag is legitimate. The spec handles only the four `result`-text matches, and only as a sensitivity list, which relies on post-match text.
Fix: add a per-innings-2 context column `target_basis_unverified` = innings 1 has `W < 10` and legal balls < `L1` and no first-innings revised field and no `revised_target`. Primary chase population excludes these innings; a sensitivity variant includes them; report the count. Keep `dls_suspected_unrecorded` (result text) as report-only. Add to the truth tables and a test.

### 3. MEDIUM: `exp_remaining` cell level and fallback chain are underspecified (section 6, design notes C)
Section 6 defines `exp_remaining(c, Brem, Wrem)` on EXACT `Brem` and `Wrem`, with one observation per source innings per cell (first row in the cell). With 793 source innings and up to 120 x 10 exact cells, an innings visits only its own path, so almost every exact cell has far fewer than `min_cell_innings` = 30 (and `min_prior_innings` = 30). The text then says "use the bins and fallback in section 8" but section 8 gives only `exp_remaining_bins` = "Brem in bins of 6, Wrem bins as below" and no ordered chain. Whether "first row in the cell" applies to the exact cell or the bin is not stated, and the result changes `req_to_exp` and `projected_total_gap` materially.
Fix: define the primary level as the BINNED cell (`Brem` bin of 6 x global `Wrem` bin), with "first row of the innings in the bin" as the observation, and the fallback chain: binned cell (n >= threshold) -> `Brem` bin only -> `competition_type` pooled. Drop "exact" wording or mark exact as a diagnostic only. Record `exp_cell_level_used` per row. State the same for the strictly-prior variant.

### 4. MEDIUM: Several arbitrary constants are not in the section 8 configuration table (section 7.4, 8, 11)
Section 8 says every configuration value lives in `config/pressure_rules_v1.json` with a basis class and sensitivity. These constants appear elsewhere without a basis class or sensitivity run: the `B_k < 12` early-flag for convention B (7.4); the 0.05 quantile tolerance for break reproducibility (11c); the 5% share defining zero-inflation (11c); the Kneedle-style knee rule and its normalisation (11c); the "Wrem low" definition at the `1 - q` quantile (11b); the 0.50 to 0.95 grid sub-selection per family. The brief forbids arbitrary cutoffs, and the spec's own claim of completeness is false as written.
Fix: add each as a row in section 8 with basis `ARBITRARY_PLACEHOLDER` (or `DATA_DERIVED` where justified) and a sensitivity: `bowl_B_early_balls` 12 (sensitivities 6 and 18), `break_reproducibility_tol` 0.05 (0.025, 0.10), `zero_inflation_share` 0.05 (0.02, 0.10). Add them to `pressure_rules_v1.json` and to the tests that assert the table equals the config keys.

### 5. MEDIUM: Split-year T20I count contradicts itself (section 2 versus section 3, open decision 17, design notes A and F)
Section 2 and design notes F say "the 6 split-year T20I matches" and then list 12 + 3 + 2 + 1 = 18. Open decision 17 says 18. A read-only query returns 18 matches (`2022/23`: 12, all dated 2022; `2023/24`: 3, all 2023; `2024/25`: 3, dated 2024 (2) and 2025 (1)). A test written from the "6" text would fail or assert the wrong number.
Fix: replace "6 split-year" with "18 split-year" in section 2 and in design notes F. Keep the 12/3/2/1 mapping, which is correct.

### 6. MEDIUM: `shrink_to_parent` constant `k` is undefined when between-cell variance is not positive (section 6 rule 6, design notes D)
`k` is defined as within-cell variance over between-cell variance by method of moments, "floored at 0". When the moment estimate of the between-cell variance is zero or negative (common with few sparse children), `k` is infinite or negative, not zero. Flooring `k` at 0 would turn off shrinkage exactly where it is needed. Also unstated: per-observation variance used for the within term, whether `n` is raw or `n_eff_kish` (reports use `n_eff_kish`), and how binary outcomes move between `shrink_to_parent` and `beta_binomial_shrink`.
Fix: write `tau2 = max(between_moment, tau2_floor)` with `tau2_floor` a config value (basis ARBITRARY_PLACEHOLDER, sensitivity 10x), `k = sigma2_within / tau2`, `sigma2_within` = pooled per-delivery variance of the parent's children, `n` = `n_eff_kish` of the cell (innings clustering) in both helpers. State that, if `tau2` hits the floor, the cell is reported as `shrinkage_floor_hit`. Unit test with a zero-between-variance parent.

### 7. NIT: Appendix A still states the old quantile grid
Row M5 says "Quantile grid fixed at 0.50, 0.75, 0.90, 0.95". Section 8 and Revision-3 finding 12 define one grid of 0.50, 0.60, 0.75, 0.80, 0.85, 0.90, 0.95. Fix: edit M5 to cite the section 8 grid, or mark M5 as superseded.

### 8. NIT: NULL and non-positive handling inside `rank_pct`, `req_to_exp` is unspecified (section 4, 9)
`V` is "signal values of deliveries in the cell", but RRR is NULL when `Brem = 0` or `Req <= 0` rows are flagged, par values are NULL when `par_unavailable`, and `req_to_exp` divides by `exp_remaining`, which can be 0 or NULL. Fix: add one sentence: NULL signals are excluded from `V` and from the count, `rank_pct` is NULL when the row's own signal is NULL, `req_to_exp` is NULL when `exp_remaining <= 0` or NULL, and each exclusion is counted in the build manifest.

### 9. NIT: Causal statement about early-ending chases is presented as fact (section 6 rule 3)
"402 are chases ended by the target or by an interruption" is not verified: the count of 402 is verified, the cause split is not (the spec itself says no rain field exists). Fix: reword to "402 are chases that ended before 120 legal balls without all out; the data do not record why".

## Verified assumptions (checked by me)

- Register has 26 restrictions; the rule ids in section 12 equal the register's 26 and every one of the 26 `metric_vocabulary` entries appears in section 12.
- `data_quality_impact_report.json` has `issue_register.cricsheet_total_disagreements` with 10 entries.
- Rows with `B_k >= 90` in innings 1 and 2: 44,452; rows with `overid >= 16`: 44,454; regulation rows 200,961.
- 421 innings with `L = 120`, fewer than 120 legal balls and fewer than 10 wickets: 19 innings 1 and 402 innings 2.
- 34 matches have any revised field; 24 of them are COMPLETED. Phase boundary table: all 14 rows reproduce under `(3L)//10` and `-((-3L)//4)`.
- Truth-table arithmetic: 7 + 2 + 2 + 14 + 9 = 34; 25 and 23 innings flags and 48 + 2 = 50 exclusions are consistent.
- Zero rows with `Req <= 0` in unrevised chases; the existing 12 rows are in the revised-target match.
- Phase 2.5 `BATTER_SQL` excludes `wide` and `Penalty`; `CHARGED_EXTRAS` is wide, Overstep, other; seed 20260512, `n_boot` 1,000 and `pool_min_absolute` 30 exist in `config/eligibility_rules_v1.json`.
- `competitions` has the `season` column; `matches` has none.
- Section 1 labels everything exploratory, not validated and not for publication; 70:30 is provisional; the eight weight configurations are preserved.
- No DLS resource table is invented (`resource_status = NOT_RECONSTRUCTED`); `resource_ratio` is explicitly a proxy.
- Cricsheet appears only as a mask source via Phase 2.5 reports with a "no Cricsheet path opened" test.

## Unverified or wrong assumptions

- WRONG: "6 split-year T20I matches" (section 2, design notes F). Actual 18 (finding 5).
- UNVERIFIED: cause of the 402 early-ending chases (finding 9).
- UNVERIFIED and presented as sound: that the 19 incomplete first innings without revised fields yield valid chase targets (finding 2).
- UNVERIFIED: that exact `(Brem, Wrem)` cells are populated enough for `exp_remaining` (finding 3); with 793 source innings they cannot be.
- STALE: Appendix A M5 grid (finding 7).
- NOT CHECKED: figures in section 2 that I did not re-run (wicket-flag lists, extras counts per type, overs-touched histogram, season counts by label other than split-year). The Stage 2 build asserts them.
