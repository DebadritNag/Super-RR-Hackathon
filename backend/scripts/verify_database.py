"""Independent re-verification of the ingested DuckDB against the source CSV files.

The CSVs are read with the stdlib `csv` module and hashed with `hashlib`; DuckDB is opened
read-only and only queried. Prints PASS/FAIL per check and exits 1 if any check fails.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings  # noqa: E402

UPDATED = "updated_ball_by_ball.csv"
ORIGINAL = "ball_by_ball.csv"
SKIPPED = [
    "matches 2026.csv",
    "batting_stats2026.csv",
    "bowling_stats2026.csv",
    "fielding_stats2026.csv",
]

RESULTS: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    RESULTS.append(("PASS" if ok else "FAIL", name, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--data-root", type=Path, default=None)
    args = ap.parse_args()
    settings = get_settings()
    root = args.data_root or settings.data_root
    db_path = args.db or settings.duckdb_path
    con = duckdb.connect(str(db_path), read_only=True)

    def q1(sql: str, params: list | None = None):
        return con.execute(sql, params or []).fetchone()[0]

    # 1. lineage + hashes ---------------------------------------------------------------------
    run = q1("SELECT max(run_id) FROM dataset_lineage")
    record("lineage_exists", run is not None, f"latest load run {run}")
    lineage = {
        r[0]: r
        for r in con.execute(
            "SELECT file_name, sha256, row_count, role, load_status FROM dataset_lineage WHERE run_id = ?",
            [run],
        ).fetchall()
    }
    status = q1("SELECT status FROM ingestion_runs WHERE run_id = ?", [run])
    record("last_load_run_status_SUCCESS", status == "SUCCESS", f"status={status}")
    for name, (_, h, rows, role, load_status) in sorted(lineage.items()):
        path = root / name
        if h is None:
            record(f"hash_{name}", not path.exists(), "file absent at load time")
            continue
        record(f"hash_{name}", sha256(path) == h, f"role={role} status={load_status}")
    for name in SKIPPED:
        if name in lineage:
            record(
                f"skipped_{name}",
                lineage[name][3] == "SKIPPED_BY_DECISION"
                and lineage[name][4] == "SKIPPED_BY_DECISION",
                "recorded with hash/row count, no table loaded",
            )

    # 2. row counts via stdlib csv ---------------------------------------------------------------
    data: dict[str, list[dict[str, str]]] = {}
    for name in (
        "competitions.csv",
        "teams.csv",
        "matches.csv",
        "playing_eleven.csv",
        "competition_team_player_mapping.csv",
        UPDATED,
        ORIGINAL,
    ):
        data[name] = read_rows(root / name)[1]
    counts = {
        "competitions": ("competitions.csv", None),
        "competition_teams": ("teams.csv", None),
        "matches": ("matches.csv", None),
        "match_squads": ("playing_eleven.csv", None),
        "player_competition_mapping": ("competition_team_player_mapping.csv", None),
        "deliveries": (UPDATED, None),
        "raw_ball_by_ball_updated": (UPDATED, None),
        "raw_ball_by_ball": (ORIGINAL, None),
        "match_reconciliation": ("matches.csv", None),
    }
    for table, (fname, _) in counts.items():
        n_db = q1(f"SELECT count(*) FROM {table}")
        record(
            f"rowcount_{table}",
            n_db == len(data[fname]),
            f"db={n_db} csv={len(data[fname])} ({fname})",
        )
    teams_distinct = len({r["team_id"] for r in data["teams.csv"]})
    record(
        "rowcount_teams",
        q1("SELECT count(*) FROM teams") == teams_distinct,
        f"distinct team_id in csv={teams_distinct}",
    )

    # 3. delivery keys, order and provenance -----------------------------------------------------
    upd = data[UPDATED]
    keys_csv = [(int(r["match_id"]), int(r["innings"]), int(r["innings_ball_num"])) for r in upd]
    record(
        "deliveries_keys_unique_in_csv",
        len(set(keys_csv)) == len(keys_csv),
        f"{len(keys_csv)} rows",
    )
    db_keys = {
        (r[0], r[1], r[2]): r[3]
        for r in con.execute(
            "SELECT match_id, innings_number, innings_ball_num, source_row_no FROM deliveries"
        ).fetchall()
    }
    record("deliveries_key_set_equals_csv", set(db_keys) == set(keys_csv), f"db={len(db_keys)}")
    order_ok = all(db_keys.get(k) == i for i, k in enumerate(keys_csv, start=1))
    record(
        "deliveries_source_row_no_matches_csv_order",
        order_ok,
        "row i of the CSV has source_row_no i",
    )
    raw_ok = con.execute(
        "SELECT count(*) FROM raw_ball_by_ball_updated WHERE source_file <> ? OR source_row_no IS NULL",
        [UPDATED],
    ).fetchone()[0]
    record("raw_updated_provenance", raw_ok == 0, "source_file/source_row_no set on every row")
    runs_missing = q1(
        "SELECT count(*) FROM deliveries d WHERE NOT EXISTS (SELECT 1 FROM ingestion_runs r WHERE r.run_id = d.ingestion_run_id)"
    )
    record("deliveries_ingestion_run_ids_exist", runs_missing == 0, f"missing={runs_missing}")

    # 4. extras / legal balls / innings totals recomputed in Python --------------------------------
    extras_csv = Counter(r["extras_type"] or None for r in upd)
    extras_db = dict(
        con.execute("SELECT extras_type, count(*) FROM deliveries GROUP BY 1").fetchall()
    )
    record(
        "extras_type_distribution_verbatim", dict(extras_csv) == extras_db, str(dict(extras_csv))
    )
    legal = defaultdict(int)
    total = defaultdict(int)
    batter = defaultdict(int)
    n_rows = defaultdict(int)
    for r in upd:
        k = (int(r["match_id"]), int(r["innings"]))
        n_rows[k] += 1
        if r["extras_type"] not in ("wide", "Overstep", "other"):
            legal[k] += 1
        b = int(r["runs"] or 0)
        batter[k] += b
        total[k] += b + int(r["extras1_runs"] or 0) + int(r["extras_2_runs"] or 0)
    bad = 0
    for mid, inn, dc, lc, br, tr in con.execute(
        "SELECT match_id, innings_number, delivery_count, legal_ball_count, batter_runs_total, source_total_runs FROM innings"
    ).fetchall():
        k = (mid, inn)
        if (dc, lc, br, tr) != (n_rows[k], legal[k], batter[k], total[k]):
            bad += 1
    record(
        "innings_aggregates_match_csv",
        bad == 0 and len(n_rows) == q1("SELECT count(*) FROM innings"),
        f"innings={len(n_rows)} mismatches={bad}",
    )
    record(
        "no_is_super_over_column",
        q1("SELECT count(*) FROM information_schema.columns WHERE column_name ILIKE '%super%'")
        == 0,
        "no super-over column exists",
    )
    unv = q1(
        "SELECT count(*) FROM innings WHERE innings_number >= 3 AND innings_role_status <> 'UNVERIFIED'"
    )
    record("innings_3_4_unverified", unv == 0, f"violations={unv}")

    # 5. playing_eleven duplicates preserved ---------------------------------------------------------
    grp = Counter((r["match_id"], r["team_id"], r["player_id"]) for r in data["playing_eleven.csv"])
    dup_groups = {k: v for k, v in grp.items() if v > 1}
    dup_rows = sum(dup_groups.values())
    db_rows = q1("SELECT count(*) FROM match_squads WHERE duplicate_key_flag")
    db_groups = q1(
        "SELECT count(*) FROM (SELECT 1 FROM match_squads WHERE duplicate_key_flag GROUP BY match_id, team_id, player_id)"
    )
    record(
        "playing_eleven_duplicates_preserved",
        (dup_rows, len(dup_groups)) == (db_rows, db_groups),
        f"csv rows={dup_rows} groups={len(dup_groups)}; db rows={db_rows} groups={db_groups}",
    )

    # 6. matches without deliveries --------------------------------------------------------------------
    with_d = {int(r["match_id"]) for r in upd}
    without_csv = {int(r["match_id"]) for r in data["matches.csv"]} - with_d
    without_db = {
        r[0]
        for r in con.execute("SELECT match_id FROM matches WHERE NOT has_deliveries").fetchall()
    }
    record(
        "matches_without_deliveries_set", without_csv == without_db, f"{len(without_db)} matches"
    )
    orphan_matches = with_d - {int(r["match_id"]) for r in data["matches.csv"]}
    record(
        "delivery_match_ids_exist_in_matches", not orphan_matches, f"orphans={len(orphan_matches)}"
    )
    unexplained = q1(
        "SELECT count(*) FROM match_reconciliation WHERE NOT has_deliveries AND NOT no_deliveries_explained"
    )
    record("no_delivery_matches_explained", unexplained == 0, f"unexplained={unexplained}")

    # 7. players: every id in any official CSV exists ---------------------------------------------------
    ids: set[int] = set()
    for r in data["competition_team_player_mapping.csv"] + data["playing_eleven.csv"]:
        ids.add(int(r["player_id"]))
    for r in data["matches.csv"]:
        for c in ("home_team_captain_id", "away_team_captain_id"):
            if r[c]:
                ids.add(int(r[c]))
    for r in upd:
        for c in ("striker_id", "non_striker_id", "bowler_id", "dismissed_player_id"):
            if r[c]:
                ids.add(int(r[c]))
    db_ids = {r[0] for r in con.execute("SELECT player_id FROM players").fetchall()}
    record("players_equal_union_of_ids", ids == db_ids, f"csv={len(ids)} db={len(db_ids)}")
    names = defaultdict(set)
    for r in data["competition_team_player_mapping.csv"]:
        names[r["player_name"]].add(r["player_id"])
    dup_names = sorted(n for n, s in names.items() if len(s) > 1)
    db_names = sorted(
        r[0]
        for r in con.execute(
            "SELECT DISTINCT player_name FROM players WHERE shares_name_with_other_id"
        ).fetchall()
    )
    record("duplicate_names_not_merged", dup_names == db_names, f"{len(dup_names)} names")

    # 8. original vs updated comparison ---------------------------------------------------------------------
    orig = {(r["match_id"], r["innings"], r["innings_ball_num"]): r for r in data[ORIGINAL]}
    diffs: Counter = Counter()
    for r in upd:
        o = orig.get((r["match_id"], r["innings"], r["innings_ball_num"]))
        if o is None:
            diffs["__missing__"] += 1
            continue
        for c, v in r.items():
            if o[c] != v:
                diffs[c] += 1
    db_diffs = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT column_name, rows_different FROM ball_by_ball_comparison WHERE rows_different > 0"
        ).fetchall()
    }
    record("original_vs_updated_differences", dict(diffs) == db_diffs, str(dict(diffs)))

    # 9. misc consistency --------------------------------------------------------------------------------------
    comp_ok = q1(
        "SELECT count(*) FROM competitions WHERE (comp_name LIKE 'IPL%') <> (competition_type = 'IPL')"
    )
    record("competition_type_ipl_rule", comp_ok == 0, f"violations={comp_ok}")
    fails = [r for r in RESULTS if r[0] == "FAIL"]
    print(f"\nsummary: {len(RESULTS) - len(fails)} PASS, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
