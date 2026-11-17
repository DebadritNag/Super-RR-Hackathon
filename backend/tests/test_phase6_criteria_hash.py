"""Criteria hash, run-order enforcement and the append-only run log (temporary directories)."""

from __future__ import annotations

import copy
import json
import shutil

import pytest

from app.phase6 import criteria as cr
from app.phase6 import store
from app.phase6.constants import CRITERIA_FILE, INVESTIGATION_CONFIG
from app.services.pressure_service import StoreError


@pytest.fixture()
def env(tmp_path):
    cfg = tmp_path / "cfg.json"
    shutil.copy(INVESTIGATION_CONFIG, cfg)
    return {
        "criteria_path": tmp_path / "criteria.json",
        "hash_path": tmp_path / "hash.json",
        "store_path": tmp_path / "x.duckdb",
        "config_path": cfg,
    }


def _write(env, **kw):
    return cr.write_criteria(
        env["criteria_path"], env["hash_path"], env["config_path"], env["store_path"], **kw
    )


def _verify(env):
    return cr.verify_criteria(env["criteria_path"], env["hash_path"], env["store_path"])


def test_write_then_verify_and_log_row_one(env):
    info = _write(env)
    assert info["seq"] == 1 and not info["already_written"]
    assert _verify(env)["sha256"] == info["sha256"]
    log = store.read_run_log(env["store_path"])
    assert list(log["seq"]) == [1] and log.iloc[0]["step"] == "plan"
    assert log.iloc[0]["criteria_sha256"] == info["sha256"]
    rec = json.loads(env["hash_path"].read_text("utf-8"))
    assert rec["sha256"] == info["sha256"] and len(rec["sha256"]) == 64
    assert len(rec["git_blob_sha"]) == 40


def test_write_is_idempotent_for_identical_content_and_refuses_changes(env):
    first = _write(env)
    again = _write(env)
    assert again["already_written"] and again["sha256"] == first["sha256"]
    assert len(store.read_run_log(env["store_path"])) == 1
    changed = copy.deepcopy(cr.CRITERIA)
    changed["rule"] = "something else"
    with pytest.raises(cr.CriteriaError):
        _write(env, criteria=changed)


def test_verify_raises_when_hash_file_or_criteria_missing(env):
    _write(env)
    env["hash_path"].unlink()
    with pytest.raises(cr.CriteriaError, match="hash file missing"):
        _verify(env)
    env["criteria_path"].unlink()
    with pytest.raises(cr.CriteriaError, match="missing"):
        _verify(env)


def test_verify_raises_when_criteria_edited_after_hash(env):
    _write(env)
    data = json.loads(env["criteria_path"].read_text("utf-8"))
    data["rule"] = "edited after the fact"
    env["criteria_path"].write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", "utf-8")
    with pytest.raises(cr.CriteriaError, match="changed"):
        _verify(env)
    with pytest.raises(cr.CriteriaError):
        cr.begin_step(
            "variance_floor", env["criteria_path"], env["hash_path"], env["config_path"],
            env["store_path"],
        )  # fmt: skip


def test_verify_raises_when_no_plan_row_was_logged_first(env):
    info = _write(env)
    env["store_path"].unlink()
    assert info["sha256"]
    with pytest.raises(cr.CriteriaError, match="seq 1"):
        _verify(env)


def test_begin_step_appends_rows_in_order(env):
    _write(env)
    a = cr.begin_step("variance_floor", env["criteria_path"], env["hash_path"],
                      env["config_path"], env["store_path"])  # fmt: skip
    b = cr.begin_step("split_half", env["criteria_path"], env["hash_path"],
                      env["config_path"], env["store_path"])  # fmt: skip
    assert (a["seq"], b["seq"]) == (2, 3)
    log = store.read_run_log(env["store_path"])
    assert list(log["step"]) == ["plan", "variance_floor", "split_half"]
    assert log["criteria_sha256"].nunique() == 1


def test_forbidden_words_rejected_outside_forbidden_inputs():
    assert cr.forbidden_hits(cr.CRITERIA) == []
    for word in cr.FORBIDDEN_WORDS:
        bad = copy.deepcopy(cr.CRITERIA)
        bad["rule"] = f"uses the {word} of someone"
        assert word in cr.forbidden_hits(bad)
    top = copy.deepcopy(cr.CRITERIA)
    top["rule"] = "Top-10 membership"
    assert "top10" in cr.forbidden_hits(top)


def test_forbidden_words_block_writing(env):
    bad = copy.deepcopy(cr.CRITERIA)
    bad["metrics"]["M1"] = "average rank of the group"
    with pytest.raises(cr.CriteriaError, match="forbidden"):
        _write(env, criteria=bad)
    assert not env["criteria_path"].exists()


def test_the_committed_criteria_file_matches_the_code_and_the_logged_hash():
    assert CRITERIA_FILE.read_bytes() == cr.criteria_bytes()
    assert cr.forbidden_hits(cr.load_criteria()) == []
    assert cr.load_criteria()["forbidden_inputs"]  # the exempt list is present


def test_run_log_is_append_only_through_the_store_api(env):
    _write(env)
    with pytest.raises(StoreError):
        store.write_p6_table(store.read_run_log(env["store_path"]), "p6_run_log", env["store_path"])
    public = [n for n in dir(store) if not n.startswith("_") and callable(getattr(store, n))]
    assert not [n for n in public if any(w in n for w in ("update", "delete", "drop", "reset"))]
