# Pressure Top 10: submitted ranking status (Phase 9)

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.32 below 0.5; split-half lower bound not above 0.

**Read this first.** Window 2022-01-22 to 2026-11-01, 2026 included by owner decision D1 (owner attestation). There is no pristine hold-out left. The label of each list is the label the evidence earned under thresholds declared before any result (criteria SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`, unchanged). Result: EXPLORATORY.

## 1. Status of each list

| role | approach | rank basis | submitted ranking status | model validation status | players listed | eligible players | split-half | interval low | interval high | out-of-time lower bound |
|---|---|---|---|---|---|---|---|---|---|---|
| batter | A | REML_POSTERIOR | EXPLORATORY | EXPLORATORY | 10 | 256 | 0.019 | -0.184 | 0.359 | -0.054 |
| bowler | C | PRI_REML_POSTERIOR_COMPONENTS | EXPLORATORY | EXPLORATORY | 10 | 156 | 0.319 | -0.107 | 0.386 | 0.059 |

## 2. Thresholds and what was earned

PROVISIONAL needs split-half reliability of at least 0.5 with a lower bound above 0 and an out-of-time lower bound above 0. VALIDATED needs at least 0.7 with a lower bound of at least 0.5 and an out-of-time lower bound above 0.3. Nothing was changed to reach a label.

- **Batters**: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.
- **Bowlers**: split-half 0.32 below 0.5; split-half lower bound not above 0.

## 3. How the approach was chosen

- **Batters**: Chosen approach A by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects A and the point-estimate path selects A: the two paths agree.
- **Bowlers**: Chosen approach C by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects C and the point-estimate path selects C: the two paths agree.

## 4. What the lists can and cannot be used for

- They describe who performed best against the model's expectation in difficult situations from 2022 to 2026, with each player's evidence.
- A list whose label is below PROVISIONAL is not evidence that the order would repeat. Each player has a 95% rank interval (CSV columns `rank_interval_low` and `rank_interval_high`) and a Top-10 inclusion probability.
- The pressure definition (P4, resource scarcity) did not pass the predeclared validity rule (the monotonic trend test fails for every candidate); it is the best available, not validated.
- A player outside the lists may be as good or better. Missing evidence is never reported as poor performance.

## 5. Evidence and data caveats

- 2026 data are an owner attestation, not an official verification (cross-source check: 36 of the 42 late-dated T20I matches consistent, 6 single-source, 0 conflicts).
- The 2026 out-of-time check of the models used data held out earlier; nothing was tuned on it, but it is not an independent test.

## 6. Players in the lists

**Batters** (approach A)

| rank | player_name | pressure_score | interval_low | interval_high | top10_inclusion_probability | evidence_class | ranking_status |
|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 0.0345 | 0.0244 | 0.0455 | 0.8820 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Tim David | 0.0326 | 0.0226 | 0.0425 | 0.8690 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Heinrich Klaasen | 0.0277 | 0.0205 | 0.0360 | 0.5110 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 4 | David Miller | 0.0265 | 0.0172 | 0.0370 | 0.3830 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Rinku Singh | 0.0265 | 0.0166 | 0.0364 | 0.3810 | INCONSISTENT | EXPLORATORY |
| 6 | Andre Russell | 0.0263 | 0.0174 | 0.0359 | 0.5140 | INCONSISTENT | EXPLORATORY |
| 7 | Romario Shepherd | 0.0261 | 0.0186 | 0.0344 | 0.5410 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Tristan Stubbs | 0.0256 | 0.0179 | 0.0340 | 0.3750 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Shreyas Iyer | 0.0248 | 0.0161 | 0.0342 | 0.3030 | INCONSISTENT | EXPLORATORY |
| 10 | Shivam Dube | 0.0238 | 0.0158 | 0.0325 | 0.1570 | INCONSISTENT | EXPLORATORY |

**Bowlers** (approach C)

| rank | player_name | pressure_score | interval_low | interval_high | top10_inclusion_probability | evidence_class | ranking_status |
|---|---|---|---|---|---|---|---|
| 1 | Sunil Narine | 3.6470 | 3.4355 | 7.9420 | 0.9770 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 2 | Matheesha Pathirana | 2.9185 | 2.2140 | 7.0689 | 0.8630 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 3 | Kuldeep Yadav | 2.6776 | 1.3149 | 6.5073 | 0.6420 | INCONSISTENT | EXPLORATORY |
| 4 | Jasprit Bumrah | 2.6634 | 1.5215 | 6.7617 | 0.7000 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 5 | Varun Chakravarthy | 2.4053 | 0.9899 | 5.8373 | 0.5060 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 6 | Abrar Ahmed | 1.8407 | 0.6667 | 6.2021 | 0.4830 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 7 | Rashid Khan | 1.7636 | 0.3329 | 4.3898 | 0.1680 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 8 | Akeal Hosein | 1.7472 | 0.2056 | 5.6218 | 0.3490 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 9 | Wanindu Hasaranga | 1.6494 | 0.1234 | 4.7273 | 0.1950 | STRONG_SUBSTANTIAL | EXPLORATORY |
| 10 | Mohammad Nawaz | 1.6336 | -0.0238 | 5.8135 | 0.3570 | STRONG_LIMITED | EXPLORATORY |
