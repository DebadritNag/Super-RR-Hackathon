"""Stage 6 tests: pressure format-weight sensitivity, missing-format handling, short lists.
EXPLORATORY code; no official ranking is produced."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.analytics import normalization_engine as ne
from app.analytics import pressure_format_sensitivity as pfs
from app.analytics.format_config import config_hash, load_config

ROOT = Path(__file__).resolve().parents[1]
FCFG = load_config(ROOT / "config" / "format_weights_v1.json")
REPORTS = ROOT / "data" / "reports"


def _sample_rows(players_by_fmt: dict[str, list[int]], seed: int = 0) -> pd.DataFrame:
    """Batter pressure samples with 3 matches per player."""
    rng = np.random.default_rng(seed)
    rows = []
    for fmt, ids in players_by_fmt.items():
        for pid in ids:
            for m in range(3):
                n = 10
                r = rng.normal(0.0, 1.0, size=n)
                rows.append({
                    "format": fmt, "player_id": pid, "match_id": m + (100 if fmt == "T20I" else 0),
                    "n": n, "legal_balls": n, "innings": 1,
                    "runs_sum": float(r.sum()), "runs_sum2": float((r**2).sum()),
                })  # fmt: skip
    cols = [
        "format",
        "player_id",
        "match_id",
        "n",
        "legal_balls",
        "innings",
        "runs_sum",
        "runs_sum2",
    ]
    return pd.DataFrame(rows, columns=cols)


def _bowl_from(bat: pd.DataFrame) -> pd.DataFrame:
    b = bat.rename(columns={"runs_sum": "econ_sum", "runs_sum2": "econ_sum2"}).copy()
    b["wkt_sum"] = b["econ_sum"] * 0.01
    b["wkt_sum2"] = b["econ_sum2"] * 0.01
    return b


THR = {f: {"batter": 20, "bowler": 20} for f in ("IPL", "T20I")}


def _run(players_by_fmt, thresholds=THR, robustness=None):
    bat = _sample_rows(players_by_fmt)
    return pfs.run(
        bat, _bowl_from(bat), FCFG, thresholds, robustness or {}, 10, "PRESSURE_SPECIFIC"
    )


# ---------------------------------------------------------------- missing formats
def test_missing_format_gives_null_combined_and_explicit_status_never_zero():
    tables, _ = pfs.pressure_tables(
        _sample_rows({"IPL": [1, 2, 3], "T20I": [2, 3, 4]}),
        _bowl_from(_sample_rows({"IPL": [1], "T20I": [1]})),
        THR,
    )
    frame = ne.build_player_frame(tables["batter"]).set_index("player_id")
    assert (
        frame.loc[1, "combined_status"] == ne.IPL_ONLY
        and frame.loc[4, "combined_status"] == ne.T20I_ONLY
    )
    assert frame.loc[2, "combined_status"] == ne.BOTH
    assert pd.isna(frame.loc[1, "t20i_z"]) and frame.loc[1, "t20i_status"] == ne.NOT_OBSERVED
    for c in FCFG["configurations"]:
        sc = ne.combined_scores(frame.reset_index(), c["ipl_weight"], c["t20i_weight"])
        sc.index = frame.index
        assert pd.isna(sc.loc[1]) and pd.isna(sc.loc[4])  # NULL, not 0
        assert sc.loc[[2, 3]].notna().all()
    audit = pfs.missing_format_audit(frame.reset_index(), FCFG)
    assert (
        audit["combined_scores_present_for_them"] == 0
        and audit["z_present_for_not_eligible_format"] == 0
    )


def test_observed_but_not_eligible_format_is_also_null():
    bat = _sample_rows({"IPL": [1, 2], "T20I": [1, 2]})
    bat = bat[~((bat["format"] == "T20I") & (bat["player_id"] == 1) & (bat["match_id"] > 100))]
    tables, _ = pfs.pressure_tables(bat, _bowl_from(bat), THR)  # player 1 has 10 T20I balls < 20
    frame = ne.build_player_frame(tables["batter"]).set_index("player_id")
    assert frame.loc[1, "t20i_status"] == ne.OBSERVED_NOT_ELIGIBLE
    assert frame.loc[1, "combined_status"] == ne.IPL_ONLY and pd.isna(frame.loc[1, "t20i_z"])


def test_format_without_pressure_rows_yields_empty_table_not_fake_players():
    bat = _sample_rows({"IPL": [1, 2, 3]})
    tables, thr = pfs.pressure_tables(bat, _bowl_from(bat), THR)
    assert len(tables["batter"]["T20I"]) == 0 and len(tables["bowler"]["T20I"]) == 0
    res = _run({"IPL": [1, 2, 3]})
    assert res["roles"]["batter"]["combined_population"] == 0
    assert res["roles"]["batter"]["status_counts"]["combined_status"][ne.BOTH] == 0
    for e in res["roles"]["batter"]["configs"].values():
        assert e["top10_player_ids"] == [] and e["spearman_with_default"] is None


# ---------------------------------------------------------------- single-format and adjusted
def test_single_format_players_only_in_own_format_list_and_adjusted_section():
    res = _run({"IPL": [1, 2, 3, 4], "T20I": [3, 4, 5, 6]})
    r = res["roles"]["batter"]
    assert r["combined_population"] == 2
    ipl = {x["player_id"] for x in r["format_rankings"]["IPL"]["top_rows"]}
    t20 = {x["player_id"] for x in r["format_rankings"]["T20I"]["top_rows"]}
    assert ipl == {1, 2, 3, 4} and t20 == {3, 4, 5, 6}
    for e in r["configs"].values():
        assert set(e["top10_player_ids"]) == {3, 4}  # single-format players never in combined
    adj = r["adjusted_estimate"]
    assert adj["label"] == "ADJUSTED_ESTIMATE" and adj["n_ranked"] == 6
    assert "not a combined score" in adj["note"].lower()
    assert all("combined_score" not in x for x in adj["ranking"])


def test_adjusted_estimate_is_separate_from_default_ranking():
    bat = _sample_rows({"IPL": [1, 2, 3], "T20I": [3]})
    tables, _ = pfs.pressure_tables(bat, _bowl_from(bat), THR)
    frame = ne.build_player_frame(tables["batter"])
    est = ne.adjusted_estimate(frame, 0.7, 0.3)
    comb = ne.combined_scores(frame, 0.7, 0.3)
    one = frame.index[frame["player_id"] == 1][0]
    assert pd.isna(comb[one]) and est[one] == pytest.approx(frame.loc[one, "ipl_z"])


# ---------------------------------------------------------------- eight configs, hashes, short lists
def test_eight_configs_present_with_hash_and_default_provisional():
    res = _run({"IPL": list(range(1, 15)), "T20I": list(range(1, 15))})
    ids = [c["id"] for c in FCFG["configurations"]]
    assert ids == ["w100_0", "w85_15", "w80_20", "w70_30", "w60_40", "w55_45", "w50_50", "w0_100"]
    cfgs = res["roles"]["batter"]["configs"]
    assert list(cfgs) == ids
    for c in cfgs.values():
        assert c["config_hash"] == config_hash(FCFG) == res["config_hash_all_results"]
    assert res["config"]["default_config_id"] == "w70_30"
    assert res["config"]["default_flag"] == "PROVISIONAL_NOT_VALIDATED"
    assert res["official_ranking"] is False and res["not_for_publication"] is True
    assert res["status"] == "EXPLORATORY_NOT_VALIDATED"


def test_short_combined_list_is_not_padded_and_overlap_is_bounded():
    res = _run({"IPL": list(range(1, 9)), "T20I": list(range(1, 9))})  # 8 players eligible in both
    r = res["roles"]["batter"]
    assert r["combined_population"] == 8
    for e in r["configs"].values():
        assert len(e["top10_player_ids"]) == 8 and e["n_ranked"] == 8
        assert e["overlap_with_default"] <= 8


def test_degenerate_configs_use_same_population_and_single_format_order():
    res = _run({"IPL": list(range(1, 13)), "T20I": list(range(1, 13))})
    r = res["roles"]["batter"]
    assert r["degenerate_check"]["w100_0"]["ranks_equal_single_format_zscore_ranks"]
    assert r["degenerate_check"]["w0_100"]["ranks_equal_single_format_zscore_ranks"]
    assert pfs.degenerate_note(res)["batter"] is True
    assert r["configs"]["w100_0"]["n_ranked"] == r["configs"]["w0_100"]["n_ranked"] == 12


def test_default_config_compared_with_itself_is_identical():
    res = _run({"IPL": list(range(1, 13)), "T20I": list(range(1, 13))})
    d = res["roles"]["batter"]["configs"]["w70_30"]
    assert d["overlap_with_default"] == 10 and d["spearman_with_default"] == pytest.approx(1.0)
    assert d["movement_vs_default"]["mean_abs_change"] == 0


def test_robustness_thresholds_change_population_and_are_reported_not_hidden():
    strict = {f: {"batter": 30, "bowler": 30} for f in ("IPL", "T20I")}
    res = _run({"IPL": [1, 2, 3, 4], "T20I": [1, 2, 3, 4]}, robustness={"STRICT": strict})
    pc = pfs.population_changes(res, None)["batter"]
    assert pc["pressure_primary"]["combined"] == 4
    assert "STRICT" in pc["pressure_robustness"]
    assert pc["pressure_robustness"]["STRICT"]["combined"] == 4  # 30 balls = 3 matches x 10


def test_rankings_are_trimmed_to_technical_ids_without_names_or_full_lists():
    res = _run({"IPL": list(range(1, 31)), "T20I": list(range(1, 31))})
    r = res["roles"]["batter"]
    assert all("ranking" not in c for c in r["configs"].values())
    assert (
        r["format_rankings"]["IPL"]["n_ranked"] == 30
        and len(r["format_rankings"]["IPL"]["top_rows"]) == 10
    )
    assert len(r["adjusted_estimate"]["ranking"]) == 10
    assert "name" not in json.dumps(res).lower().replace("config_name", "")


def test_population_change_against_phase25_all_situation_structure():
    res = _run({"IPL": [1, 2, 3], "T20I": [1, 2, 3]})
    allsit = {"eligibility_level": "P25", "roles": {
        role: {"combined_population": 133, "status_counts": {
            "ipl_status": {ne.ELIGIBLE: 257}, "t20i_status": {ne.ELIGIBLE: 506}}}
        for role in ne.ROLES}}  # fmt: skip
    out = pfs.population_changes(res, allsit)["batter"]["phase25_all_situation"]
    assert out["combined"] == 133 and out["IPL_eligible"] == 257


def test_run_sensitivity_default_path_unchanged_by_injection_arguments():
    import inspect

    sig = inspect.signature(ne.run_sensitivity)
    for name in ("tables", "thresholds", "robustness", "eligibility_label"):
        assert sig.parameters[name].default is None  # additive, defaults keep Phase 2.5 behaviour


# ---------------------------------------------------------------- real outputs
@pytest.mark.realdata
def test_real_sensitivity_output_is_exploratory_and_never_zero_fills():
    p = REPORTS / "pressure_format_weight_sensitivity.json"
    if not p.exists():
        pytest.skip("pressure sensitivity not run")
    res = json.loads(p.read_text("utf-8"))
    assert res["status"] == "EXPLORATORY_NOT_VALIDATED" and res["official_ranking"] is False
    assert res["weights_status"].startswith("70:30 is a PROVISIONAL")
    assert res["preservation"]["official_unchanged"] is True
    for role in ("batter", "bowler"):
        r = res["roles"][role]
        assert len(r["configs"]) == 8
        assert res["audit"][role]["combined_scores_present_for_them"] == 0
        assert res["audit"][role]["z_present_for_not_eligible_format"] == 0
        for e in r["configs"].values():
            assert len(e["top10_player_ids"]) == min(10, r["combined_population"])
            assert e["config_hash"] == res["config_hash_all_results"]
        assert len({e["n_ranked"] for e in r["configs"].values()}) == 1
