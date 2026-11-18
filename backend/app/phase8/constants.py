"""Phase 8 constants: paths, seeds, table prefix, status text and fixed data rules."""

from __future__ import annotations

import os
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


# ---------------------------------------------------------------------------------------------
# Phase 9 switch. Phase 8 behaviour is the default; ``SUPERR_PHASE=phase9`` redirects the store,
# table prefix, caches and protected-file manifest. Nothing else in Phase 8 changes.
# ---------------------------------------------------------------------------------------------
PHASE9_DB = DB_DIR / "phase9.duckdb"
PHASE9_PREHASH_FILE = Path("d:/Data/.agents/tasks/phase9_prehash.json")
TASKS_DIR = Path("d:/Data/.agents/tasks")


def is_phase9() -> bool:
    return os.environ.get("SUPERR_PHASE", "") == "phase9"


def active_prefix() -> str:
    return "p9_" if is_phase9() else TABLE_PREFIX


def active_db() -> Path:
    return PHASE9_DB if is_phase9() else PHASE8_DB


def active_prehash() -> Path:
    return PHASE9_PREHASH_FILE if is_phase9() else PREHASH_FILE


def translate_table(name: str) -> str:
    """Map a ``p8_`` table name to the active prefix (identity in Phase 8)."""
    if is_phase9() and name.startswith(TABLE_PREFIX):
        return "p9_" + name[len(TABLE_PREFIX) :]
    return name


def cache_dir(name: str) -> Path:
    """Scratch cache directory (``_p8c2_cache`` becomes ``_p9c2_cache`` in Phase 9)."""
    return TASKS_DIR / (name.replace("_p8", "_p9", 1) if is_phase9() else name)
