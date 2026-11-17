"""Phase 5 Chunk 4: precomputed context coverage (how many players qualify per filter combination).

Reads the stored context tables and the current classification, resolves every valid filter
combination with the ranking engine's own pool resolution (so the table cannot disagree with the
ranking endpoint) and writes ``p5_context_coverage`` plus ``phase5_context_coverage.{csv,json}`` and
``phase5_context_coverage_summary.json``. Counts are measured, not estimated. Strict-uncapped
combinations are listed as DISABLED. EXPERIMENTAL_NOT_VALIDATED; nothing here is a published list.
Exit 1 if official data, Phase 4 reports or the TEST lock changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.phase5 import coverage as cov  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.outputs import Preservation, save_table  # noqa: E402
from app.repositories.phase5_repo import Phase5Repository  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    pres = Preservation(args.reports)
    eng = Phase5Repository(args.store).engine()
    con = duckdb.connect(str(args.store), read_only=True)
    try:
        cls = con.execute("SELECT * FROM p5_player_classification").df()
        strict = bool(
            con.execute("SELECT enabled FROM p5_strict_uncapped_capability").fetchone()[0]
        )
    finally:
        con.close()
    table = cov.build_coverage(eng, cls, strict)
    save_table(table, "phase5_context_coverage", args.reports, args.store, "p5_context_coverage")
    en = table[table["enabled"]]
    by = (
        en.groupby(["format", "role"])
        .agg(combinations=("spec_hash", "size"), meets_internal_min=("meets_internal_min", "sum"),
             meets_public_min=("meets_public_min", "sum"), empty=("final_pool", lambda s: int((s == 0).sum())))
        .reset_index()
    )  # fmt: skip
    by_ctx = (
        en[(en["nationality"].isna()) & (en["status"].isna())]
        .groupby(["format", "role", "phase", "situation"])["final_pool"].max().reset_index()
    )  # fmt: skip
    summary = {
        "status": STATUS,
        "official_ranking": False,
        "minimum_pool_rule": {
            "min_internal_pool": int(eng.cfg["min_internal_pool"]),
            "min_public_pool": int(eng.cfg["min_public_pool"]),
            "both_provisional": True,
        },
        "combinations": int(len(table)),
        "enabled": int(table["enabled"].sum()),
        "disabled_strict_uncapped": int((~table["enabled"]).sum()),
        "meets_internal_min": int(table["meets_internal_min"].sum()),
        "meets_public_min": int(table["meets_public_min"].sum()),
        "empty_pool": int((en["final_pool"] == 0).sum()),
        "strict_uncapped_enabled": strict,
        "by_format_role": by.to_dict(orient="records"),
        "unfiltered_pool_by_context": by_ctx.to_dict(orient="records"),
        "note": "meets_public_min only counts the pool-size rule; every other publication gate "
        "currently fails, so no combination is publishable.",
    }
    ok = pres.verify()
    summary["preservation"] = ok
    write_json_deterministic(args.reports / "phase5_context_coverage_summary.json", summary)
    print(by.to_string(index=False))
    print("combinations", summary["combinations"], "internal", summary["meets_internal_min"],
          "public-size", summary["meets_public_min"], "disabled", summary["disabled_strict_uncapped"])  # fmt: skip
    print("preserved:", ok["all_preserved"])
    return 0 if ok["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
