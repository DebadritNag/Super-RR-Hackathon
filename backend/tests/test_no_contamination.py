"""Official data is preserved and Cricsheet never reaches DuckDB or any ranking sample."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import shutil

import pytest

from app.analytics.integrity import (
    assert_unchanged,
    open_official_readonly,
    snapshot_from_settings,
    snapshot_official,
)
from app.analytics.proxy_samples import extract_samples
from app.core.config import BACKEND_ROOT, Settings
from app.core.database import connect
from app.validation import cricsheet_super_over as so
from app.validation import data_quality_impact as dq

APP = BACKEND_ROOT / "app"
SCRIPTS = BACKEND_ROOT / "scripts"
PACKAGES = ("analytics", "validation")
SQL_WRITE = re.compile(
    r"INSERT INTO|CREATE (OR REPLACE )?(TABLE|VIEW|SEQUENCE)|UPDATE \w+ SET|DELETE FROM|"
    r"DROP (TABLE|VIEW)|ALTER TABLE"
)


def _sources(*packages):
    for pkg in packages:
        yield from sorted((APP / pkg).rglob("*.py"))


def _load_script(name):
    spec = importlib.util.spec_from_file_location(f"t_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------- static guarantees
def test_analytics_and_validation_only_open_the_database_read_only():
    offenders = []
    for path in _sources(*PACKAGES):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name != "connect":
                continue
            ro = next((k.value for k in node.keywords if k.arg == "read_only"), None)
            read_only = isinstance(ro, ast.Constant) and ro.value is True
            if not read_only and path.name != "format_config.py":
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def test_only_the_explicit_registration_function_opens_read_write():
    text = (APP / "analytics" / "format_config.py").read_text(encoding="utf-8")
    assert text.count("read_only=False") == 1
    other = [
        p.name
        for p in _sources(*PACKAGES)
        if p.name != "format_config.py" and "read_only=False" in p.read_text(encoding="utf-8")
    ]
    assert other == []


def test_validation_and_analytics_contain_no_write_sql_or_loader_imports():
    for path in _sources(*PACKAGES):
        text = path.read_text(encoding="utf-8")
        if path.name == "format_config.py":  # the single, explicit model_versions registration
            continue
        assert not SQL_WRITE.search(text), f"write SQL found in {path.name}"
    for path in _sources(*PACKAGES):
        text = path.read_text(encoding="utf-8")
        assert "csv_loader" not in text and "ingestion_service" not in text, path.name


def test_cricsheet_validation_module_has_no_database_write_path():
    text = (APP / "validation" / "cricsheet_super_over.py").read_text(encoding="utf-8")
    assert "import duckdb" not in text and "connect(" not in text
    assert "execute(" not in text and ".to_sql" not in text and "INSERT" not in text


def test_read_only_handle_refuses_writes(tmp_path):
    dbp = tmp_path / "x.duckdb"
    db = connect(dbp)
    db.apply_persistent_schema()
    db.create_replaceable()
    db.close()
    ro = open_official_readonly(dbp)
    with pytest.raises(Exception):
        ro.execute("INSERT INTO teams VALUES (1, 'A', 't.csv', 1, 1)")
    ro.close()


# ------------------------------------------------------------------ synthetic contamination
def _synthetic_world(tmp_path):
    """Official DB with one IPL match, plus a Cricsheet-only match that is not in the DB."""
    root = tmp_path / "data"
    root.mkdir()
    (root / "official.csv").write_text("a\n1\n", encoding="utf-8")
    dbp = tmp_path / "o.duckdb"
    db = connect(dbp)
    db.apply_persistent_schema()
    db.create_replaceable()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    for tid in (1, 2):
        db.execute("INSERT INTO teams VALUES (?, ?, 't.csv', 1, 1)", [tid, f"Team {tid}"])
    for pid in (1, 2):
        db.execute(
            "INSERT INTO players VALUES (?, ?, 'MAPPING', NULL, true, true, true, false, false, "
            "'p.csv', 1)",
            [pid, f"P{pid}"],
        )
    db.execute(
        "INSERT INTO matches (match_id, comp_id, match_date, home_team_id, home_team, "
        "away_team_id, away_team, result_status, competition_type, has_deliveries, source_file, "
        "ingestion_run_id) VALUES (1, 1, DATE '2024-04-01', 1, 'Team 1', 2, 'Team 2', "
        "'COMPLETED', 'IPL', true, 'm.csv', 1)"
    )
    db.execute(
        "INSERT INTO innings VALUES (1, 1, 1, 2, true, 1, 1, 4, 0, 0, 4, 0, 1, 'STANDARD', "
        "'i.csv', 1, 1, 1)"
    )
    db.execute(
        "INSERT INTO deliveries (match_id, innings_number, innings_ball_num, batting_team_id, "
        "bowling_team_id, striker_id, bowler_id, is_wicket, batter_runs, extras_type, "
        "extras_primary_runs, is_legal_ball, legal_ball_status, extras_split_status, "
        "extras_label_unverified, source_file, source_row_no, ingestion_run_id) VALUES "
        "(1, 1, 1, 1, 2, 1, 2, false, 4, 'None', 0, true, 'X', 'NONE', false, 'd.csv', 1, 1)"
    )
    db.close()
    # Cricsheet-only match (different date and teams): must stay out of everything
    inn = {
        "team": "Ghost XI",
        "overs": [
            {
                "over": 0,
                "deliveries": [
                    {"batter": "G", "bowler": "H", "runs": {"batter": 6, "extras": 0, "total": 6}}
                ],
            }
        ],
    }
    d = root / "ipl_male_json"
    d.mkdir()
    (d / "777000.json").write_text(
        json.dumps(
            {
                "meta": {},
                "info": {"dates": ["2030-01-01"], "teams": ["Ghost XI", "Phantom XI"]},
                "innings": [inn, {**inn, "team": "Phantom XI"}],
            }
        ),
        encoding="utf-8",
    )
    return root, dbp


def test_cricsheet_only_match_never_enters_samples_or_validation_output(tmp_path):
    root, dbp = _synthetic_world(tmp_path)
    before = snapshot_official(dbp, root, ["ipl_male_json"])
    db = open_official_readonly(dbp)
    try:
        samples = extract_samples(db)
        official = so.load_official_matches(db)
        rep = dq.build_report(db)
    finally:
        db.close()
    sample_ids = set(samples.batter.match_id) | set(samples.bowler.match_id)
    assert sample_ids == {1}
    assert 777000 not in sample_ids
    recs = so.load_cricsheet_records(None, root, ("ipl_male_json",))
    assert [r["match_id"] for r in recs] == ["777000"]
    res = so.validate_super_overs(official, recs, root)
    assert res["converse_check"]["official_missing_super_over"] == []
    assert res["converse_check"]["mapping_status_counts"] == {so.NOT_FOUND: 1}
    assert res["cricsheet_loaded_into_database"] is False
    assert "777000" not in json.dumps(
        [e["recomputed_count"] for e in rep["issue_register"]["entries"]]
    )
    db = connect(dbp, read_only=True)
    tables = {r[0] for r in db.query("SELECT table_name FROM information_schema.tables")}
    assert db.scalar("SELECT count(*) FROM matches WHERE match_id = 777000") == 0
    assert db.scalar("SELECT count(*) FROM deliveries WHERE match_id = 777000") == 0
    db.close()
    assert not any("cricsheet" in t.lower() or t.lower().startswith("validation_") for t in tables)
    assert assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"])) == {}


def test_validation_and_dq_leave_synthetic_official_data_unchanged(tmp_path):
    root, dbp = _synthetic_world(tmp_path)
    before = snapshot_official(dbp, root, ["ipl_male_json"])
    db = open_official_readonly(dbp)
    try:
        so.validate_super_overs(
            so.load_official_matches(db),
            so.load_cricsheet_records(None, root, ("ipl_male_json",)),
            root,
        )
        dq.build_report(db)
    finally:
        db.close()
    assert assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"])) == {}


def test_snapshot_detects_a_tampered_csv_and_cricsheet_file(tmp_path):
    root, dbp = _synthetic_world(tmp_path)
    before = snapshot_official(dbp, root, ["ipl_male_json"])
    (root / "official.csv").write_text("a\n2\n", encoding="utf-8")
    diff = assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"]))
    assert any("official.csv" in k for k in diff)
    (root / "official.csv").write_text("a\n1\n", encoding="utf-8")
    (root / "ipl_male_json" / "777001.json").write_text("{}", encoding="utf-8")
    diff = assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"]))
    assert any("cricsheet" in k for k in diff)


# ------------------------------------------------------------------------------- real data
def _real():
    s = Settings()
    if not s.duckdb_path.exists() or not (s.data_root / "updated_ball_by_ball.csv").exists():
        pytest.skip("real database or official CSVs not available")
    return s


@pytest.mark.realdata
def test_real_db_has_no_cricsheet_tables_and_reports_use_official_match_ids():
    s = _real()
    db = connect(s.duckdb_path, read_only=True)
    try:
        tables = {r[0] for r in db.query("SELECT table_name FROM information_schema.tables")}
        official_ids = {r[0] for r in db.query("SELECT match_id FROM matches")}
    finally:
        db.close()
    assert not any("cricsheet" in t.lower() or t.lower().startswith("validation_") for t in tables)
    path = s.phase25_reports_dir / "cricsheet_super_over_validation.json"
    if path.exists():
        rep = json.loads(path.read_text(encoding="utf-8"))
        ids = {m["match_id"] for m in rep["matches"]}
        ids |= {c["match_id"] for c in rep["converse_check"]["official_missing_super_over"]}
        assert ids <= official_ids
        assert rep["cricsheet_loaded_into_database"] is False
        assert rep["official_data_modified"] is False
    for name in (
        "eligibility_distribution",
        "eligibility_threshold_experiment",
        "format_weight_sensitivity",
        "cricsheet_super_over_validation",
        "data_quality_impact_report",
    ):
        p = s.phase25_reports_dir / f"{name}.json"
        if p.exists():
            r = json.loads(p.read_text(encoding="utf-8"))
            assert r["proxy_run"] is True and r["pressure_status"] == "PENDING_PHASE3", name


@pytest.mark.realdata
def test_real_validation_scripts_leave_official_data_unchanged(tmp_path):
    s = _real()
    before = snapshot_from_settings(s, s.duckdb_path)
    for name in ("validate_super_overs", "assess_data_quality_impact"):
        rc = _load_script(name).main(["--reports-dir", str(tmp_path)])
        assert rc == 0, name
    assert assert_unchanged(before, snapshot_from_settings(s, s.duckdb_path)) == {}
    assert (tmp_path / "cricsheet_super_over_validation.json").exists()
    assert (tmp_path / "data_quality_impact_report.json").exists()


@pytest.mark.realdata
def test_real_full_phase25_run_on_a_copy_preserves_official_data(tmp_path):
    s = _real()
    copy_db = tmp_path / "copy.duckdb"
    shutil.copy(s.duckdb_path, copy_db)
    real_before = snapshot_from_settings(s, s.duckdb_path)
    rc = _load_script("run_phase2_5").main(
        ["--db", str(copy_db), "--reports-dir", str(tmp_path / "reports"), "--n-boot", "20"]
    )
    assert rc == 0
    pres = json.loads((tmp_path / "reports" / "phase25_preservation.json").read_text("utf-8"))
    assert pres["unchanged"] is True and pres["all_steps_succeeded"] is True
    assert pres["cricsheet_loaded_into_database"] is False
    assert assert_unchanged(real_before, snapshot_from_settings(s, s.duckdb_path)) == {}
    db = connect(copy_db, read_only=True)
    tables = {r[0] for r in db.query("SELECT table_name FROM information_schema.tables")}
    db.close()
    assert not any("cricsheet" in t.lower() or t.lower().startswith("validation_") for t in tables)
