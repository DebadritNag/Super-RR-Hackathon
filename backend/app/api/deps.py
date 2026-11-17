"""Dependencies: service access, official-ranking refusal, admin token protection."""

from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Depends, Header, Query, Request

from app.api.errors import ApiError
from app.services.phase4_service import Phase4Service
from app.services.phase5_service import Phase5Service

ADMIN_ENV = "SUPERR_ADMIN_TOKEN"


def get_service(request: Request) -> Phase4Service:
    return request.app.state.service


def get_service5(request: Request) -> Phase5Service:
    return request.app.state.service5


def refuse_official(
    official: Annotated[bool, Query(description="Any true value is refused")] = False,
    publish: Annotated[bool, Query(description="Any true value is refused")] = False,
) -> None:
    """Official publication is not authorised; experimental outputs only."""
    if official or publish:
        raise ApiError(
            403,
            "OFFICIAL_RANKING_NOT_AUTHORIZED",
            "Official rankings are not authorised. Only EXPERIMENTAL_NOT_VALIDATED outputs exist.",
        )


def require_admin(
    request: Request,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    expected = getattr(request.app.state, "admin_token", None) or os.environ.get(ADMIN_ENV)
    if not expected:
        raise ApiError(
            503, "ADMIN_DISABLED", "admin endpoints are disabled (no admin token configured)"
        )
    if not x_admin_token or not hmac.compare_digest(
        x_admin_token.encode("utf-8"), expected.encode("utf-8")
    ):
        raise ApiError(401, "ADMIN_AUTH_FAILED", "missing or invalid admin token")


def require_internal(
    request: Request,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Internal routes use the admin token (header X-Admin-Token): 401 wrong, 503 none set."""
    require_admin(request, x_admin_token)


Service = Annotated[Phase4Service, Depends(get_service)]
Service5 = Annotated[Phase5Service, Depends(get_service5)]
