"""Eligibility harness tests on synthetic data (plus proxy extraction on an in-memory DuckDB)."""

from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest

from app.analytics import confidence_engine as ce
from app.analytics.integrity import (
    IntegrityError,
    assert_unchanged,
    open_official_readonly,
    snapshot_official,
)
from app.analytics.proxy_samples import ProxySamples, extract_samples
from app.analytics.ranking import movement, rank_players, spearman_common, topk_overlap
from app.analytics.reporting import round_floats
from app.analytics.shrinkage import eb_shrink, n_eff_kish, n_eff_shrink
from app.core.config import BACKEND_ROOT
from app.core.database import connect

RULES_PATH = BACKEND_ROOT / "config" / "eligibility_rules_v1.json"


@pytest.fixture()
def rules() -> dict:
    return ce.load_rules(RULES_PATH)


def _rows(rng, fmt, id0, n_players, match0, n_matches, role):
    out = []
    for p in range(n_players):
        k = int(rng.integers(1, n_matches + 1))
        for m in rng.choice(n_matches, size=k, replace=False):
            n = int(rng.integers(1, 25))
            x = rng.choice([0, 1, 2, 4, 6], size=n, p=[0.4, 0.3, 0.1, 0.12, 0.08])
            row = {
                "format": fmt,
                "player_id": id0 + p,
                "match_id": match0 + int(m),
                "n": n,
                "legal_balls": max(0, n - 1),
                "innings": 1,
            }
            if role == "batter":
                row.update(runs_sum=float(x.sum()), runs_sum2=float((x**2).sum()))
            else:
                w = int((rng.random(n) < 0.05).sum())
                row.update(
                    econ_sum=float(x.sum()),
                    econ_sum2=float((x**2).sum()),
                    wkt_sum=float(w),
                    wkt_sum2=float(w),
                )
            out.append(row)
    return pd.DataFrame(out)


def synthetic_samples(seed: int = 1) -> ProxySamples:
    rng = np.random.default_rng(seed)
    bat = pd.concat(
        [
            _rows(rng, "IPL", 1, 60, 1000, 40, "batter"),
            _rows(rng, "T20I", 1, 60, 2000, 40, "batter"),
        ],
        ignore_index=True,
    )
    bowl = pd.concat(
        [
            _rows(rng, "IPL", 1, 40, 1000, 40, "bowler"),
            _rows(rng, "T20I", 1, 40, 2000, 40, "bowler"),
        ],
        ignore_index=True,
    )
    window = {f: {"matches_with_deliveries": 40, "first_date": "2022", "last_date": "2026"}
              for f in ("IPL", "T20I")}  # fmt: skip
    return ProxySamples(bat, bowl, window, {i: f"P{i}" for i in range(1, 70)}, [])


def small_rules(rules: dict) -> dict:
    r = copy.deepcopy(rules)
    r["distribution_formats"] = ["IPL", "T20I"]
    r["n_boot"] = 12
    r["ladders"]["batter"].update(balls=[20, 60], matches=[3, 6], innings=[3, 6], n_eff_shrink=[10])
    r["ladders"]["bowler"].update(balls=[20, 60], matches=[3, 6], innings=[3, 6], n_eff_shrink=[10])
    return r


# ------------------------------------------------------------------------------ candidates


def test_percentile_thresholds_on_known_distribution():
    cands = ce.percentile_candidates(range(1, 101), [10, 25, 50, 75])
    assert [c["value"] for c in cands] == [11, 26, 51, 76]
    assert [c["label"] for c in cands] == ["P10", "P25", "P50", "P75"]


def test_practical_candidates_filtering_and_reasons():
    vals = range(1, 101)
    pc = ce.percentile_candidates(vals, [10, 25, 50, 75])
    pr = ce.practical_candidates([5, 11, 30, 50, 95], vals, pc, 0.05)
    kept = {p["value"]: p for p in pr}
    assert kept[30]["kept"] and "30 lies at observed percentile" in kept[30]["justification"]
    assert kept[5]["drop_reason"] == "below_observed_p10"
    assert kept[95]["drop_reason"] == "above_observed_p90"
    assert kept[11]["drop_reason"].startswith("within_5pct_of_P10")
    assert kept[50]["drop_reason"].startswith("within_5pct_of_P50")
    ladder = ce.build_ladder(pc, pr)
    assert [e["value"] for e in ladder] == sorted({e["value"] for e in ladder})
    assert 30 in [e["value"] for e in ladder]


