"""Methodology lock manifest for the experimental TRAIN+VALIDATION refit.

The lock freezes the *choices* the refit uses: config files, the provisional pressure definition,
working-pool thresholds, shrinkage choice, restrictions, features and the code that fits them. It
does NOT validate any of them. The manifest is written only by ``scripts/phase5_methodology_lock.py``
(with ``--confirm-lock``); no other module calls ``write_lock``. ``verify_lock`` recomputes every
hash and raises ``LockDriftError`` when anything differs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

from app.phase4.baseline import BASELINE_VERSION, STREAMS
from app.phase4.engine import PRIMARY
from app.phase5.constants import (
    CLASSIFICATION_V2_VERSION,
    CONFIG_DIR,
    FROZEN_CHOICES,
    PROVISIONAL_DEFINITION,
    REPORTS_DIR,
    SENSITIVITY_DEFINITIONS,
    STATUS,
)
from app.phase5.lockguard import PHASE5_LOCK_LOG, file_sha256, read_events
from app.services.pressure_service import EXPLORATORY_DB

BACKEND = CONFIG_DIR.parent
LOCK_CONFIG = CONFIG_DIR / "phase5_methodology_lock_v1.json"
LOCK_PATH = REPORTS_DIR / "phase5_methodology_lock.json"
PRERUN_HASHES = BACKEND.parent / ".agents" / "tasks" / "phase5_prerun_hashes.json"
MANIFEST_VERSION = "phase5_methodology_lock_manifest_v1"
LABEL = "EXPERIMENTAL_LOCK"

REQUIRED = "REQUIRED_FOR_EXPERIMENTAL_LOCK"
GATE = "PUBLICATION_GATE"
DECISION = "USER_DECISION"
PASS, FAIL, PENDING = "PASS", "FAIL", "USER_APPROVAL_PENDING"


class LockError(RuntimeError):
    """Base class for lock problems."""


class LockMissingError(LockError):
    """The lock manifest does not exist (or is unreadable)."""


class LockDriftError(LockError):
    """A locked file, choice or code hash differs from the manifest."""


def load_lock_config(path: Path | str = LOCK_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------- what is locked
def locked_files(cfg: dict[str, Any] | None = None) -> dict[str, Path]:
    cfg = cfg or load_lock_config()
    out = {f"config/{n}": CONFIG_DIR / n for n in cfg["locked_config_files"]}
    out.update({f"reports/{n}": REPORTS_DIR / n for n in cfg["locked_report_files"]})
    out["config/phase5_methodology_lock_v1.json"] = LOCK_CONFIG
    return out


def locked_code(cfg: dict[str, Any] | None = None) -> list[Path]:
    cfg = cfg or load_lock_config()
    files = [BACKEND / n for n in cfg["locked_code_files"]]
    files.append(Path(__file__).resolve())
    return sorted(set(files))


def hash_files(files: dict[str, Path]) -> dict[str, str]:
    missing = [k for k, p in files.items() if not Path(p).is_file()]
    if missing:
        raise LockMissingError(f"locked input files are missing: {missing}")
    return {k: file_sha256(p) for k, p in sorted(files.items())}


def code_sha256(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def gather_choices(
    frozen_path: Path | str = FROZEN_CHOICES, store: Path | str = EXPLORATORY_DB
) -> dict[str, Any]:
    """The analytical choices the refit applies, read from the frozen Phase 4 choices."""
    frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
    cfg = load_lock_config()
    strict_enabled: bool | None = None
    try:
        con = duckdb.connect(str(store), read_only=True)
        try:
            strict_enabled = bool(
                con.execute("SELECT enabled FROM p5_strict_uncapped_capability").fetchone()[0]
            )
        finally:
            con.close()
    except Exception:
        strict_enabled = None
    working_pools = {
        k: {
            "threshold_balls": v["analysis"]["threshold_balls"],
            "window_ratio": v["analysis"]["wr"],
            "label": v["analysis"]["label"],
            "phase4_status": v["decision"]["status"],
        }
        for k, v in sorted(frozen["eligibility"].items())
    }
    return {
        "definition": {
            "id": PROVISIONAL_DEFINITION,
            "status": "PROVISIONAL_NOT_VALIDATED",
            "basis": "rule winner only; not shown superior",
            "sensitivity_alternatives": list(SENSITIVITY_DEFINITIONS),
            "quantile_level_locked": True,
            "numeric_cutoffs": "refit on TRAIN+VALIDATION at the locked quantile level",
        },
        "working_pools": working_pools,
        "working_pool_status": "THRESHOLD_NOT_VALIDATED (internal exploratory use only)",
        "shrinkage": {"config": frozen["shrinkage"]["config"], "choice_data": "TRAIN+VALIDATION"},
        "features": {
            "streams": [list(s) for s in STREAMS],
            "primary_stream": {k: list(v) for k, v in PRIMARY.items()},
            "baseline_version": BASELINE_VERSION,
        },
        "restrictions": "config/data_quality_restrictions_v1.json (hash in files)",
        "classification_version": CLASSIFICATION_V2_VERSION,
        "strict_uncapped_enabled": strict_enabled,
        "refit": {
            "id": cfg["refit_id"],
            "n_boot": cfg["refit_n_boot"],
            "seed": cfg["refit_seed"],
            "fit_window": "TRAIN+VALIDATION",
            "test_rows": "never loaded",
        },
        "validation_claims": {
            "methodology_validated": False,
            "pressure_definition_validated": False,
            "working_pools_validated": False,
        },
    }


def build_lock_content(
    files: dict[str, Path] | None = None,
    code: list[Path] | None = None,
    choices: dict[str, Any] | None = None,
    store: Path | str = EXPLORATORY_DB,
) -> dict[str, Any]:
    """Everything that the lock hash covers (no timestamps; deterministic)."""
    return {
        "files": hash_files(files if files is not None else locked_files()),
        "code_sha256": code_sha256(code if code is not None else locked_code()),
        "choices": choices if choices is not None else gather_choices(store=store),
    }


def lock_hash(content: dict[str, Any]) -> str:
    return canonical_hash(content)


# ---------------------------------------------------------------- pre-lock checklist
def _item(item_id: str, kind: str, status: str, detail: str) -> dict[str, str]:
    return {"id": item_id, "kind": kind, "status": status, "detail": detail}


def _prerun(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def pre_lock_checklist(
    reports: Path | str = REPORTS_DIR,
    store: Path | str = EXPLORATORY_DB,
    prerun_path: Path | str = PRERUN_HASHES,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the chunk 1-4 outputs and record, item by item, what passes and what fails.

    ``REQUIRED_FOR_EXPERIMENTAL_LOCK`` items must pass before the explicit lock script writes a
    manifest. ``PUBLICATION_GATE`` items are recorded honestly and are expected to fail until the
    user supplies the missing evidence; they never block the experimental lock and never turn into
    a validation claim. ``USER_DECISION`` items are always pending.
    """
    reports, store = Path(reports), Path(store)
    cfg = cfg or load_lock_config()
    items: list[dict[str, str]] = []
    # ---- required items
    missing = [n for n in cfg["required_reports"] if not _nonempty(reports / n)]
    items.append(
        _item(
            "investigation_reports_present",
            REQUIRED,
            FAIL if missing else PASS,
            f"missing or empty: {missing}"
            if missing
            else f"{len(cfg['required_reports'])} present",
        )
    )
    ui = reports / "phase5_unresolved_issues.md"
    items.append(
        _item(
            "unresolved_issues_present",
            REQUIRED,
            PASS if _nonempty(ui) else FAIL,
            "phase5_unresolved_issues.md"
            + ("" if _nonempty(ui) else " is missing (run phase5_reports)"),
        )
    )
    dv = [reports / "phase5_test_set_manifest.json", reports / "phase5_t20i_date_verification.json"]
    items.append(
        _item(
            "date_verification_manifest_present",
            REQUIRED,
            PASS if all(_nonempty(p) for p in dv) else FAIL,
            "test-set manifest and date-verification summary "
            + ("present" if all(_nonempty(p) for p in dv) else "missing"),
        )
    )
    strict, strict_detail = None, "table p5_strict_uncapped_capability not readable"
    try:
        con = duckdb.connect(str(store), read_only=True)
        try:
            strict = bool(
                con.execute("SELECT enabled FROM p5_strict_uncapped_capability").fetchone()[0]
            )
            strict_detail = f"recorded; strict uncapped enabled = {strict}"
        finally:
            con.close()
    except Exception:
        pass
    items.append(
        _item(
            "strict_uncapped_capability_recorded",
            REQUIRED,
            PASS if strict is not None else FAIL,
            strict_detail,
        )
    )
    gates = _read_gates(reports)
    items.append(
        _item(
            "publication_gates_evaluated",
            REQUIRED,
            PASS if gates else FAIL,
            "phase5_publication_gates.json present" if gates else "gate report missing",
        )
    )
    pre = _prerun(Path(prerun_path))
    if pre is None:
        for i in ("phase4_outputs_unchanged", "official_data_unchanged"):
            items.append(_item(i, REQUIRED, FAIL, "pre-run hash record not available"))
    else:
        changed = sorted(
            Path(k).name for k, v in pre["phase4_reports"].items() if _sha(k) != str(v).lower()
        )
        items.append(
            _item(
                "phase4_outputs_unchanged",
                REQUIRED,
                FAIL if changed else PASS,
                f"{len(pre['phase4_reports'])} phase4 report files compared"
                + (f"; changed: {changed}" if changed else "; all identical"),
            )
        )
        official = {
            **{k: v for k, v in pre["duckdb"].items() if Path(k).name == "superr.duckdb"},
            **pre["source_csvs"],
            **pre["config_csvs"],
        }
        bad = sorted(Path(k).name for k, v in official.items() if _sha(k) != str(v).lower())
        items.append(
            _item(
                "official_data_unchanged",
                REQUIRED,
                FAIL if bad else PASS,
                f"{len(official)} official files compared"
                + (f"; changed: {bad}" if bad else "; all identical"),
            )
        )
    ev4 = [e.get("event") for e in read_events(reports / "phase4_lock_log.json")]
    items.append(
        _item(
            "phase4_lock_log_intact",
            REQUIRED,
            PASS if ev4 == ["FREEZE", "OPEN", "CLOSE"] else FAIL,
            f"events {ev4} (TEST was opened once in Phase 4 and never again)",
        )
    )
    ev5 = [e.get("event") for e in read_events(PHASE5_LOCK_LOG)]
    items.append(
        _item(
            "phase5_test_lock_not_opened",
            REQUIRED,
            FAIL if "OPEN" in ev5 else PASS,
            f"phase5 lock log events {ev5}",
        )
    )
    # ---- publication gates: recorded as they are
    status_cfg = json.loads((CONFIG_DIR / "phase5_methodology_status_v1.json").read_text("utf-8"))
    validated = bool(status_cfg.get("validated"))
    items.append(
        _item(
            "methodology_validated",
            GATE,
            PASS if validated else FAIL,
            "validated=true set by a human" if validated else "validated=false: NOT validated",
        )
    )
    for g in gates.get("gate_results", []):
        items.append(
            _item(f"gate:{g['gate_id']}", GATE, PASS if g["passed"] else FAIL, g["detail"])
        )
    items.append(
        _item(
            "strict_uncapped_enabled",
            GATE,
            PASS if strict else FAIL,
            "no authoritative cap source keyed by player_id; strict uncapped stays disabled",
        )
    )
    # ---- user decisions: always pending
    for i, d in [
        ("decision:official_rankings", "publishing an official Top 10"),
        ("decision:official_ml_training", "official ML training"),
        ("decision:validate_primary_definition", "calling any|q0.75 validated"),
        ("decision:validate_working_pools", "validating the working-pool thresholds"),
        ("decision:official_t20i_dates", "supplying official match-level T20I dates"),
        (
            "decision:authoritative_cap_source",
            "supplying an authoritative cap source with player ids",
        ),
    ]:
        items.append(_item(i, DECISION, PENDING, f"needs the user: {d}"))
    required_ok = all(x["status"] == PASS for x in items if x["kind"] == REQUIRED)
    gate_fail = [x["id"] for x in items if x["kind"] == GATE and x["status"] == FAIL]
    return {
        "label": LABEL,
        "status": STATUS,
        "items": items,
        "required_all_pass": required_ok,
        "failing_publication_checks": gate_fail,
        "pending_user_decisions": [x["id"] for x in items if x["kind"] == DECISION],
        "methodology_validated": validated,
        "publication_ready": bool(not gate_fail and validated),
    }


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def _sha(p: Path | str) -> str | None:
    p = Path(p)
    return file_sha256(p) if p.is_file() else None


