# Phase 6 technical design: cleanup and pressure-definition / reliability validation investigation

Status: `EXPERIMENTAL_NOT_VALIDATED`. Everything in Phase 6 is internal. No official Top 10, no public experimental ranking, no official ML training, no score is labelled validated. Source documents: `.agents/tasks/phase6_brief.md` (authoritative), `.agents/tasks/phase6_plan.md`. Open decisions and corrections to the plan are in `.agents/tasks/phase6_design_notes.md`.

## 1. Overview

Phase 6 has two parts.

**Part A, cleanup (four approved items).** (a) Classification wording: three real values plus a disabled placeholder. (b) Remove the vacuous `or True` assertions and add a lint test. (c) Split the public descriptive `/players` schema from gated outputs. (d) Make the ranking cache isolation-safe.

**Part B, investigation.** Find out why the between-player variance of pressure residuals sits at the shrinkage floor in all 48 contexts, how reliable the pressure streams are, which of the nine candidate pressure definitions are more reliable on criteria written down before any result exists, and which legitimate options could raise the data weight. The investigation is descriptive. It never edits a gate, a threshold, a frozen choice, a Phase 4 or Phase 5 file or table, and it never reads TEST outcomes.

Technology stack (locked on approval): Python 3.11 (`python`, not `python3`), numpy/pandas, DuckDB (`exploratory.duckdb`, `p6_*` tables only), FastAPI + Pydantic v2 for the cleanup, pytest, ruff. SciPy is already in the requirements, so `scipy.special.gammaln` is permitted for the beta-binomial and gamma-Poisson likelihoods (E4, E5); REML and ML use numpy Fisher scoring / bounded Newton. No new dependency is added. All new modules live in `app/phase6/` and reuse `app.phase5.pipeline.Study`, `app.phase5.reliability` and `app.phase4.shrink`; nothing is copied.

## 2. Facts verified against the code (the design depends on these)

| # | Claim | Evidence in code |
|---|---|---|
| F1 | The 0.5 gate is `GATE_B = 0.5` in `app/phase4/eligibility.py:36`. Per context, `data_weight_gate_passed = marginal_b >= el.GATE_B` (`app/phase5/context_eligibility.py:132`), where `marginal_b = n_eff_min / (n_eff_min + k)` over the eligible players. | `eligibility.py`, `context_eligibility.py` |
| F2 | The separate publication gate `data_weight_gate_passed` (`app/phase5/gating.py::_data_weight`) does not read 0.5. It reads the four format-role cell statuses from `phase4_frozen_choices.json` and fails if any is `THRESHOLD_NOT_VALIDATED`. | `gating.py:119-127` |
| F3 | `k_for` computes `floor_abs = floor * sigma2`; `tau2 = max(max(between, floor_abs) * mult, floor_abs)`; `k = sigma2 / tau2`. The multiplier is applied after the floor, and a second floor stops a multiplier below 1 from going under the floor. | `app/phase4/shrink.py::k_for` |
| F4 | Floor-hit `k` therefore is: `shrink_eb` 100, `shrink_tau0.5` **100** (not 200), `shrink_tau2` 50, `shrink_tau4` **25**, `shrink_floor0.001` 1000. The non-finite branch returns `k = 1/floor` (100, or 1000 for `shrink_floor0.001`) with `floor_hit = True`. `k_from_children` also returns `1/tau2_floor` when `c < 2` or `sigma2 <= 0`. | `shrink.py`, `analytics/shrinkage.py::k_from_children` |
| F5 | `p5_context_fit` / `phase5_context_fit.json` has 48 records, 48 floor hits, all `k == 25.0`, `shrink_config = shrink_tau4` (config `phase5_investigation_v1.json`). The between moment is negative in every row (e.g. IPL batter ALL/ALL: sigma2 3.12, between -1.08, tau2 0.125). | verified by loading the JSON |
| F6 | `n_eff_kish(per_match_n) = (sum n)^2 / sum n^2` is the number of equally sized matches. The Phase 4 moment estimator uses noise `sigma2 / n_eff_kish`, a per-ball variance divided by a per-match count. For a player with m matches of b pressure balls each, the true sampling variance of a ball-weighted mean under independent balls is about `sigma2 / (m*b)`, so the Phase 4 noise term is larger by a factor near b. | `phase4/shrink.py` docstring and `reliability.py` module docstring |
| F7 | Phase 5 already shows the noise basis decides the sign: on `phase4_kish` tau2 is negative in 4/4 cells; on `match_cluster` tau2 is about 0.10 with ICC 0.59 for IPL batters; the model-free odd/even split-half Spearman-Brown value for the same cell is about 0.27 (`phase5_split_half_reliability.csv`, TRAIN window). The two reliability numbers disagree and Phase 6 must say which one the data support. | `phase5_investigation_report.md`, `phase5_split_half_reliability.csv` |
| F8 | Reusable Phase 5 API: `CellData`, `from_cell`, `window_cols` (only `TRAIN` and `PRE_TEST`), `boot_moments`, `decompose_moments`, `reml_tau2`, `split_cov_rows`, `half_masks`, `half_stats`, `split_half`, `sb`, `reliability_by_opportunity`, `required_sample`, `simulate_detectability`, `pool_cells`, `multi_format_pooling`. Status constants `ESTIMATED`, `BETWEEN_VARIANCE_NOT_POSITIVE`, `NOT_ESTIMABLE`. | `app/phase5/reliability.py` |
| F9 | Windows: the exploratory store `p4_match_period` has TRAIN 512 matches (2022-01-22 to 2024-12-30), VALIDATION 211 (2025-01-02 to 2025-12-19), TEST 144 (2026-01-07 onward). `PRE_TEST` = 723. Matches with `match_date >= 2024-01-01` outside TEST: 192 TRAIN + 211 VALIDATION = 403. With `>= 2025-01-01`: 211, all VALIDATION, **no TRAIN rows**. | queried `p4_match_period` |
| F10 | `Study` loads only TRAIN+VALIDATION rows (`drop_test_rows`), fits the baseline B0 and pressure thresholds on TRAIN, and builds cells per definition via `all_cells(defn)`. | `app/phase5/pipeline.py` |
| F11 | TEST manifest: `PRIMARY_RESTRICTED` 99 matches, `STRICT_OFFICIAL_ONLY` 0, `SENSITIVITY_ALL` 144. Phase 5 lock log has 0 events. The Phase 4 lock log records the single opening. | `phase5_test_set_manifest.json`, `phase5_lock_log.json` |
| F12 | Vacuous assertions found by grep: `tests/test_phase5_dynamic_ranking.py:583` and `:594`, and `tests/test_pressure_state.py:45` (a third one the brief did not name). | grep `or True` in `tests/` |
| F13 | `RankingCache` key = SHA-256 of `spec_hash\|data_version\|model_version\|gate_version`. It stores and returns the same object (no copy). Gates are recomputed on read, so a cached entry holds the pre-gate full ranking. | `app/phase5/cache.py`, `phase5_service.py::_full` |
| F14 | `/players` and `/players/{id}` use `PlayerRow` (includes `eligible_scopes`, `conflict_flag`) and `Flags` (inherits `PublicationFlags`: publication status, gate results). Profile, rankings, compare and selection are registered on both the public router (403 without rows) and `/internal` (admin token via `require_internal`). | `routes.py`, `schemas/phase4.py`, `phase4_service.py::_player_item` |
| F15 | `ClassificationStatus` in `app/schemas/phase5.py:18` has four literals including `VERIFIED_UNCAPPED`; `STATUS_VALUES` in `classification_v2.py` has four; `phase5_context_rules_v1.json` lists `VERIFIED_UNCAPPED` among filter statuses. | grep |