def test_pool_verdict_edges():
    kw = dict(list_size=10, pool_min_absolute=30, multiplier=3)
    assert ce.pool_verdict(29, **kw)["sufficient"] is False
    assert ce.pool_verdict(30, **kw)["sufficient"] is True
    assert ce.pool_verdict(9, **kw)["fewer_than_list_size"] is True
    assert "fewer than the list size of 10" in ce.pool_verdict(9, **kw)["message"]
    assert ce.pool_verdict(10, **kw)["fewer_than_list_size"] is False
    big = dict(list_size=10, pool_min_absolute=99, multiplier=3)
    assert ce.pool_verdict(98, **big)["sufficient"] is False
    assert ce.pool_verdict(99, **big)["sufficient"] is True


def _toy_prep():
    rows = pd.DataFrame(
        {
            "player_id": [1, 1, 1, 2, 3],
            "match_id": [10, 11, 12, 10, 13],
            "n": [10, 10, 10, 5, 30],
            "legal_balls": [10, 10, 10, 5, 30],
            "innings": [1, 1, 1, 1, 1],
            "runs_sum": [5.0, 5, 5, 2, 20],
            "runs_sum2": [9.0, 9, 9, 4, 50],
        }
    )
    return ce.Prepared(rows, "batter")


def test_eligibility_and_match_coverage_on_toy_set():
    prep = _toy_prep()
    table = ce.player_table(prep)
    assert list(table["balls"]) == [30, 5, 30]
    assert list(table["matches"]) == [3, 1, 1]
    rule = {"clauses": [{"measure": "balls", "min": 30}]}
    mask = ce.eligible_mask(table, rule)
    assert list(mask) == [True, False, True]
    cov = ce.match_coverage(prep, mask, total_matches=5)
    assert cov["matches_covered"] == 4  # matches 10, 11, 12, 13
    assert cov["coverage_pct"] == pytest.approx(80.0)
    conj = {"clauses": [{"measure": "balls", "min": 30}, {"measure": "matches", "min": 2}]}
    assert list(ce.eligible_mask(table, conj)) == [True, False, False]


# ------------------------------------------------------------------------------- shrinkage


def test_shrinkage_hand_example():
    out = eb_shrink([10, 30], [2, 18], [2, 18])
    assert out["mu0"] == pytest.approx(0.5)
    assert out["sigma2"] == pytest.approx(0.2315789, rel=1e-5)
    assert out["tau2"] == pytest.approx(0.0645614, rel=1e-4)
    assert out["k"] == pytest.approx(3.58696, rel=1e-4)
    k = out["k"]
    assert out["rate"][0] == pytest.approx((10 * 0.2 + k * 0.5) / (10 + k))
    assert out["n_eff"][0] == pytest.approx(100 / (10 + k))
    assert out["n_eff"][1] == pytest.approx(900 / (30 + k))


def test_shrinkage_limits_and_equal_n():
    zero_within = eb_shrink([10, 10, 10], [10, 20, 30], [10, 40, 90])
    assert zero_within["k"] == 0.0
    assert list(zero_within["rate"]) == pytest.approx([1.0, 2.0, 3.0])
    assert list(zero_within["n_eff"]) == pytest.approx([10, 10, 10])
    identical = eb_shrink([10, 10, 10], [5, 5, 5], [5, 5, 5])
    assert identical["k"] > 1e9
    assert list(identical["rate"]) == pytest.approx([0.5, 0.5, 0.5])
    assert max(identical["n_eff"]) < 1e-6
    equal = eb_shrink([20, 20, 20], [4, 10, 16], [4, 10, 16])
    assert len(set(np.round(equal["n_eff"], 9))) == 1  # equal n gives equal weights
    empty = eb_shrink([0, 0], [0, 0], [0, 0])
    assert np.isnan(empty["mu0"])


def test_n_eff_formulas():
    assert n_eff_kish([10, 10]) == pytest.approx(2.0)
    assert n_eff_kish([20, 0]) == pytest.approx(1.0)
    assert n_eff_kish([10, 30]) == pytest.approx(1.6)
    assert n_eff_kish([]) == 0.0
    assert n_eff_shrink([10], 0.0)[0] == pytest.approx(10.0)
    assert n_eff_shrink([0], 0.0)[0] == 0.0


# ------------------------------------------------------------------------------- bootstrap


