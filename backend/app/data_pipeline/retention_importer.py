"""Retention / release list importer (CSV and XLSX) with a manual-review queue.

Availability is context only. Nothing here feeds a score, rank, eligibility gate or capped status,
and retained players stay in every historical training and analysis table: retention only changes
the final availability-aware candidate outputs (see ``availability_outputs``).

Rules enforced here:
* statuses are exactly RETAINED, RELEASED, TRADED, AUCTION_AVAILABLE, UNKNOWN (default UNKNOWN);
  an unrecognised value becomes UNKNOWN and is flagged, never guessed;
* a stable player id is matched first; a name alone only generates a candidate, accepted only when
  it is a unique exact normalised match in the official ``players`` table and the player has
  appeared for the stated team; anything else goes to the manual-review queue;
* an alias is used only when the alias file carries non-empty evidence, and the use is logged;
* AUCTION_AVAILABLE is never inferred from RELEASED, TRADED, UNKNOWN or an absent row;
* writes go only to ``p7_retention_*`` tables in the exploratory store (never the official
  database); the original file is copied to the raw directory with its SHA-256 in a manifest;
* re-importing a file with a known hash changes nothing; an import is one transaction.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb

from app.core.config import BACKEND_ROOT
from app.phase4.store import OFFICIAL_DB
from app.phase6.store import _check_store
from app.services.pressure_service import EXPLORATORY_DB

STATUSES = ("RETAINED", "RELEASED", "TRADED", "AUCTION_AVAILABLE", "UNKNOWN")
VERIFICATIONS = ("OFFICIAL_VERIFIED", "SINGLE_SOURCE", "UNVERIFIED")
# Explicit spelling variants only; everything else is UNKNOWN plus a flag.
STATUS_ALIASES = {
    "RETAINED": "RETAINED",
    "RETAIN": "RETAINED",
    "RELEASED": "RELEASED",
    "RELEASE": "RELEASED",
    "TRADED": "TRADED",
    "TRADE": "TRADED",
    "AUCTION_AVAILABLE": "AUCTION_AVAILABLE",
    "UNKNOWN": "UNKNOWN",
}
COLUMN_ALIASES = {
    "player_name": "player",
    "player": "player",
    "name": "player",
    "player_id": "player_id",
    "id": "player_id",
    "team": "team",
    "franchise": "team",
    "status": "status",
    "source": "source",
    "reference": "source",
    "source_reference": "source",
    "source/reference": "source",
    "notes": "notes",
    "note": "notes",
}
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "retention"
REPORTS_DIR = BACKEND_ROOT / "data" / "reports"
SQUAD_CSV = Path("d:/Data/ipl squad.csv")
ALIAS_CSV = BACKEND_ROOT / "config" / "retention_aliases.csv"
MAX_BYTES = 10 * 1024 * 1024
TABLES = (
    "p7_retention_imports",
    "p7_retention_rows",
    "p7_retention_review",
    "p7_retention_resolution_log",
)
REVIEW_COLUMNS = (
    "review_id", "import_id", "row_number", "raw_player_name", "raw_player_id", "team",
    "raw_status", "reason", "candidates", "state", "resolver", "evidence", "resolved_at",
    "resolved_player_id",
)  # fmt: skip


class RetentionImportError(ValueError):
    """The file cannot be read as a retention list (format, columns, size, parameters)."""


def norm_key(value: Any) -> str:
    """Name/team key: NFKD, no accents, casefold, dots dropped, hyphens/underscores as spaces."""
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    s = s.replace(".", "").replace("-", " ").replace("_", " ")
    return " ".join(s.split())


def clean_text(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- reference data
@dataclass
class Reference:
    """Identity data used for matching (read-only copy of the official ``players`` table)."""

    names: dict[int, set[str]] = field(default_factory=dict)  # id -> normalised names
    display: dict[int, str] = field(default_factory=dict)
    name_index: dict[str, set[int]] = field(default_factory=dict)
    player_teams: dict[int, set[str]] = field(default_factory=dict)  # id -> normalised teams
    franchises: dict[str, str] = field(default_factory=dict)  # normalised -> canonical
    aliases: dict[str, list[tuple[int, str]]] = field(default_factory=dict)

    def add_player(self, pid: int, name: str, variants: list[str] | None = None) -> None:
        self.display[pid] = name
        keys = {norm_key(name), *(norm_key(v) for v in (variants or []))} - {""}
        self.names[pid] = keys
        for k in keys:
            self.name_index.setdefault(k, set()).add(pid)


def load_reference(
    official_db: Path | str = OFFICIAL_DB,
    squad_csv: Path | str = SQUAD_CSV,
    alias_csv: Path | str = ALIAS_CSV,
) -> Reference:
    """Build the reference from the official database (read-only) and the squad team list."""
    ref = Reference()
    con = duckdb.connect(str(official_db), read_only=True)
    try:
        for pid, name, variants in con.execute(
            "SELECT player_id, player_name, name_variants FROM players"
        ).fetchall():
            try:
                vs = json.loads(variants) if variants else []
            except ValueError:
                vs = []
            ref.add_player(int(pid), str(name), [str(v) for v in vs])
        for pid, team in con.execute(
            "SELECT DISTINCT m.player_id, t.team_name FROM player_competition_mapping m "
            "JOIN teams t ON t.team_id = m.team_id"
        ).fetchall():
            ref.player_teams.setdefault(int(pid), set()).add(norm_key(team))
    finally:
        con.close()
    if Path(squad_csv).is_file():
        with open(squad_csv, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                t = clean_text(r.get("team_name"))
                if t:
                    ref.franchises[norm_key(t)] = t
    ref.aliases = load_aliases(alias_csv)
    return ref


def load_aliases(path: Path | str) -> dict[str, list[tuple[int, str]]]:
    """Alias rows (alias, player_id, evidence). A row without evidence is ignored."""
    out: dict[str, list[tuple[int, str]]] = {}
    p = Path(path)
    if not p.is_file():
        return out
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            alias, pid, ev = (
                norm_key(r.get("alias")),
                clean_text(r.get("player_id")),
                clean_text(r.get("evidence")),
            )
            if alias and pid.isdigit() and ev:
                out.setdefault(alias, []).append((int(pid), ev))
    return out


# --------------------------------------------------------------------------- reading files
def read_table(path: Path | str, sheet: str | None = None) -> list[dict[str, str]]:
    """Read CSV or XLSX (first sheet unless ``sheet``) into rows with canonical column names."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".csv":
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = [list(r) for r in csv.reader(f)]
    elif ext == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(p, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet else wb.worksheets[0]
            rows = [
                ["" if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)
            ]
        except KeyError as exc:
            raise RetentionImportError(f"sheet not found: {sheet}") from exc
        finally:
            wb.close()
    else:
        raise RetentionImportError(f"unsupported file type '{ext}' (use .csv or .xlsx)")
    rows = [r for r in rows if any(clean_text(c) for c in r)]
    if not rows:
        raise RetentionImportError("the file has no rows")
    header = [COLUMN_ALIASES.get(clean_text(h).casefold().replace(" ", "_"), "") for h in rows[0]]
    if "player" not in header and "player_id" not in header:
        raise RetentionImportError("the file needs a player (name) or player_id column")
    out: list[dict[str, str]] = []
    for r in rows[1:]:
        rec = {k: "" for k in ("player", "player_id", "team", "status", "source", "notes")}
        for h, c in zip(header, r, strict=False):
            if h and not rec[h]:
                rec[h] = clean_text(c)
        out.append(rec)
    return out


# --------------------------------------------------------------------------- row processing
def _team_ctx(ref: Reference, pid: int, team_key: str) -> str:
    if not team_key:
        return "NO_TEAM_GIVEN"
    return (
        "SEEN_WITH_TEAM" if team_key in ref.player_teams.get(pid, set()) else "NOT_SEEN_WITH_TEAM"
    )


def process_rows(
    rows: list[dict[str, str]], ref: Reference, default_source: str = ""
) -> list[dict[str, Any]]:
    """Normalise and map each row. Pure function: no I/O."""
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        flags: list[str] = []
        raw_status = r["status"]
        key = raw_status.strip().upper().replace(" ", "_").replace("-", "_")
        if not key:
            status = "UNKNOWN"
        elif key in STATUS_ALIASES:
            status = STATUS_ALIASES[key]
        else:
            status = "UNKNOWN"
            flags.append("STATUS_UNRECOGNISED")
        team_raw = r["team"]
        tk = norm_key(team_raw)
        team = ref.franchises.get(tk, team_raw)
        if team_raw and tk not in ref.franchises and ref.franchises:
            flags.append("TEAM_NOT_RECOGNISED")
        if not team_raw and status in ("RETAINED", "TRADED"):
            flags.append("TEAM_MISSING")
        source = r["source"] or default_source
        if not source:
            flags.append("NO_SOURCE")

        res: dict[str, Any] = {
            "row_number": i, "raw_player_name": r["player"], "raw_player_id": r["player_id"],
            "norm_name": norm_key(r["player"]), "player_id": None, "team": team,
            "raw_status": raw_status, "status": status, "source": source, "notes": r["notes"],
            "mapping_status": "UNMATCHED", "match_method": "", "team_context": "",
            "alias_evidence": "", "review_reason": "", "candidates": [],
        }  # fmt: skip
        _map_identity(res, r, ref, tk)
        res["flags"] = flags
        out.append(res)
    _mark_duplicates(out)
    return out


def _map_identity(res: dict[str, Any], r: dict[str, str], ref: Reference, tk: str) -> None:
    def review(status: str, reason: str, cands: list[int]) -> None:
        res["mapping_status"], res["review_reason"] = status, reason
        res["candidates"] = [
            {"player_id": c, "name": ref.display.get(c, "")} for c in sorted(cands)
        ]

    raw_id, nk = r["player_id"], res["norm_name"]
    if raw_id:
        if not raw_id.isdigit():
            return review("UNMATCHED", "ID_INVALID", [])
        pid = int(raw_id)
        if pid not in ref.names:
            return review("UNMATCHED", "ID_NOT_FOUND", sorted(ref.name_index.get(nk, set())))
        if nk and nk not in ref.names[pid]:
            return review("AMBIGUOUS", "ID_NAME_MISMATCH", [pid, *ref.name_index.get(nk, set())])
        res.update(player_id=pid, mapping_status="MAPPED", match_method="PLAYER_ID",
                   team_context=_team_ctx(ref, pid, tk))  # fmt: skip
        return
    if not nk:
        return review("UNMATCHED", "NO_IDENTITY", [])
    cands = ref.name_index.get(nk, set())
    if len(cands) > 1:
        return review("AMBIGUOUS", "NAME_SHARED_BY_SEVERAL_PLAYERS", sorted(cands))
    if len(cands) == 1:
        pid = next(iter(cands))
        ctx = _team_ctx(ref, pid, tk)
        res["team_context"] = ctx
        if ctx == "SEEN_WITH_TEAM":
            res.update(player_id=pid, mapping_status="MAPPED", match_method="NAME_EXACT")
            return None
        return review("AMBIGUOUS", f"NAME_UNIQUE_TEAM_NOT_CONFIRMED:{ctx}", [pid])
    hits = {p: ev for p, ev in ref.aliases.get(nk, [])}
    if len(hits) == 1:
        pid, ev = next(iter(hits.items()))
        if pid in ref.names:
            res.update(player_id=pid, mapping_status="MAPPED", match_method="ALIAS",
                       alias_evidence=ev, team_context=_team_ctx(ref, pid, tk))  # fmt: skip
            return None
    return review("UNMATCHED", "NAME_NOT_FOUND", sorted(hits))


def _mark_duplicates(rows: list[dict[str, Any]]) -> None:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for r in rows:
        k = ("id", r["player_id"]) if r["player_id"] else ("name", r["norm_name"])
        if k[1]:
            groups.setdefault(k, []).append(r)
    for g in groups.values():
        if len(g) > 1:
            kind = "CONFLICTING_STATUS" if len({x["status"] for x in g}) > 1 else "DUPLICATE_ROW"
            for x in g:
                x["flags"].append(kind)


def is_confirmed_available(row: dict[str, Any], authoritative: bool) -> bool:
    """AUCTION_AVAILABLE only: stated by the source, mapped, sourced, authoritative, no conflict."""
    return bool(
        authoritative
        and row["status"] == "AUCTION_AVAILABLE"
        and row["mapping_status"] in ("MAPPED", "RESOLVED_MANUAL")
        and row["player_id"] is not None
        and row["source"]
        and "CONFLICTING_STATUS" not in row["flags"]
        and "STATUS_UNRECOGNISED" not in row["flags"]
    )


# --------------------------------------------------------------------------- store
DDL = (
    """CREATE TABLE IF NOT EXISTS p7_retention_imports (
    import_id INTEGER PRIMARY KEY, file_sha256 VARCHAR UNIQUE NOT NULL, original_name VARCHAR,
    stored_path VARCHAR, file_format VARCHAR, season VARCHAR, snapshot_date DATE, source VARCHAR,
    verification_status VARCHAR NOT NULL, authoritative BOOLEAN NOT NULL, imported_at VARCHAR,
    n_rows INTEGER, n_mapped INTEGER, n_review INTEGER, status_counts VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS p7_retention_rows (
    import_id INTEGER NOT NULL, row_number INTEGER NOT NULL, raw_player_name VARCHAR,
    raw_player_id VARCHAR, norm_name VARCHAR, player_id INTEGER, team VARCHAR, raw_status VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'UNKNOWN' CHECK (status IN
      ('RETAINED','RELEASED','TRADED','AUCTION_AVAILABLE','UNKNOWN')),
    source VARCHAR, notes VARCHAR, mapping_status VARCHAR NOT NULL, match_method VARCHAR,
    team_context VARCHAR, alias_evidence VARCHAR, flags VARCHAR,
    PRIMARY KEY (import_id, row_number))""",
    """CREATE TABLE IF NOT EXISTS p7_retention_review (
    review_id INTEGER PRIMARY KEY, import_id INTEGER NOT NULL, row_number INTEGER NOT NULL,
    raw_player_name VARCHAR, raw_player_id VARCHAR, team VARCHAR, raw_status VARCHAR,
    reason VARCHAR, candidates VARCHAR, state VARCHAR NOT NULL DEFAULT 'OPEN',
    resolver VARCHAR, evidence VARCHAR, resolved_at VARCHAR, resolved_player_id INTEGER)""",
    """CREATE TABLE IF NOT EXISTS p7_retention_resolution_log (
    log_id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL, action VARCHAR NOT NULL,
    player_id INTEGER, resolver VARCHAR NOT NULL, evidence VARCHAR NOT NULL,
    logged_at VARCHAR NOT NULL)""",
)


def _connect(store: Path | str, official_db: Path | str = OFFICIAL_DB, create: bool = True):
    path = _check_store(store, official_db)
    con = duckdb.connect(str(path))
    if create:
        for d in DDL:
            con.execute(d)
    return con


def store_has_imports(store: Path | str) -> bool:
    """True when the store exists and holds at least one import. Never creates anything."""
    p = Path(store)
    if not p.is_file():
        return False
    con = duckdb.connect(str(p), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'p7_retention_imports'"
        ).fetchone()[0]
        return (
            bool(has) and con.execute("SELECT count(*) FROM p7_retention_imports").fetchone()[0] > 0
        )
    finally:
        con.close()


def _summary(results: list[dict[str, Any]], authoritative: bool) -> dict[str, Any]:
    counts = {s: 0 for s in STATUSES}
    maps: dict[str, int] = {}
    flags: dict[str, int] = {}
    for r in results:
        counts[r["status"]] += 1
        maps[r["mapping_status"]] = maps.get(r["mapping_status"], 0) + 1
        for f in r["flags"]:
            flags[f] = flags.get(f, 0) + 1
    return {
        "n_rows": len(results),
        "status_counts": counts,
        "mapping_counts": maps,
        "flag_counts": flags,
        "n_review": sum(1 for r in results if r["review_reason"]),
        "n_confirmed_available": sum(is_confirmed_available(r, authoritative) for r in results),
    }


def import_file(
    path: Path | str,
    *,
    snapshot_date: str,
    source: str = "",
    verification: str = "UNVERIFIED",
    authoritative: bool = False,
    season: str = "",
    sheet: str | None = None,
    dry_run: bool = False,
    store: Path | str = EXPLORATORY_DB,
    raw_dir: Path | str = RAW_DIR,
    reference: Reference | None = None,
    official_db: Path | str = OFFICIAL_DB,
    original_name: str | None = None,
) -> dict[str, Any]:
    """Validate (always) and, unless ``dry_run``, import one retention file transactionally."""
    p = Path(path)
    if not p.is_file():
        raise RetentionImportError(f"file not found: {p}")
    if p.stat().st_size > MAX_BYTES:
        raise RetentionImportError("file larger than 10 MB")
    if verification not in VERIFICATIONS:
        raise RetentionImportError(f"verification must be one of {VERIFICATIONS}")
    try:
        snap = date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise RetentionImportError("snapshot_date must be YYYY-MM-DD") from exc
    if authoritative and verification != "OFFICIAL_VERIFIED":
        raise RetentionImportError("authoritative requires verification OFFICIAL_VERIFIED")
    digest = sha256_file(p)
    ref = reference or load_reference(official_db)
    results = process_rows(read_table(p, sheet), ref, source)
    name = original_name or p.name
    out: dict[str, Any] = {
        "dry_run": dry_run, "file": name, "file_sha256": digest, "snapshot_date": snapshot_date,
        "verification_status": verification, "authoritative": authoritative,
        "rows": results, **_summary(results, authoritative),
    }  # fmt: skip
    already = _existing_import(store, digest)
    out["already_imported"] = already is not None
    if dry_run:
        out.update(status="DRY_RUN", changed=False, import_id=already)
        return out
    if already is not None:
        out.update(status="ALREADY_IMPORTED", changed=False, import_id=already)
        return out

    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    stored = raw / f"{digest[:12]}_{re.sub(r'[^A-Za-z0-9._-]', '_', name)}"
    copied = not stored.exists()
    if copied:
        shutil.copyfile(p, stored)
    con = _connect(store, official_db)
    try:
        con.execute("BEGIN")
        iid = int(
            con.execute("SELECT coalesce(max(import_id),0)+1 FROM p7_retention_imports").fetchone()[
                0
            ]
        )
        con.execute(
            "INSERT INTO p7_retention_imports VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [iid, digest, name, str(stored), p.suffix.lower().lstrip("."), season, snap, source,
             verification, authoritative, datetime.now(UTC).isoformat(), out["n_rows"],
             sum(1 for r in results if r["mapping_status"] == "MAPPED"), out["n_review"],
             json.dumps(out["status_counts"])],
        )  # fmt: skip
        rid = int(
            con.execute("SELECT coalesce(max(review_id),0)+1 FROM p7_retention_review").fetchone()[
                0
            ]
        )
        for r in results:
            con.execute(
                "INSERT INTO p7_retention_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [iid, r["row_number"], r["raw_player_name"], r["raw_player_id"], r["norm_name"],
                 r["player_id"], r["team"], r["raw_status"], r["status"], r["source"], r["notes"],
                 r["mapping_status"], r["match_method"], r["team_context"], r["alias_evidence"],
                 json.dumps(r["flags"])],
            )  # fmt: skip
            if r["review_reason"]:
                con.execute(
                    "INSERT INTO p7_retention_review (review_id, import_id, row_number, "
                    "raw_player_name, raw_player_id, team, raw_status, reason, candidates) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    [rid, iid, r["row_number"], r["raw_player_name"], r["raw_player_id"],
                     r["team"], r["raw_status"], r["review_reason"], json.dumps(r["candidates"])],
                )  # fmt: skip
                rid += 1
        con.execute("COMMIT")
    except BaseException:
        try:
            con.execute("ROLLBACK")
        finally:
            con.close()
        if copied and stored.exists():
            stored.unlink()
        raise
    con.close()
    _append_manifest(raw, name, stored, digest, iid, snapshot_date, source, verification)
    out.update(status="IMPORTED", changed=True, import_id=iid, stored_path=str(stored))
    return out