Two statements in the plan are wrong and this design overrides them (details in the notes file): the 0.5 gate lives in `app/phase4/eligibility.py`, not in a Phase 5 gate module, and the floor-hit `k` for `shrink_tau0.5` is 100, not 200.

## 3. Part A: cleanup design

### 3.1 Classification wording

Real values: `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`. `VERIFIED_UNCAPPED` stays only as a disabled placeholder constant so that the strict-uncapped filter, the override file mechanism and the `STRICT_UNCAPPED_DISABLED` response keep working unchanged.

- `app/schemas/phase5.py`: `ClassificationStatus = Literal["VERIFIED_CAPPED","DERIVED_CAPPED","UNKNOWN"]`. `CapabilitiesResponse.classification_values: list[ClassificationStatus]` and a new `disabled_placeholder_values: list[str] = ["VERIFIED_UNCAPPED"]`.
- Keep the filter `status` query parameter accepting `VERIFIED_UNCAPPED` (so the disabled response is returned, not a 422), but its description says "disabled placeholder; always returns STRICT_UNCAPPED_DISABLED".
- `classification_v2.py`: `STATUS_VALUES` for the real values becomes a three-tuple; add `DISABLED_PLACEHOLDER_VALUES = (VERIFIED_UNCAPPED,)`. Internal code that checks `VERIFIED_UNCAPPED` (override path, strict filter) uses the placeholder constant. Docstrings and `reports.py` text ("four separate statuses") are corrected. Stored Phase 5 report files are not rewritten; Phase 6 emits corrected wording in new files.
- **Enumerated code changes (review finding 3).** `STATUS_VALUES` (three real values) is used only for the public enum, the reported counts and the `classification_values` capability list. A new `ACCEPTED_STORED_VALUES = STATUS_VALUES + (VERIFIED_UNCAPPED,)` is used wherever a stored or overridden value is validated. Files and lines:
  - `app/phase4/classification_v2.py`: line 124 (validation) checks `ACCEPTED_STORED_VALUES`; lines 301 and 307 build `by_status` over `ACCEPTED_STORED_VALUES` so the key always exists; line 323 becomes `by_status.get(VERIFIED_UNCAPPED, 0)`; `OVERRIDE_STATUS_VALUES` (line 54) and the override branch at line 220 are unchanged, so an override of `VERIFIED_UNCAPPED` is still accepted. Reported "status counts" show the three real values and list the placeholder count separately.
  - `app/services/phase4_service.py:570`: `classification_values` is emitted from `STATUS_VALUES` (three), and `disabled_placeholder_values` from `DISABLED_PLACEHOLDER_VALUES`.
  - `app/api/routes_phase5.py:43`, `app/api/filters.py:20,45,130`, `app/phase4/uncapped.py`, `app/phase4/selection.py:45`: string comparisons with `VERIFIED_UNCAPPED` are replaced by the placeholder constant; behaviour is unchanged (filter accepted, response `STRICT_UNCAPPED_DISABLED`).
  - Tests added: an override file entry with `VERIFIED_UNCAPPED` is still accepted by the classification builder; the strict filter still returns `STRICT_UNCAPPED_DISABLED` on the public and internal routes; `by_status` has no `KeyError` with a three-value tuple; a wording test (section 10) scans schemas, docs and report text for "four" classification statuses.
- Risk: the stored classification table `p5_player_classification` may contain a `VERIFIED_UNCAPPED` value if an override was applied. The Phase 5 report says the strict source is unavailable, so none exist. A Phase 6 check counts them; a non-zero count is a finding, not something to change.

### 3.2 Vacuous assertions

Run each assertion first. Final replacements (no conditional choice left to the implementer). Line 583 becomes two unconditional lines: `assert math.isfinite(r["interval_low"]) and math.isfinite(r["interval_high"])` and `assert r["interval_low"] <= r["interval_high"]`. Containment of the score in its band is not asserted, because a percentile band of a shrunk score need not bracket the point estimate; instead the test body computes `inside = r["interval_low"] <= r["score"] <= r["interval_high"]` for every row, and the implementer records the observed inside-rate over the test world in the cleanup report as a finding (a rate below 1 is reported, not hidden, and does not fail the test). Line 594 becomes `assert len(table) == len(specs) == len(set(table["spec_hash"]))`; specs with equal hashes cannot occur because `enumerate_specs` yields distinct specs by construction, and the assertion would expose a regression that broke this. Replace `test_pressure_state.py:45` by deleting the always-true line (the next line asserts the real list). The lint test `tests/test_phase6_no_vacuous_assertions.py` parses every `tests/**/*.py` with `ast` and flags: an `Assert` whose test is a `BoolOp(Or)` with any operand a truthy `Constant`; `assert True`; `assert <const>`; and a text scan for `or True`. It excludes itself and fails with `file:line`. A second test feeds the scanner the three old lines as a string to prove it detects them.

### 3.3 Public descriptive schema

New models in `app/schemas/phase4.py`: `PublicPlayerRow(ClassifiedPlayer)` with `group`, `group_label`, `squad_role`, `matches`, `distinct_matches`; `PublicDescriptiveFlags` with `status`, `disclaimer`, `descriptive_only: Literal[True]` (no `official_ranking` field, so the name scan below needs no exception); `PublicPlayerListResponse(PublicDescriptiveFlags)` with `basis`, `classification_version`, `page: Page[PublicPlayerRow]`; `PublicPlayerDetailResponse` with the provenance fields already in `PlayerDetailResponse`.

The existing `/players` route declares `response_model=PlayerListResponse | Disabled`. The public route keeps a `Disabled` branch (existing behaviour when the player directory is switched off) and its response model becomes `PublicPlayerListResponse | Disabled`; `Disabled` carries only `status` and `message`, and the schema walk covers every member of the union. `/players/{id}` is handled the same way. The internal routes use `PlayerListResponse` and `PlayerDetailResponse` unchanged.

Removed from the public models: `eligible_scopes`, `conflict_flag`, `publication_status`, `gate_results`, `failing_gates`. `eligible_scopes` encodes which formats a player is eligible for and so implies ranking eligibility. `conflict_flag` is retained on the internal `PlayerRow` only. `international_status` and its verification string stay (permitted).

`Phase4Service.players()`/`player_detail()` get a `public: bool` parameter. The public path builds items with `_public_player_item` (explicit allow-list of keys, not a deny-list). The internal router gains `/internal/players` and `/internal/players/{id}` using the existing `PlayerRow`. The public `Filters` dependency includes `min_pressure_matches`; it filters on an experimental count but exposes no value. Decision: keep it for backward compatibility on the internal routes, and remove it from the public `/players` signature (a public caller filtering by pressure matches learns an eligibility-like fact). This changes the public API surface; it is recorded in the cleanup report and in OD-6.

Tests (`tests/test_phase6_public_schema.py`): recursively walk `model_fields` (including `Page[...]`, unions and nested models) of the public models and assert no field name matches `score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict`; call `/players` and `/players/{id}` without a token and assert 200 and the same recursive key scan on the JSON; assert every route under `/internal` returns 401 with no or wrong token and 503 when no token is configured; assert the public rankings/profile/compare/selection routes return 403 `PUBLICATION_GATE_NOT_SATISFIED` with no `rows`/`items`.

