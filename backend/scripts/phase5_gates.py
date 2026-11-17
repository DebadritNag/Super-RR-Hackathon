"""Phase 5 Chunk 1: evaluate the publication gates on the real inputs and report them.

Reads ``phase4_frozen_choices.json``, the methodology status config, the date-verification summary
(when the date chunk has run) and the stored strict-uncapped capability. Writes ``p5_publication_gates``
to the exploratory store and ``phase5_publication_gates.{json,md}``. Deterministic (no timestamps).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.gating import (  # noqa: E402
    RequestNeeds,
    evaluate_gates,
    failing,
    load_gate_inputs,
    publication_status,
)
from app.phase5.store import write_p5_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def stored_strict_enabled(store: Path) -> bool | None:
    try:
        con = duckdb.connect(str(store), read_only=True)
        try:
            return bool(
                con.execute("SELECT enabled FROM p5_strict_uncapped_capability").fetchone()[0]
            )
        finally:
            con.close()
    except Exception:  # missing store or table: the gate then fails closed
        return None


def dynamic_section(reports: Path, min_public_pool: int) -> list[str]:
    """How the gates apply to the dynamic filter-driven ranking (Chunk 4), with measured counts."""
    import json

    summ_path = reports / "phase5_context_coverage_summary.json"
    cov = json.loads(summ_path.read_text(encoding="utf-8")) if summ_path.exists() else None
    out = [
        "## Dynamic filter-driven ranking",
        "Every dynamic ranking, context preview, coverage page and filter catalog response carries "
        "`publication_status` and `gate_results`, produced by the same `apply_gates` call as the "
        "other rankings (one enforcement point in the service layer, not in the routes). Internal "
        "routes (`/api/v1/internal/rankings/dynamic...`, admin token required) return rows labelled "
        "`INTERNAL_EXPERIMENTAL_ONLY`. Public twins (`/api/v1/dynamic-rankings...`) answer 403 "
        "`PUBLICATION_GATE_NOT_SATISFIED` with the failing gates and no rows.",
        "",
        "Per-request gate inputs: `min_eligible_pool` uses the final pool after every filter; "
        "`strict_classification_available` becomes applicable when the request uses a verified status "
        "filter (`VERIFIED_CAPPED`; `VERIFIED_UNCAPPED` is a disabled placeholder). A filter never changes the other gates: a "
        "context with a small sample is reported as `INSUFFICIENT_SAMPLE_FOR_CONTEXT` and the global "
        "`data_weight_gate_passed` stays failed. Contexts also report the Phase 4 marginal data-weight "
        "gate per context (`CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED`).",
    ]
    if cov:
        rule = cov["minimum_pool_rule"]
        out += [
            "",
            "Measured coverage (precomputed, `p5_context_coverage`): "
            f"{cov['combinations']} valid filter combinations, {cov['disabled_strict_uncapped']} "
            f"disabled (strict uncapped), {cov['meets_internal_min']} reach the internal minimum pool "
            f"({rule['min_internal_pool']}), {cov['meets_public_min']} reach the public-size rule "
            f"({min_public_pool}). Reaching the pool-size rule is only one gate: "
            "`data_weight_gate_passed`, `methodology_validated` and `date_verification` still fail, so "
            "no combination is publishable.",
        ]
    return [*out, ""]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    inp = load_gate_inputs(stored_strict_enabled(args.store))
    scenarios = {
        "descriptive (no rows, no strict filter)": RequestNeeds(),
        "ranking with rows (pool of 10 assumed)": RequestNeeds(False, 10),
        "strict-uncapped request": RequestNeeds(True, 10),
    }
    out_rows = []
    summary = {}
    for name, needs in scenarios.items():
        gates = evaluate_gates(inp, needs)
        summary[name] = {
            "publication_status": publication_status(gates),
            "failing_gates": [g.gate_id for g in failing(gates)],
            "gate_results": [g.as_dict() for g in gates],
        }
        for g in gates:
            out_rows.append({"scenario": name, **g.as_dict()})
    write_p5_table(pd.DataFrame(out_rows), "p5_publication_gates", args.store)
    result = {
        "status": STATUS,
        "inputs": {
            "cell_statuses": inp.cell_statuses,
            "methodology_validated": bool(inp.methodology and inp.methodology.get("validated")),
            "date_gate": inp.date_gate,
            "strict_enabled": inp.strict_enabled,
            "min_public_pool": inp.min_public_pool,
        },
        "scenarios": summary,
    }
    write_json_deterministic(args.reports / "phase5_publication_gates.json", result)
    L = [
        "# Phase 5 publication gates",
        "",
        f"Status: {STATUS}. `PUBLIC_ALLOWED` requires every applicable gate to pass. A missing, "
        "unreadable or malformed input fails its gate (`INPUT_UNAVAILABLE`). Only a human edit of "
        "`config/phase5_methodology_status_v1.json` can set `methodology_validated`.",
        "",
        "## Gate definitions",
        md_table(
            ["gate", "passes when"],
            [
                [
                    "data_weight_gate_passed",
                    "none of the four format-role cells is `THRESHOLD_NOT_VALIDATED` in `phase4_frozen_choices.json`",
                ],
                [
                    "methodology_validated",
                    "`validated: true` with non-blank `validated_by`, `validated_date`, `evidence_path`",
                ],
                [
                    "strict_classification_available",
                    "applicable only to requests using uncapped or verified filters; passes when `strict_uncapped_enabled`",
                ],
                [
                    "min_eligible_pool",
                    f"eligible rows after all filters >= {inp.min_public_pool} (provisional)",
                ],
                [
                    "date_verification",
                    "date-verification summary reports the gate as passed (not yet run in this chunk: fails with `NOT_RUN`)",
                ],
            ],
        ),
        "",
    ]
    for name, s in summary.items():
        L += [
            f"## {name}",
            f"publication_status: **{s['publication_status']}**; failing: {s['failing_gates']}",
            md_table(
                ["gate", "passed", "applicable", "detail"],
                [
                    [g["gate_id"], g["passed"], g["applicable"], g["detail"]]
                    for g in s["gate_results"]
                ],
            ),
            "",
        ]
    L += dynamic_section(args.reports, inp.min_public_pool)
    write_text(args.reports / "phase5_publication_gates.md", "\n".join(L))
    for name, s in summary.items():
        print(name, "->", s["publication_status"], s["failing_gates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
