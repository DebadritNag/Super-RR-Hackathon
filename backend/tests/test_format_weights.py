"""Format-weight configuration, combination engine and sensitivity metrics."""

from __future__ import annotations

import copy
import json
import shutil

import numpy as np
import pandas as pd
import pytest

from app.analytics import normalization_engine as ne
from app.analytics.format_config import (
    FormatConfigError,
    config_hash,
    load_config,
    register_config_in_model_versions,
    settings_consistency,
    validate_config,
)
from app.analytics.integrity import snapshot_official
from app.analytics.proxy_samples import ProxySamples
from app.analytics.ranking import movement, rank_players, spearman_common, topk_overlap
from app.analytics.reporting import write_json_deterministic
from app.core.config import BACKEND_ROOT, Settings
from app.core.database import connect

CFG_PATH = BACKEND_ROOT / "config" / "format_weights_v1.json"


@pytest.fixture()
def cfg() -> dict:
    return load_config(CFG_PATH)


# ------------------------------------------------------------------------------------ config
def test_eight_configs_load_and_default_is_provisional(cfg):
    assert len(cfg["configurations"]) == 8
    pairs = [(c["ipl_weight"], c["t20i_weight"]) for c in cfg["configurations"]]
    assert (1.0, 0.0) in pairs and (0.0, 1.0) in pairs and (0.7, 0.3) in pairs
    assert cfg["default_config_id"] == "w70_30"
    assert cfg["default_flag"] == "PROVISIONAL_NOT_VALIDATED"
    assert cfg["status"] == "PROVISIONAL"


def test_weight_normalization(cfg):
    for c in cfg["configurations"]:
        assert abs(c["ipl_weight"] + c["t20i_weight"] - 1.0) < 1e-9


def _mutate(cfg, fn):
    c = copy.deepcopy(cfg)
    fn(c)
    return c


@pytest.mark.parametrize(
    "fn",
    [
        lambda c: c["configurations"][3].update(ipl_weight=0.6),  # sums to 0.9
        lambda c: c["configurations"][1].update(ipl_weight=1.2, t20i_weight=-0.2),
        lambda c: c["configurations"][1].update(id="w100_0"),  # duplicate id
        lambda c: c.update(default_config_id="w99_1"),
        lambda c: c["configurations"].pop(),
        lambda c: c.update(default_flag="VALIDATED"),
        lambda c: c.pop("version"),
    ],
)
def test_invalid_configs_rejected(cfg, fn):
    with pytest.raises(FormatConfigError):
        validate_config(_mutate(cfg, fn))


def test_hash_stable_under_key_reorder(cfg):
    reordered = {k: cfg[k] for k in reversed(list(cfg))}
    reordered["configurations"] = [
        {k: c[k] for k in reversed(list(c))} for c in cfg["configurations"]
    ]
    assert config_hash(reordered) == config_hash(cfg)
    changed = _mutate(cfg, lambda c: c.update(rationale="different"))
    assert config_hash(changed) != config_hash(cfg)


def test_settings_consistency_warning(cfg):
    assert settings_consistency(cfg, Settings()) == []
    w = settings_consistency(cfg, Settings(ipl_weight=0.6, t20i_weight=0.4))
    assert w and w[0]["code"] == "SETTINGS_WEIGHT_MISMATCH"


# --------------------------------------------------------------------- combination engine
def _frame(rows):
    cols = ["player_id", "ipl_status", "t20i_status", "ipl_z", "t20i_z"]
    df = pd.DataFrame(rows, columns=cols)
    ie, te = df["ipl_status"] == ne.ELIGIBLE, df["t20i_status"] == ne.ELIGIBLE
    df["combined_status"] = np.select(
        [ie & te, ie & ~te, ~ie & te], [ne.BOTH, ne.IPL_ONLY, ne.T20I_ONLY], default=ne.NONE_VALID
    )
    return df


E, NE, N = ne.ELIGIBLE, ne.OBSERVED_NOT_ELIGIBLE, ne.NOT_OBSERVED
ROWS = [
    (1, E, E, 1.0, -1.0),
    (2, E, E, 0.5, 2.0),
    (3, E, N, 3.0, np.nan),
    (4, N, E, np.nan, 4.0),
    (5, NE, N, np.nan, np.nan),
]


