"""Versioned IPL/T20I format-weight configuration: load, validate, hash, register."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.database import connect

EXPECTED_IDS = (
    "w100_0",
    "w85_15",
    "w80_20",
    "w70_30",
    "w60_40",
    "w55_45",
    "w50_50",
    "w0_100",
)
EXPECTED_WEIGHTS = {
    "w100_0": (1.0, 0.0),
    "w85_15": (0.85, 0.15),
    "w80_20": (0.8, 0.2),
    "w70_30": (0.7, 0.3),
    "w60_40": (0.6, 0.4),
    "w55_45": (0.55, 0.45),
    "w50_50": (0.5, 0.5),
    "w0_100": (0.0, 1.0),
}
MODEL_VERSION_NAME = "format-weights-v1"


class FormatConfigError(ValueError):
    """Raised for an invalid format-weight configuration."""


def validate_config(cfg: dict[str, Any]) -> dict[str, Any]:
    for key in ("version", "created_date", "status", "default_config_id", "configurations"):
        if key not in cfg:
            raise FormatConfigError(f"missing key: {key}")
    if cfg["status"] != "PROVISIONAL":
        raise FormatConfigError("status must be PROVISIONAL")
    confs = cfg["configurations"]
    if not isinstance(confs, list) or len(confs) != len(EXPECTED_IDS):
        raise FormatConfigError(f"exactly {len(EXPECTED_IDS)} configurations required")
    ids = [c.get("id") for c in confs]
    if len(set(ids)) != len(ids):
        raise FormatConfigError("duplicate configuration id")
    if set(ids) != set(EXPECTED_IDS):
        raise FormatConfigError(f"configuration ids must be {list(EXPECTED_IDS)}")
    for c in confs:
        try:
            wi, wt = float(c["ipl_weight"]), float(c["t20i_weight"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FormatConfigError(f"bad weights in {c.get('id')}") from exc
        if not (0.0 <= wi <= 1.0 and 0.0 <= wt <= 1.0):
            raise FormatConfigError(f"weight outside [0, 1] in {c['id']}")
        if abs(wi + wt - 1.0) > 1e-9:
            raise FormatConfigError(f"weights of {c['id']} must sum to 1")
        ew = EXPECTED_WEIGHTS[c["id"]]
        if abs(wi - ew[0]) > 1e-9 or abs(wt - ew[1]) > 1e-9:
            raise FormatConfigError(f"{c['id']} weights do not match its id")
    if cfg["default_config_id"] not in ids:
        raise FormatConfigError("default_config_id is not a configuration")
    if cfg.get("default_flag") != "PROVISIONAL_NOT_VALIDATED":
        raise FormatConfigError("default must be flagged PROVISIONAL_NOT_VALIDATED")
    return cfg


def load_config(path: Path | str) -> dict[str, Any]:
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FormatConfigError(f"cannot read config: {exc}") from exc
    return validate_config(cfg)


def config_hash(cfg: dict[str, Any]) -> str:
    """sha256 of the canonical JSON (sorted keys, compact separators)."""
    canon = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def settings_consistency(cfg: dict[str, Any], settings) -> list[dict[str, Any]]:
    """Warnings (never raises) when Settings weights differ from the config default."""
    default = next(c for c in cfg["configurations"] if c["id"] == cfg["default_config_id"])
    warnings = []
    if (
        abs(default["ipl_weight"] - settings.ipl_weight) > 1e-9
        or abs(default["t20i_weight"] - settings.t20i_weight) > 1e-9
    ):
        warnings.append(
            {
                "code": "SETTINGS_WEIGHT_MISMATCH",
                "message": (
                    f"Settings weights {settings.ipl_weight}:{settings.t20i_weight} differ from "
                    f"config default {default['ipl_weight']}:{default['t20i_weight']}"
                ),
            }
        )
    return warnings


def register_config_in_model_versions(db_path: Path | str, cfg: dict[str, Any]) -> bool:
    """Insert one model_versions row 'format-weights-v1' (idempotent).

    Opens a read-write connection only here. Returns True if a row was inserted.
    """
    payload = json.dumps(
        {
            "config_version": cfg["version"],
            "config_sha256": config_hash(cfg),
            "default_config_id": cfg["default_config_id"],
            "status": cfg["status"],
            "configurations": [
                {k: c[k] for k in ("id", "ipl_weight", "t20i_weight")}
                for c in cfg["configurations"]
            ],
        },
        sort_keys=True,
    )
    db = connect(db_path, read_only=False)
    try:
        exists = db.scalar(
            "SELECT count(*) FROM model_versions WHERE name = ?", [MODEL_VERSION_NAME]
        )
        if exists:
            return False
        db.execute(
            "INSERT INTO model_versions (name, kind, status, config_json, notes) "
            "VALUES (?, 'WEIGHTING_CONFIG', 'PROVISIONAL', ?, ?)",
            [MODEL_VERSION_NAME, payload, "Phase 2.5 IPL/T20I sensitivity grid; default 70:30"],
        )
        return True
    finally:
        db.close()
