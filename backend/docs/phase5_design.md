# Phase 5 Technical Design (INTERNAL / EXPERIMENTAL ONLY)

Status of everything described here: `EXPERIMENTAL_NOT_VALIDATED`. No official Top 10, no official model, no TEST outcome read, no validation claim. The primary pressure definition `any|q0.75` is PROVISIONAL.
Companions: `d:/Data/.agents/tasks/phase5_plan.md` (chunks and files), `d:/Data/.agents/tasks/phase5_brief.md`, `d:/Data/.agents/tasks/phase5_design_notes.md` (short list of decisions and corrections). The user's decisions quoted in the brief win over this document.

## 0. Overview and locked stack

Phase 5 adds one new package, `app/phase5/`, on top of the approved Phase 4 code. It does four things: (1) migrates the capped-status labels into three separate values and disables strict-uncapped output; (2) builds a per-match date-verification table for the 42 late T20I matches and freezes a restricted TEST set definition without opening TEST; (3) adds a publication-gating layer so every score, ranking or selection output is `INTERNAL_EXPERIMENTAL_ONLY` until every gate passes; (4) adds a dynamic filter-driven ranking engine that re-aggregates stored delivery-level residual statistics for the chosen context, plus investigations (variance decomposition, reliability, sensitivity, stability), a methodology lock and one experimental refit on TRAIN+VALIDATION.

Technology stack (locked on approval, no new dependencies): Python 3.11 (`python`), pandas, numpy, DuckDB (`superr.duckdb` read-only, all derived tables in `exploratory.duckdb` with the `p5_` prefix), FastAPI with Pydantic v2 under `/api/v1`, pytest with HTTPX `TestClient`, Ruff. Statistics are implemented in numpy (no scipy, statsmodels or networkx). Seed `20260512` everywhere, bootstrap 1000 draws unless stated.

Reuse, do not duplicate: `app/phase4/engine.py` (`base_rows`, `tag_rows`, `build_cell`, `Cell`, `global_weights`, `cell_weights`, `point_estimates`, `draws`, `rank_summary`, `summarize_ranking`, `player_ranking_table`), `shrink.py` (`match_stats`, `player_table`, `fit_cell`, `k_for`, `estimate`, `match_weights`, `bootstrap_draws`), `scoring.py` (`add_signals`, `fit_thresholds`, `combine_formats`), `baseline.py` (`prepare_frame`, `fit_baseline_set`), `eligibility.py` (`candidate_thresholds`, `window_ratio`, `evaluate_cell`, `decide`, `analysis_rule`, `eligible_mask`), `split.py` (`Split`, `TestLock`), `lockguard.py`, `app/analytics/integrity.py`, `app/analytics/reporting.py`, `app/api/errors.py` (`ApiError`), `app/api/deps.py` (`require_admin`).

### 0.1 Corrections to the plan found while designing (each is binding)

1. **Cricsheet identity matching must not read outcome fields.** The plan confirmed Cricsheet match identity with winner and first-innings total. Those describe TEST-period match results. Even though Cricsheet is not the lock's data, reading results of TEST matches runs against "keep TEST untouched". Identity is confirmed with pre-play facts only: normalised team pair, toss winner and decision, venue, playing-XI name overlap, series order (see 2.3). Winner, totals, `outcome`, `innings` results are never read by Phase 5 code.
2. **Split-boundary check added.** A wrong date next to a split boundary changes the period of a match (TRAIN/VALIDATION at 2024-12-31/2025-01-01, VALIDATION/TEST at 2025-12-31/2026-01-01, and `test_core_end` 2026-05-31). The date table therefore flags every pre-test and TEST match within 2 days of a boundary (`boundary_adjacent`). It is a flag, not a correction.
3. **The `date_verification` gate has a precise definition** (3.2). The plan left open that the 42 late matches are in TEST and never enter pre-test scores, so a naive "any unverified date in the scoring window" test would pass today.
4. **Situation filters use the carried definition's rows.** `chase` means pressure rows of `any|q0.75` that are in innings 2; `first_innings` means pressure rows of `any|q0.75` in innings 1. They are not the `chase|q0.9` definition. Alternatives get their own context-stat sets only in the sensitivity runs (4.2).
5. **Unknown-classification toggles act only on a filtered axis** (4.6). Otherwise "Indian batters" would silently drop Indian players whose status is unknown (35 of 86 scored Indians), which nobody asked for.
6. **Refit scope.** The refit produces overall scores for the four cells and may also emit context tables under its own prefix, but nothing it produces is out-of-sample evidence (6.4).

## 1. Classification migration

### 1.1 Values and mapping

