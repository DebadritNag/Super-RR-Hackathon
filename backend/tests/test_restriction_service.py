"""Stage 7/8 tests: metric-level application of the data-quality restriction register.
EXPLORATORY code; nothing here is a validated pressure result."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.analytics import feature_registry as fr
from app.services import pressure_service as ps
from app.services import restriction_service as rs
from app.validation.restrictions import load_restrictions

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
CFG = load_restrictions()
APPLIER = rs.RestrictionApplier(CFG)


def _frame(**over) -> pd.DataFrame:
    base = {
        "match_id": [1, 1, 1, 2, 2],
        "innings_number": [1, 2, 3, 4, 2],
        "striker_id": [10, 11, 12, 13, 14],
        "bowler_id": [20, 21, 22, 23, 24],
        "out_extras_type": ["None", "other", "Penalty", "wide", "None"],
        "out_extras_primary_runs": [0, 1, 5, 1, 0],
        "out_extras_secondary_runs": [0, 0, 0, 0, 2],
        "out_is_wicket": [False, True, False, False, False],
        "out_dismissed_player_id": [None, None, 12, None, None],
        "dq_cricsheet_total_disagreement_innings": [False, False, False, False, True],
        "dls_match_flag": [False, False, False, False, True],
        "dls_exclude_primary": [False, False, False, False, True],
        "exclusion_reason_code": [None, None, "UNVERIFIED_INNINGS_ROLE", None, None],
        "aux_no_xi": [False] * 5,
        "aux_no_result": [False] * 5,
        "aux_striker_not_in_squad": [False] * 5,
        "aux_bowler_not_in_squad": [False] * 5,
    }
    base.update(over)
    return pd.DataFrame(base)


def test_register_has_26_rules_all_implemented_and_no_global_exclusion():
    assert len(CFG["restrictions"]) == 26 and CFG["global_exclusion"] is False
    assert set(rs.RULE_IMPLEMENTATIONS) == {r["rule_id"] for r in CFG["restrictions"]}


def test_missing_implementation_fails_loudly(monkeypatch):
    monkeypatch.delitem(rs.RULE_IMPLEMENTATIONS, "RULE_UTC_SUFFIX")
    with pytest.raises(rs.RestrictionViolation):
        rs.RestrictionApplier(CFG)


def test_innings_3_4_excluded_from_regulation_pressure_metrics_rows_preserved():
    df = _frame()
    for m in ("batter_pressure_sample", "bowler_pressure_sample", "pressure_state_label"):
        assert APPLIER.mask_for(m, df).tolist() == [False, False, True, True, False]
    kept = APPLIER.apply("batter_pressure_sample", df)
    assert len(df) == 5 and kept.innings_number.tolist() == [1, 2, 2]


def test_metric_without_exclude_rule_is_unrestricted():
    assert not APPLIER.mask_for("match_coverage_denominators", _frame()).any()


def test_unknown_extras_never_silently_zero():
    df = _frame(out_extras_type=["None", "other", "Penalty", "None", "None"], out_extras_secondary_runs=[0] * 5,
                out_extras_primary_runs=[0, 1, 5, 2, 0])  # fmt: skip
    cat = rs.extras_category(df)
    assert cat.tolist() == ["None", "other", "Penalty", "None_with_runs", "None"]
    assert (cat[[1, 2]] != "None").all()


def test_penalty_excluded_from_ball_metrics_but_other_only_has_sensitivity():
    df = _frame()
    assert APPLIER.mask_for("bowler_legal_balls", df)[2]  # Penalty
    assert not APPLIER.mask_for("bowler_legal_balls", df)[1]  # other kept in primary
    kinds = {v["rule_id"]: v["kind"] for v in APPLIER.variants_for("bowler_legal_balls")}
    assert kinds["RULE_EXTRAS_OTHER"] == "REPORT_WITH_SENSITIVITY"
    v = next(
        x for x in APPLIER.variants_for("bowler_legal_balls") if x["rule_id"] == "RULE_EXTRAS_OTHER"
    )
    assert APPLIER.variant_drop_mask(v, df).tolist() == [False, True, False, False, False]


def test_secondary_extras_field_guard():
    with pytest.raises(rs.RestrictionViolation):
        APPLIER.guard_field("bowler_economy", "extras_secondary_runs")
    APPLIER.guard_field("bowler_economy", "out_extras_primary_runs")  # allowed


def test_wicket_flag_disagreement_handled_for_dismissal_metrics_only():
    df = _frame(out_is_wicket=[False, False, False, True, False],
                out_dismissed_player_id=[None, 11, None, None, None])  # fmt: skip
    assert APPLIER.rule_mask("RULE_DISMISSED_NO_FLAG", df).tolist() == [False, True] + [False] * 3
    assert APPLIER.rule_mask("RULE_WICKET_NO_DISMISSED", df).tolist() == [False] * 3 + [True, False]
    # state-type metric untouched
    assert not APPLIER.mask_for("pressure_state_label", df.assign(innings_number=1)).any()
    assert not APPLIER.wicket_label(df)[1] and APPLIER.wicket_label(df, True)[1]
    assert "RULE_DISMISSED_NO_FLAG" in {
        r["rule_id"] for r in APPLIER.variants_for("batter_dismissal_rate")
    }
    assert APPLIER.mask_for("batter_dismissal_rate", df)[3]  # wicket without dismissed excluded


def test_dls_requires_revised_state_and_diagnostic_variant_only():
    df = _frame()
    assert APPLIER.require_revised_state(df).tolist() == [False] * 4 + [True]
    kinds = [v["kind"] for v in APPLIER.variants_for("chase_target_features")]
    assert "DIAGNOSTIC" in kinds
    assert not APPLIER.mask_for("chase_target_features", df.assign(innings_number=2)).any()


def test_name_join_forbidden_player_id_join_allowed():
    with pytest.raises(rs.RestrictionViolation):
        APPLIER.assert_no_name_join("player_id", "player_name")
    APPLIER.assert_no_name_join("player_id")


def test_duplicate_squad_records_do_not_multiply_samples():
    df = pd.DataFrame({"match_id": [1, 1, 2], "striker_id": [10, 10, 11]})
    squad = pd.DataFrame({"match_id": [1, 1, 2], "team_id": [5, 5, 6], "player_id": [10, 10, 11]})
    safe = APPLIER.safe_squad_join(df, squad, "striker_id")
    assert len(safe) == len(df)
    assert safe.groupby("striker_id").size().equals(df.groupby("striker_id").size())
    naive = df.merge(squad, left_on=["match_id", "striker_id"], right_on=["match_id", "player_id"])
    assert len(naive) > len(df)  # demonstrates the risk the guard removes


def test_squad_inference_guard():
    with pytest.raises(rs.RestrictionViolation):
        APPLIER.guard_squad_inference("squad_membership_features")


def test_cricsheet_totals_variant_drops_listed_innings_only():
    df = _frame()
    v = next(
        x for x in APPLIER.variants_for("bowler_economy") if x["rule_id"] == "RULE_CRICSHEET_TOTALS"
    )
    assert APPLIER.variant_drop_mask(v, df).tolist() == [False] * 4 + [True]
    assert not APPLIER.mask_for("bowler_economy", df.assign(innings_number=1))[4]


def test_ledger_counts_rule_by_metric():
    led = APPLIER.ledger(_frame().assign(den_bowler_counts_row=True))
    row = led[(led.rule_id == "RULE_INNINGS_3_4") & (led.metric == "bowler_economy")].iloc[0]
    assert row.rows_excluded == 2 and row.matches_affected == 2
    assert set(led.rule_id) == set(RULE_IDS())


def RULE_IDS():
    return [r["rule_id"] for r in CFG["restrictions"]]


# ---------------------------------------------------------------- feature registry
def test_every_feature_has_availability_status_and_derived_rules():
    d = fr.build_dictionary(CFG)
    assert len({f["name"] for f in d}) == len(d)
    for f in d:
        assert f["availability"] in fr.AVAILABILITY and f["status"] == "EXPLORATORY_NOT_VALIDATED"
        assert f["formula"] and f["definition"]
        for r in f["restriction_rules"]:
            assert r in {x["rule_id"] for x in CFG["restrictions"]}
    unknown = {m for f in d for m in f["register_metrics"]} - set(CFG["metric_vocabulary"])
    assert not unknown


def test_outcome_and_post_match_features_are_never_pre_delivery():
    for f in fr.build_dictionary(CFG):
        if f["name"].startswith("out_") or f["availability"] in (fr.POST_MATCH, fr.POST_INNINGS):
            assert not f["pre_delivery"]


def test_registry_covers_every_state_store_column():
    import duckdb

    if not ps.EXPLORATORY_DB.exists():
        pytest.skip("exploratory store not built")
    con = duckdb.connect(str(ps.EXPLORATORY_DB), read_only=True)
    try:
        cols = {r[0] for r in con.execute("DESCRIBE exp_pre_delivery_state").fetchall()}
        cols |= {r[0] for r in con.execute("DESCRIBE exp_pressure_signals").fetchall()}
    finally:
        con.close()
    technical = {"match_id", "innings_number", "innings_ball_num", "season_source", "phase_rule",
                 "target_source", "limit_source", "resource_status", "state_version",
                 "config_version", "status"}  # fmt: skip
    names = {f["name"] for f in fr.FEATURE_REGISTRY}
    missing = sorted(cols - names - technical)
    assert not missing, missing


# ---------------------------------------------------------------- deliverables
DELIVERABLES = ["pressure_framework_v1.md", "pressure_feature_dictionary.json",
                "pressure_distribution_report.md", "pressure_threshold_experiment.json",
                "pressure_eligibility_report.md", "baseline_methodology_v1.md",
                "phase3_data_quality_application_report.md"]  # fmt: skip


def test_all_seven_deliverables_exist_and_parse():
    for name in DELIVERABLES:
        p = REPORTS / name
        if not p.exists():
            pytest.skip(f"{name} not generated yet")
        text = p.read_text(encoding="utf-8")
        assert text.strip()
        if name.endswith(".json"):
            d = json.loads(text)
            assert d["status"] == "EXPLORATORY_NOT_VALIDATED" and d["official_ranking"] is False


def test_application_report_shows_invariants():
    p = REPORTS / "phase3_data_quality_application.json"
    if not p.exists():
        pytest.skip("application report not generated yet")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["global_exclusion"] is False and d["records_deleted"] == 0
    inv = d["invariants"]
    assert inv["register_rules"] == 26 and inv["official_unchanged"]
    assert not inv["innings_3_4_rows_in_pressure_population"]
    assert inv["other_penalty_mapped_to_none"] == 0 and inv["xi_counts_identical"]
