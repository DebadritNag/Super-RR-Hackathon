"""Loaders and validation for the Phase 4 configuration files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.phase4.constants import SPLIT_CONFIG


class Phase4ConfigError(ValueError):
    """Raised for an invalid Phase 4 configuration."""


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_split_config(path: Path | str = SPLIT_CONFIG) -> dict[str, Any]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("periods", "par", "seed", "meaningful_split"):
        if key not in cfg:
            raise Phase4ConfigError(f"split config is missing '{key}'")
    return cfg