### 3.4 Cache isolation

`app/phase5/cache.py`:

```
cache_key(spec_hash, data_version, model_version, gate_version,
          scope, lock_version, gate_state_hash) -> sha256(json.dumps([...], separators=(",",":")))
```

**Signature and callers (review finding 11).** `scope` has no default and is the first new parameter; `lock_version` and `gate_state_hash` also have no default, because a default would let a caller build a key that ignores gate or lock state. `invalidate_if_version_changed(data_version, model_version, lock_version)` and `get_or_compute(key, factory)` are updated. Callers to update: `app/phase5/phase5_service.py::_full` (the only production caller), and the existing cache tests (`tests/test_phase5_cache*.py` and any test that calls `cache_key`, found by grep before editing). `gate_state_hash` is built in `Phase5Service._full` from the failing-gate ids returned by `app.phase5.gating.evaluate_gates(...)`, the same call that already produces the gate results for the request (computed per request; it is cheap and is not cached). The module docstring is rewritten: it says that the cache holds the pre-gate ranking, that gate state is part of the key, and that values are copied on put and get.

JSON list encoding removes delimiter ambiguity (the current `"|".join` could collide on values containing `|`). `scope` is `"internal"` or `"public"` and any other value raises `ValueError`. `gate_state_hash` is SHA-256 of the sorted ids of currently failing gates. `lock_version` is the SHA-256 of `config/phase5_methodology_lock_v1.json` (via `file_sha256`). `invalidate_if_version_changed` tracks `(data_version, model_version, lock_version)`.

`put` stores `copy.deepcopy(value)`; `get` and `get_or_compute` return `copy.deepcopy` of the stored object on hits and of the freshly computed object on misses (the caller must not hold a reference to the stored object). Deep copy cost is acceptable: entries are bounded by `max_entries` 256 and a full ranking is a few hundred rows; a measurement is added to the cleanup report, and if a single copy exceeds 50 ms on the largest real context the fallback is storing a pickled bytes blob and unpickling on read (same isolation, lower cost). `Phase5Service._full` passes `scope`, `lock_version` and `gate_state_hash`; `ranking()` deep-copies the page rows before building the payload so `page["rows"]` is never an alias of cache memory.

Tests: mutate a returned response (item dict, nested `versions`, list) and the next identical request equals a baseline; key differs for each of scope, spec, data, model, gate, lock, gate state; delimiter-collision case; version change drops entries; concurrent `get_or_compute` from 8 threads returns equal, non-identical objects; an API-level test with the FastAPI test client mutates the parsed JSON (which is already a copy) and, more importantly, calls the service directly twice and mutates the first result.

## 4. Part B: investigation design

### 4.1 Declared before any run

1. `config/phase6_investigation_v1.json` (seed 20260512, `n_boot` 1000, windows, estimator list, split modes and repeats, reliability targets, `gate_value_expected: 0.5`, `test_outcomes_used: false`) is written and committed first.
2. `config/phase6_selection_criteria_v1.json` and its hash file `data/reports/phase6_selection_criteria_hash.json` are written by `scripts/phase6_investigation_plan.py` before any estimator output exists. The plan report `phase6_investigation_plan.md` embeds the hash.

**Criteria file contents (fixed text, numbers declared now):**

- `unit`: definition x (format, role) cell. The selection rule uses the primary stream per role only (`en.PRIMARY`: batter runs, bowler charged runs). The other streams are computed descriptively and have no role in the rule.
- `window`: `PRE_TEST` for the comparison; the comparison is repeated on `TRAIN` only as a stability check.
- `metrics`: M1 to M6 as below. Only M1, M4 and M5 enter the rule. M2, M3 and M6 are reported descriptively and have no role in the rule.
  - R(d,c): odd/even split-half Spearman-Brown reliability of definition d in cell c, primary stream, PRE_TEST, minimum 6 pressure balls per half, at least 10 players. Match-cluster bootstrap, 1000 draws on `Study.W`; `lo(d,c)` is the 2.5th percentile of the draws.
  - M1(d): Fisher-z pooled R over the four cells (weights n-3, correlation clipped at 0.99). `SE1(d)` is the SD over bootstrap draws of the pooled M1 (the same match-cluster draws recomputed pooled per draw).
  - M2: split-covariance signal share `cov(half1, half2) / var(player means)`.
  - M3: share of players whose match-cluster bootstrap 95% interval for the raw mean residual excludes the cell pooled mean.
  - M4(d): a single scalar, the median over players of pressure-ball counts, with players pooled across the four cells.
  - M5(d): median over 1000 match-cluster resamples of the Spearman correlation between the resample player ordering and the full-window ordering, taken per cell and then medianed across the four cells.
  - M6(d,c): control reliability, the split-half reliability of a non-pressure ball sample matched to the pressure sample on balls per player (same player, same match set, same number of balls, drawn with a fixed seed from non-pressure balls); report `R(d,c) - M6(d,c)`. Descriptive only, because it is not a selection input.
- `rule`: PASS(d) iff R(d,c) is estimable in all four cells and `lo(d,c) > 0` in at least three cells. TOP(d) iff PASS(d) and `M1(d) >= max over passing definitions of M1 - SE1(best)`, where best is the passing definition with the largest M1. Order inside TOP: M4 descending, then M5 descending, then id ascending. The output is a pass list and a top group, not a selection.
- `stability_outcomes`: if the TOP set computed on TRAIN-only differs from the PRE_TEST TOP set, the report states `DEFINITION_ORDER_NOT_STABLE` and names no top group (the pass list is still reported).
- `confound_control`: M1, M2 and M5 are recomputed on the intersection of players eligible under all nine definitions per cell, and both versions are reported. The rule is evaluated on the intersection version when the intersection has at least 30 players in every cell. Otherwise the report states `COMPARISON_CONFOUNDED`, the output is the pass list only, and no top group is named.- `multiplicity`: nine candidates examined; no correction applied; any top group is labelled PROVISIONAL and does not replace `any|q0.75`.
- `forbidden_inputs`: player identity, player rank, score level, Top-10 membership, nationality, capped status, TEST outcomes, Cricsheet.
- `provisional_definition_unchanged`: `any|q0.75` stays the provisional definition regardless of outcome. A change needs a user decision.

**Run-order enforcement (`app/phase6/criteria.py`, review finding 2).** DuckDB tables carry no creation timestamp, so ordering is enforced by an append-only table `p6_run_log` (`seq` INTEGER primary key, `step` VARCHAR, `started_utc` TIMESTAMP, `criteria_sha256` VARCHAR, `config_sha256` VARCHAR, `git_blob_sha` VARCHAR) written only through `app/phase6/store.py::append_run_log`, which only inserts (no update, delete or replace; the store module exposes no other write path to this table, and a test asserts that).

