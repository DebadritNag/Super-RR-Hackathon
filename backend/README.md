# SupeRR Selector Season 2: backend (Phase 1: data audit)

Backend for the pressure-intelligence / player-ranking project. **Phase 1 only audits the data.**
There is no ingestion, no pressure metric, no ranking and no frontend yet.

Raw datasets live in `D:\Data` and are read-only. All code and outputs live in `D:\Data\backend`.
`data/raw` is an empty placeholder: originals are not copied or moved.

## Environment

- Python 3.11 (`python`; the `python3` command does not exist on this Windows machine).
- Install: `python -m pip install -r requirements.txt`
- Configuration: environment variables prefixed `SUPERR_` (see `.env.example`), e.g.
  `SUPERR_DATA_ROOT=D:/Data`.

## Commands (PowerShell, from `D:\Data\backend`)

```powershell
$env:PYTHONUTF8 = 1
python scripts\audit_datasets.py          # full audit, ~4 minutes, writes data\audit\*
python scripts\audit_datasets.py --skip-cricsheet   # CSV-only audit
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## Layout

```
app/core/            config (pydantic-settings), logging
app/data_pipeline/   dataset_discovery, schema_validator, data_quality, ball_by_ball_inspector,
                     cricsheet_auditor, squad_auditor, pdf_extractor, audit_runner
