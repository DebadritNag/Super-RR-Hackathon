"""The definition comparison refuses to run unless the pre-declared criteria are intact."""

from __future__ import annotations

import json
import shutil

import pandas as pd
import pytest

from app.phase6 import criteria as cr
from app.phase6 import definition_compare as dc
from app.phase6 import store
from app.phase6.constants import INVESTIGATION_CONFIG


@pytest.fixture()
def env(tmp_path):
    cfg = tmp_path / "cfg.json"
    shutil.copy(INVESTIGATION_CONFIG, cfg)
    e = {
        "criteria_path": tmp_path / "criteria.json",
        "hash_path": tmp_path / "hash.json",
        "config_path": cfg,
        "store_path": tmp_path / "x.duckdb",
    }
    cr.write_criteria(e["criteria_path"], e["hash_path"], cfg, e["store_path"])
    return e


def _begin(env):
    return dc.begin_comparison(env["criteria_path"], env["hash_path"], env["config_path"],
                               env["store_path"])  # fmt: skip


def test_runs_when_the_criteria_are_intact_and_logs_the_step(env):
    info = _begin(env)
    assert info["step"] == "definition_compare" and info["seq"] == 2
    log = store.read_run_log(env["store_path"])
    assert list(log["step"]) == ["plan", "definition_compare"]
    assert log.iloc[1]["criteria_sha256"] == log.iloc[0]["criteria_sha256"]


def test_refuses_when_the_hash_file_is_missing(env):
    env["hash_path"].unlink()
    with pytest.raises(cr.CriteriaError, match="hash file missing"):
        _begin(env)
    assert len(store.read_run_log(env["store_path"])) == 1  # no step was logged


def test_refuses_when_the_criteria_file_is_missing(env):
    env["criteria_path"].unlink()
    with pytest.raises(cr.CriteriaError, match="missing"):
        _begin(env)


def test_refuses_when_the_criteria_changed_after_the_hash_was_written(env):
    crit = json.loads(env["criteria_path"].read_text(encoding="utf-8"))
    crit["rule"] = "PASS(d) iff anything at all"
    env["criteria_path"].write_text(json.dumps(crit, indent=2, sort_keys=True) + "\n", "utf-8")
    with pytest.raises(cr.CriteriaError, match="changed after the hash"):
        _begin(env)
    assert len(store.read_run_log(env["store_path"])) == 1


def test_refuses_when_the_hash_file_was_rewritten_to_match_changed_criteria(env):
    """Changing both files still fails: the run log holds the original hash."""
    crit = json.loads(env["criteria_path"].read_text(encoding="utf-8"))
    crit["rule"] = "changed"
    data = (json.dumps(crit, indent=2, sort_keys=True) + "\n").encode("utf-8")
    env["criteria_path"].write_bytes(data)
    rec = json.loads(env["hash_path"].read_text(encoding="utf-8"))
    rec["sha256"] = cr.sha256_bytes(data)
    env["hash_path"].write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(cr.CriteriaError, match="p6_run_log"):
        _begin(env)


def test_refuses_when_no_plan_row_was_logged_first(env):
    env["store_path"].unlink()
    with pytest.raises(cr.CriteriaError, match="declared first"):
        _begin(env)


def test_refuses_to_run_over_results_made_under_another_hash(env):
    old = pd.DataFrame({"definition": ["a"], "criteria_sha256": ["0" * 64]})
    store.write_p6_table(old, "p6_definition_summary", env["store_path"])
    with pytest.raises(dc.ResultsHashError, match="p6_definition_summary"):
        _begin(env)
    assert len(store.read_run_log(env["store_path"])) == 1


def test_results_under_the_current_hash_do_not_block_a_rerun(env):
    digest = cr.verify_criteria(env["criteria_path"], env["hash_path"], env["store_path"])["sha256"]
    ok = pd.DataFrame({"definition": ["a"], "criteria_sha256": [digest]})
    store.write_p6_table(ok, "p6_definition_summary", env["store_path"])
    assert _begin(env)["step"] == "definition_compare"


def test_results_table_without_a_hash_column_blocks_the_run(env):
    store.write_p6_table(pd.DataFrame({"definition": ["a"]}), "p6_definition_outcome",
                         env["store_path"])  # fmt: skip
    with pytest.raises(dc.ResultsHashError):
        _begin(env)


def test_stored_result_hashes_lists_each_table(env):
    store.write_p6_table(pd.DataFrame({"criteria_sha256": ["a", "b"]}), "p6_definition_resampling",
                         env["store_path"])  # fmt: skip
    got = dc.stored_result_hashes(env["store_path"])
    assert got == {"p6_definition_resampling": {"a", "b"}}


def test_the_real_criteria_still_match_the_logged_hash():
    """The declared criteria on disk are the ones logged before any result existed."""
    info = cr.verify_criteria()
    assert info["logged_seq"] == 1 and len(info["sha256"]) == 64
    for hashes in dc.stored_result_hashes(cr.EXPLORATORY_DB).values():
        assert hashes == {info["sha256"]}
