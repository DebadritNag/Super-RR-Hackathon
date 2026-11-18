# Pressure Top 10: submitted ranking status

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

**Read this first.** The lists below are ordered (10 batters, 10 bowlers; none is padded), but neither is validated. The declared reliability thresholds were not met by any approach, so both lists carry the label EXPLORATORY. They are the best-supported ordering of the available data, not evidence that these players are reliably better under pressure than the players ranked below them.

## 1. Two statuses, kept apart

ranking_status is the status of the submitted order. model_validation_status is the status the approach earned on the declared reliability tests. Neither can be stronger than the declared thresholds allow.

| role | approach | rank_basis | submitted ranking status | model validation status | players listed | eligible players | split-half (Spearman-Brown) | interval low | interval high |
|---|---|---|---|---|---|---|---|---|---|
| batter | A (context-adjusted performance) | REML_POSTERIOR | EXPLORATORY | EXPLORATORY | 10 | 225 | 0.057 | -0.220 | 0.361 |
| bowler | C (Pressure Response Index) | PRI_REML_POSTERIOR_COMPONENTS | EXPLORATORY | EXPLORATORY | 10 | 221 | 0.267 | -0.078 | 0.391 |

## 2. Why neither list is PROVISIONAL or VALIDATED

Thresholds declared before any result (criteria hash `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`): PROVISIONAL needs split-half reliability of at least 0.5 with a lower bound above 0 and an out-of-time lower bound above 0; VALIDATED needs at least 0.7 with a lower bound of at least 0.5 and an out-of-time lower bound above 0.3.

- **Batters**: split-half 0.06 below 0.5; split-half lower bound not above 0.
- **Bowlers**: split-half 0.27 below 0.5; split-half lower bound not above 0.

## 3. Phase 6 findings still apply

- Between-player variance sits at the shrinkage floor in all 48 contexts.
- Pooled odd/even reliability is 0.37 (0.3656); the median over the 47 estimable contexts is 0.25.
- No context passes the 0.5 data-weight gate (0 of 48).
- No pressure definition passed the predeclared criteria; rankings are sensitive to definitions and resampling.
- Phase 8 changed the method (continuous intensity, richer expected-outcome models, match-level units, REML) and tested whether the result improved. It improved the technical pipeline and left the central finding in place: the data do not separate players reliably. The Phase 6 data-weight gate (0.5) was not lowered and is reported unchanged: no approach passes it.

## 4. How the submitted approach was chosen

- **Batters**: Chosen approach A by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects A and the point-estimate path selects A: the two paths agree.
- **Bowlers**: Chosen approach C by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects C and the point-estimate path selects C: the two paths agree.

Approach selection used only approach-level metrics (split-half and out-of-time reliability, inclusion concentration, an explainability checklist), never a player's rank or name.

## 5. What the lists can and cannot be used for

- They can be used as a transparent, reproducible description of who performed best against the model's expectation in difficult match situations in 2022 to 2025.
- They cannot be used to claim that the order is reliable. Each player's 95% rank interval spans many places (see the CSV columns `rank_interval_low` and `rank_interval_high`), and 5 of 10 listed batters have a top-10 inclusion probability of at least 50%; 5 of 10 listed bowlers have a top-10 inclusion probability of at least 50% (the share of 1000 match-cluster bootstrap draws in which the player is in the Top 10).
- The pressure definition used (P4, resource scarcity) did not pass the predeclared validity tests (the monotonic trend test failed for every candidate). It is the best available candidate, not a validated definition.
- A player outside the lists may be as good or better. Missing evidence is never reported as poor performance.

### Interval caveat

The score interval is a 95% percentile interval of a match-cluster bootstrap in which the between-player variance is re-estimated in every draw. For Approach C the draws sit above the point estimate (the scale is held at its full-sample value while the shrinkage changes), so the interval is skewed and is flagged in the `interval_flag` column. Flagged rows: 0 of 10 batters, 9 of 10 bowlers. The rank interval and the top-10 inclusion probability use every draw and are the better guide to how firm a position is.

