"""Preservation checks: hashes of official CSVs, official tables, the DB file and Cricsheet dirs."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.database import REPLACEABLE_TABLES, Database, connect


class IntegrityError(RuntimeError):
    """Raised when official data changed between two snapshots."""


def open_official_readonly(db_path: Path | str) -> Database:
    """Open the official DuckDB file read-only; any write attempt raises."""
    return connect(db_path, read_only=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_content_hash(db: Database, table: str) -> dict[str, Any]:
    """Order-independent content hash: row count plus bit_xor of the per-row hash."""
    try:
        count, xor = db.query(f"SELECT count(*), bit_xor(hash(t)) FROM {table} t")[0]
        return {"rows": int(count), "content_hash": None if xor is None else str(xor)}
    except Exception:  # fall back to a sha256 over ordered rows
        rows = db.query(f"SELECT * FROM {table} ORDER BY ALL")
        h = hashlib.sha256()
        for row in rows:
            h.update(repr(row).encode("utf-8"))
        return {"rows": len(rows), "content_hash": h.hexdigest()}


def cricsheet_manifest(directory: Path) -> dict[str, Any]:
    if not directory.is_dir():
        return {"files": 0, "bytes": 0, "sha256": None}
    lines, total = [], 0
    for p in sorted(directory.iterdir(), key=lambda q: q.name):
        if p.is_file():
            st = p.stat()
            total += st.st_size
            lines.append(f"{p.name}:{st.st_size}:{st.st_mtime_ns}")
    return {
        "files": len(lines),
        "bytes": total,
        "sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
    }


def snapshot_official(
    db_path: Path | str,
    data_root: Path | str,
    cricsheet_dirs: Iterable[str] = (),
    cricsheet_root: Path | str | None = None,
    tables: Iterable[str] = REPLACEABLE_TABLES,
    include_db_file_hash: bool = True,
) -> dict[str, Any]:
    """Snapshot top-level CSVs, official table contents, the DB file and Cricsheet manifests."""
    data_root = Path(data_root)
    snap: dict[str, Any] = {
        "csv_sha256": {p.name: sha256_file(p) for p in sorted(data_root.glob("*.csv"))},
        "tables": {},
        "db_file_sha256": None,
        "cricsheet": {},
    }
    if Path(db_path).exists():
        db = open_official_readonly(db_path)
        try:
            for t in tables:
                if db.table_exists(t):
                    snap["tables"][t] = table_content_hash(db, t)
        finally:
            db.close()
        if include_db_file_hash:
            snap["db_file_sha256"] = sha256_file(Path(db_path))
    root = Path(cricsheet_root) if cricsheet_root else data_root
    for name in cricsheet_dirs:
        snap["cricsheet"][name] = cricsheet_manifest(root / name)
    return snap


def snapshot_from_settings(settings: Settings, db_path: Path | str | None = None) -> dict:
    return snapshot_official(
        db_path or settings.duckdb_path,
        settings.data_root,
        settings.cricsheet_dirs,
        settings.cricsheet_root,
    )


def _diff(a: Any, b: Any, path: str, out: dict[str, Any]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _diff(a.get(k), b.get(k), f"{path}/{k}", out)
    elif a != b:
        out[path] = {"before": a, "after": b}


def assert_unchanged(before: dict, after: dict, raise_on_diff: bool = False) -> dict[str, Any]:
    """Return the differences between two snapshots (empty dict when identical)."""
    out: dict[str, Any] = {}
    _diff(before, after, "", out)
    if out and raise_on_diff:
        raise IntegrityError(f"official data changed: {sorted(out)[:10]}")
    return out
