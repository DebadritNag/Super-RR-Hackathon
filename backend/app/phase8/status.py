"""List and row status labels for the submitted rankings.

The label rules are the predeclared ones (criteria ``status_thresholds``); this module is the only
place that turns metrics into a label. Reports, API and the UI read the stored label and never
recompute it. A label is ``VALIDATED`` only when every declared VALIDATED threshold is met.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from app.core.config import BACKEND_ROOT
from app.phase8.approach_a import list_status as _list_status

STATUS_ORDER = ("INSUFFICIENT_EVIDENCE", "EXPLORATORY", "PROVISIONAL", "VALIDATED")
LABELS_FILE = BACKEND_ROOT / "config" / "phase8_status_labels_v1.json"


class StatusError(ValueError):
    """An invalid status label or an attempt to give a row a stronger label than its list."""


def load_labels() -> dict[str, Any]:
    return json.loads(LABELS_FILE.read_text(encoding="utf-8"))


def check_label(label: str) -> str:
    if label not in STATUS_ORDER:
        raise StatusError(f"unknown status label '{label}'")
    return label


def _rank(label: str) -> int:
    return STATUS_ORDER.index(check_label(label))


def list_status(
    crit: dict[str, Any],
    metrics: dict[str, Any],
    floor: bool,
    n_eligible: int,
) -> dict[str, str]:
    """List status from the declared thresholds.

    ``metrics`` needs ``sb`` (split-half Spearman-Brown), ``sb_low``, ``oot_low`` and the player
    counts ``n_split`` and ``n_oot``. Missing numbers make the criterion not estimable, which can
    never produce a stronger label.
    """
    out = _list_status(
        crit,
        metrics.get("sb"),
        metrics.get("sb_low"),
        metrics.get("oot_low"),
        bool(floor),
        int(n_eligible),
        int(metrics.get("n_split", 0)),
        int(metrics.get("n_oot", 0)),
    )
    check_label(out["status"])
    return out


def row_status(
    list_label: str, evidence_class: str | None, top10_prob: float | None, eligible: bool
) -> str:
    """Row label: never stronger than the list label (design section 9.3)."""
    check_label(list_label)
    if not eligible:
        return "INSUFFICIENT_EVIDENCE"
    if list_label == "INSUFFICIENT_EVIDENCE":
        return "INSUFFICIENT_EVIDENCE"
    p = float(top10_prob) if top10_prob is not None and np.isfinite(top10_prob) else 0.0
    row = "EXPLORATORY"
    if (
        _rank(list_label) >= _rank("VALIDATED")
        and evidence_class == "STRONG_SUBSTANTIAL"
        and p >= 0.5
    ):
        row = "VALIDATED"
    elif _rank(list_label) >= _rank("PROVISIONAL") and p >= 0.25:
        row = "PROVISIONAL"
    if _rank(row) > _rank(list_label):
        raise StatusError("a row cannot be stronger than its list")
    return row


def banner(list_label: str, role: str, basis: str, reason: str) -> str:
    """Header banner used by the status document, the JSON twins and the API."""
    check_label(list_label)
    who = "batters" if role == "batter" else "bowlers"
    if list_label == "VALIDATED":
        head = f"VALIDATED ranking of {who}."
    elif list_label == "PROVISIONAL":
        head = f"PROVISIONAL ranking of {who}: usable with the stated uncertainty, not validated."
    elif list_label == "EXPLORATORY":
        head = (
            f"EXPLORATORY ranking of {who}: this is the best-supported ordering of the available "
            "data, not a validated ranking. The order is not shown to separate players beyond noise."
        )
    else:
        head = f"INSUFFICIENT EVIDENCE for a ranking of {who}."
    return f"{head} Ranking basis: {basis}. Reason: {reason}."
