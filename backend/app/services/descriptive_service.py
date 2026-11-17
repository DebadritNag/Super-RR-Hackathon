"""Service for the public descriptive endpoints: lazy data load and a copy-isolated cache.

The cache is the Phase 5 ``RankingCache``. Its key holds the request hash, the descriptive data
version (sha256 of the generated files and the config), the config version, the scope (always
``public``), the lock version and the gate state (both constant: nothing here is gated). Every
read returns a deep copy, so a caller that mutates a response cannot change a later response.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.api.errors import ApiError
from app.phase5.cache import RankingCache
from app.phase7 import descriptive as ds
from app.phase7 import views as vw


class DescriptiveService:
    def __init__(self, reports: Path | str | None = None, config: Path | str | None = None):
        self.reports = Path(reports) if reports else ds.REPORTS
        self.config = Path(config) if config else ds.CONFIG_PATH
        self.cache = RankingCache(max_entries=256)
        self._data: vw.DescriptiveData | None = None
        self._lock = threading.Lock()

    @property
    def data(self) -> vw.DescriptiveData:
        with self._lock:
            if self._data is None:
                try:
                    self._data = vw.DescriptiveData(self.reports, self.config)
                except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
                    raise ApiError(
                        503,
                        "DESCRIPTIVE_DATA_UNAVAILABLE",
                        "descriptive profile files are missing; run "
                        "scripts/phase7_build_descriptive.py",
                        str(exc),
                    ) from exc
            return self._data

    def cached(self, name: str, params: dict[str, Any], compute: Callable[[], Any]) -> Any:
        data = self.data
        spec = hashlib.sha256(
            json.dumps([name, params], sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        def run() -> Any:
            try:
                return compute()
            except vw.NotFound as exc:
                raise ApiError(404, "NOT_FOUND", str(exc)) from exc
            except vw.BadRequest as exc:
                raise ApiError(422, "INVALID_REQUEST", str(exc)) from exc

        value, _hit = self.cache.get_or_compute(
            spec,
            data.version,
            data.model_version,
            run,
            scope="public",
            lock_version="none",
            gate_state="none",
        )
        return value
