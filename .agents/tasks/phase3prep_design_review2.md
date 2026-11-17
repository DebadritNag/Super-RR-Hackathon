# Design review 2 (final pass): pressure framework v1, revision 4 (Phase 3 prep)

Reviewed: `backend/docs/pressure_framework_v1.md` (revision 4), `.agents/tasks/phase3prep_design_notes.md` (revision 4), against `phase3prep_brief.md` and `phase3prep_design_review.md`.
Method: read both documents in full and re-ran read-only DuckDB checks on `superr.duckdb`.

Verdict: **CHANGES_REQUESTED** (0 HIGH, 4 MEDIUM, 5 NIT).

## Resolution of the 9 earlier findings

| Earlier finding | Status | Evidence |
|---|---|---|
| 1 Outcome-conditioned flags (`counts_as_ball_faced`, `legal_inc`) | Resolved | Matrix rows added (spec 5.3); selection rule in 5.4 and 7.4; mutation test in 5.4 and notes B/F. |
| 2 `target_basis_unverified` | Resolved | Defined in spec 3, used in 7.2, 7.6, open decision 18. Uses innings-1 data only. I confirmed 19 L=120 innings 1 are incomplete (IPL 6, T20I 13). |
| 3 `exp_remaining` level and fallback | Resolved | Binned cell, first-row-in-bin observation, E0 to E2 chain, level recorded (spec 6, notes C). |
| 4 Constants missing from the config table | Resolved | 21 parameter rows in spec 8 equal the 21 rows in notes H; parity test specified. |
| 5 "6 split-year" | Resolved | 18 (12+3+2+1) in spec 2 and notes F. |
| 6 `shrink_to_parent` k undefined | Resolved | `tau2 = max(between_moment, tau2_floor * sigma2_within)`, `k` finite, floor-hit report. |
| 7 Stale Appendix grid | Resolved | M5 cites the section 8 grid. |
| 8 NULL handling | Resolved | Spec 4 bullet and section 9 formula. |
| 9 Cause of 402 early chases | Resolved | Reworded in spec 6 rule 3. I confirmed the count: 176 + 211 + 15 = 402 chases (IPL, T20I, OTHER_T20). |

## Findings

