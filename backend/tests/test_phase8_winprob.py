"""Win-probability models: labels, features, leakage, fit-on-TRAIN-only, terminal states, artefact."""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
import pytest

from app.phase4.split import SplitIntegrityError
from app.phase8 import winprob as wp
from app.phase8.constants import MODELS_DIR

# ---------------------------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("result", "win", "rev", "expected"),
    [
        ("Match Tied", np.nan, None, "NO_WINNER"),
        ("No Result", np.nan, None, "NO_WINNER"),
        ("Match Abandoned", np.nan, None, "NO_WINNER"),
        ("Sri Lanka won the super over", 5, None, "RESULT_TEXT:super over"),
        ("Tied with DC won the Super Over", 5, None, "RESULT_TEXT:tied"),
        (
            "India Tied with Srilanka (India Won the Super Over by 2 wickets)",
            5,
            None,
            "RESULT_TEXT:tied",
        ),
        ("Australia Won the one over Eliminator", 5, None, "RESULT_TEXT:eliminator"),
        ("Australia Won by 20 runs (D/L method)", 5, None, "RESULT_TEXT:d/l"),
        ("West Indies Won by 8 wickets (DLS)", 5, None, "RESULT_TEXT:dls"),
        ("Delhi Capitals Won by 6 wickets", 5, 120, "DLS_REVISED_TARGET"),
        ("Delhi Capitals Won by 6 wickets", 5, None, None),
        ("Mumbai Indians won by 5 wickets", 5, pd.NA, None),
        ("Scotland won by 12 runs", 5, None, None),
        ("United Arab Emirates won by 3 wickets", 5, None, None),
    ],
)
def test_exclusion_reason_cases(result, win, rev, expected):
    assert wp.exclusion_reason(result, win, rev) == expected


def test_match_labels_marks_unlabelled_matches_and_never_imputes():
    m = pd.DataFrame({
        "match_id": [1, 2, 3], "result": ["X won by 5 runs", "No Result", "Y won the Super Over"],
        "win_team_id": [10.0, np.nan, 11.0], "revised_target": [None, None, None],
    })  # fmt: skip
    lab = wp.match_labels(m).set_index("match_id")
    assert lab["label_ok"].tolist() == [True, False, False]
    assert lab.loc[3, "reason"].startswith("RESULT_TEXT")


# ---------------------------------------------------------------------------------------------
# features and leakage (truncation and mutation)
# ---------------------------------------------------------------------------------------------


def _innings(match_id=1, innings=2, n=12, target=60, start_runs=0, seed=0):
    rng = np.random.default_rng(seed)
    runs = np.concatenate([[start_runs], start_runs + np.cumsum(rng.integers(0, 5, n - 1))])
    wk = np.minimum(np.cumsum(np.concatenate([[0], rng.random(n - 1) < 0.15])), 9)
    return pd.DataFrame({
        "match_id": match_id, "innings_number": innings, "innings_ball_num": np.arange(1, n + 1),
        "batting_team_id": 7 if innings == 2 else 8, "competition_type": "IPL",
        "team_runs_before": runs, "team_wickets_before": wk, "legal_balls_bowled_before": np.arange(n),
        "legal_balls_remaining": 120 - np.arange(n), "innings_limit_balls": 120,
        "target": target if innings == 2 else np.nan,
        "target_basis_unverified": False, "req_nonpositive_flag": False,
        "bat_team_prior": 0.55, "bowl_team_prior": 0.45, "par_prior": 150.0,
        "innings_phase": "powerplay", "period": "TRAIN",
        "out_batter_runs": 1, "out_is_wicket": False,
    })  # fmt: skip


def test_features_of_a_row_ignore_later_rows_and_outcomes():
    d = _innings(n=20)
    full = wp.frame_features(d)
    cut = wp.frame_features(d.iloc[:8])
    pd.testing.assert_frame_equal(full.iloc[:8], cut, check_exact=True)
    mutated = d.copy()
    mutated.loc[8:, ["team_runs_before", "team_wickets_before"]] = 0  # future state rewritten
    mutated["out_batter_runs"] = 6  # outcomes rewritten
    mutated["out_is_wicket"] = True
    pd.testing.assert_frame_equal(
        wp.frame_features(mutated).iloc[:8], full.iloc[:8], check_exact=True
    )


