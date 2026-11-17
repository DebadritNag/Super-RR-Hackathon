"""Read access to the experimental analytical store for the API.

The store is opened read-only for every load. The only write is the admin classification reload,
which rewrites the ``p5_player_classification`` table (never an official table). Callers cannot
pass SQL or paths; all statements here are fixed text. The API reads the Phase 5 classification
tables only: there is no fallback to the legacy ``p4_player_classification`` table.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.phase4 import classification as cl
from app.phase4.constants import FROZEN_CHOICES, STATUS
from app.phase4.views import Tables
from app.phase5 import classification_v2 as c2
from app.phase5.constants import CLASSIFICATION_V2_CONFIG, SOURCE_MANIFEST
from app.phase5.store import write_p5_table
from app.services.pressure_service import EXPLORATORY_DB

REQUIRED_TABLES = (
    "p5_player_classification",
    "p5_player_classification_base",
    "p4_pressure_scores_frozen_rules",
    "p4_player_stats",
)
OPTIONAL_TABLES = (
    "p4_ranking_distributions",
    "p5_classification_coverage",
    "p4_classification_unresolved",
)
SCORES_SQL = (
    "SELECT * FROM p4_pressure_scores_frozen_rules "
    "WHERE is_carried_definition AND \"window\" = 'PRE_TEST' AND stream IN ('runs', 'charged')"
)


class StoreUnavailableError(RuntimeError):
    """Raised when the analytical store or a required table is missing."""


def frozen_shrinkage(path: Path | str = FROZEN_CHOICES) -> str | None:
    """The shrinkage configuration recorded in the frozen-choices file, if present."""
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("shrinkage", {}).get("config")


def pick_shrinkage(scores: pd.DataFrame, wanted: str | None) -> pd.DataFrame:
    """Keep one shrinkage configuration so that no player appears twice per scope."""
    configs = sorted(scores["shrinkage_config"].dropna().unique()) if len(scores) else []
    if wanted and wanted in configs:
        chosen = wanted
    else:
        non_zero = [c for c in configs if c != "shrink_none"]
        chosen = non_zero[0] if non_zero else (configs[0] if configs else None)
    return scores[scores["shrinkage_config"] == chosen] if chosen else scores


def scored_ids(scores: pd.DataFrame) -> set[int]:
    """Players with an eligible experimental score (the scored pool for coverage checks)."""
    if scores.empty:
        return set()
    ok = scores["eligibility_status"].astype(str).str.startswith("ELIGIBLE")
    return {int(p) for p in scores.loc[ok, "player_id"]}


def load_tables(store: Path | str, shrinkage: str | None = None) -> Tables:
    path = Path(store)
    if not path.exists():
        raise StoreUnavailableError(f"analytical store not found: {path.name}")
    con = duckdb.connect(str(path), read_only=True)
    try:
        have = {
            t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        missing = [t for t in REQUIRED_TABLES if t not in have]
        if missing:
            raise StoreUnavailableError(f"required tables missing: {missing}")

        def opt(name: str) -> pd.DataFrame:
            return con.execute(f"SELECT * FROM {name}").df() if name in have else pd.DataFrame()

        scores = pick_shrinkage(con.execute(SCORES_SQL).df(), shrinkage)
        return Tables(
            classification=con.execute("SELECT * FROM p5_player_classification").df(),
            scores=scores,
            stats=con.execute("SELECT * FROM p4_player_stats").df(),
            ranking_dist=opt("p4_ranking_distributions"),
            coverage=opt("p5_classification_coverage"),
            unresolved=opt("p4_classification_unresolved"),
            meta={
                "definition_id": str(scores["definition_id"].iloc[0]) if len(scores) else None,
                "baseline_version": str(scores["baseline_version"].iloc[0])
                if len(scores)
                else None,
                "shrinkage_config": str(scores["shrinkage_config"].iloc[0])
                if len(scores)
                else None,
                "status": STATUS,
            },
        )
    finally:
        con.close()


class Phase4Repository:
    def __init__(
        self,
        store: Path | str | None = None,
        overrides: Path | str | None = None,
        shrinkage: str | None = None,
        source_manifest: Path | str | None = None,
        classification_config: Path | str | None = None,
    ) -> None:
        self.shrinkage = shrinkage
        self.store = Path(store) if store else EXPLORATORY_DB
        self.overrides_path = Path(overrides) if overrides else cl.OVERRIDES_FILE
        self.manifest_path = Path(source_manifest) if source_manifest else SOURCE_MANIFEST
        self.config_path = (
            Path(classification_config) if classification_config else CLASSIFICATION_V2_CONFIG
        )
        self._tables: Tables | None = None
        self._capability: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def tables(self) -> Tables:
        with self._lock:
            if self._tables is None:
                self._tables = load_tables(self.store, self.shrinkage or frozen_shrinkage())
            return self._tables

    def capability(self) -> dict[str, Any]:
        """``strict_uncapped_enabled`` and its reasons, computed from the loaded classification."""
        t = self.tables
        with self._lock:
            if self._capability is None:
                self._capability = c2.strict_uncapped_capability(
                    t.classification,
                    c2.load_source_manifest(self.manifest_path),
                    scored_ids(t.scores),
                    c2.load_config(self.config_path),
                )
            return self._capability

    def base_classification(self) -> pd.DataFrame:
        con = duckdb.connect(str(self.store), read_only=True)
        try:
            return con.execute("SELECT * FROM p5_player_classification_base").df()
        finally:
            con.close()

    def overrides(self) -> pd.DataFrame:
        return c2.load_overrides_v2(self.overrides_path, self.base_classification())

    def reload_classification(self) -> dict[str, Any]:
        """Re-apply the validated override file to the stored base classification.

        A validation failure raises before anything is written, so the previous good table and
        the in-memory state stay in place.
        """
        base = self.base_classification()
        overrides = c2.load_overrides_v2(self.overrides_path, base)
        final = c2.apply_overrides_v2(base, overrides)
        with self._lock:
            write_p5_table(final, "p5_player_classification", self.store)
            self._tables = None
            self._capability = None
        cov = c2.coverage_v2(final)
        return {
            "overrides_applied": int(len(overrides)),
            "players": int(len(final)),
            "uncapped_verified_count": int(cov["uncapped_verified_count"]),
            "strict_uncapped_enabled": bool(self.capability()["enabled"]),
        }