app/utils/           path and JSON helpers
scripts/             audit_datasets.py
tests/               test_dataset_audit.py
data/audit/          generated reports (see below)
data/staging/        cricsheet_index.parquet (generated, git-ignored)
```

## Audit outputs (`data/audit/`)

| file | content |
|---|---|
| `dataset_audit.json` / `.csv` / `.md` | all findings; per-column null/empty/distinct stats; readable summary |
| `schema_report.json` | actual vs spec schemas, inferred DuckDB types, Cricsheet key variations |
| `data_quality_report.json` | duplicates, invalid ids, categories, foreign-key orphans, team_id uniqueness |
| `extras_mapping.md` | data-derived meaning of `runs`, `extras_type`, `extras1_runs`, `extras_2_runs` |
| `match_reconciliation.csv` | every match in `matches.csv` with no deliveries, classified |
| `cricsheet_overlap_report.json` | per-directory counts, cross-directory overlap, IPL overlap, totals validation |
| `cricsheet_validation_*.csv` | per-innings comparison of the ball-by-ball files with Cricsheet |
| `problem_statement.txt` / `problem_statement_summary.md` | PDF text and requirements summary |
| `proposed_schema.sql` | proposed DuckDB schema (hand-written from the findings; not auto-generated) |
| `directory_tree.txt` | workspace and backend trees |

## Open decisions for the user

See `.agents/tasks/user_summary.md` (authoritative ball-by-ball file, use of the 2026 files,
Cricsheet coverage of the matches that are not in the supplied data, and others).

## Phase 2: DuckDB schema and official CSV ingestion

Loads the official competition CSVs into `data/database/superr.duckdb`. No pressure metric, ranking,
API or frontend exists yet. Cricsheet is not loaded.

```powershell
cd d:/Data/backend
$env:PYTHONUTF8 = 1
python scripts\ingest_competition_csv.py            # load; second run prints "no change"
python scripts\ingest_competition_csv.py --force    # reload even if nothing changed
python scripts\ingest_competition_csv.py --validate-only
python scripts\verify_database.py                   # independent re-check (stdlib csv), exit 1 on FAIL
python -m pytest -q                                 # all tests, including the real-data test
python -m pytest -q -m "not realdata"               # synthetic tests only
```

Exit codes of the ingest script: 0 success or no change, 1 failed (rolled back), 2 loaded with a
failed validation check.

- Schema: `data/audit/phase2_schema.sql` (persistent control tables plus a replaceable data layer).
  Plan and design: `data/audit/phase2_ingestion_plan.md`.
- Authoritative deliveries: `updated_ball_by_ball.csv` (`deliveries`, `innings`). The original
  `ball_by_ball.csv` is kept raw in `raw_ball_by_ball` with a column-by-column comparison table.
- `matches 2026.csv` and `*_stats2026.csv` are recorded in `dataset_lineage` as
  `SKIPPED_BY_DECISION` (hash and row count only). `ipl squad.csv` is `PENDING_PHASE`.
- Idempotency: the run compares file sha256 values, the DDL hash and table row counts with the last
  successful load. The load itself is one DuckDB transaction (drop, recreate, insert); any failure
  rolls back to the previous state and the failed run is recorded afterwards.
- Unresolved data-quality issues are stored as `OPEN` rows in `data_quality_results`
  (view `v_latest_data_quality`); nothing is silently removed or corrected.
- IPL/T20I weights: `SUPERR_IPL_WEIGHT=0.70`, `SUPERR_T20I_WEIGHT=0.30` (must sum to 1); stored in
  `model_versions`. Not used in any calculation yet.
- Reports: `data/audit/phase2_validation_report.{json,md}`, `ingestion_errors.csv`,
  `ball_by_ball_comparison.{json,md}`, `phase2_match_reconciliation.csv`.
- Test marker `realdata`: ingests the real CSVs into a temporary database; skipped if they are absent.


## Phase 2.5: format weights, eligibility thresholds, Super Over and data-quality checks

Purpose: the three approved Phase 2.5 decisions plus a data-quality impact assessment, run before any pressure calculation. Everything is a descriptive proxy: each output carries `proxy_run: true`, `pressure_status: PENDING_PHASE3`, `score_label: PROXY_NOT_PRESSURE` and `not_for_publication: true`. No pressure score, official ranking or model exists yet.

Commands (PowerShell, from `D:\Data\backend`, `$env:PYTHONUTF8=1`):

```
python scripts/run_phase2_5.py                       # all four steps + combined preservation check
python scripts/run_eligibility_experiment.py         # Decision 2
python scripts/run_format_weight_sensitivity.py      # Decision 1 (add --register to insert one model_versions row)
python scripts/validate_super_overs.py               # Decision 3 (Cricsheet, validation only)
python scripts/assess_data_quality_impact.py         # data-quality impact register
```

Outputs in `data/reports/`: `format_weight_sensitivity.json/.md`, `eligibility_distribution.json`, `eligibility_threshold_experiment.json`, `eligibility_threshold_report.md`, `cricsheet_super_over_validation.json/.md`, `data_quality_impact_report.json/.md`, `phase25_preservation.json`.

Configuration (`config/`): `format_weights_v1.json` (eight IPL:T20I weights, 70:30 provisional default), `eligibility_rules_v1.json`, `data_quality_restrictions_v1.json` (per-metric restrictions, loaded with `app.validation.restrictions.restrictions_for_metric`).

Guarantees:
- Official data is opened read-only. The only write is the explicit `--register` option of the format-weight script, which inserts one `model_versions` row. Each script hashes the official CSVs, the official tables and the Cricsheet directories before and after and exits with code 1 on any change.
- Cricsheet is validation-only. Its JSON is read from disk; it is never loaded into DuckDB, a ranking sample or a training artifact, and official innings 3/4 are never relabelled. The proposed statuses (`CONFIRMED_SUPER_OVER_BY_CRICSHEET`, `UNCONFIRMED_INNINGS_3_4`, `CONFLICT_INNINGS_3_4`) exist only in the validation JSON.
- No record is deleted and no match is excluded globally. Data-quality issues become restrictions on named metrics only.

Tests: `python -m pytest -q` (tests marked `realdata` use the real database and Cricsheet files and skip when they are absent).

## Phase 3 preparation: pressure framework and exploratory features (EXPLORATORY ONLY)

Everything here is an exploratory proxy calculation. No pressure score is validated, no official
Top 10 is published, no ML model is trained, and 70:30 IPL/T20I stays a provisional default. Every
JSON output carries `status: EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`. Official
DuckDB is opened read-only; the state store is `data/database/exploratory.duckdb`.

Run everything (about 6 minutes, mostly the 1000-resample eligibility bootstrap):

```powershell
$env:PYTHONUTF8=1
python scripts/run_phase3_prep.py          # all stages, preservation check, deliverable check
python scripts/apply_dq_restrictions.py    # Stage 7 only (restriction ledger, sensitivity, feature dictionary)
python -m pytest -q
```

Stage scripts: `build_pre_delivery_state.py`, `spot_check_pre_delivery_state.py`,
`run_pressure_distributions.py`, `run_baseline_exploration.py`, `run_pressure_eligibility.py`,
`run_pressure_format_sensitivity.py`, `apply_dq_restrictions.py`.

Deliverables in `data/reports/`: `pressure_framework_v1.md` (source: `docs/`),
`pressure_feature_dictionary.json`, `pressure_distribution_report.md`,
`pressure_threshold_experiment.json`, `pressure_eligibility_report.md`,
`baseline_methodology_v1.md`, `phase3_data_quality_application_report.md`. Also
`pressure_format_weight_sensitivity.*`, `phase3_data_quality_application.json` and
`phase3_preservation.json`.

Restrictions (`config/data_quality_restrictions_v1.json`, 26 rules) are applied by
`app/services/restriction_service.py` at metric and feature level only. No record is deleted and
no match is excluded globally. Approval gate: full pressure scoring, official rankings and ML
training require explicit approval.

## Phase 4: experimental pressure scoring and temporal validation (EXPERIMENTAL_NOT_VALIDATED)
Everything here is experimental. No pressure definition, eligibility threshold, shrinkage strength
or format weight is validated, 70:30 stays a provisional default, no official Top 10 is published
and no final ML model is trained. Official rankings and ML training wait for explicit approval.
Every output carries `status: EXPERIMENTAL_NOT_VALIDATED` and `official_ranking: false`.
`superr.duckdb` and the source CSVs are never modified; experimental tables are `p4_*` tables in
`data/database/exploratory.duckdb`.
Run everything (about 3 minutes, deterministic, seeds from `config/`):
```powershell
$env:PYTHONUTF8=1
python scripts/run_phase4.py                                  # all stages, preservation + deliverable check
python scripts/run_phase4.py --compare-hashes <earlier phase4_output_hashes.json>   # determinism check
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```
Stages (each is also a script and can be run alone with `--steps`): `phase4_split.py` (chronological
TRAIN/VALIDATION/TEST split, strictly prior par, phase boundaries), `phase4_baseline.py` (calibrated
baseline), `phase4_scoring.py` (first scoring pass), `phase4_sensitivity.py` (definition comparison,
shrinkage, eligibility, format weights, ranking stability; writes `phase4_frozen_choices.json`),
`phase4_test_eval.py` (the single TEST evaluation), `phase4_classification.py` (uncapped
intelligence), `phase4_reports.py` (spot checks, scoring report, data-quality report, user summary).
Deliverables in `data/reports/`: `phase4_temporal_validation_plan.md`,
`phase4_baseline_calibration_report.md`, `phase4_pressure_scoring_report.md`,
`phase4_definition_comparison.md`, `phase4_eligibility_validation.md`,
`phase4_shrinkage_sensitivity.md`, `phase4_format_weight_sensitivity.md`,
`phase4_ranking_stability.md`, `phase4_data_quality_report.md`, `phase4_user_summary.md` (also
copied to `.agents/tasks/`), with JSON/CSV outputs beside them, `phase4_test_evaluation.*`,
`phase4_spot_checks.json`, `phase4_preservation.json` and `phase4_output_hashes.json`.
Test lock: TEST outcomes are read only inside `evaluate_on_test`. Choices (definition, shrinkage
strength, eligibility rules) are frozen from TRAIN and VALIDATION first, their SHA-256 is logged as
`FREEZE` in `phase4_lock_log.json`, and the lock opens once (`OPEN`, then `CLOSE`). A refused read
is logged as `READ_DENIED`. This is a convention-level guard, not a security boundary. A full run
resets the run-scoped log.
Reports are generated from stored results (`app/phase4/reports.py`); no number is typed into a
template. Independent spot checks (raw CSV, direct SQL, hashes) are in `phase4_spot_checks.json`.
API (no frontend): `uvicorn app.main:app`, endpoints under `/api/v1`, experimental outputs only,
official requests answer 403, admin endpoints need `SUPERR_ADMIN_TOKEN` (503 when unset). See
`docs/frontend_backend_contracts.md` and `docs/backend_implementation_spec.md`.
Classification limits: nationality and international status are separate fields with per-field
verification. Capped is derived only from a played T20I in the data; never appearing is Unknown, not
Uncapped. Verified Uncapped stays 0 until a verified source is added through
`config/classification_overrides_v1.csv` (header only by default). Uncapped rankings and presets
report an empty or too-small pool until then.

## Phase 5: investigation, dynamic filter-driven ranking, methodology lock, experimental refit (EXPERIMENTAL_NOT_VALIDATED)
Nothing in Phase 5 is validated, published or official. Every output is labelled
`EXPERIMENTAL_NOT_VALIDATED` and `INTERNAL_EXPERIMENTAL_ONLY`. No Top 10 is published. TEST is not
opened (`phase5_lock_log.json` stays empty; `phase4_lock_log.json` keeps its three Phase 4 events).
Official data (`superr.duckdb`, source CSVs) and every `phase4_*` file and `p4_*` table stay
byte-identical; each script checks this before and after and exits 1 on any change.
Commands (PowerShell, from `D:\Data\backend`, `$env:PYTHONUTF8=1`):
```
python scripts/run_phase5.py                    # all Phase 5 scripts in order; no lock is created
python scripts/run_phase5.py --create-lock      # same, and EXPLICITLY writes the EXPERIMENTAL_LOCK manifest
python scripts/run_phase5.py --compare-hashes   # second run: every phase5_* output must hash the same
python scripts/phase5_methodology_lock.py               # pre-lock checklist only
python scripts/phase5_methodology_lock.py --confirm-lock # the only way a lock manifest is written
python scripts/phase5_refit.py                  # refuses without a valid lock
python -m pytest -q; python -m ruff check .; python -m ruff format --check .
```
Scripts, in orchestrator order: `phase5_classification.py` (four-status classification, strict
uncapped disabled), `phase5_date_verification.py` (42 late T20I dates and the restricted TEST-set
manifest; original dates are never changed), `phase5_gates.py` (publication gates),
`phase5_investigation.py`, `phase5_sensitivity.py`, `phase5_ranking_stability.py`,
`phase5_context_engine.py`, `phase5_context_coverage.py`, `phase5_dynamic_demo.py`,
`phase5_context_spotcheck.py`, `phase5_reports.py`, `phase5_methodology_lock.py`, `phase5_refit.py`.
Methodology lock: `config/phase5_methodology_lock_v1.json` lists what is hashed (config files,
frozen Phase 4 choices, test-set manifest, the modules that fit the refit) and the choices
(definition `any|q0.75` marked PROVISIONAL, alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75`,
working-pool thresholds, `shrink_tau4`, streams, restrictions). The manifest
(`data/reports/phase5_methodology_lock.json`, label `EXPERIMENTAL_LOCK`, `validated: false`) is
written only by `phase5_methodology_lock.py --confirm-lock`, which first records a checklist from the
chunk 1-4 outputs: required items must pass; failing publication gates and pending user decisions
are listed, never hidden. `verify_lock` raises `LockDriftError` when any locked byte differs, and
the refit then refuses to run. After editing a locked file, re-run the lock script on purpose.
Refit: `p5_refit_trainval_v1` fits baseline, pressure cut-offs and shrinkage on TRAIN + VALIDATION
(TEST rows are cut at load time and refused by a second check). The quantile level, working-pool
ball thresholds and shrinkage config are locked. Tables: `p5_refit_trainval_v1_scores`,
`_baseline_calibration`, `_thresholds`, `_comparison`, `_manifest`, plus `p5_methodology_lock` and
`p5_output_hashes`. The refit has no out-of-sample check, because VALIDATION was used for fitting.
Dynamic ranking: one scoring model, filters only choose who is compared (see
`data/reports/phase5_dynamic_ranking_architecture.md`). Internal routes need `X-Admin-Token`:
`/api/v1/internal/rankings/dynamic`, `.../dynamic/context-preview`, `.../dynamic/coverage`. Public
twins under `/api/v1/dynamic-rankings` answer 403 `PUBLICATION_GATE_NOT_SATISFIED` with the failing gates.
Strict uncapped selection answers `STRICT_UNCAPPED_DISABLED`. To enable it, add an authoritative
source keyed by `player_id` through `config/classification_overrides_v1.csv` and
`config/classification_source_manifest_v1.json` (see `phase5_classification_migration.md`). To
verify the 42 dates, fill `config/t20i_official_date_verification_template.csv` with official
match-level dates and re-run `phase5_date_verification.py`.
Still blocked: official rankings, official ML training, public output. Gates failing:
`data_weight_gate_passed`, `methodology_validated`, `date_verification`; request-level
`strict_classification_available` and `min_eligible_pool`. Read `data/reports/phase5_user_summary.md`
and `phase5_unresolved_issues.md` first.

