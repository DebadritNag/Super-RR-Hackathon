"""No future-data leakage in the pre-delivery state (truncation and mutation tests).

EXPLORATORY: these tests protect the state engine; they validate no pressure score.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from app.analytics import pressure_engine as pe
from app.core.config import BACKEND_ROOT, get_settings
from app.services import pressure_service as ps
from tests.pressure_helpers import deliveries, match, matches, number, row

RULES = pe.load_rules()
APP = BACKEND_ROOT / "app"


def state(d, m):
    return pe.compute_pre_delivery_state(d, m, RULES)


def assert_frames_equal(a: pd.DataFrame, b: pd.DataFrame, cols: list[str]) -> None:
    pd.testing.assert_frame_equal(
        a[cols].reset_index(drop=True), b[cols].reset_index(drop=True), check_dtype=False
    )


def mixed_match():
    """Two regulation innings with extras, wickets and a revised target (hand-made, 14 + 12 rows)."""
    inn1 = number([
        row(bat=1), row(extras="wide", prim=1), row(bat=4, four=True), row(bat=0),
        row(wicket=True, dtype="Caught", dismissed=11), row(extras="Overstep", prim=1, bat=1),
        row(extras="byes", prim=2), row(bat=6, six=True), row(extras="other", prim=1),
        row(bat=0, wicket=True, dtype="RunOut", dismissed=12), row(bat=2), row(bat=1),
        row(extras="Penalty", prim=5), row(bat=0),
    ])  # fmt: skip
    inn2 = number([
        row(bat=0), row(bat=1), row(extras="wide", prim=1), row(bat=4, four=True), row(bat=0),
        row(wicket=True, dtype="Bowled", dismissed=11), row(bat=1), row(bat=0),
        row(extras="legbyes", prim=1), row(bat=2), row(bat=0), row(bat=3),
    ], innings=2)  # fmt: skip
    return deliveries(inn1 + inn2), matches(match(first=60.0, second=60.0, target=33.0))


def truncate(d: pd.DataFrame, match_id: int, innings: int, keep: int) -> pd.DataFrame:
    """Drop rows of one innings after ball `keep` (the innings is cut short)."""
    drop = (d.match_id == match_id) & (d.innings_number == innings) & (d.innings_ball_num > keep)
    return d[~drop]


# ----------------------------------------------------------------------------- truncation
def test_truncation_gives_identical_state_for_every_k_and_innings_synthetic():
    d, m = mixed_match()
    full = state(d, m)
    cols = pe.pre_delivery_columns(full)
    for innings, n in ((1, 14), (2, 12)):
        for k in range(1, n + 1):
            part = state(truncate(d, 1, innings, k), m)
            a = part[part.innings_number == innings]
            b = full[(full.innings_number == innings) & (full.innings_ball_num <= k)]
            assert len(a) == len(b) == k
            assert_frames_equal(a, b, cols)


def test_truncating_innings2_never_changes_innings1_and_vice_versa_for_early_rows():
    d, m = mixed_match()
    full = state(d, m)
    cols = pe.pre_delivery_columns(full)
    no2 = state(d[d.innings_number == 1], m)
    assert_frames_equal(no2, full[full.innings_number == 1], cols)  # innings 1 ignores innings 2


def test_truncation_on_real_matches_for_several_cut_points():
    s = get_settings()
    if not s.duckdb_path.exists():
        pytest.skip("official DuckDB not present")
    d, m = pe.load_inputs(s.duckdb_path)
    # a deterministic sample: every 40th match in id order plus every DLS match with innings 2
    ids = sorted(m.match_id)
    dls = m[m.revised_target.notna()].match_id.tolist()[:6]
    pick = sorted(set(ids[::40]) | set(dls) | {34429, 48610})
    d, m = d[d.match_id.isin(pick)], m[m.match_id.isin(pick)]
    full = state(d, m)
    cols = pe.pre_delivery_columns(full)
    checked = 0
    for (mid, innings), g in d.groupby(["match_id", "innings_number"]):
        n = len(g)
        for k in sorted({1, max(1, n // 3), max(1, n // 2), max(1, n - 1)}):
            part = state(truncate(d, mid, innings, k), m)
            a = part[(part.match_id == mid) & (part.innings_number == innings)]
            b = full[(full.match_id == mid) & (full.innings_number == innings)
                     & (full.innings_ball_num <= k)]  # fmt: skip
            assert_frames_equal(a, b, cols)
            checked += 1
    assert checked > 100


def test_innings2_target_does_not_depend_on_later_innings2_rows():
    d, m = mixed_match()
    full = state(d, m)
    t_full = full[full.innings_number == 2].target
    assert t_full.nunique() == 1
    mutated = d.copy()
    later = (mutated.innings_number == 2) & (mutated.innings_ball_num > 3)
    mutated.loc[later, "batter_runs"] = 6
    part = state(mutated, m)
    first3 = part[(part.innings_number == 2) & (part.innings_ball_num <= 3)]
    assert_frames_equal(first3, full[(full.innings_number == 2) & (full.innings_ball_num <= 3)],
                        pe.pre_delivery_columns(full))  # fmt: skip
    assert (part[part.innings_number == 2].target == t_full.iloc[0]).all()


def test_innings1_target_columns_are_null_so_the_total_cannot_leak_into_innings1():
    d, m = mixed_match()
    s = state(d, m)
    i1 = s[s.innings_number == 1]
    for col in ("target", "runs_required", "rrr", "gap", "projected_surplus"):
        assert i1[col].isna().all(), col
    mutated = d.copy()
    last = (mutated.innings_number == 1) & (mutated.innings_ball_num == 14)
    mutated.loc[last, "batter_runs"] = 6
    s2 = state(mutated, m)
    assert_frames_equal(
        s2[s2.innings_number == 1].iloc[:13], i1.iloc[:13], pe.pre_delivery_columns(s)
    )


# ----------------------------------------------------------------------------- mutation
def test_mutating_extras_type_of_row_k_leaves_row_k_state_columns_identical():
    d, m = mixed_match()
    base = state(d, m)
    cols = pe.pre_delivery_columns(base)
    flips = {"wide": "None", "None": "wide", "Overstep": "byes", "byes": "wide", "other": "None",
             "Penalty": "None", "legbyes": "wide"}  # fmt: skip
    for k in range(len(d)):
        mut = d.copy()
        old = str(mut.at[k, "extras_type"])
        mut.at[k, "extras_type"] = flips[old]
        got = state(mut, m)
        assert_frames_equal(got.iloc[[k]], base.iloc[[k]], cols)


def test_mutating_every_outcome_column_of_row_k_leaves_row_k_state_unchanged():
    d, m = mixed_match()
    base = state(d, m)
    cols = pe.pre_delivery_columns(base)
    rng = np.random.default_rng(7)
    for k in range(len(d)):
        mut = d.copy()
        mut.at[k, "batter_runs"] = int(rng.integers(0, 7))
        mut.at[k, "is_wicket"] = not bool(mut.at[k, "is_wicket"])
        mut.at[k, "dismissed_player_id"] = 99
        mut.at[k, "extras_type"] = "wide"
        mut.at[k, "extras_primary_runs"] = 3
        mut.at[k, "extras_secondary_runs"] = 1
        mut.at[k, "is_legal_ball"] = not bool(mut.at[k, "is_legal_ball"])
        mut.at[k, "dismissal_type"] = "Caught"
        got = state(mut, m)
        assert_frames_equal(got.iloc[[k]], base.iloc[[k]], cols)


def test_mutating_future_rows_never_changes_earlier_state():
    d, m = mixed_match()
    base = state(d, m)
    cols = pe.pre_delivery_columns(base)
    for k in (3, 7, 10):
        mut = d.copy()
        fut = (mut.innings_number == 1) & (mut.innings_ball_num > k)
        mut.loc[fut, "batter_runs"] = 6
        mut.loc[fut, "is_wicket"] = True
        mut.loc[fut, "extras_type"] = "wide"
        mut.loc[fut, "is_legal_ball"] = False
        got = state(mut, m)
        sel = lambda f: f[(f.innings_number == 1) & (f.innings_ball_num <= k)]  # noqa: E731
        assert_frames_equal(sel(got), sel(base), cols)


def test_match_result_columns_are_ignored_by_the_engine():
    d, m = mixed_match()
    base = state(d, m)
    m2 = m.copy()
    m2["win_team_id"], m2["result"], m2["result_status"] = 2, "Team B won by 5 wickets", "COMPLETED"
    m2["man_of_the_match"] = 77
    changed = state(d, m2)
    assert_frames_equal(changed, base, list(base.columns))
    m3 = m2.copy()
    m3["win_team_id"], m3["result"], m3["man_of_the_match"] = 1, "Team A won by 1 run", 12
    assert_frames_equal(state(d, m3), base, list(base.columns))


def test_mutation_of_a_later_innings2_row_changes_only_rows_after_it():
    d, m = mixed_match()
    base = state(d, m)
    mut = d.copy()
    idx = mut.index[(mut.innings_number == 2) & (mut.innings_ball_num == 6)][0]
    mut.at[idx, "batter_runs"] = 6
    got = state(mut, m)
    i2b, i2g = base[base.innings_number == 2], got[got.innings_number == 2]
    cols = pe.pre_delivery_columns(base)
    assert_frames_equal(i2g.iloc[:6], i2b.iloc[:6], cols)
    assert (
        i2g.iloc[6:].team_runs_before.to_numpy() > i2b.iloc[6:].team_runs_before.to_numpy()
    ).all()


# ----------------------------------------------------------------------------- static guarantees
FORBIDDEN = ("win_team_id", "result_status", "man_of_the_match", "source_total_runs",
             "delivery_count", "legal_ball_count", "delivery_ts", "match_squads")  # fmt: skip


def _sources():
    return [APP / "analytics" / n for n in
            ("pressure_engine.py", "cricket_calculations.py", "phase_engine.py")]  # fmt: skip


def test_engine_modules_never_reference_forbidden_columns():
    for path in _sources():
        text = path.read_text(encoding="utf-8")
        code = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith(("#", '"""')))
        for word in FORBIDDEN:
            assert word not in code, f"{path.name} mentions {word}"
        assert not re.search(r"""["']result["']""", code), f"{path.name} reads result"


