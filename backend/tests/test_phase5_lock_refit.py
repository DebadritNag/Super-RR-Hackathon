"""Methodology lock and experimental refit (Chunk 5).

Unit tests use temporary files. The real-data tests build a lock in a temporary folder (the real
lock manifest is never written by a test), run the refit twice without writing any table, and check
reproducibility and preservation. They are skipped when the analytical store is absent.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import BACKEND_ROOT
from app.phase4.split import Split
from app.phase5 import lock_manifest as lm
from app.phase5 import refit as rf
from app.phase5.constants import FROZEN_CHOICES, REPORTS_DIR
from app.phase5.lockguard import PHASE5_LOCK_LOG, file_sha256, read_events
from app.phase5.store import table_hashes
from app.services.pressure_service import EXPLORATORY_DB

SCRIPTS = BACKEND_ROOT / "scripts"
need_store = pytest.mark.skipif(
    not (EXPLORATORY_DB.is_file() and FROZEN_CHOICES.is_file()),
    reason="analytical store or frozen choices absent",
)


# ---------------------------------------------------------------- synthetic lock inputs
@pytest.fixture()
def inputs(tmp_path):
    files = {}
    for name, body in {"a.json": '{"x": 1}', "b.json": '{"y": 2}'}.items():
        p = tmp_path / name
        p.write_text(body, encoding="utf-8")
        files[f"config/{name}"] = p
    code = tmp_path / "mod.py"
    code.write_text("X = 1\n", encoding="utf-8")
    return files, [code], {"definition": "any|q0.75", "shrinkage": "shrink_tau4"}


def _write(tmp_path, inputs):
    files, code, choices = inputs
    content = lm.build_lock_content(files, code, choices)
    path = tmp_path / "lock.json"
    lm.write_lock(path, lm.build_manifest(content, {"items": []}))
    return path


def test_lock_hash_is_stable_across_builds(inputs):
    files, code, choices = inputs
    a = lm.build_lock_content(files, code, choices)
    b = lm.build_lock_content(files, code, choices)
    assert a == b
    assert lm.lock_hash(a) == lm.lock_hash(b)
    assert len(lm.lock_hash(a)) == 64


def test_lock_hash_changes_when_any_locked_byte_changes(inputs):
    files, code, choices = inputs
    base = lm.lock_hash(lm.build_lock_content(files, code, choices))
    f = files["config/a.json"]
    f.write_text('{"x": 2}', encoding="utf-8")
    assert lm.lock_hash(lm.build_lock_content(files, code, choices)) != base
    f.write_text('{"x": 1}', encoding="utf-8")
    assert lm.lock_hash(lm.build_lock_content(files, code, choices)) == base
    code[0].write_text("X = 2\n", encoding="utf-8")
    assert lm.lock_hash(lm.build_lock_content(files, code, choices)) != base
    code[0].write_text("X = 1\n", encoding="utf-8")
    assert (
        lm.lock_hash(lm.build_lock_content(files, code, {**choices, "definition": "chase|q0.9"}))
        != base
    )


def test_manifest_is_labelled_experimental_and_never_validated(inputs):
    files, code, choices = inputs
    m = lm.build_manifest(lm.build_lock_content(files, code, choices))
    assert m["label"] == "EXPERIMENTAL_LOCK"
    assert m["status"] == "EXPERIMENTAL_NOT_VALIDATED"
    assert m["validated"] is False


def test_verify_lock_passes_then_raises_on_drift(tmp_path, inputs):
    files, code, choices = inputs
    path = _write(tmp_path, inputs)
    assert lm.verify_lock(path, files, code, choices)["label"] == "EXPERIMENTAL_LOCK"
    files["config/b.json"].write_text('{"y": 3}', encoding="utf-8")
    with pytest.raises(lm.LockDriftError, match="file:config/b.json"):
        lm.verify_lock(path, files, code, choices)


def test_verify_lock_detects_code_choice_and_manifest_tampering(tmp_path, inputs):
    files, code, choices = inputs
    path = _write(tmp_path, inputs)
    with pytest.raises(lm.LockDriftError, match="choice:definition"):
        lm.verify_lock(path, files, code, {**choices, "definition": "other"})
    code[0].write_text("X = 3\n", encoding="utf-8")
    with pytest.raises(lm.LockDriftError, match="code_sha256"):
        lm.verify_lock(path, files, code, choices)
    code[0].write_text("X = 1\n", encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["content"]["choices"]["definition"] = "edited"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(lm.LockDriftError, match="edited"):
        lm.verify_lock(path, files, code, {**choices, "definition": "edited"})


def test_missing_locked_input_is_reported(tmp_path):
    with pytest.raises(lm.LockMissingError):
        lm.hash_files({"config/none.json": tmp_path / "none.json"})


def test_verify_lock_raises_when_manifest_absent_or_unreadable(tmp_path):
    with pytest.raises(lm.LockMissingError):
        lm.verify_lock(tmp_path / "none.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(lm.LockMissingError):
        lm.verify_lock(bad)


# ---------------------------------------------------------------- refit refuses without a valid lock
def test_refit_refuses_without_lock_manifest(tmp_path):
    with pytest.raises(lm.LockMissingError):
        rf.run_refit(lock_path=tmp_path / "absent.json", write=False)


def test_refit_refuses_with_drifted_lock(tmp_path, inputs):
    files, code, choices = inputs
    path = _write(tmp_path, inputs)
    files["config/a.json"].write_text('{"x": 99}', encoding="utf-8")
    with pytest.raises(lm.LockDriftError):
        rf.run_refit(lock_path=path, write=False, verify_files=files, verify_code=code)


def test_refit_script_refuses_without_lock(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("p5_refit_script", SCRIPTS / "phase5_refit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--lock-path", str(tmp_path / "absent.json"), "--reports", str(tmp_path)]) == 2


# ---------------------------------------------------------------- TEST is never in the refit frame
def test_refit_split_moves_validation_into_train_and_keeps_test():
    s = Split.from_config()
    r = rf.refit_split(s)
    dates = pd.Series(pd.to_datetime(["2024-12-31", "2025-01-01", "2025-12-31", "2026-01-01"]))
    assert s.assign_period(dates).tolist() == ["TRAIN", "VALIDATION", "VALIDATION", "TEST"]
    assert r.assign_period(dates).tolist() == ["TRAIN", "TRAIN", "TRAIN", "TEST"]
    assert r.test_start == s.test_start


def test_test_rows_are_refused_by_every_refit_guard():
    raw = pd.DataFrame({"period_orig": ["TRAIN", "VALIDATION", "TEST"], "match_date": [1, 2, 3]})
    with pytest.raises(rf.RefitTestRowsError):
        rf.assert_no_test(raw)
    with pytest.raises(rf.RefitTestRowsError):
        rf.build_refit_frame(raw, Split.from_config())
    with pytest.raises(rf.RefitTestRowsError):
        rf.assert_no_test(raw.drop(columns="period_orig"))
    rf.assert_no_test(raw[raw["period_orig"] != "TEST"])


def test_refit_code_never_opens_or_evaluates_test():
    tree = ast.parse(Path(rf.__file__).read_text(encoding="utf-8"))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    for banned in (
        "evaluate_frozen",
        "evaluate_on_test",
        "open_for_evaluation",
        "_open_for_evaluation",
        "freeze",
    ):
        assert banned not in names


# ---------------------------------------------------------------- real data: refit end to end
@pytest.fixture(scope="module")
def real_lock(tmp_path_factory):
    if not (EXPLORATORY_DB.is_file() and FROZEN_CHOICES.is_file()):
        pytest.skip("analytical store or frozen choices absent")
    path = tmp_path_factory.mktemp("lock") / "lock.json"
    # Built by the test in a temporary folder; the real lock manifest is never touched here.
    lm.write_lock(path, lm.build_manifest(lm.build_lock_content(), None))
    return path


@pytest.fixture(scope="module")
def two_runs(real_lock):
    p4_tables_before = table_hashes(EXPLORATORY_DB, "p4_")
    p4_reports_before = {
        p.name: file_sha256(p) for p in REPORTS_DIR.glob("phase4_*") if p.is_file()
    }
    lock_events_before = read_events(PHASE5_LOCK_LOG)
    a = rf.run_refit(lock_path=real_lock, write=False, n_boot=60)
    b = rf.run_refit(lock_path=real_lock, write=False, n_boot=60)
    return {
        "a": a,
        "b": b,
        "p4_tables_before": p4_tables_before,
        "p4_tables_after": table_hashes(EXPLORATORY_DB, "p4_"),
        "p4_reports_before": p4_reports_before,
        "p4_reports_after": {
            p.name: file_sha256(p) for p in REPORTS_DIR.glob("phase4_*") if p.is_file()
        },
        "lock_events_before": lock_events_before,
        "lock_events_after": read_events(PHASE5_LOCK_LOG),
    }


@need_store
def test_refit_is_reproducible_with_the_same_seed(two_runs):
    assert two_runs["a"].summary["output_hashes"] == two_runs["b"].summary["output_hashes"]
    assert set(two_runs["a"].summary["output_hashes"]) == {
        "scores",
        "calibration",
        "thresholds",
        "comparison",
    }
    pd.testing.assert_frame_equal(two_runs["a"].frames["scores"], two_runs["b"].frames["scores"])


@need_store
def test_original_phase4_tables_and_reports_are_byte_identical_after_refit(two_runs):
    assert len(two_runs["p4_tables_before"]) >= 20
    assert two_runs["p4_tables_before"] == two_runs["p4_tables_after"]
    assert len(two_runs["p4_reports_before"]) >= 50
    assert two_runs["p4_reports_before"] == two_runs["p4_reports_after"]
    for r in ("a", "b"):
        pres = two_runs[r].summary["preservation"]
        assert pres["phase4_tables_byte_identical"] and pres["phase4_report_files_byte_identical"]
        assert pres["all_preserved"] is True


@need_store
def test_refit_does_not_touch_test(two_runs):
    s = two_runs["a"].summary
    pres = s["preservation"]
    assert pres["test_opened"] is False
    assert pres["rows_with_period_orig_test"] == 0
    assert pres["periods_in_refit_frame"] == ["TRAIN"]
    assert pres["period_orig_in_refit_frame"] == ["TRAIN", "VALIDATION"]
    assert s["date_max"] <= "2025-12-31"
    assert two_runs["lock_events_before"] == two_runs["lock_events_after"]
    assert not any(e.get("event") == "OPEN" for e in two_runs["lock_events_after"])
    assert pres["phase4_lock_log_sha256_before"] == pres["phase4_lock_log_sha256_after"]


@need_store
def test_refit_outputs_are_labelled_experimental_and_internal(two_runs):
    s = two_runs["a"].summary
    assert s["status"] == "EXPERIMENTAL_NOT_VALIDATED" and s["validated"] is False
    assert (
        s["official_ranking"] is False and s["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    )
    sc = two_runs["a"].frames["scores"]
    assert set(sc["status"]) == {"EXPERIMENTAL_NOT_VALIDATED"}
    assert set(sc["model_label"]) == {"EXPERIMENTAL_REFIT_TRAIN_VALIDATION"}
    assert set(sc["publication_status"]) == {"INTERNAL_EXPERIMENTAL_ONLY"}
    assert not sc["official_ranking"].any()
    assert set(sc["definition_id"]) == {"any|q0.75"} and set(sc["fit_window"]) == {
        "TRAIN+VALIDATION"
    }
    assert sc.groupby(["format", "role"]).ngroups == 4
    elig = sc[sc["eligible_working_pool"]]
    assert elig["rank"].notna().all() and sc.loc[~sc["eligible_working_pool"], "rank"].isna().all()


@need_store
def test_refit_comparison_with_phase4_is_close_but_not_identical(two_runs):
    c = two_runs["a"].frames["comparison"]
    assert len(c) == 4
    assert (c["spearman_common"] > 0.9).all()
    assert (c["mean_abs_change"] > 0).all()  # a different fit window changes the numbers


@need_store
def test_thresholds_table_records_locked_pools_unchanged(two_runs):
    t = two_runs["a"].frames["thresholds"]
    pools = t[t["threshold"].str.startswith("working_pool_balls")]
    assert len(pools) == 4 and (pools["difference"] == 0).all()


@need_store
def test_write_outputs_only_creates_p5_refit_tables(tmp_path, two_runs):
    import shutil

    store = tmp_path / "x.duckdb"
    shutil.copyfile(EXPLORATORY_DB, store)
    rf.write_outputs(two_runs["a"], store, tmp_path)
    after = table_hashes(store, "p5_refit_trainval_v1")
    assert set(after) == set(rf.TABLES.values())
    assert table_hashes(store, "p4_") == two_runs["p4_tables_before"]
    assert (tmp_path / "p5_refit_trainval_v1_manifest.json").is_file()


# ---------------------------------------------------------------- the lock is explicit only
def test_only_the_lock_script_calls_write_lock():
    callers = []
    for p in [*(BACKEND_ROOT / "app").rglob("*.py"), *SCRIPTS.glob("*.py")]:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name == "write_lock":
                    callers.append(p.name)
    assert sorted(set(callers)) == ["phase5_methodology_lock.py"]


def test_lock_script_without_confirm_flag_writes_no_lock(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p5_lock_script", SCRIPTS / "phase5_methodology_lock.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lock = tmp_path / "lock.json"
    mod.main(
        [
            "--reports",
            str(tmp_path),
            "--lock-path",
            str(lock),
            "--store",
            str(tmp_path / "none.duckdb"),
        ]
    )
    assert not lock.exists()
    # the checklist is written as a report, never as a lock
    assert (tmp_path / "phase5_pre_lock_checklist.json").is_file()


def test_lock_script_refuses_to_lock_when_required_items_fail(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p5_lock_script2", SCRIPTS / "phase5_methodology_lock.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lock = tmp_path / "lock.json"
    rc = mod.main(
        [
            "--confirm-lock",
            "--reports",
            str(tmp_path),
            "--lock-path",
            str(lock),
            "--store",
            str(tmp_path / "x.duckdb"),
        ]
    )
    assert rc == 1 and not lock.exists()


def test_orchestrator_never_creates_the_lock_implicitly():
    text = (SCRIPTS / "run_phase5.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    from importlib import util

    spec = util.spec_from_file_location("p5_orch", SCRIPTS / "run_phase5.py")
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert all("--confirm-lock" not in extra for _, _, extra in mod.STEPS)
    assert mod.LOCK_STEP[2] == ["--confirm-lock"]
    assert "--create-lock" in text and "if args.create_lock" in text
    assert "run_phase4" not in text
    assert tree is not None


# ---------------------------------------------------------------- checklist honesty
@need_store
def test_real_checklist_records_failures_and_never_claims_validation():
    chk = lm.pre_lock_checklist()
    by = {i["id"]: i for i in chk["items"]}
    assert chk["methodology_validated"] is False and chk["publication_ready"] is False
    assert by["methodology_validated"]["status"] == "FAIL"
    assert by["gate:data_weight_gate_passed"]["status"] == "FAIL"
    assert by["gate:date_verification"]["status"] == "FAIL"
    assert by["strict_uncapped_enabled"]["status"] == "FAIL"
    assert all(
        i["status"] == "USER_APPROVAL_PENDING" for i in chk["items"] if i["kind"] == "USER_DECISION"
    )
    assert "decision:official_rankings" in chk["pending_user_decisions"]
    assert {"data_weight_gate_passed", "methodology_validated", "date_verification"} <= {
        i.split(":")[-1] for i in chk["failing_publication_checks"]
    }
    # a required item that fails blocks the lock; failing publication gates do not
    assert chk["required_all_pass"] is True


def test_checklist_on_empty_reports_fails_required_items(tmp_path):
    chk = lm.pre_lock_checklist(tmp_path, tmp_path / "none.duckdb", tmp_path / "none.json")
    assert chk["required_all_pass"] is False
    assert chk["publication_ready"] is False
    assert {i["status"] for i in chk["items"] if i["kind"] == "REQUIRED_FOR_EXPERIMENTAL_LOCK"} >= {
        "FAIL"
    }


def test_canonical_hash_ignores_key_order():
    assert lm.canonical_hash({"a": 1, "b": [1, 2]}) == lm.canonical_hash({"b": [1, 2], "a": 1})
    assert lm.canonical_hash({"a": 1}) == hashlib.sha256(b'{"a":1}').hexdigest()
