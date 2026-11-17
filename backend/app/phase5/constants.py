"""Phase 5 constants: status strings, versions, table prefix, config and report paths."""

from __future__ import annotations

from app.core.config import BACKEND_ROOT

STATUS = "EXPERIMENTAL_NOT_VALIDATED"
TABLE_PREFIX = "p5_"
SEED = 20260512
PROVISIONAL_DEFINITION = "any|q0.75"
SENSITIVITY_DEFINITIONS = ("chase|q0.9", "any|q0.9", "chase|q0.75")
CLASSIFICATION_V2_VERSION = "p5_classification_v2"

INTERNAL = "INTERNAL_EXPERIMENTAL_ONLY"
PUBLIC = "PUBLIC_ALLOWED"

CONFIG_DIR = BACKEND_ROOT / "config"
REPORTS_DIR = BACKEND_ROOT / "data" / "reports"
CLASSIFICATION_V2_CONFIG = CONFIG_DIR / "phase5_classification_v2.json"
SOURCE_MANIFEST = CONFIG_DIR / "classification_source_manifest_v1.json"
GATES_CONFIG = CONFIG_DIR / "phase5_gates_v1.json"
METHODOLOGY_STATUS = CONFIG_DIR / "phase5_methodology_status_v1.json"
FROZEN_CHOICES = REPORTS_DIR / "phase4_frozen_choices.json"
# Written by the date-verification chunk. Expected shape: {"gate": {"passed": bool, "detail": str}}.
DATE_SUMMARY = REPORTS_DIR / "phase5_t20i_date_verification.json"