def test_feature_formulae_match_the_state_engine_definitions():
    d = _innings(n=10, target=70)
    f = wp.frame_features(d)
    i = 5
    br, bb = d["legal_balls_remaining"].iloc[i], d["legal_balls_bowled_before"].iloc[i]
    req = 70 - d["team_runs_before"].iloc[i]
    assert f["rrr"].iloc[i] == pytest.approx(6 * req / br)
    assert f["crr"].iloc[i] == pytest.approx(6 * d["team_runs_before"].iloc[i] / bb)
    assert f["gap"].iloc[i] == pytest.approx(f["rrr"].iloc[i] - f["crr"].iloc[i])
    assert f["resource_ratio"].iloc[i] == pytest.approx(
        br / 120 * (10 - d["team_wickets_before"].iloc[i]) / 10
    )
    assert np.isnan(f["crr"].iloc[0])  # undefined before the first ball, never zero


def test_features_match_stored_state_columns_on_real_rows():
    from app.phase8.constants import EXPLORATORY_DB

    if not EXPLORATORY_DB.exists():
        pytest.skip("exploratory database not available")
    import duckdb

    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        d = con.execute(
            "SELECT * FROM exp_pre_delivery_state WHERE match_id IN "
            "(SELECT match_id FROM exp_pre_delivery_state WHERE competition_type = 'IPL' "
            "ORDER BY match_id LIMIT 2) AND innings_number IN (1, 2)"
        ).df()
    finally:
        con.close()
    d["bat_team_prior"] = d["bowl_team_prior"] = d["par_prior"] = np.nan
    f = wp.frame_features(d)
    for c in ("rrr", "gap", "resource_ratio", "crr"):
        both = d[c].notna() & f[c].notna()
        assert both.any()
        assert np.allclose(d.loc[both, c], f.loc[both, c], atol=1e-9)


# ---------------------------------------------------------------------------------------------
# WP timeline
# ---------------------------------------------------------------------------------------------


def _timeline(winner=7):
    d = pd.concat(
        [_innings(innings=1, n=6, seed=1), _innings(innings=2, n=6, seed=2)], ignore_index=True
    )
    labels = pd.DataFrame({"match_id": [1], "win_team_id": [winner], "label_ok": [True]})
    wpb = pd.Series([0.50, 0.52, 0.55, 0.51, 0.49, 0.50, 0.40, 0.42, 0.45, 0.60, 0.70, 0.80])
    return d, labels, wpb


def test_wp_after_is_the_next_balls_wp_before_and_terminal_balls_use_documented_rules():
    d, labels, wpb = _timeline()
    after = wp.wp_after_series(d, wpb, labels)
    assert after.iloc[:5].tolist() == wpb.iloc[1:6].tolist()
    assert after.iloc[5] == pytest.approx(
        1 - 0.40
    )  # innings 1 end: 1 - WP2 of the first chase ball
    assert after.iloc[6:11].tolist() == wpb.iloc[7:12].tolist()
    assert after.iloc[11] == wp.CLIP[1]  # chasing side (team 7) won


def test_result_mutation_changes_only_the_terminal_ball_and_never_wp_before():
    d, labels, wpb = _timeline(winner=7)
    a1 = wp.wp_after_series(d, wpb, labels)
    a2 = wp.wp_after_series(d, wpb, labels.assign(win_team_id=8))
    diff = np.flatnonzero(~np.isclose(a1.to_numpy(), a2.to_numpy()))
    assert diff.tolist() == [11]
    assert a2.iloc[11] == wp.CLIP[0]
    # truncating the match after ball t leaves WP_before(t) (an input here) and WP_after(t) unchanged
    t = d.iloc[:9]
    a3 = wp.wp_after_series(t, wpb.iloc[:9], labels)
    assert a3.iloc[:8].tolist() == a1.iloc[:8].tolist()


def test_unlabelled_match_gets_no_terminal_value_not_zero():
    d, labels, wpb = _timeline()
    after = wp.wp_after_series(d, wpb, labels.assign(label_ok=False))
    assert np.isnan(after.iloc[11])


def test_non_contiguous_rows_give_no_wp_after():
    d, labels, wpb = _timeline()
    d = d.drop(index=[2]).reset_index(drop=True)
    wpb = wpb.drop(index=[2]).reset_index(drop=True)
    after = wp.wp_after_series(d, wpb, labels)
    assert np.isnan(after.iloc[1])  # ball 2's next row is ball 4


# ---------------------------------------------------------------------------------------------
# fitting on TRAIN only, folds, gate
# ---------------------------------------------------------------------------------------------


