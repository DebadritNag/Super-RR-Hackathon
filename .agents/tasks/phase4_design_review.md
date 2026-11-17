# Phase 4 Design Review

Reviewed: `backend/data/reports/phase4_temporal_validation_plan.md` and `.agents/tasks/phase4_design_notes.md`, against `phase4_brief.md`. I also read `app/analytics/pressure_features.py`, `shrinkage.py` and the config files, and re-ran read-only count queries on `superr.duckdb`.

**Verdict: CHANGES_REQUESTED** (2 HIGH, 10 MEDIUM, 2 NIT)

## Findings

1. **HIGH. The definition signals for `inn1`, `any` and the bowler side still use future-match information. The design never says otherwise.**
   Where: notes sections 3 and 5.
   Section 5 makes the *par* strictly prior. In the existing code (`pressure_features.py`, `add_signals`), the inn1 signal is `neg_par_dev`, built from `par_deviation_lomo`. `neg_proj_gap` uses `par_total_lomo` and `exp_remaining`, which comes from `exp_remaining_lomo`. `bowl_signal_B` uses `par_deviation_lomo` and `projected_surplus`. The `rank_pct_with_fallback` ranks are full-sample. Only `neg_par_dev_prior` is prior-based. Section 3 reports TRAIN-only quantile thresholds only for the chase `rrr` signal. So 6 of the 9 candidates (`inn1`, `any`) and the bowler signal could be compared on leaked features, which breaks decision 3 ("never use future match outcomes for any feature").
   Fix: add a section that lists, per candidate, the exact signal columns. State that the Phase 4 versions are `neg_par_dev_prior` and a strictly-prior or TRAIN-frozen `exp_remaining`. State that the bowler signal B is rebuilt from prior-only columns. State that rank-percentiles and quantile thresholds come from TRAIN rows only. Extend `LeakageGuard` to reject every `*_lomo` column and any full-sample rank column. Add a test that mutates later matches and checks that all nine flags for earlier matches are unchanged. For `inn1`/`any` rows without prior par, specify "flag = NULL, excluded from that candidate's population", and report the count.

2. **HIGH. Unique exact name matches to `ipl squad.csv` are labelled `VERIFIED_FROM_SOURCE`.**
   Where: notes section 9, rules for `nationality`.
   The brief says name matching only generates candidates, and tests must show "no name-only merging". The design treats the 232 case-insensitive unique name matches as verified and applies them. A unique name in `players` does not show the squad row is the same person. The design uses neither team corroboration (`competition_team_player_mapping.csv`) nor any identity key. Here the status is "verified" without verification.
   Fix: either (a) apply a squad nationality only when the name match is corroborated by a `player_id`-keyed team link (squad `team_name` equals a team the player has a mapping row for in the same competition), labelled `DERIVED` with source `ipl squad.csv NAME_PLUS_TEAM_MATCH`; or (b) set uncorroborated name matches to `UNVERIFIED` and nationality `Unknown` until confirmed. `VERIFIED_FROM_SOURCE` is reserved for a `player_id`-keyed source or a manual override. Add a test for "same name, different team stays Unknown".

3. **MEDIUM. The order of the selection steps is not fixed, and the steps depend on each other.**
   Where: notes sections 3, 4, 6.
   Eligibility rule 1 uses the data weight `B_i`, which depends on `k` (shrinkage). The shrinkage choice is scored on the eligible players. Both depend on the chosen definition. Nothing says which is chosen first, or whether the shrinkage grid and the eligibility ladder run per definition (9 times) or only for the winner. Different orders can give different frozen choices.
   Fix: state the order: (1) definition, using the all-players pool, with no eligibility threshold beyond the 12 and 6 ball floors already in R and S; (2) shrinkage strength for the chosen definition, over all players with data in both periods; (3) eligibility threshold for the chosen definition with the chosen `k`. Say that definition sensitivity runs the later steps at fixed defaults only.

4. **MEDIUM. The score `Sc` and the Gate 2 failure rule are under-specified.**
   Where: notes section 3, steps 2 and 3.
   (a) Spearman-Brown on a split-half correlation of zero or below gives zero or a negative or >1 value. Fisher-z is undefined at |r| ≥ 1. (b) "Weight `n_players - 3`" is applied to a mean of two z values, but R and S have different player counts. (c) "A candidate with two or more non-estimable cells fails Gate 2" is the only mention of Gate 2. A candidate with exactly one non-estimable cell is scored on three cells while others use four, which is not comparable. (d) The "0.02 top group" is on the correlation scale and ignores the noise in `Sc`.
   Fix: state clipping (`r` clipped to [-0.99, 0.99]); compute `z_R` and `z_S` per cell with their own weights, then pool by weighted mean; require all four cells to be estimable for a candidate to be ranked, otherwise `NOT_RANKABLE` (no Gate 2 ambiguity); and report the bootstrap SE of `Sc` beside the 0.02 margin.

