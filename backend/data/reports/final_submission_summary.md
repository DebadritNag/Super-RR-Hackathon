# Final submission summary (Phase 9, data and models)

Generated 2026-11-18T13:31:34+00:00. Criteria SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`.

## Labels earned

- **Batters**: approach A, **EXPLORATORY**. split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.
- **Bowlers**: approach C, **EXPLORATORY**. split-half 0.32 below 0.5; split-half lower bound not above 0.

## Top 10

**Batters** (approach A): 1. Suryakumar Yadav; 2. Tim David; 3. Heinrich Klaasen; 4. David Miller; 5. Rinku Singh; 6. Andre Russell; 7. Romario Shepherd; 8. Tristan Stubbs; 9. Shreyas Iyer; 10. Shivam Dube.

**Bowlers** (approach C): 1. Sunil Narine; 2. Matheesha Pathirana; 3. Kuldeep Yadav; 4. Jasprit Bumrah; 5. Varun Chakravarthy; 6. Abrar Ahmed; 7. Rashid Khan; 8. Akeal Hosein; 9. Wanindu Hasaranga; 10. Mohammad Nawaz.

## Data and training

Window 2022-01-22 to 2026-11-01; 144 2026 matches in scope, 137 with scored deliveries; 40 of 42 late-dated T20I matches contribute. Models refitted on matches to 2025-12-31 with the Phase 8 hyperparameters; 2026 out-of-time check in `submission_methodology.md` section 6.1. No pristine hold-out remains (owner decision D1).

See `phase9_comparison.md` for the Phase 8 against Phase 9 comparison and `submission_readiness_audit.md` for open items.
