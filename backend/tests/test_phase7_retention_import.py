"""Retention importer tests. ALL FIXTURES ARE SYNTHETIC (built in tmp_path, never saved in data/).

No official retention list exists yet; none of the names below is a claim about a real player.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import duckdb
import pytest
from openpyxl import Workbook

from app.data_pipeline import retention_importer as ri
from app.data_pipeline.retention_availability import COLUMNS, build_availability
from app.phase4.store import OFFICIAL_DB
from app.phase6.store import StoreError

RR, CSK, MI = "Rajasthan Royals", "Chennai Super Kings", "Mumbai Indians"
HEADER = ["Player Name", "Player ID", "Team", "Status", "Source", "Notes"]


def make_ref(aliases: dict | None = None) -> ri.Reference:
    ref = ri.Reference()
    ref.add_player(1, "Alpha One")
    ref.add_player(2, "Beta Two")
    ref.add_player(3, "Gamma Same")
    ref.add_player(4, "Gamma Same")
    ref.add_player(5, "Dëlta Five", ["D Five"])
    ref.add_player(6, "Epsilon Six")
    ref.add_player(7, "Zeta Seven")
    ref.add_player(8, "Eta Eight")
    ref.player_teams = {1: {ri.norm_key(RR)}, 2: {ri.norm_key(CSK)}, 5: {ri.norm_key(MI)},
                        6: {ri.norm_key(MI)}, 8: {ri.norm_key(RR)}}  # fmt: skip
    ref.franchises = {ri.norm_key(t): t for t in (RR, CSK, MI)}
    ref.aliases = aliases or {}
    return ref


def write_csv(path: Path, rows: list[list[str]], header=HEADER) -> Path:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def write_xlsx(path: Path, rows: list[list[str]], header=HEADER) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


ROWS = [
    ["alpha  one", "", "rajasthan royals", "retained", "SYNTHETIC doc", ""],
    ["Beta Two", "", CSK, "", "SYNTHETIC doc", "blank status"],
    ["Gamma Same", "", RR, "released", "SYNTHETIC doc", ""],
    ["Nobody Known", "", RR, "released", "SYNTHETIC doc", ""],
    ["Delta Five", "", MI, "auction available", "SYNTHETIC doc", "accent-insensitive"],
    ["Epsilon Six", "", MI, "maybe", "SYNTHETIC doc", "unrecognised status"],
    ["Zeta Seven", "", RR, "traded", "SYNTHETIC doc", "unique name but no team history"],
]


def run(tmp_path: Path, path: Path, **kw):
    args = dict(snapshot_date="2026-11-17", source="SYNTHETIC doc", verification="UNVERIFIED",
                store=tmp_path / "store.duckdb", raw_dir=tmp_path / "raw", reference=make_ref())  # fmt: skip
    args.update(kw)
    return ri.import_file(path, **args)


def by_row(res):
    return {r["raw_player_name"]: r for r in res["rows"]}


@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_csv_and_xlsx_give_identical_results(tmp_path, fmt):
    f = (write_csv if fmt == "csv" else write_xlsx)(tmp_path / f"list.{fmt}", ROWS)
    res = run(tmp_path, f)
    rows = by_row(res)
    assert res["status"] == "IMPORTED" and res["n_rows"] == 7
    assert rows["alpha one"]["status"] == "RETAINED"
    assert rows["alpha one"]["mapping_status"] == "MAPPED"
    assert rows["alpha one"]["team"] == RR  # spelling normalised to the franchise name
    assert (
        rows["Delta Five"]["player_id"] == 5 and rows["Delta Five"]["status"] == "AUCTION_AVAILABLE"
    )


def test_blank_status_defaults_to_unknown_and_bad_status_is_flagged_not_guessed(tmp_path):
    res = run(tmp_path, write_csv(tmp_path / "l.csv", ROWS))
    rows = by_row(res)
    assert rows["Beta Two"]["status"] == "UNKNOWN" and rows["Beta Two"]["flags"] == []
    assert rows["Epsilon Six"]["status"] == "UNKNOWN"
    assert "STATUS_UNRECOGNISED" in rows["Epsilon Six"]["flags"]
    assert set(ri.STATUSES) == {"RETAINED", "RELEASED", "TRADED", "AUCTION_AVAILABLE", "UNKNOWN"}


def test_ambiguous_and_unmatched_rows_go_to_the_review_queue_never_guessed(tmp_path):
    res = run(tmp_path, write_csv(tmp_path / "l.csv", ROWS))
    rows = by_row(res)
    g = rows["Gamma Same"]
    assert g["mapping_status"] == "AMBIGUOUS" and g["player_id"] is None
    assert [c["player_id"] for c in g["candidates"]] == [3, 4]
    n = rows["Nobody Known"]
    assert n["mapping_status"] == "UNMATCHED" and n["player_id"] is None
    z = rows["Zeta Seven"]  # unique name, no history with the stated team: confirmation needed
    assert z["mapping_status"] == "AMBIGUOUS" and z["review_reason"].startswith("NAME_UNIQUE_TEAM")
    queue = ri.list_review(tmp_path / "store.duckdb")
    assert {q["raw_player_name"] for q in queue} == {"Gamma Same", "Nobody Known", "Zeta Seven"}
    assert all(q["state"] == "OPEN" for q in queue)
    assert ri.export_review_csv(tmp_path / "store.duckdb", tmp_path / "q.csv") == 3
    assert "Gamma Same" in (tmp_path / "q.csv").read_text(encoding="utf-8")


def test_player_id_is_matched_first_and_a_name_mismatch_is_not_accepted(tmp_path):
    f = write_csv(tmp_path / "l.csv", [
        ["Someone Else", "1", RR, "retained", "s", ""],      # id exists, name differs
        ["", "2", CSK, "released", "s", ""],                  # id only
        ["Gamma Same", "3", RR, "released", "s", ""],         # id resolves the shared name
        ["Alpha One", "999", RR, "retained", "s", ""],        # id not found: no fallback to name
        ["Alpha One", "abc", RR, "retained", "s", ""],        # invalid id
    ])  # fmt: skip
    rows = run(tmp_path, f)["rows"]
    assert [r["mapping_status"] for r in rows] == [
        "AMBIGUOUS",
        "MAPPED",
        "MAPPED",
        "UNMATCHED",
        "UNMATCHED",
    ]
    assert rows[0]["review_reason"] == "ID_NAME_MISMATCH" and rows[0]["player_id"] is None
    assert rows[1]["player_id"] == 2 and rows[1]["match_method"] == "PLAYER_ID"
    assert rows[2]["player_id"] == 3
    assert rows[3]["review_reason"] == "ID_NOT_FOUND" and rows[3]["player_id"] is None
    assert rows[4]["review_reason"] == "ID_INVALID"


def test_alias_is_used_only_with_evidence_and_logged_on_the_row(tmp_path):
    f = write_csv(tmp_path / "l.csv", [["Al One", "", RR, "retained", "s", ""]])
    ref = make_ref({"al one": [(1, "SYNTHETIC: club sheet lists Al One as Alpha One")]})
    res = run(tmp_path, f, reference=ref)
    r = res["rows"][0]
    assert r["mapping_status"] == "MAPPED" and r["match_method"] == "ALIAS"
    assert "SYNTHETIC" in r["alias_evidence"]
    # an alias row with no evidence is ignored at load time
    a = tmp_path / "aliases.csv"
    a.write_text("alias,player_id,evidence\nAl One,1,\n", encoding="utf-8")
    assert ri.load_aliases(a) == {}
    res2 = run(tmp_path, f, reference=make_ref(ri.load_aliases(a)), dry_run=True)
    assert res2["rows"][0]["mapping_status"] == "UNMATCHED"


def test_missing_columns_bad_extension_and_bad_parameters_are_rejected(tmp_path):
    bad = write_csv(tmp_path / "bad.csv", [["x"]], header=["colour"])
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, bad)
    txt = tmp_path / "l.txt"
    txt.write_text("a", encoding="utf-8")
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, txt)
    ok = write_csv(tmp_path / "ok.csv", ROWS)
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, ok, verification="MAYBE")
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, ok, snapshot_date="17/11/2026")
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, ok, authoritative=True, verification="SINGLE_SOURCE")
    with pytest.raises(ri.RetentionImportError):
        run(tmp_path, tmp_path / "missing.csv")


def test_duplicates_and_conflicting_statuses_are_kept_side_by_side_and_flagged(tmp_path):
    f = write_csv(tmp_path / "l.csv", [
        ["Alpha One", "", RR, "retained", "s", ""],
        ["Alpha One", "", RR, "released", "s", ""],
        ["Beta Two", "", CSK, "retained", "s", ""],
        ["Beta Two", "", CSK, "retained", "s", ""],
    ])  # fmt: skip
    rows = run(tmp_path, f)["rows"]
    assert all("CONFLICTING_STATUS" in r["flags"] for r in rows[:2])
    assert all("DUPLICATE_ROW" in r["flags"] for r in rows[2:])
    assert len(rows) == 4


def test_released_traded_unknown_and_absent_are_never_confirmed_available(tmp_path):
    f = write_csv(tmp_path / "l.csv", [
        ["Alpha One", "", RR, "released", "s", ""],
        ["Beta Two", "", CSK, "traded", "s", ""],
        ["Epsilon Six", "", MI, "unknown", "s", ""],
        ["Delta Five", "", MI, "auction_available", "s", ""],
    ])  # fmt: skip
    # authoritative: only the explicit AUCTION_AVAILABLE row is confirmed
    res = run(tmp_path, f, verification="OFFICIAL_VERIFIED", authoritative=True)
    conf = {r["raw_player_name"]: ri.is_confirmed_available(r, True) for r in res["rows"]}
    assert conf == {"Alpha One": False, "Beta Two": False, "Epsilon Six": False, "Delta Five": True}
    assert res["n_confirmed_available"] == 1
    # not authoritative: nothing is confirmed
    res2 = run(tmp_path, f, dry_run=True)
    assert res2["n_confirmed_available"] == 0
    # no source on the row and none supplied: not confirmed
    nosrc = write_csv(tmp_path / "n.csv", [["Delta Five", "", MI, "auction_available", "", ""]])
    res3 = run(tmp_path, nosrc, source="", verification="OFFICIAL_VERIFIED", authoritative=True,
               dry_run=True)  # fmt: skip
    assert res3["n_confirmed_available"] == 0 and "NO_SOURCE" in res3["rows"][0]["flags"]


def test_reimport_of_the_same_file_changes_nothing(tmp_path):
    f = write_csv(tmp_path / "l.csv", ROWS)
    first = run(tmp_path, f)
    store = tmp_path / "store.duckdb"

    def snapshot():
        con = duckdb.connect(str(store), read_only=True)
        try:
            return {t: con.execute(f"SELECT * FROM {t} ORDER BY 1,2").fetchall()
                    for t in ("p7_retention_imports", "p7_retention_rows", "p7_retention_review")}  # fmt: skip
        finally:
            con.close()

    before = snapshot()
    second = run(tmp_path, f)
    assert first["status"] == "IMPORTED" and second["status"] == "ALREADY_IMPORTED"
    assert second["changed"] is False and second["import_id"] == first["import_id"]
    assert snapshot() == before
    manifest = json.loads((tmp_path / "raw" / "import_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1 and manifest[0]["sha256"] == first["file_sha256"]
    assert len(list((tmp_path / "raw").glob("*_l.csv"))) == 1


def test_original_file_is_preserved_byte_for_byte_with_its_sha256(tmp_path):
    f = write_xlsx(tmp_path / "l.xlsx", ROWS)
    res = run(tmp_path, f)
    stored = Path(res["stored_path"])
    assert stored.read_bytes() == f.read_bytes()
    assert hashlib.sha256(stored.read_bytes()).hexdigest() == res["file_sha256"]
    assert stored.parent == tmp_path / "raw"


def test_dry_run_writes_nothing(tmp_path):
    f = write_csv(tmp_path / "l.csv", ROWS)
    res = run(tmp_path, f, dry_run=True)
    assert res["status"] == "DRY_RUN" and res["changed"] is False and len(res["rows"]) == 7
    assert not (tmp_path / "store.duckdb").exists()
    assert not (tmp_path / "raw").exists()


def test_a_failure_inside_the_transaction_rolls_back_everything(tmp_path, monkeypatch):
    f = write_csv(tmp_path / "l.csv", ROWS)
    store = tmp_path / "store.duckdb"
    run(tmp_path, write_csv(tmp_path / "first.csv", [["Alpha One", "", RR, "retained", "s", ""]]))
    calls = {"n": 0}
    real = json.dumps

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 5:
            raise RuntimeError("boom")
        return real(*a, **k)

    monkeypatch.setattr(ri.json, "dumps", flaky)
    with pytest.raises(RuntimeError):
        run(tmp_path, f)
    monkeypatch.undo()
    con = duckdb.connect(str(store), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM p7_retention_imports").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM p7_retention_rows").fetchone()[0] == 1
    finally:
        con.close()
    assert not list((tmp_path / "raw").glob("*_l.csv"))  # the copy was removed too


def test_manual_resolution_records_resolver_evidence_and_timestamp(tmp_path):
    run(tmp_path, write_csv(tmp_path / "l.csv", ROWS))
    store, ref = tmp_path / "store.duckdb", make_ref()
    queue = {q["raw_player_name"]: q for q in ri.list_review(store)}
    rid = queue["Gamma Same"]["review_id"]
    with pytest.raises(ri.RetentionImportError):  # evidence is mandatory
        ri.resolve_review(store, rid, resolver="Ana", evidence=" ", player_id=3, reference=ref)
    with pytest.raises(ri.RetentionImportError):  # id must exist in the official table
        ri.resolve_review(store, rid, resolver="Ana", evidence="e", player_id=99, reference=ref)
    out = ri.resolve_review(store, rid, resolver="Ana", evidence="SYNTHETIC scorecard check",
                            player_id=3, reference=ref)  # fmt: skip
    assert out["state"] == "RESOLVED"
    with pytest.raises(ri.RetentionImportError):  # cannot resolve twice
        ri.resolve_review(store, rid, resolver="Bo", evidence="e", player_id=4, reference=ref)
    done = [q for q in ri.list_review(store, "RESOLVED")]
    assert (
        done[0]["resolver"] == "Ana"
        and done[0]["resolved_at"]
        and done[0]["resolved_player_id"] == 3
    )
    con = duckdb.connect(str(store), read_only=True)
    try:
        row = con.execute(
            "SELECT player_id, mapping_status, match_method FROM p7_retention_rows "
            "WHERE raw_player_name='Gamma Same'"
        ).fetchone()
        log = con.execute(
            "SELECT action, resolver, evidence FROM p7_retention_resolution_log"
        ).fetchall()
    finally:
        con.close()
    assert row == (3, "RESOLVED_MANUAL", "MANUAL")
    assert log == [("RESOLVED", "Ana", "SYNTHETIC scorecard check")]
    # dismissal leaves the row unresolved
    nid = queue["Nobody Known"]["review_id"]
    ri.resolve_review(store, nid, resolver="Ana", evidence="not a squad player", dismiss=True)
    assert nid not in {q["review_id"] for q in ri.list_review(store)}


def test_historical_records_are_unchanged_by_an_import(tmp_path):
    """A stand-in historical table in the same store and a stand-in source file are untouched."""
    store = tmp_path / "store.duckdb"
    con = duckdb.connect(str(store))
    con.execute(
        "CREATE TABLE p4_history_standin AS SELECT range AS i, range * 2 AS v FROM range(500)"
    )
    con.close()
    hist_csv = tmp_path / "history.csv"
    hist_csv.write_text("a,b\n1,2\n", encoding="utf-8")

    def state():
        c = duckdb.connect(str(store), read_only=True)
        try:
            n, h = c.execute("SELECT count(*), sum(hash(i, v)) FROM p4_history_standin").fetchone()
        finally:
            c.close()
        return n, h, hashlib.sha256(hist_csv.read_bytes()).hexdigest()

    before = state()
    run(tmp_path, write_csv(tmp_path / "l.csv", ROWS))
    assert state() == before
    con = duckdb.connect(str(store), read_only=True)
    names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    con.close()
    assert {n for n in names if n != "p4_history_standin"} == set(ri.TABLES)


def test_the_official_database_is_refused_as_a_store(tmp_path):
    f = write_csv(tmp_path / "l.csv", ROWS)
    with pytest.raises(StoreError):
        run(tmp_path, f, store=OFFICIAL_DB)


@pytest.mark.skipif(not Path(OFFICIAL_DB).is_file(), reason="official database not present")
def test_real_reference_loads_read_only_and_has_ten_franchises():
    before = Path(OFFICIAL_DB).stat()
    ref = ri.load_reference()
    assert len(ref.names) == 1217 and len(ref.franchises) == 10
    assert Path(OFFICIAL_DB).stat().st_mtime_ns == before.st_mtime_ns


# ------------------------------------------------------------------ availability outputs
def write_profiles(d: Path) -> None:
    people = {1: "Alpha One", 2: "Beta Two", 3: "Gamma Same", 5: "Dëlta Five", 6: "Epsilon Six",
              7: "Zeta Seven", 8: "Eta Eight"}  # fmt: skip
    with open(d / "descriptive_batter_profiles.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["player_id", "player_name", "format", "matches_played", "balls_faced"])
        for p, n in people.items():
            w.writerow([p, n, "IPL", 10, 100 + p])
    with open(d / "descriptive_bowler_profiles.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["player_id", "player_name", "format", "matches_played", "legal_balls"])
        w.writerow([2, "Beta Two", "IPL", 8, 90])


def test_availability_excludes_retained_and_never_invents_available(tmp_path):
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    f = write_csv(tmp_path / "l.csv", [
        ["Alpha One", "", RR, "retained", "SYNTHETIC doc", ""],
        ["Beta Two", "", CSK, "released", "SYNTHETIC doc", ""],
        ["Delta Five", "", MI, "auction_available", "SYNTHETIC doc", ""],
        ["Eta Eight", "", RR, "traded", "SYNTHETIC doc", ""],
        ["Gamma Same", "", RR, "retained", "SYNTHETIC doc", ""],   # ambiguous: unresolved
    ])  # fmt: skip
    run(tmp_path, f, verification="OFFICIAL_VERIFIED", authoritative=True)
    out = tmp_path / "out"
    m = build_availability(tmp_path / "store.duckdb", out, prof)
    assert m["state"] == "LIST_IMPORTED" and m["retained_excluded"] == 1
    assert m["unresolved_rows_in_list"] == 1 and "unresolved" in m["unresolved_warning"]
    rows = list(csv.DictReader(open(out / "candidate_availability.csv", encoding="utf-8")))
    names = [r["player_name"] for r in rows]
    assert "Alpha One" not in names  # retained player excluded from the candidate output
    assert names == sorted(names, key=str.casefold)  # name order only, no ranking
    st = {r["player_name"]: r for r in rows}
    assert st["Dëlta Five"]["availability_status"] == "AUCTION_AVAILABLE"
    assert st["Dëlta Five"]["confirmed_available"] == "True"
    for n in ("Beta Two", "Eta Eight"):  # released / traded: not available
        assert st[n]["confirmed_available"] == "False"
    for n in ("Epsilon Six", "Zeta Seven", "Gamma Same"):  # absent or unresolved: UNKNOWN
        assert st[n]["availability_status"] == "UNKNOWN" and st[n]["confirmed_available"] == "False"
    assert (
        st["Beta Two"]["side"] == "batter+bowler" and st["Beta Two"]["legal_balls_bowled"] == "90"
    )
    assert [c for c in rows[0]] == list(COLUMNS)
    assert not {"score", "rank", "rating"} & set(COLUMNS)


def test_availability_marks_conflicts_and_needs_authority_for_confirmation(tmp_path):
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    f = write_csv(tmp_path / "l.csv", [
        ["Alpha One", "", RR, "retained", "s", ""],
        ["Alpha One", "", RR, "auction_available", "s", ""],
        ["Delta Five", "", MI, "auction_available", "s", ""],
    ])  # fmt: skip
    run(tmp_path, f)  # UNVERIFIED, not authoritative
    m = build_availability(tmp_path / "store.duckdb", tmp_path / "o", prof)
    rows = {
        r["player_name"]: r
        for r in csv.DictReader(
            open(tmp_path / "o" / "candidate_availability.csv", encoding="utf-8")
        )
    }
    assert rows["Alpha One"]["availability_status"] == "CONFLICT"
    assert rows["Alpha One"]["confirmed_available"] == "False"
    assert rows["Dëlta Five"]["confirmed_available"] == "False"
    assert m["confirmed_available"] == 0


def test_availability_without_a_list_is_header_only_and_says_so(tmp_path):
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    m = build_availability(tmp_path / "absent.duckdb", tmp_path / "o", prof)
    assert m["state"] == "NO_RETENTION_FILE_YET" and m["list_received"] is False and m["rows"] == 0
    lines = (tmp_path / "o" / "candidate_availability.csv").read_text(encoding="utf-8").splitlines()
    assert lines == [",".join(COLUMNS)]
    assert not (tmp_path / "absent.duckdb").exists()  # nothing was created


def test_later_snapshot_supersedes_the_earlier_one(tmp_path):
    prof = tmp_path / "prof"
    prof.mkdir()
    write_profiles(prof)
    run(tmp_path, write_csv(tmp_path / "a.csv", [["Alpha One", "", RR, "retained", "s", ""]]),
        snapshot_date="2026-11-17")  # fmt: skip
    run(tmp_path, write_csv(tmp_path / "b.csv", [["Alpha One", "", RR, "released", "s", ""]]),
        snapshot_date="2026-11-20")  # fmt: skip
    build_availability(tmp_path / "store.duckdb", tmp_path / "o", prof)
    rows = {
        r["player_name"]: r
        for r in csv.DictReader(
            open(tmp_path / "o" / "candidate_availability.csv", encoding="utf-8")
        )
    }
    assert rows["Alpha One"]["availability_status"] == "RELEASED"
