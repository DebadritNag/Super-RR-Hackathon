"""Phase 5 date verification: classes, originals, restricted TEST sets, Cricsheet confinement, lock."""

from __future__ import annotations

import ast
import csv
import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from app.phase5 import date_verification as dv
from app.phase5 import test_manifest as tm
from app.phase5.constants import CONFIG_DIR, REPORTS_DIR
from app.phase5.data import OutcomeColumnError, check_columns, load_test_match_state_nonoutcome
from app.phase5.lockguard import (
    PHASE5_LOCK_LOG,
    LockGuardError,
    assert_phase4_lock_untouched,
    assert_phase5_lock_not_opened,
    file_sha256,
)

CFG = json.loads((CONFIG_DIR / "phase5_date_verification_v1.json").read_text(encoding="utf-8"))
BACKEND = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ synthetic builders
def _matches(rows: list[tuple]) -> pd.DataFrame:
    """rows: (match_id, comp_id, match_number, date, home_id, away_id)."""
    return pd.DataFrame(
        [
            {
                "match_id": i,
                "comp_id": c,
                "match_number": n,
                "match_date": pd.Timestamp(d),
                "stage": "Others",
                "home_team_id": h,
                "home_team": f"Team{h}",
                "away_team_id": a,
                "away_team": f"Team{a}",
                "competition_type": "T20I",
                "has_deliveries": True,
            }
            for i, c, n, d, h, a in rows
        ]
    )


COMPS = pd.DataFrame(
    [{"comp_id": 10, "comp_name": "Team1 in Team2 T20I Series 2026", "season": 2026}]
)


def _ts(mid: int, first: str, last: str | None = None, nonmid: int = 100, rows: int = 100) -> dict:
    return {
        "match_id": mid,
        "n_rows": rows,
        "n_nonmidnight": nonmid,
        "min_ts": f"{first} 16:00:00 UTC",
        "max_ts": f"{last or first} 19:00:00 UTC",
    }


def _cs(mid: str, d: str, total: int = 150, teams: tuple[int, int] = (1, 2)) -> dict:
    key = "|".join(sorted(f"team{t}" for t in teams))
    return {
        "match_id": mid,
        "directory": "t20s_male_json",
        "date": d,
        "teams_key": key,
        "match_type": "T20",
        "gender": "male",
        "innings_json": json.dumps([{"team": "Team1", "super_over": False, "total": total}]),
    }


def _run(matches, ts, cs_rows, official=None, first_total=150):
    """``first_total``: one total for every match or a ``{match_id: total}`` dict."""
    fi = pd.DataFrame(
        [
            {
                "match_id": m,
                "batting_team_id": 1,
                "total_runs": first_total[m] if isinstance(first_total, dict) else first_total,
            }
            for m in matches["match_id"]
        ]
    )
    cs = pd.DataFrame(cs_rows, columns=list(_cs("x", "2026-01-01").keys()))
    off = official or dv.load_official_verification(None, set(), {})
    return dv.build_date_check(
        matches, matches, COMPS, pd.DataFrame(ts, columns=list(_ts(1, "2026-01-01").keys())),
        fi, cs, None, off, CFG,
    )  # fmt: skip


def _row(df: pd.DataFrame, mid: int) -> pd.Series:
    return df[df["match_id"] == mid].iloc[0]


# ------------------------------------------------------------------ the four classes
def test_four_classes_synthetic():
    m = _matches(
        [
            (1, 10, 1, "2026-07-01", 1, 2),
            (2, 10, 2, "2026-07-03", 1, 2),
            (3, 10, 3, "2026-07-05", 1, 2),
            (4, 10, 4, "2026-07-07", 1, 2),
        ]
    )
    ts = [
        _ts(1, "2026-07-01"),  # timestamp agrees
        _ts(2, "2026-07-03"),  # timestamp agrees
        _ts(3, "2026-07-10"),  # timestamp 5 days off
        # match 4: no timestamps at all
    ]
    cs = [_cs("c1", "2026-07-01", total=151), _cs("c3", "2026-07-05", total=153)]
    out = _run(m, ts, cs, first_total={1: 151, 2: 152, 3: 153, 4: 154})
    assert _row(out, 1).date_class == dv.CONSISTENT
    assert _row(out, 2).date_class == dv.SINGLE
    assert _row(out, 3).date_class == dv.CONFLICT
    assert _row(out, 4).date_class == dv.UNVERIFIED
    assert not out["official_verified"].any()
    assert (out["official_status"] == "NOT_SUPPLIED").all()