def test_bootstrap_reproducible_and_seed_sensitive():
    prep = ce.Prepared(synthetic_samples().batter.query("format == 'IPL'"), "batter")
    a = ce.bootstrap_score_matrix(prep, np.random.default_rng(7), 15)
    b = ce.bootstrap_score_matrix(prep, np.random.default_rng(7), 15)
    c = ce.bootstrap_score_matrix(prep, np.random.default_rng(8), 15)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_bootstrap_resamples_matches_not_deliveries():
    prep = ce.Prepared(synthetic_samples().batter.query("format == 'IPL'"), "batter")
    M = len(prep.match_ids)
    mult = np.random.default_rng(3).multinomial(M, np.full(M, 1.0 / M), size=5)
    assert (mult.sum(axis=1) == M).all()  # whole matches drawn with replacement
    matrix = ce.bootstrap_score_matrix(prep, np.random.default_rng(3), 5)
    for b in range(5):
        agg = prep.aggregate(mult[b][prep.midx].astype(float))
        # each player's n is the sum over matches of n * match multiplicity
        manual = np.zeros(prep.n_players)
        for pi, mi, n in zip(prep.pidx, prep.midx, prep.n):
            manual[pi] += n * mult[b][mi]
        assert np.allclose(agg["n"], manual)
        assert np.allclose(matrix[b], ce.score_from_agg("batter", agg)["score"], equal_nan=True)


def test_bootstrap_rule_summary_shapes():
    rng = np.random.default_rng(0)
    orig = np.linspace(0, 1, 30)
    matrix = orig + rng.normal(0, 0.05, size=(40, 30))
    res = ce.bootstrap_rule(matrix, orig, np.ones(30, dtype=bool), 10)
    assert res["evaluated"] and res["top_k"] == 10
    assert 0 < res["top_k_mean_membership_freq"] <= 1
    assert 0 <= res["expected_top_k_overlap"] <= 10
    assert res["spearman_vs_original_mean"] > 0.9
    assert ce.bootstrap_rule(matrix, orig, np.zeros(30, dtype=bool))["evaluated"] is False


# --------------------------------------------------------------------------- experiment runs


def test_experiment_reproducible_and_independent(rules):
    cfg = small_rules(rules)
    s = synthetic_samples()
    d1, e1 = ce.run_experiment(s, cfg, 12)
    d2, e2 = ce.run_experiment(s, cfg, 12)
    assert json.dumps(round_floats(e1), sort_keys=True) == json.dumps(
        round_floats(e2), sort_keys=True
    )
    for doc in (d1, e1):
        assert doc["proxy_run"] is True and doc["pressure_status"] == "PENDING_PHASE3"
        assert doc["score_label"] == "PROXY_NOT_PRESSURE" and doc["not_for_publication"] is True
    # bootstrap seed sensitivity
    cfg2 = copy.deepcopy(cfg)
    cfg2["seed"] = cfg["seed"] + 1
    _, e3 = ce.run_experiment(s, cfg2, 12)
    b1 = [r["bootstrap"] for r in e1["formats"]["IPL"]["batter"]["rules"]]
    b3 = [r["bootstrap"] for r in e3["formats"]["IPL"]["batter"]["rules"]]
    assert b1 != b3
    # batter results do not depend on bowler data
    s_b = ProxySamples(s.batter, s.bowler.assign(econ_sum=s.bowler.econ_sum + 1.0),
                       s.window, s.names, [])  # fmt: skip
    _, e4 = ce.run_experiment(s_b, cfg, 12)
    assert e4["formats"]["IPL"]["batter"]["rules"] == e1["formats"]["IPL"]["batter"]["rules"]
    assert e4["formats"]["T20I"]["batter"]["rules"] == e1["formats"]["T20I"]["batter"]["rules"]
    # IPL results do not depend on T20I data
    t = s.batter.copy()
    t.loc[t.format == "T20I", "runs_sum"] += 3.0
    t.loc[t.format == "T20I", "runs_sum2"] += 20.0
    _, e5 = ce.run_experiment(ProxySamples(t, s.bowler, s.window, s.names, []), cfg, 12)
    assert e5["formats"]["IPL"]["batter"]["rules"] == e1["formats"]["IPL"]["batter"]["rules"]
    assert e5["formats"]["T20I"]["batter"]["rules"] != e1["formats"]["T20I"]["batter"]["rules"]


def test_combined_eligibility_requires_both_formats(rules):
    cfg = small_rules(rules)
    s = synthetic_samples(2)
    _, e = ce.run_experiment(s, cfg, 6)
    comb = e["combined"]["batter"]
    assert comb
    for rid, v in comb.items():
        sets = []
        for fmt in ("IPL", "T20I"):
            prep = ce.Prepared(s.batter[s.batter.format == fmt], "batter")
            table = ce.player_table(prep)
            rec = next(r for r in e["formats"][fmt]["batter"]["rules"] if r["rule_id"] == rid)
            mask = ce.eligible_mask(table, {"clauses": rec["clauses"]})
            sets.append(set(prep.player_ids[mask]))
        assert v["eligible_both_formats"] == len(sets[0] & sets[1])
        assert v["eligible_both_formats"] <= min(len(sets[0]), len(sets[1]))


