"""Pydantic v2 response models of the read-only ``/api/v1/submission/*`` routes.

Every response carries ``status_label`` and ``caveats``. ``validated`` is always False: no list or
model in this project has reached the predeclared VALIDATED criteria.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.phase5 import GateResultModel

StatusLabel = Literal[
    "VALIDATED",
    "PROVISIONAL",
    "EXPLORATORY",
    "INSUFFICIENT_EVIDENCE",
    "DESCRIPTIVE_ONLY",
    "EXPERIMENTAL_NOT_VALIDATED",
]
Role = Literal["batters", "bowlers"]


class Stamped(BaseModel):
    """Common envelope: a status label and the caveats a reader must see."""

    model_config = ConfigDict(extra="forbid")

    status_label: StatusLabel
    validated: Literal[False] = False
    caveats: list[str]
    data_version: dict[str, Any] = Field(default_factory=dict)
    publication_status: Literal[
        "COMPETITION_SUBMISSION_NOT_VALIDATED", "INTERNAL_EXPERIMENTAL_ONLY"
    ] = "COMPETITION_SUBMISSION_NOT_VALIDATED"
    gate_results: list[GateResultModel] = Field(
        default_factory=list,
        description=(
            "Phase 5 publication gates of the OLD ranking engine, reported unchanged for "
            "reference. They do not gate the Phase 8 submission lists, whose status is "
            "status_label."
        ),
    )


class Page(BaseModel):
    total: int
    limit: int
    offset: int


class ListStatus(BaseModel):
    role: str
    list_status: StatusLabel
    model_validation_status: str
    approach: str
    rank_basis: str | None = None
    n_eligible: int | None = None
    list_length: int | None = None
    shortfall: str | None = None
    banner: str
    reason: str
    combination_basis: str | None = None
    intensity_basis: str | None = None


class OverviewResponse(Stamped):
    lists: list[ListStatus]
    approaches_compared: list[dict[str, Any]]
    files: list[dict[str, Any]]
    navigation: list[str]


class Top10Response(Stamped):
    role: Role
    list_status: ListStatus
    rows: list[dict[str, Any]]


class PlayerEvidenceResponse(Stamped):
    role: Role
    player_id: int
    player_name: str | None
    selection_state: Literal["SELECTED", "NOT_SELECTED_ELIGIBLE", "NOT_ELIGIBLE", "NOT_IN_POOL"]
    top10_row: dict[str, Any] | None
    explanations: list[dict[str, Any]]
    estimate: dict[str, Any] | None
    ineligibility: dict[str, Any] | None
    descriptive: list[dict[str, Any]]


class WhyResponse(Stamped):
    role: Role
    kind: str | None
    page: Page
    rows: list[dict[str, Any]]


class MethodologyResponse(Stamped):
    role_selection: list[dict[str, Any]]
    approach_comparison: list[dict[str, Any]]
    pressure_definitions: list[dict[str, Any]]
    documents: list[dict[str, Any]]


class ValidationResponse(Stamped):
    reliability: list[dict[str, Any]]
    win_probability: list[dict[str, Any]]
    win_probability_calibration: list[dict[str, Any]]
    expected_outcome_models: list[dict[str, Any]]
    gates: list[dict[str, Any]]
    sensitivity: list[dict[str, Any]]
    phase6: dict[str, Any] | None
    ai_verification: dict[str, Any] | None


class ProfilesResponse(Stamped):
    role: Role
    page: Page
    rows: list[dict[str, Any]]


class CompareResponse(Stamped):
    role: Role
    players: list[dict[str, Any]]
    superiority_claim: Literal["NOT_MADE"] = "NOT_MADE"
    superiority_note: str


class RadarDimension(BaseModel):
    key: str
    label: str
    value: float | None
    denominator: float | None
    denominator_label: str
    cohort_percentile: float | None
    higher_is_better: bool
    available: bool
    unavailable_reason: str | None = None


class RadarResponse(Stamped):
    role: Role
    player_id: int
    player_name: str
    format: str
    normalisation_cohort: str
    cohort_size: int
    composite: None = None
    dimensions: list[RadarDimension]


class ExperimentalAiResponse(Stamped):
    publication_status: Literal["INTERNAL_EXPERIMENTAL_ONLY"] = "INTERNAL_EXPERIMENTAL_ONLY"
    role: Role
    model_note: str
    state: Literal["AVAILABLE", "INSUFFICIENT_DATA"]
    rows: list[dict[str, Any]]
    artefacts: list[dict[str, Any]]
