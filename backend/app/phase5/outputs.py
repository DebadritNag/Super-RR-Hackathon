"""Shared output helpers for the Phase 5 investigation scripts (tables, reports, preservation)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics.integrity import assert_unchanged, snapshot_from_settings
from app.analytics.reporting import write_json_deterministic
from app.core.config import get_settings
from app.phase5.constants import STATUS
from app.phase5.lockguard import (
    LOCK_LOG,
    PHASE5_LOCK_LOG,
    assert_phase5_lock_not_opened,
    file_sha256,
)
from app.phase5.store import write_p5_table


def sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """Make mixed-type object columns writable (strings win over numbers in one column)."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype != object:
            continue
        vals = out[c].dropna()
        if vals.empty:
            out[c] = out[c].astype("float64")
        elif all(isinstance(v, bool) for v in vals):
            continue
        elif not all(isinstance(v, str) for v in vals):
            out[c] = out[c].map(lambda v: v if v is None or v != v else str(v))
    return out


def save_table(
    df: pd.DataFrame, name: str, reports: Path, store: Path, table: str | None = None
) -> None:
    """CSV + deterministic JSON in the reports folder and, optionally, a p5_ table in the store."""
    reports.mkdir(parents=True, exist_ok=True)
    df = sanitize(df)
    df.to_csv(reports / f"{name}.csv", index=False)
    write_json_deterministic(
        reports / f"{name}.json",
        {
            "status": STATUS,
            "official_ranking": False,
            "records": json.loads(df.to_json(orient="records")),
        },
    )
    if table:
        write_p5_table(df, table, store)


def cols(df: pd.DataFrame, names: list[str]) -> list[str]:
    return [c for c in names if c in df.columns]


def rows_of(df: pd.DataFrame, names: list[str]) -> list[list[Any]]:
    c = cols(df, names)
    sub = df[c].astype(object).where(df[c].notna(), None)
    return [
        [v.replace("|", "\\|") if isinstance(v, str) else v for v in row]
        for row in sub.values.tolist()
    ]


class Preservation:
    """Before/after evidence that official data, Phase 4 reports and the TEST lock are untouched."""

    def __init__(self, reports: Path):
        self.reports = reports
        self.settings = get_settings()
        self.before = snapshot_from_settings(self.settings)
        self.p4_before = self._p4_hashes()
        self.lock_before = file_sha256(LOCK_LOG) if Path(LOCK_LOG).exists() else None

    def _p4_hashes(self) -> dict[str, str]:
        return {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.reports.glob("phase4_*"))
            if p.is_file()
        }

    def verify(self) -> dict[str, Any]:
        diff = assert_unchanged(self.before, snapshot_from_settings(self.settings))
        p4_after = self._p4_hashes()
        changed = sorted(k for k in self.p4_before if p4_after.get(k) != self.p4_before[k])
        lock_after = file_sha256(LOCK_LOG) if Path(LOCK_LOG).exists() else None
        p5_events = (
            assert_phase5_lock_not_opened(PHASE5_LOCK_LOG) if Path(PHASE5_LOCK_LOG).exists() else 0
        )
        ok = not diff and not changed and lock_after == self.lock_before
        return {
            "official_data_unchanged": not diff, "phase4_report_files_hashed": len(self.p4_before),
            "phase4_report_files_changed": changed, "phase4_lock_log_sha256_before": self.lock_before,
            "phase4_lock_log_sha256_after": lock_after, "phase5_lock_log_events": p5_events,
            "test_opened": False, "all_preserved": bool(ok),
        }  # fmt: skip


def failing_gates(reports: Path) -> dict[str, Any]:
    """Gate results from the Phase 5 publication-gate report (read-only)."""
    p = reports / "phase5_publication_gates.json"
    if not p.exists():
        return {
            "available": False,
            "note": "phase5_publication_gates.json not found; run scripts/phase5_gates.py",
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    scen = next(iter(data.get("scenarios", {}).values()), {})
    return {
        "available": True,
        "publication_status": scen.get("publication_status"),
        "failing": scen.get("failing_gates", []),
        "gate_results": scen.get("gate_results", []),
    }
