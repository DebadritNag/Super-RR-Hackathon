"""Dynamic filter-driven ranking engine on synthetic stored context rows (Phase 5, Chunk 4)."""

from __future__ import annotations

import ast
import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase5 import context_eligibility as ce
from app.phase5 import context_stats as cs
from app.phase5 import coverage as cov
from app.phase5.cache import RankingCache, cache_key
from app.phase5.filters import FilterSpec, canonical_json, page_hash, spec_hash
from app.phase5.ranking_engine import ContextEngine, paginate_ranked
from tests.phase5_ctx_helpers import (
    LADDERS,
    SHRINK,
    build_all,
    make_cfg,
    make_engine,
    manifest,
    player_stats_frame,
    synth_stats,
)

APP = Path(__file__).resolve().parents[1] / "app"
STRICT_OFF = False


def S(**kw) -> FilterSpec:
    kw.setdefault("role", "batter")
    kw.setdefault("format", "IPL")
    return FilterSpec(**kw)


@pytest.fixture(scope="module")
def world():
    return make_engine()


def rank(world, **kw) -> dict:
    eng, cls, _, _ = world
    return eng.rank(S(**kw), cls, STRICT_OFF)


def ids_of(res: dict) -> list[int]:
    return [r["player_id"] for r in res["rows"]]


# ----------------------------------------------------------------------------- stored rows
def test_stored_rows_are_additive_over_phase_and_situation(world):
    _, _, art, stats = world
    for comp, role in itertools.product(("IPL", "T20I"), ("batter", "bowler")):
        total = cs.select(stats, comp, role, "ALL", "ALL").groupby("player_id")[["n", "s"]].sum()
        parts = pd.concat(
            [
                cs.select(stats, comp, role, ph, si).groupby("player_id")[["n", "s"]].sum()
                for ph in cs.PHASES
                for si in cs.SITUATIONS
            ]
        )
        summed = parts.groupby(level=0).sum()
        pd.testing.assert_frame_equal(total.sort_index(), summed.sort_index(), check_exact=False)
    sc = art["scores"]
    allr = sc[(sc["phase"] == "ALL") & (sc["situation"] == "ALL")]
    atoms = sc[(sc["phase"] != "ALL") & (sc["situation"] != "ALL")]
    a = allr.groupby(["comp", "role", "player_id"])["n"].sum()
    b = atoms.groupby(["comp", "role", "player_id"])["n"].sum()
    assert (a.reindex(b.index) == b).all() and len(a) == len(b)


def test_context_rows_refuse_test_period_and_unknown_labels():
    stats = synth_stats(n_train=3, n_val=1)
    bad = stats.copy()
    bad.loc[bad.index[0], "period"] = "TEST"
    with pytest.raises(cs.ContextStatsError):
        cs.check_stats(bad)
    with pytest.raises(cs.ContextStatsError):
        ce.build_artifacts(bad, make_cfg(), LADDERS, SHRINK)
    bad2 = stats.copy()
    bad2.loc[bad2.index[0], "phase"] = "super_over"
    with pytest.raises(cs.ContextStatsError):
        cs.check_stats(bad2)
    with pytest.raises(cs.ContextStatsError):
        cs.situation_labels(np.array([1, 3]))


def test_all_48_atomic_contexts_are_built(world):
    _, _, art, _ = world
    assert len(art["rules"]) == 48
    assert set(art["rules"]["context_status"]) <= {
        ce.CONTEXT_ELIGIBLE,
        ce.NO_THRESHOLD,
        ce.NOT_ESTIMABLE,
    }


