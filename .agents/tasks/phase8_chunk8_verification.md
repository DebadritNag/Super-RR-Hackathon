# Phase 8 chunk 8 verification (reports, bundle, full verification)

## Commands and results (cwd d:/Data/backend, PYTHONUTF8=1)
- `python -m pytest -q` first full run: 1438 passed, 4 failed (`test_phase4_api::test_admin_protection`, `test_phase5_api::test_every_internal_dynamic_route_needs_the_token`, `test_phase5_gating::test_internal_routes_are_disabled_without_a_configured_token`, `test_phase7_retention_api::test_admin_endpoints_are_disabled_when_no_token_is_configured`). That run overlapped with a second pytest process I started in the same workspace. The four tests passed when run alone (4 passed). Output kept in `.agents/tasks/_p8c8_pytest_run1_4failed.txt`.
- `python -m pytest -q` clean rerun with nothing else running: **1442 passed, 0 failed**, 4 warnings, 665 s. This is the figure recorded in `submission_test_report.md`.
- `python -m ruff check .`: All checks passed. `python -m ruff format --check .`: 429 files already formatted.
- `npm run build` exit 0 (chunk size warning only). `npm run lint` exit 0 (warnings, no errors).
- Protected hashes: 234 checked, ok. One documented intentional change: `phase7_model_registry.json` (chunk 6 renamed its output keys to the preserved `*_phase7_aborted.csv` names). Source CSVs and both original duckdb files unchanged.
- `python scripts/run_phase8.py all --pytest-output ...` then `docs` twice: methodology file SHA-256 identical across runs (52BF5E71...), so the document generation is deterministic.

## Written
reports/: submission_methodology.md, submission_executive_summary.md, submission_test_report.md, submission_readiness_audit.md, phase8_build_manifest.json, final_submission_summary.md (copy of .agents/tasks/phase8_user_summary.md); scripts/run_phase8.py (orchestrator: `checks`, `docs`, `all`). ai_pipeline_verification.md section 8 updated (frontend mock data removed in chunk 7).
d:/Data/submission/: 17 files plus MANIFEST_SHA256.json; no retention, RR or auction files.

## Notes
- Orchestrator does not rerun the ranking (no random draws); the ranking scripts keep their own seeds (20260512).
- Both lists remain EXPLORATORY (batters split-half 0.057, bowlers 0.267).
