"""Pydantic v2 schema of the public ``GET /api/v1/rr/analysis`` endpoint (descriptive only).

No field carries a score, rank, eligibility, publication or pressure meaning. The payload is the
generated ``rr_analysis_tables.json`` and nothing is computed per request.
"""

from __future__ import annotations

from typing import Any

from app.schemas.phase7 import Base, DescriptiveFlags


class Team(Base):
    team_id: int
    team_name: str


class Comparison(Base):
    metric: str
    label: str
    side: str
    unit: str
    period: str
    rr_matches: int
    league_matches: int
    rr_numerator: float
    rr_balls: float
    rr_value: float | None
    league_numerator: float
    league_balls: float
    league_value: float | None
    difference: float | None
    ci_low: float | None
    ci_high: float | None
    direction: int
    assessment: str


class BowlerDepth(Base):
    season: str
    kind: str
    rr_bowlers: int
    league_mean: float
    league_min: int
    league_max: int
    min_balls: int


class Retention(Base):
    list_received: bool
    rows: int
    retained_excluded: int


class CandidateTable(Base):
    title: str
    min_balls: int
    n: int
    ordering: str
    rows: list[dict[str, Any]]


class RRAnalysis(DescriptiveFlags):
    version: str
    team: Team
    seed: int
    n_boot: int
    ci_level: float
    min_rr_balls: int
    primary_window: str
    scope: dict[str, Any]
    scope_rule: str
    provenance: dict[str, str]
    excluded_matches_with_deliveries: list[dict[str, Any]]
    season_results: list[dict[str, Any]]
    knockout_matches: list[dict[str, Any]]
    ipl_knockout_counts: list[dict[str, Any]]
    data_quality: dict[str, Any]
    comparisons: list[Comparison]
    bowler_depth: list[BowlerDepth]
    retention: Retention
    candidate_fit_tables: dict[str, CandidateTable]
    candidate_statement: str
