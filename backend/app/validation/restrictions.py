"""Loader for the machine-readable data-quality restrictions used by Phase 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_ROOT

RESTRICTIONS_PATH = BACKEND_ROOT / "config" / "data_quality_restrictions_v1.json"


class RestrictionsError(ValueError):
    """Raised when the restrictions file is malformed or tries a global exclusion."""


def validate_restrictions(cfg: dict[str, Any]) -> dict[str, Any]:
    if cfg.get("global_exclusion") is not False:
        raise RestrictionsError("global_exclusion must be false at the top level")
    vocab = set(cfg.get("metric_vocabulary") or [])
    effects = set(cfg.get("effects") or [])
    seen: set[str] = set()
    for rule in cfg.get("restrictions") or []:
        rid = rule.get("rule_id")
        if not rid or rid in seen:
            raise RestrictionsError(f"missing or duplicate rule_id: {rid}")
        seen.add(rid)
        if rule.get("global_exclusion") is not False:
            raise RestrictionsError(f"{rid}: global exclusion is not allowed")
        metrics = rule.get("applies_to_metrics")
        if not metrics or not isinstance(metrics, list):
            raise RestrictionsError(f"{rid}: applies_to_metrics must be a non-empty list")
        unknown = sorted(set(metrics) - vocab)
        if unknown:
            raise RestrictionsError(f"{rid}: metrics outside the vocabulary: {unknown}")
        if rule.get("effect") not in effects:
            raise RestrictionsError(f"{rid}: unknown effect {rule.get('effect')}")
        if not rule.get("row_filter") or not rule.get("issue_check_names"):
            raise RestrictionsError(f"{rid}: row_filter and issue_check_names are required")
    return cfg


def load_restrictions(path: Path | str = RESTRICTIONS_PATH) -> dict[str, Any]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_restrictions(cfg)


def restrictions_for_metric(
    metric_name: str, cfg: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Rules that restrict `metric_name`. A metric with no rule is unrestricted (no wildcard)."""
    cfg = cfg if cfg is not None else load_restrictions()
    return [r for r in cfg["restrictions"] if metric_name in r["applies_to_metrics"]]


def rule_by_id(rule_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    cfg = cfg if cfg is not None else load_restrictions()
    return next((r for r in cfg["restrictions"] if r["rule_id"] == rule_id), None)
