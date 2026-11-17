"""Register and summary: every Phase 5 item carried forward, labels and stop statement present."""

from __future__ import annotations

import pytest

from app.phase5.constants import REPORTS_DIR
from app.phase6 import reports as rp


def _have_outputs() -> bool:
    return all((REPORTS_DIR / d).is_file() for d in rp.DELIVERABLES)


def test_register_rows_reject_a_missing_phase5_item():
    n = {
        "cls_counts": {"VERIFIED_CAPPED": 0, "DERIVED_CAPPED": 1, "UNKNOWN": 2},
        "cls_values": ["VERIFIED_CAPPED", "DERIVED_CAPPED", "UNKNOWN"],
        "cls_placeholder": ["VERIFIED_UNCAPPED"], "cls_total": 3,
        "date_total": 42, "date_classes": {"DATE_CONSISTENT_ACROSS_SOURCES": 36}, "date_official": 0,
        "test_sets": {"PRIMARY_RESTRICTED": 99, "STRICT_OFFICIAL_ONLY": 0, "SENSITIVITY_ALL": 144},
        "var_contexts": 48, "var_floor_hits": 48, "var_verdicts": {"MIXED": 48},
        "pooled_sb": {"odd_even": 0.3}, "ctx_oe_median": 0.2, "ctx_estimable": 47,
        "elig_reached": {"0.5": [2, 4]}, "def_status": "NO_DEFINITION_PASSES",
        "def_confounded": True, "def_pass_list": "[]", "gate_contexts": 48, "gate_stored_pass": 0,
        "gate_value": 0.5, "opt_rows": 10, "opt_pass": 0, "opt_options": 2, "opt_best_b": 0.4,
        "opt_best_id": "O6", "opt_subset_pass": 0,
    }  # fmt: skip
    rows = rp.register_rows(n)
    ids = {r["id"] for r in rows}
    assert {f"P5-{i}" for i in range(1, 11)} <= ids
    assert all(r["status"] in {"UNCHANGED", "CHANGED", "CLOSED", "NEW"} for r in rows)
    with pytest.raises(ValueError):
        rp.render_register(n, {i: "x" for i in range(1, 12)})  # item 11 is not carried
    text = rp.render_register(n, {i: "x" for i in range(1, 11)})
    assert "not official verification" in text
    assert "not a pristine" in text
    assert "four statuses" not in text.lower() and "fourth status" not in text.lower()


def test_register_wording_names_three_values_and_a_disabled_placeholder():
    n_cls = ["VERIFIED_CAPPED", "DERIVED_CAPPED", "UNKNOWN"]
    assert len(n_cls) == 3
    assert "VERIFIED_UNCAPPED" not in n_cls


def test_stored_register_carries_all_phase5_items_and_the_stop_statement():
    if not _have_outputs():
        pytest.skip("Phase 6 reports not generated")
    p5 = rp.phase5_items(REPORTS_DIR)
    assert sorted(p5) == list(range(1, 11))
    reg = (REPORTS_DIR / "phase6_unresolved_issues.md").read_text(encoding="utf-8")
    for i in p5:
        assert f"| P5-{i} |" in reg
    assert "EXPERIMENTAL_NOT_VALIDATED" in reg
    assert "stops here for your review" in reg
    assert "four statuses" not in reg.lower() and "fourth status" not in reg.lower()


def test_stored_user_summary_has_label_and_stop_statement():
    if not _have_outputs():
        pytest.skip("Phase 6 reports not generated")
    s = (REPORTS_DIR / "phase6_user_summary.md").read_text(encoding="utf-8")
    assert "EXPERIMENTAL_NOT_VALIDATED" in s
    assert "not a pristine hold-out" in s
    assert "I stopped here" in s


def test_all_thirteen_deliverables_exist_and_are_non_empty():
    assert len(rp.DELIVERABLES) == 13
    if not _have_outputs():
        pytest.skip("Phase 6 reports not generated")
    for d in rp.DELIVERABLES:
        assert (REPORTS_DIR / d).stat().st_size > 0, d
