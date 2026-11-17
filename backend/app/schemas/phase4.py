"""Pydantic v2 request and response schemas for the Phase 4 experimental API."""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.phase5 import PublicationFlags

T = TypeVar("T")

StatusLiteral = Literal["EXPERIMENTAL_NOT_VALIDATED"]
GroupName = Literal["IN_CAPPED", "IN_UNCAPPED", "OS_CAPPED", "OS_UNCAPPED", "UNKNOWN"]


class Flags(PublicationFlags):
    """Disclaimer and publication-gating fields present on every experimental response."""


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ClassifiedPlayer(BaseModel):
    player_id: int
    name: str
    nationality: str
    nationality_verification: str
    international_status: str
    international_status_verification: str


class ResultRow(ClassifiedPlayer):
    """One experimental ranking or selection row (requirement 6 fields)."""

    side: str
    format: str
    group: str
    group_label: str
    squad_role: str | None = None
    eligibility: str
    score: float | None = None
    standardised_score: float | None = None
    rank: int | None = None
    view_rank: int | None = None
    pressure_opportunities: int | None = None
    distinct_matches: int | None = None
    effective_sample_size: float | None = None
    interval_low: float | None = None
    interval_high: float | None = None
    top10_inclusion_prob: float | None = None
    rank_lo: float | None = None
    rank_hi: float | None = None
    matches: int = 0
    restrictions_applied: str | None = None
    status: StatusLiteral = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False


class RankingResponse(Flags):
    role: str
    format: str
    basis: str
    definition_id: str | None
    baseline_version: str | None
    shrinkage_config: str | None = None
    pool_size: int
    note: str
    page: Page[ResultRow]


class UncappedRankingResponse(RankingResponse):
    kind: str
    verified_uncapped_in_pool: int
    unverified_candidates: list[ResultRow] | None = None
    unverified_note: str | None = None


class PlayerRow(ClassifiedPlayer):
    group: str
    group_label: str
    squad_role: str | None = None
    matches: int
    distinct_matches: int | None = None
    eligible_scopes: str
    conflict_flag: bool
    status: StatusLiteral = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False


class PlayerListResponse(Flags):
    basis: str
    page: Page[PlayerRow]


class PlayerDetailResponse(Flags):
    player: PlayerRow
    nationality_source: str | None = None
    nationality_unknown_reason: str | None = None
    international_status_source: str | None = None
    international_status_unknown_reason: str | None = None
    derived_evidence: str | None = None
    first_t20i_date: str | None = None
    t20i_appearances_to_as_of: int = 0
    as_of_date: str | None = None
    classification_version: str | None = None


class PublicDescriptiveFlags(BaseModel):
    """Flags of the public player directory: descriptive data only.

    Deliberately has no publication status, gate results or ``official_ranking`` field: the public
    directory carries no score, rank, interval, eligibility or publication-implying information.
    """

    status: StatusLiteral = "EXPERIMENTAL_NOT_VALIDATED"
    disclaimer: str
    descriptive_only: Literal[True] = True


class PublicPlayerRow(ClassifiedPlayer):
    """Descriptive directory row: identity, classification (with verification) and match counts."""

    group: str
    group_label: str
    squad_role: str | None = None
    matches: int
    distinct_matches: int | None = None


class PublicPlayerListResponse(PublicDescriptiveFlags):
    basis: str
    page: Page[PublicPlayerRow]


class PublicPlayerDetailResponse(PublicDescriptiveFlags):
    player: PublicPlayerRow
    nationality_source: str | None = None
    nationality_unknown_reason: str | None = None
    international_status_source: str | None = None
    international_status_unknown_reason: str | None = None
    derived_evidence: str | None = None
    first_t20i_date: str | None = None
    t20i_appearances_to_as_of: int = 0
    as_of_date: str | None = None
    classification_version: str | None = None