def test_engine_modules_open_no_cricsheet_path_and_never_write_sql():
    for path in _sources():
        text = path.read_text(encoding="utf-8").lower()
        assert "_male_json" not in text and "cricsheet_dirs" not in text, path.name
        assert not re.search(
            r"insert into|create (or replace )?table|update \w+ set|delete from", text
        )
        assert "read_only=false" not in text


def test_load_inputs_selects_no_outcome_of_the_match():
    sql = pe.MATCH_SQL.lower()
    for word in ("win_team_id", "result", "man_of_the_match"):
        assert word not in sql
    assert "has_deliveries" in sql


def test_cricsheet_values_come_only_from_phase25_reports_not_files():
    text = (APP / "services" / "pressure_service.py").read_text(encoding="utf-8")
    assert "_male_json" not in text and "cricsheet_dirs" not in text
    assert ps.SUPER_OVER_REPORT.endswith(".json") and ps.DQ_REPORT.endswith(".json")


# ----------------------------------------------------------------------------- store
def test_store_refuses_the_official_database_path(tmp_path):
    d, m = mixed_match()
    s = state(d, m)
    official = tmp_path / "official.duckdb"
    with pytest.raises(ps.StoreError):
        ps.write_store(s, {}, official, official)


def test_store_roundtrip_in_a_separate_file(tmp_path):
    import duckdb

    d, m = mixed_match()
    s = state(d, m)
    store = tmp_path / "exp.duckdb"
    ps.write_store(s, {"status": "EXPLORATORY_NOT_VALIDATED"}, store, tmp_path / "official.duckdb")
    con = duckdb.connect(str(store), read_only=True)
    try:
        n = con.execute(f"SELECT count(*) FROM {ps.STATE_TABLE}").fetchone()[0]
        v = con.execute(f"SELECT DISTINCT state_version FROM {ps.STATE_TABLE}").fetchall()
    finally:
        con.close()
    assert n == len(s) and v == [("pre_delivery_state_v1",)]


def test_real_build_leaves_official_data_unchanged_and_writes_only_the_store(tmp_path):
    s = get_settings()
    if not s.duckdb_path.exists():
        pytest.skip("official DuckDB not present")
    import shutil

    reports = tmp_path / "reports"
    reports.mkdir()
    for n in (ps.SUPER_OVER_REPORT, ps.DQ_REPORT):
        shutil.copy(s.phase25_reports_dir / n, reports / n)
    store = tmp_path / "exploratory.duckdb"
    man = ps.build_and_store(s, None, store, reports)
    assert man["preservation"]["official_data_unchanged"] is True
    assert man["store"]["path"].endswith("exploratory.duckdb")
    assert (reports / ps.MANIFEST_NAME).exists()
    assert man["checks"]["rows"] == 200_999 and man["inputs"]["cricsheet_files_opened"] == 0
    assert man["status"] == "EXPLORATORY_NOT_VALIDATED" and man["official_ranking"] is False
