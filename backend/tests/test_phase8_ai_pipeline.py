"""Phase 8 chunk 6: AI pipeline verification, experimental outputs and production-data scans."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase8 import ai_verify as av
from app.phase8.constants import MODELS_DIR, REPORTS_DIR
from app.phase8.expected import SPECS

BACKEND = Path(__file__).resolve().parents[1]
CSV = {r: REPORTS_DIR / f"experimental_ai_top10_{r}.csv" for r in ("batters", "bowlers")}
HAVE_ARTEFACTS = all((MODELS_DIR / f"{s}.joblib").exists() for s in av.ARTEFACT_STEMS)
needs_models = pytest.mark.skipif(not HAVE_ARTEFACTS, reason="model artefacts not generated")
needs_csv = pytest.mark.skipif(not all(p.exists() for p in CSV.values()), reason="AI CSV missing")


def test_cluster_mean_matches_a_hand_computation():
    res = pd.Series([1.0, 3.0, 2.0, 2.0, 5.0, 5.0])
    mid = pd.Series([1, 1, 2, 2, 3, 3])
    mean, se, k = av._cluster_mean(res, mid)
    assert mean == pytest.approx(3.0) and k == 3
    # cluster sums 4, 4, 10 with sizes 2: e = sum - mean*size = -2, -2, 4
    expected = np.sqrt(3 / 2 * (4 + 4 + 16)) / 6
    assert se == pytest.approx(expected)


def test_cluster_mean_single_match_has_no_standard_error():
    _m, se, k = av._cluster_mean(pd.Series([1.0, 2.0]), pd.Series([7, 7]))
    assert k == 1 and np.isnan(se)


def _scores(rows):
    d = pd.DataFrame(rows)
    d["role"] = "batter"
    return d


def test_top10_orders_by_output_breaks_ties_by_player_id_and_drops_ineligible():
    rows = [
        {
            "player_id": 9,
            "mean_runs_residual": 0.5,
            "ci_low": 0.1,
            "ci_high": 0.9,
            "eligible": True,
        },
        {
            "player_id": 3,
            "mean_runs_residual": 0.5,
            "ci_low": -0.1,
            "ci_high": 0.9,
            "eligible": True,
        },
        {
            "player_id": 5,
            "mean_runs_residual": 9.0,
            "ci_low": 8.0,
            "ci_high": 9.9,
            "eligible": False,
        },
    ]
    rows += [
        {
            "player_id": 100 + i,
            "mean_runs_residual": 0.01 * i,
            "ci_low": -1,
            "ci_high": 1,
            "eligible": True,
        }
        for i in range(12)
    ]
    out = av.top10(_scores(rows))
    assert list(out["player_id"][:2]) == [3, 9]
    assert 5 not in set(out["player_id"])
    assert len(out) == 10 and list(out["model_output_order"]) == list(range(1, 11))
    assert set(out["status_label"]) == {"EXPERIMENTAL_NOT_VALIDATED"}
    assert out.loc[out["player_id"] == 3, "interval_excludes_zero"].item() is False


def test_top10_lists_fewer_when_few_are_eligible():
    rows = [
        {"player_id": i, "mean_runs_residual": 0.1, "ci_low": 0, "ci_high": 1, "eligible": i < 4}
        for i in range(8)
    ]
    assert len(av.top10(_scores(rows))) == 4


@needs_models
def test_every_artefact_exists_with_metadata_and_trained_on_train_only():
    inv = av.artefact_inventory()
    assert len(inv) == len(SPECS) + 1
    for row in inv:
        assert row["exists"] and row["bytes"] > 1000
        assert row["trained_on"] == "TRAIN" and row["seed"] == 20260512
        assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])


@needs_models
def test_artefact_predictions_come_from_the_stored_predictor_object():
    a = av.load_artefact("p8_expected_batter_runs_v1")
    feats = a["obj"]["features"]
    x = pd.DataFrame(np.zeros((3, len(feats))), columns=feats)
    p = a["obj"]["predictor"](x)
    assert p.shape == (3,) and np.isfinite(p).all()
    a["obj"]["predictor"].how = "const"
    a["obj"]["predictor"].model = 123.0
    assert (a["obj"]["predictor"](x) == 123.0).all()  # the output follows the object, nothing else


@needs_models
def test_reloading_an_artefact_is_unaffected_by_changes_to_an_earlier_copy():
    a = av.load_artefact("p8_expected_bowler_wicket_v1")
    a["obj"]["predictor"].how = "const"
    b = av.load_artefact("p8_expected_bowler_wicket_v1")
    assert b["obj"]["predictor"].how != "const"


@needs_csv
@needs_models
@pytest.mark.parametrize("role", ["batters", "bowlers"])
def test_experimental_csv_is_real_labelled_and_tied_to_the_artefacts(role):
    d = pd.read_csv(CSV[role])
    assert 0 < len(d) <= 10
    assert list(d["model_output_order"]) == list(range(1, len(d) + 1))
    assert set(d["status_label"]) == {"EXPERIMENTAL_NOT_VALIDATED"}
    assert d["banner"].str.contains("NOT the submitted ranking").all()
    assert d["mean_runs_residual"].is_monotonic_decreasing
    r = role[:-1]
    assert set(d["model_artefact_runs_sha256"]) == {
        av.load_artefact(f"p8_expected_{r}_runs_v1")["sha256"]
    }
    assert set(d["model_artefact_wicket_sha256"]) == {
        av.load_artefact(f"p8_expected_{r}_wicket_v1")["sha256"]
    }
    assert (d["pressure_balls"] >= av.MIN_PRESSURE_BALLS).all()
    assert (d["pressure_matches"] >= av.MIN_PRESSURE_MATCHES).all()
    assert (d["ci_low"] <= d["mean_runs_residual"]).all()


@needs_csv
def test_experimental_lists_do_not_replace_the_submitted_lists():
    for role in ("batters", "bowlers"):
        sub = pd.read_csv(REPORTS_DIR / f"pressure_{role}_top10.csv")
        assert "status_label" not in sub.columns and "model_output_order" not in sub.columns
        assert set(sub["list_status"]) <= {"EXPLORATORY", "PROVISIONAL", "VALIDATED"}


def test_phase7_outputs_are_preserved_under_the_aborted_names():
    for name in (
        "ai_pipeline_verification_phase7_aborted.md",
        "experimental_ai_top10_batters_phase7_aborted.csv",
        "experimental_ai_top10_bowlers_phase7_aborted.csv",
    ):
        if not (REPORTS_DIR / name).exists():
            pytest.skip("Phase 8 verification not run")
    old = (REPORTS_DIR / "ai_pipeline_verification_phase7_aborted.md").read_text(encoding="utf-8")
    assert "no trained" in old.lower() or "not machine learning" in old.lower()


@pytest.mark.skipif(
    not (REPORTS_DIR / "phase8_ai_verification.json").exists(), reason="verification not run"
)
def test_verification_record_shows_retraining_reproduces_the_artefact_and_no_test_rows():
    j = json.loads((REPORTS_DIR / "phase8_ai_verification.json").read_text(encoding="utf-8"))
    assert j["test_rows_loaded"] == 0 and j["periods_loaded"] == ["TRAIN", "VALIDATION"]
    assert j["lock_unchanged"] is True
    for c in j["retrain_checks"]:
        assert c["max_abs_prediction_diff"] == pytest.approx(0.0, abs=1e-9)
        assert c["retrained"] < c["constant_baseline"]
    assert j["wp_check"]["brier_gain_vs_constant"] > 0


@pytest.mark.skipif(
    not (REPORTS_DIR / "ai_pipeline_verification.md").exists(), reason="report not written"
)
def test_report_separates_technical_success_from_reliability():
    t = (REPORTS_DIR / "ai_pipeline_verification.md").read_text(encoding="utf-8").lower()
    assert "technical success is not" in t and "reliab" in t
    assert "experimental_not_validated" in t
    assert "hardcoded" in t and "retained" in t


def test_ai_modules_hold_no_player_names_scores_or_random_numbers():
    files = [
        BACKEND / "app" / "phase8" / "ai_verify.py",
        BACKEND / "app" / "services" / "submission_service.py",
        BACKEND / "app" / "api" / "v1" / "routes_submission.py",
        BACKEND / "app" / "schemas" / "phase8_submission.py",
        BACKEND / "scripts" / "phase8_ai_verify.py",
    ]
    names = set()
    for p in list(CSV.values()) + [
        REPORTS_DIR / "pressure_batters_top10.csv",
        REPORTS_DIR / "pressure_bowlers_top10.csv",
    ]:
        if p.exists():
            names |= set(pd.read_csv(p)["player_name"].dropna())
    banned = re.compile(r"np\.random|random\.|Math\.random|faker|MOCK_|DEMO_|dummy_", re.I)
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert not banned.search(text), f.name
        for n in names:
            assert f'"{n}"' not in text and f"'{n}'" not in text, (f.name, n)