- `write_criteria()` serialises the criteria with sorted keys, writes `config/phase6_selection_criteria_v1.json` and the hash file `{criteria_path, sha256, investigation_config_sha256}` (no timestamp is trusted), refuses to run if the hash file or a `p6_run_log` row already exists, and inserts `seq = 1`, `step = "plan"` with the criteria hash. The criteria file and the hash file are committed to git before the first estimator run; the git blob hash (`git hash-object`) is stored in `p6_run_log.git_blob_sha` and embedded in `phase6_investigation_plan.md`.
- Every later step inserts its own row (`seq` = max + 1) before it writes any result table. `verify_criteria(step)` raises `CriteriaError` unless: row `seq = 1` exists with `step = "plan"`; its `criteria_sha256` equals the SHA-256 of the criteria file now on disk and the hash in the hash file; its `started_utc` is earlier than the current step's `started_utc`; and the criteria JSON contains no forbidden key or word (`player`, `rank`, `top10`, `promot`) outside the `forbidden_inputs` list. If the criteria file is rewritten after the plan step, the hash no longer matches and every step fails.
- `definition_compare.run()` calls `verify_criteria("definition_compare")` first, and writes `criteria_sha256` into every `p6_definition_*` row and the report header. Before writing, it checks whether a `p6_definition_*` table exists with a different `criteria_sha256` and refuses (a human must drop it).
- The orchestrator runs the plan step first and fails if `p6_run_log` has no `seq = 1` row when any other step starts. The earlier "hash-file timestamp versus table timestamp" check is removed because it cannot be implemented.
### 4.2 Windows

| Window | Rows | Use |
|---|---|---|
| Primary (`PRE_TEST`) | TRAIN + VALIDATION, 723 matches, 2022-01-22 to 2025-12-19, excluding any of the 42 late-dated T20I matches (they are in TEST by date and not loaded) | All primary-investigation tables |
| `TRAIN` | 512 matches | Order-stability check, split-half comparison with Phase 5 |
| 2024-onward | `match_date >= 2024-01-01` inside PRE_TEST: 403 matches | Separate recent-form analysis |
| 2025-onward | `match_date >= 2025-01-01` inside PRE_TEST: 211 matches (= VALIDATION) | Separate recent-form analysis |
| Season k | calendar year within PRE_TEST (2022-2025) | Robustness, labelled `ROBUSTNESS_NOT_VALIDATION` |

The user asked for the full available verified history as the primary window. TEST outcomes may not be used for tuning, TEST was already opened once and 42 T20I dates are unverified, so "full available" is implemented as PRE_TEST. This is OD-1 and the register states that the TEST matches are not in the primary window.

**Window ratio for windows without TRAIN rows (review finding 6).** `el.window_ratio(cell, windows, "TRAIN")` is not used for recent windows. The ratio for a recent window is `window_pressure_balls / PRE_TEST_pressure_balls` per cell, applied to the four frozen thresholds (rounded up, never below 1). It is labelled provisional (OD-2) and is the same formula for 2024-onward and 2025-onward, so the two are comparable.

