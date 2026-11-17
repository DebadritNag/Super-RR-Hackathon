"""Phase 8 criteria hash, run-order enforcement and the append-only run log (temp directories)."""

from __future__ import annotations

import copy
import json

import pandas as pd
import pytest

from app.phase8 import criteria as cr
from app.phase8 import store
from app.phase8.constants import CRITERIA_FILE, CRITERIA_HASH_FILE, PHASE8_DB
from app.services.pressure_service import StoreError


@pytest.fixture()
def env(tmp_path):
    return {
        "criteria_path": tmp_path / "criteria.json",
        "hash_path": tmp_path / "hash.json",
        "store_path": tmp_path / "x.duckdb",
    }


def _write(env, **kw):
    return cr.write_criteria(env["criteria_path"], env["hash_path"], env["store_path"], **kw)


def _verify(env):
    return cr.verify_criteria(env["criteria_path"], env["hash_path"], env["store_path"])


def test_write_then_verify_and_log_row_one(env):
    info = _write(env)
    assert info["seq"] == 1 and not info["already_written"]
    assert _verify(env)["sha256"] == info["sha256"]
    log = store.read_run_log(env["store_path"])
    assert list(log["seq"]) == [1] and log.iloc[0]["step"] == "plan"
    rec = json.loads(env["hash_path"].read_text("utf-8"))
    assert rec["sha256"] == info["sha256"] and len(rec["sha256"]) == 64
    assert len(rec["git_blob_sha"]) == 40


def test_write_is_idempotent(env):
    _write(env)
    again = _write(env)
    assert again["already_written"] is True
    assert list(store.read_run_log(env["store_path"])["seq"]) == [1]


def test_changed_file_makes_every_step_fail(env):
    _write(env)
    env["criteria_path"].write_text('{"edited": true}\n', encoding="utf-8")
    with pytest.raises(cr.CriteriaError):
        _verify(env)
    with pytest.raises(cr.CriteriaError):
        cr.begin_step("intensity", **env)
    assert list(store.read_run_log(env["store_path"])["seq"]) == [1]


def test_refuses_to_rewrite_different_criteria(env):
    _write(env)
    other = copy.deepcopy(cr.CRITERIA)
    other["eligibility"]["min_matches"] = 1
    with pytest.raises(cr.CriteriaError):
        _write(env, criteria=other)


def test_no_step_runs_before_the_plan_row(env):
    with pytest.raises(cr.CriteriaError):
        _verify(env)
    with pytest.raises(cr.CriteriaError):
        cr.begin_step("data", **env)


def test_missing_hash_file_fails(env):
    _write(env)
    env["hash_path"].unlink()
    with pytest.raises(cr.CriteriaError):
        _verify(env)


def test_begin_step_appends_rows_with_increasing_seq(env):
    _write(env)
    a = cr.begin_step("data", **env)
    b = cr.begin_step("intensity", **env)
    assert (a["seq"], b["seq"]) == (2, 3)
    log = store.read_run_log(env["store_path"])
    assert list(log["step"]) == ["plan", "data", "intensity"]
    assert set(log["criteria_sha256"]) == {a["sha256"]}


def test_results_cannot_be_written_before_the_plan(env):
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(StoreError):
        store.write_p8_table(df, "p8_x", env["store_path"])
    _write(env)
    store.write_p8_table(df, "p8_x", env["store_path"])


def test_result_tables_carry_the_criteria_hash_and_run_seq(env):
    info = _write(env)
    store.write_p8_table(pd.DataFrame({"a": [1]}), "p8_x", env["store_path"])
    import duckdb

    con = duckdb.connect(str(env["store_path"]), read_only=True)
    row = con.execute("SELECT criteria_sha256, run_seq FROM p8_x").fetchone()
    con.close()
    assert row == (info["sha256"], 1)


def test_store_refuses_bad_names_and_protected_databases(env, tmp_path):
    _write(env)
    df = pd.DataFrame({"a": [1]})
    for bad in ("p6_x", "x", "p8_run_log", "p8_X;drop"):
        with pytest.raises(StoreError):
            store.write_p8_table(df, bad, env["store_path"])
    from app.phase8.constants import EXPLORATORY_DB, OFFICIAL_DB

    for prot in (EXPLORATORY_DB, OFFICIAL_DB):
        with pytest.raises(StoreError):
            store.append_run_log("x", "h", store_path=prot)


def test_forbidden_inputs_are_rejected():
    bad = copy.deepcopy(cr.CRITERIA)
    bad["approach_selection"]["inputs"] = ["player_id", "split_half_sb_lower_bound"]
    assert cr.forbidden_hits(bad) == ["player_id"]
    bad2 = copy.deepcopy(cr.CRITERIA)
    bad2["combination"]["inputs"] = ["cricsheet_totals"]
    assert "cricsheet" in cr.forbidden_hits(bad2)
    bad3 = copy.deepcopy(cr.CRITERIA)
    bad3["sources"] = "Cricsheet totals"
    assert "cricsheet" in cr.forbidden_hits(bad3)
    assert cr.forbidden_hits(cr.CRITERIA) == []


def test_write_criteria_refuses_forbidden_content(env):
    bad = copy.deepcopy(cr.CRITERIA)
    bad["approach_selection"]["inputs"] = ["player rank"]
    with pytest.raises(cr.CriteriaError):
        _write(env, criteria=bad)
    assert not env["criteria_path"].exists()


def test_declared_files_are_intact_and_logged_first():
    """The real criteria file matches its hash file and the run log (written before results)."""
    info = cr.verify_criteria(CRITERIA_FILE, CRITERIA_HASH_FILE, PHASE8_DB)
    assert len(info["sha256"]) == 64
    crit = cr.load_criteria()
    assert crit["declared_before_any_result"] is True
    assert cr.criteria_bytes(crit) == CRITERIA_FILE.read_bytes()
    log = store.read_run_log(PHASE8_DB)
    assert log.iloc[0]["step"] == "plan"
    assert (log["ts"].iloc[1:] >= log["ts"].iloc[0]).all()


def test_real_result_tables_follow_the_plan_row():
    """Every stored p8 result table is stamped with the declared hash and a later run_seq."""
    import duckdb

    sha = store.read_run_log(PHASE8_DB).iloc[0]["criteria_sha256"]
    con = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        names = [
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name LIKE 'p8_%' AND table_name <> 'p8_run_log'"
            ).fetchall()
        ]
        for t in names:
            d = con.execute(f"SELECT DISTINCT criteria_sha256, run_seq FROM {t}").df()
            assert set(d["criteria_sha256"]) == {sha}, t
            assert (d["run_seq"] >= 2).all(), t
    finally:
        con.close()
