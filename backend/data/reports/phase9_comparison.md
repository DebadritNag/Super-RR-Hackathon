# Phase 8 against Phase 9

Phase 8 used matches to 2025-12-19 (TRAIN to 2024-12-31, VALIDATION calendar 2025). Phase 9 adds the 2026 matches by owner decision D1 (window 2022-01-22 to 2026-11-01) and refits the models on matches to 2025-12-31 with the Phase 8 hyperparameters. The criteria file is unchanged (SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`). Every number below is read from `phase8.duckdb` (unchanged) and `phase9.duckdb`.

## 1. Top 10 overlap and rank changes

**Batters**: 8 of 10 players appear in both Top 10 lists.

| player | Phase 9 rank | Phase 8 rank | change | Phase 9 top-10 probability |
|---|---|---|---|---|
| Suryakumar Yadav | 1 | 1 | +0 | 88% |
| Tim David | 2 | 2 | +0 | 87% |
| Heinrich Klaasen | 3 | 3 | +0 | 51% |
| David Miller | 4 | 7 | +3 | 38% |
| Rinku Singh | 5 | 8 | +3 | 38% |
| Andre Russell | 6 | 5 | -1 | 51% |
| Romario Shepherd | 7 | 4 | -3 | 54% |
| Tristan Stubbs | 8 | 6 | -2 | 38% |
| Shreyas Iyer | 9 | not in Top 10 | new | 30% |
| Shivam Dube | 10 | not in Top 10 | new | 16% |

Left the Top 10: Nicholas Pooran (was 9), Mark Chapman (was 10).

Spearman correlation of the order over the 8 players in both Top 10 lists: 0.619.

**Bowlers**: 9 of 10 players appear in both Top 10 lists.

| player | Phase 9 rank | Phase 8 rank | change | Phase 9 top-10 probability |
|---|---|---|---|---|
| Sunil Narine | 1 | 5 | +4 | 98% |
| Matheesha Pathirana | 2 | 1 | -1 | 86% |
| Kuldeep Yadav | 3 | 2 | -1 | 64% |
| Jasprit Bumrah | 4 | 3 | -1 | 70% |
| Varun Chakravarthy | 5 | 4 | -1 | 51% |
| Abrar Ahmed | 6 | not in Top 10 | new | 48% |
| Rashid Khan | 7 | 7 | +0 | 17% |
| Akeal Hosein | 8 | 6 | -2 | 35% |
| Wanindu Hasaranga | 9 | 9 | +0 | 20% |
| Mohammad Nawaz | 10 | 8 | -2 | 36% |

Left the Top 10: Abbas Afridi (was 10).

Spearman correlation of the order over the 9 players in both Top 10 lists: 0.800.

## 2. Reliability change

| role | approach | Phase 8 split-half | Phase 9 split-half | Phase 9 interval | Phase 8 out-of-time low | Phase 9 out-of-time low | eligible P8 / P9 |
|---|---|---|---|---|---|---|---|
| batter | A (submitted in Phase 9) | 0.057 | 0.019 | -0.184 to 0.359 | 0.017 | -0.054 | 225 / 256 |
| batter | B | 0.042 | -0.013 | -0.389 to 0.294 | -0.201 | -0.342 | 224 / 148 |
| batter | C | 0.057 | -0.229 | -0.367 to 0.307 | -0.197 | -0.321 | 224 / 148 |
| bowler | A | 0.220 | 0.120 | -0.243 to 0.297 | -0.074 | 0.034 | 221 / 243 |
| bowler | B | -0.135 | -0.104 | -0.494 to 0.341 | -0.364 | -0.346 | 221 / 156 |
| bowler | C (submitted in Phase 9) | 0.267 | 0.319 | -0.107 to 0.386 | 0.027 | 0.059 | 221 / 156 |

- Batters: Phase 8 approach A (EXPLORATORY), Phase 9 approach A (EXPLORATORY). Reason stored for Phase 9: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.
- Bowlers: Phase 8 approach C (EXPLORATORY), Phase 9 approach C (EXPLORATORY). Reason stored for Phase 9: split-half 0.32 below 0.5; split-half lower bound not above 0.

The out-of-time test correlates 2022-2024 estimates with 2025-2026 estimates in Phase 9 (Phase 8: 2022-2024 with 2025). The Phase 9 split-half halves by match parity and by time are defined as in Phase 8.

## 3. What changed in the data and the models

- 2026 matches in scope: 144 (IPL 74, T20I 70); 137 contribute scored deliveries, 31,996 of 33,086 deliveries. The others are fully removed by the existing restrictions (DLS targets that cannot be reconstructed, innings 3 and 4 and Super Over rows, out-of-scope competition).
- Late-dated T20I matches: 40 of 42 contribute scored deliveries (the rest carry only restricted rows).
- Expected-outcome and win-probability models: same learners, same hyperparameters as Phase 8, refitted on matches to 2025-12-31; the 2026 balls are scored by those fits, and the earlier balls out of fold (`match_id % 5`).
- Win probability W1 (first innings) on the 2026 matches: calibration slope 0.621 (declared gate 0.8 to 1.2): gate passed = False. Because the gate failed, the unchanged Approach B rule removes first-innings win-probability credit (`INNINGS1_WP_NOT_RELIABLE`).

## 4. Eligibility floor sensitivity

The criteria file names the recent-activity floor `min_matches_2025_window` (4 matches). In Phase 9 it is applied unchanged to the most recent window, which is the VALIDATION period of the window labelling (calendar 2025 and 2026). Its only uses are the late half of the out-of-time test and the window sensitivity. A variant restricted to calendar 2025 alone was not run.

## 5. Sensitivity of the Phase 9 order

| role | family | comparison | n_common | spearman | top10_overlap |
|---|---|---|---|---|---|
| batter | pressure definition | intensity_P0 | 193 | 0.787 | 0 |
| batter | pressure definition | intensity_P3 | 144 | 0.611 | 2 |
| batter | pressure definition | intensity_P5 | 140 | 0.416 | 4 |
| batter | pressure definition | intensity_P6 | 142 | 0.711 | 2 |
| batter | format (IPL, T20I, combined) | scope_IPL_only | 119 | 0.796 | 7 |
| batter | format (IPL, T20I, combined) | scope_T20I_only | 170 | 0.820 | 3 |
| batter | assumption (ordering, weights, innings) | rank_by_pressure_delta | 184 | 0.535 | 1 |
| batter | assumption (ordering, weights, innings) | unshrunk_ordering | 256 | 0.925 | 2 |
| batter | eligibility floor | eligibility_floor_x0.5 | 256 | 0.997 | 10 |
| batter | eligibility floor | eligibility_floor_x2.0 | 152 | 0.995 | 9 |
| batter | component or approach | component_runs_only | 256 | 0.640 | 4 |
| batter | component or approach | component_wicket_only | 256 | 0.668 | 0 |
| batter | bootstrap | bootstrap_method_check | 31 | n/a | n/a |
| batter | calendar window | window_2022_2024 | 188 | 0.787 | 3 |
| batter | calendar window | window_2025 | 189 | 0.669 | 1 |
| bowler | component or approach | published_approach_A_rank | 156 | 0.945 | 8 |
| bowler | component or approach | published_approach_B_rank | 156 | 0.315 | 3 |
| bowler | component or approach | component_A_only | 156 | 0.944 | 8 |
| bowler | component or approach | component_B_only | 156 | 0.315 | 3 |
| bowler | component or approach | component_CONS_only | 156 | 0.954 | 9 |
| bowler | assumption (ordering, weights, innings) | equal_weights_not_data_derived | 156 | 0.906 | 9 |
| bowler | format (IPL, T20I, combined) | scope_IPL_only | 84 | 0.868 | 5 |
| bowler | format (IPL, T20I, combined) | scope_T20I_only | 87 | 0.903 | 7 |
| bowler | eligibility floor | eligibility_floor_x0.5 | 156 | 0.999 | 9 |
| bowler | eligibility floor | eligibility_floor_x2.0 | 78 | 0.998 | 10 |
| bowler | assumption (ordering, weights, innings) | unshrunk_ordering | 156 | 0.976 | 4 |
| bowler | format (IPL, T20I, combined) | hierarchical_format_common_effect | 156 | 0.999 | 10 |
| bowler | assumption (ordering, weights, innings) | innings2_units_only | 156 | 0.646 | 7 |
| bowler | bootstrap | bootstrap_method_check | 156 | n/a | n/a |
| bowler | calendar window | window_2022_2024 | 133 | 0.774 | 5 |
| bowler | calendar window | window_2025 | 140 | 0.681 | 1 |
| bowler | pressure definition | intensity_P0 | 147 | 0.684 | 7 |
| bowler | pressure definition | intensity_P3 | 126 | 0.578 | 6 |
| bowler | pressure definition | intensity_P5 | 141 | 0.425 | 3 |
| bowler | pressure definition | intensity_P6 | 136 | 0.635 | 7 |
