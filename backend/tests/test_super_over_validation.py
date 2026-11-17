"""Cricsheet Super Over validation: mapping, classification and preservation (validation-only)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.analytics.integrity import snapshot_official
from app.core.config import Settings
from app.core.database import connect
from app.data_pipeline.cricsheet_auditor import normalise_team, summarise_innings
from app.validation import cricsheet_super_over as so

DIRS = ("ipl_male_json", "t20s_male_json", "india_male_json")


# ------------------------------------------------------------------ synthetic data builders
def _d(bat=0, extra=None, wk=False):
    d = {
        "batter": "B1",
        "bowler": "W1",
        "non_striker": "B2",
        "runs": {
            "batter": bat,
            "extras": 1 if extra else 0,
            "total": bat + (1 if extra else 0),
        },
    }
    if extra:
        d["extras"] = {extra: 1}
    if wk:
        d["wickets"] = [{"player_out": "B1", "kind": "bowled"}]
    return d


def _inn(team, deliveries, super_over=False):
    inn = {"team": team, "overs": [{"over": 0, "deliveries": deliveries}]}
    if super_over:
        inn["super_over"] = True
    return inn


def base_innings(a="Alpha XI", b="Beta XI"):
    return [
        _inn(a, [_d(1), _d(2), _d(0)]),
        _inn(b, [_d(1), _d(0), _d(0, wk=True)]),
        _inn(a, [_d(4), _d(1, "wides")], super_over=True),
        _inn(b, [_d(6)], super_over=True),
    ]


def write_match(root: Path, directory: str, mid: str, teams, date, innings, **info):
    d = Path(root) / directory
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "meta": {"data_version": "1.1.0"},
        "info": {
            "dates": [date],
            "teams": list(teams),
            "team_type": info.get("team_type", "club"),
            "event": {"name": info.get("event", "Indian Premier League")},
            "outcome": info.get("outcome", {"result": "tie", "eliminator": teams[0]}),
            "venue": "Test Ground",
        },
        "innings": innings,
    }
    (d / f"{mid}.json").write_text(json.dumps(data), encoding="utf-8")


def off_innings(num, cs_inn):
    s = summarise_innings(cs_inn)
    return {
        "innings_number": num,
        "batting_team": s["team"],
        "deliveries": s["deliveries"],
        "legal_balls": s["legal_balls"],
        "total": s["total"],
        "wickets": s["wickets"],
        "innings_role_status": "UNVERIFIED" if num > 2 else "STANDARD",
    }


def official(mid, date, home, away, innings, ctype="IPL"):
    return {
        "match_id": mid,
        "match_date": date,
        "competition_type": ctype,
        "comp_name": "Synthetic",
        "result_status": "TIED_DECIDED_BY_TIEBREAK",
        "result": "tie (Super Over)",
        "home_team": home,
        "away_team": away,
        "teams_key": "|".join(sorted((normalise_team(home), normalise_team(away)))),
        "innings": innings,
    }


def make_official(cs_innings, n=4, mid=1, date="2024-05-01", ctype="IPL"):
    return official(
        mid,
        date,
        "Alpha XI",
        "Beta XI",
        [off_innings(i + 1, cs_innings[i]) for i in range(n)],
        ctype,
    )


def run(tmp_path, off_matches):
    recs = so.load_cricsheet_records(None, tmp_path, DIRS)
    return so.finalize(so.validate_super_overs(off_matches, recs, tmp_path))


@pytest.fixture()
def world(tmp_path):
    inns = base_innings()
    write_match(tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    return tmp_path, inns


# ----------------------------------------------------------------------------- classification
def test_confirmed_when_everything_agrees(world):
    root, inns = world
    res = run(root, [make_official(inns)])
    m = res["matches"][0]
    assert m["mapping"]["status"] == so.MAPPED_UNIQUE
    assert m["classification"] == so.CONFIRMED
    assert m["reason_codes"] == []
    assert m["proposed_innings_role_status"] == "CONFIRMED_SUPER_OVER_BY_CRICSHEET"
    assert res["classification_counts"][so.CONFIRMED] == 1
    assert res["cricsheet_loaded_into_database"] is False
    assert res["official_data_modified"] is False


def test_unconfirmed_when_no_cricsheet_mapping(world):
    root, inns = world
    res = run(root, [make_official(inns, date="2024-05-02")])
    m = res["matches"][0]
    assert m["mapping"]["status"] == so.NOT_FOUND
    assert m["classification"] == so.UNCONFIRMED
    assert m["reason_codes"] == ["MAPPING_NOT_FOUND"]


def test_unconfirmed_when_mapping_is_ambiguous(world):
    root, inns = world
    write_match(root, "ipl_male_json", "9002", ("Beta XI", "Alpha XI"), "2024-05-01", inns)
    res = run(root, [make_official(inns)])
    m = res["matches"][0]
    assert m["mapping"]["status"] == so.MAPPED_AMBIGUOUS
    assert m["classification"] == so.UNCONFIRMED
    assert sorted(m["mapping"]["candidates"]) == ["9001", "9002"]


def test_unconfirmed_when_regulation_sanity_fails_even_if_super_over_agrees(world):
    root, inns = world
    off = make_official(inns)
    off["innings"][1]["total"] += 7  # regulation innings 2 disagrees
    res = run(root, [off])
    m = res["matches"][0]
    assert m["classification"] == so.UNCONFIRMED
    assert m["reason_codes"] == ["MAPPING_SANITY_FAILED"]
    assert "REG2_TOTAL_RUNS" in m["mapping"]["sanity"]["failures"]
    assert m["super_over_fields_agree_ignoring_sanity"] is True  # context only


def test_unconfirmed_when_competition_check_fails(world):
    root, inns = world
    res = run(root, [make_official(inns, ctype="T20I")])  # club match offered as a T20I
    m = res["matches"][0]
    assert m["mapping"]["sanity"]["competition_check"]["passed"] is False
    assert m["classification"] == so.UNCONFIRMED


def test_conflicting_when_cricsheet_has_no_super_over(tmp_path):
    inns = [dict(i) for i in base_innings()][:2]
    write_match(tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    off = make_official(base_innings())
    res = run(tmp_path, [off])
    m = res["matches"][0]
    assert m["classification"] == so.CONFLICTING
    assert m["reason_codes"] == ["NO_SUPER_OVER_IN_CRICSHEET"]
    assert m["proposed_innings_role_status"] == "CONFLICT_INNINGS_3_4"


def test_conflicting_when_super_over_count_differs(tmp_path):
    inns = base_innings()[:3]  # only one Super Over innings in Cricsheet
    write_match(tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    res = run(tmp_path, [make_official(base_innings())])
    m = res["matches"][0]
    assert m["classification"] == so.CONFLICTING
    assert any(r.startswith("SUPER_OVER_COUNT_MISMATCH") for r in m["reason_codes"])


def test_conflicting_when_super_over_order_or_totals_differ(tmp_path):
    inns = base_innings()
    inns[2], inns[3] = inns[3], inns[2]  # Beta bats first in the Super Over
    write_match(tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    res = run(tmp_path, [make_official(base_innings())])
    m = res["matches"][0]
    assert m["classification"] == so.CONFLICTING
    assert "POS1_BATTING_TEAM_MISMATCH" in m["reason_codes"]

    off = make_official(base_innings())
    off["innings"][3]["total"] += 1
    off["innings"][3]["wickets"] += 1
    write_match(
        tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", base_innings()
    )
    res2 = run(tmp_path, [off])
    codes = res2["matches"][0]["reason_codes"]
    assert "POS2_TOTAL_RUNS_MISMATCH" in codes and "POS2_WICKETS_MISMATCH" in codes
    assert res2["matches"][0]["classification"] == so.CONFLICTING


def test_unconfirmed_when_cricsheet_file_has_no_ball_data(tmp_path):
    inns = [{"team": "Alpha XI", "overs": []}, {"team": "Beta XI", "overs": []}]
    write_match(tmp_path, "ipl_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    res = run(tmp_path, [make_official(base_innings())])
    assert res["matches"][0]["reason_codes"] == ["CRICSHEET_NO_BALL_DATA"]
    assert res["matches"][0]["classification"] == so.UNCONFIRMED


# -------------------------------------------------------------------------------------- mapping
def test_classify_is_pure_and_never_relabels_input(world):
    root, inns = world
    off = make_official(inns)
    snapshot = copy.deepcopy(off)
    run(root, [off])
    assert off == snapshot
    assert all(i["innings_role_status"] != "SUPER_OVER" for i in off["innings"])


def test_same_cricsheet_id_in_two_directories_is_deduplicated(world):
    root, inns = world
    write_match(root, "india_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", inns)
    recs = so.load_cricsheet_records(None, root, DIRS)
    assert len(recs) == 2
    dd = so.dedupe_by_match_id(recs)
    assert list(dd) == ["9001"]
    assert dd["9001"]["directories"] == ["ipl_male_json", "india_male_json"]
    assert dd["9001"]["copies_agree"] is True
    res = so.validate_super_overs([make_official(inns)], recs, root)
    assert res["matches"][0]["mapping"]["status"] == so.MAPPED_UNIQUE  # not ambiguous
    assert res["cricsheet_context"]["ids_in_multiple_directories"] == 1


def test_disagreeing_copies_are_reported(world):
    root, inns = world
    other = base_innings()
    other[0]["overs"][0]["deliveries"][0]["runs"] = {"batter": 6, "extras": 0, "total": 6}
    write_match(root, "india_male_json", "9001", ("Alpha XI", "Beta XI"), "2024-05-01", other)
    res = run(root, [make_official(inns)])
    assert res["cricsheet_context"]["ids_with_disagreeing_copies"] == ["9001"]


def test_converse_check_reports_super_over_missing_from_official(world):
    root, inns = world
    off = make_official(inns, n=2)  # official has no innings 3/4
    res = run(root, [off])
    assert res["official_matches_with_innings_3_4"] == 0
    conv = res["converse_check"]
    assert conv["count"] == 1
    assert conv["official_missing_super_over"][0]["cricsheet_match_id"] == "9001"
    assert len(conv["official_missing_super_over"][0]["cricsheet_super_over_innings"]) == 2


def test_report_renders_and_states_validation_only(world):
    root, inns = world
    res = run(root, [make_official(inns)])
    res["preservation"] = {"unchanged": True}
    md = so.render_report(res)
    assert "Validation only" in md and "PENDING_PHASE3" in md
    assert "CONFIRMED_SUPER_OVER_BY_CRICSHEET" in md


# ------------------------------------------------------------------------ database interaction
def _db_with_super_over(path):
    db = connect(path)
    db.apply_persistent_schema()
    db.create_replaceable()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    for tid, name in ((1, "Alpha XI"), (2, "Beta XI")):
        db.execute("INSERT INTO teams VALUES (?, ?, 't.csv', 1, 1)", [tid, name])
    db.execute(
        "INSERT INTO matches (match_id, comp_id, match_date, home_team_id, home_team, "
        "away_team_id, away_team, result_status, competition_type, has_deliveries, source_file, "
        "ingestion_run_id) VALUES (1, 1, DATE '2024-05-01', 1, 'Alpha XI', 2, 'Beta XI', "
        "'TIED_DECIDED_BY_TIEBREAK', 'IPL', true, 'm.csv', 1)"
    )
    for num, bat, bowl, n, tot, wk in (
        (1, 1, 2, 3, 3, 0),
        (2, 2, 1, 3, 1, 1),
        (3, 1, 2, 2, 6, 0),
        (4, 2, 1, 1, 6, 0),
    ):
        db.execute(
            "INSERT INTO innings VALUES (1, ?, ?, ?, true, ?, ?, 0, 0, 0, ?, ?, 1, 'UNVERIFIED', "
            "'i.csv', 1, 1, 1)",
            [num, bat, bowl, n, n, tot, wk],
        )
    db.close()


def test_load_official_and_preservation_of_innings_role_status(world, tmp_path):
    root, inns = world
    dbp = tmp_path / "o.duckdb"
    _db_with_super_over(dbp)
    before = snapshot_official(dbp, tmp_path, include_db_file_hash=True)
    db = connect(dbp, read_only=True)
    off = so.load_official_matches(db)
    db.close()
    assert [i["innings_number"] for i in off[0]["innings"]] == [1, 2, 3, 4]
    res = run(root, off)
    assert res["matches"][0]["proposed_innings_role_status"] in set(so.PROPOSED_STATUS.values())
    after = snapshot_official(dbp, tmp_path, include_db_file_hash=True)
    assert before == after  # validation never writes
    db = connect(dbp, read_only=True)
    statuses = {r[0] for r in db.query("SELECT innings_role_status FROM innings")}
    tables = {r[0] for r in db.query("SELECT table_name FROM information_schema.tables")}
    db.close()
    assert statuses == {"UNVERIFIED"}
    assert not any("cricsheet" in t.lower() or t.lower().startswith("validation_") for t in tables)


# ----------------------------------------------------------------------------- real data
@pytest.mark.realdata
def test_real_official_innings_3_4_are_classified_and_unchanged():
    s = Settings()
    if not s.duckdb_path.exists() or not (s.cricsheet_root / "ipl_male_json").is_dir():
        pytest.skip("real database or Cricsheet data not available")
    db = connect(s.duckdb_path, read_only=True)
    try:
        off = so.load_official_matches(db)
        expected = {
            r[0]
            for r in db.query("SELECT DISTINCT match_id FROM innings WHERE innings_number >= 3")
        }
        statuses = {
            r[0]
            for r in db.query(
                "SELECT DISTINCT innings_role_status FROM innings WHERE innings_number >= 3"
            )
        }
    finally:
        db.close()
    recs = so.load_cricsheet_records(
        s.staging_dir / "cricsheet_index.parquet", s.cricsheet_root, s.cricsheet_dirs
    )
    res = so.validate_super_overs(off, recs, s.cricsheet_root)
    assert {m["match_id"] for m in res["matches"]} == expected
    assert all(m["classification"] in so.CLASSES for m in res["matches"])
    assert sum(res["classification_counts"].values()) == len(expected)
    assert statuses == {"UNVERIFIED"}
