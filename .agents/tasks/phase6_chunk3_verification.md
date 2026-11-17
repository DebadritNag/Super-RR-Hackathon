# Phase 6 chunk 3 (definition/context reliability, eligibility, data-weight options) verification
Working directory `d:/Data/backend`, `$env:PYTHONUTF8=1`, interpreter `python` (3.11). The workspace is not a git repository, so nothing was committed. The gate file `phase6_chunk3_gate.json` did not exist, so this is a from-scratch implementation.

## What was built
- Modules `app/phase6/`: `definition_compare.py` (metrics R, M2 to M5, control M6, pass list, top group, stability, confounding, run guard), `context_reliability.py`, `eligibility_reliability.py`, `data_weight_options.py` (options validator, Kish and match-cluster data weight, REML/MAD `tau2`).
- Scripts: `scripts/phase6_definition_compare.py`, `phase6_context_reliability.py`, `phase6_eligibility_reliability.py`, `phase6_data_weight_options.py`. Each calls `criteria.begin_step` (or `definition_compare.begin_comparison`), hashes the `p4_`/`p5_` tables and the Phase 4 lock log before and after, and ends with the preservation check.
- Tables in `exploratory.duckdb`: `p6_definition_reliability`, `p6_definition_summary`, `p6_definition_resampling`, `p6_definition_outcome`, `p6_context_reliability`, `p6_context_reliability_groups`, `p6_eligibility_reliability`, `p6_eligibility_targets`, `p6_eligibility_projection`, `p6_eligibility_n_eff`, `p6_data_weight_options`, `p6_data_weight_option_summary`, `p6_data_weight_gate_status`, `p6_data_weight_cluster_tau2`.
- Reports in `data/reports/`: `phase6_definition_reliability_comparison.md`, `phase6_context_reliability.md`, `phase6_eligibility_reliability.md`, `phase6_data_weight_improvement_options.md` (+ `.csv`/`.json` for every table and `phase6_gate_guard.json`).
- Tests (78 new): `test_phase6_definition_compare.py` (22), `test_phase6_definition_guard.py` (11), `test_phase6_gate_options.py` (30), `test_phase6_context_eligibility.py` (15).

## Commands and results
| command | result |
|---|---|
| `python scripts/phase6_definition_compare.py` | exit 0, ~60 s; 72 cell rows (9 definitions x 4 cells x 2 windows); final status `NO_DEFINITION_PASSES`; criteria verified (seq logged); `all_preserved: true` |
| `python scripts/phase6_context_reliability.py` | exit 0, ~56 s; 48 contexts, 47 estimable; stored Phase 5 data weight reproduced (max abs diff in B 0.0, 0 gate-state differences, 0 eligible-count differences); ALL/ALL equals the primary cell in 4/4; 0/48 pass the gate |
| `python scripts/phase6_eligibility_reliability.py` | exit 0, ~26 s; 125 ladder/frozen/candidate rows, 24 target rows, 24 projection rows; reproduces `reliability_by_opportunity` (32 steps, max abs diff 0.0); eligibility rules, gate config and frozen choices hashed before/after, equal |
| `python scripts/phase6_data_weight_options.py` | exit 0, ~30 s; 304 option rows, 19 option ids; 0 of 256 applicable rows pass the 0.5 gate; `validate_options_table` passed; `phase6_gate_guard.json` written |
| all four scripts run a second time, CSV/JSON hashes compared | 29 files, 0 differences (seeded, deterministic) |
| `python -m pytest -q` | **995 passed** (917 before + 78 new), 3 warnings, 589 s |
| `python -m ruff check .` / `python -m ruff format --check .` | All checks passed / 288 files already formatted |

## Independent spot checks (throwaway script, deleted afterwards)
Recomputed from raw pressure rows with pandas/numpy, without the module code:
1. Definition comparison cell `chase|q0.9`, T20I batter, PRE_TEST: individuals 52, odd/even SB 0.6848050605 (module 0.6848050605), M4 median balls 32 (module 32).
2. Eligibility ladder IPL batter, pool of at least 30 balls: pool 126, estimable 125, SB 0.52805732131693 (module 0.5280573213169297).
3. Measured n_eff >= k: IPL bowler PRE_TEST has 1 individual with Kish count >= 25, 434 balls, max n_eff 25.4466 (module identical).
4. Match-cluster data weight of the marginal eligible individual, IPL batter ALL/first_innings (O6 row): v_max recomputed from `p5_context_stats` gives B 0.412995172887114 and marginal n_eff 8.1152774 (module identical).

