"""Phase 4 constants: versions, status strings, table prefix, paths."""

from __future__ import annotations

from app.core.config import BACKEND_ROOT

STATUS = "EXPERIMENTAL_NOT_VALIDATED"
OFFICIAL_RANKING = False
TABLE_PREFIX = "p4_"
LOCKED_TABLE_PREFIX = "p4_test_locked_"
SPLIT_VERSION = "phase4_split_v1"
SEED = 20260512
SCOPE = ("IPL", "T20I")
PERIODS = ("TRAIN", "VALIDATION", "TEST")

DESCRIPTIVE_LOMO_LABEL = "DESCRIPTIVE_ONLY_USES_FUTURE_MATCHES"
PAR_FLAG = "par_unavailable_insufficient_prior"

CONFIG_DIR = BACKEND_ROOT / "config"
REPORTS_DIR = BACKEND_ROOT / "data" / "reports"
SPLIT_CONFIG = CONFIG_DIR / "phase4_split_v1.json"
LOCK_LOG = REPORTS_DIR / "phase4_lock_log.json"
FROZEN_CHOICES = REPORTS_DIR / "phase4_frozen_choices.json"
