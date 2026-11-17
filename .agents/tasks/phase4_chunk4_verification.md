# Phase 4 Chunk 4 verification
Environment: PowerShell, `$env:PYTHONUTF8=1`, Python 3.11, cwd `d:/Data/backend`. No frontend code. The repository is not a git repository, so no commit was made.

## Built
- `app/phase4/classification.py`: squad resolution (exact unique name, id-keyed team corroboration, variants never applied), nationality and status rules, validated override loader, `apply_overrides`, coverage. `config/phase4_classification_v1.json`, `config/classification_overrides_v1.csv` (header only).
- `app/phase4/serving.py`, `scripts/phase4_classification.py`: classification tables, descriptive `p4_player_stats`, reports (`phase4_classification.csv`, `phase4_classification_coverage.json`, `phase4_classification_coverage_report.md`, `phase4_unresolved_players.csv`).
- `app/phase4/selection.py`: exact DP optimiser, exact/min/max per group and role, infeasibility explanations, `allow_fewer`. `config/phase4_selection_presets_v1.json` (six presets).
- `app/phase4/uncapped.py` (filters, uncapped kinds), `views.py` (ranking, pool, directory), `profiles.py` (stats, radar data, strengths, INSUFFICIENT_DATA).
- API: `app/main.py`, `app/api/{deps,errors}.py`, `app/api/v1/routes.py`, `app/schemas/phase4.py` (Pydantic v2), `app/repositories/phase4_repo.py`, `app/services/phase4_service.py`.
- Docs: `docs/frontend_backend_contracts.md` (copied to `data/reports/`), `docs/backend_implementation_spec.md`.
- Tests: `tests/test_phase4_classification.py` (25), `test_phase4_selection.py` (15 incl. brute force), `test_phase4_api.py` (26, HTTPX TestClient), `test_phase4_classification_real.py` (5, realdata), helpers `tests/phase4_api_helpers.py`.

## Commands and results
| command | result |
|---|---|
| `python scripts/phase4_classification.py` | players 1217, verified Uncapped 0, stats rows 1001, official data unchanged True |
| `python -m pytest -q` | 488 passed (417 + 71), 3 warnings (pre-existing numpy warnings and an anyio deprecation), about 6 minutes |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 166 files already formatted |
`superr.duckdb` SHA-256 `CB4077EE...391D` equals the value in `phase4_hash_before.txt`; the script's snapshot of source CSVs and Cricsheet manifests reported no change. Writes went only to `p4_*` tables in `exploratory.duckdb` and to `data/reports` and `docs`.

## Actual classification coverage (1,217 players, as-of 2025-12-31)
| nationality | status | all players | players with an eligible experimental score (403) |
|---|---|---|---|
| Indian | Capped | 52 | 51 |
| Indian | Uncapped | 0 | 0 |
| Indian | Unknown | 112 | 35 |
| Overseas | Capped | 603 | 288 |
| Overseas | Uncapped | 0 | 0 |
| Overseas | Unknown | 3 | 1 |
| Unknown | Capped | 0 | 0 |
| Unknown | Uncapped | 0 | 0 |
| Unknown | Unknown | 447 | 28 |
- Verification: nationality DERIVED 770, UNVERIFIED 447; status DERIVED_FROM_OFFICIAL_T20I_APPEARANCES 655, UNVERIFIED 562. Verified Uncapped: 0. Conflicts: 0.
- Unknown nationality reasons: NO_SOURCE_RECORD 445, SQUAD_NAME_AMBIGUOUS 2 (Rashid Khan, Abdul Samad). Unknown status reasons: NOT_PROVEN_CAPPED_IN_DATA 498, FIRST_T20I_AFTER_AS_OF_DATE 64.
- Squad file: 257 rows, 232 resolved to exactly one player_id and all 232 corroborated by the id-keyed IPL 2026 team; 25 unresolved (23 no match, 2 ambiguous), none has a variant candidate, none applied. `designation` holds only Captain/blank: no cap information exists in any file.
- Consequence: every uncapped ranking and uncapped preset is empty or POOL_TOO_SMALL until a verified cap source is supplied. Source needed: an official/verified cap list keyed by player_id (or name plus team, e.g. a squad sheet with a capped/uncapped column), and player_id keys for the 25 unresolved squad names.

## Spot checks (different method, pandas on raw CSVs)
1. Rohit Sharma T20I appearances on or before 2025-12-31 from `playing_eleven.csv` + `matches.csv` + `competitions.csv` (match_format T20I): 23, stored 23. Jasprit Bumrah: 18, stored 18.
2. Players with a T20I appearance on or before the as-of date: 655 by pandas, stored Capped 655. Players with any T20I appearance: 719 = 655 Capped + 64 FIRST_T20I_AFTER_AS_OF_DATE.
3. Rohit Sharma IPL (innings 1-2, matches to 2025-12-31): runs 1,435 and dismissals 57 match `p4_player_stats`; balls faced 1,077 raw rows minus 46 wides = 1,031, stored 1,031.
4. Rohit Sharma nationality Indian in `ipl squad.csv`, stored Indian DERIVED (name plus team corroborated).
5. IPL batter eligible pool 132 from `p4_pressure_scores_frozen_rules` (frozen shrinkage config) equals the Chunk 3 ranking pool of 132; the API `pool_size` for `/rankings/batter` is 132 (the stored table holds two shrinkage configurations, the loader keeps only the frozen `shrink_tau4`, which an API test covers).
6. 4/3/2/1 composition: optimiser equals brute-force subset enumeration on the synthetic pool (test), plus 150 random seeded requests and role-constrained cases.

## Live API smoke (TestClient on the real store)
Ranking 0.2 s, preset 0.09 s, custom selection 0.08 s. `mixed_capped_and_uncapped_xi` returns POOL_TOO_SMALL with required 2 and 1 versus available 0 and 0. A 5 Indian capped + 5 Overseas capped request returns 10 eligible players. Official requests return 403. Admin endpoints return 503 without a token.

## Deliberate deviations and open items
- Variant-name candidates and the 2 ambiguous names are never applied (design notes rule), although Plan 0.3 allowed corroborated variants; none exist in this data.
- `standardised_score` uses the eligible pool mean and sd of the PRE_TEST score table, not TRAIN-only parameters; no TEST outcome is involved.
- API default `format` is `IPL`; `COMBINED_w70_30` stays provisional.
- Descriptive profile stats do not exclude DLS rows (stated in the `restrictions` column).
- The stored profile radar uses descriptive per-format stats; bowler pressure still uses batter state signals (Chunk 3 limitation).
- Admin protection is a minimal token (`SUPERR_ADMIN_TOKEN`); real authentication is out of scope.