## 6. Label definitions

- **VALIDATED**: The approach reached split-half reliability of at least 0.70 (interval lower bound at least 0.50) and an out-of-time correlation lower bound above 0.30, as declared before any result.
- **PROVISIONAL**: The approach reached split-half reliability of at least 0.50 with an interval lower bound above 0 and an out-of-time correlation lower bound above 0, but not every VALIDATED threshold.
- **EXPLORATORY**: An ordered list exists, but the declared PROVISIONAL thresholds were not met. The order is the best available description of the data and is not shown to separate players beyond noise.
- **INSUFFICIENT_EVIDENCE**: Fewer than ten players meet the declared eligibility floors or the approach cannot be computed. A player with this label is not ranked; it says nothing about the quality of the player.

A row never carries a stronger label than its list. VALIDATED rows need a VALIDATED list, the STRONG_SUBSTANTIAL evidence class and a Top-10 inclusion probability of at least 0.5. PROVISIONAL rows need a list of at least PROVISIONAL and an inclusion probability of at least 0.25. Every other ranked row is EXPLORATORY.

## 7. What would change the status

- More matches per player (the declared reliability grows with the sample), or a pressure definition that passes the predeclared validity tests, together with split-half reliability of at least 0.5 and a positive lower bound on held-out matches.
- Using the 2026 matches would add data, but that period was opened once in Phase 4 and is not a clean hold-out; it needs an explicit owner decision and a labelled application.

## 8. Players in the lists

**Batters** (approach A (context-adjusted performance))

| rank | player_name | pressure_score | interval_low | interval_high | top10_inclusion_probability | evidence_class | ranking_status |
|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 0.0440 | 0.0306 | 0.0590 | 0.9130 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Tim David | 0.0386 | 0.0255 | 0.0517 | 0.8260 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Heinrich Klaasen | 0.0336 | 0.0243 | 0.0436 | 0.5990 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | Romario Shepherd | 0.0328 | 0.0220 | 0.0438 | 0.6320 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Andre Russell | 0.0323 | 0.0202 | 0.0450 | 0.5220 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Tristan Stubbs | 0.0307 | 0.0199 | 0.0426 | 0.4170 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | David Miller | 0.0305 | 0.0178 | 0.0446 | 0.3260 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Rinku Singh | 0.0301 | 0.0180 | 0.0422 | 0.3140 | INCONSISTENT | EXPLORATORY |
| 9 | Nicholas Pooran | 0.0299 | 0.0166 | 0.0432 | 0.2320 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 10 | Mark Chapman | 0.0292 | 0.0182 | 0.0408 | 0.4110 | STRONG_SUBSTANTIAL | EXPLORATORY |

**Bowlers** (approach C (Pressure Response Index))

| rank | player_name | pressure_score | interval_low | interval_high | top10_inclusion_probability | evidence_class | ranking_status |
|---|---|---|---|---|---|---|---|
| 1 | Matheesha Pathirana | 3.6132 | 3.0641 | 9.2850 | 0.8630 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Kuldeep Yadav | 3.0271 | 1.8085 | 7.5369 | 0.5550 | INCONSISTENT | EXPLORATORY |
| 3 | Jasprit Bumrah | 2.8289 | 1.5024 | 7.6972 | 0.5560 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | Varun Chakravarthy | 2.8151 | 1.3280 | 7.1786 | 0.4530 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Sunil Narine | 2.7856 | 1.4815 | 7.8043 | 0.5670 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Akeal Hosein | 2.7590 | 1.4790 | 7.5519 | 0.5440 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | Rashid Khan | 2.4892 | 0.9857 | 6.2976 | 0.2690 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Mohammad Nawaz | 2.4317 | 1.0627 | 7.5332 | 0.4930 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Wanindu Hasaranga | 1.9309 | -0.0333 | 5.8102 | 0.1430 | STRONG_LIMITED | EXPLORATORY |
| 10 | Abbas Afridi | 1.8937 | 0.7330 | 7.6883 | 0.4400 | STRONG_SUBSTANTIAL | EXPLORATORY |

