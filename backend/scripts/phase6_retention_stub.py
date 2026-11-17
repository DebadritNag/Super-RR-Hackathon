"""Phase 6: create the EMPTY retention-status stub and write the importer design note.

No retention data is imported. The stub is created only in the analytical store and is not
referenced by any scoring, ranking, API, service or schema module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import write_text  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import retention_stub as rs  # noqa: E402
from app.phase6.constants import STATUS  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_retention_import_design"


def render() -> str:
    cols = "\n".join(f"| `{c}` | {d} |" for c, d in (
        ("player_id", "Resolved player id; empty while `mapping_status` is not `MAPPED`."),
        ("team", "Franchise named by the source."),
        ("season", "Auction season the row refers to."),
        ("status", "One of `retained`, `released`, `traded`, `auction_available`, `unknown`. "
                   "Default and fallback: `unknown`."),
        ("source", "Document, URL or file the row came from."),
        ("snapshot_date", "Date the source was published or captured."),
        ("verification_status", "`OFFICIAL_VERIFIED`, `SINGLE_SOURCE`, `UNVERIFIED`."),
        ("mapping_status", "`MAPPED`, `AMBIGUOUS`, `UNMATCHED`."),
        ("ambiguity_note", "Candidate ids or reason when the name did not map uniquely."),
    ))  # fmt: skip
    return f"""# Phase 6 retention and release list import design

Status: {STATUS}. DESIGN ONLY. No retention data is imported in Phase 6. The list is expected from the user and is wanted as auction-availability context. It is not an input to any score, rank, eligibility gate or classification.

## 1. Purpose
Record which players each franchise retained, released, traded or put into the auction, so that later views can show availability next to descriptive information. Availability is a separate fact. It never changes a pressure score, an eligibility decision, a data-weight gate or a capped status.

## 2. Stub table
`{rs.TABLE}` exists in the analytical store `exploratory.duckdb` only, created empty by `app/phase6/retention_stub.py`. It is not in `superr.duckdb`. No scoring, ranking, API, service or schema module references it, and a test enforces that.

| column | meaning |
|---|---|
{cols}

## 3. Status fields
- Separate values, never combined: `retained`, `released`, `traded`, `auction_available`, `unknown`.
- `unknown` is the explicit default. A player absent from a source gets no row and no inferred status.
- A player can have several rows (one per team, season and source). Rows are never merged silently. Conflicting rows stay side by side with their sources.
- `auction_available` is a stated status in a source, not a conclusion drawn from a release or from an absence on a squad list.

## 4. Source and verification per row
- Every row carries `source`, `snapshot_date` and `verification_status`. A row without all three is rejected.
- Statuses from an official franchise or league announcement are `OFFICIAL_VERIFIED`. A media list is `SINGLE_SOURCE` until a second independent source or an official record confirms it. Everything else is `UNVERIFIED`.
- Later snapshots add rows. They do not overwrite earlier snapshots, so the change over time stays visible.

## 5. Mapping to `player_id`
- Names are matched with the identity rules already used for the player directory (normalised name, alias table, team context). A name that maps to exactly one `player_id` is `MAPPED`.
- A name with zero matches is `UNMATCHED` and a name with several is `AMBIGUOUS`. Both go to a review list (`ambiguity_note` holds candidates) and are never resolved automatically.
- Mapping uses the supplied list and the identity tables only. It never infers identity or availability from squad snapshots or match lineups.

## 6. Separation from capped status
- Availability statuses never imply capped or uncapped. The three real classification values (`VERIFIED_CAPPED`, `DERIVED_CAPPED`, `UNKNOWN`) are unaffected, and `VERIFIED_UNCAPPED` stays a disabled placeholder.
- An `auction_available` player does not become `UNKNOWN` or capped because of that status, and a retained player does not become eligible for anything.

## 7. Access rules for a later phase
- The importer writes only to `{rs.TABLE}` (or a successor with the same columns) and reads only the supplied file and identity tables.
- Any route that later exposes availability is a descriptive directory field behind the same publication rules as the other descriptive fields. It carries no score, rank or eligibility field.
- Publishing is a separate decision for the user.

## 8. Open items for the user
- The file format of the list (CSV, spreadsheet or document) and the season it covers.
- Whether `traded` rows need the counterpart team.
- Which source counts as official for `OFFICIAL_VERIFIED`.

## 9. Not done in Phase 6
No data imported. No route, schema or scoring change. No inference from squads. No effect on any ranking.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    n = rs.create_stub(args.store)
    if n != 0:
        print("FATAL: the retention stub is not empty")
        return 1
    write_text(args.reports / f"{NAME}.md", render())
    print(json.dumps({"table": rs.TABLE, "rows": n}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
