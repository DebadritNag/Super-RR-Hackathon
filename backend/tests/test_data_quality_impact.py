"""Data-quality impact register and the machine-readable restrictions."""

from __future__ import annotations

import copy
import json

import pytest

from app.core.config import Settings
from app.core.database import connect
from app.validation import data_quality_impact as dq
from app.validation.restrictions import (
    RESTRICTIONS_PATH,
    RestrictionsError,
    load_restrictions,
    restrictions_for_metric,
    validate_restrictions,
)

CFG = load_restrictions()
OPEN_CHECKS = [
    "open_playing_eleven_repeated_keys",
    "open_matches_without_playing_eleven_rows",
    "open_playing_eleven_rows_without_mapping_row",
    "open_delivery_striker_not_in_match_squad",
    "open_delivery_bowler_not_in_match_squad",
    "open_dismissed_player_without_wicket_flag",
    "open_wicket_without_dismissed_player",
    "open_extras_type_other_label_unverified",
    "open_extras_type_Penalty_label_unverified",
    "open_extras_secondary_split_unverified",
    "open_innings_3_4_role_unverified",
    "open_man_of_the_match_zero_sentinel",
    "open_delivery_time_utc_suffix_vs_ist_column_name",
    "open_delivery_time_midnight_rows",
    "open_duplicate_player_names_with_different_ids",
    "open_cricsheet_innings_total_disagreements",
    "open_matches_not_linkable_to_cricsheet",
]
INFO_CHECKS = [
    "reconcile_matches_without_deliveries",
    "result_status_distribution",
    "competition_type_distribution",
    "ipl_competitions_not_format_T20",
    "comparison_columns_that_differ",
]
ENTRY_KEYS = {
    "issue_id",
    "check_name",
    "source",
    "category",
    "db_severity",
    "db_status",
    "db_affected_rows",
    "recomputed_count",
    "count_agrees_with_db",
    "share_of_deliveries",
    "share_of_matches",
    "share_of_players",
    "classification",
    "justification",
    "affects",
    "restriction",
    "handling",
    "implementing_phase",
    "resolvable_with_evidence",
    "blocking_detail",
}


def _dq_row(db, run_id, check, status, affected=None):
    db.execute(
        "INSERT INTO data_quality_results (run_id, check_name, category, severity, status, "
        "expected, observed, affected_rows, details) VALUES (?, ?, 'TEST', 'WARNING', ?, NULL, "
        "'obs', ?, NULL)",
        [run_id, check, status, affected],
    )


def _seed(extra_open=(), other_rows=0, stored_other=None):
    db = connect(":memory:")
    db.apply_persistent_schema()
    db.create_replaceable()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    for tid in (1, 2):
        db.execute("INSERT INTO teams VALUES (?, ?, 't.csv', 1, 1)", [tid, f"T{tid}"])
    for pid in (1, 2):
        db.execute(
            "INSERT INTO players VALUES (?, ?, 'MAPPING', NULL, true, true, true, false, false, "
            "'p.csv', 1)",
            [pid, f"P{pid}"],
        )
    db.execute(
        "INSERT INTO matches (match_id, comp_id, match_date, home_team_id, away_team_id, "
        "result_status, competition_type, has_deliveries, source_file, ingestion_run_id) VALUES "
        "(1, 1, DATE '2024-04-01', 1, 2, 'COMPLETED', 'IPL', true, 'm.csv', 1)"
    )
    db.execute(
        "INSERT INTO innings VALUES (1, 1, 1, 2, true, 1, 1, 0, 0, 0, 0, 0, 1, 'STANDARD', "
        "'i.csv', 1, 1, 1)"
    )
    for n in range(1, other_rows + 4):
        db.execute(
            "INSERT INTO deliveries (match_id, innings_number, innings_ball_num, batting_team_id, "
            "bowling_team_id, striker_id, bowler_id, is_wicket, batter_runs, extras_type, "
            "extras_primary_runs, is_legal_ball, legal_ball_status, extras_split_status, "
            "extras_label_unverified, source_file, source_row_no, ingestion_run_id) VALUES "
            "(1, 1, ?, 1, 2, 1, 2, false, 0, ?, 0, true, 'X', 'NONE', false, 'd.csv', ?, 1)",
            [n, "other" if n <= other_rows else "None", n],
        )
    _dq_row(db, 1, "old_run_row_must_not_appear", "OPEN", 9)
    for c in OPEN_CHECKS:
        _dq_row(
            db,
            2,
            c,
            "OPEN",
            stored_other if c == "open_extras_type_other_label_unverified" else None,
        )
    for c in INFO_CHECKS:
        _dq_row(db, 2, c, "INFO")
    _dq_row(db, 2, "pk_unique_matches", "PASS", 0)
    for c in extra_open:
        _dq_row(db, 2, c, "OPEN", 1)
    return db