def test_cricsheet_conflict_and_identity():
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2)])
    # identity confirmed (same first innings) but 5 days apart -> conflict
    out = _run(m, [_ts(1, "2026-07-01")], [_cs("c1", "2026-07-06")])
    assert _row(out, 1).cs_status == "CONFLICT" and _row(out, 1).date_class == dv.CONFLICT
    # same teams and date but a different first-innings total -> identity unconfirmed, no evidence
    out = _run(m, [_ts(1, "2026-07-01")], [_cs("c1", "2026-07-01", total=99)])
    assert _row(out, 1).cs_status == "IDENTITY_UNCONFIRMED"
    assert _row(out, 1).date_class == dv.SINGLE


def test_one_day_tolerance_and_two_day_conflict():
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2), (2, 10, 2, "2026-07-04", 1, 2)])
    out = _run(m, [_ts(1, "2026-06-30"), _ts(2, "2026-07-06")], [])
    assert _row(out, 1).ts_status == "AGREE"
    assert _row(out, 2).ts_status == "CONFLICT"
    assert _row(out, 1).ts_diff_first_days == -1


def test_placeholder_timestamps_not_informative():
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2)])
    out = _run(m, [_ts(1, "2026-07-01", nonmid=0)], [])
    r = _row(out, 1)
    assert r.ts_status == "NOT_INFORMATIVE" and not r.timestamp_informative
    assert r.date_class == dv.UNVERIFIED


def test_ordering_violation_is_conflict_and_internal_never_adds():
    m = _matches([(1, 10, 1, "2026-07-05", 1, 2), (2, 10, 2, "2026-07-03", 3, 4)])
    out = _run(m, [_ts(1, "2026-07-05"), _ts(2, "2026-07-03")], [_cs("c1", "2026-07-05")])
    assert not _row(out, 1).ordering_consistent
    assert _row(out, 1).date_class == dv.CONFLICT
    # clean ordering and clean season token with one source stays SINGLE (internal checks add nothing)
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2)])
    r = _row(_run(m, [_ts(1, "2026-07-01")], []), 1)
    assert r.ordering_consistent and r.season_token_status == "CONSISTENT"
    assert r.n_agreeing_sources == 1 and r.date_class == dv.SINGLE


def test_double_booking_and_season_token_conflicts():
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2), (2, 10, 2, "2026-07-01", 1, 3)])
    out = _run(m, [_ts(1, "2026-07-01"), _ts(2, "2026-07-01")], [])
    assert "double_booked_team_1" in _row(out, 1).double_booking
    assert _row(out, 1).date_class == dv.CONFLICT
    assert dv.season_token_status(
        "India in England T20I Series 2026", "2026", date(2027, 1, 3)
    ) == ("INCONSISTENT")
    assert dv.season_token_status("X 2025/26", "2025/26", date(2026, 1, 3)) == "CONSISTENT"
    assert dv.season_token_status("Something", "n/a", date(2026, 1, 3)) == "NOT_APPLICABLE"


def test_spacing_gap_flagged():
    m = _matches([(1, 10, 1, "2026-01-01", 1, 2), (2, 10, 2, "2026-07-01", 3, 4)])
    out = dv.ordering_checks(m, CFG).set_index("match_id")
    assert not out.loc[1, "ordering_consistent"] and "gap>" in out.loc[1, "ordering_detail"]


# ------------------------------------------------------------------ originals never modified
def test_originals_not_modified():
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2), (2, 10, 2, "2026-07-03", 1, 2)])
    before = m.copy(deep=True)
    h_before = tm.sha256_json(
        [[int(i), str(d)[:10]] for i, d in zip(m.match_id, m.match_date, strict=True)]
    )
    out = _run(m, [_ts(1, "2026-07-10"), _ts(2, "2026-07-03")], [_cs("c", "2026-07-20")])
    pd.testing.assert_frame_equal(m, before)
    h_after = tm.sha256_json(
        [[int(i), str(d)[:10]] for i, d in zip(m.match_id, m.match_date, strict=True)]
    )
    assert h_before == h_after
    # conflicting evidence never changes the reported original date
    assert list(out["original_match_date"]) == ["2026-07-01", "2026-07-03"]


def test_module_has_no_write_to_matches():
    src = (BACKEND / "app/phase5/date_verification.py").read_text(encoding="utf-8").lower()
    for bad in (
        "update matches",
        "insert into matches",
        "delete from matches",
        "to_sql",
        "write_p5",
    ):
        assert bad not in src


# ------------------------------------------------------------------ official verification loader
HEADER = ",".join(dv.OFFICIAL_COLUMNS)


