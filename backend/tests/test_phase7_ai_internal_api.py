"""Phase 7 chunk 5: token-protected internal experimental-model routes."""

from __future__ import annotations

import shutil

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4.constants import REPORTS_DIR
from app.phase7 import ai_loader as al
from app.phase7 import ai_pipeline as ap

P = "/api/v1/internal"
H = {"X-Admin-Token": "tok"}
PATHS = [f"{P}/model-status", f"{P}/experimental-predictions"]


@pytest.fixture()
def client():
    return TestClient(create_app(admin_token="tok"))


@pytest.mark.parametrize("path", PATHS)
def test_missing_or_wrong_token_is_401(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-Admin-Token": "bad"}).status_code == 401


@pytest.mark.parametrize("path", PATHS)
def test_503_when_no_token_is_configured(monkeypatch, path):
    monkeypatch.delenv("SUPERR_ADMIN_TOKEN", raising=False)
    c = TestClient(create_app(admin_token=None))
    assert c.get(path, headers=H).status_code == 503


def test_predictions_with_token(client):
    r = client.get(f"{P}/experimental-predictions", headers=H)
    assert r.status_code == 200
    b = r.json()
    assert b["state"] == "AVAILABLE"
    assert b["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    assert b["official_ranking"] is False
    assert "NOT A VALIDATED RANKING" in b["banner"]
    assert b["model_label"] == ap.MODEL_LABEL
    assert b["uncertainty_note"] == ap.NO_UNCERTAINTY
    assert set(b["roles"]) == {"batter", "bowler"}
    for role in b["roles"].values():
        assert 0 < len(role["rows"]) <= 10
        assert all(row["uncertainty"] == ap.NO_UNCERTAINTY for row in role["rows"])


def test_role_filter(client):
    b = client.get(f"{P}/experimental-predictions?role=bowler", headers=H).json()
    assert set(b["roles"]) == {"bowler"}
    assert client.get(f"{P}/experimental-predictions?role=x", headers=H).status_code == 422


def test_official_flag_is_refused(client):
    r = client.get(f"{P}/experimental-predictions?official=true", headers=H)
    assert r.status_code == 403


def test_model_status_says_no_trained_artefact(client):
    b = client.get(f"{P}/model-status", headers=H).json()
    assert b["is_machine_learning"] is False and b["is_deep_learning"] is False
    assert b["trained_artefact_exists"] is False
    assert b["test_opened_in_this_pipeline"] is False
    assert b["registry"]["model_id"] == ap.MODEL_ID


def test_mutating_a_response_does_not_change_the_next(client):
    a = client.get(f"{P}/experimental-predictions", headers=H).json()
    a["roles"]["batter"]["rows"].clear()
    b = client.get(f"{P}/experimental-predictions", headers=H).json()
    assert len(b["roles"]["batter"]["rows"]) > 0


def test_no_public_route_exposes_predictions(client):
    app = client.app
    for r in app.routes:
        if (
            isinstance(r, APIRoute)
            and "experimental" in r.path
            or "model-status" in getattr(r, "path", "")
        ):
            assert r.path.startswith("/api/v1/internal/"), r.path
    for path in ("/api/v1/players", "/api/v1/experimental-predictions", "/api/v1/model-status"):
        r = client.get(path)
        assert "model_output" not in r.text and "experimental_ai" not in r.text
    assert client.get("/api/v1/experimental-predictions").status_code == 404


def test_loader_states(tmp_path):
    assert al.load_ai_outputs(tmp_path)["state"] == al.INSUFFICIENT_DATA
    for name in (ap.REGISTRY_NAME, *ap.CSV_NAMES.values()):
        shutil.copy(REPORTS_DIR / name, tmp_path / name)
    # lock log missing: cannot verify the lock, so the outputs are withheld
    assert al.load_ai_outputs(tmp_path)["state"] == al.LOCKED
    shutil.copy(REPORTS_DIR / "phase4_lock_log.json", tmp_path / "phase4_lock_log.json")
    assert al.load_ai_outputs(tmp_path)["state"] == al.AVAILABLE
    # a changed lock log is LOCKED
    (tmp_path / "phase4_lock_log.json").write_text("[]", encoding="utf-8")
    out = al.load_ai_outputs(tmp_path)
    assert out["state"] == al.LOCKED and out["roles"] == {}
    # a changed output file is LOCKED
    shutil.copy(REPORTS_DIR / "phase4_lock_log.json", tmp_path / "phase4_lock_log.json")
    (tmp_path / ap.CSV_NAMES["batter"]).write_text("x\n", encoding="utf-8")
    assert al.load_ai_outputs(tmp_path)["state"] == al.LOCKED


def test_endpoint_reports_locked_state_instead_of_rows(tmp_path):
    c = TestClient(create_app(admin_token="tok"))
    c.app.state.ai_reports = tmp_path
    b = c.get(f"{P}/experimental-predictions", headers=H).json()
    assert b["state"] == "INSUFFICIENT_DATA" and b["roles"] == {}
