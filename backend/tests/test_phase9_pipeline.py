"""Phase 9 (chunk 1): 2026 data included by owner decision, leak-free scoring, labels, preservation."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from app.analytics.integrity import sha256_file
from app.phase8 import expected as ex
from app.phase8 import store
from app.phase8.approach_b import model_groups
from app.phase8.constants import (
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    EXPLORATORY_DB,
    MODELS_DIR,
    OFFICIAL_DB,
    PHASE8_DB,
    PHASE9_DB,
    REPORTS_DIR,
    translate_table,
)
from app.phase8.criteria import load_criteria
from app.phase8.data import (
    PHASE9_FIT_END,
    PHASE9_TRAIN_END,
    compute_team_priors,
    load_pre_test_deliveries,
)
from app.phase8.splits import fit_group
from app.phase8.status import list_status
from app.phase9 import lockrelease as lr
from app.phase9.fixed import phase8_expected_choice, phase8_wp_params
from app.services.pressure_service import StoreError

CRIT_SHA = "9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64"
TASKS = Path("d:/Data/.agents/tasks")
have_db = pytest.mark.skipif(
    not (EXPLORATORY_DB.exists() and OFFICIAL_DB.exists()), reason="databases absent"
)
have_p9 = pytest.mark.skipif(not PHASE9_DB.exists(), reason="phase 9 store not generated")


# ------------------------------------------------------------------ criteria and lock release
def test_criteria_file_hash_is_the_declared_one_and_checked_before_every_step():
    assert sha256_file(CRITERIA_FILE) == CRIT_SHA == lr.EXPECTED_CRITERIA_SHA256
    assert json.loads(CRITERIA_HASH_FILE.read_text(encoding="utf-8"))["sha256"] == CRIT_SHA
    for script in (
        "phase8_data.py",
        "phase8_intensity.py",
        "phase8_approach_a.py",
        "phase8_approach_b.py",
        "phase8_approach_c.py",
        "phase8_final_ranking.py",
        "phase9_models_check.py",
        "phase9_plan_row.py",
    ):
        text = (Path(__file__).resolve().parents[1] / "scripts" / script).read_text(
            encoding="utf-8"
        )
        assert "begin_step" in text or "CRITERIA" in text or "criteria" in text, script


@have_p9
def test_phase9_run_log_starts_with_the_unchanged_criteria_hash(monkeypatch):
    monkeypatch.setenv("SUPERR_PHASE", "phase9")
    log = store.read_run_log(PHASE9_DB)
    assert log.iloc[0]["step"] == "plan" and int(log.iloc[0]["seq"]) == 1
    assert set(log["criteria_sha256"]) == {CRIT_SHA}


def test_release_is_required_and_logged_without_touching_earlier_lock_logs(tmp_path):
    log = tmp_path / "release.json"
    with pytest.raises(lr.ReleaseError):
        lr.assert_test_released(log)
    before = {
        p.name: sha256_file(p) for p in (lr.PHASE4_LOCK_LOG, lr.PHASE5_LOCK_LOG) if p.exists()
    }
    ev = lr.release_test_lock(log, date="2026-11-18")
    assert ev["event"] == "RELEASE" and ev["reason"] == "owner decision phase 9"
    assert ev["pristine_holdout_remaining"] is False
    assert ev["criteria_sha256"] == CRIT_SHA
    assert lr.assert_test_released(log)["seq"] == 1
    assert lr.release_test_lock(log) == ev  # idempotent, append-only
    after = {p.name: sha256_file(p) for p in (lr.PHASE4_LOCK_LOG, lr.PHASE5_LOCK_LOG) if p.exists()}
    assert before == after


def test_recorded_release_exists_and_phase4_lock_log_is_unchanged():
    events = lr.read_release_events()
    rel = [e for e in events if e["event"] == "RELEASE"]
    assert len(rel) == 1 and rel[0]["reason"] == "owner decision phase 9"
    assert rel[0]["phase4_lock_log_sha256"] == sha256_file(lr.PHASE4_LOCK_LOG)
    p4 = json.loads(lr.PHASE4_LOCK_LOG.read_text(encoding="utf-8"))
    assert [e["event"] for e in p4] == ["FREEZE", "OPEN", "CLOSE"]  # old logs are not deleted
    text = (REPORTS_DIR / "phase9_owner_decisions.md").read_text(encoding="utf-8")
    assert "OWNER ATTESTATION" in text and "No pristine hold-out" in text


def test_loader_refuses_the_2026_period_without_a_release(monkeypatch):
    def deny(*_a, **_k):
        raise lr.ReleaseError("no release")

    monkeypatch.setattr(lr, "assert_test_released", deny)
    with pytest.raises(lr.ReleaseError):
        load_pre_test_deliveries(phase9=True)


# ------------------------------------------------------------------ data window
@pytest.fixture(scope="module")
def frames():
    if not (EXPLORATORY_DB.exists() and OFFICIAL_DB.exists()):
        pytest.skip("databases absent")
    d9, e9 = load_pre_test_deliveries(phase9=True)
    d8, e8 = load_pre_test_deliveries(phase9=False)
    return d9, e9, d8, e8


@have_db
def test_2026_matches_are_in_the_scoring_window_and_period_labels_are_never_test(frames):
    d9, _e9, d8, _e8 = frames
    assert "TEST" not in set(d9["period"]) and "TEST" not in set(d8["period"])
    t = d9[d9["period_src"] == "TEST"]
    assert t["match_id"].nunique() >= 130 and t["match_date"].min() >= pd.Timestamp("2026-01-01")
    assert set(t["competition_type"]) == {"IPL", "T20I"}  # OTHER_T20 stays out of scope
    assert (t["fit_group"] == "VALIDATION").all()
    assert (d9.loc[d9["match_date"] <= PHASE9_FIT_END, "fit_group"] == "TRAIN").all()
    assert (d9.loc[d9["match_date"] <= PHASE9_TRAIN_END, "period"] == "TRAIN").all()
    assert (d9.loc[d9["match_date"] > PHASE9_TRAIN_END, "period"] == "VALIDATION").all()
    assert d9["match_date"].max() <= pd.Timestamp("2026-11-01")


@have_db
def test_the_late_dated_t20i_matches_are_included(frames):
    d9, _e9, d8, _e8 = frames
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        late = set(
            con.execute("SELECT match_id FROM p5_t20i_date_verification WHERE late_after_cutoff")
            .df()["match_id"]
            .tolist()
        )
    finally:
        con.close()
    assert len(late) == 42
    assert len(late & set(d9["match_id"])) >= 38  # the rest carry only restricted rows
    assert not (late & set(d8["match_id"]))
    assert d9["match_date"].between("2026-06-01", "2026-11-01").any()  # dates are unchanged


@have_db
def test_existing_data_quality_restrictions_still_apply_to_2026(frames):
    d9, e9, d8, e8 = frames
    assert d9["innings_number"].isin([1, 2]).all()
    assert d9["competition_type"].isin(["IPL", "T20I"]).all()
    assert not d9["dls_exclude_primary"].fillna(False).astype(bool).any()
    assert d9["regulation_pressure_eligible"].fillna(False).astype(bool).all()
    reasons = set(e9["reason"])
    assert {"RESTRICTED_INNINGS_3_4_SUPER_OVER", "DLS_NOT_RECONSTRUCTABLE"} <= reasons
    assert "LATE_DATED_T20I_MATCH" not in reasons  # the exclusion no longer applies (D1)
    assert "LATE_DATED_T20I_MATCH" not in set(e8["reason"])
    assert d9["ok_wicket_target"].dtype == bool and d9["ok_run_target"].dtype == bool


@have_db
def test_phase8_loader_default_is_unchanged_and_never_loads_2026(frames):
    d9, _e9, d8, _e8 = frames
    assert "fit_group" not in d8.columns and set(d8["period"]) == {"TRAIN", "VALIDATION"}
    assert d8["match_date"].max() <= pd.Timestamp("2025-12-31")
    assert len(d8) == 158588 and d8["match_id"].nunique() == 675  # the Phase 8 figures
    key = ["match_id", "innings_number", "innings_ball_num"]
    pre = d9[d9["period_src"] != "TEST"].set_index(key)
    assert set(d8.set_index(key).index) - set(pre.index) == set()  # Phase 8 rows are a subset


@have_db
def test_every_delivery_is_scored_by_a_model_that_did_not_see_its_match(frames):
    d9 = frames[0]
    pos = np.arange(len(d9))
    folds = (d9["match_id"].astype("int64") % 5).to_numpy()
    grp = fit_group(d9).to_numpy()
    covered = np.zeros(len(d9), dtype=bool)
    fit_matches = set(d9.loc[grp == "TRAIN", "match_id"])
    for label, rows, fold in model_groups(d9):
        covered[rows] = True
        scored = set(d9.iloc[rows]["match_id"])
        if fold is None:
            assert label == "VALIDATION" and not (scored & fit_matches)
            assert (d9.iloc[rows]["period_src"] == "TEST").all()
        else:
            fit_ids = set(d9.loc[(grp == "TRAIN") & (folds != fold), "match_id"])
            assert not (scored & fit_ids) and (folds[rows] == fold).all()
    assert covered.all() and len(pos) == int(covered.sum())


# ------------------------------------------------------------------ out-of-fold scoring (synthetic)
def _frame(n_matches=40, per=30, seed=4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    mids = np.repeat(np.arange(1, n_matches + 1), per)
    n = len(mids)
    df = pd.DataFrame(
        {
            "match_id": mids,
            "period": np.where(mids <= 20, "TRAIN", "VALIDATION"),
            "fit_group": np.where(mids <= 30, "TRAIN", "VALIDATION"),
            "innings_number": 1,
            "innings_phase": rng.choice(["powerplay", "middle", "death"], n),
            "wickets_remaining": rng.integers(1, 10, n),
            "legal_balls_bowled_before": rng.integers(1, 120, n),
            "striker_id": rng.integers(1, 8, n),
            "den_legal_inc": 1,
            "den_counts_as_ball_faced": 1,
            "ok_run_target": True,
            "ok_wicket_target": True,
            "out_batter_runs": rng.integers(0, 7, n),
            "out_is_four": False,
            "out_is_six": False,
            "out_is_wicket": rng.uniform(size=n) < 0.05,
            "den_bowler_charged_runs": rng.integers(0, 7, n),
            "den_bowler_credited_wicket": (rng.uniform(size=n) < 0.04).astype(int),
        }
    )
    df["out_dismissed_player_id"] = np.where(df["out_is_wicket"], df["striker_id"], pd.NA)
    df["out_dismissed_player_id"] = df["out_dismissed_player_id"].astype("Int64")
    return df


def test_score_target_with_fixed_choice_uses_fit_group_and_never_leaks():
    df = _frame()
    x = ex.prepare_features(df, ex.category_codes(df))
    fits: list[set[int]] = []
    scored: list[set[int]] = []

    def fit(kind_model, kind, params, x_fit, y_fit):
        fits.append(set(df.loc[x_fit.index, "match_id"]))
        model = ex.Predictor("const", kind, float(np.mean(y_fit)))

        def pred(xx):
            scored.append(set(df.loc[xx.index, "match_id"]))
            return model(xx)

        return pred

    r = ex.score_target(df, x, ex.spec_for("batter", "runs"), fit=fit, fixed=("const", {}))
    assert r["metrics"]["grid"] == []  # nothing is tuned on the held-out group
    assert r["chosen"] == "const" and r["params"] == {}
    assert all(m <= set(range(1, 31)) for m in fits)  # fits use the fit group only (matches to 30)
    assert r["metrics"]["n_validation"] == int(((df["fit_group"] == "VALIDATION") & r["pop"]).sum())
    assert r["expected"].notna().sum() == r["pop"].sum()
    # the five fold fits never contain the scored match
    for f_set, s_set in zip(fits[-5:], scored[-5:], strict=True):
        assert not (f_set & s_set)
    # the held-out group (matches 31-40) is not part of any fit
    assert not any(f_set & set(range(31, 41)) for f_set in fits)


def test_a_label_that_is_undefined_is_left_out_not_imputed():
    df = _frame()
    df.loc[5, "out_is_wicket"] = True
    df.loc[5, "out_dismissed_player_id"] = pd.NA
    x = ex.prepare_features(df, ex.category_codes(df))
    r = ex.score_target(
        df, x, ex.spec_for("batter", "wicket"), fit=lambda *a: ex.Predictor("const", a[1], 0.05),
        fixed=("const", {}),
    )  # fmt: skip
    assert np.isfinite(r["metrics"]["const_log_loss"])
    assert pd.isna(r["expected"].iloc[5]) or r["y"].isna().iloc[5]


# ------------------------------------------------------------------ strictly prior priors
def test_team_priors_use_only_strictly_earlier_matches_including_2026():
    m = pd.DataFrame(
        {
            "match_id": [1, 2, 3, 4, 5],
            "match_date": pd.to_datetime(
                ["2025-12-01", "2025-12-20", "2026-03-01", "2026-03-01", "2026-04-01"]
            ),
            "home_team_id": [1, 1, 1, 2, 1],
            "away_team_id": [2, 2, 2, 3, 2],
            "win_team_id": [1, 1, 2, 3, 1],
        }
    )
    base = compute_team_priors(m).set_index(["match_id", "team_id"])["prior_win_rate"]
    mut = m.copy()
    mut.loc[mut["match_id"] >= 3, "win_team_id"] = [1, 1, 2]
    after = compute_team_priors(mut).set_index(["match_id", "team_id"])["prior_win_rate"]
    for key in [(1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2)]:
        assert np.isclose(base[key], after[key], equal_nan=True), key
    assert np.isnan(base[(1, 1)])  # no earlier match: undefined, not zero
    # matches on the same date do not feed each other's prior: mutating match 4 leaves match 3 alone
    same_day = m.copy()
    same_day.loc[same_day["match_id"] == 4, "win_team_id"] = 2
    sd = compute_team_priors(same_day).set_index(["match_id", "team_id"])["prior_win_rate"]
    assert np.isclose(sd[(3, 2)], base[(3, 2)]) and np.isclose(sd[(3, 1)], base[(3, 1)])
    # a later match does see an earlier 2026 result
    flipped = compute_team_priors(m.assign(win_team_id=[1, 1, 1, 3, 1]))
    flipped = flipped.set_index(["match_id", "team_id"])["prior_win_rate"]
    assert not np.isclose(base[(5, 1)], flipped[(5, 1)])


# ------------------------------------------------------------------ status labels from thresholds
def _lab(sb, low, oot_low, floor=False, n=50):
    m = {"sb": sb, "sb_low": low, "oot_low": oot_low, "n_split": 100, "n_oot": 100}
    return list_status(load_criteria(), m, floor, n)["status"]


@pytest.mark.parametrize(
    ("sb", "low", "oot", "floor", "n", "expected"),
    [
        (0.27, -0.1, -0.1, False, 50, "EXPLORATORY"),  # Phase 9 bowlers' kind of evidence
        (0.499, 0.2, 0.2, False, 50, "EXPLORATORY"),
        (0.5, 0.01, 0.01, False, 50, "PROVISIONAL"),
        (0.5, 0.0, 0.1, False, 50, "EXPLORATORY"),  # lower bound must be above 0
        (0.69, 0.6, 0.5, False, 50, "PROVISIONAL"),
        (0.7, 0.5, 0.31, False, 50, "VALIDATED"),
        (0.7, 0.49, 0.5, False, 50, "PROVISIONAL"),
        (0.7, 0.6, 0.3, False, 50, "PROVISIONAL"),  # out-of-time lower bound must exceed 0.3
        (0.9, 0.8, 0.8, True, 50, "EXPLORATORY"),  # variance at the floor forces EXPLORATORY
        (0.9, 0.8, 0.8, False, 9, "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_status_label_follows_the_predeclared_thresholds(sb, low, oot, floor, n, expected):
    assert _lab(sb, low, oot, floor, n) == expected


@have_p9
def test_stored_labels_equal_the_threshold_rule_applied_to_the_stored_numbers():
    c = duckdb.connect(str(PHASE9_DB), read_only=True)
    try:
        cmp_ = c.execute("SELECT * FROM p9_method_comparison").df()
        st = c.execute("SELECT * FROM p9_top10_status").df()
        cap = c.execute("SELECT role, list_status_cap FROM p9_method_selection").df()
        cap = cap.set_index("role")
    finally:
        c.close()
    crit = load_criteria()
    for r in st.itertuples():
        m = cmp_[(cmp_.role == r.role) & (cmp_.approach == r.approach)].iloc[0]
        metrics = {"sb": m["sb"], "sb_low": m["sb_low"], "oot_low": m["oot_low"],
                   "n_split": m["n_split"], "n_oot": m["n_oot"]}  # fmt: skip
        exp = list_status(
            crit, metrics, bool(m["between_player_variance_at_floor"]), int(r.n_eligible)
        )
        want = exp["status"]
        if cap.loc[r.role, "list_status_cap"] == "EXPLORATORY" and want in (
            "PROVISIONAL",
            "VALIDATED",
        ):
            want = "EXPLORATORY"  # the declared cap when no approach has a positive lower bound
        assert r.list_status == want
        if m["sb"] < 0.5:
            assert r.list_status == "EXPLORATORY"
    lists = {
        "batter": pd.read_csv(REPORTS_DIR / "pressure_batters_top10.csv"),
        "bowler": pd.read_csv(REPORTS_DIR / "pressure_bowlers_top10.csv"),
    }
    for role, d in lists.items():
        label = st.set_index("role").loc[role, "list_status"]
        assert set(d["list_status"]) == {label} and len(d) <= 10
        assert set(d["methodology_version"]) == {"phase9_methodology_v1"}
        assert set(d["criteria_sha256"]) == {CRIT_SHA}


# ------------------------------------------------------------------ models and preservation
@pytest.mark.skipif(not (MODELS_DIR / "p9_wp_v1.json").exists(), reason="p9 models absent")
def test_p9_models_use_the_phase8_hyperparameters_and_are_separate_files():
    for s in ex.SPECS:
        stem = f"expected_{s.role}_{s.name}_v1"
        m9 = json.loads((MODELS_DIR / f"p9_{stem}.json").read_text(encoding="utf-8"))
        learner, params = phase8_expected_choice(s.role, s.name)
        assert m9["algorithm"] == learner and json.loads(m9["params"]) == params
        assert (MODELS_DIR / f"p8_{stem}.joblib").exists()
        assert "2025-12-31" in m9["trained_on"]
    w9 = json.loads((MODELS_DIR / "p9_wp_v1.json").read_text(encoding="utf-8"))
    for k in ("W1", "W2"):
        assert w9["training"][k]["params"] == phase8_wp_params(k)


@have_p9
def test_2026_out_of_time_check_is_labelled_and_reproducible():
    c = duckdb.connect(str(PHASE9_DB), read_only=True)
    try:
        chk = c.execute("SELECT * FROM p9_2026_check").df()
        rep = c.execute("SELECT * FROM p9_reproducibility").df()
    finally:
        c.close()
    assert len(chk) == 10 and chk["label"].str.startswith("2026 out-of-time check").all()
    assert chk["label"].str.contains("released by owner decision").all()
    assert len(rep) == 10 and rep["identical"].all() and (rep["max_abs_diff"] == 0).all()


def test_store_refuses_to_write_phase9_tables_into_the_phase8_database(monkeypatch):
    monkeypatch.setenv("SUPERR_PHASE", "phase9")
    with pytest.raises(StoreError):
        store.append_run_log("x", CRIT_SHA, store_path=PHASE8_DB)
    assert translate_table("p8_rankings") == "p9_rankings"


def test_phase8_submission_files_are_preserved_as_copies():
    rec = json.loads((TASKS / "phase9_report_hashes.json").read_text(encoding="utf-8"))
    checked = 0
    for name, digest in rec.items():
        p = Path(name)
        cp = p.with_name(f"{p.stem}_phase8{p.suffix}")
        if cp.exists():
            assert sha256_file(cp) == digest, cp.name
            checked += 1
    assert checked >= 15


def test_protected_files_are_unchanged():
    rec = json.loads((TASKS / "phase9_prehash.json").read_text(encoding="utf-8"))
    assert len(rec) >= 30
    for name, digest in rec.items():
        assert sha256_file(Path(name)) == digest, name


@have_p9
def test_descriptive_profiles_cover_the_2026_window():
    pm = pd.read_csv(REPORTS_DIR / "phase7_descriptive_player_match.csv", usecols=["match_date"])
    assert pm["match_date"].max() >= "2026-06-01"
    b = pd.read_csv(REPORTS_DIR / "descriptive_batter_profiles.csv", usecols=["window"])
    assert b["window"].str.contains("2026-11-01").all()
    old = pd.read_csv(REPORTS_DIR / "descriptive_batter_profiles_phase8.csv", usecols=["window"])
    assert not old["window"].str.contains("2026-11-01").any()
