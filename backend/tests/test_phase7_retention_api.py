"""Retention admin API, CLI and the one-command procedure. Fixtures are SYNTHETIC (tmp_path)."""

from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes_retention import RetentionContext
from app.core.config import BACKEND_ROOT
from app.main import create_app
from tests.test_phase7_retention_import import RR, make_ref, write_csv, write_profiles

TOKEN = {"X-Admin-Token": "tok"}
ROWS = [
    ["Alpha One", "", RR, "retained", "SYNTHETIC doc", ""],
    ["Gamma Same", "", RR, "released", "SYNTHETIC doc", ""],
]
Q = "filename=l.csv&snapshot_date=2026-11-17&source=SYNTHETIC"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, BACKEND_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def client(tmp_path):
    app = create_app(admin_token="tok")
    app.state.retention = RetentionContext(
        store=tmp_path / "store.duckdb", raw_dir=tmp_path / "raw", reports_dir=tmp_path / "rep",
        profile_dir=tmp_path / "prof", reference=make_ref(),
    )  # fmt: skip
    (tmp_path / "prof").mkdir()
    write_profiles(tmp_path / "prof")
    return TestClient(app)


@pytest.fixture
def body(tmp_path) -> bytes:
    return write_csv(tmp_path / "l.csv", ROWS).read_bytes()


ROUTES = [
    ("post", f"/api/v1/internal/retention/preview?{Q}"),
    ("post", f"/api/v1/internal/retention/import?{Q}"),
    ("get", "/api/v1/internal/retention/review"),
    ("post", "/api/v1/internal/retention/review/1/resolve"),
    ("post", "/api/v1/internal/retention/availability/rebuild"),
]


@pytest.mark.parametrize(("method", "url"), ROUTES)
def test_admin_endpoints_reject_missing_and_wrong_token(client, body, tmp_path, method, url):
    for headers in ({}, {"X-Admin-Token": "wrong"}):
        kw = (
            {"json": {"resolver": "a", "evidence": "b", "player_id": 1}}
            if "resolve" in url
            else {"content": body}
        )
        r = client.request(method.upper(), url, headers=headers, **kw)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "ADMIN_AUTH_FAILED"
    assert not (tmp_path / "store.duckdb").exists()  # nothing was written


def test_admin_endpoints_are_disabled_when_no_token_is_configured(tmp_path, body):
    app = create_app()  # no token configured
    app.state.retention = RetentionContext(store=tmp_path / "s.duckdb", raw_dir=tmp_path / "r")
    r = TestClient(app).post(f"/api/v1/internal/retention/import?{Q}", content=body)
    assert r.status_code == 503 and not (tmp_path / "s.duckdb").exists()


def test_preview_validates_without_writing(client, body, tmp_path):
    r = client.post(f"/api/v1/internal/retention/preview?{Q}", headers=TOKEN, content=body)
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "DRY_RUN" and j["changed"] is False and len(j["rows"]) == 2
    assert j["mapping_counts"] == {"MAPPED": 1, "AMBIGUOUS": 1}
    assert not (tmp_path / "store.duckdb").exists() and not (tmp_path / "raw").exists()


def test_import_review_resolve_and_rebuild_flow(client, body, tmp_path):
    r = client.post(f"/api/v1/internal/retention/import?{Q}", headers=TOKEN, content=body)
    assert r.status_code == 200 and r.json()["status"] == "IMPORTED"
    again = client.post(f"/api/v1/internal/retention/import?{Q}", headers=TOKEN, content=body)
    assert again.json()["status"] == "ALREADY_IMPORTED" and again.json()["changed"] is False
    items = client.get("/api/v1/internal/retention/review", headers=TOKEN).json()["items"]
    assert [i["raw_player_name"] for i in items] == ["Gamma Same"]
    bad = client.post(f"/api/v1/internal/retention/review/{items[0]['review_id']}/resolve",
                      headers=TOKEN, json={"resolver": "Ana", "evidence": "", "player_id": 3})  # fmt: skip
    assert bad.status_code == 422
    ok = client.post(f"/api/v1/internal/retention/review/{items[0]['review_id']}/resolve",
                     headers=TOKEN, json={"resolver": "Ana", "evidence": "SYNTHETIC check", "player_id": 3})  # fmt: skip
    assert ok.status_code == 200 and ok.json()["state"] == "RESOLVED"
    assert (tmp_path / "rep" / "retention_review_queue.csv").is_file()
    rb = client.post("/api/v1/internal/retention/availability/rebuild", headers=TOKEN).json()
    assert rb["state"] == "LIST_IMPORTED" and rb["retained_excluded"] == 1
    names = [
        r["player_name"]
        for r in csv.DictReader(
            open(tmp_path / "rep" / "candidate_availability.csv", encoding="utf-8")
        )
    ]
    assert "Alpha One" not in names