# ----------------------------------------------------------------------------- AND semantics
def test_filters_are_anded_and_each_filter_only_shrinks_the_pool(world):
    eng, cls, art, _ = world
    sc = art["scores"]
    base = sc[
        (sc.comp == "IPL") & (sc.role == "batter") & (sc.phase == "ALL") & (sc.situation == "ALL")
    ]
    elig = set(base.loc[base.eligible, "player_id"])
    c = cls.set_index("player_id")
    indian = {p for p in elig if c.loc[p, "nationality"] == "Indian"}
    derived = {p for p in elig if c.loc[p, "international_status"] == "DERIVED_CAPPED"}
    r_nat = rank(world, nationality="Indian", include_unknown_nationality=False)
    r_both = rank(world, nationality="Indian", status="DERIVED_CAPPED")
    pool_nat = eng.resolve_pool(S(nationality="Indian"), cls, False)
    pool_both = eng.resolve_pool(S(nationality="Indian", status="DERIVED_CAPPED"), cls, False)
    assert set(pool_nat.ids.tolist()) == indian
    assert set(pool_both.ids.tolist()) == indian & derived
    assert set(ids_of(r_both)) <= set(ids_of(r_nat)) or r_nat["rows"] == []
    pool_exp = eng.resolve_pool(
        S(nationality="Indian", status="DERIVED_CAPPED", min_matches=12), cls, False
    )
    career = player_stats_frame().groupby("player_id")["matches_played"].first()
    assert set(pool_exp.ids.tolist()) == {p for p in indian & derived if career[p] >= 12}
    assert pool_exp.size <= pool_both.size <= pool_nat.size


def test_overseas_capped_and_indian_batter_example_sets(world):
    eng, cls, _, _ = world
    c = cls.set_index("player_id")
    for spec in (
        S(nationality="Overseas", status="CAPPED_ANY"),
        S(nationality="Indian", role="batter"),
        S(nationality="Overseas", status="DERIVED_CAPPED", phase="death"),
    ):
        pool = eng.resolve_pool(spec, cls, False)
        for p in pool.ids:
            assert c.loc[p, "nationality"] == spec.nationality
            if spec.status:
                assert c.loc[p, "international_status"] in ("DERIVED_CAPPED", "VERIFIED_CAPPED")


def test_batter_and_bowler_rankings_are_separate(world):
    bat = rank(world, role="batter")
    bowl = rank(world, role="bowler")
    assert set(ids_of(bowl)) <= set(range(7, 25))
    assert set(ids_of(bat)) != set(ids_of(bowl))
    assert bat["spec_hash"] != bowl["spec_hash"]
    for r in bowl["rows"]:
        assert r["shrunk"] == pytest.approx(-r["score"])
    for r in bat["rows"]:
        assert r["shrunk"] == pytest.approx(r["score"])


# ----------------------------------------------------------------------------- exclusion counts
def test_unknown_classification_is_excluded_by_default_and_counted(world):
    eng, cls, art, _ = world
    sc = art["scores"]
    base = sc[
        (sc.comp == "IPL") & (sc.role == "batter") & (sc.phase == "ALL") & (sc.situation == "ALL")
    ]
    elig = set(base.loc[base.eligible, "player_id"])
    c = cls.set_index("player_id")
    unk = {p for p in elig if c.loc[p, "nationality"] == "Unknown"}
    res = rank(world, nationality="Indian")
    assert res["excluded_counts"]["unknown_nationality_excluded"] == len(unk) > 0
    reason = next(r for r in res["reasons"] if r["code"] == "CLASSIFICATION_UNKNOWN_EXCLUDED")
    assert reason["count"] == len(unk)
    assert all(r["classification_match"] == "EXACT" for r in res["rows"])
    inc = rank(world, nationality="Indian", include_unknown_nationality=True)
    assert inc["excluded_counts"]["unknown_nationality_excluded"] == 0
    assert inc["pool_size"] == res["pool_size"] + len(unk)
    flagged = [
        r["player_id"] for r in inc["rows"] if r["classification_match"] == "UNKNOWN_INCLUDED"
    ]
    assert set(flagged) == unk
    # unknown values on an axis with no filter never exclude anyone
    free = rank(world)
    assert free["excluded_counts"]["unknown_nationality_excluded"] == 0
    assert free["pool_size"] == len(elig)


def test_status_toggle_and_class_empty_reason(world):
    res = rank(world, status="VERIFIED_CAPPED")
    codes = {r["code"] for r in res["reasons"]}
    assert "CLASS_EMPTY" in codes and "CLASSIFICATION_UNKNOWN_EXCLUDED" in codes
    assert res["rows"] == [] and res["pool_size"] == 0 and "POOL_TOO_SMALL" in codes
    unk = rank(world, status="UNKNOWN_STATUS")
    assert all(r["international_status"] == "UNKNOWN" for r in unk["rows"])
    assert unk["excluded_counts"]["unknown_status_excluded"] == 0
    capped = rank(world, status="CAPPED_ANY", include_unknown_status=True)
    kinds = {r["international_status"] for r in capped["rows"]}
    assert kinds == {"DERIVED_CAPPED", "UNKNOWN"}
    assert all(
        (r["classification_match"] == "UNKNOWN_INCLUDED")
        == (r["international_status"] == "UNKNOWN")
        for r in capped["rows"]
    )