**Residual comparability.** B0 is fitted on TRAIN, so 2024-onward mixes 192 in-sample TRAIN matches with 211 VALIDATION matches, while 2025-onward is VALIDATION only. Every recent-form row carries `share_rows_in_b0_fit_window` (the share of the window's balls that were in the B0 fit window), and the report states that cross-window comparison is confounded by this. A clean-residual sensitivity, `2024_VALIDATION_ONLY` (VALIDATION rows dated 2025-01-02 onward are the only rows with out-of-fit residuals, so this is the same set as 2025-onward and is reported as such, not as a separate 2024 result), is therefore not run separately; the 2025-onward table is the clean-residual analysis, and the 2024-onward table is labelled mixed-residual.

**Recent-form fitting rule.** The baseline B0 and pressure thresholds are fitted on TRAIN only (unchanged `Study`), so residuals for a match are identical whether the match is analysed in the primary or a recent window. Within a recent window there may be no TRAIN rows (2025-onward has none), so the within-window variance components, shrinkage `k`, eligibility ratio and reliability are fitted on all rows of that window, in-sample, and every table row says `FIT_ON=WINDOW_IN_SAMPLE`. The window never borrows a primary `k` or `tau2`. Ball thresholds are the Phase 4 frozen thresholds (4 numbers) multiplied by that window's own window ratio; labelled provisional (OD-2). A window with fewer than 8 players with pressure balls in a cell, fewer than 10 per split-half, or no positive variance returns `NOT_ESTIMABLE`, never a primary value. The fit uses the window's own match-cluster bootstrap weights drawn with the same seed over the window's matches.

### 4.3 Estimators of between-player variance

All operate on one cell: per-player mean residual `y_i`, ball count `n_i`, matches `m_i`, effective count, within-variance `sigma2`. Each returns `{value, status, converged, method, noise_basis}`. Statuses reuse the Phase 5 constants.

| ID | Method | Noise model | Identifiability note |
|---|---|---|---|
| E1 | Moments with floor (Phase 4): `between = var(y) - mean(sigma2/n_eff_kish)`; `tau2 = max(between, 0.01*sigma2)` | per-ball variance / match count | Reproduces Phase 4 exactly; negative in 48/48 |
| E1b | Moments, same, noise `sigma2/n_i` (ball independent) | independent balls | Optimistic about noise precision |
| E1c | Moments, noise = match-cluster robust variance of `y_i` | clusters = matches | Needs `m_i >= 2`; unstable for small `m_i` |
| E2 | REML normal-normal with known per-player noise (`rb.reml_tau2`) under each of the three noise bases | normal | Boundary at 0; reports `converged` |
| E3 | ML normal-normal (same code, ML score, no REML correction term) | normal | Downward-biased; shown next to E2 |
| E4 | Beta-binomial for binary streams (boundary or wicket indicators) by marginal likelihood: `tau2_p = a*b/((a+b)^2 (a+b+1))`; ball counts scaled by the design effect `n_eff/n` as `beta_binomial_shrink` already does | overdispersion absorbed in `a+b` | Only for binary streams; the primary streams are continuous runs |
| E5 | Gamma-Poisson for count streams (runs per ball as counts of runs per exposure) by marginal likelihood | Poisson noise | Runs per ball are bounded (0-6) and not Poisson; reported as sensitivity, flagged `MISSPECIFIED_FOR_RUNS` for the runs streams |
| E6 | Match-cluster bootstrap variance components: resample matches (`rb.boot_moments` with `en.cell_weights`), compute E1c per draw, report median and 95% interval and the share of draws with `tau2 > 0` | clusters = matches | Interval width is the evidence of weak identifiability |
| E7 | Split-covariance: `cov(odd mean, even mean)` (`rb.split_cov_rows`) | none | Model-free; the arbiter between E1 and E1c |

Per cell the study stores point estimates, bootstrap intervals and statuses in `p6_variance_estimators` (one row per cell x estimator x basis x window). Decision rule for the verdict, declared here and repeated in the plan: the between-player variance is called **identified and positive** if E7 is positive with a bootstrap 95% lower bound above 0 and E1c on the match-cluster basis is positive in at least 90% of the E6 bootstrap draws (E2 is reported as a point estimate with `converged`, and must have the same sign as E1c, but has no draw share and is not part of the 90% test); **not identified** if E7's interval contains 0 and the E6 draw share positive is below 90%; otherwise **weakly identified**. E4 and E5 are sensitivity only and never enter a verdict. The report states the verdict per cell and per context.

### 4.4 Why is the estimate at the floor? Diagnostics

The question has three candidate explanations; each gets a pre-declared test.

- **H-A, true tau2 about 0.** Test: E7 and E6 intervals include 0 and the detectability simulation (`rb.simulate_detectability`, ratios 0.0005 to 0.025 of sigma2, 400 replications) shows the design could detect a ratio of 0.01 at power at least 0.8. If power is below 0.8 the answer is "cannot tell", not "zero".
- **H-B, noise-model misspecification.** Tests: (i) F6/F7 arithmetic, computing the ratio `mean(sigma2/n_eff_kish) / mean(sigma2/n_i)` per cell, which should be near the mean balls per match if the misspecification explains the negative moment; (ii) the sign flip across noise bases; (iii) residual-variance heteroscedasticity, the ratio of residual variance in the lowest versus highest tercile of player ball counts; (iv) ICC of ball residuals within match and within innings (one-way ANOVA ICC, matches and innings as groups), and Pearson dispersion of the moment fit; (v) overdispersion check for E4/E5 where applicable.
- **H-C, sample size.** Test: required-sample projection `n* = R/(1-R) * sigma_eff/tau2` (`rb.required_sample`) using the lower and point tau2 from E7/E6; if the lower bound is 0 the projection is `NOT_ESTIMABLE` and the report says so.

**Numeric flags (declared in the criteria/plan files before any run).**

| Flag | Supported when |
|---|---|
| H-A power | `rb.simulate_detectability` power at ratio 0.01 is at least 0.8 |
| H-A null | E7 bootstrap 95% interval contains 0 and the E6 share of draws with `tau2 > 0` is below 90% |
| H-B(i) | `mean(sigma2/n_eff_kish) / mean(sigma2/n_i)` is within 25% of the mean balls per match (ratio / balls-per-match in [0.75, 1.25]) |
| H-B(ii) | sign of the between variance differs between the Kish basis (E1) and the match-cluster basis (E1c) in the same cell |
| H-B(iii) | residual-variance ratio, lowest versus highest tercile of player ball counts, is above 1.5 or below 0.67 |
| H-B(iv) | within-match or within-innings ICC of ball residuals above 0.05, or Pearson dispersion of the moment fit above 1.5 |
| H-B overall | at least two of H-B(i) to (iv) supported, including H-B(ii) |
| H-C | E7 or E6 lower bound above 0 and `rb.required_sample` gives a finite `n*` larger than the observed median `n_eff` |

**Flag-to-verdict table (evaluated in this order).**

| Condition | Verdict |
|---|---|
| H-A null and H-A power and H-B overall not supported | `H-A_SUPPORTED` (true between-player variance about 0) |
| H-A null and not H-A power | `UNIDENTIFIED` (design cannot tell) |
| H-B overall supported and H-C supported | `MIXED` |
| H-B overall supported only | `H-B_SUPPORTED` |
| H-C supported only | `H-C_SUPPORTED` |
| Any other combination | `UNIDENTIFIED` |

Verdict text is generated from these flags by a function with unit tests for every row of the table, never hand-written. The 48 contexts are processed with the context data in `p5_context_stats` read through `app.phase5.context_stats` (read-only; `p5_context_fit` is not modified). Sparse contexts (fewer than `min_train_players_for_fit` = 8 players or fewer than 10 per half) are `NOT_ESTIMABLE` with a reason.

**Consequence statement (conditional, produced by the code).** If a cell is "not identified", the report recommends: wider uncertainty (intervals from E6), shorter lists, and contexts stay restricted. It does not recommend changing the shrinkage estimator. If H-B is supported, the report records an open decision for the user (switch the noise basis in the methodology) and does not apply it, because a methodology change is outside this phase's stop condition.

### 4.5 Floor arithmetic check

A function `floor_arithmetic_table()` builds, from `CONFIGS` in `app/phase4/shrink.py`, a fit with `between = -1.0`, `sigma2 = 3.0` and calls `k_for` for every configuration. Expected: 0 (`shrink_none`), 100, 100, 50, 25, 1000, 100 (`shrink_target0` has no zero flag and the same floor), and the non-finite branch (`sigma2 = nan`) returns `1/floor`. The test asserts these against `k_for` and against the hand formula `sigma2 / (max(mult*floor, floor) * sigma2)`; it also loads `phase5_context_fit.json` and asserts all 48 records have `k == 25.0` for `shrink_tau4`, to confirm that the stored output used the multiplier-after-floor arithmetic.

### 4.6 Split-half reliability

Implementation in `app/phase6/split_half.py` wraps `rb.half_masks`, `rb.half_stats`, `rb.split_half` and `rb.sb` and adds window selection by date (the Phase 5 `window_cols` only supports `TRAIN` and `PRE_TEST`; Phase 6 builds its own boolean column mask from `CellData.dates`, leaving Phase 5 unchanged).

- **Schemes:** odd/even over each player's own matches in date order; early/late (first half versus second half of each player's matches in time); repeated random match splits (200 repeats, seeded per repeat from `seed + repeat`), each player's matches randomly partitioned into two halves.
- **Statistic:** Pearson r between the half means across players with at least `min_balls_per_half` (6) pressure balls in each half and at least `min_players_estimable` (10) players. Spearman-Brown: `r_sb = 2r/(1+r)`. If `r <= -1` the status is `NOT_ESTIMABLE`; a negative r gives a negative `r_sb`, reported as is (not clipped), because clipping would hide that there is no signal. The report explicitly notes that SB assumes parallel halves and that early/late violates stationarity.
- **Confidence intervals:** (i) bootstrap over players (resample players with replacement, recompute r and SB, 1000 draws), (ii) bootstrap over matches (match-cluster weights `W`, `half_stats` with weights), 95% percentile intervals. Random-split mode reports the median across repeats and the SD across splits, plus a bootstrap CI computed on the per-repeat median.
- **Units:** definition x format x role x stream x window x mode. Streams are the four existing streams (runs, charged, and the others in `STREAMS`).
- **Aggregation across cells:** Fisher z with weights `n-3`, with the correlation clipped at ±0.99 as in the Phase 4 definition rule (`corr_clip`).
- **Data labelled** `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST rows cannot enter (see 4.12).

### 4.7 Definition sensitivity and resampling instability

Run only after `verify_criteria()` passes. For each of the nine definitions in `config/phase4_definition_rule_v1.json` (contexts chase/inn1/any x q 0.75/0.9/0.95) use `Study.all_cells(defn)`. Thresholds are fitted on TRAIN per q (`Study.thresholds`), exactly as in Phase 4/5. Compute M1 to M5 per cell and the intersection-player versions (criteria file). Runtime: 9 definitions x 8 cells x 1000 draws for R and M5, plus 200 random splits for the descriptive random-split mode, is vectorised over draws (`Study.W` matrix products) and is budgeted at under 30 minutes for the full run on the project machine; `--quick` (200 draws, 20 random splits) exists for tests and is refused by the orchestrator for any run that writes reports. The 4.6 grid over four streams, three modes and the windows is run only for the primary window; recent-form windows run odd/even and the primary stream only. Resampling instability: for each of 1000 match-cluster resamples compute per-player mean residual, Spearman correlation with the full-window ordering over common players; report median and 5th percentile. No code in this module receives or emits a player id beyond the join key used to align orderings; rank vectors are `numpy` arrays and the output tables carry no player column. A test inspects the output frame columns.

### 4.8 Context-specific reliability

For the 48 atomic contexts (format x role x phase {ALL, powerplay, middle, death} x situation {ALL, chase, first_innings}) read via `context_stats.build_context_stats` and `cell_from_stats` (read-only): split-half (odd/even and random), E7 signal share, `n_eff`, the context data weight recomputed with `B = n_eff_min/(n_eff_min + k)` using the context's own stored `k`, and a regression check against `p5_context_eligibility_rules.marginal_data_weight` (equality within 1e-9, using the stored eligibility threshold). The ALL/ALL context is checked against the corresponding primary cell. Pass/fail against 0.5 is copied from the stored Phase 5 value; Phase 6 never sets a gate state. Contexts that fail remain restricted; the report lists them.

### 4.9 Eligibility thresholds under the reliability lens

Use `rb.reliability_by_opportunity` with the ladders in `phase5_investigation_v1.json` (batter 12 to 120 balls, bowler 12 to 144) to find, per cell and per target (0.5, 0.7, 0.8), the smallest opportunity count at which split-half reliability reaches the target, with a bootstrap interval (players and matches). Also the opportunity at which the data weight `n_eff/(n_eff+k)` reaches 0.5 for `k` under each estimator, using the Kish conversion observed in the cell (median `n_eff` per ball for players around each ladder step, measured, not assumed). Compare with the frozen thresholds (IPL batter 20, T20I batter 16, IPL bowler 49, T20I bowler 29) and the Phase 4 candidate set in `p4_eligibility_candidates`. Statuses: `TARGET_REACHED`, `TARGET_NOT_REACHED_WITHIN_LADDER`, `NOT_ESTIMABLE`. The script reads SHA-256 of `config/pressure_eligibility_rules_v1.json`, `config/phase5_gates_v1.json`, `phase4_frozen_choices.json` before and after and asserts equality. Strictly descriptive; no threshold changes.

### 4.10 Data-weight options table

Data weight in this code base is `B = n_eff / (n_eff + k)` (`shrink.estimate`; marginal version in `context_eligibility.py`). With `k = sigma2/tau2` fixed at 25 by the floor in 48/48 contexts, B reaches 0.5 only where the least-experienced eligible player has `n_eff >= 25`, with `n_eff` a count of equal-size matches. This has a consequence for the options: raising `n_eff` is legitimate; lowering `k` is legitimate only when it comes from a data-based estimate of `tau2` with interval, never from a multiplier chosen to pass.

`p6_data_weight_options` columns: `option_id`, `option_group`, `label` (`ACTUAL_RE_ESTIMATE` or `DESCRIPTIVE_PROJECTION`), `scope` (format-role cell or context), `window`, `n_eff_marginal`, `k_used`, `k_source`, `data_weight`, `data_weight_lo`, `data_weight_hi`, `gate_used` (always 0.5, read from `app.phase4.eligibility.GATE_B` at run time), `passes_gate`, `extra_n_eff_required`, `extra_matches_required`, `pool_size_after`, `requires_methodology_decision` (bool), `notes`. A validator rejects the table if any `gate_used != 0.5`, if any `option_id` matches `lower|relax|bypass|multiplier|tau_mult|gate`, or if `k_source` is `ASSUMED_MULTIPLIER`.

**Effective-count basis (review finding 8).** `p6_data_weight_options` has a column `n_eff_basis` (`KISH_MATCH` or `MATCH_CLUSTER`). The Phase 4 basis pairs `k` with the Kish match-equivalent count. A `tau2` from a match-cluster model has the match as noise unit, so O3 and O6 pair `k_used` with the match-cluster effective count `m / (1 + (m_bar - 1) * ICC)` (`m` matches, `m_bar` mean matches per cluster unit, ICC from the same bootstrap draw), never with the Kish count. All other options use `KISH_MATCH`. A validator rejects a row where `k_source` is a match-cluster estimate and `n_eff_basis` is `KISH_MATCH`, or the reverse. The 48-context regression against `p5_context_eligibility_rules` in 4.8 is run only on `KISH_MATCH` rows.

Options (legitimate):

| ID | Option | Mechanism | Label |
|---|---|---|---|
| O1 | Definition choice judged by reliability | Recompute `n_eff` for the definitions that passed the criteria file; no player outcome used | ACTUAL_RE_ESTIMATE of n_eff; `k` unchanged (floor) |
| O2 | Multi-format pooling for players in both formats | `rb.multi_format_pooling`: pooled `n_eff` and pooled reliability for the same players | ACTUAL_RE_ESTIMATE restricted to players in both formats |
| O3 | Partial pooling across similar contexts | Hierarchical normal-normal over the contexts within a format-role (phases within a situation, situations within a phase): robust empirical Bayes with `tau2` by REML and, as robustness, by median-absolute-deviation of player means, with bootstrap interval | ACTUAL_RE_ESTIMATE of tau2/k; `requires_methodology_decision = true`; `n_eff_basis = MATCH_CLUSTER` |
| O4 | Longer window (full PRE_TEST versus TRAIN only; seasons pooled) | `n_eff` increase from added matches | ACTUAL_RE_ESTIMATE |
| O5 | Bowler-specific pressure signals (three Phase 5 candidates) | Sensitivity only; counts and reliability | ACTUAL_RE_ESTIMATE, sensitivity, never feeds API |
| O6 | Match-cluster-basis `tau2` instead of the Phase 4 kish basis | Data-based `k = sigma2_eff/tau2_E1c` with its bootstrap interval; the lower interval bound of `tau2` gives an upper bound on `k` | ACTUAL_RE_ESTIMATE; `requires_methodology_decision = true`; `n_eff_basis = MATCH_CLUSTER` |
| O7 | Required-sample projection | `extra_n_eff_required = max(0, k - n_eff_marginal)` (since B = 0.5 iff `n_eff = k`), converted to matches via the observed `n_eff` per match | DESCRIPTIVE_PROJECTION |
| O8 | Pool restriction (raise eligibility threshold until B >= 0.5) | Pool size left after restriction; reported only to show the cost, `applicable = false` | DESCRIPTIVE_PROJECTION |

Not included, and listed in the report as "excluded by rule": lowering the 0.5 gate, changing the 0.5 requirement, using a larger tau multiplier (`shrink_tau0.5/2/4` are assumption-driven), changing the frozen thresholds downward, using TEST outcomes, or padding pools. The report gives the gate-pass count per option per context out of 48, and says "no option passes" when that is the result. Under no option is a gate state written. `passes_gate` is informational. O6 and O3 mean a different shrinkage methodology, so even a pass leaves the context restricted until the user approves a methodology change.

### 4.11 Recent-form and season robustness

`app/phase6/recent_form.py` builds, for `start in {2024-01-01, 2025-01-01}`, a copy of the `Study` frame filtered by `date >= start` (TEST rows already absent; an `assert_no_test_rows` guard runs on the result) and runs the same estimators, split-half and eligibility/data-weight functions with the in-sample fitting rule in 4.2. Tables `p6_recent_form_2024`, `p6_recent_form_2025`, `p6_recent_form_reliability`; every row has `analysis_label = RECENT_FORM_SEPARATE_ANALYSIS`, `window_start`, `fit_on = WINDOW_IN_SAMPLE`. Subset checks: match ids(2025) is a subset of match ids(2024), a subset of PRE_TEST.

`app/phase6/season_robustness.py`: per calendar season 2022-2025 and per format: split-half (odd/even) within the season, rank correlation of player mean residuals between adjacent seasons (players with minimum balls in both), and leave-one-season-out stability of the cell-level reliability. Tables `p6_season_robustness`, label `ROBUSTNESS_NOT_VALIDATION` on every row and in the report title. The report states that season consistency is not independent validation, that TEST was opened once in Phase 4 and is not pristine, that `PRIMARY_RESTRICTED` (99 matches) is for internal diagnostic comparison only, and that `STRICT_OFFICIAL_ONLY` (0 matches) is a separate empty set.

### 4.12 TEST-lock guard

`app/phase6/lockguard.py` re-exports `phase5.lockguard` (read-only) and adds:

- `assert_no_test_rows(df)`: raises `LockGuardError` if a `period` column contains `TEST`, or if any `match_date` is after `2025-12-31`, or if any `match_id` is in the TEST sets of the manifest.
- `snapshot()` / `assert_unchanged(snapshot)`: SHA-256 of `phase4_lock_log.json`, event count of `phase5_lock_log.json` (must stay 0), and absence of an `OPEN` event.
- An import guard test: AST scan of `app/phase6/**` and `scripts/phase6_*.py` for imports of `evaluate_on_test`, `_open_for_evaluation`, `LockedFrame`, `test_eval`, `load_test_match_outcomes`; any hit fails the test.
- The only data entry point for Phase 6 analyses is `load_study()` (pre-test only). A wrapper `load_study_p6()` calls it and then `assert_no_test_rows(study.d)`. The retention stub, recent-form and season modules take their frames from it.
- The orchestrator calls `snapshot()` at start and `assert_unchanged` at end and after each step.

### 4.13 Gate stays 0.5

`GATE_B` is imported, not redefined. A test asserts `eligibility.GATE_B == 0.5`, that `config/phase5_gates_v1.json` and `app/phase4/eligibility.py` hashes equal the recorded pre-run hashes, that no assignment to `GATE_B` or to a name containing `gate` with a numeric constant below 0.5 exists under `app/` or `scripts/phase6_*` (AST scan), and that `p6_data_weight_options.gate_used` is 0.5 on every row.

### 4.14 Retention stub

`app/phase6/retention_stub.py` creates an empty `p6_retention_status_stub` in `exploratory.duckdb` with columns `player_id` INTEGER, `team` VARCHAR, `season` INTEGER, `status` VARCHAR (check: one of `retained`, `released`, `traded`, `auction_available`, `unknown`, default `unknown`), `source` VARCHAR, `snapshot_date` DATE, `verification_status` VARCHAR, `mapping_status` VARCHAR, `ambiguity_note` VARCHAR. DuckDB `CHECK` constraints are supported in `CREATE TABLE`. The design note `phase6_retention_import_design.md` covers the future importer: separate availability statuses with explicit `unknown` default; source, snapshot date and verification status per row; mapping to `player_id` through the existing identity rules with an ambiguity list (unmatched and multiply-matched names go to a review list, never auto-resolved); no inference from squad snapshots; availability never implies capped or uncapped; no scoring or API module may read the table. No data is imported. Tests: table exists with 0 rows; no module under `app/phase4`, `app/phase5`, `app/services`, `app/api`, `app/schemas` mentions `p6_retention`; the table is not in `superr.duckdb`.

## 5. Output tables in `exploratory.duckdb` (all `p6_*`)

`p6_variance_estimators`, `p6_floor_diagnostics`, `p6_floor_arithmetic`, `p6_split_half`, `p6_split_half_ci`, `p6_definition_reliability`, `p6_definition_resampling`, `p6_context_reliability`, `p6_eligibility_reliability`, `p6_data_weight_options`, `p6_data_weight_gate_status`, `p6_recent_form_2024`, `p6_recent_form_2025`, `p6_recent_form_reliability`, `p6_season_robustness`, `p6_retention_status_stub` (empty), and `p6_run_log` (append-only, section 4.1). Every table has columns `label` (`EXPERIMENTAL_NOT_VALIDATED` plus the specific analysis label), `window`, `fit_on`, `seed`, `n_boot`, `criteria_sha256` where applicable. Writes only through `app/phase6/store.py::write_p6_table`, which rejects any name not matching `^p6_[a-z0-9_]+$` and any store path equal to the official database. Tables are written with `CREATE OR REPLACE`, so re-running the orchestrator is idempotent; the definition tables refuse to replace results made under a different criteria hash (4.1).

## 6. Error handling

| Operation | Failure condition | Recoverable? | Caller receives | Logging |
|---|---|---|---|---|
| `verify_criteria` | `p6_run_log` seq 1 missing, criteria bytes no longer match the logged hash, forbidden word, plan row not earlier than current step | Fatal for the definition step | `CriteriaError` (message names the check); script exits 1 | ERROR, one line |
| `write_p6_table` | name not `p6_*`, store equals official DB | Fatal | `StoreError` | ERROR |
| TEST guard | TEST row, date after 2025-12-31, lock hash change, Phase 5 event count != 0 | Fatal for the whole run | `LockGuardError`; orchestrator exits 1 and does not write reports | ERROR |
| Estimator on a cell | fewer than 10 players, non-finite input, REML non-convergence, singular information | Recoverable | row with `status` `NOT_ESTIMABLE` or `converged=False`, value NaN stored as NULL | WARNING once per cell in the run log, not per draw |
| Bootstrap | fewer than 20 finite draws for an interval | Recoverable | interval NULL, status `CI_NOT_ESTIMABLE` | none (status carries it) |
| Beta-binomial / gamma-Poisson | non-binary or non-count stream, fit does not converge | Recoverable | status `MISSPECIFIED_FOR_STREAM` or `NOT_ESTIMABLE` | none |
| Recent-form window | fewer than 8 players or too few per half | Recoverable | `NOT_ESTIMABLE`; primary values never substituted | none |
| Preservation check | any hash of `superr.duckdb`, source CSVs, `phase4_*`/`phase5_*` files, `p4_*`/`p5_*` tables differs from `phase6_prerun_hashes.json` | Fatal | orchestrator exit 1, `phase6_orchestrator_run.json` records the differing paths | ERROR |
| Cache | invalid `scope` | Fatal programming error | `ValueError` | none |
| Public `/players` | player id unknown | Recoverable | 404 `NotFoundError` (existing) | existing |
| Internal route | missing/wrong token | Recoverable | 401 `ADMIN_AUTH_FAILED`; 503 `ADMIN_DISABLED` when no token set (existing) | existing |

Library warnings (divide by zero) stay suppressed inside `np.errstate` blocks, as Phase 5 does; nothing is silenced globally.

## 7. Input validation rules

| Input | Rule | On failure |
|---|---|---|
| `config/phase6_investigation_v1.json` | required; `declared_before_any_run` true; `seed` int; `n_boot` int 200 to 5000; `windows` subset of the list in 4.2; `gate_value_expected` equals 0.5; `test_outcomes_used` false | `ConfigError`, exit 1 |
| Criteria file | required; keys and metrics exactly as in 4.1; hash file present | `CriteriaError` |
| CLI flags of scripts | `--n-boot` (int 200 to 5000, default config), `--seed` (int, default config), `--store` (path; must not equal the official DB), `--compare-hashes` (flag) | argparse error, exit 2 |
| `min_balls_per_half`, `min_players_estimable` | positive ints from config | `ConfigError` |
| Window start | one of the two configured dates | `ConfigError` |
| Cache `scope` | one of `internal`, `public` | `ValueError` |
| Public `/players` query | existing validated query params (limit 1 to 200, offset 0 to 100000, `q` max 64, enums) minus `min_pressure_matches` | 422 (existing handler) |

## 8. Invariants and the layer that owns them

| Invariant | Owner | Why that layer |
|---|---|---|
| Gate 0.5 never lowered | `app/phase4/eligibility.GATE_B` (single constant) plus the AST test | One definition, imported everywhere; the test catches any new assignment |
| No TEST outcome in Phase 6 | `load_study_p6` (data entry) plus the import-guard test | Prevention at load; scanning at test time |
| Criteria precede results | append-only `p6_run_log` plus `criteria.verify_criteria` at the start of every step and at table write | Only the comparison step can violate it |
| Official data and Phase 4/5 artefacts unchanged | orchestrator preservation check vs. `phase6_prerun_hashes.json` | Needs a global view across steps |
| Only `p6_*` tables written | `store.write_p6_table` | All writes go through it |
| Public descriptive responses contain no score/rank/eligibility | the Pydantic response model (allow-list) plus schema test | FastAPI strips undeclared fields at serialization, so a service bug cannot leak a field |
| Cached payloads are not shared | `RankingCache` (copy on put and get) | Callers cannot be trusted to avoid mutation |
| Three real classification values | `ClassificationStatus` literal in the schema and `STATUS_VALUES` in code | One place each; tests compare both |
| No padding of results | existing `paginate_ranked` and pool-size rules (5 and 10, provisional) | Unchanged in Phase 6 |

## 9. Reproducibility and preservation

Seed 20260512 everywhere; each stage derives sub-seeds as `seed + stable_index` (cell index in a sorted list, repeat number) so the result does not depend on iteration order. Bootstrap weights reuse `Study.W` for the primary window; recent-form windows draw their own with `en.global_weights(match_ids, n_boot, seed)`. Output tables are written with sorted rows and rounded to 12 significant digits where floats are exported to CSV/JSON so the second-run hash comparison is stable. `scripts/run_phase6.py --compare-hashes` compares `phase6_output_hashes.json` (volatile files such as the run timestamp excluded). The preservation step recomputes SHA-256 of `superr.duckdb`, source CSVs, all `phase4_*` and `phase5_*` report files, and `table_hashes(store, "p4_")` and `("p5_")` against `.agents/tasks/phase6_prerun_hashes.json`, which must exist before the first run. No `phase4_*` or `phase5_*` file is overwritten; Phase 6 writes only `phase6_*`.

## 10. Testability

Unit-testable without the database:

- Estimators on synthetic data with known variances: normal-normal tau2 = 0.04, 300 players, recovered within 25%; zero-between-variance data gives REML near 0 with `converged` and statuses not positive, never a large positive; beta-binomial recovers known `(a, b)` within 15%; gamma-Poisson likewise; a data set built with sigma2 / n_eff_kish noise deliberately mis-stated shows the sign flip between bases (mirrors the real finding).
- Floor arithmetic against `k_for`, hand formula and the stored 48 contexts.
- Split-half and Spearman-Brown on synthetic players with true reliability 0.6 (recover within 0.1 over 400 players), pure-noise data (CI covers 0), formula `sb(0.5) = 2/3`, bootstrap deterministic per seed and different across seeds.
- Criteria hash behaviour in a temp directory (missing file, edited criteria, later hash timestamp, forbidden word).
- TEST guard on a synthetic frame; import-guard AST scan.
- Gate AST scan; options-table validator on synthetic rows including a forbidden option id.
- Recent-form filters on a synthetic frame, subset relations.
- Cache: key components, deep-copy isolation, concurrency.
- Schema tests (pure Pydantic introspection) and lint test for vacuous assertions.

Integration-tested (real data, reading `exploratory.duckdb`): the 48-context regression against `p5_context_fit`/`p5_context_eligibility_rules`, window match counts against raw CSV (723, 403, 211), preservation, orchestrator determinism, the API test client for `/players` and the internal routes, and the independent spot checks (one split-half r recomputed from raw per-match sums, one variance component by a direct formula, a 2024-onward match count from `matches.csv`, the primary window count and range, cache isolation through the service, and the gate value from stored output).

Additional tests required by the brief (review finding 9):

- **No Cricsheet:** AST and text scan of `app/phase6/**`, `scripts/phase6_*.py` and all scoring modules for `cricsheet` (case-insensitive) in imports, paths and string literals; zero hits except in the `forbidden_inputs` list of the criteria file.
- **Classification wording:** `ClassificationStatus` args equal the three real values; `STATUS_VALUES` has three entries; `DISABLED_PLACEHOLDER_VALUES == ("VERIFIED_UNCAPPED",)`; a scan of the OpenAPI schema, `docs/*.md` and Phase 6 report text finds no phrase "four statuses", "four classification" or a list of four values presented as real.
- **Retention stub unreferenced:** no module under scoring, API, services or schemas contains `p6_retention`; `p6_retention_status_stub` has 0 rows; the table is absent from `superr.duckdb`.
- **Primary tables unmodified by recent-form:** `table_hashes(store, "p5_")` and the Phase 6 primary tables (`p6_variance_estimators`, `p6_split_half`, `p6_definition_reliability`) have identical hashes before and after `recent_form.run()` and `season_robustness.run()`.
- **Internal players routes:** `/internal/players` and `/internal/players/{id}` return 401 with a missing or wrong token, 503 when no token is configured, and 200 with the full `PlayerRow` fields (including `eligible_scopes`) with the correct token.
- **Run log:** `p6_run_log` accepts inserts and rejects update/delete through the store API; a changed criteria file makes `verify_criteria` raise; running a step with no seq 1 row raises.
- **Verdict function:** one test per row of the flag-to-verdict table in 4.4.
- **Selection rule:** synthetic reliability tables exercise PASS, TOP, tie-breaks, `DEFINITION_ORDER_NOT_STABLE` and `COMPARISON_CONFOUNDED`.

Existing 793 tests must keep passing. Edits to existing tests are limited to the three vacuous assertions and the API tests that assert fields removed from the public model; each edit is listed in the cleanup report with the reason.

## 11. Deliverables and delivery order

Deliverable map (review finding 15). Every report is written by the script named; `scripts/run_phase6.py` calls them in order.

| Deliverable | Written by |
|---|---|
| `phase6_investigation_plan.md`, criteria hash | `scripts/phase6_investigation_plan.py` |
| Cleanup report (classification, assertions, public schema, cache) | `scripts/phase6_cleanup_report.py` |
| Variance-estimator, floor-diagnostics and floor-arithmetic reports | `scripts/phase6_variance_study.py` |
| Split-half reliability report | `scripts/phase6_split_half.py` |
| Definition-comparison report | `scripts/phase6_definition_compare.py` |
| Context-reliability and eligibility-reliability reports | `scripts/phase6_context_reliability.py` |
| Data-weight options report | `scripts/phase6_data_weight_options.py` |
| Recent-form and season-robustness reports | `scripts/phase6_recent_form.py`, `scripts/phase6_season_robustness.py` |
| `phase6_retention_import_design.md`, retention stub | `scripts/phase6_retention_stub.py` |
| `phase6_unresolved_issues.md`, user summary (copied to `.agents/tasks/phase6_user_summary.md`) | `scripts/phase6_final_reports.py` |

The unresolved-issues register carries forward every Phase 5 register item, each with an explicit status (`UNCHANGED`, `CHANGED`, `CLOSED`) and a one-line reason; a test asserts that every Phase 5 item id appears in the Phase 6 register. The brief's full report list is checked against the table by `scripts/phase6_final_reports.py`, which fails if a named file is missing.

Delivery order:

1. Pre-run hashes already present; run baseline tests.
2. Part A (cleanup) with tests, docs updates (`frontend_backend_contracts.md`, `backend_implementation_spec.md`).
3. Write investigation config, criteria file and hash; write `phase6_investigation_plan.md`.
4. Estimators, floor study, split-half; spot checks.
5. Definition comparison, context reliability, eligibility reliability, data-weight options.
6. Recent-form and season robustness, retention stub and design note.
7. Reports, unresolved-issues register, user summary, orchestrator, README, final verification.
8. Stop for user review. No methodology change, no publication, no TEST access, no retention import.
