"""Publication gating: every output is INTERNAL_EXPERIMENTAL_ONLY unless every gate passes.

``evaluate_gates`` and ``publication_status`` are pure functions over ``GateInput``. Inputs are read
from files once (``load_gate_inputs``); a missing, unreadable or malformed input fails its gate
(``INPUT_UNAVAILABLE``). Nothing in code can set ``methodology_validated``: only a human edit of
``config/phase5_methodology_status_v1.json`` can.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.phase5.constants import (
    DATE_SUMMARY,
    FROZEN_CHOICES,
    GATES_CONFIG,
    INTERNAL,
    METHODOLOGY_STATUS,
    PUBLIC,
)

GATE_IDS = (
    "data_weight_gate_passed",
    "methodology_validated",
    "strict_classification_available",
    "min_eligible_pool",
    "date_verification",
)
NOT_VALIDATED = "THRESHOLD_NOT_VALIDATED"
EXPECTED_CELLS = 4
UNAVAILABLE = "INPUT_UNAVAILABLE"


class PublicationGateError(Exception):
    """Raised on a public route when the publication gates are not all satisfied."""

    def __init__(self, gate_results: list[dict[str, Any]]) -> None:
        super().__init__("PUBLICATION_GATE_NOT_SATISFIED")
        self.gate_results = gate_results


@dataclass(frozen=True)
class GateInput:
    """Everything the gates read. ``None`` means the input could not be loaded."""

    cell_statuses: dict[str, str] | None
    methodology: dict[str, Any] | None
    date_gate: dict[str, Any] | None
    strict_enabled: bool | None
    min_public_pool: int = 10


@dataclass(frozen=True)
class RequestNeeds:
    """What a request touches. ``eligible_pool`` is None when no rows are evaluated."""

    uses_strict_classification: bool = False
    eligible_pool: int | None = None


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    passed: bool
    applicable: bool
    detail: str
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "passed": self.passed,
            "applicable": self.applicable,
            "detail": self.detail,
        }


def _read_json(path: Path | str) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def load_gate_inputs(
    strict_enabled: bool | None,
    frozen_path: Path | str = FROZEN_CHOICES,
    methodology_path: Path | str = METHODOLOGY_STATUS,
    date_summary_path: Path | str = DATE_SUMMARY,
    gates_path: Path | str = GATES_CONFIG,
) -> GateInput:
    frozen = _read_json(frozen_path)
    cells: dict[str, str] | None = None
    if frozen is not None:
        try:
            cells = {str(k): str(v["decision"]["status"]) for k, v in frozen["eligibility"].items()}
        except (KeyError, TypeError):
            cells = None
    date_summary = _read_json(date_summary_path)
    date_gate = date_summary.get("gate") if date_summary else None
    cfg = _read_json(gates_path)
    try:
        min_pool = int(cfg["min_public_pool"]) if cfg else 10
    except (KeyError, TypeError, ValueError):
        min_pool = 10
    return GateInput(
        cell_statuses=cells,
        methodology=_read_json(methodology_path),
        date_gate=date_gate if isinstance(date_gate, dict) else None,
        strict_enabled=strict_enabled,
        min_public_pool=min_pool,
    )


def _data_weight(inp: GateInput) -> GateResult:
    gid = "data_weight_gate_passed"
    cells = inp.cell_statuses
    if not cells or len(cells) < EXPECTED_CELLS:
        return GateResult(gid, False, True, UNAVAILABLE)
    bad = sorted(k for k, v in cells.items() if v == NOT_VALIDATED)
    if bad:
        return GateResult(gid, False, True, f"{len(bad)} of {len(cells)} cells {NOT_VALIDATED}")
    return GateResult(gid, True, True, f"all {len(cells)} cells validated")


def _methodology(inp: GateInput) -> GateResult:
    gid = "methodology_validated"
    m = inp.methodology
    if m is None:
        return GateResult(gid, False, True, UNAVAILABLE)
    complete = all(
        str(m.get(k, "")).strip() for k in ("validated_by", "validated_date", "evidence_path")
    )
    if m.get("validated") is True and complete:
        return GateResult(gid, True, True, "validated by a human reviewer")
    if m.get("validated") is True:
        return GateResult(
            gid, False, True, "validated=true without validated_by/date/evidence_path"
        )
    return GateResult(gid, False, True, "methodology not validated")


def _strict(inp: GateInput, needs: RequestNeeds) -> GateResult:
    gid = "strict_classification_available"
    if not needs.uses_strict_classification:
        return GateResult(gid, True, False, "not applicable: request uses no strict status filter")
    if inp.strict_enabled is None:
        return GateResult(gid, False, True, UNAVAILABLE)
    if inp.strict_enabled:
        return GateResult(gid, True, True, "strict_uncapped_enabled")
    return GateResult(gid, False, True, "STRICT_UNCAPPED_DISABLED")


def _pool(inp: GateInput, needs: RequestNeeds) -> GateResult:
    gid = "min_eligible_pool"
    if needs.eligible_pool is None:
        return GateResult(gid, True, False, "not applicable: evaluated per request with rows")
    ok = needs.eligible_pool >= inp.min_public_pool
    return GateResult(
        gid, ok, True, f"{needs.eligible_pool} eligible rows, minimum {inp.min_public_pool}"
    )


def _dates(inp: GateInput) -> GateResult:
    gid = "date_verification"
    g = inp.date_gate
    if g is None:
        return GateResult(gid, False, True, "NOT_RUN")
    passed = g.get("passed") is True
    return GateResult(
        gid, passed, True, str(g.get("detail", "")) or ("passed" if passed else "failed")
    )


def evaluate_gates(inp: GateInput, needs: RequestNeeds | None = None) -> list[GateResult]:
    needs = needs or RequestNeeds()
    return [
        _data_weight(inp),
        _methodology(inp),
        _strict(inp, needs),
        _pool(inp, needs),
        _dates(inp),
    ]


def publication_status(gates: list[GateResult]) -> str:
    """PUBLIC_ALLOWED only if every applicable gate passed (and at least one gate was evaluated)."""
    applicable = [g for g in gates if g.applicable]
    return PUBLIC if applicable and all(g.passed for g in applicable) else INTERNAL


def failing(gates: list[GateResult]) -> list[GateResult]:
    return [g for g in gates if g.applicable and not g.passed]


def apply_gates(
    response: dict[str, Any], inp: GateInput, needs: RequestNeeds, internal: bool
) -> dict[str, Any]:
    """Single enforcement point. Public callers get PublicationGateError instead of rows."""
    gates = evaluate_gates(inp, needs)
    status = publication_status(gates)
    results = [g.as_dict() for g in gates]
    if status != PUBLIC and not internal:
        raise PublicationGateError(results)
    return {**response, "publication_status": status, "gate_results": results}
