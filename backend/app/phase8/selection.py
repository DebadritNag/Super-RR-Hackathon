"""Predeclared approach selection (criteria ``approach_selection``).

The rule is applied to approach-level metrics only. It receives no player identity, rank or score
level (``assert_metrics_only`` refuses anything else), so it cannot be steered by who ranks where.

Rule, in the declared order:

1. Highest split-half lower bound. An approach within 0.05 of the best lower bound is a
   contender; contenders are ordered by out-of-time lower bound, then Top-10 inclusion
   concentration, then explainability, then id order A, B, C.
2. When no approach has a positive split-half lower bound, the list is EXPLORATORY and the
   approach with the highest split-half point estimate is submitted (ties by id order).

Both branches are always computed and reported, so the reader can see whether they agree.
"""

from __future__ import annotations

import math
from typing import Any

APPROACH_IDS = ("A", "B", "C")
MARGIN = 0.05
TIE_TOL = 1e-12
# Fixed explainability checklist (inputs observable, no latent factor, plain-language statement):
# A uses observed versus expected only (3); B and C add a modelled win-probability state or a
# data-weighted index (2). It is the fourth tie-break and decides nothing unless three earlier
# criteria tie.
EXPLAINABILITY = {"A": 3, "B": 2, "C": 2}
METRIC_KEYS = (
    "sb",
    "sb_low",
    "oot",
    "oot_low",
    "concentration",
    "explainability",
    "n_split",
    "n_oot",
)


class SelectionError(ValueError):
    """The selection rule was given something other than approach-level metrics."""


def assert_metrics_only(metrics: dict[str, dict[str, Any]]) -> None:
    for a, m in metrics.items():
        if a not in APPROACH_IDS:
            raise SelectionError(f"unknown approach id '{a}'")
        extra = set(m) - set(METRIC_KEYS)
        if extra:
            raise SelectionError(
                f"selection takes approach-level metrics only, got {sorted(extra)}"
            )


def _num(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f if math.isfinite(f) else float("nan")


def _lower_bound_path(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lb = {a: _num(m.get("sb_low")) for a, m in metrics.items()}
    valid = {a: v for a, v in lb.items() if not math.isnan(v)}
    if not valid:
        return {"chosen": None, "contenders": [], "best_lower_bound": float("nan")}
    best = max(valid.values())
    contenders = [a for a, v in sorted(valid.items()) if best - v < MARGIN]

    def key(a: str) -> tuple:
        m = metrics[a]
        oot = _num(m.get("oot_low"))
        return (
            -(oot if not math.isnan(oot) else -math.inf),
            -_num(m.get("concentration") or 0.0),
            -_num(m.get("explainability") or 0.0),
            a,
        )

    contenders.sort(key=key)
    return {"chosen": contenders[0], "contenders": contenders, "best_lower_bound": best}


def _point_path(metrics: dict[str, dict[str, Any]]) -> str | None:
    pts = {a: _num(m.get("sb")) for a, m in metrics.items()}
    valid = {a: v for a, v in pts.items() if not math.isnan(v)}
    if not valid:
        return None
    best = max(valid.values())
    return sorted(a for a, v in valid.items() if best - v < TIE_TOL)[0]


def select_approach(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Apply the declared rule to ``{approach: metrics}`` and return the decision with its reason."""
    assert_metrics_only(metrics)
    if not metrics:
        raise SelectionError("no approach metrics given")
    lb = _lower_bound_path(metrics)
    point = _point_path(metrics)
    any_positive = any(
        not math.isnan(_num(m.get("sb_low"))) and _num(m.get("sb_low")) > 0
        for m in metrics.values()
    )
    if any_positive:
        chosen, path = lb["chosen"], "HIGHEST_SPLIT_HALF_LOWER_BOUND"
    else:
        chosen, path = point, "NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE"
    if chosen is None:
        raise SelectionError("no approach has a usable split-half estimate")
    agree = lb["chosen"] == point
    parts = [
        f"Chosen approach {chosen} by rule path {path}.",
        (
            "No approach has a split-half lower bound above 0, so the list is EXPLORATORY."
            if not any_positive
            else "At least one approach has a positive split-half lower bound."
        ),
        (
            f"The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects "
            f"{lb['chosen']} and the point-estimate path selects {point}"
            + (": the two paths agree." if agree else ": the two paths differ.")
        ),
    ]
    return {
        "chosen": chosen,
        "path": path,
        "lower_bound_path": lb["chosen"],
        "point_estimate_path": point,
        "paths_agree": bool(agree),
        "contenders": lb["contenders"],
        "any_positive_lower_bound": bool(any_positive),
        "list_status_cap": "EXPLORATORY" if not any_positive else None,
        "reason": " ".join(parts),
    }