5. **MEDIUM. The tie-break "largest absolute pooled D" rewards extreme thresholds and ignores direction.**
   Where: notes section 3, step 3.
   B0 has no pressure term. A higher `rrr` quantile selects rows that are mechanically harder, so |D| rises with the quantile. Using the absolute value would also accept a definition whose pressure rows do *better* than baseline. This is the same population-size mistake as before, just moved to D.
   Fix: declare the expected sign per stream before the run (batter runs per ball below baseline, dismissal rate above, bowler runs above baseline), count only D in the expected direction, and state in the report that D grows with the threshold by construction. Use D to compare only among candidates with the same quantile, or keep D as a report-only metric and break ties by lexicographic `definition_id`.

6. **MEDIUM. The eligibility rule can pass almost any threshold, and "reproducibility not significantly negative" is undefined.**
   Where: notes section 6, rules 1 and 2.
   Rule 1 uses the *median* data weight over eligible players. A threshold of 6 balls passes if the median eligible player has 60 balls. That does not mean a player at the threshold has weight 0.5. Rule 2 then picks the smallest passing threshold, so the rule is close to "lowest rung". The fallback in rule 3 picks the best reproducibility among candidates with at least 5 players, a maximum over noisy values with no correction.
   Fix: define the gate on the player at the threshold: `B(t) = t_neff / (t_neff + k) >= 0.5`, where `t_neff` is the `n_eff` that a player with exactly `t` balls has (state the formula, or use the observed `n_eff` of the lowest-count eligible player). Define "significantly negative" (for example: the bootstrap 95% interval of the Spearman correlation lies entirely below 0). For the fallback, report the candidate list and require n ≥ 15 players for any reproducibility figure, otherwise `REPRODUCIBILITY_NOT_ESTIMABLE`.

7. **MEDIUM. The window used to count pressure balls for eligibility, and for the shrinkage target `mu_{-i}`, is ambiguous.**
   Where: plan sections 3 and 4; notes sections 1, 4, 6.
   Thresholds are derived from TRAIN distributions, but user-facing scores use the pooled PRE_TEST window, which is longer (about 1.5 times the TRAIN ball count for IPL). Applying a TRAIN-derived ball threshold to PRE_TEST counts is looser than the threshold implies. Notes section 4 says "parameters stay TRAIN-fitted, data in the player estimate come from the scoring window" but does not say whether `mu_{-i}` is from TRAIN or the scoring window. Decision 2 says "training-period data only".
   Fix: state explicitly (a) which window's ball counts decide eligibility for PRE_TEST scoring (and rescale the threshold by the stated window ratio, or apply it to the TRAIN counts), and (b) that `mu_{-i}` is the pooled mean of other players' residuals from the same window as the player's `r_i`, or from TRAIN only. If the scoring window is used, document it as a deviation from "training only" and add the TRAIN-only variant as a sensitivity.

8. **MEDIUM. Frozen-choices integrity and the lock are not auditable.**
   Where: plan section 7; notes section 8.
   `evaluate_on_test` checks that the frozen file's SHA-256 matches "the recorded" hash, but the plan does not say where that hash is recorded. If it is recorded in the same file or in a file the same code can rewrite, the check proves nothing. The log has no wall-clock time (for determinism), so the order "freeze before open" cannot be shown. `LockedFrame` stops accessors only, so a direct DuckDB query or a pandas read of a `p4_*` table bypasses the lock.
   Fix: write the frozen-file hash into the lock log (and the Chunk report) at freeze time as a separate, append-only entry with a sequence number. Require `evaluate_on_test` to see freeze entry N and then write open entry N+1. Add a non-hashed audit file with file modification times. Store TEST outcome tables only under a name prefix (`p4_test_locked_*`) that no non-evaluation module imports, and add a test (static grep over `app/phase4`) that no other module references it.

9. **MEDIUM. Classification and API stats can leak TEST-period facts, and "played a T20I" is not defined.**
   Where: notes sections 9 and 11.
   `Capped` is derived from any T20I appearance "in the data", including 2026 TEST-period matches. A player who debuts in 2026 would be Capped when scoring 2022-2025 performance, which makes "uncapped at the time" wrong for the evaluation. Profile endpoints give "performance stats", but the source is not stated, and could include TEST-period outcomes before the lock opens. "Appeared" is not defined (playing-eleven row, ball faced, or ball bowled).
   Fix: add an `as_of_date` to the classification (default: end of PRE_TEST, 2025-12-31) and record the first T20I date. Define appearance as "listed in `playing_eleven` for a T20I match", or choose another definition and state why. State that profile/ranking endpoints read only `p4_*` tables and exclude TEST-period outcome fields until `evaluate_on_test` has completed.

10. **MEDIUM. The selection optimiser has no defined score scale, direction, or all-rounder handling.**
    Where: notes section 10.
    Every player has a score "sorted descending", but batter and bowler pressure scores are on different scales, and a bowler's lower runs conceded is better. A player can have both a batter and a bowler score. The role grouping says "Wicket Keeper/All Rounder grouped as in the squad file's four roles", which is ambiguous (four roles, but the names list reads as two roles folded in), and the roles of players outside the squad file are not specified.
    Fix: define `selection_score` as the shrunk residual converted to "higher is better" (negate for bowler runs conceded), standardised per (role, format) with TRAIN parameters, and say which role a two-sided player is selected under (the role with the higher standardised score, or both entries with a no-double-count rule). Enumerate the four role values and the role for players absent from the squad file (`Unknown`, excluded from role-constrained requests).

