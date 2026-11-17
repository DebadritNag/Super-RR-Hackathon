"""Filter specification of the dynamic ranking engine (classification and context filters).

A filter never selects a model: every selected filter is ANDed over the same stored analytics.
``FilterSpec`` is a strict Pydantic v2 model (unknown fields are rejected, every free value is an
enumerated literal or a bounded integer), so no SQL, path or column name can enter through it.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FormatName = Literal["IPL", "T20I", "COMBINED_w70_30"]
RoleName = Literal["batter", "bowler"]
NationalityName = Literal["Indian", "Overseas", "Unknown"]
StatusFilter = Literal[
    "CAPPED_ANY", "VERIFIED_CAPPED", "DERIVED_CAPPED", "VERIFIED_UNCAPPED", "UNKNOWN_STATUS"
]
PhaseName = Literal["ALL", "powerplay", "middle", "death"]
SituationName = Literal["ALL", "chase", "first_innings"]
SortName = Literal["rank", "score", "name", "matches", "n", "n_eff"]
OrderName = Literal["asc", "desc"]

STRICT_UNCAPPED_DISABLED = "STRICT_UNCAPPED_DISABLED"
RANKING_FIELDS = (
    "role",
    "format",
    "nationality",
    "status",
    "phase",
    "situation",
    "min_matches",
    "min_context_matches",
    "include_unknown_nationality",
    "include_unknown_status",
)
CAPPED_FILTERS = ("CAPPED_ANY", "VERIFIED_CAPPED", "DERIVED_CAPPED")
STATUS_MEMBERS = {
    "CAPPED_ANY": ("VERIFIED_CAPPED", "DERIVED_CAPPED"),
    "VERIFIED_CAPPED": ("VERIFIED_CAPPED",),
    "DERIVED_CAPPED": ("DERIVED_CAPPED",),
    "VERIFIED_UNCAPPED": ("VERIFIED_UNCAPPED",),
    "UNKNOWN_STATUS": ("UNKNOWN",),
}


class FilterSpec(BaseModel):
    """All selected filters (AND semantics). ``role`` is required: batter and bowler rankings are
    always separate. Pagination and sort fields do not change the ranking itself."""

    model_config = ConfigDict(extra="forbid")

    role: RoleName
    format: FormatName = "COMBINED_w70_30"
    nationality: NationalityName | None = None
    status: StatusFilter | None = Field(
        None,
        description="Capped-status filter over the three real values. VERIFIED_UNCAPPED is a "
        "disabled placeholder and always returns STRICT_UNCAPPED_DISABLED.",
    )
    phase: PhaseName = "ALL"
    situation: SituationName = "ALL"
    min_matches: int = Field(0, ge=0, le=200, description="career matches in the format window")
    min_context_matches: int = Field(0, ge=0, le=200, description="pressure matches in context")
    include_unknown_nationality: bool = False
    include_unknown_status: bool = False
    limit: int = Field(10, ge=1, le=50)
    offset: int = Field(0, ge=0, le=10000)
    sort: SortName = "rank"
    order: OrderName | None = None

    def ranking_dict(self) -> dict[str, Any]:
        """Fields that define the ranking (not its paging or display order), defaults explicit."""
        return {k: getattr(self, k) for k in sorted(RANKING_FIELDS)}

    def effective_order(self) -> str:
        if self.order is not None:
            return self.order
        return "asc" if self.sort in ("rank", "name") else "desc"


def canonical_json(spec: FilterSpec) -> str:
    """Key-order independent JSON of the ranking-defining fields (defaults made explicit)."""
    return json.dumps(spec.ranking_dict(), sort_keys=True, separators=(",", ":"))


def spec_hash(spec: FilterSpec) -> str:
    return hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()


def page_hash(spec: FilterSpec) -> str:
    """Hash of the ranking plus its paging and display order (identifies one response page)."""
    body = {**spec.ranking_dict(), "limit": spec.limit, "offset": spec.offset,
            "sort": spec.sort, "order": spec.effective_order()}  # fmt: skip
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def validate_combination(spec: FilterSpec, strict_enabled: bool) -> list[dict[str, Any]]:
    """Reason codes that make the whole request unservable (empty list when it can run)."""
    out: list[dict[str, Any]] = []
    if spec.status == "VERIFIED_UNCAPPED" and not strict_enabled:
        out.append(
            {
                "code": STRICT_UNCAPPED_DISABLED,
                "count": 0,
                "detail": "VERIFIED_UNCAPPED needs an authoritative player_id-keyed source.",
            }
        )
    return out


def uses_strict_classification(spec: FilterSpec) -> bool:
    """Verified-status filters rely on the strict classification capability (gate input)."""
    return spec.status in ("VERIFIED_CAPPED", "VERIFIED_UNCAPPED")


def catalog(cfg: dict[str, Any], strict_enabled: bool) -> dict[str, Any]:
    """Valid values of every filter with enabled/disabled flags and the reason."""

    def item(value: str, enabled: bool = True, reason: str | None = None) -> dict[str, Any]:
        return {"value": value, "enabled": enabled, "reason": reason}

    uncapped_reason = None if strict_enabled else cfg["disabled"]["strict_uncapped"]
    return {
        "role": [item(v) for v in cfg["roles"]],
        "format": [item(v) for v in cfg["formats"]],
        "nationality": [item(v) for v in cfg["nationalities"]],
        "status": [
            item(
                v,
                enabled=(v != "VERIFIED_UNCAPPED" or strict_enabled),
                reason=uncapped_reason if v == "VERIFIED_UNCAPPED" else None,
            )
            for v in cfg["statuses"]
        ],
        "phase": [item(v) for v in cfg["phases"]],
        "situation": [item(v) for v in cfg["situations"]],
        "wickets_remaining_band": [item("ANY", False, cfg["disabled"]["wickets_remaining_bands"])],
        "all_rounder_role": [item("all_rounder", False, cfg["disabled"]["all_rounder_role"])],
        "sort": [item(v) for v in cfg["sort_whitelist"]],
        "include_unknown_nationality": [item("false"), item("true")],
        "include_unknown_status": [item("false"), item("true")],
    }