def _existing_import(store: Path | str, digest: str) -> int | None:
    p = Path(store)
    if not p.is_file():
        return None
    con = duckdb.connect(str(p), read_only=True)
    try:
        if not con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name='p7_retention_imports'"
        ).fetchone()[0]:
            return None
        r = con.execute(
            "SELECT import_id FROM p7_retention_imports WHERE file_sha256=?", [digest]
        ).fetchone()
        return int(r[0]) if r else None
    finally:
        con.close()


def _append_manifest(raw: Path, name, stored, digest, iid, snap, source, verification) -> None:
    mp = raw / "import_manifest.json"
    entries = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else []
    entries.append({
        "import_id": iid, "original_name": name, "stored_file": stored.name, "sha256": digest,
        "snapshot_date": snap, "source": source, "verification_status": verification,
        "imported_at": datetime.now(UTC).isoformat(),
    })  # fmt: skip
    mp.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- manual review
def list_review(store: Path | str, state: str | None = "OPEN") -> list[dict[str, Any]]:
    if not Path(store).is_file() or not store_has_imports(store):
        return []
    con = duckdb.connect(str(store), read_only=True)
    try:
        q = f"SELECT {', '.join(REVIEW_COLUMNS)} FROM p7_retention_review"
        cur = con.execute(q + (" WHERE state = ?" if state else "") + " ORDER BY review_id",
                          [state] if state else [])  # fmt: skip
        rows = [dict(zip(REVIEW_COLUMNS, r, strict=True)) for r in cur.fetchall()]
    finally:
        con.close()
    for r in rows:
        r["candidates"] = json.loads(r["candidates"] or "[]")
    return rows