def _synthetic(n_matches=140, per=40, seed=11):
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(1, n_matches + 1):
        period = "TRAIN" if m <= 100 else "VALIDATION"
        rr = rng.uniform(20, 160, per)
        br = rng.uniform(1, 120, per)
        p = 1 / (1 + np.exp(-(0.04 * (rr.mean() * 0 + 80 - rr) + 0.02 * br)))
        y = float(rng.random() < p.mean())
        for k in range(per):
            rows.append({"match_id": m, "period": period, "rr": rr[k], "br": br[k],
                         "wk": rng.integers(1, 10), "y": y if period == "TRAIN" else float(rng.random() < 0.5)})  # fmt: skip
    return pd.DataFrame(rows)


def test_fit_wp_uses_only_train_matches_and_folds_never_share_a_match():
    d = _synthetic()
    x = pd.DataFrame({"rrr": d["rr"], "legal_balls_remaining": d["br"], "wickets_remaining": d["wk"],
                      "competition_code": 0.0, "runs_required": d["rr"]})  # fmt: skip
    cols = ["rrr", "legal_balls_remaining", "wickets_remaining", "competition_code"]
    y, pop = d["y"], pd.Series(True, index=d.index)
    fit = wp.fit_wp("T", d, x, y, pop, cols, ["rrr", "wickets_remaining"], pop)
    assert set(fit.fold_predictors) == {0, 1, 2, 3, 4}
    assert fit.train_matches == d.loc[d["period"] == "TRAIN", "match_id"].nunique()
    assert fit.pred.notna().all()
    # VALIDATION labels play no part in fitting: flipping them leaves the predictor unchanged
    d2 = d.assign(y=np.where(d["period"] == "VALIDATION", 1 - d["y"], d["y"]))
    fit2 = wp.fit_wp("T", d2, x, d2["y"], pop, cols, ["rrr", "wickets_remaining"], pop)
    probe = x.iloc[:50]
    assert np.allclose(fit.predictor(probe), fit2.predictor(probe))
    # OOF TRAIN prediction of a match comes from a fold model that did not see it
    fold = d["match_id"] % 5
    m = d.index[(d["period"] == "TRAIN") & (fold == 2)][:30]
    assert np.allclose(fit.pred.loc[m], fit.fold_predictors[2](x.loc[m]))


def test_fit_on_non_train_matches_is_refused():
    from app.phase8.splits import assert_fit_on_train

    d = _synthetic()
    with pytest.raises(SplitIntegrityError):
        assert_fit_on_train(d.loc[d["period"] == "VALIDATION", "match_id"], d)


def test_innings_gate_applies_the_declared_thresholds():
    ok = wp.innings_gate({"slope": 0.9, "brier_gain_vs_const": 0.05})
    assert ok["passed"]
    assert not wp.innings_gate({"slope": 0.7, "brier_gain_vs_const": 0.05})["passed"]
    assert not wp.innings_gate({"slope": 1.0, "brier_gain_vs_const": 0.01})["passed"]
    assert not wp.innings_gate({"slope": 1.3, "brier_gain_vs_const": 0.2})["passed"]


# ---------------------------------------------------------------------------------------------
# transitions and leverage
# ---------------------------------------------------------------------------------------------


class _StubWP:
    """WP that falls as the required rate rises (no fitting; cols as the real W2)."""

    def __init__(self, const=None):
        self.const = const

    def __call__(self, x):
        if self.const is not None:
            return np.full(len(x), self.const)
        return 1.0 / (1.0 + np.exp(0.5 * (x["rrr"].to_numpy() - 8.0)))


class _StubModel:
    classes_ = np.arange(wp.N_CLASS)

    def predict_proba(self, x):
        return np.full((len(x), wp.N_CLASS), 1.0 / wp.N_CLASS)


class _StubCls:
    model = _StubModel()

    def proba(self, x):
        return self.model.predict_proba(x)


def _chase_state(**kw):
    d = _innings(n=2, target=100)
    d.loc[:, "team_runs_before"] = kw.get("runs", 50)
    d.loc[:, "team_wickets_before"] = kw.get("wk", 3)
    d.loc[:, "legal_balls_bowled_before"] = kw.get("bb", 60)
    d.loc[:, "legal_balls_remaining"] = 120 - kw.get("bb", 60)
    return d


