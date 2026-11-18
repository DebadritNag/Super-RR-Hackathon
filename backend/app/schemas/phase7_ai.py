"""Response models of the internal experimental-model routes (token-protected only)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.phase5 import GateResultModel


class AiRolePredictions(BaseModel):
    rows: list[dict[str, Any]]
    rows_written: int
    short_list: bool


class AiPredictionsResponse(BaseModel):
    status: Literal["EXPERIMENTAL_NOT_VALIDATED"] = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False
    publication_status: Literal["INTERNAL_EXPERIMENTAL_ONLY"] = "INTERNAL_EXPERIMENTAL_ONLY"
    gate_results: list[GateResultModel]
    state: Literal["AVAILABLE", "INSUFFICIENT_DATA", "LOCKED"]
    reason: str
    banner: str
    model_label: str
    uncertainty_note: str
    roles: dict[str, AiRolePredictions]


class AiModelStatusResponse(BaseModel):
    status: Literal["EXPERIMENTAL_NOT_VALIDATED"] = "EXPERIMENTAL_NOT_VALIDATED"
    official_ranking: Literal[False] = False
    publication_status: Literal["INTERNAL_EXPERIMENTAL_ONLY"] = "INTERNAL_EXPERIMENTAL_ONLY"
    gate_results: list[GateResultModel]
    state: Literal["AVAILABLE", "INSUFFICIENT_DATA", "LOCKED"]
    reason: str
    banner: str
    model_label: str
    is_machine_learning: bool
    is_deep_learning: bool
    trained_artefact_exists: bool
    registry: dict[str, Any] | None
    test_opened_in_this_pipeline: bool