`international_status` is one of `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `VERIFIED_UNCAPPED`, `UNKNOWN`. Each row also keeps an evidence label (`status_verification`): `VERIFIED_FROM_SOURCE`, `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES`, `UNVERIFIED`. Nationality stays `Indian|Overseas|Unknown` with its Phase 4 verification label.

| Phase 4 `international_status` | Phase 4 verification | Phase 5 status | Note |
|---|---|---|---|
| Capped | DERIVED_FROM_OFFICIAL_T20I_APPEARANCES | DERIVED_CAPPED | data-proven appearance in a T20I playing XI dated on or before `as_of_date` 2025-12-31 |
| Capped | VERIFIED_FROM_SOURCE | VERIFIED_CAPPED | only from an override row or authoritative source |
| Uncapped | VERIFIED_FROM_SOURCE | VERIFIED_UNCAPPED | only from an override row or authoritative source |
| Unknown | UNVERIFIED | UNKNOWN | includes `NOT_PROVEN_CAPPED_IN_DATA` (498) and `FIRST_T20I_AFTER_AS_OF_DATE` (64) sub-reasons, kept as `status_reason` |

Any other combination (for example `Capped` + `UNVERIFIED`, or `Uncapped` + `DERIVED...`) raises `ClassificationMigrationError` (fatal, no output table written, message lists the offending player ids, capped at 20 ids plus the count). `migrate_classification(df)` also asserts: row count in equals row count out, no duplicate `player_id`, and on the real data VERIFIED_CAPPED 0, DERIVED_CAPPED 655, VERIFIED_UNCAPPED 0, UNKNOWN 562 (total 1,217) equal the Phase 4 counts read from `phase4_classification_coverage.json`; a mismatch is fatal. The mapping is stored as `p5_classification_migration_map` and documented in `docs/frontend_backend_contracts.md`. No inference of any kind: the module imports no names, squad, domestic or IPL tables. The 42 late T20I matches are after `as_of_date`, so DERIVED_CAPPED counts do not depend on the disputed dates (the report states this).

The "not proven capped" pool is surfaced only as group `UNKNOWN_STATUS` (display label of the `UNKNOWN` status). It is never labelled uncapped in any schema, table, response or document.

### 1.2 Override validation (`validate_overrides_v2`)

File `config/classification_overrides_v1.csv` stays header-only and byte-identical. Columns: `player_id,field,value,source,verified_by,verified_date`.

| Field | Rule | On failure |
|---|---|---|
| `player_id` | required, integer-like, must exist in the classification base table | row error `UNKNOWN_PLAYER_ID` |
| `field` | one of `international_status`, `nationality` | `INVALID_FIELD` |
| `value` | for `international_status`: `VERIFIED_CAPPED` or `VERIFIED_UNCAPPED`; for `nationality`: `Indian` or `Overseas`. Legacy `Capped`/`Uncapped` rejected with a message naming the mapping | `INVALID_VALUE` / `LEGACY_STATUS_VALUE` |
| `source` | required, non-blank, not a placeholder (`tbd`, `unknown`, `n/a`, case-insensitive) | `MISSING_SOURCE` |
| `verified_by` | required, non-blank | `MISSING_VERIFIED_BY` |
| `verified_date` | required, ISO `YYYY-MM-DD`, not after today's date | `MISSING_OR_BAD_VERIFIED_DATE` |
| duplicates | one row per (`player_id`,`field`) | `DUPLICATE_OVERRIDE` |
| conflict | a `VERIFIED_UNCAPPED` override on a player who is `DERIVED_CAPPED` | `CONTRADICTS_DERIVED_EVIDENCE` (fatal; derived evidence is data-proven and a human must resolve it) |

Validation collects all row errors and raises one `ClassificationConfigError` (existing class, maps to the existing error handler, HTTP 500 at reload time, fatal for that reload only; the previous good table stays in memory). A valid `VERIFIED_CAPPED` override on a `DERIVED_CAPPED` player upgrades only that player and keeps `derived_evidence` in a separate column. Overrides never touch other players. Enforcement layer: `classification_v2` (data layer) owns validity; the repository calls it on every load, so no route can see unvalidated overrides.

### 1.3 `strict_uncapped_enabled`

Computed by `strict_uncapped_capability(...)`, never stored as a hand-edited flag. True only if all hold: (a) `config/classification_source_manifest_v1.json` lists at least one source with `authoritative: true` and `id_keyed: true` (declared by a human; today `{"sources": []}`); (b) at least one `VERIFIED_*` row passes validation; (c) `verified_coverage` (share of the scored pool with a `VERIFIED_CAPPED` or `VERIFIED_UNCAPPED` status) is at least `min_verified_coverage` (provisional 0.95, config). Output: `{enabled, reasons[], source_needed, verified_coverage, scored_pool_size}`. Today: false, reasons `NO_AUTHORITATIVE_SOURCE`, `NO_VERIFIED_ROWS`, `COVERAGE_BELOW_MINIMUM (0.0 < 0.95)`. Fail closed: a missing or malformed manifest gives `enabled=false`.

### 1.4 Disabled response

`STRICT_UNCAPPED_DISABLED` is returned (HTTP 200 on internal routes; the public paths answer 403 `PUBLICATION_GATE_NOT_SATISFIED` first) when a request touches: any `/internal/rankings/uncapped/{kind}`, any of the 6 presets (all declare `depends_on_verified_classification: true`), a custom selection with `IN_UNCAPPED` or `OS_UNCAPPED` having `min>0` or `exact>0`, `uncapped_mode=include_uncapped`, or a dynamic filter with `status=VERIFIED_UNCAPPED`. Allowed and unaffected: `exclude_uncapped`, `max=0`, `exact=0`.

```json
{"result_status": "STRICT_UNCAPPED_DISABLED",
 "reason": "No authoritative player_id-keyed source of international status is loaded.",
 "source_needed": "An authoritative source keyed by player_id (for example an official board or ICC record) plus verified override rows with source, verified_by, verified_date.",
 "capability": {"enabled": false, "reasons": ["NO_AUTHORITATIVE_SOURCE","NO_VERIFIED_ROWS","COVERAGE_BELOW_MINIMUM"], "verified_coverage": 0.0},
 "rows": [], "publication_status": "INTERNAL_EXPERIMENTAL_ONLY", "gate_results": []}
