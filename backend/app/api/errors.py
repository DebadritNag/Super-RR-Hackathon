"""Uniform error model ``{"error": {"code", "message", "details"}}`` for the Phase 4 API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.phase4.classification import ClassificationConfigError
from app.phase4.selection import SelectionRequestError
from app.phase4.uncapped import FilterError
from app.phase5.classification_v2 import ClassificationMigrationError
from app.phase5.gating import PublicationGateError
from app.repositories.phase4_repo import StoreUnavailableError
from app.services.phase4_service import NotFoundError


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def _body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def _resp(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status, content=jsonable_encoder(_body(code, message, details)))


_HTTP_CODES = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    503: "SERVICE_UNAVAILABLE",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError) -> JSONResponse:
        return _resp(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": [str(x) for x in e.get("loc", [])],
                "message": e.get("msg", ""),
                "type": e.get("type", ""),
            }
            for e in exc.errors()
        ]
        return _resp(422, "VALIDATION_ERROR", "request validation failed", details)

    @app.exception_handler(NotFoundError)
    async def _nf(_: Request, exc: NotFoundError) -> JSONResponse:
        return _resp(404, "NOT_FOUND", str(exc))

    @app.exception_handler(FilterError)
    async def _filter(_: Request, exc: FilterError) -> JSONResponse:
        return _resp(422, "CONFLICTING_FILTERS", str(exc))

    @app.exception_handler(SelectionRequestError)
    async def _sel(_: Request, exc: SelectionRequestError) -> JSONResponse:
        return _resp(422, "INVALID_SELECTION_REQUEST", str(exc))

    @app.exception_handler(ClassificationConfigError)
    async def _cls(_: Request, exc: ClassificationConfigError) -> JSONResponse:
        return _resp(422, "INVALID_CLASSIFICATION_CONFIG", str(exc))

    @app.exception_handler(PublicationGateError)
    async def _gate(_: Request, exc: PublicationGateError) -> JSONResponse:
        return _resp(
            403,
            "PUBLICATION_GATE_NOT_SATISFIED",
            "Publication gates are not satisfied; no rows are returned on public routes.",
            {"publication_status": "INTERNAL_EXPERIMENTAL_ONLY", "gate_results": exc.gate_results},
        )

    @app.exception_handler(ClassificationMigrationError)
    async def _mig(_: Request, exc: ClassificationMigrationError) -> JSONResponse:
        return _resp(500, "CLASSIFICATION_MIGRATION_ERROR", str(exc))

    @app.exception_handler(StoreUnavailableError)
    async def _store(_: Request, exc: StoreUnavailableError) -> JSONResponse:
        return _resp(503, "STORE_UNAVAILABLE", str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _resp(
            exc.status_code, _HTTP_CODES.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)
        )