def test_missing_format_gives_null_and_status_never_zero():
    df = _frame(ROWS)
    sc = ne.combined_scores(df, 0.7, 0.3)
    assert sc[0] == pytest.approx(0.7 * 1.0 + 0.3 * -1.0)
    assert sc[1] == pytest.approx(0.7 * 0.5 + 0.3 * 2.0)
    assert sc.iloc[2:].isna().all()
    assert not (sc.iloc[2:] == 0).any()
    st = dict(zip(df["player_id"], df["combined_status"]))
    assert st == {
        1: ne.BOTH,
        2: ne.BOTH,
        3: ne.IPL_ONLY,
        4: ne.T20I_ONLY,
        5: ne.NONE_VALID,
    }


def test_adjusted_estimate_is_separate_and_not_in_default_ranking():
    df = _frame(ROWS)
    adj = ne.adjusted_estimate(df, 0.7, 0.3)
    assert adj[2] == pytest.approx(3.0)  # IPL-only renormalised weight 1.0
    assert adj[3] == pytest.approx(4.0)
    assert np.isnan(adj[4])
    sc = ne.combined_scores(df, 0.7, 0.3)
    assert sc[2] != adj[2] and np.isnan(sc[2])
    # both-format players: renormalised weights equal the configured weights
    assert adj[0] == pytest.approx(sc[0])


def _samples(seed=0, n_players=60):
    rng = np.random.default_rng(seed)
    out = {"batter": [], "bowler": []}
    for fmt, m0 in (("IPL", 1000), ("T20I", 2000)):
        for p in range(1, n_players + 1):
            if fmt == "T20I" and p % 5 == 0:
                continue  # missing T20I observations for some players
            if fmt == "IPL" and p % 7 == 0:
                continue
            for m in rng.choice(40, size=int(rng.integers(1, 20)), replace=False):
                n = int(rng.integers(1, 25))
                x = rng.choice([0, 1, 2, 4, 6], size=n)
                out["batter"].append(
                    dict(
                        format=fmt,
                        player_id=p,
                        match_id=m0 + int(m),
                        n=n,
                        legal_balls=n,
                        innings=1,
                        runs_sum=float(x.sum()),
                        runs_sum2=float((x**2).sum()),
                    )
                )
                w = int((rng.random(n) < 0.06).sum())
                out["bowler"].append(
                    dict(
                        format=fmt,
                        player_id=p,
                        match_id=m0 + int(m),
                        n=n,
                        legal_balls=n,
                        innings=1,
                        econ_sum=float(x.sum()),
                        econ_sum2=float((x**2).sum()),
                        wkt_sum=float(w),
                        wkt_sum2=float(w),
                    )
                )
    return ProxySamples(pd.DataFrame(out["batter"]), pd.DataFrame(out["bowler"]))


def test_degenerate_configs_equal_format_ranks(cfg):
    res = ne.run_sensitivity(_samples(), cfg)
    for role in ("batter", "bowler"):
        d = res["roles"][role]["degenerate_check"]
        assert d["w100_0"]["ranks_equal_single_format_zscore_ranks"]
        assert d["w0_100"]["ranks_equal_single_format_zscore_ranks"]
        # eligibility identical across all eight configs
        assert res["roles"][role]["eligibility_change_summary"][
            "eligibility_identical_across_configs"
        ]


def test_every_ranking_row_carries_config_and_no_zero_fill(cfg):
    res = ne.run_sensitivity(_samples(), cfg)
    for role in ("batter", "bowler"):
        for cid, e in res["roles"][role]["configs"].items():
            assert len(e["ranking"]) == e["n_ranked"]
            for row in e["ranking"]:
                assert row["config_id"] == cid
                assert row["config_hash"] == config_hash(cfg)
                assert row["config_version"] == cfg["version"]
                assert row["combined_status"] == ne.BOTH
                assert row["ipl_z"] is not None and row["t20i_z"] is not None
        ranked_ids = {r["player_id"] for r in res["roles"][role]["configs"]["w70_30"]["ranking"]}
        single = res["roles"][role]["format_rankings"]
        # a single-format player is never in the combined ranking
        only_ipl = {r["player_id"] for r in single["IPL"]} - ranked_ids
        only_t20 = {r["player_id"] for r in single["T20I"]} - ranked_ids
        assert only_ipl and only_t20