## Preservation and constraints
- `phase6_prerun_hashes.json` (146 files): 145 unchanged; only `exploratory.duckdb` differs (new `p6_` tables). Every script hashed all `p4_` and `p5_` tables before and after: unchanged. Phase 4 lock log SHA unchanged (`cae1e06c...eb75c`); Phase 5 lock log has 0 events; `test_opened: false`; superr.duckdb unchanged.
- The gate stays 0.5: `GATE_B` is read in four places and assigned nowhere in Phase 6; AST tests find no numeric gate below 0.5 assigned anywhere under `app/` or `scripts/` and no use of the Phase 4 `ALT_GATES`; `gate_used` is 0.5 in all 304 option rows and all 48 gate-status rows; the options report lists the lowered-gate idea only under "Excluded by rule". The pre-existing Phase 4 constant `ALT_GATES = (0.3, 0.1)` in `app/phase4/eligibility.py` (used by the Phase 4 sensitivity report) was not touched and no Phase 6 code reads it.
- Criteria-hash refusal: tests cover missing hash file, missing criteria file, criteria edited after the hash, hash file rewritten to match edited criteria (the run log still holds the original), no plan row, stored result tables under another hash or without a hash column.
- No TEST rows, no Cricsheet, no player column in any definition table (tested on real CSVs and synthetic builders).

## Key findings (all from the reports)
- Definition comparison (PRE_TEST, nine definitions, four cells): no definition passes (needs R estimable in all four cells and lower bound above 0 in at least three). `any|q0.75` has lower bound above 0 in 2 of 4 cells. The individuals eligible under all nine definitions number 3, 19, 2 and 11 (IPL batter, IPL bowler, T20I batter, T20I bowler), below the 30 the rule needs, so the comparison is confounded and the intersection versions of M1 and M5 are not interpretable. No bowler cell has a lower bound above 0 under `any|q0.75`. The match-bootstrap interval midpoint is below the point estimate in 33 of 36 cells (disclosed in the report). TRAIN-only repeat also passes nothing, so no instability flag arises. Nothing about players was used; `any|q0.75` stays provisional.
- Resampling instability (M5): median Spearman correlation of resample versus full-window ordering 0.71 to 0.79 across definitions; 5th percentile as low as 0.43 for `inn1|q0.95` IPL bowler.
- Context reliability: SB median 0.25 over 47 estimable contexts; lower bound above 0 in 12 contexts (individual bootstrap) and 5 (match bootstrap). Middle-overs contexts have the lowest SB (median 0.14, no lower bound above 0). All 48 contexts stay restricted (marginal n_eff 1.00 to 3.44 against k = 25).
- Eligibility: point SB reaches 0.5 in 2 of 4 cells (IPL batter at 30 balls, IPL bowler at 72) and 0.7 in none; no interval lower bound reaches 0.5. At the frozen scaled thresholds SB is 0.47 (IPL batter), 0.45 (IPL bowler), 0.33 (T20I batter), 0.41 (T20I bowler). Only 2 of 1345 individuals reach a Kish count of 25 (B = 0.5). Projections for R = 0.5: model-free E7 needs about 99 to 258 balls per individual depending on cell; the ball-independent E1b needs 13 to 39. Three of 18 projection rows have the point value outside its own bootstrap band (stated in the report).
- Data-weight options: none of 256 applicable rows passes. O6 (own-context match-cluster `tau2`) has one context whose estimable individuals reach 0.56, but that context has eligible individuals with a single match and no cluster-noise estimate, so the marginal individual is not estimable and it is not counted as a pass (93 O3/O6 rows are in that state). REML and MAD `tau2` disagree in 24 of 48 contexts. O3 and O6 need a methodology decision and were not applied.

## Honest limits
- Everything is in-sample on TRAIN and VALIDATION; TEST was opened once in Phase 4 and is not pristine; nothing is validation.
- The match-cluster bootstrap is shifted upward and match-bootstrap intervals are not centred; the reports say so wherever "lower bound above 0" counts appear.
- O3 is an empirical-Bayes hyperparameter pooling (parent-context `tau2`), not a full hierarchical model.
- The comparison cannot name a top group; this is a valid finding, not a failure to run.
