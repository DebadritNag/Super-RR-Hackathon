# Phase 6 final decisions (OD-1 to OD-3 and carried-forward items)

Source read: `backend/data/reports/phase6_unresolved_issues.md`. In that file the ids appear as `P6-1 (OD-1)`, `P6-2 (OD-2)` and `P6-3 (OD-3)`. Other "OD-n" labels in `backend/docs/phase6_design.md` (OD-6, OD-9, OD-10) are design-time notes with different meanings and are not these items.

No new methodological or publication decision was made. Each outcome below applies an owner decision (D1 to D5) from the Phase 7 brief or the standing constraints (TEST is never used to tune; protected files are not modified).

## OD-1 (P6-1): primary window is pre-test only

- Exact issue: the full verified history available is TRAIN + VALIDATION (723 matches, 2022-01-22 to 2025-12-19). TEST outcomes are outside the primary window. The report asks the owner to confirm, or supply a new hold-out (see OD-3).
- Current state: open in the Phase 6 file. The figures were rechecked in Phase 7: `p4_match_period` holds TRAIN 512, VALIDATION 211, TEST 144 (read-only query).
- Category: methodology.
- Blocks submission: no.
- Outcome: **CONFIRMED as is, by existing owner constraints.** TEST is not used for tuning (standing rule). The 42 late T20I dates stay unverified and excluded (D5). No new hold-out has been supplied.
- Owner input needed: none. Default if the owner disagrees: none before 18 Nov 2026.

## OD-2 (P6-2): recent-form thresholds are provisional

- Exact issue: the 2024-onward and 2025-onward windows scale the four frozen ball thresholds with `ceil(t x window balls / TRAIN balls)`. They are not validated, each window is fitted in-sample, and 2025-onward has no TRAIN rows. The report asks whether a window should get frozen thresholds of its own.
- Current state: open. Recomputed in Phase 7 from `phase6_recent_form_analyses_2024.csv` and `_2025.csv`: best marginal data weight 0.065 (2024-onward) and 0.038 (2025-onward), so neither window approaches the 0.5 gate.
- Category: methodology.
- Blocks submission: no.
- Outcome: **No window receives its own frozen thresholds.** Recent-form stays an in-sample, descriptive robustness analysis labelled provisional and is never used for a published ranking. D1 and D2 forbid changing methodology or gates to make a gate pass.
- Owner input needed: none.

## OD-3 (P6-3): no clean hold-out exists

- Exact issue: all Phase 6 reliability figures are in-sample diagnostics on TRAIN + VALIDATION. Season consistency is robustness, not validation. TEST was opened once in Phase 4 (lock log: FREEZE, OPEN, CLOSE) and is not pristine.
- Current state: open. This is a standing limitation, and one of the reasons no Top 10 pressure list is published.
- Category: methodology and publication.
- Blocks submission: no. It is the stated reason a pressure ranking is not claimed (D3).
- Outcome: **Recorded as a standing limitation.** No fresh data can be collected before 18 Nov 2026, and D3 removes the ranking claim, so no hold-out is needed for the submission.
- Question for the owner (only if they want to change this): "Do you want fresh matches collected as a hold-out after the submission?" Recommended default: **no new hold-out before 18 Nov 2026; revisit after the season data is complete.**

## Other items: mapping to owner decisions

| Id | Item | Status in Phase 7 | Basis |
|---|---|---|---|
| P5-1 | Strict uncapped selection disabled (no authoritative cap source with player ids) | Carried forward unchanged, still pending input | D5 item 2 |
| P5-2 | 42 late T20I dates unverified | Carried forward; stay excluded; never inferred | D5 item 1 |
| P5-3 | Data-weight gate fails in 48 of 48 contexts | Approved: gate stays 0.5, shrinkage kept, 0.56 option unadopted | D1, D2 |
| P5-4 | Methodology validation (`validated=false`) | Carried forward unchanged | D3 |
| P5-5 | Between-player variance sits at the floor in 48 of 48 contexts | Approved: shrinkage kept; documented | D1 |
| P5-6 | Ranking instability | Carried forward unchanged; reason a Top 10 is not published | D3 |
| P5-7 | Primary TEST-set strictness | Carried forward unchanged; non-blocking (no TEST evaluation planned) | Standing rule |
| P5-8 | TEST is not a pristine hold-out | Carried forward unchanged | Standing rule |
| P5-9 | Minimum pool sizes 5 and 10 provisional | Carried forward unchanged; lists are never padded | D2 |
| P5-10 | Refit has no hold-out | Carried forward unchanged; non-blocking | D3 |
| P6-4 | Public `/players` is descriptive-only | Confirmed by code, tests and live probe (see `phase6_final_audit.md`) | D4 |
| P6-5 | Retention list pending | Carried forward; importer and availability analysis handled in later chunks, nothing invented | D5 item 3 |
| P6-6 | Low reliability (pooled 0.37, median 0.25) | Settled: contexts stay restricted, uncertainty displayed, no short lists presented as rankings | D2 |

## Pending official inputs (not filled)

1. Official verification of the 42 late T20I match dates.
2. An authoritative cap-status source with stable player ids.
3. The official IPL retention list (expected 17 Nov 2026).

None of these has been invented, inferred or filled.

## Owner questions

None blocks the submission. The only optional question is the OD-3 hold-out question above, with the recommended default.
