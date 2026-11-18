"""Loader for the experimental statistical-model outputs (internal use only).
Returns an explicit state instead of raising: ``INSUFFICIENT_DATA`` when the generated files are
missing, ``LOCKED`` when the stored integrity evidence no longer matches (a changed output file
or a changed TEST lock log), ``AVAILABLE`` otherwise. Nothing is written and every call builds
new objects, so a caller cannot change a later response.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.phase4.constants import REPORTS_DIR
from app.phase5.lockguard import file_sha256
from app.phase7 import ai_pipeline as ap

AVAILABLE = "AVAILABLE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
LOCKED = "LOCKED"


def _empty(state: str, reason: str) -> dict[str, Any]:
    return {
        "state": state,
        "reason": reason,
        "banner": ap.BANNER,
        "model_label": ap.MODEL_LABEL,
        "registry": None,
        "roles": {},
    }


def load_ai_outputs(reports: Path | str | None = None) -> dict[str, Any]:
    base = Path(reports) if reports else REPORTS_DIR
    reg_path = base / ap.REGISTRY_NAME
    if not reg_path.exists():
        return _empty(
            INSUFFICIENT_DATA, f"{ap.REGISTRY_NAME} not found; run scripts/phase7_ai_pipeline.py"
        )
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _empty(INSUFFICIENT_DATA, f"registry unreadable: {exc}")
    lock_path = base / "phase4_lock_log.json"
    if not lock_path.exists():
        return _empty(LOCKED, "phase4_lock_log.json is missing; the TEST lock cannot be verified")
    expected = (reg.get("lock_after") or {}).get("phase4_lock_log_sha256")
    if expected != file_sha256(lock_path) or not reg.get("lock_unchanged", False):
        return _empty(LOCKED, "the TEST lock log differs from the one recorded at run time")
    roles: dict[str, Any] = {}
    for role, name in ap.CSV_NAMES.items():
        p = base / name
        if not p.exists():
            return _empty(INSUFFICIENT_DATA, f"{name} not found; run scripts/phase7_ai_pipeline.py")
        if (reg.get("outputs") or {}).get(name) != file_sha256(p):
            return _empty(LOCKED, f"{name} differs from the hash recorded in the registry")
        df = pd.read_csv(p)
        df = df.astype(object).where(df.notna(), None)
        roles[role] = {
            "rows": df.to_dict(orient="records"),
            "rows_written": int(len(df)),
            "short_list": bool(len(df) < ap.TOP_N),
        }
    state = AVAILABLE if all(r["rows_written"] > 0 for r in roles.values()) else INSUFFICIENT_DATA
    out = _empty(state, "" if state == AVAILABLE else "no player meets the technical input rule")
    out["roles"] = roles
    out["registry"] = reg
    return out