11. **MEDIUM. The format-combined estimate and Stage D/E procedures are not specified in these documents.**
    Where: notes section 4 (last bullet), absent elsewhere.
    The brief requires the eight-weight analysis, Top-10 overlap "where meaningful", rank movement, bootstrap stability, the baseline alternatives (with/without season offsets, coarser/finer cells), and ranking-stability measures (rank intervals, inclusion probability, expected overlap). The notes say only that combination happens "after shrinkage" for players eligible in both. They give no formula or interval rule for the combined score, no rule for the "meaningful" Top-10 overlap (pool size below ten), and no definition for the baseline alternatives.
    Fix: add a section giving the combined estimate `w_ipl * m_ipl + w_t20i * m_t20i` with the config weights, an interval by bootstrapping IPL and T20I matches independently, and a rule: the overlap is reported only when both pools have at least 10 players, otherwise report the overlap `k` as `min(pool_a, pool_b)` and mark it `TRIVIAL_FULL_POOL`. List the baseline alternatives by id.

12. **MEDIUM. The shrinkage choice rule uses an undefined standard error.**
    Where: notes section 4, choice rule.
    "Differences within one bootstrap standard error go to `shrink_eb`" does not say the standard error of what (the loss difference between two configurations? paired by player or by match?). The grid also mixes floors (0.01, 0.001) and multipliers.
    Fix: define it as the match-cluster bootstrap SE of the paired loss difference `loss(config) - loss(shrink_eb)`, and choose a non-default config only when its mean difference is below `-1 SE`.

13. **NIT. The rolling-origin folds are not out-of-sample unless parameters are refit per origin.**
    Where: plan section 6.
    The 2024-01-01 origin evaluates 2024 data that is inside TRAIN (the primary TRAIN fit includes 2024). Fix: state that baseline cells and shrinkage parameters are refit on data before each origin.

14. **NIT. Selection-stability bootstrap scope.**
    Where: notes section 3, step 4.
    State whether each of the 1,000 resamples recomputes the TRAIN-only quantile thresholds and the baseline, or holds them fixed. Fix: recompute thresholds per resample, hold the baseline fixed, and say so.

## Verified Assumptions

- Match counts by period (re-queried on `superr.duckdb`): IPL 219/74/74, T20I 278/122/70, OTHER_T20 15/15/0. They match the plan and sum to 367, 470 and 30.
- 42 T20I matches with deliveries are dated after 2026-05-31, so TEST_CORE is 28 T20I matches (70 minus 42). This matches the plan.
- Per-limit shortened-innings table: deliveries sum to 3,404 and innings to 50, which matches the stated DLS exclusion count and the correction of the "48" figure.
- `par_columns` computes strictly prior par with `np.searchsorted(..., side="left")` on dates, so same-date matches are excluded. `min_prior_innings` is 30 in `pressure_rules_v1.json`. The par NULL path exists (`np.where(k >= min_prior, prior, nan)`), but there is no `par_unavailable_insufficient_prior` flag column yet; the design correctly says to add it.
- `k_from_children` implements `tau2 = max(between, floor * sigma2)` and `k = sigma2 / tau2`, so `k <= 1 / floor`. `shrink_to_parent` and `pooled_other_mean` exist as described. `tau2_floor` is 0.01 with sensitivity [0.001, 0.1] in the config. Reuse is feasible.
- `min_data_weight` 0.5 and the confidence ladder helpers (`percentile_candidates`, `practical_candidates`, `build_ladder`) exist in the repo.
- The DP state-count claim holds: 4-vectors with sum at most 10 number C(14,4) = 1,001.
- The plan's table totals are consistent with the notes (pressure-ball percentiles and the 24 and 36 ball counts match between the two documents).
- The plan claims it used only dates, competition types and pre-delivery state columns. Nothing in either document shows an outcome column.

## Unverified/Wrong Assumptions

- Not verified: the pressure-ball counts, `rrr` quantiles, P50/P90 figures, par-NULL counts (3,737 and 3,955 rows) and squad/name-match counts (232/23/2, 719 of 1,217). They come from queries I did not re-run. The plan itself says Chunk 1 recomputes the pressure counts.
- Wrong or unsupported: "unique exact name match = VERIFIED_FROM_SOURCE" (finding 2).
- Unsupported: that the current inn1/bowler signals can be reused with "TRAIN-only quantile thresholds" and still be leakage-free (finding 1). The code uses LOMO columns and full-sample ranks.
- Unverified: whether the 2026 T20I dates (to 2026-11-01) are real. The design correctly keeps them as recorded, adds TEST_CORE, and lists the question as O3.
- Unverified: that `phase4_plan.md` (referenced, not provided to me) contains the format-weight and Stage E procedures. If it does, finding 11 reduces to adding a cross-reference.
