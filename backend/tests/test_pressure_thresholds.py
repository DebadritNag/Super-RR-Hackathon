"""Stage 5 tests: pressure-specific eligibility thresholds, sample counts, selection rule,
ranking stability and independence of roles and formats. EXPLORATORY code; nothing is ranked."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.analytics import baseline_engine as be
from app.analytics import confidence_engine as ce
from app.analytics import pressure_distributions as pdist
from app.analytics import pressure_eligibility as pe
from app.analytics.proxy_samples import ProxySamples
from app.services import pressure_service as ps

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "pressure_eligibility_rules_v1.json").read_text("utf-8"))
REPORTS = ROOT / "data" / "reports"


# ---------------------------------------------------------------- synthetic samples
def _samples(seed: int = 0, bowler_shift: float = 0.0) -> ProxySamples:
    """Two formats, 40 batters and 40 bowlers each, 30 matches, 1-12 balls per (player, match)."""
    rng = np.random.default_rng(seed)
    brows, wrows = [], []
    for fmt in ("IPL", "T20I"):
        for role_rows, role in ((brows, "b"), (wrows, "w")):
            for pid in range(1, 41):
                base = (1000 if fmt == "T20I" else 0) + (0 if role == "b" else 500) + pid
                for m in rng.choice(30, size=int(rng.integers(3, 15)), replace=False):
                    n = int(rng.integers(1, 13))
                    r = rng.normal(0.05, 0.9, size=n)
                    w = rng.normal(0.0, 0.3, size=n) + bowler_shift
                    row = {
                        "format": fmt,
                        "player_id": base,
                        "match_id": int(m) + (100 if fmt == "T20I" else 0),
                        "n": n,
                        "legal_balls": n,
                        "innings": 1,
                    }
                    if role == "b":
                        row.update(runs_sum=float(r.sum()), runs_sum2=float((r**2).sum()))
                    else:
                        row.update(
                            econ_sum=float(r.sum()),
                            econ_sum2=float((r**2).sum()),
                            wkt_sum=float(w.sum()),
                            wkt_sum2=float((w**2).sum()),
                        )
                    role_rows.append(row)
    window = {"IPL": {"matches_with_deliveries": 30}, "T20I": {"matches_with_deliveries": 30}}
    return ProxySamples(pd.DataFrame(brows), pd.DataFrame(wrows), window, {}, [])


def _small_cfg() -> dict:
    cfg = dict(CFG)
    cfg["n_boot"] = 30
    return cfg


# ---------------------------------------------------------------- thresholds
def test_percentile_candidates_on_known_distribution():
    pc = ce.percentile_candidates(np.arange(1, 101), [10, 25, 50, 75])
    assert [c["value"] for c in pc] == [11, 26, 51, 76]  # ceil of numpy percentiles
    assert pc[0]["observed_value"] == pytest.approx(10.9)


def test_practical_ladder_keeps_only_rungs_between_observed_p10_and_p90():
    v = np.arange(1, 101)
    pc = ce.percentile_candidates(v, [25, 75])
    pr = ce.practical_candidates([2, 40, 90, 500], v, pc, 0.05)
    kept = {p["value"]: p["kept"] for p in pr}
    assert kept[2] is False and kept[500] is False and kept[40] is True
    assert pr[0]["drop_reason"] == "below_observed_p10"


def test_pressure_ladders_are_rescaled_below_all_situation_ladders():
    old = json.loads((ROOT / "config" / "eligibility_rules_v1.json").read_text("utf-8"))
    for role in ("batter", "bowler"):
        assert CFG["ladders"][role]["balls"][0] < old["ladders"][role]["balls"][0]
        assert max(CFG["ladders"][role]["balls"]) < max(old["ladders"][role]["balls"])
    assert CFG["status"] == "EXPLORATORY_NOT_VALIDATED"


def test_pool_verdict_fewer_than_ten_is_reported_and_never_padded():
    v = ce.pool_verdict(7, 10, 30, 3)
    assert v["fewer_than_list_size"] and not v["sufficient"] and "none is padded" in v["message"]
    ok = ce.pool_verdict(30, 10, 30, 3)
    assert ok["sufficient"] and not ok["fewer_than_list_size"]
    mid = ce.pool_verdict(15, 10, 30, 3)
    assert not mid["sufficient"] and not mid["fewer_than_list_size"]


def test_n_eff_formulas_kish_and_shrink():
    rows = pd.DataFrame({
        "player_id": [1, 1, 2], "match_id": [1, 2, 1], "n": [3, 1, 5], "legal_balls": [3, 1, 5],
        "innings": [1, 1, 1], "runs_sum": [0.3, 0.1, 0.2], "runs_sum2": [0.5, 0.1, 0.4],
    })  # fmt: skip
    t = ce.player_table(ce.Prepared(rows, "batter")).set_index("player_id")
    assert t.loc[1, "n_eff_kish"] == pytest.approx(16 / 10)  # (3+1)^2 / (9+1)
    assert t.loc[2, "n_eff_kish"] == pytest.approx(1.0)
    assert t.loc[1, "balls"] == 4 and t.loc[1, "matches"] == 2
    assert (t["n_eff_shrink"] > 0).all() and (t["n_eff_shrink"] <= t["balls"] + 1e-9).all()


# ---------------------------------------------------------------- independence
def test_batter_results_independent_of_bowler_samples():
    a = _samples(0)
    b = _samples(0)
    b.bowler["econ_sum"] = b.bowler["econ_sum"] * 3 + 1.0  # change bowlers only
    _, ea = ce.run_experiment(a, _small_cfg(), 30)
    _, eb = ce.run_experiment(b, _small_cfg(), 30)
    for fmt in ("IPL", "T20I"):
        assert json.dumps(ea["formats"][fmt]["batter"], sort_keys=True, default=str) == json.dumps(
            eb["formats"][fmt]["batter"], sort_keys=True, default=str
        )
        assert ea["formats"][fmt]["bowler"]["rules"] != eb["formats"][fmt]["bowler"]["rules"]


def test_ipl_results_independent_of_t20i_samples():
    a = _samples(1)
    b = _samples(1)
    m = b.batter["format"] == "T20I"
    b.batter.loc[m, "runs_sum"] = b.batter.loc[m, "runs_sum"] + 5.0
    _, ea = ce.run_experiment(a, _small_cfg(), 30)
    _, eb = ce.run_experiment(b, _small_cfg(), 30)
    ra = [(r["rule_id"], r["eligible"]) for r in ea["formats"]["IPL"]["batter"]["rules"]]
    rb = [(r["rule_id"], r["eligible"]) for r in eb["formats"]["IPL"]["batter"]["rules"]]
    assert ra == rb
    assert (
        ea["recommendation_inputs"]["IPL"]["batter"] == eb["recommendation_inputs"]["IPL"]["batter"]
    )


# ---------------------------------------------------------------- ranking stability
def test_bootstrap_resamples_matches_and_is_seed_reproducible():
    s = _samples(2)
    rows = s.batter[s.batter["format"] == "IPL"]
    prep = ce.Prepared(rows, "batter")
    m1 = ce.bootstrap_score_matrix(prep, np.random.default_rng(5), 20)
    m2 = ce.bootstrap_score_matrix(prep, np.random.default_rng(5), 20)
    m3 = ce.bootstrap_score_matrix(prep, np.random.default_rng(6), 20)
    assert np.array_equal(m1, m2) and not np.array_equal(m1, m3)
    # one single match: resampling matches always returns that match, so every row equals the base
    one = rows[rows["match_id"] == rows["match_id"].iloc[0]]
    p1 = ce.Prepared(one, "batter")
    mat = ce.bootstrap_score_matrix(p1, np.random.default_rng(1), 5)
    base = ce.score_from_agg("batter", p1.aggregate())["score"]
    assert np.allclose(mat, base[None, :])


def test_bootstrap_rule_reports_stability_for_eligible_set_only():
    s = _samples(3)
    prep = ce.Prepared(s.batter[s.batter["format"] == "IPL"], "batter")
    mat = ce.bootstrap_score_matrix(prep, np.random.default_rng(1), 40)
    full = ce.score_from_agg("batter", prep.aggregate())["score"]
    sel = np.zeros(prep.n_players, bool)
    sel[:15] = True
    r = ce.bootstrap_rule(matrix=mat, orig=full, sel=sel, k=10)
    assert r["eligible"] == 15 and 0 <= r["expected_top_k_overlap"] <= 10
    assert -1 <= r["spearman_vs_original_mean"] <= 1
    short = np.zeros(prep.n_players, bool)
    short[:4] = True
    r4 = ce.bootstrap_rule(mat, full, short, 10)
    assert r4["top_k"] == 4  # no padding to ten


def test_rule_uncertainty_is_aggregate_only_and_batter_has_zero_reference():
    s = _samples(4)
    prep = ce.Prepared(s.batter[s.batter["format"] == "IPL"], "batter")
    mask = np.ones(prep.n_players, bool)
    u = pe.rule_uncertainty(prep, mask, np.random.default_rng(1), 30, "batter")
    assert u["evaluated"] and 0 <= u["interval_excludes_zero_share"] <= 1
    assert not any(isinstance(v, (list, dict)) for v in u.values())  # no player listing
    pw = ce.Prepared(s.bowler[s.bowler["format"] == "IPL"], "bowler")
    ub = pe.rule_uncertainty(
        pw, np.ones(pw.n_players, bool), np.random.default_rng(1), 30, "bowler"
    )
    assert ub["interval_excludes_zero_share"] is None


# ---------------------------------------------------------------- pressure sample counts
def _frame():
    return pd.DataFrame({
        "competition_type": ["IPL"] * 6 + ["T20I"] * 3,
        "player_id": [1, 1, 1, 2, 2, 1, 3, 3, 3],
        "match_id": [10, 10, 11, 11, 11, 12, 20, 20, 21],
        "inn_key": [101, 101, 111, 111, 111, 121, 201, 201, 211],
        "den_legal_inc": [1, 0, 1, 1, 1, 1, 1, 1, 1],
        "den_counts_as_ball_faced": [1] * 9,
    })  # fmt: skip


def test_batter_pressure_samples_match_independent_pandas_count():
    d = _frame()
    flag = np.array([1, 1, 1, 1, 0, 1, 1, 0, 1], bool)
    res = np.arange(9, dtype=float) / 10
    out = pe.batter_samples(d, flag, res)
    sub = d[flag].assign(r=res[flag])
    exp = sub.groupby(["competition_type", "player_id", "match_id"]).agg(
        n=("r", "size"), s=("r", "sum"), s2=("r", lambda x: float((x**2).sum()))
    )
    got = out.set_index(["format", "player_id", "match_id"])
    assert got["n"].to_numpy().tolist() == exp["n"].to_numpy().tolist()
    assert np.allclose(got["runs_sum"], exp["s"]) and np.allclose(got["runs_sum2"], exp["s2"])
    assert got.loc[("IPL", 1, 10), "legal_balls"] == 1  # the non-legal row is a ball faced only
    # agrees with the Stage 3 counting function (same player and match totals)
    pc = pdist.player_counts(
        d.rename(columns={"player_id": "striker_id"}).assign(bowler_id=0, den_bowler_counts_row=1),
        flag,
        "batter",
    ).set_index("player_id")
    assert got.groupby("player_id")["n"].sum().to_dict() == pc["n"].to_dict()


def test_bowler_pressure_samples_carry_both_streams_and_legal_balls():
    d = _frame()
    flag = np.ones(9, bool)
    out = pe.bowler_samples(d, flag, np.full(9, 0.5), np.full(9, -0.1))
    row = out[(out["format"] == "IPL") & (out["player_id"] == 1) & (out["match_id"] == 10)].iloc[0]
    assert row["n"] == 2 and row["legal_balls"] == 1
    assert row["econ_sum"] == pytest.approx(1.0) and row["wkt_sum"] == pytest.approx(-0.2)
    assert row["econ_sum2"] == pytest.approx(0.5) and row["wkt_sum2"] == pytest.approx(0.02)


def test_samples_with_empty_flag_are_empty_not_zero_filled():
    d = _frame()
    out = pe.batter_samples(d, np.zeros(9, bool), np.zeros(9))
    assert len(out) == 0


def test_lpo_residual_leaves_own_deliveries_out():
    rng = np.random.default_rng(0)
    n = 60
    d = pd.DataFrame({
        "competition_type": "IPL", "role_ctx": "chase", "innings_phase": "death", "wbin": "a",
        "inn_key": np.repeat(np.arange(6), 10), "match_id": np.repeat(np.arange(6), 10),
        "player_id": np.tile([1, 2, 3, 4, 5], 12), "runs": rng.integers(0, 7, n).astype(float),
    })  # fmt: skip
    params = {"min_cell_innings": 1, "tau2_floor": 0.01}
    r = pe.lpo_residual(d, "runs", False, params)
    other = np.array([d.loc[d.player_id != p, "runs"].mean() for p in d.player_id])
    assert np.allclose(r, d["runs"].to_numpy() - other)


# ---------------------------------------------------------------- definitions and selection
def test_definition_grid_is_predeclared_and_complete():
    ds = pe.definitions(CFG)
    assert len(ds) == len(CFG["definition_grid"]["contexts"]) * len(CFG["definition_grid"]["q"])
    assert {d["ctx"] for d in ds} == {"chase", "inn1", "any"}


def test_definition_flag_any_is_union_of_chase_and_inn1_per_comp():
    n = 8
    flags = {}
    rng = np.random.default_rng(0)
    for ctx, sig in (("chase", "rrr"), ("inn1", "neg_par_dev")):
        for comp in ("IPL", "T20I"):
            flags[f"a|{ctx}|{comp}|batter|{sig}|abs|0.9"] = rng.random(n) > 0.5
    d_any = {"id": "any|q0.9", "ctx": "any", "q": 0.9, "view": "abs"}
    got = pe.definition_flag(flags, CFG, d_any, "batter")
    exp = np.zeros(n, bool)
    for k, v in flags.items():
        exp |= v
    assert np.array_equal(got, exp)
    d_ch = {"id": "chase|q0.9", "ctx": "chase", "q": 0.9, "view": "abs"}
    ch = pe.definition_flag(flags, CFG, d_ch, "batter")
    assert np.array_equal(
        ch, flags["a|chase|IPL|batter|rrr|abs|0.9"] | flags["a|chase|T20I|batter|rrr|abs|0.9"]
    )


def _res(def_id, ctx, q, rows, recs):
    """Result stub: recs maps (fmt, role) -> eligible players or None."""
    summary = {}
    for f in ("IPL", "T20I"):
        summary[f] = {}
        for r in ("batter", "bowler"):
            e = recs[(f, r)]
            summary[f][r] = {
                "pressure_unit_rows": rows,
                "recommended": None if e is None else {"eligible_players": e},
            }
    return {"definition": {"id": def_id, "ctx": ctx, "q": q}, "summary": summary}


def test_select_definition_highest_q_then_larger_population_and_population_only():
    ok = {(f, r): 40 for f in ("IPL", "T20I") for r in ("batter", "bowler")}
    bad = {**ok, ("T20I", "bowler"): None}
    results = [
        _res("chase|q0.75", "chase", 0.75, 100, ok),
        _res("chase|q0.9", "chase", 0.9, 50, ok),
        _res("any|q0.9", "any", 0.9, 80, ok),
        _res("inn1|q0.95", "inn1", 0.95, 999, bad),
    ]
    sel = pe.select_definition(results, CFG)
    assert sel["selected_id"] == "any|q0.9"  # same q as chase|q0.9, larger population wins
    assert sel["viable_count"] == 3
    assert sel["definitions_examined_in_experiment"] == 4
    assert "never used" in sel["rule"]
    none = pe.select_definition([_res("x", "chase", 0.9, 1, bad)], CFG)
    assert none["selected_id"] is None  # nothing is forced


def test_select_definition_does_not_depend_on_scores():
    ok = {(f, r): 40 for f in ("IPL", "T20I") for r in ("batter", "bowler")}
    a = _res("chase|q0.9", "chase", 0.9, 50, ok)
    b = json.loads(json.dumps(a))
    b["summary"]["IPL"]["batter"]["recommended"]["scores"] = [9, 8, 7]  # extra, must be ignored
    assert pe.select_definition([a], CFG)["table"] == pe.select_definition([b], CFG)["table"]


def test_combined_both_formats_counts_intersection_without_padding():
    tab = {
        ("IPL", "batter"): pd.DataFrame({"player_id": [1, 2, 3], "balls": [30, 30, 5]}),
        ("T20I", "batter"): pd.DataFrame({"player_id": [2, 3, 4], "balls": [30, 30, 30]}),
    }
    for fmt in ("IPL", "T20I"):
        tab[(fmt, "bowler")] = pd.DataFrame({"player_id": [], "balls": []})
    summary = {f: {r: {"recommended": {"min_balls": 24}} for r in ("batter", "bowler")}
               for f in ("IPL", "T20I")}  # fmt: skip
    out = pe.combined_both_formats(summary, tab, 10)
    assert out["batter"]["eligible_both_formats"] == 1  # only player 2 passes in both
    assert out["batter"]["fewer_than_list_size"] is True
    summary["IPL"]["bowler"]["recommended"] = None
    assert pe.combined_both_formats(summary, tab, 10)["bowler"]["eligible_both_formats"] is None


# ---------------------------------------------------------------- Phase 2.5 comparison
def test_phase25_threshold_parsing_and_pass_counts():
    rep = {"recommendation_inputs": {"IPL": {"batter": {"primary_family": "balls", "families": {
        "balls": {"data_weight_rule": "balls:PR120", "required_balls_for_data_weight": 106.6,
                  "ladder": [{"rule_id": "balls:PR120", "min_value": 120, "eligible": 129}]}}}}}}  # fmt: skip
    p = pe.phase25_thresholds(rep)
    assert (
        p["IPL"]["batter"]["min_balls"] == 120
        and p["IPL"]["batter"]["eligible_all_situation"] == 129
    )
    t = pd.DataFrame({"balls": [5, 119, 120, 300]})
    assert pe.players_passing(t, 120) == 2 and pe.players_passing(t, None) is None


# ---------------------------------------------------------------- real data and reports
@pytest.mark.realdata
def test_real_pressure_samples_equal_stage3_counts_and_exclude_restricted_innings():
    if not ps.EXPLORATORY_DB.exists():
        pytest.skip("exploratory store not built")
    from app.analytics import pressure_features as pf
    from scripts.run_pressure_distributions import prepare

    rules, df, _ = prepare(ps.EXPLORATORY_DB)
    specs, flags = pf.build_candidates(df, rules)
    d = {"id": "chase|q0.9", "ctx": "chase", "q": 0.9, "view": "abs"}
    bat = be.batter_frame(df)
    fb = pe.definition_flag(flags, CFG, d, "batter")
    sub = fb[bat["_src_index"].to_numpy()]
    res = np.zeros(len(bat))
    out = pe.batter_samples(bat, sub, res)
    pc = pdist.player_counts(df, fb, "batter")
    assert int(out["n"].sum()) == int(pc["n"].sum())
    assert (
        out.groupby("player_id")["match_id"].nunique().to_dict()
        == pc.set_index("player_id")["matches"].to_dict()
    )
    assert set(df.loc[fb, "innings_number"]) <= {2}
    assert not df.loc[fb, "competition_type"].eq("OTHER_T20").any()
    restricted = df["innings_number"].isin([3, 4])
    assert not (fb & restricted.to_numpy()).any()


@pytest.mark.realdata
def test_threshold_experiment_report_is_exploratory_and_lists_no_players():
    p = REPORTS / "pressure_threshold_experiment.json"
    if not p.exists():
        pytest.skip("experiment not run")
    exp = json.loads(p.read_text("utf-8"))
    assert exp["status"] == "EXPLORATORY_NOT_VALIDATED" and exp["official_ranking"] is False
    assert exp["not_for_publication"] is True and exp["preservation"]["official_unchanged"]
    assert exp["selection"]["status"].startswith("PROVISIONAL_NOT_VALIDATED")
    text = p.read_text("utf-8")
    assert '"technical_appendix"' not in text and '"player_name"' not in text
    sel = exp["selection"]["selected_id"]
    for d in exp["definitions"]:
        for f in ("IPL", "T20I"):
            for r in ("batter", "bowler"):
                c = d["summary"][f][r]
                if c["recommended"] is None:
                    assert c["verdict"].startswith("NO_RULE")  # reported, never padded
                else:
                    assert c["recommended"]["pool"]["sufficient"]
    assert any(d["definition"]["id"] == sel for d in exp["definitions"]) or sel is None
    assert exp["provisional_recommendation"]["status"] in (
        "PROVISIONAL_NOT_VALIDATED",
        "NO_DEFINITION_VIABLE",
    )
    # all-situation thresholds were compared, not reused
    comp = next(d for d in exp["definitions"] if d["definition"]["id"] == sel)[
        "comparison_with_phase25"
    ]
    for f in ("IPL", "T20I"):
        for r in ("batter", "bowler"):
            x = comp[f][r]
            assert (
                x["players_passing_phase25_threshold_on_pressure_samples"]
                < x["pressure_specific_eligible"]
            )