class PublicDisabled(PublicDescriptiveFlags):
    """Public answer to a strict-uncapped directory request while strict uncapped is disabled."""

    result_status: Literal["STRICT_UNCAPPED_DISABLED"]
    reason: str
    source_needed: str
    request_kind: str


class RadarAxis(BaseModel):
    axis: str
    label: str
    formula: str
    unit: str
    higher_is_better: bool
    value: float | None
    reference_overall_n: int
    reference_uncapped_n: int
    percentile_overall: float | None
    percentile_uncapped: float | None
    label_overall: Literal["OK", "INSUFFICIENT_DATA"]
    label_uncapped: Literal["OK", "INSUFFICIENT_DATA"]
    reason_overall: str | None
    reason_uncapped: str | None


class Strength(BaseModel):
    axis: str
    percentile_overall: float
    evidence: str


class SideProfile(BaseModel):
    side: str
    format: str
    sample_size: dict[str, Any]
    descriptive: dict[str, int]
    pressure: dict[str, Any]
    radar: dict[str, Any]
    strengths: list[Strength]
    ranking_status: dict[str, Any]


class ProfileResponse(Flags):
    player: dict[str, Any]
    blocks: list[SideProfile]
    insufficient_data: dict[str, Any] | None = None


class CompareResponse(Flags):
    format: str
    items: list[ProfileResponse]


class BoundModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exact: int | None = Field(default=None, ge=0, le=50)
    min: int | None = Field(default=None, ge=0, le=50)
    max: int | None = Field(default=None, ge=0, le=50)


class SelectionRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int = Field(default=10, ge=1, le=50)
    groups: dict[GroupName, BoundModel] = Field(default_factory=dict)
    roles: dict[str, BoundModel] = Field(default_factory=dict)
    allow_fewer: bool = False
    format: Literal["IPL", "T20I", "COMBINED_w70_30"] = "IPL"
    basis: Literal["INCLUDE_DERIVED_CAPPED", "VERIFIED_ONLY"] = "INCLUDE_DERIVED_CAPPED"
    side: Literal["batter", "bowler"] | None = None
    uncapped_mode: Literal["include_uncapped", "exclude_uncapped"] | None = None
    min_matches: int | None = Field(default=None, ge=0)
    min_pressure_matches: int | None = Field(default=None, ge=0)
    official: bool = False


class PresetRunModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["IPL", "T20I", "COMBINED_w70_30"] = "IPL"
    basis: Literal["INCLUDE_DERIVED_CAPPED", "VERIFIED_ONLY"] = "INCLUDE_DERIVED_CAPPED"
    min_matches: int | None = Field(default=None, ge=0)
    official: bool = False


class Explanation(BaseModel):
    constraint: str
    required: int
    available: int
    message: str


class SelectionResponse(Flags):
    selection_status: Literal["OK", "PARTIAL", "INFEASIBLE", "POOL_TOO_SMALL"]
    preset_id: str | None = None
    requested_total: int
    size: int
    total_standardised_score: float | None
    message: str | None = None
    selected: list[ResultRow]
    explanations: list[Explanation]
    available_by_group: dict[str, int]
    available_by_role: dict[str, int]
    excluded_unknown_role: int
    pool_size: int
    request: dict[str, Any]


class PresetInfo(BaseModel):
    preset_id: str
    name: str
    description: str
    request: dict[str, Any]
    depends_on_verified_classification: bool
    available: bool = True
    unavailable_reason: str | None = None


class PresetListResponse(Flags):
    items: list[PresetInfo]


class CoverageResponse(Flags):
    coverage: dict[str, Any]
    strict_uncapped: dict[str, Any]
    unresolved_players: int
    note: str


class OverrideRow(BaseModel):
    player_id: int
    field: str
    value: str
    source: str
    verified_by: str
    verified_date: str


class OverridesResponse(BaseModel):
    count: int
    items: list[OverrideRow]
    version: str


class ReloadResponse(BaseModel):
    reloaded: bool
    overrides_applied: int
    players: int
    uncapped_verified_count: int
    strict_uncapped_enabled: bool
