# Phase 9 owner decisions

Date: 2026-11-18. Recorded before any Phase 9 result was produced.

## D1. 2026 data are genuine; TEST lock released

Owner statement (verbatim from the request): "all the 2026 datas are genuiene so if not add them and
train with them".

- **Owner attestation.** The owner attests that all 2026 matches, including the 42 late-dated T20I
  matches (dated after 2026-05-31), are genuine and must be added and used for training and scoring.
  This is an OWNER ATTESTATION. It is not an official third-party verification. The Phase 5
  cross-source check found 36 of the 42 late-dated matches consistent across sources and 6 with a
  single source; no conflict was found (0 of 42). The original match dates are unchanged.
- **Scope.** All 144 2026 matches in scope (IPL 74, T20I 70, 2026-01-07 to 2026-11-01) with their
  deliveries are included. Every existing data-quality restriction still applies (innings 3 and 4
  and Super Over exclusions with reason codes, unreconstructable DLS rows, extras `other` and
  `Penalty`, wicket-flag anomalies, OTHER_T20 out of scope).
- **TEST lock released.** The Phase 4 lock (`TestLock`) has no release operation, and its log
  (`phase4_lock_log.json`: FREEZE, OPEN, CLOSE) and the Phase 5 log are protected evidence that is
  not edited. The release is recorded as a `RELEASE` event with reason `owner decision phase 9` in
  the separate append-only file `phase9_lock_release_log.json`, which also stores the SHA-256 of the
  earlier lock logs, of the frozen choices and of the criteria file.
- **No pristine hold-out remains.** From this release on there is no untouched evaluation period.
  Every Phase 9 report states this. The 2026 out-of-time check is a check on data that was held out
  before, not an independent test; nothing was tuned on it.

## D2. Remove the word "EXPLORATORY" from every frontend page

Presentation decision. The word and the ranking-status banners and pills are removed from the user
interface. The replacement is not VALIDATED or PROVISIONAL: those labels appear only if the
predeclared criteria (`config/phase8_selection_criteria_v1.json`, SHA-256
`9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`) are met. The status fields in the
data files and reports keep whatever label the evidence earns.

## What did not change

Criteria file, thresholds, floors, shrinkage, weights, definitions, hyperparameter choices (taken
from the Phase 8 model artefacts), the seed (20260512), the fold rule (`match_id % 5`), the
intensity-selection procedure and the status-label rule.