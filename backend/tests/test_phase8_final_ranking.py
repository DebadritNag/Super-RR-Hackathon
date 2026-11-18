"""Phase 8 final ranking: selection rule, status labels, ordering, eligibility, outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase8 import explain, ranking, selection, status
from app.phase8.constants import CRITERIA_FILE, CRITERIA_HASH_FILE, PHASE8_DB, REPORTS_DIR
from app.phase8.criteria import load_criteria, verify_criteria
from app.phase8.sensitivity import consistency_rank, window_overlap
from app.phase8.stability import point_ranking

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------------------------
# approach selection (approach-level metrics only)
# ---------------------------------------------------------------------------------------------
def _m(sb, low, oot_low=0.0, conc=0, expl=2):
    return {"sb": sb, "sb_low": low, "oot": 0.0, "oot_low": oot_low, "concentration": conc,
            "explainability": expl, "n_split": 100, "n_oot": 50}  # fmt: skip


def test_selection_takes_highest_positive_lower_bound():
    d = selection.select_approach({"A": _m(0.6, 0.3), "B": _m(0.7, 0.1), "C": _m(0.5, 0.05)})
    assert d["chosen"] == "A" and d["path"] == "HIGHEST_SPLIT_HALF_LOWER_BOUND"
    assert d["list_status_cap"] is None


def test_selection_within_margin_uses_out_of_time_then_concentration():
    d = selection.select_approach(
        {"A": _m(0.6, 0.30, oot_low=0.1), "B": _m(0.6, 0.27, oot_low=0.4), "C": _m(0.3, 0.1)}
    )
    assert d["chosen"] == "B"  # within 0.05 of the best lower bound, higher out-of-time bound
    d2 = selection.select_approach(
        {"A": _m(0.6, 0.30, 0.2, conc=1), "B": _m(0.6, 0.30, 0.2, conc=4), "C": _m(0.3, 0.1)}
    )
    assert d2["chosen"] == "B"
    d3 = selection.select_approach({"A": _m(0.6, 0.30, 0.2, 3, 2), "B": _m(0.6, 0.30, 0.2, 3, 3)})
    assert d3["chosen"] == "B"
    d4 = selection.select_approach({"B": _m(0.6, 0.30, 0.2, 3, 2), "A": _m(0.6, 0.30, 0.2, 3, 2)})
    assert d4["chosen"] == "A"  # id order is the last tie-break


def test_selection_without_positive_lower_bound_is_exploratory_highest_point_estimate():
    d = selection.select_approach({"A": _m(0.06, -0.2), "B": _m(0.04, -0.3), "C": _m(0.27, -0.08)})
    assert d["chosen"] == "C"
    assert d["path"] == "NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE"
    assert d["list_status_cap"] == "EXPLORATORY"


def test_selection_reports_when_the_two_paths_differ():
    d = selection.select_approach(
        {"A": _m(0.05, -0.10, oot_low=0.1), "B": _m(0.04, -0.12, oot_low=0.0), "C": _m(0.30, -0.5)}
    )
    assert d["point_estimate_path"] == "C" and d["lower_bound_path"] == "A"
    assert d["chosen"] == "C" and not d["paths_agree"]


def test_selection_refuses_player_level_inputs():
    bad = {"A": {**_m(0.1, 0.0), "player_id": 7}}
    with pytest.raises(selection.SelectionError):
        selection.select_approach(bad)
    with pytest.raises(selection.SelectionError):
        selection.select_approach({"Z": _m(0.1, 0.0)})
    with pytest.raises(selection.SelectionError):
        selection.select_approach({})


# ---------------------------------------------------------------------------------------------
# status labels
# ---------------------------------------------------------------------------------------------
def _ls(sb, low, oot_low, floor=False, n_elig=200, n_split=100, n_oot=60):
    crit = load_criteria()
    met = {"sb": sb, "sb_low": low, "oot_low": oot_low, "n_split": n_split, "n_oot": n_oot}
    return status.list_status(crit, met, floor, n_elig)["status"]


def test_validated_only_when_every_declared_threshold_is_met():
    assert _ls(0.75, 0.55, 0.4) == "VALIDATED"
    assert _ls(0.75, 0.45, 0.4) == "PROVISIONAL"  # lower bound below 0.5
    assert _ls(0.65, 0.55, 0.4) == "PROVISIONAL"  # point estimate below 0.7
    assert _ls(0.75, 0.55, 0.2) == "PROVISIONAL"  # out-of-time bound not above 0.3
    assert _ls(0.55, 0.1, 0.1) == "PROVISIONAL"
    assert _ls(0.55, -0.1, 0.1) == "EXPLORATORY"
    assert _ls(0.45, 0.1, 0.1) == "EXPLORATORY"
    assert _ls(0.55, 0.1, -0.1) == "EXPLORATORY"


def test_floor_missing_values_and_small_samples_never_strengthen_the_label():
    assert _ls(0.9, 0.8, 0.8, floor=True) == "EXPLORATORY"
    assert _ls(0.9, 0.8, None) == "EXPLORATORY"
    assert _ls(0.9, None, 0.8) == "EXPLORATORY"
    assert _ls(0.9, 0.8, 0.8, n_split=10) == "EXPLORATORY"
    assert _ls(0.9, 0.8, 0.8, n_oot=10) == "EXPLORATORY"
    assert _ls(0.9, 0.8, 0.8, n_elig=9) == "INSUFFICIENT_EVIDENCE"


def test_row_status_never_exceeds_list_and_follows_the_declared_rules():
    rs = status.row_status
    assert rs("EXPLORATORY", "STRONG_SUBSTANTIAL", 0.99, True) == "EXPLORATORY"
    assert rs("PROVISIONAL", "STRONG_SUBSTANTIAL", 0.99, True) == "PROVISIONAL"
    assert rs("PROVISIONAL", "STRONG_SUBSTANTIAL", 0.10, True) == "EXPLORATORY"
    assert rs("VALIDATED", "STRONG_SUBSTANTIAL", 0.6, True) == "VALIDATED"
    assert rs("VALIDATED", "STRONG_LIMITED", 0.6, True) == "PROVISIONAL"
    assert rs("VALIDATED", "STRONG_SUBSTANTIAL", 0.3, True) == "PROVISIONAL"
    assert rs("VALIDATED", "STRONG_SUBSTANTIAL", 0.6, False) == "INSUFFICIENT_EVIDENCE"
    assert rs("INSUFFICIENT_EVIDENCE", "STRONG_SUBSTANTIAL", 0.9, True) == "INSUFFICIENT_EVIDENCE"
    assert rs("EXPLORATORY", None, None, True) == "EXPLORATORY"
    with pytest.raises(status.StatusError):
        rs("MAYBE", "STRONG_SUBSTANTIAL", 0.9, True)


def test_banner_names_the_status_and_never_claims_validation_for_exploratory():
    b = status.banner("EXPLORATORY", "batter", "REML_POSTERIOR", "x")
    assert b.startswith("EXPLORATORY") and "not a validated ranking" in b
    assert "not validated" in status.banner("PROVISIONAL", "bowler", "b", "x")
    assert "INSUFFICIENT" in status.banner("INSUFFICIENT_EVIDENCE", "bowler", "b", "x")


def test_label_file_defines_exactly_the_four_labels():
    labels = status.load_labels()
    assert set(labels["labels"]) == set(status.STATUS_ORDER)


# ---------------------------------------------------------------------------------------------
# ordering, tie-breaks, eligibility and shortfall
# ---------------------------------------------------------------------------------------------
def _frame(scores, ids=None, evidence="STRONG_SUBSTANTIAL", prob=0.6):
    ids = list(range(1, len(scores) + 1)) if ids is None else ids
    n = len(scores)
    return pd.DataFrame(
        {"player_id": ids, "player_name": [f"P{i}" for i in ids], "score": scores,
         "interval_low": np.asarray(scores) - 0.1, "interval_high": np.asarray(scores) + 0.1,
         "evidence_class": evidence, "top_k_prob": prob, "n_matches": 40, "matches_ipl": 20.0,
         "matches_t20i": 20.0, "rank_low": 1.0, "rank_high": 30.0, "n_units": 30,
         "n_innings1": 100.0, "n_innings2": 100.0, "rank": np.arange(1, n + 1)}
    )  # fmt: skip


def _ctx(role="batter"):
    return {"role": role, "interval_method": "m", "combination_basis": "FORMAT_COMBINATION_UNSUPPORTED_X",
            "min_matches": 8, "floor_cell": False, "definition_status": "INTENSITY_DEFINITION_NOT_VALIDATED",
            "data_version_hash": "h", "criteria_sha256": "c", "generated_at": "t"}  # fmt: skip


def _build(frame, label="EXPLORATORY", role="batter"):
    return ranking.build_list(frame, approach="A", role=role, list_label=label,
                              validation_label=label, rank_basis="REML_POSTERIOR",
                              ranks_by_approach={}, context=_ctx(role))  # fmt: skip


def test_ordering_is_descending_and_independent_of_input_order():
    rng = np.random.default_rng(3)
    scores = rng.normal(0, 1, 40)
    f = _frame(scores)
    a = _build(f)["top"]
    b = _build(f.sample(frac=1.0, random_state=9))["top"]
    assert list(a["player_id"]) == list(b["player_id"])
    assert list(a["rank"]) == list(range(1, 11))
    assert (np.diff(a["score"].to_numpy()) <= 0).all()


def test_exact_ties_break_by_player_id_but_close_values_do_not():
    f = _frame(
        [1.0, 1.0, 1.0, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2],
        ids=[9, 3, 5, 1, 2, 4, 6, 7, 8, 10, 11],
    )
    top = _build(f)["top"]
    assert list(top["player_id"][:3]) == [3, 5, 9]
    close = _frame(
        [1.0 + 1e-6, 1.0] + [0.1 * i for i in range(10, 0, -1)] * 1,
        ids=[50, 2] + list(range(100, 110)),
    )
    first = _build(close)["top"].iloc[0]
    assert first["player_id"] == 50  # a difference of 1e-6 beats the smaller id
    assert point_ranking(pd.Series([1.0, 1.0 + 1e-13], index=[7, 3]))[3] == 1


def test_duplicate_players_are_refused():
    f = _frame([1.0, 0.9, 0.8], ids=[1, 1, 2])
    with pytest.raises(ranking.RankingError):
        ranking.order_players(f, "score")


def test_fewer_than_ten_eligible_players_is_not_padded():
    f = _frame([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3])
    built = _build(f)
    assert len(built["top"]) == 7 and built["label"] == "INSUFFICIENT_EVIDENCE"
    assert built["shortfall"] and "7" in built["shortfall"]
    assert set(built["top"]["ranking_status"]) == {"INSUFFICIENT_EVIDENCE"}
    assert len(built["pool"]) == 7  # the candidate pool holds the remaining players


def test_exactly_ten_and_candidate_pool_are_separate():
    f = _frame(np.linspace(1, 0, 25))
    built = _build(f)
    assert len(built["top"]) == 10 and len(built["pool"]) == 10
    assert set(built["top"]["player_id"]).isdisjoint(built["pool"]["player_id"])
    assert list(built["pool"]["rank"]) == list(range(11, 21))


def test_exploratory_list_has_no_stronger_rows_and_output_invariants_hold():
    f = _frame(np.linspace(1, 0, 15))
    built = _build(f)
    out = ranking.to_output(built["top"], built, lambda r, role, ap: "x")
    ranking.check_output(out, "EXPLORATORY")
    assert set(out["ranking_status"]) == {"EXPLORATORY"}
    assert list(out.columns) == ranking.OUT_COLUMNS
    bad = out.copy()
    bad.loc[0, "ranking_status"] = "VALIDATED"
    with pytest.raises(ranking.RankingError):
        ranking.check_output(bad, "EXPLORATORY")
    gap = out.iloc[[0, 2]].copy()
    with pytest.raises(ranking.RankingError):
        ranking.check_output(gap, "EXPLORATORY")


def test_row_statuses_in_a_provisional_list_follow_the_inclusion_probability():
    f = _frame(np.linspace(1, 0, 12))
    f["top_k_prob"] = [0.9, 0.8, 0.5, 0.3, 0.2, 0.1, 0.05, 0.9, 0.9, 0.9, 0.9, 0.9]
    top = _build(f, label="PROVISIONAL")["top"].sort_values("rank")
    assert list(top["ranking_status"][:7]) == ["PROVISIONAL"] * 4 + ["EXPLORATORY"] * 3
    assert "VALIDATED" not in set(top["ranking_status"])


def test_interval_flags_and_eligibility_flags():
    assert ranking.interval_flag(1.0, 0.8, 1.2) == "OK"
    assert ranking.interval_flag(1.0, 0.9, 2.5) == "ASYMMETRIC_UPPER_TAIL"
    assert ranking.interval_flag(1.0, -1.0, 1.1) == "ASYMMETRIC_LOWER_TAIL"
    assert ranking.interval_flag(3.0, 1.0, 2.0) == "POINT_OUTSIDE_INTERVAL"
    assert ranking.interval_flag(1.0, np.nan, 2.0) == "INTERVAL_UNAVAILABLE"
    r = pd.Series({"n_matches": 12, "matches_ipl": 12.0, "matches_t20i": np.nan})
    flags = ranking.eligibility_flags(r, 8)
    assert "MATCHES_BELOW_2X_FLOOR" in flags and "ONE_FORMAT_BELOW_HALF_FLOOR" in flags


def test_combined_frame_contribution_uses_match_counts_and_keeps_missing_scores_empty():
    est = pd.DataFrame(
        {"role": "batter", "scope": ["COMBINED", "COMBINED", "IPL"], "player_id": [1, 2, 1],
         "estimate": [0.2, 0.1, 0.3], "est_low": 0.0, "est_high": 0.4, "rank": [1, 2, 1],
         "sum_w": [10.0, 10.0, 6.0], "matches_ipl": [30.0, np.nan, np.nan],
         "matches_t20i": [10.0, 20.0, np.nan], "B": [0.2, 0.3, 0.1]}
    )  # fmt: skip
    f = ranking.combined_frame(est, "A", "batter").set_index("player_id")
    assert f.loc[1, "ipl_contribution"] == pytest.approx(0.75)
    assert f.loc[2, "ipl_contribution"] == 0.0 and f.loc[2, "t20i_contribution"] == 1.0
    assert f.loc[1, "ipl_score"] == pytest.approx(0.3)
    assert np.isnan(f.loc[1, "t20i_score"]) and np.isnan(f.loc[2, "ipl_score"])
    with pytest.raises(ranking.RankingError):
        ranking.combined_frame(est, "A", "bowler")


def test_csv_and_json_text_are_deterministic():
    f = _frame(np.linspace(1, 0, 12))
    built = _build(f)
    out = ranking.to_output(built["top"], built, lambda r, role, ap: "x")
    t1, t2 = ranking.csv_text(out), ranking.csv_text(out.copy())
    assert ranking.sha256_text(t1) == ranking.sha256_text(t2) and "\r" not in t1
    j1 = ranking.json_payload(out, {"b": 1, "a": 2})
    assert j1 == ranking.json_payload(out.copy(), {"a": 2, "b": 1})
    assert json.loads(j1)["rows"][0]["rank"] == 1


# ---------------------------------------------------------------------------------------------
# explanations never call a player poor for lacking evidence
# ---------------------------------------------------------------------------------------------
def test_below_floor_reason_states_counts_and_lack_of_evidence():
    r = pd.Series({"n_matches": 3, "balls": 20, "hi_units": 2, "failed_rules": "matches;balls;"})
    code, text = explain.reason_below_floor(r, "batter")
    assert code == "BELOW_ELIGIBILITY_FLOOR" and "3 matches" in text and "20 balls faced" in text
    assert "not a finding about the player's quality" in text
    assert not re.search(r"\bpoor|weak|bad\b", text)
    code2, text2 = explain.no_estimate_reason()
    assert code2 == "NO_PRESSURE_ESTIMATE" and "not zero" in text2


def test_eligible_reasons_use_the_declared_codes():
    r = pd.Series({"score": 0.02, "interval_high": 0.05, "top_k_prob": 0.1, "rank_low": 3.0,
                   "rank_high": 120.0, "evidence_class": "INCONSISTENT", "pos_share": 0.44,
                   "n_units": 30, "matches_ipl": 30.0, "matches_t20i": np.nan,
                   "pressure_perf_unshrunk": -0.01})  # fmt: skip
    got = {c for c, _ in explain.reasons_for_eligible(r, 0.03, 8, True)}
    assert got <= set(explain.REASON_CODES)
    assert {"LOW_TOP10_INCLUSION_PROBABILITY", "INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR",
            "INCONSISTENT_ACROSS_MATCHES", "ONE_FORMAT_ONLY_LOW_EVIDENCE",
            "HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT"} <= got  # fmt: skip
    plain = pd.Series({**r.to_dict(), "top_k_prob": 0.6, "evidence_class": "STRONG_SUBSTANTIAL",
                       "matches_t20i": 30.0})  # fmt: skip
    only = explain.reasons_for_eligible(plain, 0.03, 8, False)
    assert [c for c, _ in only] == ["INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR"]


def test_short_explanation_states_pressure_versus_baseline_direction():
    row = {"rank": 2, "pressure_score": 0.03, "pressure_innings_or_spells": 40.0,
           "pressure_deliveries": 600.0, "total_matches": 50.0, "observed_runs_per_ball": 1.8,
           "expected_runs_per_ball": 1.6, "observed_wicket_rate": 0.04,
           "expected_wicket_rate": 0.05, "normal_baseline": 0.2,
           "pressure_performance_unshrunk": 0.1, "pressure_delta": -0.1,
           "top10_inclusion_probability": 0.4, "rank_interval_low": 1.0, "rank_interval_high": 30.0,
           "evidence_class": "STRONG_SUBSTANTIAL", "ranking_status": "EXPLORATORY",
           "positive_unit_share": 0.55}  # fmt: skip
    t = explain.short_explanation(row, "batter", "A")
    assert "below the normal-play baseline" in t and "EXPLORATORY" in t
    t2 = explain.short_explanation({**row, "pressure_delta": 0.1}, "bowler", "C")
    assert "above the normal-play baseline" in t2 and "conceded" in t2


# ---------------------------------------------------------------------------------------------
# sensitivity helpers
# ---------------------------------------------------------------------------------------------
def _units(n_players=40, seed=2):
    rng = np.random.default_rng(seed)
    rows = []
    mid = 0
    for p in range(1, n_players + 1):
        skill = rng.normal(0, 0.5)
        for k in range(16):
            mid += 1
            rows.append({"player_id": p, "match_id": mid, "period": "TRAIN" if k < 10 else "VALIDATION",
                         "competition_type": "IPL" if k % 2 else "T20I",
                         "y": skill + rng.normal(0, 1), "prec": 5.0})  # fmt: skip
    return pd.DataFrame(rows)


def test_window_overlap_runs_on_each_window_and_flags_small_samples():
    u = _units()
    main = point_ranking(
        u.groupby("player_id").apply(
            lambda g: (g["y"] * g["prec"]).sum() / g["prec"].sum(), include_groups=False
        )
    )
    rows = window_overlap(u, main, "mean", {"TRAIN": 8, "VALIDATION": 4})
    assert [r["comparison"] for r in rows] == ["window_2022_2024", "window_2025"]
    assert all(r["n_common"] == 40 and -1 <= r["spearman"] <= 1 for r in rows)
    few = window_overlap(
        u[u["player_id"] <= 5], main.iloc[:5], "mean", {"TRAIN": 8, "VALIDATION": 4}
    )
    assert all(r["note"] == "NOT_ESTIMABLE_FEW_PLAYERS" for r in few)
    pos = window_overlap(u, main, "pos_share", {"TRAIN": 8, "VALIDATION": 4})
    assert all("spearman" in r for r in pos)
    with pytest.raises(ValueError):
        window_overlap(u, main, "bad", {"TRAIN": 8, "VALIDATION": 4})


def test_consistency_rank_orders_by_share_of_positive_units():
    u = _units()
    r = consistency_rank(u, np.arange(1, 41))
    assert len(r) == 40 and sorted(r.to_numpy()) == list(range(1, 41))


# ---------------------------------------------------------------------------------------------
# run order and guards in the script
# ---------------------------------------------------------------------------------------------
def test_every_stage_of_the_script_verifies_the_criteria_first():
    text = (ROOT / "scripts" / "phase8_final_ranking.py").read_text(encoding="utf-8")
    for stage in ("compare", "rank", "report"):
        assert re.search(rf'_begin\("{stage}"\)', text), stage
    assert 'begin_step(f"final_ranking_{stage}")' in text
    assert "evaluate_on_test" not in text and "read_csv" not in text


# ---------------------------------------------------------------------------------------------
# stored outputs (skipped when the pipeline has not been run)
# ---------------------------------------------------------------------------------------------
BAT_CSV = REPORTS_DIR / "pressure_batters_top10.csv"
BOW_CSV = REPORTS_DIR / "pressure_bowlers_top10.csv"
have = pytest.mark.skipif(
    not (PHASE8_DB.exists() and BAT_CSV.exists() and BOW_CSV.exists()),
    reason="final ranking outputs not built",
)


@have
@pytest.mark.parametrize("path,role", [(BAT_CSV, "batter"), (BOW_CSV, "bowler")])
def test_stored_lists_are_complete_labelled_and_consistent(path, role):
    d = pd.read_csv(path)
    assert list(d.columns) == ranking.OUT_COLUMNS
    assert list(d["rank"]) == list(range(1, len(d) + 1)) and len(d) <= 10
    assert d["player_id"].is_unique and set(d["role"]) == {role}
    assert set(d["ranking_status"]) <= set(status.STATUS_ORDER)
    assert set(d["model_validation_status"]) <= set(status.STATUS_ORDER)
    assert d["criteria_sha256"].nunique() == 1
    # no player is ranked with a stronger label than the list label
    lst = set(d["list_status"])
    assert len(lst) == 1
    order = {s: i for i, s in enumerate(status.STATUS_ORDER)}
    assert all(order[s] <= order[next(iter(lst))] for s in d["ranking_status"])
    assert d["pressure_score"].notna().all() and d["short_explanation"].str.len().min() > 50
    top = d["pressure_score"].to_numpy()
    assert (np.diff(top) <= 1e-12).all()


@have
def test_stored_lists_are_not_validated_because_no_declared_criterion_is_met():
    crit = load_criteria()
    import duckdb

    con = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        m = con.execute("SELECT * FROM p8_method_comparison WHERE chosen").df()
        st = con.execute("SELECT * FROM p8_top10_status").df()
    finally:
        con.close()
    for _, r in m.iterrows():
        met = {"sb": r["sb"], "sb_low": r["sb_low"], "oot_low": r["oot_low"],
               "n_split": r["n_split"], "n_oot": r["n_oot"]}  # fmt: skip
        label = status.list_status(
            crit, met, bool(r["between_player_variance_at_floor"]), int(r["n_eligible"])
        )["status"]
        stored = st[st["role"] == r["role"]].iloc[0]["list_status"]
        assert stored == label
        sb_ok = r["sb"] >= crit["status_thresholds"]["PROVISIONAL"]["split_half_min"]
        if not sb_ok:
            assert stored not in ("PROVISIONAL", "VALIDATED")


@have
def test_stored_json_twins_match_the_csv_files():
    for path, js in (
        (BAT_CSV, "pressure_batters_top10.json"),
        (BOW_CSV, "pressure_bowlers_top10.json"),
    ):
        d = pd.read_csv(path)
        j = json.loads((REPORTS_DIR / js).read_text(encoding="utf-8"))
        assert [r["player_id"] for r in j["rows"]] == list(d["player_id"])
        assert [r["rank"] for r in j["rows"]] == list(d["rank"])
        assert j["list_status"] == d["list_status"].iloc[0]
        assert j["banner"].startswith(j["list_status"]) or j["list_status"] in j["banner"]
        assert j["list_length"] == len(d)
        ids = {r["player_id"] for r in j["candidate_pool"]}
        assert ids.isdisjoint(set(d["player_id"]))


@have
def test_stored_outputs_carry_the_verified_criteria_hash():
    info = verify_criteria(CRITERIA_FILE, CRITERIA_HASH_FILE, PHASE8_DB)
    for p in (BAT_CSV, BOW_CSV):
        assert set(pd.read_csv(p)["criteria_sha256"]) == {info["sha256"]}


@have
def test_status_document_has_banner_and_both_statuses():
    text = (REPORTS_DIR / "pressure_top10_status.md").read_text(encoding="utf-8")
    assert text.lstrip().startswith("# Pressure Top 10")
    assert "> **Batters:" in text and "> **Bowlers:" in text
    assert "submitted ranking status" in text and "model validation status" in text
    assert "VALIDATED ranking" not in text.split("## 6.")[0]
