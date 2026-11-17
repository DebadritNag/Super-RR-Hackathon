# Chunk 1 review: temporal split, strictly-prior par, phase boundaries

Chunk 1 adds a date-rule chronological split with a test-period lock, strictly prior first-innings par, and phase-boundary reporting. The evidence file is complete, and a narrow spot-check passed (53 chunk-1 tests). No official data was modified: the `superr.duckdb` SHA-256 equals `phase4_hash_before.txt`.

**Verdict**: APPROVED

Watch for (all non-blocking):
- The lock is a convention-level guard, not a security boundary (likely, stated in the module docstring).
- `LockedFrame` guards only a fixed set of access paths (confirmed in `split.py`). Outcome columns are identified by the prefixes `out_`, `den_`, `post_innings_` and by "residual" in the name.
- Phase labels for DLS-shortened innings cannot be tied to the time the revision was announced.

## High-level view

The split is a pure function of `match_date` (TRAIN <= 2024-12-31, VALIDATION 2025, TEST >= 2026-01-01). Boundaries are fixed in config before any evaluation, and deliveries follow their match. The real data supports a population-level split in every format and period. Player-level tests are mostly insufficient for VALIDATION and TEST, and the coder reports this instead of inventing a split.

Strictly prior par uses a `searchsorted(side="left")` on dates. This excludes same-date matches, including the earlier game of a double-header. Fewer than 30 prior innings gives NULL plus the flag `par_unavailable_insufficient_prior`, with no zero-fill and no cross-format fallback. The coder cross-checked it against raw CSVs for three T20I matches by a different code path, and the values matched. The unavailable rows (7,692) all fall in TRAIN, so VALIDATION and TEST are fully covered.

Leave-one-match-out par is quarantined behind `LeakageGuard`, which rejects columns containing `_lomo`, the descriptive label, or `full_sample`. Phase boundaries wrap the existing `phase_engine` without changing it. Shortened innings (50 regulation innings, 3,404 deliveries) are all DLS-excluded, and no resources are imputed.

<details>
<summary>Issues (3)</summary>

1. **Lock bypass via unguarded access** (possible) — `LockedFrame` guards `__getitem__`, `values`, `to_numpy`, `to_frame`, `__iter__` and `sum`. The reviewer did not check other paths such as `len`-based inference. Later chunks should keep test outcomes only inside `LockedFrame` and not copy them elsewhere. Not blocking.
2. **Outcome-column detection by prefix** (likely) — `test_state` retains any column that does not match `out_`, `den_`, `post_innings_` or contain "residual". A later chunk that adds outcome-derived columns with other names would leak them into `test_state`. Extend the prefix list or add a test when new columns are created.
3. **Revision timing** (confirmed, documented) — the data has no announcement time, so a revised-limit label may use later information. This is harmless while all shortened innings stay excluded from primary scoring. Keep that exclusion in place.

</details>

<details>
<summary>Details</summary>

### Strictly prior par and the same-day rule

`strictly_prior_par` builds per-format cumulative source-innings sums sorted by date. For each innings-1 row it takes `k`, the count of source matches dated strictly before the match date, and divides the cumulative runs at ball B by `k`. Par is NULL when `k < min_prior`. The coder checked that it equals the existing `par_runs_prior` column on all 200,999 rows, with an identical NULL pattern. The sensitivity counts for `min_prior` of 15, 30 and 60 are reported, which is honest about how much early data is lost.

### Honesty and data preservation

The verification file states limitations plainly: the approximate counts in plan section 3 are superseded, and the stale "48" note in `pressure_rules_v1.json` is reconciled in a report and not edited. The repository is not under git, so no commit exists. The reviewer's hash comparison of `superr.duckdb` matches. The store layer refuses the official DB and writes only `p4_` tables to `exploratory.duckdb`.

### Not verified by the reviewer

The full 362-test suite and Ruff were not re-run, per instructions. They rest on the coder's evidence.

</details>

## File map

<details>
<summary>Files</summary>

- `app/phase4/split.py`: split, integrity check, rolling folds, test lock
- `app/phase4/par.py`: strictly prior par, descriptive-only leave-one-match-out par, leakage guard
- `app/phase4/phases.py`: boundary table, shortened-innings and label checks
- `config/phase4_split_v1.json`: fixed split boundaries
- `tests/test_phase4_*.py`: 53 new tests
</details>
