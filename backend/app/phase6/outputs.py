"""Output helpers for the Phase 6 scripts: tables (CSV, JSON, p6_ table) and preservation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.analytics.reporting import write_json_deterministic
from app.phase5.outputs import (  # noqa: F401  (re-exported)
    Preservation,
    cols,
    failing_gates,
    rows_of,
    sanitize,
)
from app.phase6.constants import STATUS
from app.phase6.store import write_p6_table


def save_table(
    df: pd.DataFrame, name: str, reports: Path, store: Path, table: str | None = None
) -> None:
    """CSV + deterministic JSON in the reports folder and, optionally, a p6_ table."""
    reports.mkdir(parents=True, exist_ok=True)
    df = sanitize(df)
    df.to_csv(reports / f"{name}.csv", index=False)
    write_json_deterministic(
        reports / f"{name}.json",
        {
            "status": STATUS,
            "official_ranking": False,
            "records": json.loads(df.to_json(orient="records")),
        },
    )
    if table:
        write_p6_table(df, table, store)