## Phase 6: cleanup and pressure-definition / reliability validation investigation (EXPERIMENTAL_NOT_VALIDATED)
Phase 6 is internal. No official Top 10, no public experimental ranking, no official ML training, and
no score is called validated. TEST was opened once in Phase 4 and is not a pristine hold-out; Phase 6
does not open it (`phase4_lock_log.json` unchanged, `phase5_lock_log.json` empty). Official data,
every `phase4_*`/`phase5_*` file and every `p4_*`/`p5_*` table stay byte-identical. New outputs are
`phase6_*` files in `data/reports/` and `p6_*` tables in `data/database/exploratory.duckdb`.
Classification wording: three real values (`VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`) and a
disabled placeholder `VERIFIED_UNCAPPED`. This supersedes the "four-status" wording in the Phase 5
section above. Strict uncapped selection stays disabled.
Commands (PowerShell, from `D:\Data\backend`, `$env:PYTHONUTF8=1`; the full run takes about 15 minutes):
```
python scripts/run_phase6.py                    # all Phase 6 scripts in order; creates no lock
python scripts/run_phase6.py --compare-hashes   # second run: every phase6_* output must hash the same
python scripts/phase6_recent_form.py            # 2024-onward and 2025-onward, separate analyses
python scripts/phase6_season_robustness.py      # season-by-season robustness (not validation)
python -m pytest -q; python -m ruff check .; python -m ruff format --check .
```
Scripts, in orchestrator order: `phase6_cleanup_checks.py`, `phase6_investigation_plan.py` (criteria
written and hashed before any result; later steps refuse to run if the criteria file changed),
`phase6_variance_floor.py`, `phase6_split_half.py`, `phase6_definition_compare.py`,
`phase6_context_reliability.py`, `phase6_eligibility_reliability.py`,
`phase6_data_weight_options.py`, `phase6_recent_form.py`, `phase6_season_robustness.py`,
`phase6_retention_stub.py`, `phase6_reports.py`. Everything is seeded (20260512).
The primary window is the full verified pre-test history (TRAIN + VALIDATION, 723 matches). The
2024-onward and 2025-onward analyses are separate (own tables `p6_recent_form_*`, own eligibility and
reliability, label `RECENT_FORM_SEPARATE_ANALYSIS`). Season checks carry `ROBUSTNESS_NOT_VALIDATION`.
The 0.5 data-weight gate is unchanged and never lowered or bypassed; failed contexts stay restricted.
The 42 late-dated T20I matches stay excluded; cross-source consistency is not official verification.
Retention list: `phase6_retention_import_design.md` is a design note and `p6_retention_status_stub` is
an empty table in the analytical store. No data is imported and no module reads the table.
Stop condition: Phase 6 ends with review. Read `data/reports/phase6_user_summary.md` and
`phase6_unresolved_issues.md` first. Nothing changes in the official methodology until you decide.
