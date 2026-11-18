"""Internal (token-protected) routes for the experimental statistical-model outputs.
``GET /api/v1/internal/model-status`` and ``GET /api/v1/internal/experimental-predictions``.
There is no public twin. The files are read per request into new objects.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import refuse_official, require_internal
from app.phase5.gating import RequestNeeds, evaluate_gates
from app.phase7 import ai_loader as al
from app.phase7 import ai_pipeline as ap
from app.schemas.phase7_ai import AiModelStatusResponse, AiPredictionsResponse

internal = APIRouter(
    prefix="/internal",
    tags=["internal-experimental-model"],
    dependencies=[Depends(require_internal), Depends(refuse_official)],
)


def _gates(request: Request) -> list[dict[str, Any]]:
    try:
        return [
            g.as_dict()
            for g in evaluate_gates(request.app.state.service.gate_input(), RequestNeeds())
        ]
    except Exception:  # noqa: BLE001 - an unreadable gate input must not expose anything else
        return []


def _reports(request: Request):
    return getattr(request.app.state, "ai_reports", None)


@internal.get("/model-status", response_model=AiModelStatusResponse)
def model_status(request: Request) -> AiModelStatusResponse:
    out = al.load_ai_outputs(_reports(request))
    return AiModelStatusResponse(
        gate_results=_gates(request),
        state=out["state"],
        reason=out["reason"],
        banner=out["banner"],
        model_label=out["model_label"],
        is_machine_learning=False,
        is_deep_learning=False,
        trained_artefact_exists=False,
        registry=out["registry"],
        test_opened_in_this_pipeline=False,
    )


@internal.get("/experimental-predictions", response_model=AiPredictionsResponse)
def experimental_predictions(
    request: Request,
    role: Annotated[Literal["batter", "bowler"] | None, Query()] = None,
) -> AiPredictionsResponse:
    out = al.load_ai_outputs(_reports(request))
    roles = {k: v for k, v in out["roles"].items() if role in (None, k)}
    return AiPredictionsResponse(
        gate_results=_gates(request),
        state=out["state"],
        reason=out["reason"],
        banner=out["banner"],
        model_label=out["model_label"],
        uncertainty_note=ap.NO_UNCERTAINTY,
        roles=roles,
    )
