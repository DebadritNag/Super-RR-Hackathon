"""Experimental endpoints under /api/v1. No endpoint accepts SQL or a filesystem path.

Rows-returning handlers (profiles, compare, rankings, selection) are registered twice from one
factory: on the public router (answers 403 PUBLICATION_GATE_NOT_SATISFIED with no rows unless every
publication gate passes) and on the ``/internal`` router (admin token required, always returns
rows labelled with ``publication_status`` and ``gate_results``). The single enforcement point is
``Phase4Service._gate``/``precheck`` (``app.phase5.gating.apply_gates``), not the route.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import Service, refuse_official, require_admin, require_internal
from app.api.errors import ApiError
from app.phase4 import uncapped as unc
from app.phase5 import classification_v2 as c2
from app.schemas import phase4 as sc
from app.schemas import phase5 as sc5

Format = Literal["IPL", "T20I", "COMBINED_w70_30"]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0, le=100000)]
Order = Literal["asc", "desc"]
RankSort = Literal["rank", "score", "name", "matches", "pressure_opportunities", "distinct_matches"]
PlayerSort = Literal["player_id", "name", "matches", "distinct_matches"]

ERRORS = {
    401: {"model": sc.ErrorResponse},
    403: {"model": sc.ErrorResponse},
    404: {"model": sc.ErrorResponse},
    422: {"model": sc.ErrorResponse},
    503: {"model": sc.ErrorResponse},
}

public = APIRouter(dependencies=[Depends(refuse_official)], responses=ERRORS)
internal = APIRouter(
    prefix="/internal",
    dependencies=[Depends(require_internal), Depends(refuse_official)],
    responses=ERRORS,
)
admin = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)], responses=ERRORS)

Disabled = sc5.StrictUncappedDisabledResponse


def filter_params(
    classification: unc.ClassificationFilter | None = None,
    uncapped_mode: unc.UncappedMode | None = None,
    min_matches: Annotated[int | None, Query(ge=0)] = None,
    min_pressure_matches: Annotated[int | None, Query(ge=0)] = None,
) -> unc.FilterParams:
    return unc.FilterParams(classification, uncapped_mode, min_matches, min_pressure_matches)


def public_filter_params(
    classification: unc.ClassificationFilter | None = None,
    uncapped_mode: unc.UncappedMode | None = None,
    min_matches: Annotated[int | None, Query(ge=0)] = None,
) -> unc.FilterParams:
    """Public directory filters: no pressure-count filter (it would leak experimental counts)."""
    return unc.FilterParams(classification, uncapped_mode, min_matches, None)


Filters = Annotated[unc.FilterParams, Depends(filter_params)]
PublicFilters = Annotated[unc.FilterParams, Depends(public_filter_params)]
Basis = Annotated[unc.ClassificationBasis, Query()]
DEFAULT_BASIS = unc.ClassificationBasis.INCLUDE_DERIVED_CAPPED


# ----------------------------------------------------------------------------- descriptive (public)
@public.get("/players", response_model=sc.PublicPlayerListResponse | sc.PublicDisabled)
def list_players(
    svc: Service,
    params: PublicFilters,
    basis: Basis = DEFAULT_BASIS,
    q: Annotated[str | None, Query(max_length=64)] = None,
    sort_by: PlayerSort = "player_id",
    order: Order = "asc",
    limit: Limit = 50,
    offset: Offset = 0,
):
    """Descriptive directory only: identity, classification and match counts. No scores."""
    return svc.players(params, basis, q, sort_by, order == "desc", limit, offset, public=True)


@public.get("/players/{player_id}", response_model=sc.PublicPlayerDetailResponse)
def player_detail(player_id: int, svc: Service, basis: Basis = DEFAULT_BASIS):
    return svc.player_detail(player_id, basis, public=True)


@internal.get("/players", response_model=sc.PlayerListResponse | Disabled)
def internal_list_players(
    svc: Service,
    params: Filters,
    basis: Basis = DEFAULT_BASIS,
    q: Annotated[str | None, Query(max_length=64)] = None,
    sort_by: PlayerSort = "player_id",
    order: Order = "asc",
    limit: Limit = 50,
    offset: Offset = 0,
):
    """Token-protected directory with eligibility scopes, conflict flag and publication flags."""
    return svc.players(params, basis, q, sort_by, order == "desc", limit, offset)


@internal.get("/players/{player_id}", response_model=sc.PlayerDetailResponse)
def internal_player_detail(player_id: int, svc: Service, basis: Basis = DEFAULT_BASIS):
    return svc.player_detail(player_id, basis)


@public.get("/selection/presets", response_model=sc.PresetListResponse)
def list_presets(svc: Service):
    """Parameter templates only (no player rows); availability reflects strict uncapped."""
    return {**svc.flags(), "items": svc.preset_catalog()}


@public.get("/meta/classification-coverage", response_model=sc.CoverageResponse)
def classification_coverage(svc: Service):
    return svc.coverage()


@public.get("/meta/capabilities", response_model=sc5.CapabilitiesResponse)
def capabilities(svc: Service):
    return svc.capabilities()


@public.get("/meta/publication-gates", response_model=sc5.PublicationGatesResponse)
def publication_gates(svc: Service):
    return svc.publication_gates()


# ----------------------------------------------------------------------------- gated handlers
def register_gated(router: APIRouter, is_internal: bool) -> None:
    @router.get("/players/{player_id}/profile", response_model=sc.ProfileResponse)
    def player_profile(
        player_id: int,
        svc: Service,
        basis: Basis = DEFAULT_BASIS,
        format: Format | None = None,
    ):
        return svc.profile(player_id, basis, format, is_internal)

    @router.get("/rankings/uncapped/{kind}", response_model=sc.UncappedRankingResponse | Disabled)
    def uncapped_ranking(
        kind: unc.UncappedKind,
        svc: Service,
        format: Format = "IPL",
        basis: Basis = DEFAULT_BASIS,
        min_matches: Annotated[int | None, Query(ge=0)] = None,
        min_pressure_matches: Annotated[int | None, Query(ge=0)] = None,
        include_unverified_list: bool = False,
        sort_by: RankSort = "rank",
        order: Order = "asc",
        limit: Limit = 50,
        offset: Offset = 0,
    ):
        return svc.uncapped_ranking(
            kind, format, basis, min_matches, min_pressure_matches, include_unverified_list,
            sort_by, order == "desc", limit, offset, is_internal,
        )  # fmt: skip

    @router.get("/rankings/{role}", response_model=sc.RankingResponse | Disabled)
    def ranking(
        role: Literal["batter", "bowler"],
        svc: Service,
        params: Filters,
        format: Format = "IPL",
        basis: Basis = DEFAULT_BASIS,
        include_ineligible: bool = False,
        sort_by: RankSort = "rank",
        order: Order = "asc",
        limit: Limit = 50,
        offset: Offset = 0,
    ):
        return svc.ranking(
            role, format, basis, params, include_ineligible, sort_by, order == "desc",
            limit, offset, is_internal,
        )  # fmt: skip

    @router.get("/compare", response_model=sc.CompareResponse)
    def compare(
        svc: Service,
        player_ids: Annotated[str, Query(max_length=64, pattern=r"^\d+(,\d+){0,4}$")],
        format: Format = "IPL",
        basis: Basis = DEFAULT_BASIS,
    ):
        ids = [int(x) for x in player_ids.split(",")]
        if len(set(ids)) != len(ids):
            raise ApiError(422, "VALIDATION_ERROR", "player_ids must be distinct")
        return svc.compare(ids, basis, format, is_internal)

    @router.post("/selection/custom", response_model=sc.SelectionResponse | Disabled)
    def custom_selection(body: sc.SelectionRequestModel, svc: Service):
        if body.official:
            raise ApiError(
                403, "OFFICIAL_RANKING_NOT_AUTHORIZED", "Official selections are not authorised."
            )
        req = body.model_dump(exclude_none=True, exclude={"official"})
        req["groups"] = {g: b.model_dump(exclude_none=True) for g, b in body.groups.items()}
        req["roles"] = {r: b.model_dump(exclude_none=True) for r, b in body.roles.items()}
        return svc.compose(req, internal=is_internal)

    @router.post("/selection/presets/{preset_id}", response_model=sc.SelectionResponse | Disabled)
    def run_preset(
        preset_id: Annotated[str, Path(max_length=64, pattern=r"^[a-z0-9_]+$")],
        svc: Service,
        body: sc.PresetRunModel | None = None,
    ):
        body = body or sc.PresetRunModel()
        if body.official:
            raise ApiError(
                403, "OFFICIAL_RANKING_NOT_AUTHORIZED", "Official selections are not authorised."
            )
        return svc.run_preset(preset_id, body.format, body.basis, body.min_matches, is_internal)


register_gated(public, False)
register_gated(internal, True)


# ----------------------------------------------------------------------------- admin
@admin.post("/classification/reload", response_model=sc.ReloadResponse)
def reload_classification(svc: Service):
    out = svc.repo.reload_classification()
    svc.reset_gates()
    return {"reloaded": True, **out}


@admin.get("/classification/overrides", response_model=sc.OverridesResponse)
def list_overrides(svc: Service):
    df = svc.repo.overrides()
    return {
        "count": int(len(df)),
        "items": df.to_dict(orient="records"),
        "version": c2.CLASSIFICATION_V2_VERSION,
    }
