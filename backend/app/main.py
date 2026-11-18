"""FastAPI application for the experimental API (no frontend code).

Run with ``uvicorn app.main:app``. The store defaults to the exploratory analytical store and is
read-only for every request except the admin classification reload. Set ``SUPERR_ADMIN_TOKEN``
to enable the admin and internal endpoints; without it they answer 503. Rows-returning public
routes answer 403 PUBLICATION_GATE_NOT_SATISFIED until every publication gate passes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.v1 import (
    routes,
    routes_descriptive,
    routes_internal_ai,
    routes_phase5,
    routes_retention,
    routes_rr,
    routes_submission,
)
from app.phase5.gating import GateInput
from app.phase7.descriptive import load_config as load_descriptive_config
from app.repositories.phase4_repo import Phase4Repository
from app.repositories.phase5_repo import Phase5Repository
from app.services.descriptive_service import DescriptiveService
from app.services.phase4_service import PRESETS_FILE, Phase4Service
from app.services.phase5_service import Phase5Service
from app.services.submission_service import SubmissionService


def _load_dotenv() -> None:
    """Load ``backend/.env`` for local runs. Variables already set (for example on Render) win,
    and the file is skipped under pytest so tests never pick up a local admin token."""
    if "pytest" in sys.modules:
        return
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


_load_dotenv()


def _cors_origins() -> list[str]:
    """Local dev origins from config, plus any deployed origins in ``SUPERR_CORS_ORIGINS``
    (comma-separated, e.g. ``https://my-app.vercel.app``)."""
    origins = list(load_descriptive_config()["cors_origins"])
    extra = os.environ.get("SUPERR_CORS_ORIGINS", "")
    origins += [o.strip().rstrip("/") for o in extra.split(",") if o.strip()]
    return origins


def create_app(
    store: Path | str | None = None,
    overrides: Path | str | None = None,
    presets: Path | str | None = None,
    admin_token: str | None = None,
    gate_inputs: GateInput | None = None,
    source_manifest: Path | str | None = None,
    classification_config: Path | str | None = None,
    descriptive_reports: Path | str | None = None,
    submission_reports: Path | str | None = None,
    submission_db: Path | str | None = None,
) -> FastAPI:
    """``gate_inputs`` is a function argument only (never an environment variable or request
    field); tests use it to supply synthetic all-pass or single-failure gate fixtures."""
    app = FastAPI(
        title="SupeRR Selector experimental API",
        version="phase5-experimental",
        description="EXPERIMENTAL_NOT_VALIDATED outputs only. No official rankings.",
    )
    store = store or os.environ.get("SUPERR_P4_STORE")
    repo = Phase4Repository(
        store,
        overrides,
        source_manifest=source_manifest,
        classification_config=classification_config,
    )
    app.state.service = Phase4Service(repo, presets or PRESETS_FILE, gate_inputs=gate_inputs)
    app.state.service5 = Phase5Service(app.state.service, Phase5Repository(repo.store))
    app.state.admin_token = admin_token
    app.state.retention = routes_retention.RetentionContext()
    app.state.descriptive = DescriptiveService(descriptive_reports)
    app.state.submission = SubmissionService(
        submission_reports, submission_db, descriptive_reports or submission_reports
    )
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(routes_phase5.internal)
    v1.include_router(routes_retention.internal)
    v1.include_router(routes_internal_ai.internal)
    v1.include_router(routes_submission.internal)
    v1.include_router(routes_phase5.public)
    v1.include_router(routes.public)
    v1.include_router(routes_descriptive.public)
    v1.include_router(routes_submission.public)
    v1.include_router(routes_rr.public)
    v1.include_router(routes.internal)
    v1.include_router(routes.admin)

    @v1.get("/health", tags=["meta"])
    def health() -> dict[str, object]:
        return {"ok": True, "status": "EXPERIMENTAL_NOT_VALIDATED", "official_ranking": False}

    app.include_router(v1)
    return app


app = create_app()
