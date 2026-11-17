"""Recent-form windows: 2024/2025 filters are correct, nested and kept apart from primary outputs."""

from __future__ import annotations

import ast
import re

import numpy as np
import pandas as pd
import pytest

from app.core.config import BACKEND_ROOT
from app.phase5.constants import REPORTS_DIR
from app.phase6 import recent_form as rf
from app.phase6.lockguard import LockGuardError

SCRIPT = BACKEND_ROOT / "scripts" / "phase6_recent_form.py"
MODULE = BACKEND_ROOT / "app" / "phase6" / "recent_form.py"
PRIMARY_TABLES = {"p6_variance_estimators", "p6_split_half", "p6_definition_reliability"}


def _frame() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2022-03-01", "2023-12-31", "2024-01-01", "2024-06-15", "2024-12-31", "2025-01-01",
         "2025-07-04", "2025-12-19"]
    )  # fmt: skip
    return pd.DataFrame({"match_id": np.arange(8), "match_date": dates,
                         "competition_type": ["IPL", "T20I"] * 4,
                         "period": ["TRAIN"] * 5 + ["VALIDATION"] * 3})  # fmt: skip


def test_2024_filter_keeps_only_rows_from_2024_01_01():
    w = rf.filter_window(_frame(), rf.WINDOWS["2024"])
    assert rf.WINDOWS["2024"] == "2024-01-01"
    assert list(w["match_id"]) == [2, 3, 4, 5, 6, 7]
    assert (w["match_date"] >= pd.Timestamp("2024-01-01")).all()
    assert pd.Timestamp("2023-12-31") not in set(w["match_date"])


def test_2025_filter_keeps_only_rows_from_2025_01_01_and_boundary_is_inclusive():
    w = rf.filter_window(_frame(), rf.WINDOWS["2025"])
    assert rf.WINDOWS["2025"] == "2025-01-01"
    assert list(w["match_id"]) == [5, 6, 7]
    assert w["match_date"].min() == pd.Timestamp("2025-01-01")


def test_windows_are_nested_and_distinct():
    d = _frame()
    a = set(rf.filter_window(d, rf.WINDOWS["2024"])["match_id"])
    b = set(rf.filter_window(d, rf.WINDOWS["2025"])["match_id"])
    assert b < a < set(d["match_id"])  # strict subsets
    assert rf.WINDOWS["2024"] != rf.WINDOWS["2025"]


def test_filter_ignores_time_of_day_and_does_not_mutate_input():
    d = _frame()
    d.loc[2, "match_date"] = pd.Timestamp("2024-01-01 23:59:00")
    before = d.copy()
    w = rf.filter_window(d, "2024-01-01")
    assert 2 in set(w["match_id"])
    pd.testing.assert_frame_equal(d, before)


def test_window_counts_refuses_a_test_period():
    d = _frame()
    d.loc[7, "period"] = "TEST"
    with pytest.raises(LockGuardError):
        rf.window_counts(d, "2025-01-01")


def test_window_counts_per_format():
    c = rf.window_counts(_frame(), "2025-01-01").set_index("format")
    assert int(c["matches"].sum()) == 3
    assert c.loc["T20I", "matches"] == 2 and c.loc["IPL", "matches"] == 1


def test_scaled_threshold_is_ceiling_never_below_one_and_none_stays_none():
    assert rf.scaled_threshold(20, 300.0, 1000.0) == 6
    assert rf.scaled_threshold(20, 1.0, 1000.0) == 1
    assert rf.scaled_threshold(None, 300.0, 1000.0) is None
    assert rf.scaled_threshold(20, 300.0, 0.0) is None
    # a window as large as TRAIN keeps the frozen threshold
    assert rf.scaled_threshold(20, 1000.0, 1000.0) == 20


def test_gate_is_read_not_redefined():
    from app.phase4 import eligibility as el

    assert rf.GATE == el.GATE_B == 0.5
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "GATE":
                    assert isinstance(node.value, ast.Attribute)  # el.GATE_B, not a literal


def test_labels_are_constants():
    assert rf.LABEL == "RECENT_FORM_SEPARATE_ANALYSIS"
    assert rf.FIT_ON == "WINDOW_IN_SAMPLE"


def test_script_writes_only_recent_form_tables_never_a_primary_table():
    text = SCRIPT.read_text(encoding="utf-8")
    written = set(re.findall(r'"(p6_[a-z0-9_]+)"', text)) | set(
        re.findall(r'f"(p6_[a-z_{}0-9]+)"', text)
    )
    assert written, "script names no table"
    for name in written - PRIMARY_TABLES:
        assert name.startswith(("p6_recent_form", "p6_")), name
    # primary tables appear only in the before/after guard, never as a write target
    for m in re.finditer(r"save_table\(([^)]*)\)", text):
        assert not any(t in m.group(1) for t in PRIMARY_TABLES)
    assert "write_p6_table" not in MODULE.read_text(encoding="utf-8")


def test_module_never_imports_a_loader_of_test_outcomes_or_cricsheet():
    src = MODULE.read_text(encoding="utf-8").lower()
    for bad in ("cricsheet", "test_eval", "load_test_match_outcomes", "evaluate_on_test"):
        assert bad not in src


# ---------------------------------------------------------------- stored outputs (real run)
def _stored(name: str) -> pd.DataFrame:
    p = REPORTS_DIR / name
    if not p.is_file():
        pytest.skip(f"{name} not present (run scripts/phase6_recent_form.py)")
    return pd.read_csv(p)


@pytest.mark.parametrize("key,start", [("2024", "2024-01-01"), ("2025", "2025-01-01")])
def test_stored_window_tables_are_labelled_and_separate(key, start):
    s = _stored(f"phase6_recent_form_analyses_{key}.csv")
    assert set(s["analysis_label"]) == {rf.LABEL}
    assert set(s["window_start"]) == {start}
    assert set(s["fit_on"]) == {rf.FIT_ON}
    assert len(s) == 8
    assert (s["definition"] == "any|q0.75").all()
    gated = s[s["status"] == "ESTIMATED"]
    assert (gated["gate"] == 0.5).all()
    assert not gated["passes_gate_informational"].astype(bool).any()  # no context passes 0.5


def test_stored_2025_sample_is_smaller_than_2024_in_every_cell():
    a, b = (
        _stored("phase6_recent_form_analyses_2024.csv"),
        _stored("phase6_recent_form_analyses_2025.csv"),
    )
    key = ["format", "role", "stream"]
    m = a.merge(b, on=key, suffixes=("_24", "_25"))
    assert len(m) == 8
    assert (m["matches_25"] < m["matches_24"]).all()
    assert (m["pressure_observations_25"] < m["pressure_observations_24"]).all()
    assert (b["share_rows_in_b0_fit_window"] == 0).all()  # 2025 has no TRAIN rows
    assert (a["share_rows_in_b0_fit_window"] > 0).all()


def test_stored_reliability_rows_carry_window_labels_and_no_player_column():
    r = _stored("phase6_recent_form_analyses_reliability.csv")
    assert set(r["window_start"]) == {"2024-01-01", "2025-01-01"}
    assert set(r["analysis_label"]) == {rf.LABEL}
    assert not [c for c in r.columns if "player_id" in c]


def test_stored_primary_analysis_is_not_overwritten_by_the_window_tables():
    # the combined file holds only window rows; no primary window value appears in it
    s = _stored("phase6_recent_form_analyses.csv")
    assert set(s["window_start"]) == {"2024-01-01", "2025-01-01"}
    assert "PRE_TEST" not in set(s.get("window", pd.Series(dtype=str)))
