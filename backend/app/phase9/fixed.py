"""Hyperparameters carried over unchanged from the Phase 8 artefacts (no new tuning in Phase 9)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.phase8.constants import MODELS_DIR


def phase8_expected_choice(
    role: str, name: str, models_dir: Path | str = MODELS_DIR
) -> tuple[str, dict[str, Any]]:
    """(learner, params) chosen in Phase 8 for one expected-outcome target."""
    meta = json.loads(
        (Path(models_dir) / f"p8_expected_{role}_{name}_v1.json").read_text(encoding="utf-8")
    )
    params = meta.get("params") or "{}"
    return str(meta["algorithm"]), dict(json.loads(params) if isinstance(params, str) else params)


def phase8_wp_params(model: str, models_dir: Path | str = MODELS_DIR) -> dict[str, Any]:
    """Grid point chosen in Phase 8 for the win-probability model ``W1`` or ``W2``."""
    meta = json.loads((Path(models_dir) / "p8_wp_v1.json").read_text(encoding="utf-8"))
    return dict(meta["training"][model]["params"])
