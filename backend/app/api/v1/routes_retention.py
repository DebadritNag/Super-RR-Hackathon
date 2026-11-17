"""Admin retention-list endpoints. Every route needs the internal token (X-Admin-Token).

The body of the import and preview routes is the raw file (octet-stream) so no multipart
dependency is needed; the file name goes in the query. Preview never writes anything.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.deps import require_internal
from app.api.errors import ApiError
from app.data_pipeline import retention_importer as ri
from app.data_pipeline.retention_availability import build_availability


@dataclass
class RetentionContext:
    store: Path = field(default_factory=lambda: Path(ri.EXPLORATORY_DB))
    raw_dir: Path = field(default_factory=lambda: Path(ri.RAW_DIR))
    reports_dir: Path = field(default_factory=lambda: Path(ri.REPORTS_DIR))
    profile_dir: Path = field(default_factory=lambda: Path(ri.REPORTS_DIR))
    reference: ri.Reference | None = None

    def ref(self) -> ri.Reference:
        if self.reference is None:
            self.reference = ri.load_reference()
        return self.reference


def get_ctx(request: Request) -> RetentionContext:
    return request.app.state.retention


Ctx = Annotated[RetentionContext, Depends(get_ctx)]
internal = APIRouter(prefix="/internal/retention", dependencies=[Depends(require_internal)])


class Resolution(BaseModel):
    resolver: str
    evidence: str
    player_id: int | None = None
    dismiss: bool = False


def _strip(res: dict[str, Any], rows: bool) -> dict[str, Any]:
    out = {k: v for k, v in res.items() if k != "rows"}
    if rows:
        out["rows"] = res["rows"]
    return out


async def _run(
    request: Request, ctx: RetentionContext, dry_run: bool, filename: str, q: dict[str, Any]
) -> dict[str, Any]:
    body = await request.body()
    if not body:
        raise ApiError(422, "EMPTY_FILE", "the request body must be the retention file")
    if len(body) > ri.MAX_BYTES:
        raise ApiError(413, "FILE_TOO_LARGE", "file larger than 10 MB")
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / f"upload{suffix}"
        tmp.write_bytes(body)
        try:
            res = ri.import_file(
                tmp, dry_run=dry_run, store=ctx.store, raw_dir=ctx.raw_dir,
                reference=ctx.ref(), original_name=Path(filename).name, **q,
            )  # fmt: skip
        except ri.RetentionImportError as exc:
            raise ApiError(422, "INVALID_RETENTION_FILE", str(exc)) from exc
    if res["changed"]:
        ri.export_review_csv(ctx.store, ctx.reports_dir / "retention_review_queue.csv")
    return _strip(res, rows=dry_run)


def _params(
    snapshot_date: str,
    source: str,
    verification: str,
    authoritative: bool,
    season: str,
    sheet: str | None,
) -> dict[str, Any]:
    return {"snapshot_date": snapshot_date, "source": source, "verification": verification,
            "authoritative": authoritative, "season": season, "sheet": sheet}  # fmt: skip


@internal.post("/preview")
async def preview(
    request: Request, ctx: Ctx, filename: str, snapshot_date: str, source: str = "",
    verification: str = "UNVERIFIED", authoritative: bool = False, season: str = "",
    sheet: str | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Validate a file and show how each row would be mapped. Writes nothing."""
    q = _params(snapshot_date, source, verification, authoritative, season, sheet)
    return await _run(request, ctx, True, filename, q)


@internal.post("/import")
async def import_list(
    request: Request, ctx: Ctx, filename: str, snapshot_date: str, source: str = "",
    verification: str = "UNVERIFIED", authoritative: bool = False, season: str = "",
    sheet: str | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Import a file (idempotent on the file hash). Availability stays separate from every pressure output."""
    q = _params(snapshot_date, source, verification, authoritative, season, sheet)
    return await _run(request, ctx, False, filename, q)


@internal.get("/review")
def review(
    ctx: Ctx, state: Annotated[str | None, Query(pattern="^(OPEN|RESOLVED|DISMISSED)$")] = "OPEN"
) -> dict[str, Any]:
    items = ri.list_review(ctx.store, state)
    return {"items": items, "count": len(items)}


@internal.post("/review/{review_id}/resolve")
def resolve(review_id: int, body: Resolution, ctx: Ctx) -> dict[str, Any]:
    try:
        res = ri.resolve_review(
            ctx.store, review_id, resolver=body.resolver, evidence=body.evidence,
            player_id=body.player_id, dismiss=body.dismiss, reference=ctx.ref(),
        )  # fmt: skip
    except ri.RetentionImportError as exc:
        raise ApiError(422, "INVALID_RESOLUTION", str(exc)) from exc
    ri.export_review_csv(ctx.store, ctx.reports_dir / "retention_review_queue.csv")
    return res


@internal.post("/availability/rebuild")
def rebuild(ctx: Ctx) -> dict[str, Any]:
    """Regenerate the availability-aware candidate output from the stored import."""
    m = build_availability(ctx.store, ctx.reports_dir, ctx.profile_dir)
    return {k: m[k] for k in ("state", "rows", "retained_excluded", "confirmed_available",
                              "unresolved_rows_in_list", "statement")}  # fmt: skip
