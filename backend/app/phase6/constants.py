"""Phase 6 constants: status label, table prefix, seed and file locations."""

from __future__ import annotations

from app.phase5.constants import CONFIG_DIR, REPORTS_DIR

STATUS = "EXPERIMENTAL_NOT_VALIDATED"
TABLE_PREFIX = "p6_"
SEED = 20260512
PROVISIONAL_DEFINITION = "any|q0.75"
INVESTIGATION_CONFIG = CONFIG_DIR / "phase6_investigation_v1.json"
CRITERIA_FILE = CONFIG_DIR / "phase6_selection_criteria_v1.json"
CRITERIA_HASH_FILE = REPORTS_DIR / "phase6_selection_criteria_hash.json"
PLAN_REPORT = REPORTS_DIR / "phase6_investigation_plan.md"
IN_SAMPLE_LABEL = "IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION"
