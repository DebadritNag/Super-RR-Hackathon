# Phase 5 Chunk 1 review: classification migration, strict-uncapped disabling, publication gating

Chunk 1 replaces the Phase 4 `Capped/Uncapped/Unknown` labels with four explicit values (VERIFIED_CAPPED, DERIVED_CAPPED, VERIFIED_UNCAPPED, UNKNOWN). It makes every strict-uncapped path return `STRICT_UNCAPPED_DISABLED`, and adds a single publication-gating function. Real-data counts are 655 DERIVED_CAPPED, 0 VERIFIED, 562 UNKNOWN, matching Phase 4 coverage and an independent recount. Watch for: public `/players` rows are not gated (confirmed, minor, descriptive only); gate thresholds 0.95 and 10 are provisional (confirmed, documented).

**Verdict**: APPROVED

## High-level view

Classification is a pure migration of Phase 4 labels through an explicit four-entry mapping. Any unmapped combination is fatal, and counts are asserted against the stored Phase 4 coverage. Nothing reads names, domestic records or IPL data.

Strict uncapped is controlled by a computed capability flag. It needs an authoritative id-keyed source in the manifest, at least one verified row, and verified coverage of at least 0.95 of the scored pool. All three fail today, so the flag is false. It fails closed on a missing or malformed manifest.

Gating is one pure function over file-derived inputs. A missing or malformed input fails its gate. `methodology_validated` can only be set by a human edit of a config file that also requires validator, date and evidence. Public rows routes raise `PUBLICATION_GATE_NOT_SATISFIED` with no rows. The `/internal` router requires the admin token.

Preservation holds. The `superr.duckdb` SHA-256 equals the pre-run hash (I re-hashed it: `CB4077EE...391D`). The overrides file is still header-only, and Phase 4 tables and reports were not overwritten.

<details>
<summary>Issues (3)</summary>

1. **Public `/players` and `/players/{id}` return descriptive rows ungated** (confirmed, minor). These are directory rows with classification labels, not rankings or scores. The brief's "no rows" requirement is about ranking, selection and score outputs. Decide in the final review whether the directory should also be gated.
2. **Provisional thresholds** (confirmed, informational). `min_verified_coverage` 0.95 and `min_public_pool` 10 are config values labelled provisional. They need human confirmation before any public release.
3. **Date gate depends on a Chunk 2 artifact** (confirmed). The gate reads `phase5_t20i_date_verification.json` key `gate`. It fails closed with `NOT_RUN` until Chunk 2 writes it. Chunk 2 must write exactly that shape.

</details>

<details>
<summary>Details</summary>

### Classification migration and override validation

`MIGRATION_MAP` has exactly four entries, and DERIVED_CAPPED keeps its own `derived_evidence` label. VERIFIED_CAPPED is reachable only through a source-verified base row or a validated override row. Override validation collects all row errors and requires a non-placeholder source, `verified_by` and an ISO `verified_date` that is not in the future. It rejects duplicates, unknown player ids and the legacy `Capped`/`Uncapped` values. It also rejects VERIFIED_UNCAPPED for a player with derived T20I evidence, which forces human resolution rather than silently overriding data-proven capped status. UNKNOWN is displayed as `UNKNOWN_STATUS` with the banner `NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED`.

### Strict-uncapped disabling

The `disabled()` body carries the reason, the source needed, the capability reasons and empty `rows`. The tests cover every uncapped ranking kind, every preset, composition constraints, the `include_uncapped` mode and the uncapped classification filters. They also show that requests selecting nothing uncapped still work, and that enabling goes through the validated reload (disabled, then enabled, then disabled). The preset catalog marks strict-dependent presets unavailable with `STRICT_UNCAPPED_DISABLED` and returns no player rows.

### Gating is real

`evaluate_gates` reads the frozen eligibility cell statuses (four cells currently `THRESHOLD_NOT_VALIDATED`), the methodology status file and the date summary. None is hard-coded to pass. `all_pass_gates()` exists only as a test fixture, injected through `create_app(gate_inputs=...)`, and is not the default. The same function backs the gates endpoint and the per-request gates, so the status cannot diverge between routes. Enforcement is in the service layer, so a route cannot bypass it.

### Test changes to Phase 4 tests

The modified Phase 4 tests change labels and inject synthetic all-pass gates so the Phase 4 logic keeps being exercised. Behaviour changes (uncapped now returns the disabled body) are asserted rather than loosened. 117 new tests were added, and the full suite is reported as 626 passed with ruff clean. I did not re-run the suites.

### Preservation

The `superr.duckdb` hash was re-checked and matches. The `exploratory.duckdb` hash differs from the pre-run value, which is expected because `p5_` tables were added. The evidence says no `p4_` table was written.

</details>

<details>
<summary>File map</summary>

New: `app/phase5/*`, `app/schemas/phase5.py`, `scripts/phase5_classification.py`, `scripts/phase5_gates.py`, four `config/*.json` files, three `tests/test_phase5_*.py` files, and the Phase 5 classification and gate reports. Modified: `app/phase4/{uncapped,selection,spotchecks}.py`, the repository, service, schemas, deps, errors, routes, main, the Phase 4 test helpers and tests, and the two docs.

</details>
