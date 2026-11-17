# Phase 4 Chunk 3 verification

Environment: PowerShell, `$env:PYTHONUTF8=1`, Python 3.11, cwd `d:/Data/backend`.

## Built
- `app/phase4/engine.py`: pressure-row tables (through `guard_frame`), player x match matrices, one global seeded match-cluster resample matrix, bootstrap draws, rank utilities (`rank_summary`: Top-10 inclusion, expected overlap, Jaccard, Spearman, rank intervals, never padded).
- `app/phase4/definitions.py` + `config/phase4_definition_rule_v1.json` (written before any metric; SHA-256 recorded): nine-candidate comparison, Gate 1 (floor), R split-half, S TRAIN-to-VALIDATION stability, D/SNR/population/par availability report-only, selection share, winner PROVISIONAL, full table retained, population never a selector.
- `app/phase4/eligibility.py`: data-derived per-cell (IPL/T20I x batter/bowler) thresholds, candidate metrics (opportunities, matches, n_eff, interval width, bootstrap Jaccard/pool interval, reproducibility with bootstrap CI), pre-declared decision rule, labelled working pool when nothing is validated.
- `app/phase4/sensitivity.py`: shrinkage sensitivity, eight-config format weights over one shared eligibility rule set, baseline alternatives, ranking stability (baseline, threshold variants, shrinkage variants).
- `scoring.py`: optional `elig`/`elig_rules` (default behaviour and records unchanged). `baseline.py`: optional `first_level`, `no_offset`, `version` (defaults unchanged).
- `scripts/phase4_sensitivity.py`: order definition -> shrinkage (VALIDATION) -> eligibility -> `phase4_frozen_choices.json` (FREEZE logged) -> sensitivities -> Stage C records for all nine definitions under the frozen rules.
- Tests: `tests/test_phase4_chunk3.py` (26).

## Commands and results
| command | result |
|---|---|
| `python scripts/phase4_sensitivity.py` | chosen `any|q0.75` (PROVISIONAL rule winner), shrinkage `shrink_tau4`, 19,762 score records, official data unchanged True, about 1.3 minutes |
| `python -m pytest -q` | 417 passed (391 + 26), 2 pre-existing warnings |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 139 files already formatted |

`superr.duckdb` SHA-256 CB4077EE...391D equals `phase4_hash_before.txt`; source CSVs checked by the script's snapshot. Writes went only to `p4_*` tables in `exploratory.duckdb` and to `data/reports`.

## Outputs (data/reports)
`phase4_definition_comparison.{md,csv,json}`, `phase4_definition_candidates.csv`, `phase4_definition_selection.json`, `phase4_eligibility_validation.md`, `phase4_eligibility_candidates.{csv,json}`, `phase4_eligibility_frozen.{csv,json}`, `phase4_shrinkage_sensitivity.{md,csv,json}`, `phase4_shrinkage_choice_final.json`, `phase4_format_weight_sensitivity.md`, `phase4_format_weight_{results,pairwise,players}.{csv,json}`, `phase4_ranking_stability.md`, `phase4_ranking_{distributions,summary,threshold_variants}.{csv,json}`, `phase4_baseline_alternatives.{md,csv,json}`, `phase4_pressure_scores_frozen_rules.{csv,json}`, `phase4_frozen_choices.json`. Tables: `p4_definition_comparison`, `p4_definition_candidates`, `p4_eligibility_candidates`, `p4_eligibility_frozen`, `p4_shrinkage_sensitivity`, `p4_format_weight_{results,pairwise,players}`, `p4_ranking_{distributions,summary,threshold_variants}`, `p4_baseline_alternatives`, `p4_pressure_scores_frozen_rules`.

## Findings
- Definition: `chase|q0.95` and `inn1|q0.95` are NOT_RANKABLE (fewer than 15 players in some cell for S). The top group (`any|q0.9`, `chase|q0.75`, `any|q0.75`) is statistically indistinguishable (Sc 0.26, 0.25, 0.24; SE 0.04 to 0.06); `any|q0.75` wins by the pre-declared lexicographic tie-break and has the largest pressure population, which the report flags together with a sample-size confound check. `chase|q0.9` is rankable (Sc 0.17) but not in the top group. Selection shares are 0.33 / 0.30 / 0.15, so the choice is weak.
- Between-player variance (SNR) is negative in every cell: residual means show no detectable between-player spread beyond noise, bowler split-half reliability is near 0, so shrinkage is strong and rankings are fragile (expected Top-10 overlap about 5 to 6 of 10).
- Eligibility: all four cells are THRESHOLD_NOT_VALIDATED (marginal data weight never reaches 0.5; no candidate has estimable positive reproducibility with weight >= 0.1). No threshold was lowered. Downstream experiments use the labelled `ELIGIBLE_WORKING_POOL_NOT_VALIDATED` pool (TRAIN median of per-player pressure balls: IPL batter 20, T20I batter 16, IPL bowler 49, T20I bowler 29). Pools: 132 / 243 / 80 / 141; combined (both formats) 48 batters, 39 bowlers.
- Format weights: batter Top-10 overlap with 70:30 (pool 48) is 9 for IPL-only, 85:15 and 80:20, 7 at 50:50 and 3 for T20I-only (Spearman 0.95 to 0.99 for 100:0 to 50:50, 0.46 for T20I-only); bowlers (pool 39) 5 for T20I-only, 9 to 10 elsewhere; 70:30 is not validated.
- Baseline alternatives: Spearman against B0 above 0.95 in all cells.

## Spot checks (independent of the code path that produced them)
1. Spearman of `w0_100` vs `w70_30`, recomputed with scipy from the stored player table: batter 0.459184 (stored 0.459184, n=48), bowler 0.605263 (stored 0.605263, n=39).
2. Stage C record arithmetic: B = n_eff / (n_eff + k) holds to 1e-16 on 267 IPL batter records; the implied shrink target (shrunk - B x residual)/(1 - B) lies in 0.005 to 0.020, consistent with a pooled leave-player-out mean.
3. Top-10 inclusion probabilities sum to exactly 10.0 in each of the four pools (pools 132 / 80 / 243 / 141).

## Deliberate deviations and open items
- `evaluate_on_test` was NOT run. The frozen file and FREEZE log entry exist; TEST rows were never loaded and the lock stayed closed. The single test evaluation is left to the orchestrator in Chunk 5.
- Bowler pressure still uses the batter state signals (bowler signal B not implemented); stated in the reports.
- The bootstrap holds TRAIN-only thresholds fixed (not refitted per resample); stated in the rule file and report.
- `shrink_mu_window` and the unscaled-eligibility sensitivities were not run; stated in the shrinkage report.
- Stage E ranking score uses the primary stream only (runs for batters, runs conceded for bowlers).
- The repository is not a git repository, so no commit was made.
