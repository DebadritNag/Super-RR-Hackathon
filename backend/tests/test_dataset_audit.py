"""Tests for the Phase 1 audit functions, using small synthetic CSVs."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from app.data_pipeline import data_quality as dq
from app.data_pipeline.ball_by_ball_inspector import KEY, compare_ball_files
from app.data_pipeline.dataset_discovery import discover_datasets
from app.data_pipeline.schema_validator import compare_schema, describe_file, read_csv_header
from app.utils.paths import sql_quote


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    yield c
    c.close()


def test_compare_schema_missing_extra_reorder() -> None:
    r = compare_schema(["b", "a", "z"], ["a", "b", "c"])
    assert r["missing"] == ["c"]
    assert r["unexpected"] == ["z"]
    assert r["order_differs"] is True
    assert compare_schema(["a", "b"], ["a", "b"])["matches_exactly"] is True


def test_duplicate_rows_and_keys(tmp_path: Path, con) -> None:
    write(tmp_path / "t.csv", "id,v\n1,a\n1,a\n2,b\n2,c\n3,d\n")
    dq.register_csv_views(con, {"t": tmp_path / "t.csv"})
    assert dq.duplicate_rows(con, "t") == 1
    d = dq.duplicate_keys(con, "t", ["id"])
    assert d["duplicate_key_groups"] == 2
    assert d["rows_in_duplicate_groups"] == 4


def test_invalid_ids(tmp_path: Path, con) -> None:
    write(tmp_path / "t.csv", "id\n1\n\nabc\n-4\n0\n7\n")
    dq.register_csv_views(con, {"t": tmp_path / "t.csv"})
    r = dq.invalid_ids(con, "t", "id")
    assert r == {"column": "id", "null_or_empty": 1, "non_numeric": 1, "non_positive": 2}


def test_value_counts_and_date_range(tmp_path: Path, con) -> None:
    write(tmp_path / "t.csv", "c,d\nx,2022-01-05\nx,2023-02-01\ny,notadate\n")
    dq.register_csv_views(con, {"t": tmp_path / "t.csv"})
    assert dq.value_counts(con, "t", "c") == [("x", 2), ("y", 1)]
    r = dq.date_range(con, "t", "d")
    assert str(r["min"]) == "2022-01-05" and str(r["max"]) == "2023-02-01"
    assert r["unparseable"] == 1


def test_fk_orphans(tmp_path: Path, con) -> None:
    write(tmp_path / "p.csv", "id\n1\n2\n")
    write(tmp_path / "c.csv", "pid\n1\n3\n3\n\n")
    dq.register_csv_views(con, {"p": tmp_path / "p.csv", "c": tmp_path / "c.csv"})
    r = dq.fk_orphans(con, "c", ["pid"], "p", ["id"])
    assert r["orphan_rows"] == 2
    assert r["distinct_orphan_keys"] == 1
    assert r["child_rows_checked"] == 3  # the empty value is not checked


def test_team_id_uniqueness_detects_shared_id(tmp_path: Path, con) -> None:
    write(tmp_path / "teams.csv", "comp_id,team_id,team_name\n1,5,India\n2,5,Pakistan\n3,6,India\n")
    write(tmp_path / "mapping.csv", "comp_id,team_id,team_name\n1,5,India\n")
    dq.register_csv_views(
        con, {"teams": tmp_path / "teams.csv", "mapping": tmp_path / "mapping.csv"}
    )
    r = dq.team_id_uniqueness(con)
    assert r["teams"]["team_ids_with_multiple_names"] == 1
    assert r["team_id_is_globally_unique_key"] is False
    assert r["team_names_with_multiple_ids_in_teams"] == 1


def test_discover_datasets_flags_missing_and_extras(tmp_path: Path) -> None:
    write(tmp_path / "competitions.csv", "comp_id\n1\n")
    write(tmp_path / "ipl squad.csv", "a\n1\n")
    write(tmp_path / "updated_ball_by_ball.csv", "a\n1\n")
    write(tmp_path / "surprise.csv", "a\n1\n")
    (tmp_path / "ipl_male_json").mkdir()
    write(tmp_path / "ipl_male_json" / "1.json", "{}")
    write(tmp_path / "ipl_male_json" / "readme.txt", "x")
    res = discover_datasets(tmp_path, tmp_path)
    assert "competitions.csv" in res.found and "ipl squad.csv" in res.found
    assert "matches.csv" in res.missing
    assert "surprise.csv" in res.extras
    assert "updated_ball_by_ball.csv" in res.supplementary
    assert res.json_dirs["ipl_male_json"]["json_files"] == 1
    assert res.json_dirs["ipl_male_json"]["txt_files"] == ["readme.txt"]
    assert "t20s_male_json" in res.missing_json_dirs


def _ball_csv(path: Path, rows: list[tuple]) -> Path:
    header = ",".join(KEY + ["extras1_runs", "striker_name"])
    body = "\n".join(",".join(str(x) for x in r) for r in rows)
    return write(path, header + "\n" + body + "\n")


def test_compare_ball_files_identical_changed_extra_row(tmp_path: Path, con) -> None:
    base = [(1, 1, 1, 1, 1, 6, "A"), (1, 1, 2, 1, 2, 6, "A")]
    a = _ball_csv(tmp_path / "a.csv", base)
    same = _ball_csv(tmp_path / "same.csv", base)
    changed = _ball_csv(tmp_path / "chg.csv", [base[0], (1, 1, 2, 1, 2, 0, "A")])
    extra = _ball_csv(tmp_path / "extra.csv", base + [(1, 1, 3, 1, 3, 6, "A")])
    dq.register_csv_views(con, {"a": a, "same": same, "chg": changed, "extra": extra})
    assert compare_ball_files(con, "a", "same")["verdict"] == "IDENTICAL"
    r = compare_ball_files(con, "a", "chg")
    assert r["verdict"] == "SAME_ROWS_SAME_KEYS_VALUES_DIFFER"
    assert r["differing_rows_per_column"] == {"extras1_runs": 1}
    r = compare_ball_files(con, "a", "extra")
    assert r["verdict"] == "B_IS_SUPERSET_OF_A" and r["only_in_b"] == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Match Abandoned", "ABANDONED"),
        ("No Result", "NO_RESULT"),
        ("India Won by 5 runs", "COMPLETED"),
        ("Match Tied", "TIED"),
        ("India won the Super Over(Match Tied)", "TIED_DECIDED_BY_TIEBREAK"),
        ("???", "UNKNOWN"),
        ("", "UNKNOWN"),
    ],
)
def test_classify_result(text: str, expected: str) -> None:
    assert dq.classify_result(text) == expected


def test_reconcile_matches_lists_every_match_without_balls(tmp_path: Path, con) -> None:
    write(
        tmp_path / "matches.csv",
        "match_id,comp_id,match_date,stage,home_team,away_team,"
        "result,win_team_id,knock_out,first_inn_revised_overs,second_inn_revised_overs,"
        "revised_target\n1,9,2024-01-01,League,A,B,A Won by 1 run,1,0,,,\n"
        "2,9,2024-01-02,League,A,B,Match Abandoned,,0,,,\n"
        "3,9,2024-01-03,League,A,B,No Result,,0,,,\n"
        "4,9,2024-01-04,League,A,B,weird text,,0,,,\n",
    )
    write(tmp_path / "competitions.csv", "comp_id,comp_name,match_format,season\n9,X,T20I,2024\n")
    write(tmp_path / "bbb.csv", "match_id\n1\n1\n")
    write(tmp_path / "pe.csv", "match_id,is_played\n2,true\n2,false\n")
    dq.register_csv_views(
        con,
        {
            "matches": tmp_path / "matches.csv",
            "competitions": tmp_path / "competitions.csv",
            "bbb": tmp_path / "bbb.csv",
            "playing_eleven": tmp_path / "pe.csv",
        },
    )
    df = dq.reconcile_matches(con)
    assert list(df["match_id"]) == ["2", "3", "4"]
    assert dict(zip(df["match_id"], df["status"], strict=True)) == {
        "2": "ABANDONED",
        "3": "NO_RESULT",
        "4": "UNKNOWN",
    }
    assert int(df.loc[df["match_id"] == "2", "played_rows"].iloc[0]) == 1


def test_path_with_space_and_quote(tmp_path: Path, con) -> None:
    p = write(tmp_path / "my file's data.csv", "a,b\n1,\n2,x\n")
    assert read_csv_header(p) == ["a", "b"]
    d = describe_file(con, p)
    assert d["rows"] == 2
    assert d["column_stats"]["b"]["null_count"] == 1
    assert sql_quote("it's") == "'it''s'"


def test_ipl_overlap_report_shapes() -> None:
    from app.data_pipeline.cricsheet_auditor import ipl_overlap_with_csv

    idx = pd.DataFrame(
        {
            "directory": ["ipl_male_json"],
            "match_id": ["10"],
            "date": ["2024-04-01"],
            "teams_key": ["a|b"],
            "team_a": ["A"],
            "team_b": ["B"],
            "event_name": ["IPL"],
        }
    )
    matches = pd.DataFrame(
        {
            "match_id": ["1", "2"],
            "comp_id": ["5", "5"],
            "match_date": ["2024-04-01", "2024-04-02"],
            "home_team": ["A", "A"],
            "away_team": ["B", "B"],
        }
    )
    comps = pd.DataFrame({"comp_id": ["5"], "comp_name": ["IPL 2024"]})
    r = ipl_overlap_with_csv(idx, matches, comps)
    assert r["matched_keys"] == 1 and r["csv_ipl_unmatched"] == 1


@pytest.mark.skipif(not Path("D:/Data/competitions.csv").exists(), reason="real data not present")
def test_real_competitions_row_count_smoke() -> None:
    c = duckdb.connect()
    n = c.execute(
        "SELECT count(*) FROM read_csv('D:/Data/competitions.csv', header=true)"
    ).fetchone()[0]
    assert n == 141
