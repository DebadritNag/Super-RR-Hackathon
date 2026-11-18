"""Public ``GET /api/v1/rr/analysis``: the generated RR historical-performance tables.

Descriptive only, no token. The file is validated into fresh model objects on every request, so
a caller cannot alter a later response.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from app.api.deps import refuse_official
from app.api.errors import ApiError
from app.schemas.rr import RRAnalysis

public = APIRouter(prefix="/rr", tags=["rr"], dependencies=[Depends(refuse_official)])
FILE = "rr_analysis_tables.json"


@public.get("/analysis", response_model=RRAnalysis)
def rr_analysis(request: Request) -> RRAnalysis:
    path = Path(request.app.state.descriptive.reports) / FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ApiError(
            503,
            "RR_ANALYSIS_UNAVAILABLE",
            "rr_analysis_tables.json is missing; run scripts/rr_analysis.py",
            str(exc),
        ) from exc
    return RRAnalysis.model_validate(raw)
