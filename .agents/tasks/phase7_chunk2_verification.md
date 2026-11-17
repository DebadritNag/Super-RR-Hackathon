# Phase 7 chunk 2 verification (executed by the implementer)

All commands ran in `d:/Data/backend` with `PYTHONUTF8=1`. `D:\Data` is not a git repository, so nothing was committed.

## Design decisions (deviations from the task text, with reasons)

| Task text | What was done | Reason |
|---|---|---|
| New tables only in `exploratory.duckdb` with prefix `p7_` | No database writes. Outputs are CSV/JSON files in `data/reports/`. | The Phase 7 plan lists `exploratory.duckdb` among the protected files (hash-checked by `phase7_protected_check.py`). Writing a table would change its hash. |
| `/compare` at `/api/v1/compare` | All new routes are under `/api/v1/descriptive/...` (`profiles/batters`, `profiles/bowlers`, `profiles/{player_id}`, `compare`, `radar`, `overview`, `methodology/summary`). | `/api/v1/compare` already exists as the publication-gated pressure compare, with existing tests expecting its 403. Replacing it would change user-visible behaviour. One prefix keeps the descriptive routes apart from the gated ones. |
| Column "pressure-context sample counts" | Columns `context_sample_balls`, `context_sample_matches`, `context_sample_label` (`DESCRIPTIVE_EXPERIMENTAL_COUNT_ONLY`), `context_definition` (`any|q0.75 PROVISIONAL`). | Phase 6 field-name walker forbids the word `pressure` in public field names. The label and the definition carry the meaning. |
| `sort_by` | Only `player_name`, `player_id`, `matches_played`, `volume`. | A sort by strike rate or runs would be a performance leaderboard. |

## Commands and actual results

| Command | Actual result |
|---|---|
| `python scripts/phase7_build_descriptive.py` (run three times) | 920 batter rows, 672 bowler rows, 19,056 per-match rows from 160,906 in-scope delivery rows. IPL 293 matches, T20I 400 matches. Output sha256 identical on rerun (batter `ac2e7867...`, bowler `da6b81f9...`, per-match `f4ac1860...`). |
| `python -m pytest tests/test_phase7_descriptive_builder.py` | 24 passed |
| `python -m pytest tests/test_phase7_descriptive_api.py` | 39 passed |
| `python -m pytest tests/test_phase7_descriptive_real.py` (marker `realdata`) | 12 passed |
| First full run `python -m pytest -q -p no:cacheprovider` | 1119 passed, 1 failed: `tests/test_phase5_gating.py::test_every_rows_returning_route_carries_the_publication_fields` expected gate fields on the new descriptive routes. Fix: added the seven new descriptive paths to its existing `PUBLIC_DESCRIPTIVE_PATHS` set (the same exemption used for public `/players`). No app behaviour changed. |
| Final full run `python -m pytest -q -p no:cacheprovider` (log: `.agents/tasks/_p7c2_full_pytest.txt`) | **1120 passed, 3 warnings in 473 s** (1045 before this chunk + 75 new) |
| `python -m ruff check .` | All checks passed! |
| `python -m ruff format --check .` | 328 files already formatted |
| `python scripts/phase7_protected_check.py --phase6` | phase7_prehash 218 files, 0 mismatches; phase6_prerun 146 entries, 0 unexpected mismatches (1 expected: exploratory.duckdb); lock check PASS (phase4 lock log sha256 `cae1e06c...`, events FREEZE/OPEN/CLOSE; phase5 lock log `[]`); RESULT PASS |

## What the real-data tests check (all executed, in the 12 passed)

* Batter balls, runs, dismissals, fours and sixes equal `p4_player_stats` for all 920 batter rows. Bowler runs, wickets and dot balls equal it for all 672 bowler rows. Bowler legal balls differ from `p4_player_stats.bowl_balls` by exactly the in-scope Penalty row count (asserted `<= 1`), because the restriction register removes the Penalty row from legal balls.
* No `match_id` in the per-match CSV belongs to a TEST-period match; latest match date <= 2025-12-31.
* Independent recomputation with pandas from the organiser's raw `updated_ball_by_ball.csv` (match dates and competition type from the official `matches` table) for players 8 (IPL), 4722 (IPL and T20I) and 1187 (T20I): balls faced, runs, dismissals, strike rate, dot balls, fours, sixes, average; for bowlers legal balls, runs conceded, bowler-credited wickets (run outs, retire out and obstructing excluded), economy and wides. All equal.
* Missing values: average empty when dismissals = 0, split rates and runs empty when the split has no balls, interval reason present when no interval.
* Manifest input hashes equal the current sha256 of `superr.duckdb` and `exploratory.duckdb`; output hashes equal the files.
* API items equal the CSV rows for five sampled batters and five sampled bowlers (values, intervals, splits, context counts, provenance).
* Overview counts equal direct queries of the official database (883 matches, 200,999 deliveries); methodology values equal `p6_split_half_pooled`, `p5_context_fit` (48/48 at the floor) and `p6_data_weight_gate_status` (0 passing).

## Data observations

* Columns of `descriptive_batter_profiles.csv`: 75. Of `descriptive_bowler_profiles.csv`: 80.
* Bowler wickets exclude run outs: player 4722 has 65 credited wickets against 67 wicket flags in IPL.
* Many nationality and international-status values are `UNKNOWN`/`UNVERIFIED` (134 of 920 batter rows have status UNKNOWN). They are shown as such with their verification labels; nothing was inferred.
* 38 delivery rows have no innings phase; they are in totals but in no phase split.

## Files created or changed

Created: `config/phase7_descriptive_v1.json`; `app/phase7/{__init__,descriptive,context,views}.py`; `app/schemas/phase7.py`; `app/services/descriptive_service.py`; `app/api/v1/routes_descriptive.py`; `scripts/phase7_build_descriptive.py`; tests `phase7_desc_helpers.py`, `test_phase7_descriptive_{builder,api,real}.py`; reports `descriptive_batter_profiles.csv`, `descriptive_bowler_profiles.csv`, `phase7_descriptive_player_match.csv`, `phase7_descriptive_manifest.json`, `phase7_descriptive_context.json`, `player_profile_explanations.md`.
Changed: `app/main.py` (descriptive router, service, CORS for `http://localhost:5173` and `http://127.0.0.1:5173`, GET and Content-Type only); `tests/test_phase5_gating.py` (exempt set, see above).
Not changed: `/players` and `/internal/players` code, cache code, any protected file, any gate, shrinkage or locked config.

## Not done or not claimed

* The Phase 6 schema test (`tests/test_phase6_public_schema.py`) was not edited. The new models are covered by the same walker in `test_phase7_descriptive_api.py`.
* The TEST lock was never opened or imported; there was no attempted access to record.
* `phase7_endpoint_probe.py` from chunk 1 was not rerun.
* Frontend integration is chunk 6.