# ----------------------------------------------------------------------------- context recompute
def _hand_context(stats, comp, role, phase, sit) -> pd.DataFrame:
    sub = cs.select(stats, comp, role, phase, sit)
    pm = sub.groupby(["player_id", "match_id"], as_index=False).agg(n=("n", "sum"), s=("s", "sum"))
    g = pm.groupby("player_id")
    out = pd.DataFrame(
        {
            "n": g["n"].sum(),
            "matches": g["match_id"].nunique(),
            "n_eff": g["n"].sum() ** 2 / g["n"].apply(lambda x: float((x**2).sum())),
            "mean": g["s"].sum() / g["n"].sum(),
        }
    )
    train = pm[pm.match_id.isin(sub.loc[sub.period == "TRAIN", "match_id"])]
    out["train_n"] = train.groupby("player_id")["n"].sum().reindex(out.index).fillna(0)
    return out


def test_context_values_are_recomputed_from_the_stored_rows(world):
    _, _, art, stats = world
    comp, role, phase, sit = "IPL", "batter", "death", "chase"
    hand = _hand_context(stats, comp, role, phase, sit)
    sc = art["scores"]
    got = sc[(sc.comp == comp) & (sc.role == role) & (sc.phase == phase) & (sc.situation == sit)]
    got = got.set_index("player_id").sort_index()
    assert list(got.index) == list(hand.index)
    np.testing.assert_allclose(got["n"], hand["n"])
    np.testing.assert_array_equal(got["matches"], hand["matches"])
    np.testing.assert_allclose(got["n_eff"], hand["n_eff"])
    np.testing.assert_allclose(got["mean_residual"], hand["mean"])
    # threshold: one of the context's own candidates; eligibility = n >= threshold * window ratio
    train_n = hand["train_n"][hand["train_n"] > 0].to_numpy()
    cands = {c["threshold"] for c in el.candidate_thresholds(train_n, LADDERS[role]["balls"])}
    thr = int(got["threshold_balls"].iloc[0])
    assert thr in cands
    wr = hand["n"].sum() / hand["train_n"].sum()
    np.testing.assert_array_equal(got["eligible"].to_numpy(), (hand["n"] >= thr * wr).to_numpy())
    # a different context has its own threshold derivation (not copied from the overall cell)
    rules = art["rules"].set_index(["comp", "role", "phase", "situation"])
    thr_all = rules.loc[(comp, role, "ALL", "ALL"), "threshold_balls"]
    assert rules.loc[(comp, role, phase, sit), "threshold_balls"] != thr_all


