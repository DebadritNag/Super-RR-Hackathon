"""Retention data never reaches scoring, ranking, eligibility, classification or public routes."""

from __future__ import annotations

import re

from app.core.config import BACKEND_ROOT

APP = BACKEND_ROOT / "app"
ALLOWED = {
    APP / "data_pipeline" / "retention_importer.py",
    APP / "data_pipeline" / "retention_availability.py",
    APP / "api" / "v1" / "routes_retention.py",
    APP / "main.py",
}
NEEDLE = re.compile(r"retention_importer|retention_availability|p7_retention|routes_retention")


def test_only_the_retention_modules_reference_retention_data():
    hits = [
        str(p.relative_to(APP))
        for p in sorted(APP.rglob("*.py"))
        if p not in ALLOWED and NEEDLE.search(p.read_text(encoding="utf-8"))
    ]
    assert hits == []


def test_main_only_registers_the_internal_retention_router():
    t = (APP / "main.py").read_text(encoding="utf-8")
    assert "routes_retention.internal" in t
    assert "routes_retention.public" not in t


def test_no_script_other_than_the_retention_scripts_uses_retention_tables():
    # rr_analysis.py reads retention only for the descriptive availability split of squad-gap
    # candidates (never for scoring, ranking or eligibility); it is allow-listed deliberately.
    allowed = {"import_retention_list.py", "run_retention_procedure.py", "rr_analysis.py"}
    for p in (BACKEND_ROOT / "scripts").glob("*.py"):
        if p.name not in allowed:
            assert not NEEDLE.search(p.read_text(encoding="utf-8")), p.name
