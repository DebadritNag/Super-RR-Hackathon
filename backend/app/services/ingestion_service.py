"""Idempotent, transactional ingestion of the official competition CSVs into DuckDB."""

from __future__ import annotations

import csv
import hashlib
import json
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings
from app.core.database import REPLACEABLE_TABLES, Database, connect, ddl_sha256
from app.data_pipeline import csv_loader as cl
from app.data_pipeline.data_quality import classify_result

ERROR_COLUMNS = [
    "error_id",
    "run_id",
    "severity",
    "error_type",
    "table_name",
    "source_file",
    "source_row_no",
    "message",
    "raw_payload",
    "created_at",
]


class IngestionError(Exception):
    """A hard failure that must roll the load transaction back."""

    def __init__(self, error_type: str, message: str, table_name: str | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.table_name = table_name


@dataclass
class FileInfo:
    spec: cl.SourceSpec
    path: Path
    exists: bool
    sha256: str | None = None
    size_bytes: int | None = None
    row_count: int | None = None
    column_count: int | None = None


@dataclass
class RunResult:
    run_id: int
    status: str
    mode: str
    reason: str
    counts: dict[str, int] = field(default_factory=dict)
    validation: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    elapsed_seconds: float = 0.0

    @property
    def exit_code(self) -> int:
        if self.status == "FAILED":
            return 1
        if self.validation.get("FAIL", 0) > 0:
            return 2
        return 0


METRIC_DEFINITIONS: list[tuple[str, str, str, str, str, str]] = [
    (
        "is_legal_ball",
        "extras_type IS NULL OR extras_type NOT IN ('wide','Overstep','other')",
        "extras_type",
        "updated_ball_by_ball.csv",
        "Equals Cricsheet legal balls in 1,497 of 1,504 innings (Phase 1 extras_mapping.md). "
        "The 'Penalty' row is counted legal by this rule but legal_ball_status is UNVERIFIED.",
        "VERIFIED",
    ),
    (
        "batter_runs",
        "source column runs, verbatim",
        "runs",
        "updated_ball_by_ball.csv",
        "Equals Cricsheet batter runs in 1,488 of 1,504 innings (Phase 1).",
        "VERIFIED",
    ),
    (
        "has_extra",
        "extras_type IS NOT NULL AND extras_type <> 'None'",
        "extras_type",
        "updated_ball_by_ball.csv",
        "The literal string 'None' is a category, not a missing value (definitional).",
        "VERIFIED",
    ),
    (
        "competition_type",
        "IPL if comp_name starts with 'IPL'; T20I if match_format = 'T20I'; else OTHER_T20",
        "comp_name, match_format",
        "competitions.csv",
        "Counts per type are stored in phase2_validation_report.",
        "VERIFIED",
    ),
    (
        "result_status",
        "classify_result(matches.result) from app/data_pipeline/data_quality.py",
        "result",
        "matches.csv",
        "Text classifier; all 16 matches without deliveries are ABANDONED (Phase 1).",
        "PARTIALLY_VERIFIED",
    ),
    (
        "source_total_runs",
        "batter_runs + extras_primary_runs + extras_secondary_runs summed per innings",
        "runs, extras1_runs, extras_2_runs",
        "updated_ball_by_ball.csv",
        "Equals Cricsheet innings total in 1,494 of 1,504 innings (Phase 1); the extras split "
        "between the two columns is unverified.",
        "PARTIALLY_VERIFIED",
    ),
    (
        "extras_label_unverified",
        "extras_type IN ('other','Penalty')",
        "extras_type",
        "updated_ball_by_ball.csv",
        "The meaning of 'other' and 'Penalty' is not established; no meaning is assumed.",
        "UNVERIFIED",
    ),
    (
        "innings_role_status",
        "STANDARD for innings 1-2, UNVERIFIED for innings >= 3",
        "innings",
        "updated_ball_by_ball.csv",
        "Innings 3/4 are not classified as Super Overs without verification.",
        "UNVERIFIED",
    ),
    (
        "extras_secondary_runs",
        "source column extras_2_runs, verbatim",
        "extras_2_runs",
        "updated_ball_by_ball.csv",
        "Only the sum extras1+extras2 agrees with Cricsheet; the split is unverified.",
        "UNVERIFIED",
    ),
]


def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        db_path: Path | str | None = None,
        expected_counts: dict[str, int] | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self.db_path = Path(db_path) if db_path else settings.duckdb_path
        self.expected_counts = cl.EXPECTED_ROWS if expected_counts is None else expected_counts
        self.fault_hook = fault_hook
        self.warnings: list[dict] = []

    # ------------------------------------------------------------------ helpers
    def _hook(self, step: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(step)

    def _paths(self) -> dict[str, Path]:
        return {s.file_name: self.settings.data_root / s.file_name for s in cl.SOURCES}

    def _profile(self, db: Database) -> dict[str, FileInfo]:
        infos: dict[str, FileInfo] = {}
        for spec in cl.SOURCES:
            path = self.settings.data_root / spec.file_name
            if not path.is_file():
                if spec.required:
                    raise IngestionError("MISSING_FILE", f"required file not found: {path}")
                infos[spec.file_name] = FileInfo(spec, path, False)
                continue
            header = cl.read_header(path)
            problem = cl.header_problem(spec, header)
            if problem:
                raise IngestionError("HEADER_MISMATCH", f"{spec.file_name}: {problem}")
            infos[spec.file_name] = FileInfo(
                spec,
                path,
                True,
                cl.sha256_file(path),
                path.stat().st_size,
                cl.count_rows(db, path),
                len(header),
            )
        return infos

    @staticmethod
    def _table_counts(db: Database) -> dict[str, int]:
        counts: dict[str, int] = {}
        for table in reversed(REPLACEABLE_TABLES):
            if db.table_exists(table):
                counts[table] = int(db.scalar(f"SELECT count(*) FROM {table}"))
        return counts

    @staticmethod
    def _versions(infos: dict[str, FileInfo]) -> tuple[str, str]:
        lines = sorted(
            f"{n}:{i.sha256}"
            for n, i in infos.items()
            if i.exists and i.spec.role in (cl.PRIMARY, cl.COMPARISON_RAW)
        )
        data_version = "data-" + hashlib.sha256("\n".join(lines).encode()).hexdigest()[:12]
        return data_version, "phase2-" + ddl_sha256()[:8]

    # ------------------------------------------------------------------ run control
    def run(self, force: bool = False, validate_only: bool = False) -> RunResult:
        started = time.time()
        mode = "VALIDATE_ONLY" if validate_only else ("FORCE" if force else "LOAD")
        db = connect(self.db_path)
        run_id = -1
        self.warnings = []
        try:
            db.apply_persistent_schema()
            db.execute(
                "UPDATE ingestion_runs SET status = 'ABORTED', finished_at = current_timestamp "
                "WHERE status = 'RUNNING'"
            )
            run_id = int(
                db.scalar(
                    "INSERT INTO ingestion_runs (started_at, status, mode, force_flag) "
                    "VALUES (current_timestamp, 'RUNNING', ?, ?) RETURNING run_id",
                    [mode, force],
                )
            )
            try:
                result = self._run(db, run_id, mode, force, validate_only)
            except Exception as exc:  # noqa: BLE001 - recorded then reported as a failed run
                result = self._record_failure(db, run_id, mode, exc)
            result.elapsed_seconds = round(time.time() - started, 2)
            return result
        finally:
            db.close()

    def _run(
        self, db: Database, run_id: int, mode: str, force: bool, validate_only: bool
    ) -> RunResult:
        from app.services import validation_service as vs

        infos = self._profile(db)
        hashes = {n: i.sha256 for n, i in infos.items() if i.exists}
        data_version, schema_version = self._versions(infos)

        if validate_only:
            summary = vs.run_validation(db, run_id, self.settings, self.expected_counts)
            vs.write_reports(db, run_id, self.settings)
            self._finish(db, run_id, "SUCCESS", "validate-only", schema_version, data_version)
            return RunResult(
                run_id, "SUCCESS", mode, "validate-only", self._table_counts(db), summary
            )

        must_load, reason = self._decide(db, infos, force)
        if not must_load:
            self._register_model_versions(db, run_id, data_version, schema_version)
            self._finish(db, run_id, "NO_CHANGE", reason, schema_version, data_version, hashes)
            return RunResult(run_id, "NO_CHANGE", mode, reason, self._table_counts(db))

        self._load(db, run_id, infos, data_version, schema_version)
        counts = self._table_counts(db)
        self._write_row_warnings(db, run_id)
        summary = vs.run_validation(db, run_id, self.settings, self.expected_counts)
        vs.write_reports(db, run_id, self.settings)
        self._write_errors_csv(db, run_id)
        self._finish(db, run_id, "SUCCESS", reason, schema_version, data_version, hashes, counts)
        return RunResult(run_id, "SUCCESS", mode, reason, counts, summary)

    def _finish(
        self,
        db: Database,
        run_id: int,
        status: str,
        reason: str,
        schema_version: str,
        data_version: str,
        hashes: dict | None = None,
        counts: dict | None = None,
        error: str | None = None,
    ) -> None:
        db.execute(
            "UPDATE ingestion_runs SET status = ?, finished_at = current_timestamp, reason = ?, "
            "schema_version = ?, data_version = ?, source_hashes = ?, rows_loaded = ?, "
            "error_message = ? WHERE run_id = ?",
            [
                status,
                reason,
                schema_version,
                data_version,
                _json(hashes) if hashes is not None else None,
                _json(counts) if counts is not None else None,
                error,
                run_id,
            ],
        )

    def _record_failure(self, db: Database, run_id: int, mode: str, exc: Exception) -> RunResult:
        """Called after the load transaction (if any) has been rolled back."""
        error_type = getattr(exc, "error_type", "EXCEPTION")
        table_name = getattr(exc, "table_name", None)
        message = f"{type(exc).__name__}: {exc}"
        try:
            db.execute("ROLLBACK")  # no-op safety if a transaction is somehow still open
        except Exception:  # noqa: BLE001
            pass
        db.execute(
            "UPDATE ingestion_runs SET status = 'FAILED', finished_at = current_timestamp, "
            "error_message = ? WHERE run_id = ?",
            [message, run_id],
        )
        rows = [
            {
                "severity": "ERROR",
                "error_type": error_type,
                "table_name": table_name,
                "source_file": None,
                "source_row_no": None,
                "message": message,
                "raw_payload": _json({"traceback": traceback.format_exc()[-4000:]}),
            }
        ] + self.warnings
        self._insert_errors(db, run_id, rows)
        self._write_errors_csv(db, run_id)
        return RunResult(run_id, "FAILED", mode, "load failed; rolled back", error=message)

    # ------------------------------------------------------------------ idempotency
    def _decide(self, db: Database, infos: dict[str, FileInfo], force: bool) -> tuple[bool, str]:
        if force:
            return True, "forced reload (--force)"
        last = db.scalar("SELECT max(run_id) FROM dataset_lineage")
        if last is None:
            return True, "no previous successful load"
        status = db.scalar("SELECT status FROM ingestion_runs WHERE run_id = ?", [last])
        if status != "SUCCESS":
            return True, f"last load run {last} has status {status}"
        lineage = {
            r[0]: (r[1], r[2])
            for r in db.query(
                "SELECT file_name, sha256, row_count FROM dataset_lineage WHERE run_id = ?", [last]
            )
        }
        if set(lineage) != set(infos):
            return True, "tracked file set changed"
        for name, info in infos.items():
            if lineage[name][0] != info.sha256:
                return True, f"source file changed: {name}"
        meta = dict(db.query("SELECT key, value FROM schema_meta"))
        if meta.get("ddl_sha256") != ddl_sha256():
            return True, "schema DDL changed"
        for name, tables in cl.COUNT_TABLES.items():
            for table in tables:
                if not db.table_exists(table):
                    return True, f"table missing: {table}"
                if int(db.scalar(f"SELECT count(*) FROM {table}")) != lineage[name][1]:
                    return True, f"row count of {table} differs from lineage"
        return False, "no change: source hashes, schema and row counts match the last load"

    # ------------------------------------------------------------------ load transaction
    def _load(
        self,
        db: Database,
        run_id: int,
        infos: dict[str, FileInfo],
        data_version: str,
        schema_version: str,
    ) -> None:
        with db.transaction():
            db.drop_replaceable()
            db.create_replaceable()
            self._hook("schema")
            self._stage(db, infos)
            self._hook("stage")
            self._pre_checks(db, infos)
            self._hook("pre_checks")
            steps = [
                (
                    "raw_ball_by_ball",
                    cl.insert_raw_sql("raw_ball_by_ball", "stg_orig", cl.ORIGINAL, run_id),
                ),
                (
                    "raw_ball_by_ball_updated",
                    cl.insert_raw_sql("raw_ball_by_ball_updated", "stg_upd", cl.UPDATED, run_id),
                ),
                ("competitions", cl.insert_competitions_sql(run_id)),
                ("teams", cl.insert_teams_sql(run_id)),
                ("competition_teams", cl.insert_competition_teams_sql(run_id)),
                ("venues", cl.insert_venues_sql(run_id)),
                ("players", cl.insert_players_sql(run_id)),
                ("player_competition_mapping", cl.insert_mapping_sql(run_id)),
                ("matches", cl.insert_matches_sql(run_id)),
                ("match_squads", cl.insert_match_squads_sql(run_id)),
                ("innings", cl.insert_innings_sql(run_id)),
                ("deliveries", cl.insert_deliveries_sql(run_id)),
                ("match_reconciliation", cl.insert_reconciliation_sql(run_id)),
            ]
            for name, sql in steps:
                try:
                    db.execute(sql)
                except Exception as exc:
                    raise IngestionError(
                        "EXCEPTION", f"{type(exc).__name__}: {exc}", table_name=name
                    ) from exc
                self._hook(name)
            for sql in cl.comparison_sql(run_id):
                db.execute(sql)
            self._hook("comparison")
            self._post_checks(db, infos)
            self._write_lineage(db, run_id, infos)
            self._register_model_versions(db, run_id, data_version, schema_version)
            db.execute(
                "INSERT OR REPLACE INTO schema_meta VALUES ('schema_version', ?), "
                "('ddl_sha256', ?)",
                [schema_version, ddl_sha256()],
            )
            self._hook("metadata")
            for name, info in infos.items():
                if info.exists and cl.sha256_file(info.path) != info.sha256:
                    raise IngestionError(
                        "SOURCE_CHANGED_DURING_RUN", f"{name} changed while the run was in progress"
                    )

    def _stage(self, db: Database, infos: dict[str, FileInfo]) -> None:
        for info in infos.values():
            if info.spec.stage_table and info.exists:
                db.execute(cl.stage_sql(info.spec.stage_table, info.path))
        db.execute(
            "CREATE OR REPLACE TEMP TABLE stg_result_map (result VARCHAR, result_status VARCHAR)"
        )
        results = [r[0] for r in db.query("SELECT DISTINCT coalesce(result, '') FROM stg_matches")]
        for res in results:
            db.execute(
                "INSERT INTO stg_result_map VALUES (?, ?)", [res, classify_result(res or None)]
            )
        db.execute(cl.create_t_del_sql())

    def _pre_checks(self, db: Database, infos: dict[str, FileInfo]) -> None:
        for info in infos.values():
            stage = info.spec.stage_table
            if stage and info.exists:
                n = int(db.scalar(f"SELECT count(*) FROM {stage}"))
                if n != info.row_count:
                    raise IngestionError(
                        "ROW_COUNT_MISMATCH",
                        f"{info.spec.file_name}: staged {n} rows, file profile {info.row_count}",
                    )
        for stage, specs in cl.CAST_SPECS.items():
            file_name = next(s.file_name for s in cl.SOURCES if s.stage_table == stage)
            for col, kind, is_key in specs:
                rows = db.query(cl.cast_failure_sql(stage, col, kind))
                if not rows:
                    continue
                if is_key:
                    raise IngestionError(
                        "CAST_FAILURE",
                        f"{file_name}.{col}: {len(rows)} non-castable key values "
                        f"(first row {rows[0][0]}: {rows[0][1]!r})",
                        table_name=stage,
                    )
                for row_no, value in rows:
                    self.warnings.append(
                        {
                            "severity": "WARNING",
                            "error_type": "CAST_FAILURE",
                            "table_name": stage,
                            "source_file": file_name,
                            "source_row_no": row_no,
                            "message": f"{col}={value!r} cannot be cast to {kind}; stored as NULL",
                            "raw_payload": _json({"column": col, "value": value}),
                        }
                    )
        bad = db.query(
            "SELECT team_id FROM stg_teams GROUP BY team_id HAVING count(DISTINCT team_name) > 1"
        )
        if bad:
            raise IngestionError("KEY_CONFLICT", f"team_id with several names: {bad[:5]}", "teams")
        bad = db.query(
            "SELECT venue_id FROM stg_matches GROUP BY venue_id "
            "HAVING count(DISTINCT venue_country) > 1"
        )
        if bad:
            raise IngestionError(
                "KEY_CONFLICT", f"venue_id with several countries: {bad[:5]}", "venues"
            )
        for stage in ("stg_orig", "stg_upd"):
            dup = db.scalar(
                f"SELECT count(*) FROM (SELECT 1 FROM {stage} GROUP BY match_id, innings, "
                "innings_ball_num HAVING count(*) > 1)"
            )
            if dup:
                raise IngestionError(
                    "DUPLICATE_KEY",
                    f"{stage}: {dup} duplicated (match_id, innings, innings_ball_num) keys",
                )

    def _post_checks(self, db: Database, infos: dict[str, FileInfo]) -> None:
        for name, tables in cl.COUNT_TABLES.items():
            for table in tables:
                n = int(db.scalar(f"SELECT count(*) FROM {table}"))
                if n != infos[name].row_count:
                    raise IngestionError(
                        "ROW_COUNT_MISMATCH",
                        f"{table}: {n} rows loaded, {name} has {infos[name].row_count}",
                        table_name=table,
                    )
        n_teams = int(db.scalar("SELECT count(*) FROM teams"))
        n_dist = int(db.scalar("SELECT count(DISTINCT team_id) FROM stg_teams"))
        if n_teams != n_dist:
            raise IngestionError("ROW_COUNT_MISMATCH", f"teams {n_teams} != distinct {n_dist}")

    def _write_lineage(self, db: Database, run_id: int, infos: dict[str, FileInfo]) -> None:
        for name, info in infos.items():
            spec = info.spec
            note = spec.note if info.exists else f"{spec.note} (file not found)"
            db.execute(
                "INSERT INTO dataset_lineage (run_id, file_name, file_path, sha256, size_bytes, "
                "row_count, column_count, role, target_table, load_status, decision_note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    run_id,
                    name,
                    info.path.as_posix(),
                    info.sha256,
                    info.size_bytes,
                    info.row_count,
                    info.column_count,
                    spec.role,
                    ",".join(spec.target_tables) or None,
                    spec.load_status,
                    note,
                ],
            )

    def _register_model_versions(
        self, db: Database, run_id: int, data_version: str, schema_version: str
    ) -> None:
        s = self.settings
        weight_name = f"weighting-ipl{s.ipl_weight:.2f}-t20i{s.t20i_weight:.2f}"
        rows = [
            (data_version, "DATA_VERSION", "ACTIVE", _json({"basis": "sha256 of source files"})),
            (
                schema_version,
                "SCHEMA_VERSION",
                "ACTIVE",
                _json({"basis": "sha256 of phase2_schema.sql"}),
            ),
            (
                weight_name,
                "WEIGHTING_CONFIG",
                "PROVISIONAL",
                _json(
                    {
                        "ipl_weight": s.ipl_weight,
                        "t20i_weight": s.t20i_weight,
                        "status": "PROVISIONAL",
                        "note": "no calculation performed in Phase 2; sensitivity grid pending",
                    }
                ),
            ),
        ]
        for name, kind, status, cfg in rows:
            db.execute(
                "INSERT INTO model_versions (name, kind, status, config_json, created_by_run_id) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (name) DO NOTHING",
                [name, kind, status, cfg, run_id],
            )
        for metric, formula, inputs, source, evidence, status in METRIC_DEFINITIONS:
            db.execute(
                "INSERT INTO metric_definitions (metric_name, version, formula, input_columns, "
                "source_datasets, evidence, status) VALUES (?, '1.0', ?, ?, ?, ?, ?) "
                "ON CONFLICT (metric_name, version) DO NOTHING",
                [metric, formula, inputs, source, evidence, status],
            )

    # ------------------------------------------------------------------ error rows
    @staticmethod
    def _insert_errors(db: Database, run_id: int, rows: list[dict]) -> None:
        for r in rows:
            db.execute(
                "INSERT INTO ingestion_errors (run_id, severity, error_type, table_name, "
                "source_file, source_row_no, message, raw_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    run_id,
                    r["severity"],
                    r["error_type"],
                    r.get("table_name"),
                    r.get("source_file"),
                    r.get("source_row_no"),
                    r.get("message"),
                    r.get("raw_payload"),
                ],
            )

    def _write_row_warnings(self, db: Database, run_id: int) -> None:
        """Row-level findings, written after COMMIT so they cannot be confused with a rollback."""
        with db.transaction():
            self._insert_errors(db, run_id, self.warnings)
            db.execute(
                f"""INSERT INTO ingestion_errors (run_id, severity, error_type, table_name,
                       source_file, source_row_no, message, raw_payload)
                SELECT {int(run_id)}, 'WARNING', 'DUPLICATE_KEY_PRESERVED', 'match_squads',
                       source_file, source_row_no,
                       'repeated (match_id, team_id, player_id) key; row kept, squad_row_no='
                       || squad_row_no || ' of ' || duplicate_group_size,
                       CAST(to_json({{'match_id': match_id, 'team_id': team_id,
                                     'player_id': player_id}}) AS VARCHAR)
                FROM match_squads WHERE duplicate_key_flag"""
            )
            db.execute(
                f"""INSERT INTO ingestion_errors (run_id, severity, error_type, table_name,
                       source_file, source_row_no, message, raw_payload)
                SELECT {int(run_id)}, 'WARNING', 'ORPHAN_RECORDED_NOT_DROPPED', 'match_squads',
                       source_file, source_row_no,
                       'squad row has no competition_team_player_mapping row for the match '
                       || 'competition and team; row kept',
                       CAST(to_json({{'match_id': match_id, 'team_id': team_id,
                                     'player_id': player_id}}) AS VARCHAR)
                FROM match_squads WHERE NOT mapping_row_exists"""
            )
            for role, col in (("striker", "striker_id"), ("bowler", "bowler_id")):
                db.execute(
                    f"""INSERT INTO ingestion_errors (run_id, severity, error_type, table_name,
                           source_file, source_row_no, message, raw_payload)
                    SELECT {int(run_id)}, 'WARNING', 'ORPHAN_RECORDED_NOT_DROPPED', 'deliveries',
                           d.source_file, d.source_row_no,
                           '{role} is not in the match squad (playing_eleven); row kept',
                           CAST(to_json({{'match_id': d.match_id, 'innings': d.innings_number,
                                         'innings_ball_num': d.innings_ball_num,
                                         '{col}': d.{col}}}) AS VARCHAR)
                    FROM deliveries d
                    WHERE d.{col} IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM match_squads s
                        WHERE s.match_id = d.match_id AND s.player_id = d.{col})"""
                )

    def _write_errors_csv(self, db: Database, run_id: int) -> None:
        path = self.settings.ingestion_errors_csv
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = db.query(
            f"SELECT {', '.join(ERROR_COLUMNS)} FROM ingestion_errors WHERE run_id = ? "
            "ORDER BY error_id",
            [run_id],
        )
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(ERROR_COLUMNS)
            w.writerows(rows)