def test_experiment_reports_fewer_than_ten_plainly(rules):
    cfg = small_rules(rules)
    cfg["list_size"] = 10
    rng = np.random.default_rng(5)
    bat = _rows(rng, "IPL", 1, 8, 1000, 6, "batter")
    bat = pd.concat([bat, bat.assign(format="T20I", match_id=bat.match_id + 1000)])
    bowl = _rows(rng, "IPL", 1, 8, 1000, 6, "bowler")
    bowl = pd.concat([bowl, bowl.assign(format="T20I", match_id=bowl.match_id + 1000)])
    window = {f: {"matches_with_deliveries": 6, "first_date": "a", "last_date": "b"}
              for f in ("IPL", "T20I")}  # fmt: skip
    _, e = ce.run_experiment(ProxySamples(bat, bowl, window, {}, []), cfg, 6)
    rules_ipl = e["formats"]["IPL"]["batter"]["rules"]
    assert all(r["eligible"] <= 8 for r in rules_ipl)
    assert all(r["pool"]["fewer_than_list_size"] for r in rules_ipl)
    assert all("fewer than the list size" in r["pool"]["message"] for r in rules_ipl)
    assert any("fewer than 10 eligible" in line for line in e["narrative"]["IPL"])


# ------------------------------------------------------------------ threshold sensitivity


def test_threshold_sensitivity_on_constructed_ranking_ladder():
    base = pd.DataFrame({"player_id": range(1, 21), "score": np.arange(20, 0, -1.0)})
    drop3 = base[base.player_id > 3]
    ids_a = list(rank_players(base)["player_id"])
    ids_b = list(rank_players(drop3)["player_id"])
    assert topk_overlap(ids_a, ids_b, 10) == 7
    assert spearman_common(base, drop3) == {"rho": pytest.approx(1.0), "n": 17}
    flipped = drop3.assign(score=-drop3.score)
    assert spearman_common(base, flipped)["rho"] == pytest.approx(-1.0)
    assert spearman_common(base.head(2), base.head(2))["rho"] is None  # n < 3
    ladder = [base.head(20), base.head(12), base.head(6), base.head(4)]
    overlaps = [
        topk_overlap(list(rank_players(ladder[0])["player_id"]), list(rank_players(x)["player_id"]))
        for x in ladder
    ]
    assert overlaps == [10, 10, 6, 4]  # stricter thresholds shrink the common Top 10
    mv = movement(base, drop3)
    assert mv["entering_top_k"] == [11, 12, 13] and mv["leaving_top_k"] == [1, 2, 3]
    assert mv["max_abs_change"] == 3


def test_rank_players_tie_break_by_player_id():
    df = pd.DataFrame({"player_id": [5, 2, 9], "score": [1.0, 1.0, 1.0]})
    assert list(rank_players(df)["player_id"]) == [2, 5, 9]


# ------------------------------------------------------------------------ proxy extraction


def _seed_db():
    db = connect(":memory:")
    db.apply_persistent_schema()
    db.create_replaceable()
    for cid, ctype in ((1, "IPL"), (2, "T20I"), (3, "OTHER_T20")):
        db.execute(
            "INSERT INTO competitions VALUES (?, ?, 'T20', '2024', ?, 'c.csv', 1, 1)",
            [cid, f"C{cid}", ctype],
        )
    for tid in (1, 2):
        db.execute("INSERT INTO teams VALUES (?, ?, 't.csv', 1, 1)", [tid, f"T{tid}"])
    for pid in (1, 2, 10):
        db.execute(
            "INSERT INTO players VALUES (?, ?, 'MAPPING', NULL, true, true, true, false, "
            "false, 'p.csv', 1)",
            [pid, f"Player {pid}"],
        )
    for mid, cid, ctype, has in ((1, 1, "IPL", True), (2, 2, "T20I", True),
                                 (3, 3, "OTHER_T20", True), (4, 1, "IPL", False)):  # fmt: skip
        db.execute(
            "INSERT INTO matches (match_id, comp_id, match_date, home_team_id, away_team_id, "
            "result_status, competition_type, has_deliveries, source_file, ingestion_run_id) "
            "VALUES (?, ?, DATE '2024-04-01', 1, 2, 'RESULT', ?, ?, 'm.csv', 1)",
            [mid, cid, ctype, has],
        )
    for mid, inn in ((1, 1), (1, 3), (2, 1), (3, 1)):
        db.execute(
            "INSERT INTO innings VALUES (?, ?, 1, 2, true, 1, 1, 0, 0, 0, 0, 0, 1, 'X', "
            "'i.csv', 1, 1, 1)",
            [mid, inn],
        )
    return db


