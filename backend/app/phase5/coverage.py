"""Precomputed context coverage: how many players qualify for each valid filter combination.

Counts are measured by the engine's own ``resolve_pool`` (the function the ranking uses), so the
table and the ranking endpoint cannot disagree. ``VERIFIED_UNCAPPED`` combinations are listed as
DISABLED while strict uncapped is off. The minimum pool rule is stored with every row
(``meets_internal_min`` uses ``min_internal_pool``, ``meets_public_min`` uses ``min_public_pool``).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from app.phase5.filters import CAPPED_FILTERS, FilterSpec, spec_hash
from app.phase5.ranking_engine import ContextEngine

COVERAGE_COLUMNS = [
    "spec_hash",
    "format",
    "role",
    "nationality",
    "status",
    "phase",
    "situation",
    "include_unknown_nationality",
    "include_unknown_status",
    "result_status",
    "enabled",
    "context_status",
    "players_in_context",
    "eligible_in_context",
    "after_nationality",
    "after_status",
    "final_pool",
    "reason_codes",
    "excluded_unknown_nationality",
    "excluded_unknown_status",
    "min_internal_pool",
    "min_public_pool",
    "meets_internal_min",
    "meets_public_min",
]


def enumerate_specs(cfg: dict[str, Any]) -> Iterator[FilterSpec]:
    """Every valid combination; the unknown toggles only vary where they can change the result."""
    nats: list[tuple[str | None, bool]] = [(None, False)]
    for n in cfg["nationalities"]:
        nats += [(n, False), (n, True)] if n != "Unknown" else [(n, False)]
    stats: list[tuple[str | None, bool]] = [(None, False)]
    for s in cfg["statuses"]:
        stats += [(s, False), (s, True)] if s in CAPPED_FILTERS else [(s, False)]
    for fmt in cfg["formats"]:
        for role in cfg["roles"]:
            for phase in cfg["phases"]:
                for sit in cfg["situations"]:
                    for nat, inat in nats:
                        for st, ist in stats:
                            yield FilterSpec(
                                role=role,
                                format=fmt,
                                nationality=nat,
                                status=st,
                                phase=phase,
                                situation=sit,
                                include_unknown_nationality=inat,
                                include_unknown_status=ist,
                            )


def build_coverage(engine: ContextEngine, cls: pd.DataFrame, strict_enabled: bool) -> pd.DataFrame:
    n_int = int(engine.cfg["min_internal_pool"])
    n_pub = int(engine.cfg["min_public_pool"])
    rows = []
    for spec in enumerate_specs(engine.cfg):
        pool = engine.resolve_pool(spec, cls, strict_enabled)
        sc = pool.stage_counts
        rows.append(
            {
                "spec_hash": spec_hash(spec),
                "format": spec.format,
                "role": spec.role,
                "nationality": spec.nationality,
                "status": spec.status,
                "phase": spec.phase,
                "situation": spec.situation,
                "include_unknown_nationality": spec.include_unknown_nationality,
                "include_unknown_status": spec.include_unknown_status,
                "result_status": pool.result_status,
                "enabled": not pool.disabled,
                "context_status": "|".join(
                    f"{c}:{s}" for c, s in sorted(pool.context_status.items())
                ),
                "players_in_context": sc.get("players_in_context"),
                "eligible_in_context": sc.get("eligible_in_context"),
                "after_nationality": sc.get("after_nationality"),
                "after_status": sc.get("after_status"),
                "final_pool": 0 if pool.disabled else pool.size,
                "reason_codes": ",".join(sorted({r["code"] for r in pool.reasons})),
                "excluded_unknown_nationality": pool.excluded_counts.get(
                    "unknown_nationality_excluded"
                ),
                "excluded_unknown_status": pool.excluded_counts.get("unknown_status_excluded"),
                "min_internal_pool": n_int,
                "min_public_pool": n_pub,
                "meets_internal_min": (not pool.disabled) and pool.size >= n_int,
                "meets_public_min": (not pool.disabled) and pool.size >= n_pub,
            }
        )
    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)
