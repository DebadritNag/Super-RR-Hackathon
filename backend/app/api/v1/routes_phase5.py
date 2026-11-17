"""Dynamic filter-driven ranking endpoints (Phase 5, internal and experimental).

Internal routes (``/api/v1/internal/...``) need the admin/internal token and always return rows
labelled with ``publication_status`` and ``gate_results``. The public twins
(``/api/v1/dynamic-rankings...``) pass through the same service and answer 403
``PUBLICATION_GATE_NOT_SATISFIED`` with no rows unless every gate passes. No endpoint accepts SQL,
a column name or a path: the request body is the strict ``FilterSpec`` and query filters are
enumerated literals.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import Service5, refuse_official, require_internal
from app.phase5.filters import FilterSpec
from app.schemas import phase4 as sc
from app.schemas import phase5 as sc5
from app.schemas import phase5_dynamic as sd

ERRORS = {
    401: {"model": sc.ErrorResponse},
    403: {"model": sc.ErrorResponse},
    422: {"model": sc.ErrorResponse},
    503: {"model": sc.ErrorResponse},
}
internal = APIRouter(
    prefix="/internal",
    dependencies=[Depends(require_internal), Depends(refuse_official)],
    responses=ERRORS,
)
public = APIRouter(dependencies=[Depends(refuse_official)], responses=ERRORS)
Disabled = sc5.StrictUncappedDisabledResponse

Fmt = Literal["IPL", "T20I", "COMBINED_w70_30"]
Role = Literal["batter", "bowler"]
Phase = Literal["ALL", "powerplay", "middle", "death"]
Situation = Literal["ALL", "chase", "first_innings"]
Nationality = Literal["Indian", "Overseas", "Unknown"]
# Three real status filters plus the disabled placeholder VERIFIED_UNCAPPED (always answered with
# STRICT_UNCAPPED_DISABLED while strict uncapped selection is disabled).
Status = Literal[
    "CAPPED_ANY", "VERIFIED_CAPPED", "DERIVED_CAPPED", "VERIFIED_UNCAPPED", "UNKNOWN_STATUS"
]


def coverage_filters(
    format: Fmt | None = None,
    role: Role | None = None,
    phase: Phase | None = None,
    situation: Situation | None = None,
    nationality: Nationality | None = None,
    status: Status | None = None,
    meets_internal_min: bool | None = None,
    result_status: Literal["RANKED", "FEWER_THAN_LIST_SIZE", "EMPTY", "STRICT_UNCAPPED_DISABLED"]
    | None = None,
) -> dict[str, object]:
    return {
        "format": format, "role": role, "phase": phase, "situation": situation,
        "nationality": nationality, "status": status,
        "meets_internal_min": meets_internal_min, "result_status": result_status,
    }  # fmt: skip


CoverageFilters = Annotated[dict[str, object], Depends(coverage_filters)]
CovLimit = Annotated[int, Query(ge=1, le=200)]
CovOffset = Annotated[int, Query(ge=0, le=100000)]


def register(router: APIRouter, is_internal: bool, prefix: str) -> None:
    @router.post(f"{prefix}", response_model=sd.DynamicRankingResponse | Disabled)
    def dynamic_ranking(spec: FilterSpec, svc: Service5):
        return svc.ranking(spec, is_internal)

    @router.post(f"{prefix}/context-preview", response_model=sd.ContextPreviewResponse | Disabled)
    def context_preview(spec: FilterSpec, svc: Service5):
        return svc.context_preview(spec, is_internal)

    @router.get(f"{prefix}/coverage", response_model=sd.CoverageResponse)
    def coverage(
        svc: Service5, filters: CoverageFilters, limit: CovLimit = 50, offset: CovOffset = 0
    ):
        return svc.coverage(filters, limit, offset, is_internal)


register(internal, True, "/rankings/dynamic")
register(public, False, "/dynamic-rankings")


@internal.get("/filters/catalog", response_model=sd.CatalogResponse)
def filter_catalog(svc: Service5):
    return svc.filter_catalog()