def test_context_uncertainty_matches_an_independent_bootstrap(world):
    eng, cls, art, stats = world
    comp, role, phase, sit = "T20I", "batter", "ALL", "chase"
    res = rank(world, format=comp, role=role, phase=phase, situation=sit)
    assert res["rows"], "pool expected"
    row = res["rows"][0]
    pid = row["player_id"]
    sub = cs.select(stats, comp, role, phase, sit)
    gm, W = en.global_weights(stats["match_id"].to_numpy(), int(eng.cfg["n_boot"]), eng.cfg["seed"])
    pm = sub[sub.player_id == pid].groupby("match_id").agg(n=("n", "sum"), s=("s", "sum"))
    sc = (
        art["scores"]
        .set_index(["comp", "role", "phase", "situation", "player_id"])
        .loc[(comp, role, phase, sit, pid)]
    )
    draws = []
    for b in range(W.shape[0]):
        nb = sum(W[b, gm.get_loc(m)] * r.n for m, r in pm.iterrows())
        sb = sum(W[b, gm.get_loc(m)] * r.s for m, r in pm.iterrows())
        if nb <= 0:
            continue
        ne = sc["n_eff"] * nb / pm["n"].sum()
        B = ne / (ne + sc["k"])
        draws.append(sc["target"] + B * (sb / nb - sc["target"]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    assert row["interval_low"] == pytest.approx(lo, abs=1e-9)
    assert row["interval_high"] == pytest.approx(hi, abs=1e-9)
    assert 0.0 <= row["top10_inclusion_prob"] <= 1.0
    assert row["rank_lo"] <= row["rank_median"] <= row["rank_hi"]
    assert rank(world, format=comp, role=role, phase=phase, situation=sit) == res


def test_overall_context_matches_independent_shrinkage(world):
    """(ALL, ALL) shrunk values from plain pandas: leave-one-player-out target, k from the fit."""
    _, _, art, stats = world
    comp, role = "IPL", "batter"
    sub = cs.select(stats, comp, role, "ALL", "ALL")
    hand = _hand_context(stats, comp, role, "ALL", "ALL")
    tr = sub[sub.period == "TRAIN"].groupby("player_id")[["n", "s"]].sum()
    tot_n, tot_s = tr["n"].sum(), tr["s"].sum()
    own_n = tr["n"].reindex(hand.index).fillna(0)
    own_s = tr["s"].reindex(hand.index).fillna(0)
    target = (tot_s - own_s) / (tot_n - own_n)
    fit = (
        art["fit"].set_index(["comp", "role", "phase", "situation"]).loc[(comp, role, "ALL", "ALL")]
    )
    k = fit["k"]
    shrunk = target + hand["n_eff"] / (hand["n_eff"] + k) * (hand["mean"] - target)
    sc = art["scores"]
    got = sc[(sc.comp == comp) & (sc.role == role) & (sc.phase == "ALL") & (sc.situation == "ALL")]
    np.testing.assert_allclose(
        got.set_index("player_id")["shrunk"].sort_index(), shrunk.sort_index()
    )


# ----------------------------------------------------------------------------- no padding, reasons
def test_short_pools_are_never_padded(world):
    eng, cls, _, _ = world
    found = 0
    for ph, si, nat in itertools.product(cs.PHASES, cs.SITUATIONS, ("Indian", "Overseas")):
        for fmt, role in itertools.product(("IPL", "T20I"), ("batter", "bowler")):
            spec = S(format=fmt, role=role, phase=ph, situation=si, nationality=nat)
            res = eng.rank(spec, cls, False)
            pool = eng.resolve_pool(spec, cls, False)
            assert len(res["rows"]) == (
                pool.size if pool.size >= eng.cfg["min_internal_pool"] else 0
            )
            assert len(res["rows"]) <= pool.size
            if 5 <= pool.size < 10:
                found += 1
                assert res["result_status"] == "FEWER_THAN_LIST_SIZE"
                assert any(r["code"] == "FEWER_THAN_LIST_SIZE" for r in res["reasons"])
                assert len(res["rows"]) < 10
            if pool.size < 5:
                assert res["result_status"] == "EMPTY"
                assert any(r["code"] == "POOL_TOO_SMALL" for r in res["reasons"])
    assert found > 0, "the synthetic pools must include a 5-9 player case"


def test_not_estimable_contexts_return_empty_with_reason():
    stats = synth_stats(n_train=6, n_val=2)
    cfg = make_cfg()
    cfg["min_train_players_for_fit"] = 10_000
    art = build_all(stats, cfg)
    assert set(art["rules"]["context_status"]) == {ce.NOT_ESTIMABLE}
    assert art["scores"].empty
    eng = ContextEngine(stats, art["rules"], art["scores"], cfg, {}, player_stats_frame(), "v")
    from tests.phase4_api_helpers import base_classification_v2

    res = eng.rank(S(), base_classification_v2(), False)
    assert res["rows"] == []
    assert {r["code"] for r in res["reasons"]} >= {"CONTEXT_NOT_ESTIMABLE"}
    comb = eng.rank(S(format="COMBINED_w70_30"), base_classification_v2(), False)
    assert "FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS" in {r["code"] for r in comb["reasons"]}


def test_strict_uncapped_is_disabled_and_returns_no_rows(world):
    eng, cls, _, _ = world
    res = eng.rank(S(status="VERIFIED_UNCAPPED"), cls, False)
    assert res["result_status"] == "STRICT_UNCAPPED_DISABLED" and res["rows"] == []
    assert res["reasons"][0]["code"] == "STRICT_UNCAPPED_DISABLED"
    for kw in (dict(nationality="Indian"), dict(nationality="Overseas", role="bowler")):
        res = eng.rank(S(status="VERIFIED_UNCAPPED", **kw), cls, False)
        assert res["result_status"] == "STRICT_UNCAPPED_DISABLED" and res["rows"] == []
    # an enabled capability on a synthetic verified source is the only way to see such a class
    cls2 = cls.copy()
    cls2.loc[cls2.player_id.isin([7, 8, 9, 10, 11, 12]), "international_status"] = (
        "VERIFIED_UNCAPPED"
    )
    ok = eng.rank(S(status="VERIFIED_UNCAPPED"), cls2, True)
    assert (
        set(ids_of(ok)) <= {7, 8, 9, 10, 11, 12}
        and ok["result_status"] != "STRICT_UNCAPPED_DISABLED"
    )


# ----------------------------------------------------------------------------- order
def test_ties_are_broken_by_player_id(world):
    eng, cls, art, stats = world
    sc = art["scores"].copy()
    key = (sc.comp == "IPL") & (sc.role == "batter") & (sc.phase == "ALL") & (sc.situation == "ALL")
    elig = sc[key & sc.eligible]
    top = float(elig["score"].max()) + 1.0
    a, b = sorted(elig["player_id"].iloc[[3, 0]].tolist())
    for p in (a, b):
        sc.loc[key & (sc.player_id == p), ["score", "shrunk"]] = top
    eng2 = ContextEngine(
        stats, art["rules"], sc, eng.cfg, eng.manifest, player_stats_frame(), "tie"
    )
    res = eng2.rank(S(), cls, False)
    assert ids_of(res)[:2] == [a, b]
    assert [r["rank"] for r in res["rows"]][:2] == [1, 2]
    rows = res["rows"]
    keyed = [(-r["score"], r["player_id"]) for r in rows]
    assert keyed == sorted(keyed)


def test_pagination_and_display_sort_do_not_change_ranks(world):
    eng, cls, _, _ = world
    full = eng.rank(S(), cls, False)
    assert full["pool_size"] >= 12
    by_rank = {r["player_id"]: r["rank"] for r in full["rows"]}
    p1 = paginate_ranked(full, S(limit=5, offset=0))
    p2 = paginate_ranked(full, S(limit=5, offset=5))
    assert [r["rank"] for r in p1["rows"]] == [1, 2, 3, 4, 5]
    assert [r["rank"] for r in p2["rows"]] == [6, 7, 8, 9, 10]
    assert p1["total"] == full["pool_size"]
    by_name = paginate_ranked(full, S(limit=50, sort="name"))["rows"]
    assert [r["name"] for r in by_name] == sorted(r["name"] for r in by_name)
    assert {r["player_id"]: r["rank"] for r in by_name} == by_rank
    by_n = paginate_ranked(full, S(limit=50, sort="n"))["rows"]
    assert [r["n"] for r in by_n] == sorted((r["n"] for r in by_n), reverse=True)


# ----------------------------------------------------------------------------- cache
def test_cache_key_is_stable_and_changes_with_every_ranking_field():
    a = FilterSpec.model_validate({"role": "bowler", "format": "IPL", "phase": "death"})
    b = FilterSpec.model_validate({"phase": "death", "format": "IPL", "role": "bowler"})
    c = FilterSpec(role="bowler", format="IPL", phase="death", situation="ALL", limit=10)
    assert canonical_json(a) == canonical_json(b) == canonical_json(c)
    assert spec_hash(a) == spec_hash(b) == spec_hash(c)
    base = spec_hash(a)
    for kw in (
        {"role": "batter"},
        {"format": "T20I"},
        {"phase": "middle"},
        {"situation": "chase"},
        {"nationality": "Indian"},
        {"status": "CAPPED_ANY"},
        {"min_matches": 3},
        {"min_context_matches": 2},
        {"include_unknown_nationality": True},
        {"include_unknown_status": True},
    ):
        assert spec_hash(a.model_copy(update=kw)) != base, kw
    for kw in ({"limit": 5}, {"offset": 3}, {"sort": "name"}, {"order": "desc"}):
        paged = a.model_copy(update=kw)
        assert spec_hash(paged) == base
        assert page_hash(paged) != page_hash(a)
    k = cache_key(base, "d1", "m1", "g1", "internal", "l1", "s1")
    assert k == cache_key(base, "d1", "m1", "g1", "internal", "l1", "s1")
    assert len({k, cache_key(base, "d2", "m1", "g1", "internal", "l1", "s1"),
                cache_key(base, "d1", "m2", "g1", "internal", "l1", "s1"),
                cache_key(base, "d1", "m1", "g2", "internal", "l1", "s1"),
                cache_key("x", "d1", "m1", "g1", "internal", "l1", "s1")}) == 5  # fmt: skip


def test_cache_hits_invalidates_on_version_change_and_equals_recomputed(world):
    eng, cls, _, _ = world
    cache = RankingCache(max_entries=2)
    spec = S(phase="death")
    calls = []

    def compute():
        calls.append(1)
        return eng.rank(spec, cls, False)

    kw = {"scope": "internal", "lock_version": "l1", "gate_state": "s1"}
    v1, hit1 = cache.get_or_compute(spec_hash(spec), "d1", "m1", compute, **kw)
    v2, hit2 = cache.get_or_compute(spec_hash(spec), "d1", "m1", compute, **kw)
    assert (hit1, hit2) == (False, True) and len(calls) == 1
    assert v1 is not v2 and v1 == v2 == eng.rank(spec, cls, False)  # cached equals recomputed
    _, hit3 = cache.get_or_compute(spec_hash(spec), "d2", "m1", compute, **kw)  # data version bump
    assert hit3 is False and len(calls) == 2 and cache.invalidations == 1
    _, hit4 = cache.get_or_compute(spec_hash(spec), "d2", "m2", compute, **kw)  # model version bump
    assert hit4 is False and cache.invalidations == 2
    assert cache.stats()["entries"] == 1
    for ph in ("powerplay", "middle", "death"):  # LRU bound
        cache.get_or_compute(spec_hash(S(phase=ph)), "d2", "m2", lambda: {}, **kw)
    assert cache.stats()["entries"] <= 2 and cache.evictions >= 1


# ----------------------------------------------------------------------------- no separate model
def test_no_estimator_is_fitted_per_filter_combination(world, monkeypatch):
    eng, cls, _, stats = world
    calls = []
    real = sh.fit_cell
    monkeypatch.setattr(sh, "fit_cell", lambda *a, **k: calls.append(1) or real(*a, **k))
    for spec in (S(), S(phase="death"), S(situation="chase", nationality="Indian"),
                 S(format="COMBINED_w70_30", role="bowler", phase="middle")):  # fmt: skip
        eng.rank(spec, cls, False)
    assert calls == [], "the request path must not fit anything"
    art = ce.build_artifacts(stats, make_cfg(), LADDERS, SHRINK)
    assert len(calls) == 48 == len(art["rules"]), "one fit per atomic context at build time"
    src = (APP / "phase5" / "ranking_engine.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "fit_cell" not in names | attrs and "fit" not in attrs
    mods = {
        (n.module or "") + "." + a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
        for a in n.names
    }
    assert not any("shrink" in m for m in mods)


def test_a_filter_cannot_create_reliability(world):
    """Players eligible overall but below the context's own threshold never reach a context list."""
    eng, cls, art, _ = world
    sc = art["scores"].sort_values(["comp", "role", "phase", "situation", "player_id"])
    sc = sc.set_index(["comp", "role", "phase", "situation", "player_id"]).sort_index()
    overall = sc.loc[("IPL", "batter", "ALL", "ALL")]
    elig_overall = set(overall.index[overall["eligible"].to_numpy()])
    checked = 0
    for ph, si in itertools.product(("powerplay", "middle", "death"), ("chase", "first_innings")):
        ctx = sc.loc[("IPL", "batter", ph, si)]
        weak = [p for p in ctx.index[~ctx["eligible"].to_numpy()] if p in elig_overall]
        if not weak:
            continue
        checked += 1
        res = rank(world, phase=ph, situation=si)
        assert not set(weak) & set(ids_of(res))
        low = next(r for r in res["reasons"] if r["code"] == "INSUFFICIENT_SAMPLE_FOR_CONTEXT")
        assert low["count"] >= len(weak)
        for r in res["rows"]:
            comp = r["components"]["IPL"]
            assert comp["n"] >= ctx.loc[r["player_id"], "scaled_threshold"]
            assert comp["k"] == ctx["k"].iloc[0]  # the context's own fitted strength, held fixed
    assert checked >= 1, (
        "synthetic data must contain overall-eligible but context-ineligible players"
    )
    for r in rank(world)["rows"]:
        assert r["components"]["IPL"]["k"] == overall["k"].iloc[0]


def test_context_variance_is_fitted_on_train_rows_only(world):
    _, _, art, stats = world
    key = ["comp", "role", "phase", "situation"]
    s2 = stats.copy()
    s2.loc[s2.period == "VALIDATION", "s"] += 7.0
    art2 = build_all(s2)
    pd.testing.assert_frame_equal(art["fit"], art2["fit"])
    assert not np.allclose(art["scores"]["shrunk"], art2["scores"]["shrunk"])
    s3 = stats.copy()
    s3.loc[(s3.period == "TRAIN") & (s3.comp == "IPL"), "s"] += 3.0
    art3 = build_all(s3)
    f1, f3 = art["fit"].set_index(key), art3["fit"].set_index(key)
    changed = (f1["between"] != f3["between"]).loc[("IPL", "batter", "ALL", "ALL")]
    assert changed or not np.isclose(f1["train_sum_residual"].sum(), f3["train_sum_residual"].sum())
    assert not f1["train_sum_residual"].equals(f3["train_sum_residual"])
    unchanged = f1.loc["T20I"]["train_sum_residual"].equals(f3.loc["T20I"]["train_sum_residual"])
    assert unchanged  # perturbing IPL TRAIN rows leaves the T20I contexts alone


# ----------------------------------------------------------------------------- combined format
def test_combined_format_needs_both_formats_and_weights_70_30(world):
    eng, cls, art, _ = world
    comb = rank(world, format="COMBINED_w70_30")
    sc = art["scores"].set_index(["comp", "role", "phase", "situation", "player_id"]).sort_index()
    ipl, t20 = sc.loc[("IPL", "batter", "ALL", "ALL")], sc.loc[("T20I", "batter", "ALL", "ALL")]
    both = {
        p for p in ipl.index if p in t20.index and ipl.loc[p, "eligible"] and t20.loc[p, "eligible"]
    }
    assert set(ids_of(comb)) == both
    one = {p for p in set(ipl.index) | set(t20.index)
           if bool(ipl["eligible"].get(p, False)) != bool(t20["eligible"].get(p, False))}  # fmt: skip
    codes = [r for r in comb["reasons"] if r["code"] == "FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS"]
    assert sum(r["count"] for r in codes) == len(one)
    # force an asymmetry: a player stops being eligible in T20I only
    victim = sorted(both)[0]
    sc2 = art["scores"].copy()
    hit = (sc2.comp == "T20I") & (sc2.role == "batter") & (sc2.phase == "ALL")
    hit &= (sc2.situation == "ALL") & (sc2.player_id == victim)
    sc2.loc[hit, "eligible"] = False
    eng2 = ContextEngine(
        world[3], art["rules"], sc2, eng.cfg, eng.manifest, player_stats_frame(), "x"
    )
    res2 = eng2.rank(S(format="COMBINED_w70_30"), cls, False)
    assert victim not in ids_of(res2) and set(ids_of(res2)) == both - {victim}
    asym = next(
        r for r in res2["reasons"] if r["code"] == "FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS"
    )
    assert asym["count"] == len(one) + 1
    for r in comb["rows"]:
        p = r["player_id"]
        assert r["score"] == pytest.approx(0.7 * ipl.loc[p, "score"] + 0.3 * t20.loc[p, "score"])
        assert r["n"] == ipl.loc[p, "n"] + t20.loc[p, "n"]
        ne = 1.0 / (0.49 / ipl.loc[p, "n_eff"] + 0.09 / t20.loc[p, "n_eff"])
        assert r["n_eff"] == pytest.approx(ne)
        assert set(r["components"]) == {"IPL", "T20I"}
        assert r["residual"] == pytest.approx(r["raw"] - r["expected"])
    assert not (set(ids_of(comb)) & one)


# ----------------------------------------------------------------------------- explanation
def test_every_row_carries_the_full_explanation(world):
    res = rank(world, nationality="Indian", status="DERIVED_CAPPED")
    assert res["rows"]
    need = {"raw", "expected", "residual", "shrunk", "interval_low", "interval_high", "rank_lo",
            "rank_hi", "top10_inclusion_prob", "n", "matches", "n_eff", "eligibility_status",
            "eligibility_thresholds", "restrictions_applied", "nationality",
            "nationality_verification", "international_status",
            "international_status_verification", "classification_match"}  # fmt: skip
    for r in res["rows"]:
        assert need <= set(r)
        assert r["raw"] - r["expected"] == pytest.approx(r["residual"])
        assert math.isfinite(r["interval_low"]) and math.isfinite(r["interval_high"])
        assert r["interval_low"] <= r["interval_high"]
    v = res["versions"]
    assert v["definition_label"] == "PROVISIONAL" and v["model_version"] == "p5_context_v1_train"
    assert set(res["context_data_weight"]) == {"IPL"}


# ----------------------------------------------------------------------------- coverage
def test_coverage_counts_equal_the_rankings_pool(world):
    eng, cls, _, _ = world
    table = cov.build_coverage(eng, cls, False)
    specs = list(cov.enumerate_specs(eng.cfg))
    assert len(table) == len(specs) == len(set(table["spec_hash"]))
    dis = table[table["status"] == "VERIFIED_UNCAPPED"]
    assert len(dis) and not dis["enabled"].any() and (dis["final_pool"] == 0).all()
    assert (dis["result_status"] == "STRICT_UNCAPPED_DISABLED").all()
    rng = np.random.default_rng(3)
    for i in rng.choice(len(specs), 40, replace=False):
        spec = specs[int(i)]
        res = eng.rank(spec, cls, False)
        row = table.iloc[int(i)]
        assert row["spec_hash"] == spec_hash(spec)
        if not row["enabled"]:
            continue
        assert row["final_pool"] == res["pool_size"]
        assert (len(res["rows"]) == row["final_pool"]) or row["final_pool"] < 5
        assert bool(row["meets_internal_min"]) == (row["final_pool"] >= 5)
        assert bool(row["meets_public_min"]) == (row["final_pool"] >= 10)
    # every toggle combination is listed only where it can change the result
    nat_unknown = table[(table["nationality"] == "Unknown")]
    assert not nat_unknown["include_unknown_nationality"].any()


def test_engine_rejects_test_rows_and_is_deterministic(world):
    eng, cls, art, stats = world
    bad = stats.copy()
    bad.loc[bad.index[0], "period"] = "TEST"
    with pytest.raises(cs.ContextStatsError):
        ContextEngine(bad, art["rules"], art["scores"], eng.cfg, {}, player_stats_frame(), "v")
    again = ContextEngine(stats, art["rules"], art["scores"], eng.cfg, eng.manifest,
                          player_stats_frame(), "v1")  # fmt: skip
    spec = S(phase="middle", situation="first_innings", nationality="Overseas")
    assert again.rank(spec, cls, False) == eng.rank(spec, cls, False)
    assert manifest(stats, cls)["stats_hash"] == manifest(stats, cls)["stats_hash"]
    assert not math.isnan(eng.w_ipl)


def test_dynamic_modules_never_import_cricsheet_or_open_the_test_lock():
    mods = (
        "phase5/context_stats.py",
        "phase5/context_eligibility.py",
        "phase5/filters.py",
        "phase5/ranking_engine.py",
        "phase5/cache.py",
        "phase5/coverage.py",
        "repositories/phase5_repo.py",
        "services/phase5_service.py",
        "api/v1/routes_phase5.py",
    )
    for rel in mods:
        src = (APP / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = {
            (n.module or "") + "." + a.name
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
            for a in n.names
        } | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not any("cricsheet" in m.lower() for m in imported), rel
        assert not any("evaluate_on_test" in m or "TestLock" in m for m in imported), rel