def _read_gates(reports: Path) -> dict[str, Any]:
    p = reports / "phase5_publication_gates.json"
    if not p.is_file():
        return {}
    scen = next(iter(json.loads(p.read_text(encoding="utf-8")).get("scenarios", {}).values()), {})
    return {"failing": scen.get("failing_gates", []), "gate_results": scen.get("gate_results", [])}


# ---------------------------------------------------------------- manifest I/O
def build_manifest(
    content: dict[str, Any] | None = None, checklist: dict[str, Any] | None = None
) -> dict[str, Any]:
    content = content if content is not None else build_lock_content()
    return {
        "manifest_version": MANIFEST_VERSION,
        "label": LABEL,
        "status": STATUS,
        "validated": False,
        "statement": load_lock_config()["statement"],
        "lock_hash": lock_hash(content),
        "content": content,
        "pre_lock_checklist": checklist,
    }


def write_lock(path: Path | str, manifest: dict[str, Any]) -> Path:
    """Write the manifest. Called only by ``scripts/phase5_methodology_lock.py``."""
    from app.analytics.reporting import write_json_deterministic

    p = Path(path)
    write_json_deterministic(p, manifest)
    return p


def load_lock(path: Path | str = LOCK_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise LockMissingError(f"methodology lock manifest not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data["content"], data["lock_hash"]  # noqa: B018
    except (ValueError, KeyError, TypeError) as exc:
        raise LockMissingError(f"methodology lock manifest unreadable: {p}") from exc
    return data


def verify_lock(
    path: Path | str = LOCK_PATH,
    files: dict[str, Path] | None = None,
    code: list[Path] | None = None,
    choices: dict[str, Any] | None = None,
    store: Path | str = EXPLORATORY_DB,
) -> dict[str, Any]:
    """Recompute the locked content and compare it with the manifest. Raises on any difference."""
    manifest = load_lock(path)
    if manifest.get("label") != LABEL:
        raise LockDriftError(f"unexpected lock label {manifest.get('label')!r}")
    now = build_lock_content(files, code, choices, store)
    old = manifest["content"]
    if canonical_hash(old) != manifest["lock_hash"]:
        raise LockDriftError("the manifest was edited: its content no longer matches its lock_hash")
    diffs = [f"file:{k}" for k in sorted(set(old["files"]) | set(now["files"]))
             if old["files"].get(k) != now["files"].get(k)]  # fmt: skip
    if old["code_sha256"] != now["code_sha256"]:
        diffs.append("code_sha256")
    if old["choices"] != now["choices"]:
        diffs += [
            f"choice:{k}"
            for k in sorted(set(old["choices"]) | set(now["choices"]))
            if old["choices"].get(k) != now["choices"].get(k)
        ]
    if diffs:
        raise LockDriftError(f"locked items changed since the lock was written: {diffs}")
    return manifest