def _csv(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "official.csv"
    p.write_text(HEADER + "\n" + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


ORIG = {1: date(2026, 7, 1), 2: date(2026, 7, 3), 3: date(2026, 7, 5)}


def test_template_files_are_header_only():
    for p in (
        CONFIG_DIR / "t20i_official_date_verification_template.csv",
        REPORTS_DIR / "phase5_t20i_official_verification_template.csv",
    ):
        assert p.read_text(encoding="utf-8").strip() == HEADER


def test_loader_only_complete_rows_are_official(tmp_path):
    p = _csv(
        tmp_path,
        [
            "1,2026-07-01,BCCI scorecard,Reviewer A,2026-11-20",
            "2,2026-07-03,,Reviewer A,2026-11-20",  # missing source -> incomplete
            "3,2026-07-06,ICC match centre,Reviewer B,2026-11-21",  # differs from original
        ],
    )
    res = dv.load_official_verification(p, set(ORIG), ORIG)
    assert list(res["official"]["match_id"]) == [1]
    assert [r["match_id"] for r in res["incomplete"]] == ["2"]
    assert list(res["differs"]["match_id"]) == [3]
    assert ORIG[3] == date(2026, 7, 5)  # original untouched


def test_loader_errors(tmp_path):
    with pytest.raises(dv.DateVerificationError):
        dv.load_official_verification(
            _csv(tmp_path, ["9,2026-07-01,s,v,2026-11-20"]), set(ORIG), ORIG
        )
    with pytest.raises(dv.DateVerificationError):
        dv.load_official_verification(
            _csv(tmp_path, ["1,07/01/2026,s,v,2026-11-20"]), set(ORIG), ORIG
        )
    with pytest.raises(dv.DateVerificationError):
        dv.load_official_verification(
            _csv(tmp_path, ["1,2026-07-01,s,v,2026-11-20", "1,2026-07-01,s,v,2026-11-20"]),
            set(ORIG),
            ORIG,
        )
    bad = tmp_path / "bad.csv"
    bad.write_text("match_id,date\n1,2026-07-01\n", encoding="utf-8")
    with pytest.raises(dv.DateVerificationError):
        dv.load_official_verification(bad, set(ORIG), ORIG)
    assert dv.load_official_verification(tmp_path / "missing.csv", set(ORIG), ORIG)[
        "official"
    ].empty


def test_official_row_marks_official_verified_but_keeps_evidence_class(tmp_path):
    m = _matches([(1, 10, 1, "2026-07-01", 1, 2), (2, 10, 2, "2026-07-03", 1, 2)])
    off = dv.load_official_verification(
        _csv(tmp_path, ["1,2026-07-01,src,who,2026-11-20", "2,2026-07-09,src,who,2026-11-20"]),
        {1, 2},
        {1: date(2026, 7, 1), 2: date(2026, 7, 3)},
    )
    out = _run(m, [], [], official=off)
    assert _row(out, 1).official_status == "OFFICIAL_VERIFIED" and _row(out, 1).official_verified
    assert _row(out, 1).date_class == dv.UNVERIFIED  # evidence class itself is unchanged
    assert (
        _row(out, 2).official_status == "OFFICIAL_DATE_DIFFERS"
        and not _row(out, 2).official_verified
    )
    assert _row(out, 2).original_match_date == "2026-07-03"


# ------------------------------------------------------------------ restricted TEST sets
def _check(rows: list[tuple]) -> pd.DataFrame:
    """rows: (match_id, date, class, official_status)."""
    return pd.DataFrame(
        [
            {"match_id": i, "original_match_date": d, "date_class": c, "official_status": o}
            for i, d, c, o in rows
        ]
    )


def _state(ids: list[int]) -> pd.DataFrame:
    rows = []
    for i in ids:
        for b in range(3):
            rows.append({"match_id": i, "striker_id": i * 10 + b, "bowler_id": 7})
    return pd.DataFrame(rows)


def test_primary_excludes_unverified_late_and_includes_official():
    check = _check(
        [
            (1, "2026-03-01", dv.CONSISTENT, "NOT_SUPPLIED"),  # early consistent -> in primary
            (2, "2026-03-02", dv.SINGLE, "NOT_SUPPLIED"),  # early single -> out
            (
                3,
                "2026-07-01",
                dv.CONSISTENT,
                "NOT_SUPPLIED",
            ),  # late consistent, not official -> out
            (4, "2026-07-02", dv.UNVERIFIED, "OFFICIAL_VERIFIED"),  # late official -> in
            (5, "2026-03-05", dv.CONFLICT, "NOT_SUPPLIED"),  # conflict -> out
            (6, "2026-07-09", dv.CONSISTENT, "OFFICIAL_DATE_DIFFERS"),  # date disputed -> out
        ]
    )
    mem = tm.build_membership(check, "2026-05-31", {1, 2, 3, 4, 5, 6})
    sel = lambda s: sorted(mem[(mem.set_name == s) & mem.member].match_id)  # noqa: E731
    assert sel(tm.PRIMARY) == [1, 4]
    assert sel(tm.STRICT) == [4]
    assert sel(tm.ALL) == [1, 2, 3, 4, 5, 6]


def test_strict_set_empty_without_official_rows():
    check = _check([(i, "2026-03-01", dv.CONSISTENT, "NOT_SUPPLIED") for i in (1, 2)])
    mem = tm.build_membership(check, "2026-05-31", {1, 2})
    assert not mem[(mem.set_name == tm.STRICT) & mem.member].any().any()


def test_membership_limited_to_state_matches_and_counts():
    check = _check(
        [
            (1, "2026-03-01", dv.CONSISTENT, "NOT_SUPPLIED"),
            (2, "2026-03-02", dv.CONSISTENT, "NOT_SUPPLIED"),
            (3, "2026-07-02", dv.CONSISTENT, "NOT_SUPPLIED"),
            (4, "2026-03-03", dv.UNVERIFIED, "NOT_SUPPLIED"),  # abandoned, not in state
        ]
    )
    mem = tm.build_membership(check, "2026-05-31", {1, 2, 3})
    assert 4 not in set(mem.match_id)
    state = _state([1, 2, 3])
    ct = {1: "IPL", 2: "IPL", 3: "T20I"}
    counts = tm.set_counts(mem, state, ct)
    assert counts[tm.PRIMARY]["matches"] == 2 and counts[tm.PRIMARY]["deliveries"] == 6
    assert counts[tm.ALL]["matches"] == 3 and counts[tm.ALL]["deliveries"] == 9
    assert counts[tm.ALL]["by_competition_type"]["T20I"]["matches"] == 1
    eff = tm.excluded_effect(mem, state, ct)
    assert eff["excluded_matches"] == 1 and eff["excluded_deliveries"] == 3
    assert eff["players_only_in_excluded_matches"] == 3  # strikers 30,31,32 (bowler 7 is shared)


def test_manifest_hash_detects_tampering():
    check = _check([(1, "2026-03-01", dv.CONSISTENT, "NOT_SUPPLIED")])
    mem = tm.build_membership(check, "2026-05-31", {1})
    man = tm.build_manifest(mem, check, _state([1]), {1: "IPL"}, "2026-05-31", {"x": 1})
    assert man["test_evaluated_in_phase5"] is False and tm.verify_manifest(man)
    man["sets"][tm.PRIMARY]["match_ids"].append(99)
    assert not tm.verify_manifest(man)


# ------------------------------------------------------------------ Cricsheet confinement
SCORING_DIRS = ("app/phase4", "app/phase5", "app/analytics")


def _scoring_files() -> list[Path]:
    files = []
    for d in SCORING_DIRS:
        files += sorted((BACKEND / d).rglob("*.py"))
    files.append(BACKEND / "app/services/pressure_service.py")
    return [f for f in files if f.name != "date_verification.py"]


def test_no_cricsheet_import_in_scoring_modules():
    offenders = []
    for f in _scoring_files():
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "cricsheet_index" in node.value:
                    names = [node.value]
            if any("cricsheet" in n.lower() for n in names):
                offenders.append(f"{f.relative_to(BACKEND)}:{node.lineno}")
    assert offenders == []


def test_only_date_verification_phase5_module_reads_cricsheet():
    for f in sorted((BACKEND / "app/phase5").glob("*.py")):
        text = f.read_text(encoding="utf-8").lower()
        if f.name == "date_verification.py":
            continue
        assert "cricsheet_auditor" not in text and "read_parquet" not in text, f.name


# ------------------------------------------------------------------ lock untouched
def test_outcome_columns_rejected():
    for col in ("out_batter_runs", "den_legal_inc", "post_innings_wickets", "residual_x"):
        with pytest.raises(OutcomeColumnError):
            check_columns(("match_id", col))
    check_columns(("match_id", "innings_number", "innings_ball_num", "striker_id", "bowler_id"))


def test_test_state_loader_selects_identity_columns_only(tmp_path):
    p = tmp_path / "x.duckdb"
    con = duckdb.connect(str(p))
    con.execute(
        "CREATE TABLE exp_pre_delivery_state(match_id INT, innings_number INT, innings_ball_num INT, "
        "striker_id INT, bowler_id INT, out_batter_runs INT, den_legal_inc INT, post_innings_wickets INT)"
    )
    con.execute("INSERT INTO exp_pre_delivery_state VALUES (1,1,1,5,6,4,1,3),(2,1,1,7,8,9,9,9)")
    con.execute("CREATE TABLE p4_match_period(match_id INT, period VARCHAR)")
    con.execute("INSERT INTO p4_match_period VALUES (1,'TEST'),(2,'TRAIN')")
    con.close()
    df = load_test_match_state_nonoutcome(p)
    assert list(df["match_id"]) == [1]
    assert not [c for c in df.columns if c.startswith(("out_", "den_", "post_innings_"))]


def test_lock_guard_detects_changes(tmp_path):
    lock = tmp_path / "lock.json"
    lock.write_text('[{"event": "OPEN"}]', encoding="utf-8")
    digest = file_sha256(lock)
    assert assert_phase4_lock_untouched(digest, lock) == digest
    lock.write_text('[{"event": "OPEN"}, {"event": "OPEN"}]', encoding="utf-8")
    with pytest.raises(LockGuardError):
        assert_phase4_lock_untouched(digest, lock)
    with pytest.raises(LockGuardError):
        assert_phase5_lock_not_opened(lock)
    assert assert_phase5_lock_not_opened(tmp_path / "absent.json") == 0


def test_phase4_and_phase5_lock_logs_untouched():
    prerun = Path("d:/Data/.agents/tasks/phase5_prerun_hashes.json")
    p4 = REPORTS_DIR / "phase4_lock_log.json"
    if not prerun.exists() or not p4.exists():
        pytest.skip("prerun hashes or lock log absent")
    expected = json.loads(prerun.read_text(encoding="utf-8"))["phase4_reports"][
        "d:/Data/backend/data/reports/phase4_lock_log.json"
    ].lower()
    assert_phase4_lock_untouched(expected)
    assert assert_phase5_lock_not_opened(PHASE5_LOCK_LOG) == 0


# ------------------------------------------------------------------ real data (independent recompute)
@pytest.mark.realdata
def test_real_late42_recomputed_from_raw_csvs():
    data = Path("d:/Data")
    rep = REPORTS_DIR / "phase5_t20i_date_verification.csv"
    if not (data / "matches.csv").exists() or not rep.exists():
        pytest.skip("raw CSVs or report absent")
    t20i_comps = {
        int(r["comp_id"]) for r in csv.DictReader((data / "competitions.csv").open(encoding="utf-8"))
        if r["match_format"] == "T20I"
    }  # fmt: skip
    late = {}
    with (data / "matches.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["comp_id"]) in t20i_comps and r["match_date"][:10] > "2026-05-31":
                late[int(r["match_id"])] = r["match_date"][:10]
    report = pd.read_csv(rep)
    assert len(late) == 42 and sorted(late) == sorted(report["match_id"])
    assert {int(r.match_id): r.original_match_date for r in report.itertuples()} == late
    # timestamp evidence for three matches recomputed from updated_ball_by_ball.csv
    pick = sorted(late)[:2] + [sorted(late)[-1]]
    firsts: dict[int, str] = {}
    with (data / "updated_ball_by_ball.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            mid = int(r["match_id"])
            t = r["delivery_ist_time"]
            if mid in pick and not t[11:19] == "00:00:00":
                firsts[mid] = min(firsts.get(mid, t), t)
    for mid in pick:
        diff = (date.fromisoformat(firsts[mid][:10]) - date.fromisoformat(late[mid])).days
        row = report[report.match_id == mid].iloc[0]
        assert row.ts_first_date == firsts[mid][:10]
        assert int(row.ts_diff_first_days) == diff
        assert row.ts_status == ("AGREE" if abs(diff) <= 1 else "CONFLICT")


@pytest.mark.realdata
def test_real_summary_states_nothing_official_verified():
    p = REPORTS_DIR / "phase5_t20i_date_verification.json"
    if not p.exists():
        pytest.skip("summary absent")
    s = json.loads(p.read_text(encoding="utf-8"))
    assert s["official_verified_late42"] == 0 and s["gate"]["passed"] is False
    assert "No match is official-verified" in s["statement"]
    assert s["guards"]["phase5_test_opened"] is False and s["guards"]["official_db_unchanged"]
    man = json.loads((REPORTS_DIR / "phase5_test_set_manifest.json").read_text(encoding="utf-8"))
    assert tm.verify_manifest(man) and man["test_evaluated_in_phase5"] is False
