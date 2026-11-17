"""Empty retention-status table stub for a future importer (no data is imported in Phase 6).

The table lives only in the analytical store (``exploratory.duckdb``). No scoring, ranking, API,
service or schema module reads it, and availability statuses never imply capped or uncapped status.
``status`` defaults to ``unknown``; the CHECK constraint lists the only allowed values.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from app.phase4.store import OFFICIAL_DB
from app.phase6.store import _check_store
from app.services.pressure_service import EXPLORATORY_DB

TABLE = "p6_retention_status_stub"
STATUS_VALUES = ("retained", "released", "traded", "auction_available", "unknown")
COLUMNS = ("player_id", "team", "season", "status", "source", "snapshot_date",
           "verification_status", "mapping_status", "ambiguity_note")  # fmt: skip

_VALUES = ", ".join(f"'{v}'" for v in STATUS_VALUES)
DDL = f"""CREATE TABLE IF NOT EXISTS {TABLE} (
    player_id INTEGER,
    team VARCHAR,
    season INTEGER,
    status VARCHAR NOT NULL DEFAULT 'unknown' CHECK (status IN ({_VALUES})),
    source VARCHAR,
    snapshot_date DATE,
    verification_status VARCHAR,
    mapping_status VARCHAR,
    ambiguity_note VARCHAR
)"""


def create_stub(
    store_path: Path | str = EXPLORATORY_DB, official_db: Path | str = OFFICIAL_DB
) -> int:
    """Create the empty stub if missing and return its row count (0). Never inserts a row."""
    store = _check_store(store_path, official_db)
    con = duckdb.connect(str(store))
    try:
        con.execute(DDL)
        return int(con.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0])
    finally:
        con.close()
