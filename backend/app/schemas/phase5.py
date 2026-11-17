"""Pydantic v2 schemas for the Phase 5 publication gating and strict-uncapped responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StatusLiteral = Literal["EXPERIMENTAL_NOT_VALIDATED"]
PublicationStatus = Literal["INTERNAL_EXPERIMENTAL_ONLY", "PUBLIC_ALLOWED"]
GateId = Literal[
    "data_weight_gate_passed",
    "methodology_validated",
    "strict_classification_available",
    "min_eligible_pool",
    "date_verification",
]
# Three real values. VERIFIED_UNCAPPED is a disabled placeholder, not a fourth status: it is listed
# separately in ``CapabilitiesResponse.disabled_placeholder_values``.
ClassificationStatus = Literal["VERIFIED_CAPPED", "DERIVED_CAPPED", "UNKNOWN"]


class GateResultModel(BaseModel):
    gate_id: GateId
    passed: bool
    applicable: bool
    detail: str


class PublicationFlags(BaseModel):
    """Fields present on every experimental response (Phase 4 flags plus publication gating)."""

    status: StatusLiteral = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False
    disclaimer: str
    publication_status: PublicationStatus
    gate_results: list[GateResultModel]


class CapabilityModel(BaseModel):
    enabled: bool
    reasons: list[str]
    verified_coverage: float
    min_verified_coverage: float


class StrictUncappedDisabledResponse(BaseModel):
    """Returned for every uncapped endpoint, preset, ranking or constraint while disabled."""

    result_status: Literal["STRICT_UNCAPPED_DISABLED"]
    reason: str
    source_needed: str
    capability: CapabilityModel
    request_kind: str
    rows: list[Any] = Field(default_factory=list)
    preset_id: str | None = None
    filter_echo: dict[str, Any] | None = None
    status: StatusLiteral = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False
    disclaimer: str
    publication_status: Literal["INTERNAL_EXPERIMENTAL_ONLY"]
    gate_results: list[GateResultModel]
    failing_gates: list[str]


class CapabilitiesResponse(PublicationFlags):
    strict_uncapped_enabled: bool
    capability: dict[str, Any]
    classification_values: list[ClassificationStatus] = Field(
        description="The three real international_status values."
    )
    disabled_placeholder_values: list[str] = Field(
        default_factory=lambda: ["VERIFIED_UNCAPPED"],
        description="Disabled placeholder(s), not established statuses. Strict uncapped selection "
        "is disabled; a filter on a placeholder returns STRICT_UNCAPPED_DISABLED.",
    )
    unknown_status_label: str
    unknown_status_banner: str


class PublicationGatesResponse(PublicationFlags):
    gates: list[GateResultModel]
    failing_gates: list[str]
    note: str
