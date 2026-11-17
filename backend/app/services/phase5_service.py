"""Service of the dynamic filter-driven ranking: catalog, context preview, ranking, coverage.

Every output passes through the single gating function of ``Phase4Service`` (``apply_gates``), so
``publication_status`` and ``gate_results`` are present on every response and public callers get
``PUBLICATION_GATE_NOT_SATISFIED`` without rows. Strict-uncapped requests return the structured
``STRICT_UNCAPPED_DISABLED`` body before any score table is touched.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any

import pandas as pd

from app.phase5 import coverage as cov
from app.phase5.cache import RankingCache, gate_state_hash
from app.phase5.filters import FilterSpec, catalog, spec_hash, uses_strict_classification
from app.phase5.gating import RequestNeeds, evaluate_gates, failing
from app.phase5.lock_manifest import LOCK_CONFIG
from app.phase5.lockguard import file_sha256
from app.phase5.ranking_engine import ContextEngine, paginate_ranked
from app.repositories.phase5_repo import Phase5Repository, frame_hash
from app.services.phase4_service import Phase4Service

NOTE = (
    "INTERNAL_EXPERIMENTAL: filter-specific ranking over stored delivery-level evidence of the "
    "PROVISIONAL definition. Thresholds are working values and are not validated. A filter never "
    "creates reliability; short or empty results are reported with reasons and never padded."
)
SEMANTICS = {
    "and": "All selected filters must match (AND).",
    "roles": "Batter and bowler rankings are separate; there is no all-rounder role.",
    "unknown_toggles": (
        "include_unknown_* act only on a filtered axis (default false: unknowns are excluded and "
        "their count is reported)."
    ),
    "context_filters": (
        "phase and situation re-aggregate stored delivery-level residuals; eligibility, sample "
        "sizes and uncertainty are recomputed for the context."
    ),
    "order": "Canonical order: score descending, player_id ascending. Rank values never change "
    "with the display sort.",
}


def _none(v: Any) -> Any:
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA:
        return None
    return v


class Phase5Service:
    def __init__(self, p4: Phase4Service, repo: Phase5Repository) -> None:
        self.p4 = p4
        self.repo = repo
        self.cache: RankingCache | None = None
        self._cov: tuple[str, pd.DataFrame] | None = None

    # ------------------------------------------------------------------ plumbing
    def engine(self) -> ContextEngine:
        eng = self.repo.engine()
        if self.cache is None:
            self.cache = RankingCache(int(eng.cfg["cache"]["max_entries"]))
        return eng

    def _cls(self) -> pd.DataFrame:
        return self.p4.t.classification

    def _strict_enabled(self) -> bool:
        return bool(self.p4.repo.capability()["enabled"])

    def _data_version(self, eng: ContextEngine, cls: pd.DataFrame) -> str:
        """Context tables, config, model version and the classification table in force."""
        return hashlib.sha256(f"{eng.data_version}|{frame_hash(cls)}".encode()).hexdigest()

    @staticmethod
    def _lock_version() -> str:
        """SHA-256 of the methodology lock config in force (part of every cache key)."""
        try:
            return file_sha256(LOCK_CONFIG)
        except OSError:
            return "NO_LOCK_CONFIG"

    def _gate_state(self) -> str:
        """Hash of the gates failing now (request-independent gates only; pool is per request)."""
        gates = evaluate_gates(self.p4.gate_input(), RequestNeeds())
        return gate_state_hash([g.gate_id for g in failing(gates)])

    def _needs(self, spec: FilterSpec, pool: int | None = None) -> RequestNeeds:
        return RequestNeeds(uses_strict_classification=uses_strict_classification(spec),
                            eligible_pool=pool)  # fmt: skip

    def _echo(self, spec: FilterSpec) -> dict[str, Any]:
        return {**spec.ranking_dict(), "limit": spec.limit, "offset": spec.offset,
                "sort": spec.sort, "order": spec.effective_order()}  # fmt: skip

    def _disabled(self, spec: FilterSpec, kind: str) -> dict[str, Any]:
        out = self.p4.disabled(kind, self._needs(spec))
        out["filter_echo"] = self._echo(spec)
        return out

    # ------------------------------------------------------------------ catalog
    def filter_catalog(self) -> dict[str, Any]:
        eng = self.engine()
        strict = self._strict_enabled()
        return {
            **self.p4.flags(),
            "filters": catalog(eng.cfg, strict),
            "strict_uncapped_enabled": strict,
            "semantics": SEMANTICS,
            "cache": self.cache.stats() if self.cache else {},
            "versions": eng.versions(),
        }

    # ------------------------------------------------------------------ ranking
    def _full(self, spec: FilterSpec, internal: bool) -> tuple[dict[str, Any], bool]:
        """Full pre-gate ranking from the cache; the returned object is a private copy."""
        eng, cls, strict = self.engine(), self._cls(), self._strict_enabled()
        dv = self._data_version(eng, cls)
        assert self.cache is not None

        def compute() -> dict[str, Any]:
            full = eng.rank(spec, cls, strict)
            full["versions"] = {**full["versions"], "data_version": dv}
            return full

        return self.cache.get_or_compute(
            spec_hash=spec_hash(spec), data_version=dv, model_version=eng.model_version,
            compute=compute, scope="internal" if internal else "public",
            lock_version=self._lock_version(), gate_state=self._gate_state(),
        )  # fmt: skip

    def ranking(self, spec: FilterSpec, internal: bool = True) -> dict[str, Any]:
        needs = self._needs(spec)
        self.p4.precheck(needs, internal)
        if spec.status == "VERIFIED_UNCAPPED" and not self._strict_enabled():
            return self._disabled(spec, "dynamic_ranking")
        full, hit = self._full(spec, internal)
        page = copy.deepcopy(paginate_ranked(full, spec))  # never alias cached/shared rows
        payload = {
            **self.p4.flags(),
            "result_status": page["result_status"],
            "spec_hash": page["spec_hash"],
            "filter_echo": self._echo(spec),
            "pool_size": page["pool_size"],
            "reasons": page["reasons"],
            "stage_counts": page["stage_counts"],
            "excluded_counts": page["excluded_counts"],
            "context_status": page["context_status"],
            "context_data_weight": page["context_data_weight"],
            "versions": page["versions"],
            "note": NOTE,
            "cache_hit": hit,
            "low_data_weight": page["low_data_weight"],
            "page": {
                "items": page["rows"],
                "total": page["total"],
                "limit": page["limit"],
                "offset": page["offset"],
            },
        }
        return self.p4._gate(payload, self._needs(spec, page["pool_size"]), internal)

    def context_preview(self, spec: FilterSpec, internal: bool = True) -> dict[str, Any]:
        """Qualifying players and exclusion reasons before ranking; no rows, no bootstrap."""
        needs = self._needs(spec)
        self.p4.precheck(needs, internal)
        if spec.status == "VERIFIED_UNCAPPED" and not self._strict_enabled():
            return self._disabled(spec, "dynamic_context_preview")
        eng, cls = self.engine(), self._cls()
        pool = eng.resolve_pool(spec, cls, self._strict_enabled())
        versions = {**eng.versions(), "data_version": self._data_version(eng, cls)}
        payload = {
            **self.p4.flags(),
            "result_status": pool.result_status,
            "spec_hash": pool.spec_hash,
            "filter_echo": self._echo(spec),
            "pool_size": pool.size,
            "reasons": pool.reasons,
            "stage_counts": pool.stage_counts,
            "excluded_counts": pool.excluded_counts,
            "context_status": pool.context_status,
            "context_data_weight": eng.context_weight(spec, pool),
            "versions": versions,
            "note": NOTE,
            "qualifying_players": pool.size,
            "would_return_rows": pool.size >= int(eng.cfg["min_internal_pool"]),
            "cache_hit": False,
        }
        return self.p4._gate(payload, self._needs(spec, pool.size), internal)

    # ------------------------------------------------------------------ coverage
    def _coverage_frame(self) -> tuple[str, pd.DataFrame]:
        eng, cls = self.engine(), self._cls()
        chash = frame_hash(cls)
        stored = self.repo.coverage_table()
        if stored is not None and eng.manifest.get("classification_hash") == chash:
            return "STORED_TABLE", stored
        if self._cov is None or self._cov[0] != chash:
            self._cov = (chash, cov.build_coverage(eng, cls, self._strict_enabled()))
        return "RECOMPUTED_CLASSIFICATION_CHANGED", self._cov[1]

    def coverage(
        self,
        filters: dict[str, Any],
        limit: int,
        offset: int,
        internal: bool = True,
    ) -> dict[str, Any]:
        needs = RequestNeeds()
        self.p4.precheck(needs, internal)
        source, df = self._coverage_frame()
        eng = self.engine()
        for col, val in filters.items():
            if val is None:
                continue
            df = df[df[col] == val]
        df = df.sort_values(["format", "role", "phase", "situation", "spec_hash"], kind="mergesort")
        page = df.iloc[offset : offset + limit]
        items = [{k: _none(v) for k, v in r.items()} for r in page.to_dict(orient="records")]
        for it in items:
            for k in ("enabled", "meets_internal_min", "meets_public_min",
                      "include_unknown_nationality", "include_unknown_status"):  # fmt: skip
                it[k] = bool(it[k])
            for k in ("players_in_context", "eligible_in_context", "after_nationality",
                      "after_status", "excluded_unknown_nationality", "excluded_unknown_status"):  # fmt: skip
                it[k] = None if it[k] is None else int(it[k])
        summary = {
            "combinations": int(len(df)),
            "disabled": int((~df["enabled"]).sum()),
            "meets_internal_min": int(df["meets_internal_min"].sum()),
            "meets_public_min": int(df["meets_public_min"].sum()),
            "empty": int((df["final_pool"] == 0).sum()),
        }
        payload = {
            **self.p4.flags(),
            "coverage_source": source,
            "minimum_pool_rule": {
                "min_internal_pool": int(eng.cfg["min_internal_pool"]),
                "min_public_pool": int(eng.cfg["min_public_pool"]),
                "rule": "below min_internal_pool no rows are returned (POOL_TOO_SMALL); below "
                "list_size 10 the list is shorter than ten and never padded; a public output needs "
                "min_public_pool eligible rows and every other publication gate.",
                "both_provisional": True,
            },
            "summary": summary,
            "page": {"items": items, "total": int(len(df)), "limit": limit, "offset": offset},
            "note": NOTE,
        }
        return self.p4._gate(payload, needs, internal)
