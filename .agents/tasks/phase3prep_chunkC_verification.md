# Phase 3 prep, chunk C verification (pressure eligibility and format-weight sensitivity)

Every output carries `status: EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`,
`not_for_publication: true`. No official Top 10, no ML training, no validated pressure score.
70:30 stays PROVISIONAL. Official DuckDB opened read-only; the integrity snapshot before/after each
script reported `official_unchanged=True`. Gate file `phase3prep_chunkC_gate.json` did not exist at
start, so this is a first implementation. Project root `d:/Data/backend`.

## Files added or changed

| File | Change |
|---|---|
| `config/pressure_eligibility_rules_v1.json` | New. Phase 2.5 harness settings, nominal ladders rescaled for pressure sample sizes (flagged nominal), pre-declared definition grid (chase / inn1 / any x q 0.75, 0.9, 0.95), selection rule text, baseline settings. |
| `app/analytics/pressure_eligibility.py` | New. Pressure sample builders (batter/bowler, residual streams), definition flags, per-candidate and B0 leave-player-out residuals, harness run per definition, rule uncertainty, both-format counts, selection rule, Phase 2.5 comparison. `confidence_engine.py` is reused unchanged: residual sums feed its `runs`/`econ`/`wkt` streams, so no `ScoreSpec` change was needed. |
| `app/analytics/pressure_eligibility_report.py` | New. Provisional recommendation text and Markdown report generated from the JSON numbers. |
| `app/analytics/normalization_engine.py` | Additive only: `run_sensitivity(..., tables, thresholds, robustness, eligibility_label)` (all default `None`); old behaviour unchanged. |
| `app/analytics/pressure_format_sensitivity.py`, `pressure_format_report.py` | New. Pressure tables, missing-format audit, trimmed technical rankings, population changes. |
| `scripts/run_pressure_eligibility.py`, `scripts/run_pressure_format_sensitivity.py` | New. |
| `tests/test_pressure_thresholds.py` (22), `tests/test_phase3_format_sensitivity.py` (14) | New. |
| Outputs in `data/reports/` | `pressure_threshold_experiment.json`, `pressure_eligibility_report.md`, `pressure_format_weight_sensitivity.json`, `pressure_format_weight_sensitivity.md`. |

## Commands run and results (raw)

```
PS> python scripts/run_pressure_eligibility.py          (1000 bootstrap resamples, about 5 minutes)
definitions=9 selected=chase|q0.9 viable=3 official_unchanged=True

PS> python scripts/run_pressure_format_sensitivity.py
combined populations: batter=8, bowler=6; official_unchanged=True

PS> python -m pytest -q tests/test_pressure_thresholds.py          22 passed
PS> python -m pytest -q tests/test_phase3_format_sensitivity.py    14 passed
PS> python -m pytest -q
290 passed in 201.99s (0:03:21)          (254 earlier tests unchanged + 36 new)
PS> python -m ruff check .
All checks passed!
PS> python -m ruff format --check .
95 files already formatted
```

Determinism: both scripts were run twice; the JSON outputs were identical apart from
`provenance.generated_at_utc` (compared programmatically: `True` for both files).

## Key figures (from DuckDB through the exploratory state)

- 9 pressure definitions run through the full harness (drawn from 364 Stage 3 family a/b
  candidates; the Stage 3 report lists 384 with the 20 break rows). 3 are viable (a data-weight rule
  with a sufficient pool in all four format-role cells): chase q0.75, any q0.75, chase q0.9.
  Pre-declared population-level selection rule (highest q, ties to the larger population, no
  player scores) selects `chase|q0.9`: PROVISIONAL, one of N examined, not validated.
- chase|q0.9 pressure deliveries: IPL batter 3,884, IPL bowler 4,093, T20I batter 4,592, T20I bowler 4,787.
- Recommended minimum pressure balls (eligible players): IPL batter 24 (56), IPL bowler 32 (43),
  T20I batter 24 (61), T20I bowler 36 (32). Balls at which data outweighs the EB prior: 20.9, 30.3, 22.0, 33.6.
- Phase 2.5 all-situation thresholds on the same pressure samples (120/192 IPL, 120/144 T20I):
  only 1, 0, 0, 1 players pass. They were not reused.
- Stability (bootstrap by match): expected Top 10 overlap 6.6 / 5.2 / 7.0 / 6.6; Spearman vs original
  0.81 / 0.62 / 0.80 / 0.69; batter 95% interval excludes zero for 27% (IPL) and 15% (T20I) of eligible batters.
  B0 versus per-candidate baseline Spearman 0.99 to 1.00.
- Both-format eligibility at those thresholds: batters 8, bowlers 6, both fewer than ten, so the
  combined lists are short and are not padded (looser rung: 12 and 10; stricter rung: 6 and 4).
  Phase 2.5 all-situation combined populations were 133 and 114.
- Format-weight rerun: eight configs present with config id and hash; population identical across
  configs; 100:0 and 0:100 rank the same population by one format's z-score; missing-format audit:
  0 combined scores for players not eligible in both formats, 0 z-scores for a non-eligible format.

## Known limitations (stated in the reports)

- Eligibility is held fixed inside the bootstrap. The data-weight floor is necessary, not sufficient.
- Nominal ladder rungs are placeholders. Selection is one of nine definitions examined.
- Pressure scores are actual minus expected under a FULL_SAMPLE baseline, not validated pressure scores.
- Combined Spearman and overlap on 8 and 6 players are descriptive only.
- Per-candidate baselines were built for the nine definitions of this experiment, not all 364 candidates.
