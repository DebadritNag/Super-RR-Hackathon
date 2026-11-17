"""Pydantic v2 schemas of the public descriptive endpoints (Phase 7).

No field of these models may carry a score, rank, eligibility, publication or pressure-gate
meaning (checked by ``tests/test_phase7_descriptive_api.py`` with the Phase 6 field walker).
Percentiles are positions of a raw value inside a named cohort, not merit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Status = Literal["DESCRIPTIVE_NOT_A_PRESSURE_MEASURE"]
DISCLAIMER = (
    "Descriptive statistics from official ball-by-ball data. They describe what happened and are "
    "not a measure of performance under pressure, not an ordering of players and not an "
    "auction-suitability statement."
)
Format = Literal["IPL", "T20I"]
Side = Literal["batter", "bowler"]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DescriptiveFlags(Base):
    status: Status = "DESCRIPTIVE_NOT_A_PRESSURE_MEASURE"
    disclaimer: str = DISCLAIMER
    descriptive_only: bool = True


class Page(Base):
    total: int
    limit: int
    offset: int


class Split(Base):
    key: str
    label: str
    balls: int | None = None
    runs: int | None = None
    outs: int | None = None
    rate: float | None = None
    rate_name: str
    unavailable_reason: str | None = None


class ContextSample(Base):
    balls: int
    matches: int
    label: str
    definition: str


class Provenance(Base):
    descriptive_version: str
    window: str
    state_version: str
    official_db_sha256: str
    analytical_store_sha256: str


class Quality(Base):
    sample_sufficiency: str
    sample_note: str | None = None
    dls_rows: int
    anomaly_rows: int
    extras_other_rows: int
    missing_value_notes: list[str]
    mapping_warnings: list[str]
    caveat_dls: str


class ProfileBase(Base):
    player_id: int
    player_name: str | None = None
    side: Side
    format: Format
    participation_role: str | None = None
    squad_role_listed: str | None = None
    nationality: str | None = None
    nationality_verification: str | None = None
    international_status: str | None = None
    international_status_verification: str | None = None
    seasons_covered: list[str]
    matches_played: int | None = None
    matches_with_participation: int
    opportunities_innings: int
    fours: int
    sixes: int
    boundary_runs: int | None = None
    dot_balls: int
    dot_ball_share: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    ci_metric: str
    ci_unavailable_reason: str | None = None
    ci_method: str
    splits: list[Split]
    context_sample: ContextSample
    quality: Quality
    provenance: Provenance


class BatterProfile(ProfileBase):
    side: Literal["batter"] = "batter"
    balls_faced: int
    runs: int | None = None
    dismissals: int
    strike_rate: float | None = None
    average: float | None = None
    balls_per_dismissal: float | None = None
    boundary_run_share: float | None = None
    boundary_ball_share: float | None = None


class BowlerProfile(ProfileBase):
    side: Literal["bowler"] = "bowler"
    legal_balls: int
    overs: str | None = None
    runs_conceded: int | None = None
    wickets: int
    economy: float | None = None
    balls_per_wicket: float | None = None
    boundary_conceded_share: float | None = None
    wides: int | None = None
    no_balls: int | None = None
    extras_charged_runs: int | None = None
    bowling_style_modal: str | None = None
    bowling_style_modal_share: float | None = None
    pace_or_spin_modal: str | None = None


class BatterListResponse(DescriptiveFlags):
    page: Page
    items: list[BatterProfile]
    sort_note: str


class BowlerListResponse(DescriptiveFlags):
    page: Page
    items: list[BowlerProfile]
    sort_note: str


class PlayerProfileResponse(DescriptiveFlags):
    player_id: int
    player_name: str | None = None
    batting: list[BatterProfile]
    bowling: list[BowlerProfile]
    explanations: list[str]
    limitations: list[str]


# ----------------------------------------------------------------------------- compare
class CompareValue(Base):
    player_id: int
    value: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    matches: int
    ci_low: float | None = None
    ci_high: float | None = None
    unavailable_reason: str | None = None


class PairDifference(Base):
    player_a: int
    player_b: int
    difference: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    evidence: Literal["SUPPORTED", "NOT_DISTINGUISHABLE", "LOW_SAMPLE", "UNAVAILABLE"]
    text: str


class MetricComparison(Base):
    metric: str
    label: str
    unit: str
    formula: str
    values: list[CompareValue]
    differences: list[PairDifference]


class ComparedPlayer(Base):
    player_id: int
    player_name: str | None = None
    balls: int
    matches: int
    sample_sufficiency: str


class CompareResponse(DescriptiveFlags):
    side: Side
    format: Format
    players: list[ComparedPlayer]
    metrics: list[MetricComparison]
    summary: list[str]
    limitations: list[str]
    method: str


# ----------------------------------------------------------------------------- radar
class RadarDimension(Base):
    key: str
    label: str
    unit: str
    raw_value: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    min_denominator: int
    available: bool
    percentile_in_cohort: float | None = None
    cohort_size: int
    unavailable_reason: str | None = None


class RadarPlayer(Base):
    player_id: int
    player_name: str | None = None
    dimensions: list[RadarDimension]


class RadarResponse(DescriptiveFlags):
    side: Side
    format: Format
    cohort_name: str
    cohort_definition: str
    percentile_definition: str
    players: list[RadarPlayer]
    notes: list[str]


# ----------------------------------------------------------------------------- overview
class MatchesByCompetition(Base):
    competition_type: str
    matches: int
    matches_with_deliveries: int
    first_date: str
    last_date: str


class LineageRow(Base):
    file_name: str
    role: str
    row_count: int
    sha256: str
    load_status: str


class FormatScope(Base):
    format: str
    matches: int
    delivery_rows: int
    batter_profiles: int
    bowler_profiles: int


class PendingInput(Base):
    item: str
    status: str
    handling: str


class ReliabilityCheck(Base):
    check_id: str
    label: str
    observed: str
    threshold: str
    status: str


class OverviewResponse(DescriptiveFlags):
    matches_total: int
    delivery_rows_total: int
    matches_by_competition: list[MatchesByCompetition]
    descriptive_window: str
    scope_by_format: list[FormatScope]
    players_with_any_profile: int
    match_periods: dict[str, int]
    rows_in_innings_3_4_excluded: int
    rows_out_of_scope_competition: int
    late_t20i_dates_unverified: int
    lineage: list[LineageRow]
    pending_official_inputs: list[PendingInput]
    reliability_checks: list[ReliabilityCheck]
    lists_available: bool
    why_no_ordered_lists: list[str]
    descriptive_hashes: dict[str, str]


class MethodologySection(Base):
    title: str
    text: str


class MethodologyResponse(DescriptiveFlags):
    sections: list[MethodologySection]
    reliability_facts: dict[str, float | int | dict]
    primary_definition_id: str
    primary_definition_label: str
    profile_columns_note: str
