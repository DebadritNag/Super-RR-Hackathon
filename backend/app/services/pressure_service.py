"""Build the exploratory pre-delivery state store (EXPLORATORY, separate from the official DB).

The official DuckDB is opened read-only by `app.analytics.pressure_engine.load_inputs`. State goes
to a different file (`data/database/exploratory.duckdb`, table `exp_pre_delivery_state`) and the
build manifest is written next to the Phase 2.5 reports. Writing to the official file is refused.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.analytics import pressure_engine as pe
from app.analytics.integrity import assert_unchanged, sha256_file, snapshot_from_settings
from app.analytics.reporting import code_version
from app.core.config import BACKEND_ROOT, Settings, get_settings
from app.utils.jsonio import write_json

EXPLORATORY_DB = BACKEND_ROOT / "data" / "database" / "exploratory.duckdb"
STATE_TABLE = "exp_pre_delivery_state"
MANIFEST_TABLE = "exp_pre_delivery_state_manifest"
MANIFEST_NAME = "pre_delivery_state_manifest.json"
SUPER_OVER_REPORT = "cricsheet_super_over_validation.json"
DQ_REPORT = "data_quality_impact_report.json"


class StoreError(RuntimeError):
    pass


def engine_code_hash() -> str:
    h = hashlib.sha256()
    for name in ("pressure_engine.py", "cricket_calculations.py", "phase_engine.py"):
        h.update((BACKEND_ROOT / "app" / "analytics" / name).read_bytes())
    return h.hexdigest()


def read_phase25_masks(reports_dir: Path, rules: dict[str, Any]) -> dict[str, Any]:
    """Read row masks from Phase 2.5 REPORTS (never from Cricsheet files)."""
    so = json.loads((reports_dir / SUPER_OVER_REPORT).read_text(encoding="utf-8"))
    cls = {int(m["match_id"]): m.get("classification") or m.get("verdict") for m in so["matches"]}
    confirmed_report = sorted(k for k, v in cls.items() if v == "CONFIRMED_SUPER_OVER")
    cfg = rules["restricted_innings"]["reason_codes"]
    if confirmed_report != sorted(cfg["CONFIRMED_SUPER_OVER_BY_CRICSHEET"]):
        raise StoreError(
            f"config and Phase 2.5 report disagree on confirmed matches: {confirmed_report}"
        )
    dq = json.loads((reports_dir / DQ_REPORT).read_text(encoding="utf-8"))
    pairs = {
        (int(r["match_id"]), int(r["innings"]))
        for r in dq["issue_register"]["cricsheet_total_disagreements"]
    }
    return {
        "confirmed_report": confirmed_report,
        "cricsheet_total_innings": pairs,
        "classification": cls,
    }


SUPER_OVER_REPORT = SUPER_OVER_REPORT


def build_state(
    settings: Settings | None = None, db_path: Path | None = None
) -> tuple[pd.DataFrame, dict]:
    s = settings or get_settings()
    db_path = Path(db_path or s.duckdb_path)
    rules = pe.load_rules()
    masks = read_phase25_masks(s.phase25_reports_dir, rules)
    deliveries, matches = pe.load_inputs(db_path)
    state = pe.compute_pre_delivery_state(
        deliveries, matches, rules, cricsheet_total_innings=masks["cricsheet_total_innings"]
    )
    return state, {
        "rules": rules,
        "masks": masks,
        "matches": matches,
        "deliveries_rows": len(deliveries),
    }


def write_store(state: pd.DataFrame, manifest: dict, store_path: Path, official_db: Path) -> None:
    store_path, official_db = Path(store_path).resolve(), Path(official_db).resolve()
    if store_path == official_db:
        raise StoreError("the exploratory store must not be the official database")
    store_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(store_path))
    try:
        con.register("state_df", state)
        con.execute(f"CREATE OR REPLACE TABLE {STATE_TABLE} AS SELECT * FROM state_df")
        con.unregister("state_df")
        con.execute(f"CREATE OR REPLACE TABLE {MANIFEST_TABLE} (manifest_json VARCHAR)")
        con.execute(f"INSERT INTO {MANIFEST_TABLE} VALUES (?)", [json.dumps(manifest, default=str)])
    finally:
        con.close()


def build_and_store(
    settings: Settings | None = None,
    db_path: Path | None = None,
    store_path: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    s = settings or get_settings()
    db_path = Path(db_path or s.duckdb_path)
    store_path = Path(store_path or EXPLORATORY_DB)
    reports_dir = Path(reports_dir or s.phase25_reports_dir)
    before = snapshot_from_settings(s, db_path)
    state, aux = build_state(s, db_path)
    checks = pe.build_checks(state, aux["matches"])
    manifest = {
        **pe.STATUS_FIELDS,
        "artifact": STATE_TABLE,
        "state_version": aux["rules"]["state_version"],
        "config_version": aux["rules"]["config_version"],
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_version": {"engine_sha256": engine_code_hash(), "analytics_validation_sha256": code_version()},
        "inputs": {
            "official_db": db_path.as_posix(),
            "official_db_sha256": before["db_file_sha256"],
            "official_tables_content_hash": {
                k: before["tables"].get(k) for k in ("deliveries", "matches", "competitions")
            },
            "pressure_rules_sha256": sha256_file(pe.RULES_PATH),
            "restrictions_sha256": sha256_file(BACKEND_ROOT / "config" / "data_quality_restrictions_v1.json"),
            "phase25_masks_read_from": [SUPER_OVER_REPORT, DQ_REPORT],
            "phase25_masks_sha256": {
                n: sha256_file(Path(reports_dir) / n) for n in (SUPER_OVER_REPORT, DQ_REPORT)
            },
            "cricsheet_files_opened": 0,
        },
        "store": {"path": store_path.as_posix(), "table": STATE_TABLE, "columns": list(state.columns)},
        "restriction_rules_applied_as_masks": ["RULE_INNINGS_3_4"],
        "restriction_masks_carried_as_flags": ["RULE_CRICSHEET_TOTALS", "RULE_DISMISSED_NO_FLAG", "RULE_WICKET_NO_DISMISSED", "RULE_EXTRAS_OTHER", "RULE_EXTRAS_PENALTY", "RULE_DLS_TARGETS"],
        "checks": checks,
        "scope_note": "State columns only. Par, expectation and rank columns (spec sections 4 and 6) are built in a later chunk.",
    }  # fmt: skip
    write_store(state, manifest, store_path, db_path)
    after = snapshot_from_settings(s, db_path)
    diff = assert_unchanged(before, after)
    manifest["preservation"] = {"official_data_unchanged": not diff, "differences": diff}
    write_json(reports_dir / MANIFEST_NAME, manifest)
    con = duckdb.connect(str(store_path))
    try:
        con.execute(
            f"UPDATE {MANIFEST_TABLE} SET manifest_json = ?", [json.dumps(manifest, default=str)]
        )
    finally:
        con.close()
    return manifest
