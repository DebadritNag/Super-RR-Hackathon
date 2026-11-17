# Phase 8 chunk 1 verification

Run from `d:/Data/backend` with `$env:PYTHONUTF8=1`.

| Command | Result |
|---|---|
| `python scripts/phase8_criteria.py` | criteria sha256 9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64 written, run-log seq 1 `plan` |
| `python scripts/phase8_data.py` | 158,588 rows, 675 matches (TRAIN 487, VALIDATION 188), exclusions table written |
| `python scripts/phase8_intensity.py` | P0, P3, P4, P5, P6 coverage and correlation tables written (no validity or ranking result) |
| `python -m pytest tests/test_phase8_criteria.py tests/test_phase8_guards.py tests/test_phase8_data.py tests/test_phase8_intensity.py tests/test_phase8_eval_utils.py -q` | 81 passed |
| `python -m pytest -q -p no:cacheprovider` (full) | 1270 passed, 3 warnings, 618 s (log: `.agents/tasks/_p8c1_full_pytest.txt`) |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 377 files already formatted |
| `check_protected(only=())` | 234 recorded protected files checked, all unchanged (both DuckDB files included) |

## Delivered (under `backend/app/phase8/`)
constants, store (`phase8.duckdb`, append-only `p8_run_log`, results refused before the plan row), criteria (hash, `verify_criteria`, `begin_step`, forbidden-input check), lockguard (TEST guards, protected-hash check), splits (Phase 4 split, `match_id % 5` folds, partition integrity), data (single loader, exclusions, feature whitelist, strictly-prior team priors), intensity (P0, P3, P4, P5, P6 with TRAIN-only OOF CDF; P1/P2 hook for chunk 2), calibration, reliability (parity/time split-half, Spearman-Brown, ICC, out-of-time), stability (seeded match bootstrap, Top-10 inclusion, rank intervals, tie rule), units. Scripts: `scripts/phase8_{criteria,data,intensity}.py`. Config: `config/phase8_selection_criteria_v1.json`; hash: `data/reports/phase8_selection_criteria_hash.json`.

## Notes
- The criteria file was written before any p8 result table; a test asserts all result tables carry its hash and run_seq >= 2.
- P6 uses the equal-loading first principal component of two CDF-scaled inputs (P3, P4), computed without fitted parameters. P5 is excluded from it because it has the defending side's orientation. The earlier fitted-PCA version made a delivery's value depend on later rows of its own fold; this fixes that.
- Truncation test: P0, P3, P4, P5 are exactly unchanged. P6 changes by under 0.01 because the P6 CDF is refit from the other-fold values of the composite, which depend on the truncated match's own fold rows. State columns only, no outcomes.
- Retention test fix (D6): the only change was one report sentence in `scripts/rr_report.py` that quoted a table name. No guard or allow-list was edited.
- p8 tables live in `phase8.duckdb`, not `exploratory.duckdb` (plan decision D5).
