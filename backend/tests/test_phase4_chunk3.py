"""Phase 4 Stages D and E: definition rule, eligibility thresholds, ranking stability,
format weights, shrinkage sensitivity and baseline variants (synthetic data)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.phase4 import baseline as bl
from app.phase4 import definitions as dfn
from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4 import sensitivity as sn
from app.phase4.split import TestLock, TestPeriodLockError
from tests.phase4_scoring_helpers import synth_frame

PARAMS = {"min_cell_innings": 5, "tau2_floor": 0.01}


@pytest.fixture(scope="module")
def frame():
    f = synth_frame(3)
    f["par_unavailable_insufficient_prior"] = False
    return f


@pytest.fixture
def lock(tmp_path):
    return TestLock(tmp_path / "lock.json")


@pytest.fixture(scope="module")
def bset(frame):
    return bl.fit_baseline_set(frame, PARAMS)


def press_rows(n_players=14, n_matches=30, effect_sd=0.6, seed=0, comps=("IPL", "T20I")):
    """Synthetic pressure rows with a stable per-player effect plus noise."""
    rng = np.random.default_rng(seed)
    eff = rng.normal(0, effect_sd, n_players)
    out, mid = [], 0
    for comp in comps:
        for m in range(n_matches):
            mid += 1
            period = "TRAIN" if m < n_matches * 0.6 else "VALIDATION"
            date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=m + (0 if comp == "IPL" else 400))
            for p in range(n_players):
                for _ in range(rng.integers(1, 5)):
                    out.append((p + 1, mid, comp, period, date, eff[p] + rng.normal(0, 1.0)))
    t = pd.DataFrame(out, columns=["player_id", "match_id", "comp", "period", "date", "resid"])
    t["actual"], t["expected"], t["src"] = t["resid"], 0.0, np.arange(len(t))
    return t


# ---------------------------------------------------------------- eligibility thresholds
def test_candidate_thresholds_from_percentiles_and_ladder():
    balls = np.arange(1, 101, dtype=float)
    c = {x["threshold"]: x["source"] for x in el.candidate_thresholds(balls, [6, 24, 500])}
    assert c[51] == "P50"  # ceil(50.5)
    assert 6 in c and 24 in c and 500 not in c  # rung beyond the observed maximum is dropped
    assert all(t >= 1 for t in c)
    merged = el.candidate_thresholds(np.array([10.0, 10, 10, 10]), [10])
    assert merged == [{"threshold": 10, "source": "P10+P25+P50+P60+P75+ladder"}]


def row(t, b, repro="ESTIMABLE", lo=None, hi=None, n=20, src="ladder"):
    r = {"threshold_balls": t, "source": src, "eligible_players": n, "marginal_data_weight": b,
         "reproducibility_status": repro, "reproducibility_lo": lo, "reproducibility_hi": hi}  # fmt: skip
    return r


def test_decide_selects_smallest_passing_and_never_lowers():
    rows = [row(6, 0.2), row(12, 0.55), row(24, 0.8)]
    d = el.decide(rows, pd.DataFrame(), 1.3)
    assert d["status"] == "THRESHOLD_SELECTED_PROVISIONAL" and d["threshold_balls"] == 12


def test_decide_skips_significantly_negative_reproducibility():
    rows = [row(12, 0.55, lo=-0.9, hi=-0.1), row(24, 0.8, lo=0.0, hi=0.5)]
    assert el.decide(rows, pd.DataFrame(), 1.0)["threshold_balls"] == 24


def test_decide_not_validated_has_no_threshold_and_fallback_needs_floor_and_positive_interval():
    rows = [
        row(3, 0.05, lo=0.2, hi=0.6, src="P10"),  # positive but data weight below 0.1
        row(48, 0.12, lo=0.1, hi=0.5, src="P50"),
        row(96, 0.3, repro="REPRODUCIBILITY_NOT_ESTIMABLE"),
    ]
    d = el.decide(rows, pd.DataFrame(), 1.0)
    assert d["status"] == "THRESHOLD_NOT_VALIDATED" and d["threshold_balls"] is None
    assert d["fallback_threshold_balls"] == 48 and d["label"] == el.LABEL_FALLBACK
    none = el.decide([row(3, 0.05, lo=0.2, hi=0.6, src="P50")], pd.DataFrame(), 1.0)
    assert none["fallback_threshold_balls"] is None and none["label"] == el.LABEL_WORKING
    assert el.analysis_rule(none)["label"] == el.LABEL_WORKING  # never labelled validated


def test_eligible_mask_without_threshold_is_empty_and_pool_not_padded():
    est = pd.DataFrame({"n": [5.0, 40.0, 80.0], "shrunk": [0.1, 0.2, 0.3]})
    rule = {"threshold_balls": 30, "label": el.LABEL_SELECTED}
    assert el.eligible_mask(est, rule, 1.0).sum() == 2  # fewer than ten stays fewer than ten
    assert el.eligible_mask(est, {"threshold_balls": None}, 1.0).sum() == 0
    assert el.eligible_mask(est, rule, 2.0).tolist() == [False, False, True]  # t * W = 60


def test_evaluate_cell_runs_and_pool_is_monotone_in_threshold():
    rows = press_rows()
    cell = en.build_cell(rows, "IPL", "batter", "runs")
    gm, W = en.global_weights(rows["match_id"].to_numpy(), 50, 7)
    e = el.evaluate_cell(cell, cell.fit(), "shrink_eb", gm, W, [2, 4, 8], 1.0)
    sizes = [r["eligible_players"] for r in e["candidates"]]
    assert sizes == sorted(sizes, reverse=True)
    dec = e["decision"]
    ts = {r["threshold_balls"] for r in e["candidates"]}
    assert dec["threshold_balls"] in ts | {None} and dec["status"].startswith("THRESHOLD_")
    assert dec["gate_marginal_data_weight"] == 0.5


# ---------------------------------------------------------------- ranking engine and bootstrap
def test_col_ranks_and_masked_correlations():
    X = np.array([[3.0, 1.0], [1.0, 9.0], [2.0, 5.0]])
    present = np.array([[True, True], [True, False], [True, True]])
    r = en.col_ranks(X, present)
    assert r[:, 0].tolist() == [1, 3, 2]
    assert np.isnan(r[1, 1]) and r[0, 1] == 2 and r[2, 1] == 1
    a = np.arange(10.0)[:, None]
    b = (a**2 + 1)[::-1]
    assert en.masked_pearson(a, b, np.ones_like(a, dtype=bool))[0] == pytest.approx(
        np.corrcoef(a[:, 0], b[:, 0])[0, 1]
    )
    assert en.masked_spearman(a, a * 3, np.ones_like(a, dtype=bool))[0] == pytest.approx(1.0)


def test_rank_summary_inclusion_sums_and_never_pads():
    rng = np.random.default_rng(1)
    n, B = 25, 400
    point = rng.normal(size=n)
    draws = point[:, None] + rng.normal(0, 0.3, (n, B))
    present = np.ones(n, dtype=bool)
    rs = en.rank_summary(draws, point, present)
    assert rs["inclusion_prob"].sum() == pytest.approx(10.0)  # exactly k per resample
    assert rs["max_overlap"] == 10 and 5 < rs["overlap"].mean() <= 10
    small = en.rank_summary(draws[:6], point[:6], present[:6])
    assert small["inclusion_prob"].sum() == pytest.approx(6.0)  # pool of 6: Top 10 = the 6
    sm = en.summarize_ranking(small)
    assert sm["trivial_full_pool"] and sm["pool_size"] == 6
    assert small["rank_hi"].max() <= 6  # no padding to ten


def test_rank_summary_absent_players_excluded_and_deterministic_weights():
    point = np.array([3.0, 2.0, 1.0, 0.0])
    present = np.array([True, True, True, False])
    draws = np.tile(point[:, None], (1, 5))
    draws[1, 2] = np.nan
    rs = en.rank_summary(draws, point, present)
    assert np.all(np.isnan(rs["rank_med"][3])) and rs["present_prob"][3] == 0
    assert rs["present_prob"][1] == pytest.approx(0.8)
    g1 = en.global_weights(np.array([5, 3, 3, 9]), 20, 11)
    g2 = en.global_weights(np.array([5, 3, 3, 9]), 20, 11)
    g3 = en.global_weights(np.array([5, 3, 3, 9]), 20, 12)
    assert list(g1[0]) == [3, 5, 9] and (g1[1] == g2[1]).all() and not (g1[1] == g3[1]).all()
    assert (g1[1].sum(1) == 3).all()  # one multinomial draw of n matches per resample


def test_bootstrap_draws_match_point_estimate_with_unit_weights():
    rows = press_rows(n_players=8, n_matches=20)
    cell = en.build_cell(rows, "IPL", "batter", "runs")
    est = en.point_estimates(cell, cell.fit(), "shrink_eb")
    nb, dr = en.draws(cell, est, np.ones((len(cell.matches), 1)))
    assert np.allclose(dr[:, 0], est["shrunk"].to_numpy())
    assert np.allclose(nb[:, 0], est["n"].to_numpy())


# ---------------------------------------------------------------- definition rule
def cand(i, sc_, p=50, gate=True, rank=True, balls=1000, se=0.01):
    return {"definition_id": i, "gate1_pass": gate, "rankable": rank, "Sc": sc_,
            "Sc_boot_se": se, "min_P": p, "total_P": p * 4,
            "total_pressure_balls_TRAIN": balls, "_boot": np.full(100, sc_ if rank else np.nan)}  # fmt: skip


def test_rule_file_is_fixed_and_has_nine_candidates():
    rule = dfn.load_rule()
    assert rule["fixed_before_evaluation"] and rule["test_outcomes_used"] is False
    ids = dfn.definition_ids(rule)
    assert len(ids) == 9 and "chase|q0.9" in ids
    assert rule["candidates"]["leading_provisional"] == "chase|q0.9"
    assert "population" in " ".join(rule["gates_and_choice"]).lower()


def test_big_population_low_reliability_candidate_does_not_win():
    rule = dfn.load_rule()
    big = cand("any|q0.75", 0.05, p=900, balls=90000)
    small = cand("chase|q0.9", 0.40, p=40, balls=3000)
    res = dfn.apply_rule([big, small], rule)
    assert res["winner"] == "chase|q0.9"
    assert res["label"].startswith("PROVISIONAL")
    assert {c["definition_id"] for c in res["candidates"]} == {"any|q0.75", "chase|q0.9"}  # kept


def test_gate1_and_rankability_exclude_and_tie_goes_to_lexicographic_id():
    rule = dfn.load_rule()
    cs = [cand("b|q1", 0.30), cand("a|q1", 0.295), cand("z|q1", 0.9, gate=False),
          cand("y|q1", 0.9, rank=False)]  # fmt: skip
    res = dfn.apply_rule(cs, rule)
    status = {c["definition_id"]: c["status"] for c in res["candidates"]}
    assert status["z|q1"] == "GATE1_FAIL" and status["y|q1"] == "NOT_RANKABLE"
    assert res["top_group"] == ["a|q1", "b|q1"] and res["winner"] == "a|q1"


def test_no_rankable_candidate_means_no_winner_and_leading_default_kept():
    rule = dfn.load_rule()
    res = dfn.apply_rule([cand("chase|q0.9", None, gate=False, rank=False)], rule)
    assert res["winner"] is None and res["leading_provisional"] == "chase|q0.9"
    assert "NO_RULE_WINNER" in res["label"]


def test_reliability_statistics_separate_signal_from_noise():
    p = dfn.load_rule()["parameters"]
    sig = en.build_cell(press_rows(n_players=60, effect_sd=1.5, seed=2), "IPL", "batter", "runs")
    noise = en.build_cell(press_rows(n_players=60, effect_sd=0.0, seed=2), "IPL", "batter", "runs")
    one = np.ones((len(sig.matches), 1))
    a = dfn.rs_stats(sig, one, p)
    b = dfn.rs_stats(noise, np.ones((len(noise.matches), 1)), p)
    assert a["r_half"][0] > 0.6 and a["r_S"][0] > 0.5
    assert abs(b["r_half"][0]) < 0.45 and a["r_half"][0] > b["r_half"][0]
    assert dfn.spearman_brown(np.array([0.5]))[0] == pytest.approx(2 * 0.5 / 1.5)
    assert np.isnan(dfn.spearman_brown(np.array([-1.0]))[0])


def test_split_half_uses_only_train_and_stability_uses_both_periods():
    p = dfn.load_rule()["parameters"]
    rows = press_rows(seed=4)
    cell = en.build_cell(rows, "IPL", "batter", "runs")
    base = dfn.rs_stats(cell, np.ones((len(cell.matches), 1)), p)
    changed = rows.copy()
    changed.loc[changed["period"] == "VALIDATION", "resid"] += 5.0 * (changed["player_id"] % 3)
    c2 = en.build_cell(changed, "IPL", "batter", "runs")
    after = dfn.rs_stats(c2, np.ones((len(c2.matches), 1)), p)
    assert after["r_half"][0] == pytest.approx(base["r_half"][0])  # TRAIN-only statistic
    assert after["r_S"][0] != pytest.approx(base["r_S"][0])


def test_contrast_detects_pressure_effect_with_bootstrap_interval():
    rng = np.random.default_rng(5)
    n = 4000
    t = pd.DataFrame({"match_id": rng.integers(1, 41, n), "period": "VALIDATION", "in_pop": True,
                      "press": rng.random(n) < 0.3})  # fmt: skip
    t["resid"] = rng.normal(0, 1, n) - 0.4 * t["press"]
    gm, W = en.global_weights(t["match_id"].to_numpy(), 200, 3)
    c = dfn.contrast(t, gm, W)
    assert c["D"] < -0.2 and c["D_hi"] < 0 and c["D_lo"] < c["D"] < c["D_hi"]
    assert dfn.contrast(t.assign(press=False), gm, W)["D"] is None


# ---------------------------------------------------------------- pressure scoring with rules
def test_score_cell_eligibility_rule_labels_and_empty_pool(frame, bset, lock):
    d = sc.add_signals(frame, lock) if False else frame
    thr = sc.fit_thresholds(d[d["period"] == "TRAIN"], 0.75)
    rows = sc.residual_rows(d, bset, "chase|q0.75", thr, "batter", "runs", lock)
    base_rule = {"threshold_balls": 3, "label": el.LABEL_SELECTED, "wr": 1.0, "basis": "TEST_BASIS"}
    recs, _ = sc.score_cell(rows, "batter", "runs", "IPL", "chase|q0.75", "v", "shrink_eb", 20,
                            elig=base_rule)  # fmt: skip
    assert recs and {r.eligibility_basis for r in recs} == {"TEST_BASIS"}
    assert {r.eligibility_status for r in recs} <= {el.LABEL_SELECTED, "NOT_ELIGIBLE"}
    none_rule = {**base_rule, "threshold_balls": None, "label": el.LABEL_NO}
    recs2, _ = sc.score_cell(rows, "batter", "runs", "IPL", "chase|q0.75", "v", "shrink_eb", 20,
                             elig=none_rule)  # fmt: skip
    assert all(r.eligibility_status == "NOT_ELIGIBLE" for r in recs2)  # nobody is padded in
    legacy, _ = sc.score_cell(rows, "batter", "runs", "IPL", "chase|q0.75", "v", "shrink_eb", 20)
    assert {r.eligibility_basis for r in legacy} == {sc.ELIG_PLACEHOLDER}  # default unchanged


def test_engine_base_rows_refuses_test_rows_while_locked(bset, lock):
    f = synth_frame(3, with_test=True)
    f["par_unavailable_insufficient_prior"] = False
    with pytest.raises(TestPeriodLockError):
        en.base_rows(f, bset, "batter", "runs", lock)
    assert any(e["event"] == "READ_DENIED" for e in lock.entries)


def test_population_excludes_innings1_rows_without_prior_par(frame):
    f = frame.copy()
    f["par_unavailable_insufficient_prior"] = False
    f.loc[f.index[:50], "par_unavailable_insufficient_prior"] = True
    i1 = en.population(f, "inn1")
    assert not i1.iloc[:50].any() and i1.sum() == f["inn1_pop"].sum() - int(
        f["inn1_pop"].iloc[:50].sum()
    )
    assert en.population(f, "chase").sum() == f["chase_pop"].sum()
    assert en.population(f, "any").sum() == en.population(f, "chase").sum() + i1.sum()


# ---------------------------------------------------------------- baseline variants
def test_baseline_variants_change_levels_and_offsets_without_touching_default(frame):
    b0 = bl.fit_baseline_set(frame, PARAMS)
    coarse = bl.fit_baseline_set(frame, {**PARAMS, "first_level": 2}, version="x")
    nooff = bl.fit_baseline_set(frame, {**PARAMS, "no_offset": True})
    fr = bl.role_frame("batter", frame)
    e0 = b0.expected("batter", "runs", fr)
    ec = coarse.expected("batter", "runs", fr)
    en_ = nooff.expected("batter", "runs", fr)
    assert b0.version == bl.BASELINE_VERSION and coarse.version == "x"
    assert len(coarse.frozen[("batter", "runs")].uniques) == 2
    assert not np.allclose(e0["expected"], ec["expected"])
    assert nooff.frozen[("batter", "runs")].use_offsets is False
    assert np.isfinite(en_["expected"]).all()


# ---------------------------------------------------------------- sensitivity analyses
@pytest.fixture(scope="module")
def synth_cells():
    rows = press_rows(n_players=14, n_matches=30, seed=9)
    cells = {}
    for comp in ("IPL", "T20I"):
        for role in ("batter", "bowler"):
            r = rows if role == "batter" else rows.assign(resid=-rows["resid"])
            cells[(comp, role)] = en.build_cell(r, comp, role, en.PRIMARY[role][0])
    # a player seen only in IPL batters
    extra = rows[rows["comp"] == "IPL"].head(10).assign(player_id=999)
    cells[("IPL", "batter")] = en.build_cell(
        pd.concat([rows, extra], ignore_index=True), "IPL", "batter", "runs"
    )
    gm, W = en.global_weights(rows["match_id"].to_numpy(), 60, 5)
    fits = {k: c.fit() for k, c in cells.items()}
    rules = {k: {"threshold_balls": 2, "label": el.LABEL_WORKING, "wr": 1.0} for k in cells}
    return cells, fits, rules, gm, W


WCFG = {
    "default_config_id": "w70_30",
    "configurations": [
        {"id": "w100_0", "ipl_weight": 1.0, "t20i_weight": 0.0},
        {"id": "w70_30", "ipl_weight": 0.7, "t20i_weight": 0.3},
        {"id": "w0_100", "ipl_weight": 0.0, "t20i_weight": 1.0},
    ],
}


def test_format_weights_never_zero_fill_a_missing_format(synth_cells):
    cells, fits, rules, gm, W = synth_cells
    fw = sn.format_weight_analysis(cells, fits, rules, gm, W, "shrink_eb", WCFG)
    cfgs, players = fw["configs"], fw["players"]
    assert 999 not in set(players["player_id"])  # IPL-only player is not combined
    bat = cfgs[cfgs["role"] == "batter"]
    assert (bat["pool_size"] == 14).all()  # identical eligibility pool for every configuration
    assert set(bat["config_id"]) == {"w100_0", "w70_30", "w0_100"}
    ref = bat[bat["config_id"] == "w70_30"].iloc[0]
    assert (
        ref["spearman_vs_default"] == pytest.approx(1.0) and ref["top10_overlap_vs_default"] == 10
    )
    sf = fw["single_format"]
    assert sf[(sf["role"] == "batter") & (sf["scope"] == "IPL_ONLY")]["pool_size"].iloc[0] == 15
    assert np.isfinite(fw["pairwise"]["spearman"]).all()


def test_sensitivity_tables_are_one_factor_not_a_joint_grid(synth_cells):
    cells, fits, rules, gm, W = synth_cells
    fw = sn.format_weight_analysis(cells, fits, rules, gm, W, "shrink_eb", WCFG)
    for col in ("definition_id", "shrinkage_config", "baseline"):
        assert col not in fw["configs"].columns
    sens = sn.shrinkage_sensitivity(cells, fits, rules, gm, W, {}, 40, 1)
    for col in ("config_id", "ipl_weight", "definition_id", "baseline"):
        assert col not in sens.columns
    assert set(sens["shrinkage_config"]) == set(sn.sh.CONFIGS)


def test_zero_shrinkage_is_retained_and_has_full_data_weight(synth_cells):
    cells, fits, rules, gm, W = synth_cells
    sens = sn.shrinkage_sensitivity(cells, fits, rules, gm, W, {}, 40, 1)
    none = sens[sens["shrinkage_config"] == "shrink_none"]
    assert (none["median_data_weight_pool"] == 1.0).all() and (none["k"] == 0).all()
    assert not none["choosable_as_primary"].any()
    eb = sens[sens["shrinkage_config"] == "shrink_eb"]
    assert (eb["median_data_weight_pool"] <= 1.0).all()
    assert (eb["spearman_vs_shrink_eb"] > 0.999).all()


def test_ranking_stability_outputs_are_labelled_and_not_padded(synth_cells):
    cells, fits, rules, gm, W = synth_cells
    sens = sn.shrinkage_sensitivity(cells, fits, rules, gm, W, {}, 40, 1)
    e = {
        k: [{"threshold_balls": 2, "source": "ladder", "expected_top10_overlap": 7.0}]
        for k in cells
    }
    rs = sn.ranking_stability(cells, fits, rules, gm, W, "shrink_eb", e, sens)
    summ = rs["summary"]
    assert (summ["eligibility_label"] == el.LABEL_WORKING).all()
    p = rs["players"]
    bowl = p[(p["scope"] == "T20I") & (p["role"] == "bowler")]
    assert len(bowl) == 14 and bowl["rank_hi"].max() <= 14
    assert (p["top10_inclusion_prob"] <= p["present_prob"] + 1e-12).all()
    assert (summ["top10_size"] == 10).all()
    tv = rs["threshold_variants"]
    assert tv["is_analysis_threshold"].all() and set(rs["shrinkage_variants"]["shrinkage_config"])


def test_frozen_choices_file_is_deterministic_json(tmp_path, lock):
    from app.phase4.split import write_frozen_choices

    path = tmp_path / "frozen.json"
    sha1 = write_frozen_choices({"b": 1, "a": {"y": 2, "x": 1}}, path, lock)
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == {"a": {"x": 1, "y": 2}, "b": 1}
    assert write_frozen_choices({"a": {"x": 1, "y": 2}, "b": 1}, path, lock) == sha1