def test_invalid_upload_is_a_clean_422(client):
    r = client.post("/api/v1/internal/retention/preview?filename=l.txt&snapshot_date=2026-11-17",
                    headers=TOKEN, content=b"a,b")  # fmt: skip
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_RETENTION_FILE"
    r = client.post(f"/api/v1/internal/retention/preview?{Q}", headers=TOKEN, content=b"")
    assert r.status_code == 422


def test_retention_routes_are_only_internal_and_expose_no_ranking_fields():
    app = create_app(admin_token="tok")
    paths = [p for p in app.openapi()["paths"] if "retention" in p]
    assert paths and all(p.startswith("/api/v1/internal/retention") for p in paths)
    src = (BACKEND_ROOT / "app" / "api" / "v1" / "routes_retention.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(rank|score|eligib)", src, re.I)


# ------------------------------------------------------------------ CLI and procedure
def test_cli_without_a_file_exits_2_and_changes_nothing(tmp_path, capsys):
    cli = load_script("import_retention_list")
    code = cli.main(["--file", str(tmp_path / "nope.csv"), "--snapshot-date", "2026-11-17",
                     "--store", str(tmp_path / "s.duckdb")])  # fmt: skip
    assert code == 2 and "NO RETENTION FILE" in capsys.readouterr().out
    assert not (tmp_path / "s.duckdb").exists()


def test_cli_dry_run_and_invalid_file(tmp_path, capsys):
    cli = load_script("import_retention_list")
    f = write_csv(tmp_path / "l.csv", ROWS)
    args = ["--file", str(f), "--snapshot-date", "2026-11-17", "--store", str(tmp_path / "s.duckdb"),
            "--raw-dir", str(tmp_path / "raw"), "--reports-dir", str(tmp_path / "rep")]  # fmt: skip
    assert cli.main([*args, "--dry-run"]) == 0 and "DRY_RUN" in capsys.readouterr().out
    assert not (tmp_path / "s.duckdb").exists()
    bad = write_csv(tmp_path / "bad.csv", [["x"]], header=["colour"])
    assert cli.main([*args[:0], "--file", str(bad), "--snapshot-date", "2026-11-17",
                     "--store", str(tmp_path / "s.duckdb")]) == 1  # fmt: skip


def test_procedure_with_no_file_runs_cleanly_with_an_explicit_state(tmp_path, capsys):
    proc = load_script("run_retention_procedure")
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    code = proc.main(["--file", str(tmp_path / "missing.xlsx"), "--store", str(tmp_path / "s.duckdb"),
                      "--reports-dir", str(tmp_path / "rep"), "--profile-dir", str(prof)])  # fmt: skip
    assert code == 0 and "NO RETENTION FILE YET" in capsys.readouterr().out
    report = (tmp_path / "rep" / "retention_import_run_report.md").read_text(encoding="utf-8")
    assert "NO RETENTION FILE YET" in report
    header = (
        (tmp_path / "rep" / "candidate_availability.csv").read_text(encoding="utf-8").splitlines()
    )
    assert len(header) == 1
    assert not (tmp_path / "s.duckdb").exists()


def test_procedure_with_a_synthetic_file_imports_reports_and_regenerates(
    tmp_path, capsys, monkeypatch
):
    from app.data_pipeline import retention_importer as ri

    monkeypatch.setattr(ri, "load_reference", lambda *a, **k: make_ref())
    proc = load_script("run_retention_procedure")
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    f = write_csv(tmp_path / "l.csv", ROWS)
    args = ["--file", str(f), "--snapshot-date", "2026-11-17", "--source", "SYNTHETIC",
            "--store", str(tmp_path / "s.duckdb"), "--raw-dir", str(tmp_path / "raw"),
            "--reports-dir", str(tmp_path / "rep"), "--profile-dir", str(prof)]  # fmt: skip
    assert proc.main(args) == 0
    assert proc.main(args) == 0  # rerun is idempotent
    report = (tmp_path / "rep" / "retention_import_run_report.md").read_text(encoding="utf-8")
    assert "ALREADY_IMPORTED" in report and "LIST_IMPORTED" in report
    con = duckdb.connect(str(tmp_path / "s.duckdb"), read_only=True)
    assert con.execute("SELECT count(*) FROM p7_retention_imports").fetchone()[0] == 1
    con.close()
    assert Path(tmp_path / "rep" / "retention_review_queue.csv").is_file()
