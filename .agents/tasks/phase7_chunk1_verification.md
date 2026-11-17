# Phase 7 chunk 1 verification (executed by the implementer, 17 Nov 2026)

All commands ran in `d:/Data/backend` with `PYTHONUTF8=1` (and `PYTHONPATH=d:/Data/backend` for the probes). `D:\Data` is not a git repository, so nothing was committed.

| Command | Actual result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` (output in `backend/data/reports/phase7_pytest_chunk1.txt`) | **1045 passed, 3 warnings in 468 s** (1038 earlier + 5 + 2 new) |
| `python -m pytest tests/test_phase7_no_mock_in_production.py tests/test_phase7_public_players_openapi.py` | 5 passed; 2 passed |
| `python -m pytest tests/test_phase6_public_schema.py tests/test_phase6_cache_isolation.py -q` | 32 passed |
| `python -m ruff check .` | All checks passed! |
| `python -m ruff format --check .` | 314 files already formatted (after formatting my own 4 new files) |
| `python scripts/phase7_protected_check.py --phase6` | phase7_prehash: 218 files, 0 mismatches; phase6_prerun: 146 entries, 0 unexpected mismatches, 1 expected (exploratory.duckdb); lock check PASS (phase4 lock log sha256 cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c, events FREEZE/OPEN/CLOSE; phase5 log `[]`); RESULT PASS |
| `python scripts/phase7_audit_probe.py` -> `phase7_audit_probe.json` | pooled_sb 0.3656; median oe_sb 0.2538 over 47; floor_hit 48/48; gate passed 0/48; 256 applicable option rows, 0 pass, 18 ids, best 0.5619 (O6); ladder 0.5 reached 2/4, 0.7 0/4, 0.8 0/4; season medians 0.2446 and 0.1109; gate file hashes all match |
| `python scripts/phase7_spotcheck_probe.py` -> `phase7_spotcheck_probe.json` | spot 1 r 0.29324, SB 0.45350; spot 2 k 25, tau2 0.12774; spot 3 71 + 74 = 145; spot 4 298 - 70 = 228 (from official DuckDB, not raw CSV) |
| `python scripts/phase7_endpoint_probe.py` -> `phase7_endpoint_probe.json` | public `/players` 200, no forbidden keys, descriptive_only true, no publication_status, `min_pressure_matches` absent from OpenAPI and ignored (1217 = 1217); internal 401 no token, 401 wrong token, 503 unconfigured, 200 with token and contains eligible_scopes/conflict_flag/publication_status; public `/rankings/batter` 403; cache: 7/7 key components change key, unknown scope refused, unit copy isolation true, live second call cache_hit true, mutation_leaks_into_cache false |
| Mock scan of `app/**/*.py` and `scripts/*.py` | No player-name literals (257 squad names), no banned random/mock tokens, no rank/score literals. Only seeded `default_rng`/`SeedSequence` uses |

TEST lock: never opened or imported by any new code; no attempted access to record. DuckDB files were opened read-only only (protected check confirms hashes unchanged).

Files created: `scripts/phase7_protected_check.py`, `phase7_audit_probe.py`, `phase7_spotcheck_probe.py`, `phase7_endpoint_probe.py`; `tests/test_phase7_no_mock_in_production.py`, `tests/test_phase7_public_players_openapi.py`; reports `phase6_final_audit.md`, `phase6_final_decisions.md`, `hardcoded_mock_data_audit.md`, `phase7_pytest_chunk1.txt`, `phase7_audit_probe.json`, `phase7_spotcheck_probe.json`, `phase7_endpoint_probe.json`.

Not done in this chunk (outside its task list): `phase7_unadopted_shrinkage_option.md`, `phase7_mock_census.md` (frontend entries are added in chunk 6). No product-behaviour change was made, so no warning was raised.