### 1. MEDIUM: Player residuals are shrunk to 0 although the reference baseline excludes match state (spec 6 rule 6 and 13, notes D)
The reference baseline B0 uses cells `competition_type x innings role x phase x Wrem bin` and no match-state or pressure term. Actual minus expected summed over pressure deliveries therefore has a non-zero population mean (a batter chasing a high RRR scores and is dismissed differently from the cell average). `shrink_player` pulls low-sample players towards `target = 0`, which is the all-delivery average, not the pressure-sample average. Low-volume players are pulled to the wrong centre, and Stage 5 ranking stability and Stage 6 scores inherit it. The brief also asks to control for "match state"; B0 does so only in the per-candidate sensitivity baselines.
Fix: set `target` to the pooled mean residual of the pressure sample (estimated from all other players' pressure deliveries, labelled FULL_SAMPLE and descriptive, strictly prior for predictive use). Keep 0 as a named sensitivity. Add a test on a synthetic table where every player has residual +0.2 and the shrunk value of a one-ball player must approach +0.2, not 0. State in section 13 that B0 plus pooled-mean target is the primary and the per-candidate baselines are the match-state control.

### 2. MEDIUM: No stated rule for choosing the provisional pressure definition (spec 11.5, brief Stage 5)
Section 11.5 says Stage 5 "selects a provisional pressure definition after reading the numbers". No criterion is given. A choice made after seeing exploratory player scores or rankings is selection on the outcome and is an arbitrary cutoff by another route, which the brief forbids. The number of candidates examined (several hundred combinations: 8 signals x 7 quantiles x absolute/relative x LOMO/prior, plus conjunctions and bowling conventions) is not recorded either.
Fix: add to 11.5: the selection may use only population-level quantities (pressure deliveries, matches, innings, n_eff, eligible-player counts, reproducibility across IPL, T20I, LOMO and strictly prior), never player scores or rankings; ties go to the larger pressure population at the same `q`. Ranking stability is reported, not used to choose. The report records the total candidate count and states that the recommendation is one of N examined.

### 3. MEDIUM: The wickets-bin merge rule can merge bins that are not deficient (spec 8, step 4)
Step 4 merges the adjacent pair with the smallest combined `m`, wherever it is. If bin {10} has `m` below 30 while {2} and {1} each have `m` above 30 but a small combined `m`, the first merge is {2},{1}, which does not address the deficient bin. The rule then over-merges, contradicting "coarsest-needed partition", and two coders could build different partitions.
Fix: replace step 4 with: take the bin with the smallest `m` (ties toward `Wrem` 1); merge it with the adjacent bin that gives the larger combined `m` (ties toward `Wrem` 1); repeat from step 2. Add a synthetic test: counts where {10} is the only deficient bin must produce a partition in which {2} and {1} stay separate.

### 4. MEDIUM: `dls_state_reliable = true` includes revised innings that ended short of their stated limit (spec 7.6, notes A)
Read-only check: of the 25 innings 1 with `first_inn_revised_overs`, 15 reach the limit, 2 end all out, and 8 end short of the limit without all out: 15410 (21 of 114 legal balls), 15546 (78 of 84), 31707 (2 of 30), 36208 (47 of 54, COMPLETED), 41975 (58 of 108), 46311 (13 of 54), 46749 (22 of 84), 50408 (46 of 54). The stated limit was therefore not the effective limit for these innings (further interruption or abandonment). The spec claims 48 `dls_state_reliable = true` innings and adds them in the sensitivity variant, where `Brem` and `RRR` would be wrong for these rows. Match 36208 is COMPLETED, so its chase target is also affected.
Fix: add `innings_ended_short_of_stated_limit` (legal balls < `L`, `W` < 10, `dls_flag` true) and set `dls_state_reliable = false` when it holds. Report the count (8 innings 1 expected; recompute for innings 2, where a chase may legitimately end at the target, so apply the rule to innings 2 only when the chase is not completed by reaching the target). Update the 48/2 counts accordingly and add a unit test.

### 5. NIT: `RRR` when `Req <= 0` is defined two ways (spec 3 versus 7.2 and 4)
Section 3 and 9 give `RRR` NULL only when `Brem = 0` or no target. Section 7.2 says `Req <= 0` gives "RRR NULL or non-pressure", and section 4 lists `Req <= 0` rows among NULL `RRR`. Fix: define `RRR_k` NULL when `req_nonpositive_flag` is true (12 rows seen), and say so in section 3.

### 6. NIT: OTHER_T20 treatment in the state table is unstated (spec 2, 6, notes B)
Par sources and cells exist only for IPL and T20I. OTHER_T20 rows (30 matches, 60 innings) stay in the state table but have no par cell. Fix: state that OTHER_T20 rows keep state columns, get NULL par, `exp_remaining` and `rank_pct`, are counted as `format_out_of_scope`, and enter no pressure population.

### 7. NIT: Candidate family definitions leave two details open (spec 11)
(a) "The signal's own context population" does not say whether quantiles are per format or pooled IPL and T20I. (b) The pair (`-resource_ratio`, phase = death) has no quantile in its second condition, yet "both conditions use the same q". Fix: quantiles are computed per `competition_type x role` (IPL and T20I separately, pooled as a sensitivity); for the death pair the phase condition is the fixed label and only `-resource_ratio` uses `q`.

### 8. NIT: Availability matrix omits several derived signals (spec 5.3)
`resource_ratio`, `projected_surplus`, `bowl_rel_A`, `bowl_rel_B`, `bat_pressure_rel`, `gap_k` (partly) and `bowl_B_early_flag` have no explicit row. All derive from earlier-row state, so they are `yes` (or PARTIAL with `par_basis` where par or rank cells are used). Fix: add one row each so the feature dictionary has a source of truth for allowed use.

### 9. NIT: Stage 5 and Stage 6 flows are not specified beyond "reuse Phase 2.5" (spec 14, notes)
Neither document defines how pressure-specific eligibility candidates are generated (which percentile list, per format and role), how the exploratory score feeds the Phase 2.5 combination engine, or how `ADJUSTED_ESTIMATE` is produced. The Phase 2.5 code exists and can be read, so this is not blocking. Fix: add a short subsection naming the Phase 2.5 functions reused, the inputs they receive (pressure balls, pressure matches, `n_eff`), and the rule that a missing format score stays missing.

## Verified assumptions

- Revision-4 responses to all 9 earlier findings are present and consistent between spec and notes.
- Parameter rows: spec 8 has 21, notes H has the same 21 names.
- Truth table arithmetic: 7+2+2+14+9 = 34; first-innings revised 25; second-innings revised 25; revised targets 23; COMPLETED with revised target 22.
- Phase boundary table: recomputed `(3L)//10` and `-((-3L)//4)` for all 14 `L`; all match. Innings per `L` sum to 48 shortened innings.
- Innings counts: 367+363 IPL, 470+452 T20I, 30+30 OTHER_T20 = 1,712; chases 845 = 822 + 23.
- Overs-touched histogram sums to 1,712. Legal flag counts sum to 200,999. Wicket counts 10,881; credited 10,272; not credited 609.
- Source innings: IPL 358 and T20I 435 complete innings 1 with L=120 (793); incomplete 6 and 13. Incomplete chases with L=120: 176 + 211 + 15 = 402.
- `deliveries` has `extras_label_unverified`, `dismissal_field_anomaly`, `is_legal_ball`, `striker_id`; `matches` has no season column, `first_inn_revised_overs` and `second_inn_revised_overs` are DOUBLE.
- Matches 16753 and 19959: first-innings limit 66, second innings 65 and 63 legal balls, no innings 2 limit; `innings_limit_unstated` and `L <= limit` hold.
- 12 rows with `dismissed_player_id` set, `is_wicket` false, `dismissal_type` null.
- Leakage controls hold on paper: innings-1 total barred from innings-1 rows; own match removed from par and rank cells; strictly-prior excludes same-day matches; outcome flags are in the `out_` group; Cricsheet is a mask source only.

## Unverified or wrong assumptions

- WRONG (implicit): revised innings limits are the effective limit for every revised innings. Eight innings 1 end short of it without all out (finding 4).
- UNVERIFIED: that the pressure-sample mean residual under B0 is near zero (finding 1). The Stage 4 build should report it.
- UNVERIFIED: that the merge algorithm yields the coarsest-needed partition (finding 3).
- NOT RE-RUN: extras counts by type beyond the totals, per-match wicket-flag list, season label counts, `Req <= 0` rows in 48610. The Stage 2 build asserts them.
