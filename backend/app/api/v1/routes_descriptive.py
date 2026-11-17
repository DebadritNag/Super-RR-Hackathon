"""Public descriptive endpoints under ``/api/v1/descriptive`` (no token, no score, no ordering).

The prefix keeps these routes apart from the publication-gated pressure routes, one of which
(``/compare``) already exists with a different meaning.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.deps import refuse_official
from app.api.errors import ApiError
from app.phase7 import views as vw
from app.schemas import phase7 as sc
from app.services.descriptive_service import DescriptiveService

public = APIRouter(
    prefix="/descriptive", tags=["descriptive"], dependencies=[Depends(refuse_official)]
)


def get_descriptive(request: Request) -> DescriptiveService:
    return request.app.state.descriptive


Svc = Annotated[DescriptiveService, Depends(get_descriptive)]
Fmt = Annotated[sc.Format | None, Query(description="IPL or T20I (formats are never pooled)")]
SortBy = Annotated[
    str,
    Query(
        pattern="^(player_name|player_id|matches_played|volume)$",
        description="identity or volume only",
    ),
]
Order = Annotated[str, Query(pattern="^(asc|desc)$")]


def _ids(raw: str) -> list[int]:
    try:
        ids = [int(x) for x in raw.split(",") if x.strip() != ""]
    except ValueError as exc:
        raise ApiError(
            422, "INVALID_REQUEST", "player_ids must be comma-separated integers"
        ) from exc
    if any(i <= 0 for i in ids):
        raise ApiError(422, "INVALID_REQUEST", "player ids are positive integers")
    return ids


def _listing(
    svc: DescriptiveService,
    side: str,
    fmt: str | None,
    q: str | None,
    nationality: str | None,
    min_balls: int,
    sort_by: str,
    order: str,
    limit: int,
    offset: int,
):
    params = dict(
        side=side,
        fmt=fmt,
        q=q,
        nationality=nationality,
        min_balls=min_balls,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return svc.cached(
        "list",
        params,
        lambda: vw.list_profiles(
            svc.data, side, fmt, q, nationality, min_balls, sort_by, order, limit, offset
        ),
    )


@public.get("/profiles/batters", response_model=sc.BatterListResponse)
def batters(
    svc: Svc,
    format: Fmt = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
    nationality: Annotated[str | None, Query(pattern="^(Indian|Overseas|Unknown)$")] = None,
    min_balls: Annotated[int, Query(ge=0, le=100000)] = 0,
    sort_by: SortBy = "player_name",
    order: Order = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    return _listing(svc, "batter", format, q, nationality, min_balls, sort_by, order, limit, offset)


@public.get("/profiles/bowlers", response_model=sc.BowlerListResponse)
def bowlers(
    svc: Svc,
    format: Fmt = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
    nationality: Annotated[str | None, Query(pattern="^(Indian|Overseas|Unknown)$")] = None,
    min_balls: Annotated[int, Query(ge=0, le=100000)] = 0,
    sort_by: SortBy = "player_name",
    order: Order = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    return _listing(svc, "bowler", format, q, nationality, min_balls, sort_by, order, limit, offset)


@public.get("/profiles/{player_id}", response_model=sc.PlayerProfileResponse)
def player(svc: Svc, player_id: Annotated[int, Path(ge=1)]):
    return svc.cached(
        "player", {"player_id": player_id}, lambda: vw.player_profile(svc.data, player_id)
    )


@public.get("/compare", response_model=sc.CompareResponse)
def compare(
    svc: Svc,
    player_ids: Annotated[str, Query(max_length=60, description="2 to 4 comma-separated ids")],
    side: sc.Side = "batter",
    format: sc.Format = "IPL",
):
    ids = _ids(player_ids)
    return svc.cached(
        "compare",
        {"ids": ids, "side": side, "format": format},
        lambda: vw.compare_players(svc.data, side, format, ids),
    )


@public.get("/radar", response_model=sc.RadarResponse)
def radar(
    svc: Svc,
    player_ids: Annotated[str, Query(max_length=60, description="1 to 4 comma-separated ids")],
    side: sc.Side = "batter",
    format: sc.Format = "IPL",
):
    ids = _ids(player_ids)
    return svc.cached(
        "radar",
        {"ids": ids, "side": side, "format": format},
        lambda: vw.radar(svc.data, side, format, ids),
    )


@public.get("/overview", response_model=sc.OverviewResponse)
def overview(svc: Svc):
    return svc.cached("overview", {}, lambda: vw.overview(svc.data))


@public.get("/methodology/summary", response_model=sc.MethodologyResponse)
def methodology(svc: Svc):
    return svc.cached("methodology", {}, lambda: vw.methodology(svc.data))