```

No approximation is ever produced: the code path returns before touching score tables. `UNKNOWN_STATUS` is offered as its own labelled group only, with a banner string `NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED`.

### 1.5 Where labels change

All files listed in plan section 0 (`classification.py` is kept as the legacy builder; `uncapped.py`, `selection.assign_group`, `views.py`, `profiles.py`, `spotchecks.check_capped_count`, repo, service, schemas, routes, scripts, configs, docs, five test modules). `p5_player_classification` is the only table read by the API after Phase 5; there is no fallback to the legacy table (a missing table is `StoreUnavailableError`). Legacy `p4_player_classification` stays byte-identical.

## 2. Date verification

### 2.1 Scope and non-modification

Per-match rows for the 42 matches dated after 2026-05-31, and, for context, every TEST-period match (144; 2 T20I TEST-period matches present in `matches` but absent from the Phase 4 state are located and reported with an explanation), plus a CONTROL group: all pre-2026 T20I matches (428 in the plan's count), classified by the same code to show the base rate of source disagreement. `original_match_date` is copied unchanged; the code has no write path to `matches`. A SHA-256 of the `matches` date column is recorded before and after. A user-supplied official date that differs from the original is recorded as `official_date_differs` and the original stays. Nobody corrects dates in Phase 5.

### 2.2 Evidence sources

| Id | Source | Independence | Rule | Counts toward consistent? |
|---|---|---|---|---|
| a | date part of first and last `delivery_ist_time` in the ball-by-ball file (suffix `UTC`; treat clock as UTC) | partly independent of `matches.match_date` (different file, possibly same upstream; independence assumed, not shown) | `AGREE_EXACT` same date, `AGREE_TOLERANCE` within 1 day (the pre-2026 control shows 22 of 428 at 1 day, 3 at 2 days), `DISAGREE` at 2+ days; `NOT_INFORMATIVE` if all times are `00:00:00` placeholders or missing | yes |
| b | ordering inside the competition: dates non-decreasing with `match_number`/stage, gap between consecutive matches within the series window, no team twice on one date | internal | `PASS` / `FAIL` / `NOT_APPLICABLE` | no (can only cause a conflict) |
| c | season/series window from `competitions.csv`. It holds only `comp_id, comp_name, match_format, season`, so the check is "date year equals season year token" | internal, weak | `PASS` / `FAIL` / `NOT_APPLICABLE` | no |
| d | `matches 2026.csv` overlap. It is the IPL 2026 file, so it never overlaps T20I; recorded `NOT_APPLICABLE` | independent when applicable | `AGREE` / `DISAGREE` / `NOT_APPLICABLE` | yes when applicable (IPL TEST rows only) |
| e | Cricsheet date for the same fixture, via the existing normalised team mapping and the staged `cricsheet_index.parquet` | independent upstream assumed; **validation-only, secondary evidence, not an official record** | `AGREE_EXACT`, `DISAGREE` (any difference, off-by-one recorded as `CRICSHEET_OFF_BY_ONE`), `NO_MATCH`, `AMBIGUOUS_MATCH` | yes. The date-verification report states the pre-2026 control-group disagreement rate of (a) and of (e) separately, because `PRIMARY_RESTRICTED` depends on their independence |
| f | internal conflicts: duplicate (teams, date) pairs, team playing two matches within 12 hours by timestamps, match date later than data export date, date equal to another match in the same series | internal | list of conflict codes | no |

### 2.3 Cricsheet use and identity

The Cricsheet index reader selects an explicit column whitelist (match key, date, team names, toss winner and decision, venue, player names); winner, outcome and score columns are never loaded into memory, and a test asserts the whitelist and that no outcome column name appears in the loaded frame. Only `app/phase5/date_verification.py` may import the Cricsheet helpers; no scoring, baseline, ranking, service or repository module may (AST test). Output tables carry `evidence_secondary_source = "CRICSHEET_VALIDATION_ONLY"` and no column derived from Cricsheet exists outside `p5_t20i_date_verification` / `p5_test_match_date_check`.

Candidate selection for a match: same normalised team pair, Cricsheet date within +/-3 days of the original date. Identity is confirmed using non-outcome facts present in both sources, in this order: toss winner plus decision, venue string after normalisation, overlap of the playing-XI name sets (at least 9 of 11 per side after the existing name mapping). If exactly one candidate survives, `identity_basis` records which facts matched. If several candidates survive, ordered assignment is used only when the number of official matches for the team pair in the window equals the number of Cricsheet candidates (k-th with k-th by timestamp order); otherwise `AMBIGUOUS_MATCH` and the source counts as not informative. If no non-outcome fact can confirm identity, the result is `NO_MATCH`, never a guess. Fields `winner`, `outcome`, `innings` results and totals are never read.

### 2.4 Classification rules (pure function `classify(evidence)`)

Order of evaluation:
1. `DATE_CONFLICT` if any of a, d, e is `DISAGREE`, or b is `FAIL`, or c is `FAIL`, or f is non-empty. The reason codes are listed.
2. else `DATE_CONSISTENT_ACROSS_SOURCES` if at least 2 of {a, d, e} are `AGREE_*` (a counts only if informative).
3. else `DATE_SINGLE_SOURCE` if exactly 1 does.
4. else `DATE_UNVERIFIED`.
Every row also has `official_verified` (bool, true only if a valid row exists in the user's official CSV) and the fixed statement `NOT_OFFICIALLY_VERIFIED` when false. A match may be `DATE_CONSISTENT_ACROSS_SOURCES` and still `official_verified=false`; consistency is evidence, not verification. Internal checks b, c, f can lower a class to conflict but never raise a class.

Official template (`config/t20i_official_date_verification_template.csv`, copy in reports): header only `match_id,verified_date,source,verified_by,date_of_verification`. Validation of the user file:

| Field | Rule | On failure |
|---|---|---|
| `match_id` | required, an existing T20I match id in `matches` | row error `UNKNOWN_MATCH_ID` |
| `verified_date` | ISO date | `BAD_DATE` |
| `source` | required, non-blank, not a placeholder | `MISSING_SOURCE` |
| `verified_by` | required | `MISSING_VERIFIED_BY` |
| `date_of_verification` | ISO date, not in the future | `BAD_VERIFICATION_DATE` |
| duplicates | one row per match | `DUPLICATE_MATCH` |

All row errors are collected and raised as one `OfficialVerificationError`; fatal for the script (exit 1); no tables are rewritten on failure. A valid row with `verified_date` equal to the original gives `official_verified=true`. A valid row that differs sets `official_verified=false`, class `DATE_CONFLICT`, code `OFFICIAL_DATE_DIFFERS`.

### 2.5 Primary vs sensitivity TEST sets and the lock

Decision D1 (kept): TEST is not opened. Phase 5 never calls `evaluate_on_test`, `evaluate_frozen` or the full `run_phase4.py`, never writes `phase4_lock_log.json` (sha256 `86f5ce9d588dba715c18e4f3f60b5e8a328c03c2f24c73db73614b2e4d101e42`, events FREEZE, OPEN, CLOSE), and leaves `phase5_lock_log.json` as `[]`. The test-state loader selects only columns that do not start with `out_`, `den_`, `post_innings_`, and only for match-level counts. A later single evaluation needs a user approval, a valid methodology lock and the manifest below; it opens `phase5_lock_log.json` once, not the Phase 4 log.

Sets in `phase5_test_set_manifest.json`:
- `PRIMARY_RESTRICTED` (default): matches with `official_verified=true`, plus matches dated on or before `test_core_end` 2026-05-31 whose class is `DATE_CONSISTENT_ACROSS_SOURCES`. Excludes all 42 late matches until officially verified, and excludes any earlier TEST match that fails the same test.
- `STRICT_OFFICIAL_ONLY`: only `official_verified=true` (0 matches today).
- `SENSITIVITY_ALL`: all TEST matches (the set Phase 4 evaluated).
For each set: match ids, counts of matches, deliveries and distinct players (striker and bowler ids from non-outcome state columns), by competition type. Manifest hash: SHA-256 of canonical JSON of `{set_name: sorted match_ids, rule_text, date_check_table_hash, config_hash}`; no wall-clock value inside the hash. Preservation statement: Phase 4's aggregate TEST evaluation already covered all 144 matches including the 42; it stays byte-identical and is called "sensitivity-only, includes unverified dates" in Phase 5 reports without editing Phase 4 files. A later TEST evaluation is therefore not a pristine hold-out (open decision 1).

### 2.6 Failure handling (dates)

| Operation | Failure | Class | Caller receives | Log |
|---|---|---|---|---|
| read `matches`/ball-by-ball | file missing or schema change | fatal | script exit 1, no tables | ERROR |
| read Cricsheet index | missing or unreadable | recoverable | evidence e = `SOURCE_UNAVAILABLE` for all rows; classes computed without it; report banner | WARNING |
| single match: no timestamps | recoverable | a = `NOT_INFORMATIVE` | row stays | none |
| official CSV invalid | fatal for that run | exit 1, error list | ERROR |
| lock log hash differs from the recorded one | fatal | exit 1, no outputs | ERROR |
| `matches` date hash differs before/after | fatal | exit 1 | ERROR |

Tests: pure `classify` and per-source evaluators are unit tested on synthetic cases (all four classes, off-by-one, 2-day conflict, placeholder timestamps, ordering violation, internal checks cannot raise a class, ambiguous Cricsheet). The raw-CSV recompute and the control-group rate are integration tests (`realdata`).

## 3. Publication gating

### 3.1 Model

`GateInput` (frozen) is read once at app start and on reload: `phase4_frozen_choices.json` (eligibility status per cell), `config/phase5_methodology_status_v1.json`, `p5` date-verification summary, `p5_strict_uncapped_capability`, `config/phase5_gates_v1.json`. `evaluate_gates(inputs, request_needs) -> list[GateResult]` and `publication_status(gates) -> status` are pure functions. Every output of a ranking, selection, score, profile or compare call carries `publication_status` and `gate_results = [{gate_id, passed, applicable, detail}]`.

### 3.2 Gates

| gate_id | Passes when | Today |
|---|---|---|
| `data_weight_gate_passed` | every one of the four format-role cells has eligibility status other than `THRESHOLD_NOT_VALIDATED` in `phase4_frozen_choices.json` | fails (all four `THRESHOLD_NOT_VALIDATED`) |
| `methodology_validated` | `config/phase5_methodology_status_v1.json` has `validated: true` and non-blank `validated_by`, `validated_date`, `evidence_path`; an `validated: true` without those three is read as false | fails (`validated:false`) |
| `strict_classification_available` | applicable only when the request uses uncapped or verified filters or presets; passes when `strict_uncapped_enabled` | applicable only for those requests; fails |
| `min_eligible_pool` | eligible rows after all filters are at least `min_public_pool` (provisional 10) | evaluated per request |
| `date_verification` | (i) no match in the TRAIN/VALIDATION windows has class `DATE_CONFLICT` or `boundary_adjacent` with a non-consistent class, and (ii) every match of the TEST set designated for the validation evidence is `official_verified` (the set in the methodology status file, default `PRIMARY_RESTRICTED`) | fails (0 official rows; 42 unverified) |

Intended consequence of part (ii): `PRIMARY_RESTRICTED` admits matches that are only cross-source consistent, but the gate demands full official verification of the designated set, so the gate cannot pass until every match in that set has a valid official row. This is deliberate: consistency is evidence, not verification, and the gate stays conservative. `PUBLIC_ALLOWED` only if every applicable gate passes. Fail closed: a missing, unreadable or malformed input marks that gate failed with detail `INPUT_UNAVAILABLE`. Nothing in the code path sets `methodology_validated`; only a human edit of the config can. The gate-input override (`create_app(gate_inputs=...)`) exists as a function argument only, never an environment variable or request field, so production cannot inject it; tests use it for synthetic all-pass and single-fail fixtures.

### 3.3 Routes

- Internal (token required): `/api/v1/internal/...` mounts rankings, uncapped rankings, selection/presets/compose, profiles, compare, and the Phase 5 filter/ranking endpoints. Responses carry `publication_status` and `gate_results`. Token check reuses `require_admin` (header `X-Admin-Token`; 401 wrong or missing token, 503 when no token is configured). `require_internal` is a thin alias.
- Public ranking/selection/compare/profile paths from Phase 4 (`/rankings/*`, `/selection/*`, `/compare`, `/players/{id}/profile`): HTTP 403, envelope code `PUBLICATION_GATE_NOT_SATISFIED`, `details = {publication_status, gate_results}`, no player rows. When all gates pass (future only), the same handlers return rows with `PUBLIC_ALLOWED`.
- Public and descriptive: `/players`, `/players/{id}` (no scores, but flags), `/meta/capabilities`, `/meta/publication-gates`, `/meta/classification-coverage`.
Each gate is enforced in the service layer (single function `apply_gates(response, request_needs)`), not in individual routes, so a new route cannot forget it; a test enumerates all registered routes and fails if a route returning rows lacks the status fields.

## 4. Dynamic ranking engine

### 4.1 Layers

1. Analytics layer, run once per model version: baseline and residuals under `p4_baseline_b0_train_frozen_v1` for the carried definition, stored as sufficient statistics (4.2); no per-filter model exists anywhere.
2. Classification/filter layer: nationality, status, role, experience, format, phase, situation (4.4).
3. Ranking layer: apply filters, recompute context statistics, eligibility, shrinkage, uncertainty (4.3, 4.5).

Model versions: `model_version = "p5_context_v1_train"` (TRAIN-fitted baseline, thresholds, context variances; scores computed on TRAIN+VALIDATION rows, VALIDATION out-of-sample as in Phase 4). VALIDATION rows never affect any fitted parameter of this version (baseline, thresholds, `tau2`, `k`, targets); they only receive scores. The refit (6.4) is a separate version.

### 4.2 Stored component rows (`p5_context_stats`)

One row per (`player_id`, `match_id`, `comp`, `role`, `stream`, `period`, `phase`, `situation`) holding `n` (pressure deliveries), `s` (sum of residual), `s2` (sum of squared residual) for pressure rows of `any|q0.75` (thresholds TRAIN only from `phase4_frozen_choices.json`; reproduced and asserted equal before use). `phase` from `innings_phase` (`powerplay|middle|death`), `situation` from `innings_number` (`chase` = 2, `first_innings` = 1). `period` is TRAIN or VALIDATION only; TEST rows are excluded in SQL (`p4_match_period.period <> 'TEST'`) before the frame exists. Residual is the observed minus B0-expected value on the delivery; bowler residual keeps its natural sign and the score is negated for display (higher is better), as in `views.py`. Because `n, s, s2` are additive, any context is a sum over rows (phase ALL and situation ALL are sums over all labels); this identity is unit tested (sum of phases equals overall).

Alternative definitions (`chase|q0.9`, `any|q0.9`, `chase|q0.75`) get their own stat sets (`p5_context_stats_alt_<id>`) built by the same function, used only by sensitivity/stability scripts, never by the API.

### 4.3 Context re-aggregation and shrinkage

Atomic context = (`comp` in IPL/T20I, `role`, `phase` in ALL/powerplay/middle/death, `situation` in ALL/chase/first_innings): 2 x 2 x 4 x 3 = 48 cells. For each:
1. `context_cell(...)` builds the `engine.Cell` equivalent from the summed rows (match-level `n, s, s2`, so `shrink.match_stats`/`player_table` run unchanged).
2. Between-player variance `tau2` is estimated by `shrink.fit_cell` on TRAIN rows of that context only. No VALIDATION or TEST row enters the fit (test: perturbing VALIDATION rows leaves the fit unchanged; perturbing TRAIN rows changes it).
3. Floor/fallback (documented, never borrowed from the parent): if TRAIN players with at least one pressure match in the context is below `min_train_players_for_fit` (config, provisional 8), or `sigma2` is not finite, the context is `CONTEXT_NOT_ESTIMABLE` and has no scores. If `tau2 <= tau2_floor` (0.01 per `pressure_eligibility_rules_v1`), `k_for` applies its floor behaviour (maximum shrinkage; `k = sigma2 / (0.01 * sigma2) = 100`, i.e. scores are pulled almost entirely to the target) and the row carries `fit_floor_hit=true`. Rows from floor-hit contexts are still ranked but every row says so; their reliability is about zero by construction.
4. Shrunk score per player from `shrink.estimate` with the frozen choice `shrink_tau4`, producing raw, expected, residual, shrunk, `k`, target, `n`, matches, Kish `n_eff`.

The per-context scores are precomputed for all 48 atomic cells in the build script (`p5_context_scores`), so the request path does no model fitting. That is a cache of one estimator applied to stored rows, not a per-filter model; a test asserts `fit_cell` is called once per atomic context at build time and never from the request path.

### 4.4 Filter specification (`FilterSpec`, Pydantic v2, `extra="forbid"`)

| Field | Type / values | Required | Default | Validation / failure |
|---|---|---|---|---|
| `role` | `batter`, `bowler` | yes | none | 422 |
| `format` | `IPL`, `T20I`, `COMBINED_w70_30` | no | `COMBINED_w70_30` | 422 on other values. Combined requires eligibility in both formats in the context, else reason `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS` |
| `nationality` | `Indian`, `Overseas`, `Unknown`, null | no | null | 422 |
| `status` | `CAPPED_ANY`, `VERIFIED_CAPPED`, `DERIVED_CAPPED`, `VERIFIED_UNCAPPED`, `UNKNOWN_STATUS`, null | no | null | `VERIFIED_UNCAPPED` returns `STRICT_UNCAPPED_DISABLED` while disabled |
| `phase` | `ALL`, `powerplay`, `middle`, `death` | no | `ALL` | 422 |
| `situation` | `ALL`, `chase`, `first_innings` | no | `ALL` | 422 |
| `min_matches` | integer 0..200 | no | 0 | career `matches_played` from `p4_player_stats` (experience filter; that table is per player and format and excludes TEST). For `format=COMBINED_w70_30` the value is the sum across IPL and T20I, pre-test only; for a single-format request it is that format's value only |
| `min_context_matches` | integer 0..200 | no | 0 | pressure matches in the context |
| `include_unknown_nationality`, `include_unknown_status` | bool | no | false | see 4.6 |
| `limit` | integer 1..50 | no | 10 | 422 outside range |
| `offset` | integer 0..10000 | no | 0 | 422 |
| `sort` | `rank`, `score`, `name`, `matches`, `n`, `n_eff` | no | `rank` | whitelist; 422 otherwise |
| `order` | `asc`, `desc` | no | `asc` for rank/name, `desc` otherwise | 422 |

Wickets-remaining bands are not supported in v1 (catalog shows them disabled with the observed fragment sizes from the coverage run). There is no free-text, SQL, path or column-name parameter anywhere. All filters are ANDed. All-rounder is not a role: a player appears in the batter list and the bowler list independently, each from actual participation. `canonical_json(spec)` sorts keys and normalises defaults (so omitted and explicit-default specs hash equally); pagination and sort fields are excluded from the ranking hash and included in the page hash (`spec_hash` = SHA-256 of canonical JSON of the ranking-defining fields).

### 4.5 Ranking procedure and eligibility

1. `validate_combination(spec, capability)`: strict-uncapped check first (return `STRICT_UNCAPPED_DISABLED`, no rows).
2. Look up the atomic context table(s) for (comp(s), role, phase, situation). If the context is `CONTEXT_NOT_ESTIMABLE` the result is empty with that reason.
3. Context eligibility. For each atomic context `context_eligibility.py` runs the same derivation as Phase 4 (`candidate_thresholds` from the ladders in `pressure_eligibility_rules_v1.json`, `evaluate_cell`, `decide`, `analysis_rule`, `window_ratio`) on that context's cell with the same period usage Phase 4 used (thresholds from TRAIN distribution; VALIDATION only for the window ratio as Phase 4 does; no TEST). Outcomes per context: `ELIGIBLE_WORKING_POOL_NOT_VALIDATED` with its derived ball threshold, `INSUFFICIENT_SAMPLE_FOR_CONTEXT` (no threshold reaches the pool minimum), `CONTEXT_NOT_ESTIMABLE`, `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT`. Thresholds are never borrowed from the overall cell. A player eligible overall but below the context threshold gets `INSUFFICIENT_SAMPLE_FOR_CONTEXT` for that context. Because 48 contexts are each derived separately, the multiple-derivation caveat is printed in the architecture report: these thresholds are data-derived, not validated.
4. Pool: eligible players in the context, then classification filters (4.6), `min_matches`, `min_context_matches`; each removal is counted with a reason code.
5. Pool-size rule: pool below `min_internal_pool` (provisional 5) gives empty rows with `POOL_TOO_SMALL`; pool of 5 to 9 gives fewer than 10 rows, reasons list `FEWER_THAN_LIST_SIZE`. Slots are never filled (no padding, no borrowing from a wider context).
6. Uncertainty: seeded match-cluster bootstrap. For each atomic context, draws come from `engine.global_weights(match_ids_of_context, n_boot=1000, seed=20260512)` over that context's matches (sorted, so the draw matrix is deterministic and independent of the filter); the estimator is re-run per draw on weighted `n, s, s2` (`engine.draws`) with TRAIN-fitted `k`, target and tau2 held fixed (no refitting inside the bootstrap, which keeps the interval about sampling noise and is stated as such). Draws are restricted to the filtered pool per request and ranks are computed within the pool per draw (`engine.rank_summary`), giving the score interval, rank interval and Top-10 inclusion probability for that pool. These pool-relative statistics differ from the overall-pool statistics by design. For `COMBINED_w70_30`, IPL and T20I draws (disjoint match sets, independent clusters) are combined per draw index with weights 0.7/0.3 via `scoring.combine_formats`.
7. Ordering: score descending (bowler score is negated residual-based, higher better), ties broken by `player_id` ascending; the sort whitelist is applied after this canonical order for display only, and rank values always come from the canonical order. Pagination slices the canonical list; `total` is the pool size.
8. Response and per-row explanation: `rank`, `player_id`, `name`, raw, expected, residual, shrunk score, 90% interval, rank interval, `top10_inclusion_probability`, `n`, matches, `n_eff`, `k`, `fit_floor_hit`, eligibility status and threshold, restrictions applied (`data_quality_restrictions_v1` ids), classification fields with verification labels, `definition_id` `any|q0.75` with label `PROVISIONAL`, baseline/shrinkage versions, `model_version`, `data_version`, filter echo (canonical spec), config hashes, `publication_status`, `gate_results`, and result-level `reasons[]` with `{code, count, detail}` and `excluded_counts`.

Reason codes: `INSUFFICIENT_SAMPLE_FOR_CONTEXT`, `POOL_TOO_SMALL`, `STRICT_UNCAPPED_DISABLED`, `CLASSIFICATION_UNKNOWN_EXCLUDED`, `CONTEXT_NOT_ESTIMABLE`, `NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT`, `FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS`, `FEWER_THAN_LIST_SIZE`, `CLASS_EMPTY` (a valid class such as `VERIFIED_CAPPED` that has no scored player today).

### 4.6 Unknown-classification toggles

A value on a selected axis is matched exactly; an unknown player never matches `Indian`, `Overseas`, `CAPPED_ANY`, `DERIVED_CAPPED` or `VERIFIED_CAPPED`. When `nationality` is set, `include_unknown_nationality=false` (default) excludes players with unknown nationality and reports their count (`CLASSIFICATION_UNKNOWN_EXCLUDED`); `true` adds them to the pool flagged `classification_match = UNKNOWN_INCLUDED` and never calls them Indian. The same applies to `status` and `include_unknown_status`. Unknown values on an axis with no filter never exclude anyone. `nationality=Unknown` and `status=UNKNOWN_STATUS` are explicit ways to list those groups. Excluded counts are returned on every response, including empty ones.

### 4.7 Cache

In-memory dictionary, key = SHA-256 of (`spec_hash`, `data_version`, `model_version`, `gate_version`). `data_version` = SHA-256 over the content hashes of the `p5_context_*` and classification tables, the config file hashes used, and `code_version()`. Cached value is the full unsliced ranking for the pool; pagination is applied after retrieval. Bounded size (config 256 entries, least recently used eviction). Any version change invalidates all entries (`invalidate_if_version_changed`). Hit/miss counters are exposed on the internal catalog endpoint. A test asserts cached equals freshly computed output and that the cache stores no gate result older than the current `gate_version` (gates are recomputed on read because they are cheap and can change independently).

### 4.8 Endpoints (all under `/api/v1/internal`, token required)

- `GET /filters/catalog`: valid values per filter, enabled/disabled with reason, capability flag, wickets bands disabled, cache counters.
- `POST /rankings/context-preview`: for a `FilterSpec`, number of qualifying players and exclusion counts by reason, before ranking; no rows.
- `POST /rankings/dynamic`: ranking with pagination and explanations.
- `GET /rankings/coverage`: paginated precomputed coverage table (`p5_context_coverage`).
- Public stubs for the same capabilities answer 403 `PUBLICATION_GATE_NOT_SATISFIED`.

Coverage table: all combinations of format (3), role (2), nationality (null, Indian, Overseas, Unknown), status (null, CAPPED_ANY, VERIFIED_CAPPED, DERIVED_CAPPED, UNKNOWN_STATUS; `VERIFIED_UNCAPPED` listed as `DISABLED`), phase (4), situation (3), each with default toggles and with both toggles true. Columns: spec hash, player counts per stage (eligible in context, after classification, after min filters), final pool, reasons, `meets_internal_min`, `meets_public_min`. Counts are measured, not estimated; the engine's own `rank` is run to produce them so the table and the endpoint cannot disagree.

### 4.9 Error model

| Failure | Class | Caller receives | Logged |
|---|---|---|---|
| invalid filter value, unknown field, bad range | recoverable, client | 422 envelope `VALIDATION_ERROR` with field paths | no |
| missing or wrong token | client | 401 `UNAUTHORIZED`; 503 `ADMIN_TOKEN_NOT_CONFIGURED` | WARNING (no token value) |
| strict uncapped requested | policy | 200 `STRICT_UNCAPPED_DISABLED` (internal) | INFO |
| public route with rows | policy | 403 `PUBLICATION_GATE_NOT_SATISFIED`, failing gates, no rows | INFO |
| empty or short pool | normal result | 200, `rows` shorter or empty, `reasons[]` | no |
| p5 table missing/stale version | fatal for request | 503 `STORE_UNAVAILABLE` (existing handler) | ERROR |
| bootstrap or fit raises (numeric) | fatal for that context | 500 `INTERNAL_ERROR`, no partial rows | ERROR with spec hash |
| classification config invalid on reload | fatal for reload | previous table retained; 500 on the reload call | ERROR |

## 5. Investigations (Chunk 3)

All use pre-test rows only; everything is descriptive and labelled. Outputs are tables plus JSON/CSV plus the three reports. Where the data cannot support an estimate the value is the string `NOT_ESTIMABLE`.

1. **Variance decomposition** per (format, role, stream, definition): between-player variance `tau2` from the Phase 4 moment estimator (`shrink.fit_cell`) and a cross-check by REML computed with a numpy Fisher-scoring loop (500 iterations max, tolerance 1e-8, non-convergence recorded), mean within-player noise `sigma2/n_eff`, signal-to-noise `tau2 / mean(sigma2/n_eff)`, `ICC = tau2 / (tau2 + mean(sigma2/n_eff))`. If `tau2 <= 0` the status is `BETWEEN_VARIANCE_NOT_POSITIVE`. The pair of estimators separates "no detectable between-player spread" from "moment estimator artifact". A seeded match-cluster bootstrap (1000 draws) gives intervals for `tau2`, SNR and ICC.
2. **Detectability simulation (parametric, labelled)**: with the observed per-player `n_eff` and `sigma2`, simulate players with true `tau2` in a grid and report the share of replications where the estimator is positive and the split-half reliability exceeds 0.3. This states whether the current samples could have detected a spread at all.
3. **Split-half reliability**: modes `odd_even` (by the player's chronological match index), `early_late` (first and second half of the player's matches), and `random` (200 seeded random splits of the player's matches, mean reported). Players need at least `min_balls_per_half` (config, provisional 6) in each half. Correlation (Pearson and Spearman) of half means, Spearman-Brown corrected `2r/(1+r)`. Early/late mixes noise with real form change, so it is a lower bound; this caveat is printed. Bootstrap by match gives intervals. A separate reliability within bins of pressure opportunities (balls bins from the ladders) shows how reliability changes with sample size.
4. **Required sample projection** (`DESCRIPTIVE_PROJECTION`): `n_eff* = R/(1-R) * sigma2/tau2` for R in 0.5, 0.7, 0.8. If `tau2 <= 0`, `NOT_ESTIMABLE`. A second, labelled bound uses the bootstrap 90th percentile of `tau2` ("at least this many even under an optimistic tau2"). Compared with the observed `n_eff` distribution (median, P90). Never turned into an eligibility threshold.
5. **Bowler-specific signals** (SENSITIVITY_ONLY): three candidates written to `config/phase5_investigation_v1.json` before any run: (i) fielding-side defence margin (the batting side's required run gap or projected surplus, taken from the same pre-delivery state columns, TRAIN quantile at q0.75), (ii) death-phase with close gap, (iii) batting-side wickets-in-hand at or below a TRAIN-quantile bin. Only pre-delivery columns that exist in `exp_pre_delivery_state` and are not outcome-prefixed are allowed; a candidate whose columns do not exist is reported `CANDIDATE_NOT_BUILDABLE`. Thresholds from TRAIN only. They go through the same residual and shrinkage pipeline for the bowler cells and are compared on `tau2`, ICC, split-half. They never replace the primary definition and never feed the API. Four signals (primary plus three) are reported with no selection on the result.
6. **Multi-format pooling**: for players present in both IPL and T20I in the same role, pooled (match-weighted, baselines stay per-competition) versus single-format split-half reliability and SNR; descriptive; the number of such players per role is reported first (small counts mean `NOT_ESTIMABLE`).
7. **Sensitivity grid** (Chunk 3, no TEST outcomes): one-at-a-time around the primary for: definition (`any|q0.75`, `chase|q0.9`, `any|q0.9`, `chase|q0.75`), q grid from the rule file, shrinkage (the 7 `shrink.CONFIGS`), baseline alternatives (`phase4.sensitivity.baseline_alternatives`), format weights (8 configs, `format_weights_v1.json`, same final eligibility rules, independent of the definition axis). A full factorial would multiply to thousands of runs for no extra interpretation, so one extra cross is run: definition (4) x shrinkage (7) = 28. The working-pool ball thresholds (20/16/49/29) are fixed for every run; because alternative definitions have different pressure ball counts, each run reports its resulting pool size. Metrics against the primary: Top-10 overlap, Spearman on common eligible players, Kendall tau, pool size. Date-restricted TEST sensitivity is reported only as set composition and counts (TEST stays closed; the report says so).
8. **Ranking stability**: for the overall cell and for each atomic context with at least 5 eligible players: bootstrap Top-10 inclusion probabilities, rank intervals, expected overlap between two independent bootstrap Top 10s, Spearman between draws; also across the four definitions. Never padded. The report states: if SNR stays at or below zero, rankings are fragile in every context, and filters do not fix that.

Correctness cross-checks (spot checks, independent code): split-half of one cell by plain numpy loops; ICC on simulated data with known `tau2, sigma2`; Phase 4 scores reproduced to 1e-9 by `reproduce_phase4_scores` before any investigation runs (fatal if not).

## 6. Lock and refit

### 6.1 Pre-lock checklist (`pre_lock_checklist()`), run by `phase5_lock.py`

Automated items (each `PASS`/`FAIL` with evidence path): Phase 5 investigation, sensitivity, stability reports exist and are non-empty; `phase5_unresolved_issues.md` exists; date-verification table and TEST manifest exist and their hashes match; classification migration table exists and the capability is recorded; gates evaluated and written; `phase4_lock_log.json` hash equals `86f5ce9d...`; `phase5_lock_log.json` has no OPEN; Phase 4 report and `p4_*` table hashes equal their recorded values; official-data snapshot unchanged; `reproduce_phase4_scores` passes. Human items (`USER_APPROVAL_PENDING`, never auto-passed): methodology and thresholds accepted for the experimental refit; shrinkage choice; restriction register; feature/stream choices; primary TEST set rule. The lock script refuses without `--confirm-lock` and refuses if any automated item fails. A passed checklist is recorded as a pre-condition for an experimental refit and does not set `methodology_validated`.

### 6.2 Manifest (`phase5_methodology_lock.json`, label `EXPERIMENTAL_LOCK`)

Contents: SHA-256 of each of `phase4_split_v1.json`, `data_quality_restrictions_v1.json`, `pressure_rules_v1.json`, `pressure_eligibility_rules_v1.json`, `eligibility_rules_v1.json`, `format_weights_v1.json`, `phase5_*` configs; definition `any|q0.75` with thresholds and the three alternatives; working-pool ball thresholds 20/16/49/29 and their `THRESHOLD_NOT_VALIDATED` status; shrinkage `shrink_tau4`; stream and feature list; classification version and capability; TEST-set manifest hash; list of locked code files (explicit list of modules in `app/phase4` and `app/phase5` that affect scoring, each with SHA-256) plus `code_version()` for reference. Not hashed: reports, scripts, wall-clock values. `manifest_hash` = SHA-256 of canonical JSON of the above. `verify_lock()` recomputes every item; any difference raises `LockDriftError` (fatal, names the drifted items). The lock locks choices for an experimental run; it validates nothing.

### 6.3 Refit (`run_refit`, `p5_refit_trainval_v1`)

Refuses (`RefitRefusedError`, fatal, no tables) if the lock file is missing, `verify_lock()` fails, or `phase5_lock_log.json` contains an event. Procedure: `load_pre_test_state` (SQL excludes TEST) -> copy with VALIDATION rows relabelled `TRAIN` and original label kept in `period_orig` -> assert `period_orig` has no `TEST` and the set of periods is `{TRAIN}` -> unchanged Phase 4 `prepare_frame`, `fit_baseline_set`, `fit_thresholds`, `fit_cell` -> score all four cells with the locked definition and locked ball thresholds -> comparison with the Phase 4 TRAIN-only scores (Top-10 overlap, Spearman, mean absolute change per cell). Outputs only `p5_refit_trainval_v1_*` tables. `p4_*` tables and Phase 4 reports are never written (hash before/after). Deterministic: two runs give equal content hashes.

### 6.4 What the refit does not provide

All rows are in the fit window, so there is no out-of-sample evidence: leave-player-out baselines reduce but do not remove in-sample influence; comparison to Phase 4 is a stability statement only. Context tables can be rebuilt under `p5_refit_trainval_v1_context_*` using the same functions (the engine takes a `model_version` and table prefix); the API serves only `p5_context_v1_train` in v1. Reports and responses label refit outputs `EXPERIMENTAL_REFIT_NOT_OUT_OF_SAMPLE`.

## 7. Invariants and the layer that owns each

| Invariant | Owner | Why there |
|---|---|---|
| three capped values stay separate; no inference | `classification_v2` (data layer) | single builder; every reader goes through `p5_player_classification` |
| override rows are validated | `classification_v2.validate_overrides_v2` called by repository on every load | a route cannot bypass it |
| strict uncapped disabled | service layer `uncapped_guard()` before any score read | one choke point for ranking, presets, selection, dynamic |
| original dates unchanged | `date_verification` has no write API; script hashes before/after | defence plus detection |
| TEST untouched | `data.load_pre_test_state` (SQL filter), `lockguard`, orchestrator log hash check | filter prevents loading; hash check detects violation |
| context variance TRAIN only | `context_eligibility`/`ranking_engine` build step; frames pass through `drop_test_rows` and a TRAIN filter | fit is build-time, never request-time |
| no padding | `ranking_engine.rank` | the only function that produces rows |
| gating | `apply_gates` in the service layer plus route-enumeration test | cannot be forgotten per route |
| Cricsheet isolation | AST contamination test over scoring modules | structural, not by convention |
| official data preserved | orchestrator snapshot before/after (`integrity.assert_unchanged`) | existing mechanism |

## 8. Testability

Unit tests (pure, synthetic, no database): migration mapping and failures; override validation; capability; `classify` and every evidence evaluator; official CSV validation; gate evaluation (each gate failing alone, all passing); `FilterSpec` validation and `canonical_json`/hash stability; context re-aggregation sums; shrinkage floor/fallback; ranking AND semantics, role separation, exclusion counts, no padding, tie-breaks; cache key and invalidation; variance decomposition and split-half on simulated data with known components compared with an independent loop implementation; lock manifest hash and drift.
Integration tests (synthetic DuckDB store with TEST sentinel rows): TEST sentinels never reach any frame; refit refuses without a lock and leaves `p4_*` unchanged; HTTPX `TestClient` for catalog, preview, dynamic ranking, coverage, token protection, gate responses, strict-uncapped responses for every uncapped route and all 6 presets, route enumeration for gate fields.
Real-data tests (`realdata` marker, skipped when the store is absent): 655/562 recomputed from raw CSVs; the 42 ids and three classifications recomputed with the `csv` module; death + chase + Indian + DERIVED_CAPPED result read from the stored coverage table (no invented expectation); `reproduce_phase4_scores` equals stored scores to 1e-9; preservation hashes.
What cannot be unit tested: the substantive claims (whether tau2 is truly zero) are data findings, reported with intervals, not asserted.

## 9. Leakage and ambiguity log (checked while writing)

Leakage: (1) Cricsheet outcome fields excluded from identity matching (0.1 item 1). (2) Context tau2 TRAIN-only, even though scores use TRAIN+VALIDATION rows; context eligibility derivation uses VALIDATION only for the window ratio exactly as Phase 4 did. (3) Pressure thresholds TRAIN-only; context rows use the frozen `any|q0.75` thresholds, not re-derived from any wider window. (4) Pool-relative bootstrap ranks use the filtered pool but fixed (TRAIN) parameters, so filters cannot change fitted values. (5) Sensitivity runs compare to the primary using pre-test rows only; no TEST row exists in any frame. (6) Date-verification reads match-level timestamps and counts, never `out_*` columns. (7) The refit chooses nothing; all choices are fixed by the lock before it runs. Residual risk: Phase 4 aggregate TEST results were shown to the user, so the lock's choices could be influenced by them (open decision 1).
Ambiguities resolved: situation semantics (0.1 item 4); unknown toggles (4.6); gate `date_verification` meaning (3.2); combined-format eligibility; independence of timestamps and Cricsheet (assumed, flagged); the exact semantics of `VERIFIED_CAPPED` filter with 0 players (valid, `CLASS_EMPTY`).

## 10. Open decisions (residual, with the safest option chosen)

1. **Hold-out purity.** A later TEST evaluation is not pristine because Phase 4 aggregates were already reported. Chosen: keep the Phase 4 log as is, freeze sets in a manifest, require user approval. Needs the user's call on whether to accept the caveat or to hold out fresh data.
2. **Primary TEST strictness.** `PRIMARY_RESTRICTED` keeps early-2026 matches that are cross-source consistent; `STRICT_OFFICIAL_ONLY` (currently empty) is the user's literal reading. Chosen: report both; the user decides which is primary.
3. **Minimum pools**: internal 5, public 10 (provisional config values; no data basis).
4. **`min_verified_coverage` 0.95** to enable strict uncapped (provisional).
5. **`min_train_players_for_fit` 8** and `min_balls_per_half` 6 (provisional; sensitivity of the number of fitted contexts is reported).
6. **Independence of date sources** (timestamps and Cricsheet) is assumed; if both derive from one upstream, "consistent" is weaker than it looks. Reported as a caveat on every consistent row.
7. **Unknown toggles** (4.6) behaviour on unfiltered axes; alternative is to exclude unknowns from any classification-filtered list.
8. **Shrinkage choice** `shrink_tau4` was chosen on VALIDATION in Phase 4; the refit keeps it and reports sensitivity rather than re-choosing.
9. **Context derivation multiplicity**: 48 context thresholds are each data-derived; none validated.
10. **Refit context tables** are buildable but not served in v1.
11. **Phase 4 test updates** are unavoidable for the label migration and public-route gating; each is listed in the verification file and the test count must not decrease below the Phase 4 baseline of 509 tests (stated explicitly in the verification file).
12. **TEST non-outcome identifiers are read for set counts** (match ids, striker and bowler ids, delivery counts; never `out_`, `den_`, `post_innings_` columns or results). This does not open TEST outcomes, but the user said TEST stays untouched. Chosen: keep, because the manifest needs counts. Alternative: drop the distinct-player count per set and keep only match ids and delivery counts. User's call.
13. **Date-source independence evidence.** The report gives control-group disagreement rates for (a) and (e); if either is high or they co-vary, `PRIMARY_RESTRICTED` should be dropped in favour of `STRICT_OFFICIAL_ONLY`.

## 11. Responses to design review (second pass, verdict APPROVED, 0 HIGH)

1. MEDIUM, TEST non-outcome identifiers: addressed by open decision 12, with the option to drop the distinct-player count.
2. MEDIUM, `min_matches` source: addressed in the 4.4 table (sum of IPL and T20I pre-test for combined; per-format otherwise).
3. MEDIUM, date-source independence: addressed in 2.2 row (e) (control-group disagreement rates reported for a and e) and open decision 13.
4. MEDIUM, gate (ii) cannot pass for `PRIMARY_RESTRICTED` without full official coverage: stated as intended in 3.2.
5. NIT, Cricsheet column whitelist: addressed in 2.3 with a test.
6. NIT, 4.1 wording: VALIDATION rows never affect fitted parameters, now stated.
7. NIT, 509 baseline: stated in open decision 11.
The unverified build-time risk (that `candidate_thresholds`, `evaluate_cell` and `decide` run unchanged on a 48-context cell) is kept as a first task of the context-eligibility chunk; if they need changes, the change is a wrapper, not an edit to Phase 4 code.
