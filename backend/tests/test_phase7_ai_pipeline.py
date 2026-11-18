"""Phase 7 chunk 5: statistical baseline/shrinkage verification run (no ML model exists)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.phase4.constants import REPORTS_DIR
from app.phase7 import ai_pipeline as ap

LOCK_SHA = "cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c"


@pytest.fixture(scope="module")
def runs():
    first = ap.run_pipeline(timestamp="2026-11-16T00:00:00Z")
    second = ap.run_pipeline(timestamp="2026-11-16T00:00:01Z")
    return first, second


def test_label_is_exactly_the_statistical_wording():
    assert ap.MODEL_LABEL == (
        "statistical baseline/shrinkage model (not machine learning or deep learning)"
    )


def test_registry_metadata_record_exists_and_says_there_is_no_trained_artefact():
    reg = json.loads((REPORTS_DIR / ap.REGISTRY_NAME).read_text(encoding="utf-8"))
    assert reg["model_label"] == ap.MODEL_LABEL
    assert reg["is_machine_learning"] is False and reg["is_deep_learning"] is False
    assert reg["trained_artefact_exists"] is False
    assert reg["test_opened"] is False and reg["lock_unchanged"] is True
    assert reg["seed"] == 20260512
    for key in (
        "model_version",
        "training_data_version",
        "run_timestamp_utc",
        "code_sha256",
        "split_config_sha256",
        "state_store_sha256",
        "outputs",
        "deterministic_digest",
    ):
        assert reg[key]
    # the hashes of the written outputs match the files on disk
    import hashlib

    for name, digest in reg["outputs"].items():
        assert hashlib.sha256((REPORTS_DIR / name).read_bytes()).hexdigest() == digest


def test_two_runs_are_identical_apart_from_the_timestamp(runs):
    a, b = runs
    assert ap.deterministic_digest(a) == ap.deterministic_digest(b)
    assert a["timestamp"] != b["timestamp"]


def test_train_only_fit_and_no_test_rows_loaded(runs):
    m = runs[0]["metrics"]
    chk = m["data_checks"]
    assert chk["test_match_ids_in_frame"] == 0
    assert chk["test_matches_listed_in_p4_match_period"] == 144
    assert chk["periods_in_frame"] == ["TRAIN", "VALIDATION"]
    assert m["thresholds_max_abs_diff_vs_phase4_frozen"] < 1e-6
    assert chk["baseline_cell_keys_use_outcome_columns"] is False
    assert m["restricted_test"]["opened_in_this_run"] is False
    assert m["restricted_test"]["independent_out_of_sample_validation_claimed"] is False


def test_lock_logs_unchanged_by_the_run(runs):
    reg = runs[0]["registry"]
    assert reg["lock_before"] == reg["lock_after"]
    assert reg["lock_after"]["phase4_lock_log_sha256"] == LOCK_SHA
    assert reg["lock_after"]["phase4_events"] == ["FREEZE", "OPEN", "CLOSE"]
    assert reg["lock_after"]["phase5_open_events"] == 0


def test_pipeline_source_never_touches_the_test_lock_machinery():
    src = Path(ap.__file__).read_text(encoding="utf-8")
    for banned in ("evaluate_on_test", "_open_for_evaluation", "TestLock(", "write_p4_table"):
        assert banned not in src


def test_validation_metrics_are_present_and_the_period_is_validation(runs):
    dv = runs[0]["metrics"]["delivery_level_validation"]
    assert set(dv) == {"batter:runs", "batter:dismissal", "bowler:charged", "bowler:wkt"}
    for blk in dv.values():
        v = blk["periods"]["VALIDATION"]
        assert v["rows"] > 10_000 and v["rmse"] > 0 and v["mae"] > 0
        assert len(blk["validation_by_predicted_decile"]) == 10
    pv = runs[0]["metrics"]["player_level_validation_train_to_validation"]
    assert pv["batter:IPL"]["status"] == "OK"


@pytest.mark.parametrize("role", ["batter", "bowler"])
def test_output_frames_have_no_fabricated_uncertainty_and_failing_gates(runs, role):
    df = runs[0]["outputs"][role]
    assert 0 < len(df) <= 10
    assert (df["uncertainty"] == ap.NO_UNCERTAINTY).all()
    assert not [
        c for c in df.columns if any(w in c.lower() for w in ("interval", "ci_", "confidence"))
    ]
    assert (df["methodology_gate_status"] == "INTERNAL_EXPERIMENTAL_ONLY").all()
    assert (df["experimental_publication_status"] == ap.PUBLICATION_STATUS).all()
    assert (df["model_label"] == ap.MODEL_LABEL).all()
    assert df["banner"].str.contains("NOT A VALIDATED RANKING").all()
    assert df["model_output_value"].is_monotonic_decreasing
    assert df["player_id"].is_unique and df["player_name"].notna().all()
    assert (df["data_weight"] < 1).all()


def test_csv_files_on_disk_match_the_columns_and_have_no_uncertainty_numbers():
    for name in ap.CSV_NAMES.values():
        df = pd.read_csv(REPORTS_DIR / name)
        assert list(df.columns) == ap.CSV_COLUMNS
        assert (df["uncertainty"] == ap.NO_UNCERTAINTY).all()
        assert len(df) <= 10


def test_short_list_is_not_padded():
    est = pd.DataFrame(
        {
            "n": [30, 40, 50],
            "matches": [4, 5, 6],
            "mean": [0.1, 0.2, 0.3],
            "B": [0.3, 0.3, 0.3],
            "floor_hit": [True, True, True],
            "observed_pressure_mean": [1.0, 1.0, 1.0],
            "expected_pressure_mean": [0.9, 0.9, 0.9],
            "model_output": [0.1, 0.3, 0.2],
            "eligible": [True, True, False],
            "player_name": ["A", "B", "C"],
        },
        index=pd.Index([1, 2, 3], name="player_id"),
    )
    out, note = ap.build_output_frame(est, "batter", "v", "dv", "2026-01-01T00:00:00Z")
    assert list(out["player_id"]) == [2, 1]
    assert "no padding" in note


def test_submitted_top10_files_never_claim_validation_without_declared_evidence():
    """Phase 7 asserted that no Top 10 file exists. The official scope correction requires the two
    Top 10 files, so the invariant now is that any such file carries an honest status label and is
    never the experimental AI output."""
    for name in ("pressure_batters_top10.csv", "pressure_bowlers_top10.csv"):
        p = REPORTS_DIR / name
        if not p.exists():
            continue
        df = pd.read_csv(p)
        assert {"ranking_status", "model_validation_status", "list_status"} <= set(df.columns)
        assert set(df["ranking_status"]) <= {
            "VALIDATED",
            "PROVISIONAL",
            "EXPLORATORY",
            "INSUFFICIENT_EVIDENCE",
        }
        assert "EXPERIMENTAL_AI" not in " ".join(df.columns).upper()
