"""Phase 4 Stage F: TEST evaluation helpers, spot checks, report generators, orchestrator checks.

Synthetic data for the logic; stored outputs for the "every number comes from stored results"
checks (skipped when the stored outputs are absent).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase4 import reports as rp
from app.phase4 import spotchecks as spc
from app.phase4 import test_eval as te
from app.phase4.split import Split, TestLock, TestPeriodLockError

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"


# ---------------------------------------------------------------- pressure effect
def test_pressure_effect_hand_checked_and_deterministic():
    rows = []
    for m in range(1, 21):
        rows += [{"match_id": m, "press": True, "resid": 1.0}] * 3
        rows += [{"match_id": m, "press": False, "resid": 0.25}] * 3
    df = pd.DataFrame(rows)
    a = te.pressure_effect(df, n_boot=200, seed=7)
    b = te.pressure_effect(df, n_boot=200, seed=7)
    assert a == b
    assert a["effect"] == pytest.approx(0.75)
    assert a["ci_low"] == pytest.approx(0.75) and a["ci_high"] == pytest.approx(0.75)
    assert a["pressure_rows"] == 60 and a["non_pressure_rows"] == 60 and a["matches"] == 20


def test_pressure_effect_without_both_groups_is_insufficient_not_zero():
    df = pd.DataFrame({"match_id": [1, 2], "press": [True, True], "resid": [0.5, 0.5]})
    out = te.pressure_effect(df, n_boot=50)
    assert out["status"] == "INSUFFICIENT_ROWS" and out["effect"] is None


# ---------------------------------------------------------------- player level
def _cell(n_players: int, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(1, n_players + 1):
        for per, matches in (("TRAIN", (1, 2, 3)), ("VALIDATION", (4, 5)), ("TEST", (6, 7))):
            for m in matches:
                for _ in range(3):
                    rows.append(
                        {
                            "player_id": p,
                            "match_id": m,
                            "comp": "IPL",
                            "period": per,
                            "resid": float(rng.normal(0, 1)),
                        }  # fmt: skip
                    )
    return pd.DataFrame(rows)


ELIG = {"threshold_balls": 3, "wr": 1.0, "label": "ELIGIBLE_WORKING_POOL_NOT_VALIDATED"}


def test_player_level_needs_enough_qualifying_players():
    ok = te.player_level(_cell(20), "IPL", "batter", "shrink_eb", ELIG, "TEST", n_boot=100)
    assert ok["status"] == "OK" and ok["qualifying_players"] == 20
    assert set(ok["loss_weighted_mse"]) == {"shrunk", "raw", "zero"}
    few = te.player_level(_cell(10), "IPL", "batter", "shrink_eb", ELIG, "TEST", n_boot=100)
    assert few["status"] == "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST"
    assert few["qualifying_players"] == 10 and "loss_weighted_mse" not in few


def test_player_level_without_a_threshold_is_not_relaxed():
    out = te.player_level(
        _cell(20), "IPL", "batter", "shrink_eb", {"threshold_balls": None, "wr": 1.0}, "TEST"
    )
    assert out["status"] == "NO_ELIGIBILITY_THRESHOLD" and out["qualifying_players"] == 0


def test_player_level_ignores_players_without_enough_test_balls():
    df = _cell(20)
    drop = df[(df["player_id"] <= 6) & (df["period"] == "TEST") & (df["match_id"] == 7)]
    df = df.drop(drop.index)  # six players keep only 3 TEST balls (< min_test_balls = 6)
    out = te.player_level(df, "IPL", "batter", "shrink_eb", ELIG, "TEST", n_boot=100)
    assert out["qualifying_players"] == 14
    assert out["status"] == "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST"


# ---------------------------------------------------------------- lock behaviour
def test_evaluate_frozen_refuses_without_a_frozen_file(tmp_path):
    lock = TestLock(tmp_path / "log.json")
    with pytest.raises(TestPeriodLockError):
        te.evaluate_frozen(tmp_path / "missing.json", lock, Split.from_config(), tmp_path / "s.db")
    assert not lock.is_open and not lock.opened_before()


def test_evaluate_frozen_refuses_a_modified_frozen_file(tmp_path):
    p = tmp_path / "frozen.json"
    p.write_text('{"a": 1}\n', encoding="utf-8")
    lock = TestLock(tmp_path / "log.json")
    lock.freeze(p)
    p.write_text('{"a": 2}\n', encoding="utf-8")
    with pytest.raises(TestPeriodLockError):
        te.evaluate_frozen(p, lock, Split.from_config(), tmp_path / "s.db")
    assert not lock.opened_before()


def test_lock_facts_orders_and_counts():
    ok = [{"event": "FREEZE", "sha256": "a"}, {"event": "OPEN", "sha256": "a"}, {"event": "CLOSE"}]
    f = rp.lock_facts(ok)
    assert f["freeze_recorded_before_open"] and f["opened_exactly_once"]
    assert f["hash_at_open_equals_hash_at_freeze"] and f["READ_DENIED_entries"] == 0
    bad = [{"event": "OPEN", "sha256": "a"}, {"event": "FREEZE", "sha256": "a"}, {"event": "OPEN"}]
    g = rp.lock_facts(bad)
    assert not g["opened_exactly_once"] and not g["freeze_recorded_before_open"]
    assert rp.lock_facts([])["freeze_recorded_before_open"] is None


# ---------------------------------------------------------------- spot-check helpers
def test_hash_check_detects_a_changed_file(tmp_path):
    import hashlib

    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("x\n", encoding="utf-8")
    b.write_text("y\n", encoding="utf-8")
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()  # noqa: E731
    ref = tmp_path / "hashes.txt"
    ref.write_text(f"\ufeff{h(a)} {a}\n{h(b)} {b}\n", encoding="utf-8")
    assert spc.check_hashes(ref)["ok"]
    b.write_text("z\n", encoding="utf-8")
    out = spc.check_hashes(ref)
    assert not out["ok"] and out["changed"] == [str(b)]


def test_hash_check_skips_the_exploratory_store(tmp_path):
    s = tmp_path / "exploratory.duckdb"
    s.write_bytes(b"one")
    ref = tmp_path / "hashes.txt"
    ref.write_text(f"{'0' * 64} {s}\n", encoding="utf-8")
    assert spc.check_hashes(ref)["ok"]


def test_shrunk_check_reproduces_a_hand_example():
    # B = n_eff / (n_eff + k) = 4 / (4 + 4) = 0.5; shrunk = target + B (resid - target)
    target, resid = 0.02, 0.5
    shrunk = target + 0.5 * (resid - target)
    frozen = {"definition": {"id": "d"}, "shrinkage": {"config": "c"}}
    base = {
        "definition_id": "d", "shrinkage_config": "c", "format": "IPL", "role": "batter",
        "stream": "runs", "effective_sample_size": 4.0, "shrinkage_k": 4.0, "data_weight": 0.5,
        "residual": resid, "raw_pressure_outcome": 1.5, "expected_baseline_outcome": 1.0,
        "shrunk_estimate": shrunk, "interval_low": 0.0, "interval_high": 0.6,
    }  # fmt: skip
    out = spc.check_shrunk_by_hand(pd.DataFrame([base, {**base}]), frozen)
    assert out["ok"] and out["max_abs_B_error"] < 1e-12
    wrong = pd.DataFrame([{**base, "data_weight": 0.9}])
    assert not spc.check_shrunk_by_hand(wrong, frozen)["ok"]


def test_inclusion_sums_check():
    dist = pd.DataFrame(
        {"scope": ["IPL"] * 4, "role": ["batter"] * 4, "top10_inclusion_prob": [0.5] * 4}
    )
    summ = pd.DataFrame({"scope": ["IPL"], "role": ["batter"], "pool_size": [2]})
    assert spc.check_inclusion_sums(dist, summ)["ok"]  # sums to 2 = min(10, pool 2)
    summ["pool_size"] = 40
    assert not spc.check_inclusion_sums(dist, summ)["ok"]


# ---------------------------------------------------------------- scans and data-quality masks
def test_literal_scan_ignores_docstrings_but_finds_code_strings(tmp_path):
    f = tmp_path / "m.py"
    f.write_text(
        '"""Cricsheet is never a source."""\n'
        "def g():\n"
        '    """Cricsheet again."""\n'
        '    return "cricsheet/data.json"\n',
        encoding="utf-8",
    )
    out = rp.nonoutcome_literals([f], "cricsheet")
    assert out["string_literal_hits"] == 1 and out["hits"] == ["m.py:4"]


def test_phase4_sources_contain_no_cricsheet_string_literal():
    out = rp.nonoutcome_literals(rp.phase4_sources(), "cricsheet")
    assert out["string_literal_hits"] == 0, out["hits"]


def test_row_exclusion_categories_are_exclusive_and_preserve_rows(tmp_path):
    import duckdb

    store = tmp_path / "s.duckdb"
    con = duckdb.connect(str(store))
    con.execute(
        "CREATE TABLE exp_pre_delivery_state (match_date DATE, innings_number INT, "
        "competition_type VARCHAR, format_out_of_scope BOOLEAN, dls_exclude_primary BOOLEAN, "
        "regulation_pressure_eligible BOOLEAN)"
    )
    con.execute(
        "INSERT INTO exp_pre_delivery_state VALUES "
        "('2024-01-01', 3, 'IPL', false, false, false), "
        "('2024-01-01', 1, 'OTHER_T20', true, false, true), "
        "('2024-01-01', 1, 'IPL', false, true, true), "
        "('2025-06-01', 2, 'T20I', false, false, false), "
        "('2026-02-01', 1, 'T20I', false, false, true), "
        "('2026-02-01', 1, 'T20I', false, false, true)"
    )
    con.close()
    cfg = {"periods": {"TRAIN": {"end": "2024-12-31"}, "VALIDATION": {"end": "2025-12-31"}}}
    out = rp.row_exclusions(store, cfg)
    assert int(out["rows"].sum()) == 6
    got = {(r.period, r.category): int(r.rows) for r in out.itertuples()}
    assert got[("TRAIN", "1_innings_3_4_restricted")] == 1
    assert got[("TRAIN", "2_out_of_scope_format")] == 1
    assert got[("TRAIN", "3_dls_not_reconstructable")] == 1
    assert got[("VALIDATION", "4_not_regulation_eligible")] == 1
    assert got[("TEST", "5_in_primary_scoring_base")] == 2


# ---------------------------------------------------------------- orchestrator helpers
def test_orchestrator_deliverable_check_and_hashes(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_phase4", ROOT / "scripts" / "run_phase4.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "phase4_user_summary.md").write_text("x", encoding="utf-8")
    (tmp_path / "phase4_frozen_choices.json").write_text(
        json.dumps({"status": "EXPERIMENTAL_NOT_VALIDATED", "official_ranking": True}),
        encoding="utf-8",
    )
    (tmp_path / "phase4_lock_log.json").write_text("[]", encoding="utf-8")
    res = mod.check_deliverables(tmp_path)
    assert res["phase4_user_summary.md"]["ok"]
    assert not res["phase4_frozen_choices.json"]["ok"]  # official_ranking true is refused
    assert not res["phase4_temporal_validation_plan.md"]["ok"]  # missing
    hashes = mod.output_hashes(tmp_path)
    assert "phase4_lock_log.json" not in hashes and "phase4_user_summary.md" in hashes
    with pytest.raises(SystemExit):
        mod.main(["--steps", "not_a_step", "--reports", str(tmp_path)])


# ---------------------------------------------------------------- reports read stored results
NEEDED = [
    "phase4_split_manifest.json", "phase4_calibration.json", "phase4_definition_selection.json",
    "phase4_frozen_choices.json", "phase4_shrinkage_choice_final.json",
    "phase4_classification_coverage.json", "phase3_data_quality_application.json",
    "phase4_pressure_scores_frozen_rules.csv", "phase4_eligibility_frozen.csv",
    "phase4_format_weight_results.csv", "phase4_ranking_summary.csv",
    "phase4_ranking_distributions.csv", "phase4_definition_comparison.csv",
    "phase4_unresolved_players.csv", "phase4_lock_log.json",
]  # fmt: skip


@pytest.fixture()
def stored(tmp_path):
    if not all((REPORTS / n).exists() for n in NEEDED):
        pytest.skip("stored Phase 4 outputs absent")
    for n in NEEDED + ["phase4_test_evaluation.json", "phase4_spot_checks.json"]:
        if (REPORTS / n).exists():
            shutil.copy(REPORTS / n, tmp_path / n)
    return tmp_path


def _split_cfg():
    return json.loads((ROOT / "config" / "phase4_split_v1.json").read_text(encoding="utf-8"))


def test_user_summary_numbers_follow_the_stored_results(stored):
    p = stored / "phase4_ranking_summary.csv"
    df = pd.read_csv(p)
    df.loc[0, "pool_size"] = 98765
    df.to_csv(p, index=False)
    late = {
        "core_end": "2026-05-31",
        "t20i_matches_after_core_end": 31337,
        "last_date": "2026-11-01",
    }
    text = rp.render_user_summary(rp.load_bundle(stored), _split_cfg(), late)
    flat = text.replace(",", "")
    assert "98765" in flat and "31337" in flat
    assert "EXPERIMENTAL_NOT_VALIDATED" in text and "not authorised" in text
    for section in ("Data split methodology", "Temporal leakage checks", "Baseline calibration",
                    "Pressure definition comparison", "Eligibility", "Shrinkage", "Format weighting",
                    "Ranking stability", "Uncertainty", "Data-quality restrictions", "limitations",
                    "Recommended final methodology", "Open decisions", "Data request"):  # fmt: skip
        assert section.lower() in text.lower(), section


def test_scoring_report_numbers_follow_the_stored_scores(stored):
    b = rp.load_bundle(stored)
    defn = b.frozen["definition"]["id"]
    b.scores.loc[b.scores["definition_id"] == defn, "pressure_opportunities"] = 424242
    text = rp.render_pressure_scoring(b)
    assert "424242" in text.replace(",", "")
    assert "EXPERIMENTAL_NOT_VALIDATED" in text and "shrink_none" in text
    assert b.frozen["shrinkage"]["config"] in text


def test_data_quality_report_covers_the_register_and_follows_stored_counts(stored):
    b = rp.load_bundle(stored)
    b.dq["checks"]["innings_3_4"]["rows"] = 777001
    b.dq["checks"]["extras"]["category_counts"]["Penalty"] = 777002
    excl = pd.DataFrame(
        {"period": ["TRAIN"], "category": ["5_in_primary_scoring_base"], "rows": [5]}
    )
    late = {"core_end": "2026-05-31", "t20i_matches_after_core_end": 42}
    lits = {"files_scanned": 3, "string_literal_hits": 0, "hits": []}
    text = rp.render_data_quality(b, _split_cfg(), excl, late, lits)
    flat = text.replace(",", "")
    assert "777001" in flat and "777002" in flat
    for needle in ("RULE_INNINGS_3_4", "CONFIRMED_SUPER_OVER_BY_CRICSHEET", "UNVERIFIED_INNINGS_ROLE",
                   "Penalty", "other", "DLS", "player_id", "never imputed", "never multiply",
                   "Cricsheet is not a data source"):  # fmt: skip
        assert needle in text, needle
    assert "0 hits" in text


def test_test_evaluation_report_states_insufficient_cells_without_relaxing(stored):
    if not (stored / "phase4_test_evaluation.json").exists():
        pytest.skip("TEST evaluation not run")
    res = json.loads((stored / "phase4_test_evaluation.json").read_text(encoding="utf-8"))
    res["player_level"][0].update(
        {"status": "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST", "qualifying_players": 3}
    )
    text = rp.render_test_evaluation(res)
    assert "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST" in text
    assert res["definition_id"] in text
    assert res["official_ranking"] is False and res["status"] == "EXPERIMENTAL_NOT_VALIDATED"


def test_stored_test_run_opened_the_lock_once_after_the_freeze():
    p = REPORTS / "phase4_lock_log.json"
    if not p.exists():
        pytest.skip("lock log absent")
    f = rp.lock_facts(json.loads(p.read_text(encoding="utf-8")))
    if f["OPEN_entries"] == 0:
        pytest.skip("TEST evaluation not run")
    assert f["opened_exactly_once"] and f["freeze_recorded_before_open"]
    assert f["hash_at_open_equals_hash_at_freeze"]