def test_z_and_combination_arithmetic_hand_computed():
    tables = {
        "IPL": pd.DataFrame(
            {
                "player_id": [1, 2, 3],
                "balls": [10, 20, 30],
                "score": [1.0, 2.0, 3.0],
                "eligible": [True, True, True],
            }
        ),
        "T20I": pd.DataFrame(
            {
                "player_id": [1, 2, 4],
                "balls": [10, 20, 30],
                "score": [10.0, 30.0, 20.0],
                "eligible": [True, True, False],
            }
        ),
    }
    f = ne.build_player_frame(tables).set_index("player_id")
    sd = np.std([1.0, 2.0, 3.0])
    assert f.loc[1, "ipl_z"] == pytest.approx((1 - 2) / sd)
    # T20I pool is players 1 and 2 only: z = -1 and +1
    assert f.loc[1, "t20i_z"] == pytest.approx(-1.0)
    assert f.loc[2, "t20i_z"] == pytest.approx(1.0)
    assert np.isnan(f.loc[4, "t20i_z"])
    assert f.loc[4, "t20i_status"] == NE and f.loc[3, "t20i_status"] == N
    assert f.loc[3, "combined_status"] == ne.IPL_ONLY


# ------------------------------------------------------------------ ranking helpers
def test_rank_tie_break_by_player_id():
    df = pd.DataFrame({"player_id": [9, 3, 5], "score": [1.0, 1.0, 2.0]})
    r = rank_players(df)
    assert list(r["player_id"]) == [5, 3, 9]
    assert list(r["rank"]) == [1, 2, 3]


def test_overlap_spearman_movement_on_constructed_rankings():
    a = pd.DataFrame({"player_id": range(1, 13), "score": range(12, 0, -1)}, dtype=float)
    b = a.copy()
    assert topk_overlap(a["player_id"], b["player_id"], 10) == 10
    assert spearman_common(a, b)["rho"] == pytest.approx(1.0)
    rev = pd.DataFrame({"player_id": a["player_id"], "score": a["score"][::-1].to_numpy()})
    assert spearman_common(a, rev)["rho"] == pytest.approx(-1.0)
    swapped = a.copy()
    swapped.loc[swapped["player_id"] == 1, "score"] = 0.5  # player 1 drops to last
    mv = movement(a, swapped, 10)
    assert mv["leaving_top_k"] == [1] and mv["entering_top_k"] == [11]
    assert mv["biggest_movers"][0]["player_id"] == 1
    tiny = a.head(2)
    assert spearman_common(tiny, tiny) == {"rho": None, "n": 2}


# --------------------------------------------------------------- reproducibility, outputs
def _strip(res):
    res = copy.deepcopy(res)
    res.setdefault("provenance", {}).pop("generated_at_utc", None)
    return res


def test_ranking_reproducibility_and_byte_identical_json(cfg, tmp_path):
    outs = []
    for i in range(2):
        res = ne.run_sensitivity(_samples(), cfg)
        res["provenance"] = {"generated_at_utc": f"t{i}", "config_hash": config_hash(cfg)}
        p = tmp_path / f"r{i}.json"
        write_json_deterministic(p, res)
        d = json.loads(p.read_text(encoding="utf-8"))
        d["provenance"].pop("generated_at_utc")
        outs.append(json.dumps(d, sort_keys=False))
    assert outs[0] == outs[1]


def test_threshold_levels_are_nested(cfg):
    res = ne.run_sensitivity(_samples(), cfg)
    for role in ("batter", "bowler"):
        p10 = res["robustness"]["P10"]["roles"][role]["combined_population"]
        p25 = res["roles"][role]["combined_population"]
        p50 = res["robustness"]["P50"]["roles"][role]["combined_population"]
        assert p10 >= p25 >= p50
        ch = res["robustness"]["P10"]["roles"][role]["eligibility_change_vs_primary"]
        assert ch["leaving"] == 0 and ch["entering"] == p10 - p25


# ----------------------------------------------------- registration on a temp DB (idempotent)
def test_register_is_idempotent_and_leaves_official_tables_unchanged(cfg, tmp_path):
    src = BACKEND_ROOT / "data" / "database" / "superr.duckdb"
    if not src.exists():
        pytest.skip("real DB not available")
    dst = tmp_path / "t.duckdb"
    shutil.copy(src, dst)
    tmp = connect(dst, read_only=False)
    tmp.execute("DELETE FROM model_versions WHERE name = 'format-weights-v1'")
    tmp.close()
    before = snapshot_official(dst, tmp_path, include_db_file_hash=False)
    assert register_config_in_model_versions(dst, cfg) is True
    assert register_config_in_model_versions(dst, cfg) is False
    after = snapshot_official(dst, tmp_path, include_db_file_hash=False)
    assert before == after
    db = connect(dst, read_only=True)
    try:
        rows = db.query(
            "SELECT status, kind, config_json FROM model_versions WHERE name = 'format-weights-v1'"
        )
    finally:
        db.close()
    assert len(rows) == 1 and rows[0][0] == "PROVISIONAL" and rows[0][1] == "WEIGHTING_CONFIG"
    assert config_hash(cfg) in rows[0][2]
