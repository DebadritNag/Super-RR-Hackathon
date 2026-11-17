"""Stage 3 tests: wickets-bin merge, relative percentile, candidate flags and pressure sample
counts (independent pandas recount), knee rule. EXPLORATORY code; no ranking is produced."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics import pressure_distributions as pdist
from app.analytics import pressure_features as pf
from app.services import pressure_service as ps


def _merge_frame(counts: dict[tuple[str, int], int]) -> pd.DataFrame:
    rows, k = [], 0
    for (cell, w), n in counts.items():
        for _ in range(n):
            k += 1
            rows.append({"cell": cell, "inn_key": k, "wrem": w})
    return pd.DataFrame(rows)


def test_merge_only_deficient_bin_merges_and_low_bins_stay_separate():
    counts = {("A", w): 50 for w in range(1, 11)}
    counts[("A", 10)] = 5  # only {10} is deficient
    out = pf.merge_wickets_bins(_merge_frame(counts), 30)
    assert [10, 9] in out["bins"] and [2] in out["bins"] and [1] in out["bins"]
    assert len(out["bins"]) == 9 and not out["wickets_bins_failed"]
    assert out["merge_log"][0]["deficient_bin"] == [10]


def test_merge_no_merge_when_all_bins_sufficient():
    out = pf.merge_wickets_bins(_merge_frame({("A", w): 40 for w in range(1, 11)}), 30)
    assert len(out["bins"]) == 10 and out["merge_log"] == []


def test_merge_fails_flag_when_total_too_small():
    out = pf.merge_wickets_bins(_merge_frame({("A", w): 1 for w in range(1, 11)}), 30)
    assert out["bins"] == [list(range(10, 0, -1))] and out["wickets_bins_failed"]


def test_rank_pct_excludes_own_match_and_uses_mid_rank():
    v = np.array([1.0, 2.0, 2.0, 3.0, 5.0])
    cell = np.array(["c"] * 5)
    match = np.array([1, 2, 2, 3, 1])
    r = pf.rank_pct_excl_match(v, cell, match, np.ones(5, bool))
    # row 1 (value 2, match 2): V = {1, 3, 5}; less = 1, eq = 0 -> 1/3
    assert r[1] == pytest.approx(1 / 3)
    # row 0 (value 1, match 1): V = {2, 2, 3}; less = 0 -> 0
    assert r[0] == pytest.approx(0.0)
    # row 4 (value 5, match 1): V = {2, 2, 3} -> 1
    assert r[4] == pytest.approx(1.0)
    v2 = np.array([2.0, 2.0, 2.0])
    r2 = pf.rank_pct_excl_match(v2, np.array(["c"] * 3), np.array([1, 2, 3]), np.ones(3, bool))
    assert r2 == pytest.approx([0.5, 0.5, 0.5])


def test_rank_pct_null_signal_is_null_and_excluded_from_v():
    v = np.array([1.0, np.nan, 3.0, 2.0])
    r = pf.rank_pct_excl_match(v, np.array(["c"] * 4), np.array([1, 2, 3, 4]), np.ones(4, bool))
    assert np.isnan(r[1])
    assert r[3] == pytest.approx(0.5)  # V = {1, 3}


def test_lower_quantile_is_an_observed_value():
    x = np.array([10, 9, 9, 8, 3, 1.0])
    assert pf.lower_quantile(x, 0.25) in set(x)


def _counts_frame():
    """Ten rows; batter rows exclude the wide, bowler rows exclude the Penalty."""
    return pd.DataFrame({
        "striker_id": [1, 1, 1, 2, 2, 2, 1, 3, 3, 3],
        "bowler_id": [9, 9, 9, 9, 8, 8, 8, 8, 8, 8],
        "match_id": [100, 100, 100, 100, 200, 200, 200, 300, 300, 300],
        "inn_key": [1001, 1001, 1001, 1001, 2002, 2002, 2002, 3002, 3002, 3002],
        "den_counts_as_ball_faced": [1, 0, 1, 1, 1, 1, 1, 1, 1, 0],
        "den_bowler_counts_row": [1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        "den_legal_inc": [1, 0, 1, 1, 1, 1, 1, 1, 1, 0],
    })  # fmt: skip


def test_pressure_sample_counts_match_independent_pandas_count():
    df = _counts_frame()
    mask = np.array([1, 1, 1, 0, 1, 1, 1, 1, 1, 1], bool)
    bat = pdist.player_counts(df, mask, "batter").set_index("player_id")
    sub = df[mask & (df["den_counts_as_ball_faced"] == 1)]
    exp = sub.groupby("striker_id").agg(n=("match_id", "size"), matches=("match_id", "nunique"))
    assert bat["n"].to_dict() == exp["n"].to_dict()
    assert bat["matches"].to_dict() == exp["matches"].to_dict()
    assert bat.loc[1, "n"] == 3  # wide on row 2 is not a ball faced
    bowl = pdist.player_counts(df, mask, "bowler").set_index("player_id")
    assert bowl.loc[9, "n"] == 3 and bowl.loc[9, "legal"] == 2  # wide counts as an opportunity
    assert bowl.loc[8, "n"] == 5 and bowl.loc[8, "legal"] == 5  # Penalty row not counted


def test_pressure_sample_kish_effective_size():
    df = _counts_frame()
    out = pdist.player_counts(df, np.ones(len(df), bool), "batter").set_index("player_id")
    # player 1: 2 balls in match 100, 1 in match 200 -> (3^2)/(4+1) = 1.8
    assert out.loc[1, "n_eff_kish"] == pytest.approx(1.8)
    assert pdist.kish([5, 5]) == pytest.approx(2.0) and pdist.kish([]) == 0.0


def test_effect_row_counts_matches_innings_and_floors():
    df = _counts_frame()
    spec = {"id": "x", "family": "a", "ctx": "chase", "comp": "IPL", "role": "batter",
            "signal": "s", "view": "abs", "q": 0.5, "threshold": 1.0}  # fmt: skip
    e = pdist.effect_row(df, spec, np.ones(len(df), bool))
    assert e["pressure_rows"] == 10 and e["pressure_unit_rows"] == 8
    assert e["matches"] == 3 and e["innings"] == 3
    assert e["players_ge_floor2"] == 0  # floors come from the Phase 2.5 ladders (60 balls)


def test_knee_point_finds_break_of_kinked_curve():
    x = np.r_[np.linspace(0, 1, 900), np.linspace(1, 10, 100)]
    k = pdist.knee_point(x)
    assert k["available"] and 0.5 <= k["value"] <= 2.0
    assert not pdist.knee_point(np.ones(100))["available"]


def test_describe_handles_nulls():
    d = pdist.describe(np.array([1.0, np.nan, 3.0]))
    assert d["n"] == 3 and d["n_null"] == 1 and d["p50"] == pytest.approx(2.0)
    assert pdist.describe(np.array([np.nan]))["n_null"] == 1


@pytest.mark.realdata
def test_real_store_populations_and_restricted_innings():
    if not ps.EXPLORATORY_DB.exists():
        pytest.skip("exploratory store not built")
    df = pf.add_populations(pf.load_state(ps.EXPLORATORY_DB))
    pop = df["chase_pop"] | df["inn1_pop"]
    assert not (pop & ~df["innings_number"].isin([1, 2])).any()  # innings 3/4 never in a population
    assert not (pop & (df["competition_type"] == "OTHER_T20")).any()
    assert not (df["chase_pop"] & df["req_nonpositive_flag"].fillna(False)).any()
    assert not (df["chase_pop"] & df["target_basis_unverified"].fillna(False)).any()
    assert int((~df["innings_number"].isin([1, 2])).sum()) == 38
