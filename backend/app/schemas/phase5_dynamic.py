"""Pydantic v2 response schemas of the dynamic filter-driven ranking endpoints (Phase 5)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.phase5 import PublicationFlags

ResultStatus = Literal["RANKED", "FEWER_THAN_LIST_SIZE", "EMPTY", "STRICT_UNCAPPED_DISABLED"]


class ReasonModel(BaseModel):
    code: str
    count: int
    detail: str


class ComponentModel(BaseModel):
    n: int
    matches: int
    n_eff: float
    k: float
    shrinkage_weight: float
    threshold_balls: int | None
    fit_floor_hit: bool


class DynamicRow(BaseModel):
    rank: int
    player_id: int
    name: str | None
    score: float
    raw: float
    expected: float
    residual: float
    shrunk: float
    interval_low: float | None
    interval_high: float | None
    rank_lo: float | None
    rank_median: float | None
    rank_hi: float | None
    top10_inclusion_prob: float | None
    n: int
    matches: int
    n_eff: float
    shrinkage_weight: float
    fit_floor_hit: bool
    eligibility_status: str
    eligibility_label: str
    eligibility_thresholds: dict[str, int | None]
    components: dict[str, ComponentModel]
    restrictions_applied: str | None
    nationality: str
    nationality_verification: str | None
    international_status: str
    international_status_verification: str | None
    classification_match: Literal["NOT_FILTERED", "EXACT", "UNKNOWN_INCLUDED"]
    career_matches: int


class RowPage(BaseModel):
    items: list[DynamicRow]
    total: int
    limit: int
    offset: int


class VersionsModel(BaseModel):
    definition_id: str | None
    definition_label: str
    baseline_version: str | None
    shrinkage_config: str | None
    model_version: str
    data_version: str
    config_hashes: dict[str, str]
    interval_level: float
    n_boot: int
    seed: int


class DynamicBase(PublicationFlags):
    result_status: ResultStatus
    spec_hash: str
    filter_echo: dict[str, Any]
    pool_size: int
    reasons: list[ReasonModel]
    stage_counts: dict[str, int | None]
    excluded_counts: dict[str, int]
    context_status: dict[str, str]
    context_data_weight: dict[str, dict[str, Any]]
    versions: VersionsModel
    note: str


class DynamicRankingResponse(DynamicBase):
    cache_hit: bool
    low_data_weight: bool
    page: RowPage


class ContextPreviewResponse(DynamicBase):
    qualifying_players: int
    would_return_rows: bool
    cache_hit: bool = False


class CoverageRow(BaseModel):
    spec_hash: str
    format: str
    role: str
    nationality: str | None
    status: str | None
    phase: str
    situation: str
    include_unknown_nationality: bool
    include_unknown_status: bool
    result_status: str
    enabled: bool
    context_status: str | None
    players_in_context: int | None
    eligible_in_context: int | None
    after_nationality: int | None
    after_status: int | None
    final_pool: int
    reason_codes: str | None
    excluded_unknown_nationality: int | None
    excluded_unknown_status: int | None
    min_internal_pool: int
    min_public_pool: int
    meets_internal_min: bool
    meets_public_min: bool


class CoverageItems(BaseModel):
    items: list[CoverageRow]
    total: int
    limit: int
    offset: int


class CoverageResponse(PublicationFlags):
    coverage_source: Literal["STORED_TABLE", "RECOMPUTED_CLASSIFICATION_CHANGED"]
    minimum_pool_rule: dict[str, Any]
    summary: dict[str, int]
    page: CoverageItems
    note: str


class CatalogItem(BaseModel):
    value: str
    enabled: bool
    reason: str | None


class CatalogResponse(PublicationFlags):
    filters: dict[str, list[CatalogItem]]
    strict_uncapped_enabled: bool
    semantics: dict[str, str]
    cache: dict[str, int]
    versions: dict[str, Any] = Field(default_factory=dict)