def _ball(db, mid, inn, n, striker, bowler, runs, extras, prim, legal, wicket=False, dtype=None):
    db.execute(
        "INSERT INTO deliveries (match_id, innings_number, innings_ball_num, batting_team_id, "
        "bowling_team_id, striker_id, bowler_id, is_wicket, dismissal_type, batter_runs, "
        "extras_type, extras_primary_runs, is_legal_ball, legal_ball_status, "
        "extras_split_status, extras_label_unverified, source_file, source_row_no, "
        "ingestion_run_id) VALUES (?, ?, ?, 1, 2, ?, ?, ?, ?, ?, ?, ?, ?, 'X', 'NONE', false, "
        "'d.csv', ?, 1)",
        [mid, inn, n, striker, bowler, wicket, dtype, runs, extras, prim, legal, n],
    )


def test_proxy_extraction_rules_on_in_memory_duckdb():
    db = _seed_db()
    _ball(db, 1, 1, 1, 1, 10, 4, "None", 0, True)
    _ball(db, 1, 1, 2, 1, 10, 0, "wide", 1, False)
    _ball(db, 1, 1, 3, 1, 10, 2, "Overstep", 1, False)
    _ball(db, 1, 1, 4, 1, 10, 0, "Penalty", 5, False)
    _ball(db, 1, 1, 5, 1, 10, 0, "None", 0, True, True, "Caught")
    _ball(db, 1, 1, 6, 1, 10, 0, "None", 0, True, True, "RunOut")
    _ball(db, 1, 3, 1, 1, 10, 6, "None", 0, True)  # innings 3: excluded
    _ball(db, 2, 1, 1, 2, 10, 1, "None", 0, True)  # T20I
    _ball(db, 3, 1, 1, 1, 10, 6, "None", 0, True)  # OTHER_T20
    s = extract_samples(db)
    bat = s.batter
    ipl = bat[(bat.format == "IPL") & (bat.player_id == 1)].iloc[0]
    assert (ipl.n, ipl.legal_balls, ipl.runs_sum, ipl.runs_sum2, ipl.innings) == (4, 3, 6, 20, 1)
    assert set(bat.format) == {"IPL", "T20I", "OTHER_T20"}
    assert 3 in set(bat[bat.format == "OTHER_T20"].match_id)
    assert 3 not in set(bat[bat.format.isin(["IPL", "T20I"])].match_id)
    assert (bat.innings <= 1).all() and 4 not in set(bat.match_id)
    bw = s.bowler[(s.bowler.format == "IPL") & (s.bowler.player_id == 10)].iloc[0]
    assert (bw.n, bw.legal_balls, bw.econ_sum, bw.wkt_sum) == (5, 3, 8, 1)
    assert "Caught" in s.distinct_dismissal_types and "RunOut" in s.distinct_dismissal_types
    assert s.window["IPL"]["matches_with_deliveries"] == 1
    # the in-memory data model refuses writes through a read-only handle: see integrity test


# --------------------------------------------------------------------------------- integrity


def test_integrity_snapshot_detects_changes_and_readonly_blocks_writes(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    (root / "a.csv").write_text("x\n1\n", encoding="utf-8")
    crics = root / "ipl_male_json"
    crics.mkdir()
    (crics / "1.json").write_text("{}", encoding="utf-8")
    dbp = tmp_path / "x.duckdb"
    db = connect(dbp)
    db.apply_persistent_schema()
    db.create_replaceable()
    db.execute("INSERT INTO teams VALUES (1, 'A', 't.csv', 1, 1)")
    db.close()
    before = snapshot_official(dbp, root, ["ipl_male_json"])
    assert assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"])) == {}
    ro = open_official_readonly(dbp)
    with pytest.raises(Exception):
        ro.execute("INSERT INTO teams VALUES (2, 'B', 't.csv', 1, 1)")
    ro.close()
    assert assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"])) == {}
    (root / "a.csv").write_text("x\n2\n", encoding="utf-8")
    diff = assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"]))
    assert "/csv_sha256/a.csv" in diff
    with pytest.raises(IntegrityError):
        assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"]), True)
    (root / "a.csv").write_text("x\n1\n", encoding="utf-8")
    d = connect(dbp)
    d.execute("INSERT INTO teams VALUES (2, 'B', 't.csv', 1, 1)")
    d.close()
    diff = assert_unchanged(before, snapshot_official(dbp, root, ["ipl_male_json"]))
    assert "/tables/teams/rows" in diff
