# Phase 2.5 review

Verdict: APPROVED (no high or medium findings; all gates pass).

## Gates
- `python -m pytest -q`: 142 passed (145 s).
- `python -m ruff check .`: clean. `python -m ruff format --check .`: 64 files already formatted.
- `python scripts/run_phase2_5.py` re-run twice: exit 0 for all four steps, preservation `unchanged=true`, `cricsheet_loaded_into_database=false`.
- Determinism: JSON outputs hashed with `generated_at_utc` stripped were identical across runs.

## Scope and preservation
- No pressure scores, official rankings, ML or API code found (grep for sklearn/xgboost/torch/fastapi/pressure_score/win_prob in app/analytics and app/validation: no hits). Every JSON output carries `proxy_run: true`, `pressure_status: PENDING_PHASE3`, `score_label: PROXY_NOT_PRESSURE`, `not_for_publication: true`; every md report opens with the interpretation.
- Analytics and validation open DuckDB read-only. The only read-write path is the explicit `format-weights-v1` registration into `model_versions` (idempotent, tested). Official CSV hashes and table content hashes unchanged.
- Cricsheet is read from JSON only; tests cover no write SQL, no loader imports, no Cricsheet tables in the DB, and a Cricsheet-only match never reaching samples.

## Requirement coverage
- Decision 1: eight configurations in `config/format_weights_v1.json`, `w70_30` marked PROVISIONAL_NOT_VALIDATED; missing format gives NULL plus status, ADJUSTED_ESTIMATE kept separate; tests for normalization, reproducibility, degenerate configs.
- Decision 2: percentile (P10/P25/P50/P75) and practical candidates, per-format and independent batter/bowler, pool verdicts, bootstrap with seed 20260512 over matches; recommendation labelled PROVISIONAL and derived from results (not a fixed invented minimum).
- Decision 3: six official matches classified with evidence: 3 CONFIRMED_SUPER_OVER, 3 UNCONFIRMED (2 not found in Cricsheet, 1 failed regulation sanity), 0 CONFLICTING. No relabelling; proposed status is "not written".
- DQ: 26 register entries covering all 17 OPEN rows plus 5 INFO and 4 carried over; 0 BLOCKING, 16 non-blocking with restrictions, 10 informational; scoped restrictions in `config/data_quality_restrictions_v1.json` with `global_exclusion: false`; 0 records deleted, 0 matches excluded.
- Required tests all exist (missing format, weight normalization, reproducibility, eligibility, threshold sensitivity, Super Over mapping, preservation, no contamination).

## Observations (low)
1. Registering `format-weights-v1` writes a row to the official DuckDB `model_versions` table, so the DB file hash changes on first registration. It is idempotent and excluded from the official-table preservation check, but a reader of "preservation" should know the DB file is not strictly byte-identical to Phase 2.
2. Match 40725 is UNCONFIRMED because the REG2_WICKETS sanity check fails by one wicket, caused by an open official row (dismissed player without wicket flag). This is conservative and documented; it could be revisited after the upstream data issue is resolved.
3. T20I batter pool recommendation input differs (PR300 vs P75 for the others); worth confirming in Phase 3 planning that the thin T20I pool is intended to stay provisional.