def test_next_state_terminal_rules():
    d = _chase_state(runs=95, bb=110, wk=3)
    s = _StubWP()
    one = np.ones(len(d))
    assert (wp.next_state_wp(s, s, d, 6 * one, 0 * one, one) == wp.CLIP[1]).all()  # chase won
    d2 = _chase_state(runs=50, bb=119, wk=3)
    assert (wp.next_state_wp(s, s, d2, 0 * np.ones(2), np.zeros(2), np.ones(2)) == wp.CLIP[0]).all()
    d3 = _chase_state(runs=50, bb=60, wk=9)
    assert (wp.next_state_wp(s, s, d3, np.zeros(2), np.ones(2), np.ones(2)) == wp.CLIP[0]).all()
    d4 = _innings(innings=1, n=2)
    d4.loc[:, "legal_balls_remaining"] = 1  # last ball of innings 1
    out = wp.next_state_wp(
        _StubWP(), _StubWP(const=0.3), d4, np.full(2, 4.0), np.zeros(2), np.ones(2)
    )
    assert np.allclose(out, 1 - 0.3)


def test_leverage_is_zero_for_constant_wp_and_positive_otherwise_and_unaffected_by_future_rows():
    d = _chase_state(runs=30, bb=40, wk=2)
    cols = ["innings_number", "team_runs_before", "team_wickets_before", "legal_balls_bowled_before",
            "legal_balls_remaining", "innings_limit_balls", "competition_type", "target",
            "bat_team_prior", "bowl_team_prior", "par_prior", "innings_phase"]  # fmt: skip
    dd = d[cols]
    wpb = np.full(len(dd), 0.5)
    lev0, p = wp.leverage_and_components(_StubWP(), _StubWP(const=0.5), _StubCls(), dd, wpb)
    assert np.allclose(lev0, 0.0) and np.allclose(p.sum(axis=1), 1.0)
    s = _StubWP()
    before = wp.apply_wp(s, s, wp.frame_features(d), d["innings_number"].to_numpy())
    lev, _ = wp.leverage_and_components(s, s, _StubCls(), dd, before)
    assert (lev > 0).all()
    # truncation: removing the other row leaves row 0's leverage unchanged
    lev_cut, _ = wp.leverage_and_components(s, s, _StubCls(), dd.iloc[:1], before[:1])
    assert lev_cut[0] == pytest.approx(lev[0])
    # mutation of outcome columns (not inputs of leverage) changes nothing
    d_mut = d.assign(out_batter_runs=6, out_is_wicket=True)
    lev_mut, _ = wp.leverage_and_components(s, s, _StubCls(), d_mut[cols], before)
    assert np.allclose(lev_mut, lev)


def test_class_target_maps_runs_and_wickets_and_drops_untrusted_rows():
    d = pd.DataFrame({
        "den_legal_inc": [1, 1, 1, 1, 0, 1], "out_batter_runs": [0, 4, 6, 5, 0, 1],
        "out_is_wicket": [False, False, False, False, False, True],
        "ok_run_target": True, "ok_wicket_target": [True, True, True, True, True, True],
    })  # fmt: skip
    y, pop = wp.class_target(d)
    assert y[pop].tolist() == [0, 4, 5, 6]  # 5 runs (rare) and the non-legal ball are dropped
    assert y.isna().tolist() == [False, False, False, True, True, False]


# ---------------------------------------------------------------------------------------------
# saved artefact
# ---------------------------------------------------------------------------------------------

ART = MODELS_DIR / "p8_wp_v1.joblib"
META = MODELS_DIR / "p8_wp_v1.json"


@pytest.mark.skipif(not ART.exists(), reason="WP artefact not built")
def test_saved_artefact_loads_and_predicts_probabilities():
    bundle = joblib.load(ART)
    d = _innings(n=30, target=150)
    f = wp.frame_features(d)
    p2 = bundle["w2"](f)
    assert p2.shape == (30,) and ((p2 >= 0) & (p2 <= 1)).all()
    d1 = _innings(innings=1, n=30)
    p1 = bundle["w1"](wp.frame_features(d1))
    assert ((p1 >= 0) & (p1 <= 1)).all()
    pc = bundle["cls"].proba(wp.frame_features(d1))
    assert np.allclose(pc.sum(axis=1), 1.0)


@pytest.mark.skipif(not META.exists(), reason="WP artefact not built")
def test_artefact_metadata_is_complete_and_states_the_split():
    m = json.loads(META.read_text(encoding="utf-8"))
    for k in ("algorithm", "version", "training_period", "train_matches", "features", "targets",
              "metrics", "seed", "timestamp", "data_hash_exploratory_db", "criteria_sha256",
              "training"):  # fmt: skip
        assert k in m, k
    assert m["test"] == "never loaded" and m["trained_on"] == "TRAIN"
    assert set(m["features"]) == {"W1", "W2", "CLS"}
    for k in ("W1", "W2"):
        assert m["metrics"][k]["brier"] < m["metrics"][k]["brier_const"]