# --------------------------------------------------------------------------------- register
def test_every_open_and_info_row_is_registered_once():
    db = _seed()
    reg = dq.build_register(db, CFG)
    names = [e["check_name"] for e in reg["entries"] if e["source"] == "phase2_data_quality_table"]
    assert sorted(names) == sorted(OPEN_CHECKS + INFO_CHECKS)
    assert len(names) == len(set(names))
    assert reg["open_rows"] == 17 and reg["info_rows"] == 5
    assert "pk_unique_matches" not in names and "old_run_row_must_not_appear" not in names
    ids = [e["issue_id"] for e in reg["entries"]]
    assert len(ids) == len(set(ids))


def test_entry_schema_classification_enum_and_scoped_restriction():
    reg = dq.build_register(_seed(), CFG)
    for e in reg["entries"]:
        assert ENTRY_KEYS <= set(e)
        assert e["classification"] in dq.CLASSIFICATIONS
        assert set(e["affects"]) == {"calculations", "features", "labels", "models"}
        r = e["restriction"]
        assert r["global_exclusion"] is False
        assert r["rule_id"] and r["applies_to_metrics"], e["check_name"]
        assert e["handling"] and e["justification"]
        assert set(e["resolvable_with_evidence"]) == {"possible", "evidence_needed"}
        if e["classification"] == dq.BLOCKING:
            assert e["blocking_detail"]
        else:
            assert e["blocking_detail"] is None


def test_carried_over_issues_added_without_duplicating_register_rows():
    reg = dq.build_register(_seed(), CFG)
    carried = [e for e in reg["entries"] if e["source"] == "carried_over_phase1"]
    assert {e["check_name"] for e in carried} == {c for c, _, _ in dq.CARRIED}
    assert reg["carried_over_rows"] == len(dq.CARRIED)


def test_no_global_exclusion_and_nothing_deleted():
    db = _seed()
    before = db.scalar("SELECT count(*) FROM deliveries")
    rep = dq.build_report(db, CFG)
    assert rep["global_exclusion"] is False
    assert rep["records_deleted"] == 0 and rep["matches_excluded_globally"] == 0
    assert rep["proxy_run"] is True and rep["pressure_status"] == "PENDING_PHASE3"
    assert db.scalar("SELECT count(*) FROM deliveries") == before
    assert all(not e["restriction"]["global_exclusion"] for e in rep["issue_register"]["entries"])


def test_unassessed_row_is_blocking_with_detail():
    reg = dq.build_register(_seed(extra_open=["brand_new_check"]), CFG)
    e = next(x for x in reg["entries"] if x["check_name"] == "brand_new_check")
    assert e["classification"] == dq.BLOCKING
    assert e["blocking_detail"]
    assert reg["classification_counts"][dq.BLOCKING] == 1


def test_count_recomputation_agreement_flag_and_disagreement_blocks():
    agree = dq.build_register(_seed(other_rows=2, stored_other=2), CFG)
    e = next(x for x in agree["entries"] if x["check_name"].startswith("open_extras_type_other"))
    assert e["recomputed_count"] == 2 and e["count_agrees_with_db"] is True
    assert e["classification"] == dq.NON_BLOCKING
    assert e["share_of_deliveries"] == pytest.approx(2 / 5)

    clash = dq.build_register(_seed(other_rows=2, stored_other=5), CFG)
    e = next(x for x in clash["entries"] if x["check_name"].startswith("open_extras_type_other"))
    assert e["count_agrees_with_db"] is False
    assert e["classification"] == dq.BLOCKING
    assert "5" in e["blocking_detail"]


