"""Post-load validation: PK/FK/row-count/reconciliation checks and OPEN data-quality issues.

Every number is computed from the loaded database. Expected values only label PASS/FAIL.
OPEN issues are preserved findings; they are never fixed and never fail the run.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.core.config import Settings
from app.core.database import Database
from app.data_pipeline import csv_loader as cl

PK_SPECS: dict[str, tuple[str, ...]] = {
    "competitions": ("comp_id",),
    "teams": ("team_id",),
    "competition_teams": ("comp_id", "team_id"),
    "venues": ("venue_id",),
    "players": ("player_id",),
    "player_competition_mapping": ("comp_id", "team_id", "player_id"),
    "matches": ("match_id",),
    "match_squads": ("match_id", "team_id", "player_id", "squad_row_no"),
    "innings": ("match_id", "innings_number"),
    "deliveries": ("match_id", "innings_number", "innings_ball_num"),
    "match_reconciliation": ("match_id",),
    "raw_ball_by_ball": ("source_row_no",),
    "raw_ball_by_ball_updated": ("source_row_no",),
}

# (child, child columns, parent, parent columns); all are enforced FOREIGN KEYs.
FK_SPECS: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = [
    ("competition_teams", ("comp_id",), "competitions", ("comp_id",)),
    ("competition_teams", ("team_id",), "teams", ("team_id",)),
    (
        "player_competition_mapping",
        ("comp_id", "team_id"),
        "competition_teams",
        ("comp_id", "team_id"),
    ),
    ("player_competition_mapping", ("player_id",), "players", ("player_id",)),
    ("matches", ("comp_id",), "competitions", ("comp_id",)),
    ("matches", ("venue_id",), "venues", ("venue_id",)),
    ("matches", ("home_team_id",), "teams", ("team_id",)),
    ("matches", ("away_team_id",), "teams", ("team_id",)),
    ("matches", ("toss_win_team_id",), "teams", ("team_id",)),
    ("matches", ("win_team_id",), "teams", ("team_id",)),
    ("matches", ("home_team_captain_id",), "players", ("player_id",)),
    ("matches", ("away_team_captain_id",), "players", ("player_id",)),
    ("match_squads", ("match_id",), "matches", ("match_id",)),
    ("match_squads", ("team_id",), "teams", ("team_id",)),
    ("match_squads", ("player_id",), "players", ("player_id",)),
    ("innings", ("match_id",), "matches", ("match_id",)),
    ("innings", ("batting_team_id",), "teams", ("team_id",)),
    ("innings", ("bowling_team_id",), "teams", ("team_id",)),
    ("deliveries", ("match_id", "innings_number"), "innings", ("match_id", "innings_number")),
    ("deliveries", ("batting_team_id",), "teams", ("team_id",)),
    ("deliveries", ("bowling_team_id",), "teams", ("team_id",)),
    ("deliveries", ("striker_id",), "players", ("player_id",)),
    ("deliveries", ("non_striker_id",), "players", ("player_id",)),
    ("deliveries", ("bowler_id",), "players", ("player_id",)),
    ("deliveries", ("dismissed_player_id",), "players", ("player_id",)),
    ("match_reconciliation", ("match_id",), "matches", ("match_id",)),
]

LEGAL = "extras_type IS NULL OR extras_type NOT IN ('wide', 'Overstep', 'other')"


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(
        self,
        name: str,
        category: str,
        status: str,
        expected=None,
        observed=None,
        affected: int | None = None,
        severity: str | None = None,
        details=None,
    ) -> None:
        if severity is None:
            severity = {"FAIL": "ERROR", "OPEN": "WARNING"}.get(status, "INFO")
        self.rows.append(
            {
                "check_name": name,
                "category": category,
                "severity": severity,
                "status": status,
                "expected": None if expected is None else str(expected),
                "observed": None if observed is None else str(observed),
                "affected_rows": None if affected is None else int(affected),
                "details": None if details is None else json.dumps(details, default=str),
            }
        )

    def check(self, name, category, expected, observed, details=None) -> None:
        self.add(
            name,
            category,
            "PASS" if expected == observed else "FAIL",
            expected,
            observed,
            details=details,
        )


def _count(db: Database, sql: str) -> int:
    return int(db.scalar(sql) or 0)


def run_validation(
    db: Database, run_id: int, settings: Settings, expected_counts: dict[str, int]
) -> dict[str, int]:
    rec = Recorder()
    lineage = {
        r[0]: {"rows": r[1], "sha256": r[2], "path": r[3], "status": r[4]}
        for r in db.query(
            "SELECT file_name, row_count, sha256, file_path, load_status FROM dataset_lineage "
            "WHERE run_id = (SELECT max(run_id) FROM dataset_lineage)"
        )
    }
    _row_counts(db, rec, lineage, expected_counts)
    _keys(db, rec)
    _reconciliation(db, rec)
    _innings(db, rec)
    _comparison(db, rec)
    _sources_unchanged(rec, lineage)
    _config(db, rec, settings)
    _open_issues(db, rec)
    for r in rec.rows:
        db.execute(
            "INSERT INTO data_quality_results (run_id, check_name, category, severity, status, "
            "expected, observed, affected_rows, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                r["check_name"],
                r["category"],
                r["severity"],
                r["status"],
                r["expected"],
                r["observed"],
                r["affected_rows"],
                r["details"],
            ],
        )
    summary: dict[str, int] = {}
    for r in rec.rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return summary


# ---------------------------------------------------------------------------------------------
def _row_counts(db, rec, lineage, expected_counts) -> None:
    for file_name, tables in cl.COUNT_TABLES.items():
        src = lineage.get(file_name, {}).get("rows")
        for table in tables:
            n = _count(db, f"SELECT count(*) FROM {table}")
            rec.check(f"rowcount_{table}_vs_{file_name}", "ROW_COUNT", src, n)
    rec.check(
        "rowcount_teams_vs_distinct_team_ids_in_teams.csv",
        "ROW_COUNT",
        _count(db, "SELECT count(DISTINCT team_id) FROM competition_teams"),
        _count(db, "SELECT count(*) FROM teams"),
    )
    for table, exp in sorted(expected_counts.items()):
        rec.check(
            f"spec_rowcount_{table}", "ROW_COUNT", exp, _count(db, f"SELECT count(*) FROM {table}")
        )


def _keys(db, rec) -> None:
    for table, cols in PK_SPECS.items():
        keys = ", ".join(cols)
        dup = _count(
            db,
            f"SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT {keys} FROM {table})) "
            f"FROM {table}",
        )
        rec.check(f"pk_unique_{table}", "PK", 0, dup, {"key": list(cols)})
    for child, ccols, parent, pcols in FK_SPECS:
        cond = " AND ".join(f"c.{c} IS NOT NULL" for c in ccols)
        join = " AND ".join(f"p.{p} = c.{c}" for c, p in zip(ccols, pcols, strict=True))
        n = _count(
            db,
            f"SELECT count(*) FROM {child} c WHERE {cond} AND NOT EXISTS "
            f"(SELECT 1 FROM {parent} p WHERE {join})",
        )
        rec.check(f"fk_orphans_{child}.{'+'.join(ccols)}->{parent}", "FK", 0, n, {"enforced": True})
    for table in PK_SPECS:
        n = _count(
            db,
            f"SELECT count(*) FROM {table} t WHERE ingestion_run_id IS NULL OR NOT EXISTS "
            "(SELECT 1 FROM ingestion_runs r WHERE r.run_id = t.ingestion_run_id)",
        )
        rec.check(f"provenance_run_id_{table}", "FK", 0, n)
        if table != "players":
            rec.check(
                f"provenance_source_file_{table}",
                "PK",
                0,
                _count(db, f"SELECT count(*) FROM {table} WHERE source_file IS NULL"),
            )
    for table in ("competition_teams", "matches", "match_squads", "deliveries"):
        rec.check(
            f"provenance_source_row_no_{table}",
            "PK",
            0,
            _count(db, f"SELECT count(*) FROM {table} WHERE source_row_no IS NULL"),
        )


def _reconciliation(db, rec) -> None:
    total = _count(db, "SELECT count(*) FROM matches")
    with_d = _count(db, "SELECT count(*) FROM matches WHERE has_deliveries")
    without = db.query(
        "SELECT match_id, match_date, result, result_status, win_team_id, "
        "no_deliveries_explained FROM match_reconciliation WHERE NOT has_deliveries "
        "ORDER BY match_id"
    )
    rec.check(
        "reconcile_matches_equal_with_plus_without", "RECONCILIATION", total, with_d + len(without)
    )
    rec.add(
        "reconcile_matches_without_deliveries",
        "RECONCILIATION",
        "INFO",
        None,
        f"{len(without)} of {total} matches have no deliveries; {with_d} have",
        len(without),
        details=[
            {
                "match_id": r[0],
                "match_date": str(r[1]),
                "result": r[2],
                "result_status": r[3],
                "win_team_id": r[4],
                "explained": r[5],
            }
            for r in without
        ],
    )
    unexplained = [r[0] for r in without if not r[5]]
    rec.add(
        "reconcile_no_delivery_matches_explained",
        "RECONCILIATION",
        "PASS" if not unexplained else "OPEN",
        "all explained (ABANDONED/NO_RESULT, no winner)",
        f"{len(without) - len(unexplained)} explained, {len(unexplained)} unexplained",
        len(unexplained),
        details={"unexplained_match_ids": unexplained},
    )
    rec.check(
        "reconcile_has_deliveries_flag_consistent",
        "RECONCILIATION",
        0,
        _count(
            db,
            "SELECT count(*) FROM matches m WHERE m.has_deliveries <> EXISTS "
            "(SELECT 1 FROM deliveries d WHERE d.match_id = m.match_id)",
        ),
    )
    unknown = _count(db, "SELECT count(*) FROM matches WHERE result_status = 'UNKNOWN'")
    rec.add(
        "result_status_unknown",
        "CONSISTENCY",
        "PASS" if unknown == 0 else "OPEN",
        0,
        unknown,
        unknown,
    )
    dist = dict(db.query("SELECT result_status, count(*) FROM matches GROUP BY 1 ORDER BY 1"))
    rec.add(
        "result_status_distribution", "CONSISTENCY", "INFO", None, json.dumps(dist), details=dist
    )
    types = {
        r[0]: {"competitions": r[1], "matches": r[2]}
        for r in db.query(
            "SELECT c.competition_type, count(DISTINCT c.comp_id), count(m.match_id) "
            "FROM competitions c LEFT JOIN matches m ON m.comp_id = c.comp_id GROUP BY 1 ORDER BY 1"
        )
    }
    rec.add(
        "competition_type_distribution",
        "CONSISTENCY",
        "INFO",
        None,
        json.dumps(types),
        details=types,
    )
    ipl_fmt = _count(
        db,
        "SELECT count(*) FROM competitions WHERE competition_type = 'IPL' AND match_format <> 'T20'",
    )
    rec.add("ipl_competitions_not_format_T20", "CONSISTENCY", "INFO", 0, ipl_fmt, ipl_fmt)


def _innings(db, rec) -> None:
    rec.check(
        "innings_teams_are_match_home_away_pair",
        "CONSISTENCY",
        0,
        _count(
            db,
            "SELECT count(*) FROM innings i JOIN matches m USING (match_id) WHERE NOT "
            "((i.batting_team_id = m.home_team_id AND i.bowling_team_id = m.away_team_id) OR "
            "(i.batting_team_id = m.away_team_id AND i.bowling_team_id = m.home_team_id))",
        ),
    )
    rec.check(
        "innings_single_batting_and_bowling_team",
        "CONSISTENCY",
        0,
        _count(db, "SELECT count(*) FROM innings WHERE NOT teams_consistent"),
    )
    rec.check(
        "innings_1_exists_for_every_match_with_deliveries",
        "CONSISTENCY",
        0,
        _count(
            db,
            "SELECT count(*) FROM matches m WHERE m.has_deliveries AND NOT EXISTS "
            "(SELECT 1 FROM innings i WHERE i.match_id = m.match_id AND i.innings_number = 1)",
        ),
    )
    rec.check(
        "innings_ball_num_is_1_to_n",
        "CONSISTENCY",
        0,
        _count(
            db,
            "SELECT count(*) FROM (SELECT 1 FROM deliveries GROUP BY match_id, innings_number "
            "HAVING min(innings_ball_num) <> 1 OR max(innings_ball_num) <> count(*))",
        ),
    )
    bad = _count(
        db,
        f"""SELECT count(*) FROM innings i JOIN (
              SELECT TRY_CAST(match_id AS INTEGER) m, TRY_CAST(innings AS INTEGER) n,
                     count(*) FILTER (WHERE {LEGAL}) legal,
                     coalesce(sum(TRY_CAST(runs AS INTEGER)), 0)
                     + coalesce(sum(TRY_CAST(extras1_runs AS INTEGER)), 0)
                     + coalesce(sum(TRY_CAST(extras_2_runs AS INTEGER)), 0) total
              FROM raw_ball_by_ball_updated GROUP BY 1, 2) r
            ON r.m = i.match_id AND r.n = i.innings_number
            WHERE r.legal <> i.legal_ball_count OR r.total <> i.source_total_runs""",
    )
    rec.check("innings_legal_balls_and_total_recomputed_from_raw", "CONSISTENCY", 0, bad)
    rec.check(
        "innings_numbers_within_1_to_4",
        "CONSISTENCY",
        0,
        _count(db, "SELECT count(*) FROM innings WHERE innings_number NOT BETWEEN 1 AND 4"),
    )


def _comparison(db, rec) -> None:
    n_o = _count(db, "SELECT count(*) FROM raw_ball_by_ball")
    n_u = _count(db, "SELECT count(*) FROM raw_ball_by_ball_updated")
    rec.check("comparison_row_counts_equal", "RECONCILIATION", n_o, n_u)
    only = _count(
        db,
        "SELECT coalesce(max(rows_only_in_original + rows_only_in_updated), 0) FROM ball_by_ball_comparison",
    )
    rec.check("comparison_key_sets_equal", "RECONCILIATION", 0, only)
    diffs = {
        r[0]: r[1]
        for r in db.query(
            "SELECT column_name, rows_different FROM ball_by_ball_comparison "
            "WHERE rows_different > 0 ORDER BY column_name"
        )
    }
    rec.add(
        "comparison_columns_that_differ",
        "RECONCILIATION",
        "INFO",
        None,
        json.dumps(diffs),
        sum(diffs.values()),
        details=diffs,
    )


def _sources_unchanged(rec, lineage) -> None:
    for name, info in sorted(lineage.items()):
        path = Path(info["path"])
        if info["sha256"] is None:
            continue
        now = cl.sha256_file(path) if path.is_file() else None
        rec.check(f"source_unchanged_{name}", "CONSISTENCY", info["sha256"], now)


def _config(db, rec, settings) -> None:
    rec.add(
        "weights_sum_to_one",
        "CONSISTENCY",
        "PASS" if abs(settings.ipl_weight + settings.t20i_weight - 1) < 1e-9 else "FAIL",
        1.0,
        settings.ipl_weight + settings.t20i_weight,
    )
    n = _count(db, "SELECT count(*) FROM model_versions WHERE kind = 'WEIGHTING_CONFIG'")
    rec.add("weighting_config_stored", "CONSISTENCY", "PASS" if n >= 1 else "FAIL", ">= 1", n)


def _open_issues(db, rec) -> None:
    def open_(name, n, observed=None, details=None, expected="0 (issue preserved, not fixed)"):
        rec.add(
            name,
            "OPEN_ISSUE",
            "OPEN" if n else "PASS",
            expected,
            observed if observed is not None else n,
            n,
            details=details,
        )

    r = db.query(
        "SELECT count(*), count(DISTINCT (match_id, team_id, player_id)), count(DISTINCT match_id) "
        "FROM match_squads WHERE duplicate_key_flag"
    )[0]
    open_(
        "open_playing_eleven_repeated_keys",
        r[0],
        f"{r[0]} rows in {r[1]} (match,team,player) groups across {r[2]} matches; all kept",
        {"rows": r[0], "groups": r[1], "matches": r[2]},
    )
    n = _count(
        db,
        "SELECT count(*) FROM matches m WHERE NOT EXISTS (SELECT 1 FROM match_squads s WHERE s.match_id = m.match_id)",
    )
    ids = [
        x[0]
        for x in db.query(
            "SELECT match_id FROM matches m WHERE NOT EXISTS (SELECT 1 FROM match_squads s WHERE s.match_id = m.match_id) ORDER BY 1"
        )
    ]
    open_("open_matches_without_playing_eleven_rows", n, details={"match_ids": ids})
    n = _count(db, "SELECT count(*) FROM match_squads WHERE NOT mapping_row_exists")
    open_("open_playing_eleven_rows_without_mapping_row", n)
    for role, col in (("striker", "striker_id"), ("bowler", "bowler_id")):
        base = (
            f"FROM deliveries d WHERE d.{col} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM match_squads s "
            f"WHERE s.match_id = d.match_id AND s.player_id = d.{col})"
        )
        rows = _count(db, f"SELECT count(*) {base}")
        pairs = _count(db, f"SELECT count(*) FROM (SELECT DISTINCT d.match_id, d.{col} {base})")
        no_squad = _count(
            db,
            f"SELECT count(*) {base} AND NOT EXISTS (SELECT 1 FROM match_squads s2 WHERE s2.match_id = d.match_id)",
        )
        open_(
            f"open_delivery_{role}_not_in_match_squad",
            rows,
            f"{rows} delivery rows, {pairs} distinct (match, {role}) pairs",
            {
                "rows": rows,
                "distinct_pairs": pairs,
                "rows_in_matches_without_any_squad_rows": no_squad,
            },
        )
    n = _count(
        db,
        "SELECT count(*) FROM deliveries WHERE dismissal_field_anomaly = 'DISMISSED_PLAYER_WITHOUT_WICKET'",
    )
    open_("open_dismissed_player_without_wicket_flag", n)
    types = dict(
        db.query(
            "SELECT coalesce(dismissal_type, '<null>'), count(*) FROM deliveries "
            "WHERE dismissal_field_anomaly = 'WICKET_WITHOUT_DISMISSED_PLAYER' GROUP BY 1 ORDER BY 1"
        )
    )
    open_(
        "open_wicket_without_dismissed_player",
        sum(types.values()),
        details={"dismissal_types": types},
    )
    for label in ("other", "Penalty"):
        n = _count(db, f"SELECT count(*) FROM deliveries WHERE extras_type = '{label}'")
        open_(
            f"open_extras_type_{label}_label_unverified", n, f"{n} rows; extras_type kept verbatim"
        )
    n = _count(db, "SELECT count(*) FROM deliveries WHERE extras_secondary_runs > 0")
    open_(
        "open_extras_secondary_split_unverified",
        n,
        f"{n} rows with extras_2_runs > 0; split between extras1/extras_2 unverified",
    )
    r = db.query(
        "SELECT count(*), count(DISTINCT match_id), coalesce(sum(delivery_count), 0) "
        "FROM innings WHERE innings_role_status = 'UNVERIFIED'"
    )[0]
    open_(
        "open_innings_3_4_role_unverified",
        r[0],
        f"{r[0]} innings in {r[1]} matches ({r[2]} delivery rows); not classified as Super Overs",
        {"innings": r[0], "matches": r[1], "delivery_rows": int(r[2])},
    )
    n = _count(db, "SELECT count(*) FROM matches WHERE man_of_the_match = 0")
    open_(
        "open_man_of_the_match_zero_sentinel",
        n,
        f"{n} matches with man_of_the_match = 0 (not a player id; no FK)",
    )
    n = _count(db, "SELECT count(*) FROM deliveries WHERE delivery_time_raw LIKE '% UTC'")
    open_(
        "open_delivery_time_utc_suffix_vs_ist_column_name",
        n,
        f"{n} rows carry a 'UTC' suffix in column delivery_ist_time; no timezone conversion applied",
    )
    n = _count(db, "SELECT count(*) FROM deliveries WHERE delivery_time_is_midnight")
    open_(
        "open_delivery_time_midnight_rows",
        n,
        f"{n} rows with a 00:00:00 time part (likely date-only)",
    )
    names = db.query(
        "SELECT player_name, list(player_id ORDER BY player_id) FROM players WHERE shares_name_with_other_id "
        "GROUP BY 1 ORDER BY 1"
    )
    open_(
        "open_duplicate_player_names_with_different_ids",
        len(names),
        f"{len(names)} names map to more than one player_id; not merged",
        {n[0]: n[1] for n in names},
    )
    n = _count(db, "SELECT count(*) FROM players WHERE name_source = 'UNKNOWN'")
    open_("open_players_without_any_name", n)
    for name, observed in (
        (
            "open_cricsheet_innings_total_disagreements",
            "10 innings (matches 14130, 14164, 32618, 37349, 37352, 50504) disagree with Cricsheet totals",
        ),
        (
            "open_matches_not_linkable_to_cricsheet",
            "108 matches with deliveries could not be linked to Cricsheet (79 T20I, 29 T20)",
        ),
    ):
        rec.add(
            name,
            "OPEN_ISSUE",
            "OPEN",
            "carried from Phase 1, not recomputed (Cricsheet is not loaded in Phase 2)",
            observed,
            None,
            details={"source": "data/audit/cricsheet_overlap_report.json (Phase 1)"},
        )


# ---------------------------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------------------------
def write_reports(db: Database, run_id: int, settings: Settings) -> None:
    audit = settings.audit_dir
    audit.mkdir(parents=True, exist_ok=True)
    cols = [
        "check_name",
        "category",
        "severity",
        "status",
        "expected",
        "observed",
        "affected_rows",
        "details",
    ]
    results = [
        dict(zip(cols, r, strict=True))
        for r in db.query(
            f"SELECT {', '.join(cols)} FROM data_quality_results WHERE run_id = ? ORDER BY result_id",
            [run_id],
        )
    ]
    for r in results:
        r["details"] = json.loads(r["details"]) if r["details"] else None
    run = db.query(
        "SELECT run_id, status, mode, schema_version, data_version, reason FROM ingestion_runs WHERE run_id = ?",
        [run_id],
    )[0]
    lineage = [
        dict(
            zip(
                ["file_name", "role", "load_status", "sha256", "row_count", "target_table"],
                r,
                strict=True,
            )
        )
        for r in db.query(
            "SELECT file_name, role, load_status, sha256, row_count, target_table FROM dataset_lineage "
            "WHERE run_id = (SELECT max(run_id) FROM dataset_lineage) ORDER BY lineage_id"
        )
    ]
    counts = {
        t: _count(db, f"SELECT count(*) FROM {t}")
        for t in cl.COUNT_TABLES_ALL
        if db.table_exists(t)
    }
    summary: dict[str, int] = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    report = {
        "run": dict(
            zip(
                ["run_id", "status", "mode", "schema_version", "data_version", "reason"],
                run,
                strict=True,
            )
        ),
        "summary": summary,
        "table_row_counts": counts,
        "lineage": lineage,
        "results": results,
    }
    settings.validation_report_json.write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    settings.validation_report_md.write_text(_markdown(report), encoding="utf-8")

    comp = [
        dict(
            zip(
                [
                    "column_name",
                    "rows_compared",
                    "rows_different",
                    "rows_only_in_original",
                    "rows_only_in_updated",
                    "details",
                ],
                r,
                strict=True,
            )
        )
        for r in db.query(
            "SELECT column_name, rows_compared, rows_different, rows_only_in_original, rows_only_in_updated, details "
            "FROM ball_by_ball_comparison ORDER BY column_name"
        )
    ]
    for c in comp:
        c["details"] = json.loads(c["details"]) if c["details"] else None
    (audit / "ball_by_ball_comparison.json").write_text(
        json.dumps(comp, indent=2, default=str), encoding="utf-8"
    )
    lines = [
        "# ball_by_ball.csv (original) vs updated_ball_by_ball.csv",
        "",
        "Computed from the loaded raw tables, joined on (match_id, innings, innings_ball_num).",
        "",
        "| column | rows compared | rows different | only in original | only in updated |",
        "|---|---|---|---|---|",
    ]
    for c in comp:
        lines.append(
            f"| {c['column_name']} | {c['rows_compared']} | {c['rows_different']} | "
            f"{c['rows_only_in_original']} | {c['rows_only_in_updated']} |"
        )
    (audit / "ball_by_ball_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rec_cols = [
        "match_id",
        "comp_id",
        "match_date",
        "home_team_id",
        "away_team_id",
        "result",
        "result_status",
        "win_team_id",
        "has_deliveries",
        "delivery_count",
        "innings_count",
        "squad_row_count",
        "played_row_count",
        "no_deliveries_explained",
        "reason",
    ]
    with (audit / "phase2_match_reconciliation.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(rec_cols)
        w.writerows(
            db.query(f"SELECT {', '.join(rec_cols)} FROM match_reconciliation ORDER BY match_id")
        )


def _markdown(report: dict) -> str:
    run = report["run"]
    out = [
        "# Phase 2 validation report",
        "",
        f"Run {run['run_id']} ({run['status']}, {run['mode']}); schema `{run['schema_version']}`, data `{run['data_version']}`.",
        "",
        "Summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report["summary"].items())),
        "",
        "## Table row counts",
        "",
        "| table | rows |",
        "|---|---|",
    ]
    out += [f"| {t} | {n} |" for t, n in report["table_row_counts"].items()]
    out += [
        "",
        "## Source lineage",
        "",
        "| file | role | status | rows | sha256 |",
        "|---|---|---|---|---|",
    ]
    out += [
        f"| {x['file_name']} | {x['role']} | {x['load_status']} | {x['row_count']} | {(x['sha256'] or '')[:16]} |"
        for x in report["lineage"]
    ]
    for status in ("FAIL", "OPEN", "PASS", "INFO"):
        rows = [r for r in report["results"] if r["status"] == status]
        out += [
            "",
            f"## {status} ({len(rows)})",
            "",
            "| check | expected | observed | affected |",
            "|---|---|---|---|",
        ]
        for r in rows:
            obs = str(r["observed"]).replace("|", "/")
            exp = str(r["expected"]).replace("|", "/")
            out.append(f"| {r['check_name']} | {exp} | {obs[:200]} | {r['affected_rows']} |")
    return "\n".join(out) + "\n"
