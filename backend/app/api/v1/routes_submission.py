"""Public read-only submission routes under ``/api/v1/submission`` and one token-protected
internal route for the experimental AI output.

The submitted Top 10 lists are public because the competition requires them, but every response
carries its status label and caveats. Nothing here writes, and no request value reaches SQL text.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.deps import refuse_official, require_internal
from app.api.errors import ApiError
from app.phase5.gating import RequestNeeds, evaluate_gates
from app.schemas import phase8_submission as sc
from app.services.submission_service import SubmissionService

public = APIRouter(
    prefix="/submission", tags=["submission"], dependencies=[Depends(refuse_official)]
)
internal = APIRouter(
    prefix="/internal",
    tags=["internal-experimental-ai"],
    dependencies=[Depends(require_internal), Depends(refuse_official)],
)


def get_submission(request: Request) -> SubmissionService:
    return request.app.state.submission


def old_gates(request: Request) -> list[dict[str, Any]]:
    """Phase 5 gates of the old engine, reported unchanged (they do not gate Phase 8 lists)."""
    try:
        return [
            g.as_dict()
            for g in evaluate_gates(request.app.state.service.gate_input(), RequestNeeds())
        ]
    except Exception:  # noqa: BLE001 - an unreadable gate input must not break the response
        return []


Svc = Annotated[SubmissionService, Depends(get_submission)]
Gates = Annotated[list[dict[str, Any]], Depends(old_gates)]
RoleP = Annotated[Literal["batters", "bowlers"], Path(description="batters or bowlers")]
PlayerP = Annotated[int, Path(ge=1)]
FormatQ = Annotated[Literal["IPL", "T20I"] | None, Query(description="formats are never pooled")]


@public.get("/overview", response_model=sc.OverviewResponse)
def overview(svc: Svc, gates: Gates) -> dict:
    return {**svc.overview(), "gate_results": gates}


@public.get("/top10/{role}", response_model=sc.Top10Response)
def top10(role: RoleP, svc: Svc, gates: Gates) -> dict:
    return {**svc.top10(role), "gate_results": gates}


@public.get("/players/{role}/{player_id}", response_model=sc.PlayerEvidenceResponse)
def player_evidence(role: RoleP, player_id: PlayerP, svc: Svc, gates: Gates) -> dict:
    return {**svc.player_evidence(role, player_id), "gate_results": gates}


@public.get("/why/{role}", response_model=sc.WhyResponse)
def why(
    role: RoleP,
    svc: Svc,
    gates: Gates,
    kind: Annotated[Literal["SELECTED", "NEAR_MISS", "RAW_STANDOUT"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return {**svc.why(role, kind, limit, offset), "gate_results": gates}


@public.get("/methodology", response_model=sc.MethodologyResponse)
def methodology(svc: Svc, gates: Gates) -> dict:
    return {**svc.methodology(), "gate_results": gates}


@public.get("/validation", response_model=sc.ValidationResponse)
def validation(svc: Svc, gates: Gates) -> dict:
    return {**svc.validation(), "gate_results": gates}


@public.get("/profiles/{role}", response_model=sc.ProfilesResponse)
def profiles(
    role: RoleP,
    svc: Svc,
    gates: Gates,
    format: FormatQ = None,  # noqa: A002 - public query name
    q: Annotated[str | None, Query(max_length=60)] = None,
    min_volume: Annotated[int, Query(ge=0, le=100000)] = 0,
    sort_by: Annotated[
        Literal["player_name", "player_id", "volume", "matches_played"],
        Query(description="identity or volume only"),
    ] = "player_name",
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return {
        **svc.profiles(role, format, q, min_volume, sort_by, order, limit, offset),
        "gate_results": gates,
    }


@public.get("/compare/{role}", response_model=sc.CompareResponse)
def compare(
    role: RoleP,
    svc: Svc,
    gates: Gates,
    player_ids: Annotated[str, Query(description="2 to 4 comma-separated player ids")],
    format: FormatQ = None,  # noqa: A002
) -> dict:
    try:
        ids = [int(x) for x in player_ids.split(",") if x.strip()]
    except ValueError as exc:
        raise ApiError(
            422, "INVALID_REQUEST", "player_ids must be comma-separated integers"
        ) from exc
    if not 2 <= len(ids) <= 4 or len(set(ids)) != len(ids) or any(i <= 0 for i in ids):
        raise ApiError(422, "INVALID_REQUEST", "provide 2 to 4 distinct positive player ids")
    return {**svc.compare(role, ids, format), "gate_results": gates}


@public.get("/radar/{role}/{player_id}", response_model=sc.RadarResponse)
def radar(
    role: RoleP,
    player_id: PlayerP,
    svc: Svc,
    gates: Gates,
    format: Annotated[Literal["IPL", "T20I"], Query()] = "IPL",  # noqa: A002
) -> dict:
    return {**svc.radar(role, player_id, format), "gate_results": gates}


@internal.get("/experimental-ai/{role}", response_model=sc.ExperimentalAiResponse)
def experimental_ai(role: RoleP, svc: Svc, gates: Gates) -> dict:
    return {**svc.experimental_ai(role), "gate_results": gates}