def test_perturbation_for_disagreeing_innings():
    db = _seed(other_rows=0)
    out = dq.perturbation(db, [{"match_id": 1, "innings": 1}, {"match_id": 1, "innings": 2}])
    assert out["innings"][0]["official_delivery_rows"] == 3
    assert out["batters"]["players_touched"] == 1
    assert out["batters"]["max_share_of_player_deliveries"] == pytest.approx(1.0)
    assert dq.perturbation(db, [])["batters"] is None


def test_report_renders_with_status_fields():
    db = _seed()
    rep = dq.build_report(db, CFG)
    rep["preservation"] = {"unchanged": True}
    md = dq.render_report(rep)
    assert "PENDING_PHASE3" in md and "Restrictions per metric" in md
    assert "no match is excluded globally" in md


# ------------------------------------------------------------------------------ restrictions
def test_restrictions_file_loads_and_is_never_global():
    assert RESTRICTIONS_PATH.exists()
    assert CFG["global_exclusion"] is False
    assert all(r["global_exclusion"] is False for r in CFG["restrictions"])


def test_restrictions_for_metric_lookup():
    rules = {r["rule_id"] for r in restrictions_for_metric("batter_balls_faced", CFG)}
    assert "RULE_INNINGS_3_4" in rules and "RULE_EXTRAS_PENALTY" in rules
    assert restrictions_for_metric("metric_nobody_restricts", CFG) == []
    ids = {r["rule_id"] for r in restrictions_for_metric("player_identity_join", CFG)}
    assert ids == {"RULE_DUPLICATE_NAMES"}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(global_exclusion=True),
        lambda c: c["restrictions"][0].update(global_exclusion=True),
        lambda c: c["restrictions"][0].update(applies_to_metrics=[]),
        lambda c: c["restrictions"][0].update(applies_to_metrics=["not_a_metric"]),
        lambda c: c["restrictions"][1].update(rule_id=c["restrictions"][0]["rule_id"]),
        lambda c: c["restrictions"][0].update(effect="DELETE_ROWS"),
    ],
)
def test_invalid_restrictions_rejected(mutate):
    bad = copy.deepcopy(CFG)
    mutate(bad)
    with pytest.raises(RestrictionsError):
        validate_restrictions(bad)


def test_register_rules_and_config_rules_are_consistent():
    rule_ids = {r["rule_id"] for r in CFG["restrictions"]}
    spec_rules = {s["rule_id"] for s in dq.SPECS.values()}
    assert spec_rules == rule_ids
    checked = {c for r in CFG["restrictions"] for c in r["issue_check_names"]}
    assert checked == set(dq.SPECS)
    # a rule must be attached to the issue that names it
    for check, spec in dq.SPECS.items():
        rule = next(r for r in CFG["restrictions"] if r["rule_id"] == spec["rule_id"])
        assert check in rule["issue_check_names"]


def test_restriction_matrix_lists_rules_per_metric():
    m = dq.restriction_matrix(CFG)
    assert set(m) == set(CFG["metric_vocabulary"])
    assert "RULE_INNINGS_3_4" in m["pressure_state_label"]
    json.dumps(m)


# --------------------------------------------------------------------------------- real data
@pytest.mark.realdata
def test_real_open_rows_are_all_registered():
    s = Settings()
    if not s.duckdb_path.exists():
        pytest.skip("real database not available")
    db = connect(s.duckdb_path, read_only=True)
    try:
        open_rows = {
            r[0]
            for r in db.query("SELECT check_name FROM v_latest_data_quality WHERE status = 'OPEN'")
        }
        info_rows = {
            r[0]
            for r in db.query("SELECT check_name FROM v_latest_data_quality WHERE status = 'INFO'")
        }
        reg = dq.build_register(db, CFG, s.audit_dir / "cricsheet_overlap_report.json")
    finally:
        db.close()
    assert len(open_rows) == 17
    registered = {e["check_name"] for e in reg["entries"]}
    assert open_rows <= registered and info_rows <= registered
    for e in reg["entries"]:
        assert e["count_agrees_with_db"] is not False, e["check_name"]
        assert e["classification"] in dq.CLASSIFICATIONS
        assert e["restriction"]["applies_to_metrics"]
    assert reg["classification_counts"][dq.BLOCKING] == 0
