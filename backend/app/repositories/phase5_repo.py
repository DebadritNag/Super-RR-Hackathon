"""Read access to the Phase 5 context tables (``p5_context_*``) in the analytical store.

Every load opens the store read-only with fixed statements; callers pass no SQL or paths. The
engine is built once from the stored rows (no fitting happens at load or request time) and is
rebuilt only when the store changes (``reset``).
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.phase4.config import file_sha256
from app.phase5.constants import CONFIG_DIR
from app.phase5.ranking_engine import ContextEngine
from app.repositories.phase4_repo import StoreUnavailableError
from app.services.pressure_service import EXPLORATORY_DB

CONTEXT_RULES_CONFIG = CONFIG_DIR / "phase5_context_rules_v1.json"
CONTEXT_TABLES = (
    "p5_context_stats",
    "p5_context_eligibility_rules",
    "p5_context_fit",
    "p5_context_scores",
    "p5_context_manifest",
    "p4_player_stats",
)


def frame_hash(df: pd.DataFrame) -> str:
    """Order-sensitive content hash of a frame (values and column names)."""
    h = hashlib.sha256()
    h.update("|".join(map(str, df.columns)).encode("utf-8"))
    if len(df):
        h.update(
            pd.util.hash_pandas_object(df.reset_index(drop=True), index=False).to_numpy().tobytes()
        )
    return h.hexdigest()


def load_context_config(path: Path | str = CONTEXT_RULES_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Phase5Repository:
    def __init__(self, store: Path | str | None = None, config: Path | str | None = None) -> None:
        self.store = Path(store) if store else EXPLORATORY_DB
        self.config_path = Path(config) if config else CONTEXT_RULES_CONFIG
        self._engine: ContextEngine | None = None
        self._coverage: pd.DataFrame | None = None
        self._lock = threading.Lock()

    def config(self) -> dict[str, Any]:
        return load_context_config(self.config_path)

    def reset(self) -> None:
        with self._lock:
            self._engine = None
            self._coverage = None

    def engine(self) -> ContextEngine:
        with self._lock:
            if self._engine is None:
                self._engine = self._load()
            return self._engine

    def coverage_table(self) -> pd.DataFrame | None:
        self.engine()
        return self._coverage

    def _load(self) -> ContextEngine:
        if not self.store.exists():
            raise StoreUnavailableError(f"analytical store not found: {self.store.name}")
        con = duckdb.connect(str(self.store), read_only=True)
        try:
            have = {
                t
                for (t,) in con.execute(
                    "SELECT table_name FROM information_schema.tables"
                ).fetchall()
            }
            missing = [t for t in CONTEXT_TABLES if t not in have]
            if missing:
                raise StoreUnavailableError(
                    f"context tables missing: {missing}; run scripts/phase5_context_engine.py"
                )
            tb = {t: con.execute(f"SELECT * FROM {t}").df() for t in CONTEXT_TABLES}
            cov = (
                con.execute("SELECT * FROM p5_context_coverage").df()
                if "p5_context_coverage" in have
                else None
            )
        finally:
            con.close()
        cfg = self.config()
        man = tb["p5_context_manifest"]
        manifest = json.loads(man["manifest_json"].iloc[0]) if len(man) else {}
        parts = [
            frame_hash(tb[t])
            for t in (
                "p5_context_stats",
                "p5_context_eligibility_rules",
                "p5_context_scores",
                "p5_context_manifest",
            )
        ]
        version = hashlib.sha256(
            "|".join([*parts, file_sha256(self.config_path), str(cfg["model_version"])]).encode()
        ).hexdigest()
        self._coverage = cov
        return ContextEngine(
            tb["p5_context_stats"],
            tb["p5_context_eligibility_rules"],
            tb["p5_context_scores"],
            cfg,
            manifest,
            tb["p4_player_stats"],
            version,
        )
