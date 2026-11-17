# Phase 3 prep: residual findings (known caveats)

## 17. Open decisions / residual review findings

Source: design review 2 (final pass, revision 4): 0 HIGH, 4 MEDIUM, 5 NIT. These were not folded into the text above. Each item gives the reviewer's text verbatim and the safest documented handling. Implementation chunks treat them as known caveats.

1. **MEDIUM**
   - Reviewer: Player residuals are shrunk towards 0 although reference baseline B0 has no match-state or pressure term, so the pressure-sample mean residual is non-zero and low-volume players are pulled to the wrong centre (spec 6 rule 6, 13; notes D). Fix: set shrink target to the pooled mean pressure residual of other players (FULL_SAMPLE, descriptive; strictly prior for predictive use), keep 0 as a named sensitivity, add a synthetic test (all residuals +0.2, one-ball player approaches +0.2), and state that per-candidate baselines are the match-state control.
   - Handling: Primary: B0 plus shrink target set to the pooled mean pressure-sample residual of all other players (labelled FULL_SAMPLE, descriptive; strictly prior when used predictively). Target 0 is kept as a named sensitivity. Per-candidate baselines are the match-state control. Required test: all residuals +0.2, a one-ball player's shrunk value approaches +0.2. The Stage 4 build reports the pressure-sample mean residual.

2. **MEDIUM**
   - Reviewer: No rule for choosing the provisional pressure definition (spec 11.5): 'after reading the numbers' allows selection on exploratory scores and ignores multiplicity. Fix: selection may use only population-level quantities (deliveries, matches, innings, n_eff, eligible counts, cross-format and LOMO/prior reproducibility), never player scores or rankings; ties go to the larger population at the same q; ranking stability is reported not used; report total candidates examined.
   - Handling: Selection of the provisional pressure definition uses only population-level quantities (pressure deliveries, matches, innings, n_eff, eligible-player counts, reproducibility across IPL, T20I, LOMO and strictly prior). Player scores and rankings are never used. Ties go to the larger pressure population at the same q. Ranking stability is reported, not used to choose. The report records the total candidates examined and states that the recommendation is one of N.

3. **MEDIUM**
   - Reviewer: Wickets-bin merge step 4 merges the adjacent pair with the smallest combined m anywhere, so non-deficient bins (e.g. {2},{1}) can merge before the deficient bin ({10}); over-merges and is ambiguous (spec 8). Fix: merge the bin with the smallest m with the adjacent bin giving the larger combined m (ties toward Wrem 1), repeat; add a synthetic test where only {10} is deficient and {2},{1} stay separate.
   - Handling: Replace merge step 4: take the bin with the smallest m, merge it with the adjacent bin giving the larger combined m (ties toward Wrem 1), repeat from step 2. Required synthetic test: only {10} deficient, so {2} and {1} stay separate. Until implemented, treat the older rule as superseded.

4. **MEDIUM**
   - Reviewer: dls_state_reliable=true includes revised innings that ended short of the stated limit: 8 of 25 revised innings 1 end below the limit without all out (15410, 15546, 31707, 36208 COMPLETED, 41975, 46311, 46749, 50408), so Brem/RRR would be wrong in the sensitivity variant (spec 7.6, notes A). Fix: add innings_ended_short_of_stated_limit (legal balls < L, W < 10, dls_flag true; for innings 2 only when not completed by reaching the target), set dls_state_reliable=false when true, update the 48/2 counts, add a unit test.
   - Handling: Add innings_ended_short_of_stated_limit (legal balls < L, W < 10, dls_flag true; for innings 2 only when the chase did not end by reaching the target). Set dls_state_reliable = false when it holds. Expect 8 innings 1 (15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408) and recompute innings 2. The 48 reliable-innings count is superseded and must be recomputed. Unit test required. Primary results already exclude DLS-unreliable rows; this only affects the sensitivity variant.

5. **NIT**
   - Reviewer: RRR when Req <= 0 is defined two ways: spec 3 and 9 say NULL only when Brem=0 or no target; spec 7.2 and 4 say NULL or non-pressure. Fix: RRR_k is NULL when req_nonpositive_flag is true (12 rows seen) and say so in section 3.
   - Handling: RRR_k is NULL whenever req_nonpositive_flag is true (12 rows seen) as well as when Brem = 0 or there is no target. Such rows are never pressure rows via RRR. Sections 3, 4, 7.2 and 9 are read consistently with this.

6. **NIT**
   - Reviewer: OTHER_T20 treatment in the state table is unstated (30 matches, 60 innings; par cells exist only for IPL and T20I). Fix: keep state columns, set par, exp_remaining and rank_pct NULL, count as format_out_of_scope, exclude from all pressure populations.
   - Handling: OTHER_T20 rows (30 matches, 60 innings) keep state columns, get NULL par, exp_remaining and rank_pct, are counted as format_out_of_scope, and enter no pressure population.

7. **NIT**
   - Reviewer: Candidate family details open (spec 11): quantile context for family (a) not stated as per-format or pooled; the pair (-resource_ratio, phase=death) has no quantile in its phase condition although 'both conditions use the same q'. Fix: quantiles per competition_type x role with pooled as sensitivity; for the death pair the phase is the fixed label and only -resource_ratio uses q.
   - Handling: Quantiles are computed per competition_type x role (IPL and T20I separately), with pooled as a sensitivity. For the (-resource_ratio, phase = death) pair, phase is the fixed label and only -resource_ratio uses q.

8. **NIT**
   - Reviewer: Availability matrix (spec 5.3) has no rows for resource_ratio, projected_surplus, bowl_rel_A, bowl_rel_B, bat_pressure_rel, bowl_B_early_flag. Fix: add one row each (pre-delivery yes, or PARTIAL with par_basis where par or rank cells are used).
   - Handling: Add one availability row each for resource_ratio, projected_surplus, bowl_rel_A, bowl_rel_B, bat_pressure_rel, bowl_B_early_flag, and gap_k. Default classification is pre-delivery yes. Where par or rank cells are used, mark PARTIAL with par_basis. Until the rows exist, the feature dictionary must carry these classifications and the leakage test must cover them.

9. **NIT**
   - Reviewer: Stage 5 and Stage 6 flows are specified only as 'reuse Phase 2.5' (spec 14, notes): eligibility candidate generation, feeding the exploratory score into the combination engine and ADJUSTED_ESTIMATE are not defined. Fix: add a short subsection naming the Phase 2.5 functions reused, their inputs, and the rule that a missing format score stays missing.
   - Handling: Stage 5/6 implementers read the Phase 2.5 code and name the functions reused, their inputs (pressure balls, pressure matches, n_eff) and the candidate percentile list per format and role in the build manifest. The exploratory score feeds the combination engine only as a labelled proxy. ADJUSTED_ESTIMATE stays in its own section. A missing format score stays missing and is never imputed.