def resolve_review(
    store: Path | str,
    review_id: int,
    *,
    resolver: str,
    evidence: str,
    player_id: int | None = None,
    dismiss: bool = False,
    reference: Reference | None = None,
    official_db: Path | str = OFFICIAL_DB,
) -> dict[str, Any]:
    """Resolve a review item to a player id (or dismiss it), logging resolver and evidence."""
    resolver, evidence = clean_text(resolver), clean_text(evidence)
    if not resolver or not evidence:
        raise RetentionImportError("resolver and evidence are required")
    if not dismiss:
        if player_id is None:
            raise RetentionImportError("player_id is required to resolve (or use dismiss)")
        ref = reference or load_reference(official_db)
        if int(player_id) not in ref.names:
            raise RetentionImportError(
                f"player_id {player_id} is not in the official players table"
            )
    con = _connect(store, official_db)
    try:
        con.execute("BEGIN")
        r = con.execute(
            "SELECT import_id, row_number, state FROM p7_retention_review WHERE review_id=?",
            [review_id],
        ).fetchone()
        if r is None:
            raise RetentionImportError(f"review item {review_id} not found")
        if r[2] != "OPEN":
            raise RetentionImportError(f"review item {review_id} is already {r[2]}")
        now = datetime.now(UTC).isoformat()
        action = "DISMISSED" if dismiss else "RESOLVED"
        pid = None if dismiss else int(player_id)
        con.execute(
            "UPDATE p7_retention_review SET state=?, resolver=?, evidence=?, resolved_at=?, "
            "resolved_player_id=? WHERE review_id=?",
            [action, resolver, evidence, now, pid, review_id],
        )
        if not dismiss:
            con.execute(
                "UPDATE p7_retention_rows SET player_id=?, mapping_status='RESOLVED_MANUAL', "
                "match_method='MANUAL' WHERE import_id=? AND row_number=?",
                [pid, r[0], r[1]],
            )
        lid = int(
            con.execute(
                "SELECT coalesce(max(log_id),0)+1 FROM p7_retention_resolution_log"
            ).fetchone()[0]
        )
        con.execute(
            "INSERT INTO p7_retention_resolution_log VALUES (?,?,?,?,?,?,?)",
            [lid, review_id, action, pid, resolver, evidence, now],
        )
        con.execute("COMMIT")
    except BaseException:
        try:
            con.execute("ROLLBACK")
        finally:
            con.close()
        raise
    con.close()
    return {"review_id": review_id, "state": action, "player_id": pid, "resolver": resolver}


