"""Provenance, deterministic JSON writing and Markdown helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.utils.jsonio import to_jsonable, write_json

PROXY_FIELDS = {
    "proxy_run": True,
    "pressure_status": "PENDING_PHASE3",
    "score_label": "PROXY_NOT_PRESSURE",
    "not_for_publication": True,
}

INTERPRETATION = (
    "Pressure is not defined until Phase 3. Every number in this report is an all-situation "
    "descriptive proxy (innings 1 and 2, all match situations), labelled PROXY_NOT_PRESSURE, "
    "and is not for publication. The harness is generic and accepts pressure samples unchanged."
)

ANALYTICS_PACKAGES = ("analytics", "validation")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_version(app_root: Path | None = None) -> str:
    """sha256 over the sources of app/analytics and app/validation (sorted, deterministic)."""
    root = app_root or Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for pkg in ANALYTICS_PACKAGES:
        for p in sorted((root / pkg).rglob("*.py")):
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def data_version(db) -> dict[str, Any]:
    """Latest DATA_VERSION row plus source sha256s from dataset_lineage (db is read-only)."""
    row = db.query(
        "SELECT name, status FROM model_versions WHERE kind = 'DATA_VERSION' "
        "ORDER BY model_version_id DESC LIMIT 1"
    )
    lineage = db.query(
        "SELECT file_name, sha256 FROM dataset_lineage WHERE role = 'PRIMARY' "
        "AND run_id = (SELECT max(run_id) FROM dataset_lineage) ORDER BY file_name"
    )
    return {
        "data_version": row[0][0] if row else None,
        "source_sha256": {name: sha for name, sha in lineage},
    }


def provenance(
    db=None,
    config_path: Path | None = None,
    seed: int | None = None,
    extra: dict | None = None,
) -> dict[str, Any]:
    prov: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_version": code_version(),
        "seed": seed,
    }
    if config_path is not None:
        prov["config_file"] = Path(config_path).name
        prov["config_sha256"] = sha256_bytes(Path(config_path).read_bytes())
    if db is not None:
        prov.update(data_version(db))
    prov.update(extra or {})
    return prov


def round_floats(obj: Any, places: int = 10) -> Any:
    obj = to_jsonable(obj)
    if isinstance(obj, float):
        return round(obj, places) if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: round_floats(v, places) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_floats(v, places) for v in obj]
    return obj


def write_json_deterministic(path: Path, data: Any) -> None:
    write_json(Path(path), round_floats(data))


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def fmt(v: Any, places: int = 2) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        if v != 0 and abs(v) < 0.01:
            return f"{v:.3g}"
        return f"{v:.{places}f}"
    return str(v)


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(fmt(c) for c in r) + " |")
    return "\n".join(lines) + "\n"
