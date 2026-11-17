"""Phase 5 Chunk 3 tests: reliability, variance decomposition, sensitivity grid, ranking stability.

Synthetic data with known variance components; independent numpy implementations; determinism;
labelling; and static checks that the investigation code never touches TEST or Cricsheet.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase4 import definitions as df_
from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase5 import reliability as rb
from app.phase5 import sensitivity as sn
from app.phase5 import spotchecks as spc
from app.phase5 import stability as stb
from app.phase5.constants import CONFIG_DIR, REPORTS_DIR

APP = Path(__file__).resolve().parents[1] / "app" / "phase5"
CHUNK3_MODULES = (
    "reliability",
    "investigation",
    "pressure_signals",
    "sensitivity",
    "stability",
    "pipeline",
    "outputs",
    "spotchecks",
)


# ---------------------------------------------------------------- synthetic data
def synth(players=400, matches=20, balls=5, tau2=0.04, sigma2=1.0, seed=1) -> rb.CellData:
    """Every player in every match with ``balls`` balls; true player effect ~ N(0, tau2)."""
    rng = np.random.default_rng(seed)
    mu = rng.normal(0.0, np.sqrt(tau2), players)
    N = np.full((players, matches), float(balls))
    S = mu[:, None] * N + rng.normal(0.0, np.sqrt(sigma2 * balls), (players, matches))
    # per-ball squared sums consistent with the per-match noise: sum of squares of balls
    S2 = np.maximum(sigma2 * balls + (S**2) / N, 0.0) * 1.0
    dates = pd.date_range("2023-01-01", periods=matches).to_numpy()
    return rb.CellData(
        np.arange(players), np.arange(matches), dates, np.array(["TRAIN"] * matches), N, S, S2
    )


def ball_level_cell(players=300, matches=16, balls=4, tau2=0.05, sigma2=1.0, seed=2):
    """Ball-level rows -> Phase 4 Cell, so S2 is exact."""
    rng = np.random.default_rng(seed)
    mu = rng.normal(0.0, np.sqrt(tau2), players)
    rows = []
    for m in range(matches):
        per = "TRAIN" if m < matches // 2 else "VALIDATION"
        resid = (mu[:, None] + rng.normal(0.0, np.sqrt(sigma2), (players, balls))).ravel()
        rows.append(pd.DataFrame({"player_id": np.repeat(np.arange(players), balls), "match_id": m,
                                  "comp": "IPL", "period": per, "date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=m),
                                  "resid": resid}))  # fmt: skip
    r = pd.concat(rows, ignore_index=True)
    return en.build_cell(r, "IPL", "batter", "runs"), r


# ---------------------------------------------------------------- variance components and ICC
def exact_cd(players=800, matches=20, balls=5, tau2=0.04, sigma2=1.0, seed=11) -> rb.CellData:
    cell, _ = ball_level_cell(
        players=players, matches=matches, balls=balls, tau2=tau2, sigma2=sigma2, seed=seed
    )
    return rb.from_cell(cell)


def test_decomposition_recovers_known_components():
    cd = exact_cd()
    dec = rb.decompose_moments(rb.boot_moments(cd, np.ones((cd.N.shape[1], 1))), 1)
    # true sigma2 = 1, noise of a player mean = 1 / (20 * 5) = 0.01, so true ICC = 0.04 / 0.05 = 0.8
    assert dec["sigma2"][0] == pytest.approx(1.0, abs=0.03)
    assert dec["ball_independent_noise_mean"][0] == pytest.approx(0.01, abs=0.001)
    assert dec["ball_independent_tau2"][0] == pytest.approx(0.04, abs=0.008)
    assert dec["ball_independent_icc"][0] == pytest.approx(0.8, abs=0.06)
    assert dec["match_cluster_tau2"][0] == pytest.approx(0.04, abs=0.01)


def test_phase4_basis_is_negative_when_kish_units_are_matches():
    """The Phase 4 noise divides a per-ball variance by a Kish count of matches: noise is inflated."""
    cd = exact_cd()
    dec = rb.decompose_moments(rb.boot_moments(cd, np.ones((cd.N.shape[1], 1))), 1)
    assert dec["phase4_kish_noise_mean"][0] == pytest.approx(1.0 / 20, rel=0.1)
    # the inflated noise absorbs essentially all of the true between-player variance (true tau2 = 0.04)`n    assert dec["phase4_kish_tau2"][0] < 0.01 < 0.03 < dec["ball_independent_tau2"][0]


def test_zero_between_variance_is_not_estimated_as_positive_signal():
    cd = exact_cd(tau2=0.0, seed=5)
    dec = rb.decompose_moments(rb.boot_moments(cd, np.ones((cd.N.shape[1], 1))), 1)
    assert abs(dec["ball_independent_tau2"][0]) < 0.008
    assert dec["ball_independent_icc"][0] < 0.45


def test_variance_rows_label_and_status_when_tau2_not_positive():
    cd = synth(tau2=0.0, sigma2=1.0, balls=5, matches=20, seed=6)
    w = en.cell_weights  # noqa: F841 - keep import used
    W = np.random.default_rng(0).multinomial(20, np.full(20, 0.05), size=50).astype(float).T
    rows = rb.variance_rows(cd, W, "TRAIN", [1])
    p4 = next(r for r in rows if r["noise_basis"] == "phase4_kish")
    assert p4["status"] in (rb.BETWEEN_NOT_POSITIVE, rb.NOT_ESTIMABLE)
    assert all("EXPERIMENTAL_NOT_VALIDATED" in r["label"] for r in rows)


# ---------------------------------------------------------------- split-half
def test_split_half_matches_known_reliability():
    cd = synth(tau2=0.04, sigma2=1.0, balls=5, matches=20)
    # half mean noise = sigma2 / (10 matches * 5 balls) = 0.02, so r_half = 0.04 / 0.06 and SB = 0.8
    r = rb.split_half(cd, "TRAIN", "odd_even", 6, None, 0)
    assert r["status"] == rb.ESTIMATED
    assert r["sb_pearson"] == pytest.approx(0.8, abs=0.06)
    assert r["r_pearson"] == pytest.approx(0.04 / 0.06, abs=0.06)


def numpy_loop_split_half(cd: rb.CellData, min_balls: int):
    a, b = [], []
    for i in range(cd.N.shape[0]):
        idx = [j for j in range(cd.N.shape[1]) if cd.N[i, j] > 0]
        odd, even = idx[0::2], idx[1::2]
        n1, n2 = cd.N[i, odd].sum(), cd.N[i, even].sum()
        if n1 >= min_balls and n2 >= min_balls:
            a.append(cd.S[i, odd].sum() / n1)
            b.append(cd.S[i, even].sum() / n2)
    r = float(np.corrcoef(a, b)[0, 1])
    return len(a), r, 2 * r / (1 + r)


def test_split_half_agrees_with_independent_numpy_loop_incl_sparse_players():
    cd = synth(players=120, matches=18, balls=4, tau2=0.05, seed=9)
    rng = np.random.default_rng(3)
    drop = rng.random(cd.N.shape) < 0.4  # sparse participation, uneven halves
    cd.N[drop] = 0.0
    cd.S[drop] = 0.0
    cd.S2[drop] = 0.0
    n, r, sbv = numpy_loop_split_half(cd, 6)
    res = rb.split_half(cd, "TRAIN", "odd_even", 6, None, 0)
    assert res["players"] == n
    assert res["r_pearson"] == pytest.approx(r, abs=1e-12)
    assert res["sb_pearson"] == pytest.approx(sbv, abs=1e-12)


def test_split_half_agrees_with_pandas_spotcheck_on_ball_rows():
    cell, rows = ball_level_cell()
    cd = rb.from_cell(cell)
    mine = rb.split_half(cd, "PRE_TEST", "odd_even", 6, None, 0)
    ind = spc.independent_odd_even(rows, "IPL", ("TRAIN", "VALIDATION"), 6)
    assert mine["players"] == ind["players"]
    assert mine["r_pearson"] == pytest.approx(ind["r"], abs=1e-12)


def test_split_half_too_few_players_is_not_estimable():
    cd = synth(players=5, matches=20)
    assert rb.split_half(cd, "TRAIN", "odd_even", 6, None, 0)["status"] == rb.NOT_ESTIMABLE


def test_spearman_brown():
    assert float(rb.sb(0.5)) == pytest.approx(2 * 0.5 / 1.5)
    assert float(rb.sb(0.0)) == 0.0


def test_early_late_and_random_modes_run_and_random_is_seeded():
    cd = synth(players=150, matches=20, tau2=0.05)
    el_ = rb.split_half(cd, "TRAIN", "early_late", 6, None, 0)
    assert el_["status"] == rb.ESTIMATED
    r1 = rb.split_half(cd, "TRAIN", "random", 6, None, 123, n_random=30)
    r2 = rb.split_half(cd, "TRAIN", "random", 6, None, 123, n_random=30)
    r3 = rb.split_half(cd, "TRAIN", "random", 6, None, 124, n_random=30)
    assert r1["sb_pearson"] == r2["sb_pearson"]
    assert r1["sb_pearson"] != r3["sb_pearson"]


# ---------------------------------------------------------------- bootstrap determinism
def test_bootstrap_weights_and_intervals_are_deterministic():
    gm1, W1 = en.global_weights(np.arange(20), 100, 20260512)
    gm2, W2 = en.global_weights(np.arange(20), 100, 20260512)
    gm3, W3 = en.global_weights(np.arange(20), 100, 7)
    assert np.array_equal(W1, W2) and not np.array_equal(W1, W3)
    cd = synth(players=150, matches=20, tau2=0.05)
    a = rb.split_half(cd, "TRAIN", "odd_even", 6, W1.T, 0)
    b = rb.split_half(cd, "TRAIN", "odd_even", 6, W2.T, 0)
    assert (a["sb_lo"], a["sb_hi"]) == (b["sb_lo"], b["sb_hi"])
    assert (
        0.0 < a["sb_lo"] < a["sb_hi"] < 1.0
    )  # percentile intervals need not bracket the point value


# ---------------------------------------------------------------- projections
def test_required_sample_hand_values_and_not_estimable():
    out = rb.required_sample(0.01, 1.0, (0.5, 0.8), "balls")
    assert out[0]["required_n"] == pytest.approx(100.0)
    assert out[1]["required_n"] == pytest.approx(400.0)
    assert all(o["label"] == "DESCRIPTIVE_PROJECTION" for o in out)
    for bad in (0.0, -0.3, None, float("nan")):
        assert all(
            o["required_n"] == rb.NOT_ESTIMABLE
            for o in rb.required_sample(bad, 1.0, (0.5,), "balls")
        )
    assert rb.required_sample(0.01, None, (0.5,), "balls")[0]["required_n"] == rb.NOT_ESTIMABLE


def test_detectability_simulation_seeded_and_monotone():
    noise = np.full(200, 0.01)
    a = rb.simulate_detectability(noise, 1.0, [0.0005, 0.025], 300, 1)
    b = rb.simulate_detectability(noise, 1.0, [0.0005, 0.025], 300, 1)
    assert a == b
    assert a[0]["share_estimate_positive"] < a[1]["share_estimate_positive"]
    assert a[1]["share_estimate_positive"] > 0.95
    assert (
        rb.simulate_detectability(np.array([0.1]), 1.0, [0.01], 10, 0)[0]["status"]
        == rb.NOT_ESTIMABLE
    )


# ---------------------------------------------------------------- pooling
def test_pooling_uses_only_players_in_both_formats():
    a, b = synth(players=60, matches=12, seed=3), synth(players=60, matches=12, seed=4)
    b.players = b.players + 30  # overlap: ids 30..59
    b.dates = b.dates + np.timedelta64(400, "D")
    a_s, b_s, pooled, _ = rb.pool_cells(a, b, "TRAIN")
    assert set(a_s.players) == set(b_s.players) == set(pooled.players) == set(range(30, 60))
    assert pooled.N.shape[1] == 24
    assert np.all(np.diff(pooled.dates.astype("datetime64[D]").astype(int)) >= 0)
    res = rb.multi_format_pooling(a, b, "TRAIN", 6, 10)
    assert res["players_in_both_formats"] == 30


# ---------------------------------------------------------------- sensitivity grid
def test_definition_grid_includes_primary_and_named_alternatives():
    rule = df_.load_rule()
    cfg = json.loads((CONFIG_DIR / "phase5_investigation_v1.json").read_text(encoding="utf-8"))
    ids = df_.definition_ids(rule)
    assert len(ids) == 9
    assert cfg["definitions"]["primary"] == "any|q0.75"
    assert set(cfg["definitions"]["alternatives"]) == {"chase|q0.9", "any|q0.9", "chase|q0.75"}
    assert {cfg["definitions"]["primary"], *cfg["definitions"]["alternatives"]} <= set(ids)
    assert "PROVISIONAL" in cfg["definitions"]["primary_label"]
    assert len(sh.CONFIGS) == 7
    assert cfg["sensitivity"]["named_definitions_for_shrinkage_cross"] == [
        "any|q0.75", "chase|q0.9", "any|q0.9", "chase|q0.75"]  # fmt: skip


def test_eight_format_weight_configs_sum_to_one():
    w = json.loads((CONFIG_DIR / "format_weights_v1.json").read_text(encoding="utf-8"))
    assert len(w["configurations"]) == 8
    assert all(abs(c["ipl_weight"] + c["t20i_weight"] - 1.0) < 1e-12 for c in w["configurations"])


def test_compare_identical_reversed_and_disjoint():
    ids = np.arange(1, 31)
    ref = pd.Series(np.arange(30, 0, -1, dtype=float), index=ids)
    same = sn.compare(ref, ref)
    assert (
        same["top_k_overlap"] == 10
        and same["spearman"] == pytest.approx(1.0)
        and same["kendall_tau"] == pytest.approx(1.0)
    )
    rev = sn.compare(ref, pd.Series(np.arange(1, 31, dtype=float), index=ids))
    assert (
        rev["top_k_overlap"] == 0
        and rev["spearman"] == pytest.approx(-1.0)
        and rev["kendall_tau"] == pytest.approx(-1.0)
    )
    small = sn.compare(ref.iloc[:6], ref.iloc[:6])
    assert small["top_k"] == 6 and small["top_k_trivial_full_pool"] is True
    empty = sn.compare(ref.iloc[:0], ref)
    assert empty["top_k_overlap"] is None and empty["spearman"] is None


def test_topk_ties_break_by_player_id_and_kendall_hand_value():
    s = pd.Series([1.0, 1.0, 1.0, 0.5], index=[7, 3, 5, 1])
    assert sn.topk_ids(s, 3) == [3, 5, 7]
    assert sn.kendall_tau(np.array([1.0, 2, 3, 4]), np.array([1.0, 3, 2, 4])) == pytest.approx(
        (5 - 1) / 6
    )


def test_combined_scores_never_zero_fill_players_missing_in_a_format():
    run = {
        ("IPL", "batter"): {"scores": pd.Series([1.0, 2.0, 3.0], index=[1, 2, 3])},
        ("T20I", "batter"): {"scores": pd.Series([5.0, 6.0], index=[2, 9])},
    }
    c = sn.combined_scores(run, "batter", 0.7)
    assert list(c.index) == [2] and c[2] == pytest.approx(0.7 * 2.0 + 0.3 * 5.0)
    assert sn.combined_scores(run, "bowler", 0.7).empty


def test_test_set_comparison_is_counts_only(tmp_path):
    m = {"status": "S", "test_evaluated_in_phase5": False,
         "sets": {"A": {"rule": "r", "counts": {"matches": 3, "deliveries": 30, "players": 9,
                                                "by_competition_type": {"IPL": {"matches": 2}, "T20I": {"matches": 1}}}}}}  # fmt: skip
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    out = sn.test_set_comparison(p)
    assert (
        out["sets"][0]["matches_T20I"] == 1
        and out["status"] == "SET_DEFINITIONS_ONLY_NO_TEST_OUTCOMES"
    )
    assert set(out["sets"][0]) == {
        "set",
        "rule",
        "matches",
        "deliveries",
        "players",
        "matches_IPL",
        "matches_T20I",
    }
    assert sn.test_set_comparison(tmp_path / "none.json")["status"] == "MANIFEST_MISSING"


# ---------------------------------------------------------------- ranking stability
RULE = {"threshold_balls": 8, "label": "ELIGIBLE_WORKING_POOL_NOT_VALIDATED", "wr": 1.0}


def test_stability_is_deterministic_and_inclusion_probabilities_are_sane():
    cell, _ = ball_level_cell(players=60, matches=16, balls=4, tau2=0.1)
    gm, W = en.global_weights(cell.matches, 200, 20260512)
    a = stb.cell_stability(cell, RULE, "shrink_tau4", gm, W)
    b = stb.cell_stability(cell, RULE, "shrink_tau4", gm, W)
    pd.testing.assert_frame_equal(a["players"], b["players"])
    assert a["summary"] == b["summary"]
    t = a["players"]
    assert t["top10_inclusion_prob"].between(0, 1).all()
    assert t["top10_inclusion_prob"].sum() == pytest.approx(10.0, abs=0.5)
    assert (t["rank_lo"] <= t["rank_median"]).all() and (t["rank_median"] <= t["rank_hi"]).all()
    assert list(t["point_rank"]) == sorted(t["point_rank"])
    s = a["summary"]
    assert 0 <= s["expected_overlap_with_point_top10"] <= 10
    assert 0 <= s["expected_overlap_two_independent_bootstrap_top10"] <= 10
    assert "EXPERIMENTAL_NOT_VALIDATED" in s["label"]


def test_stability_never_pads_small_pool():
    cell, _ = ball_level_cell(players=7, matches=16, balls=4)
    gm, W = en.global_weights(cell.matches, 100, 1)
    r = stb.cell_stability(cell, RULE, "shrink_tau4", gm, W)
    assert r["summary"]["pool_size"] == 7 and r["summary"]["trivial_full_pool"] is True
    assert len(r["players"]) == 7
    assert r["players"]["top10_inclusion_prob"].min() > 0.9  # everyone is in a Top 10 of 7
    empty = stb.cell_stability(cell, {**RULE, "threshold_balls": 10_000}, "shrink_tau4", gm, W)
    assert empty["summary"]["status"] == "POOL_EMPTY" and empty["players"].empty
    none_rule = stb.cell_stability(cell, {**RULE, "threshold_balls": None}, "shrink_tau4", gm, W)
    assert none_rule["summary"]["pool_size"] == 0


def test_perfectly_separated_players_have_stable_top10():
    rows = []
    for m in range(12):
        for p in range(30):
            rows.append({"player_id": p, "match_id": m, "comp": "IPL", "period": "TRAIN",
                         "date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=m), "resid": 10.0 * p + (m % 2) * 0.01})  # fmt: skip
    cell = en.build_cell(pd.DataFrame(rows), "IPL", "batter", "runs")
    gm, W = en.global_weights(cell.matches, 200, 3)
    r = stb.cell_stability(
        cell, {"threshold_balls": 1, "label": "x", "wr": 1.0}, "shrink_none", gm, W
    )
    assert r["summary"]["expected_overlap_with_point_top10"] == pytest.approx(10.0, abs=0.01)
    assert r["summary"]["expected_overlap_two_independent_bootstrap_top10"] == pytest.approx(
        10.0, abs=0.01
    )


def test_paired_overlap_and_context_rule():
    sd = np.vstack([np.arange(20, 0, -1.0)] * 4).T
    po = stb.paired_overlap(sd, np.isfinite(sd))
    assert list(po) == [10.0, 10.0]
    cell, _ = ball_level_cell(players=40)
    rule = stb.context_rule(cell, [6, 12, 24])
    assert rule["label"].endswith("NOT_VALIDATED") and rule["threshold_balls"] >= 1
    assert stb.MIN_TRAIN_PLAYERS_FOR_FIT == 8


# ---------------------------------------------------------------- no TEST, no Cricsheet, labelling
def _imports(path: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


@pytest.mark.parametrize("name", CHUNK3_MODULES)
def test_chunk3_modules_do_not_import_cricsheet_or_open_test(name):
    src = (APP / f"{name}.py").read_text(encoding="utf-8")
    imps = _imports(APP / f"{name}.py")
    assert not any("cricsheet" in i.lower() or "date_verification" in i for i in imps)
    for forbidden in (
        "evaluate_on_test",
        "evaluate_frozen",
        "_open_for_evaluation",
        "write_frozen_choices",
        "evaluate_test_scores",
    ):
        assert forbidden not in src
    assert "train_test_split" not in src


def test_chunk3_scripts_never_open_test_or_write_lock_logs():
    for s in ("phase5_investigation", "phase5_sensitivity", "phase5_ranking_stability"):
        src = (Path(__file__).resolve().parents[1] / "scripts" / f"{s}.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "evaluate_on_test",
            "evaluate_frozen",
            "run_phase4",
            "cricsheet",
            "write_frozen_choices",
        ):
            assert (
                forbidden not in src.lower()
                or forbidden == "cricsheet"
                and "Cricsheet: not used" in src
            )


def test_pipeline_drops_test_rows_before_any_frame_exists():
    src = (APP / "pipeline.py").read_text(encoding="utf-8")
    assert "drop_test_rows(" in src and "TEST rows reached" in src


def test_investigation_config_is_labelled_provisional_and_declared_before_runs():
    cfg = json.loads((CONFIG_DIR / "phase5_investigation_v1.json").read_text(encoding="utf-8"))
    assert cfg["status"] == "EXPERIMENTAL_NOT_VALIDATED" and cfg["declared_before_any_run"] is True
    assert cfg["data_used"] == ["TRAIN", "VALIDATION"] and cfg["test_outcomes_used"] is False
    assert "SENSITIVITY_ONLY" in cfg["bowler_signal_candidates"]["label"]
    assert len(cfg["bowler_signal_candidates"]["candidates"]) == 3


# ---------------------------------------------------------------- real-data report checks
REPORTS = (
    "phase5_investigation_report.md",
    "phase5_sensitivity_report.md",
    "phase5_ranking_stability.md",
)


@pytest.mark.realdata
@pytest.mark.parametrize("name", REPORTS)
def test_reports_exist_are_labelled_and_never_claim_validation(name):
    p = REPORTS_DIR / name
    if not p.exists():
        pytest.skip("run the Phase 5 chunk 3 scripts first")
    t = p.read_text(encoding="utf-8")
    assert "EXPERIMENTAL_NOT_VALIDATED" in t and "PROVISIONAL" in t
    low = t.lower()
    for bad in (
        "official top 10",
        "superior to",
        "demonstrably",
        "has been validated",
        "was validated",
    ):
        assert bad not in low
    negators = ("not ", "no ", "nothing", "never", "none", "cannot", "until", "without", "un")
    for m in re.finditer(r"\bvalidated\b", low):
        assert any(n in low[max(0, m.start() - 45) : m.start()] for n in negators), low[
            m.start() - 60 : m.end()
        ]
    assert "Unresolved issues" in t and "Gates still failing" in t
    assert "data_weight_gate_passed" in t


@pytest.mark.realdata
def test_split_half_spotcheck_recorded_and_agrees():
    p = REPORTS_DIR / "phase5_investigation_spotcheck.json"
    if not p.exists():
        pytest.skip("run scripts/phase5_investigation.py first")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["split_half_agrees"] and d["snr_agrees"]
    assert d["split_half"]["abs_diff_r"] < 1e-9
