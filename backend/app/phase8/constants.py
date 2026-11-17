"""Phase 8 constants: paths, seeds, table prefix, status text and fixed data rules."""

from __future__ import annotations

from pathlib import Path

from app.core.config import BACKEND_ROOT
from app.phase4.constants import SPLIT_CONFIG  # noqa: F401  (re-exported: the Phase 4 split)

STATUS = "EXPERIMENTAL_NOT_VALIDATED"
TABLE_PREFIX = "p8_"
SEED = 20260512
SCOPE = ("IPL", "T20I")
PRE_TEST_PERIODS = ("TRAIN", "VALIDATION")
N_FOLDS = 5

CONFIG_DIR = BACKEND_ROOT / "config"
REPORTS_DIR = BACKEND_ROOT / "data" / "reports"
DB_DIR = BACKEND_ROOT / "data" / "database"
OFFICIAL_DB = DB_DIR / "superr.duckdb"
EXPLORATORY_DB = DB_DIR / "exploratory.duckdb"
PHASE8_DB = DB_DIR / "phase8.duckdb"
MODELS_DIR = BACKEND_ROOT / "data" / "models"

CRITERIA_FILE = CONFIG_DIR / "phase8_selection_criteria_v1.json"
CRITERIA_HASH_FILE = REPORTS_DIR / "phase8_selection_criteria_hash.json"
PREHASH_FILE = Path("d:/Data/.agents/tasks/phase8_prehash.json")

# Restricted innings (rule RULE_INNINGS_3_4): confirmed Super Over and unverified innings 3/4.
RESTRICTED_MATCH_IDS = (34429, 45512, 50359, 40725, 48027, 48029)
REGULATION_INNINGS = (1, 2)
LATE_DATE_TABLE = "p5_t20i_date_verification"
PERIOD_TABLE = "p4_match_period"
PAR_TABLE = "p4_par_prior"
STATE_TABLE = "exp_pre_delivery_state"

# Outcome-side column prefixes: label-only, never features.
LABEL_PREFIXES = ("out_", "den_", "post_innings_")
