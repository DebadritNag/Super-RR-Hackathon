# Pressure Top 10 status

`pressure_batters_top10.csv` and `pressure_bowlers_top10.csv` are **intentionally not produced**. No such files exist.

## Why no defensible Top 10 exists
Figures are from the Phase 6 reports (`phase6_final_audit.md` recomputed them from the stored tables).
- Between-player variance sits at the shrinkage floor in all 48 contexts, so the data cannot separate players beyond the floor.
- Data-weight gate (marginal data weight 0.5): fails in all 48 contexts (0 of 48 pass).
- Pooled odd/even reliability of the provisional definition is 0.37; the median over 47 estimable contexts is 0.25; 0.5 is reached in 2 of 4 cells of the tested ball ladder; 0.7 and 0.8 are not reached.
- Within-season reliability median 0.24; adjacent-season correlation median 0.11.
- No pressure definition passes the predeclared criteria; `any|q0.75` is provisional, not validated.
- TEST was opened once in Phase 4, so no clean hold-out exists. Phase 4 TEST aggregates are non-pristine.
- 42 late T20I match dates are unverified and excluded; the strict uncapped classification is disabled for lack of a cap-status source with stable player ids.
- Phase 6 tested 18 improvement options; none reaches the 0.5 data-weight gate without a methodology change. The best option (marginal data weight 0.56) changes the methodology and is documented as unadopted.

## What exists instead
- Descriptive profiles and evidence-supported comparisons (public, no ranking claims).
- `experimental_ai_top10_batters.csv` and `experimental_ai_top10_bowlers.csv`: internal, token-protected, ordered by the output of the statistical baseline/shrinkage model (not machine learning or deep learning), labelled not validated. They are not the pressure ranking and must not be published or used for selection.

## What would change this
- A methodology or data change that raises the marginal data weight to the gate **and** shows improved reliability on a clean hold-out (reaching the threshold alone does not prove reliability).
- Official verification of the 42 T20I dates, a stable-id cap-status source, and a validated pressure definition and eligibility pools.

## No padding
No list is padded to reach ten players. A list with fewer than ten qualifying players is returned as is.