def export_review_csv(store: Path | str, path: Path | str) -> int:
    rows = list_review(store, state=None)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(REVIEW_COLUMNS)
        for r in rows:
            r = {**r, "candidates": json.dumps(r["candidates"])}
            w.writerow([r[c] if r[c] is not None else "" for c in REVIEW_COLUMNS])
    return len(rows)


# --------------------------------------------------------------------------- availability
def latest_rows(store: Path | str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Rows of the latest snapshot import (highest snapshot_date, then import_id)."""
    if not store_has_imports(store):
        return None, []
    con = duckdb.connect(str(store), read_only=True)
    try:
        imp = con.execute(
            "SELECT import_id, snapshot_date, source, verification_status, authoritative, "
            "original_name, file_sha256 FROM p7_retention_imports "
            "ORDER BY snapshot_date DESC, import_id DESC LIMIT 1"
        ).fetchone()
        cols = ("player_id", "team", "status", "source", "mapping_status", "flags", "row_number")
        rows = con.execute(
            f"SELECT {', '.join(cols)} FROM p7_retention_rows WHERE import_id=? ORDER BY row_number",
            [imp[0]],
        ).fetchall()
    finally:
        con.close()
    meta = dict(zip(("import_id", "snapshot_date", "source", "verification_status",
                     "authoritative", "original_name", "file_sha256"), imp, strict=True))  # fmt: skip
    recs = [dict(zip(cols, r, strict=True)) for r in rows]
    for r in recs:
        r["flags"] = json.loads(r["flags"] or "[]")
    return meta, recs


def effective_status(
    store: Path | str,
) -> tuple[dict[str, Any] | None, dict[int, dict[str, Any]], int]:
    """Per player status from the latest import: (meta, {player_id: info}, unresolved_rows)."""
    meta, recs = latest_rows(store)
    if meta is None:
        return None, {}, 0
    per: dict[int, dict[str, Any]] = {}
    unresolved = 0
    for r in recs:
        if r["player_id"] is None or r["mapping_status"] not in ("MAPPED", "RESOLVED_MANUAL"):
            unresolved += 1
            continue
        d = per.setdefault(int(r["player_id"]), {"statuses": set(), "team": "", "rows": []})
        d["statuses"].add(r["status"])
        d["team"] = d["team"] or r["team"] or ""
        d["rows"].append(r)
    for d in per.values():
        d["status"] = next(iter(d["statuses"])) if len(d["statuses"]) == 1 else "CONFLICT"
        d["confirmed_available"] = (
            d["status"] == "AUCTION_AVAILABLE"
            and len(d["rows"]) >= 1
            and all(is_confirmed_available(r, bool(meta["authoritative"])) for r in d["rows"])
        )
    return meta, per, unresolved
