"""Overview and methodology-summary facts for the public descriptive endpoints.

Built once by ``scripts/phase7_build_descriptive.py`` from the official database and the stored
Phase 5 / Phase 6 tables and reports (all opened read-only) and written to
``phase7_descriptive_context.json``. The API reads that file; it never recomputes or invents
these numbers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.phase7.descriptive import EXPLORATORY_DB, OFFICIAL_DB, REPORTS

PRIMARY_DEFINITION = "any|q0.75"


def official_counts(official: Path | str = OFFICIAL_DB) -> dict[str, Any]:
    o = duckdb.connect(str(official), read_only=True)
    try:
        m = o.execute(
            "SELECT competition_type, count(*) AS matches, "
            "sum(CASE WHEN has_deliveries THEN 1 ELSE 0 END) AS with_deliveries, "
            "min(match_date) AS first_date, max(match_date) AS last_date "
            "FROM matches GROUP BY 1 ORDER BY 1"
        ).df()
        deliveries = int(o.execute("SELECT count(*) FROM deliveries").fetchone()[0])
        lineage = o.execute(
            "SELECT file_name, role, row_count, sha256, load_status FROM dataset_lineage "
            "ORDER BY lineage_id"
        ).df()
        schema = o.execute("SELECT * FROM schema_meta").df()
    finally:
        o.close()
    return {
        "matches_by_competition": [
            {
                "competition_type": r.competition_type,
                "matches": int(r.matches),
                "matches_with_deliveries": int(r.with_deliveries),
                "first_date": str(r.first_date)[:10],
                "last_date": str(r.last_date)[:10],
            }
            for r in m.itertuples()
        ],
        "matches_total": int(m["matches"].sum()),
        "delivery_rows_total": deliveries,
        "lineage": [
            {
                "file_name": r.file_name,
                "role": r.role,
                "row_count": int(r.row_count),
                "sha256": r.sha256,
                "load_status": r.load_status,
            }
            for r in lineage.itertuples()
        ],
        "schema_meta": {str(r[0]): str(r[1]) for r in schema.itertuples(index=False)}
        if schema.shape[1] >= 2
        else {},
    }


def store_counts(store: Path | str = EXPLORATORY_DB) -> dict[str, Any]:
    e = duckdb.connect(str(store), read_only=True)
    try:
        periods = e.execute("SELECT period, count(*) FROM p4_match_period GROUP BY 1").fetchall()
        inn34 = int(
            e.execute(
                "SELECT count(*) FROM exp_pre_delivery_state WHERE innings_number IN (3, 4)"
            ).fetchone()[0]
        )
        oos = int(
            e.execute(
                "SELECT count(*) FROM exp_pre_delivery_state WHERE format_out_of_scope"
            ).fetchone()[0]
        )
        late = e.execute(
            "SELECT count(*), count(DISTINCT match_id) FROM p5_t20i_date_verification"
        ).fetchone()
    finally:
        e.close()
    return {
        "match_periods": {str(p): int(n) for p, n in periods},
        "rows_in_innings_3_4_excluded": inn34,
        "rows_out_of_scope_competition": oos,
        "late_t20i_dates_unverified": int(late[1]),
    }


def reliability_facts(
    store: Path | str = EXPLORATORY_DB, reports: Path | str = REPORTS
) -> dict[str, Any]:
    reports = Path(reports)
    e = duckdb.connect(str(store), read_only=True)
    try:
        fit = e.execute(
            "SELECT count(*), sum(CAST(floor_hit AS INTEGER)) FROM p5_context_fit"
        ).fetchone()
        gate = e.execute(
            "SELECT count(*), sum(CAST(data_weight_gate_passed AS INTEGER)), max(gate_used) "
            "FROM p6_data_weight_gate_status"
        ).fetchone()
        pooled = e.execute(
            "SELECT pooled_sb FROM p6_split_half_pooled WHERE definition = ? "
            "AND stream_group = 'primary' AND \"window\" = 'PRE_TEST' AND \"mode\" = 'odd_even'",
            [PRIMARY_DEFINITION],
        ).fetchone()
        best = e.execute(
            "SELECT max(data_weight), count(DISTINCT option_id) FROM p6_data_weight_options "
            "WHERE applicable"
        ).fetchone()
    finally:
        e.close()
    ctx = pd.read_csv(reports / "phase6_context_reliability.csv")
    est = ctx[ctx["oe_status"] == "ESTIMATED"]
    tg = pd.read_csv(reports / "phase6_eligibility_reliability_targets.csv")
    pre = tg[tg["window"] == "PRE_TEST"]
    ladder = {
        str(t): {"cells": int(len(g)), "reached": int((g["status"] == "TARGET_REACHED").sum())}
        for t, g in pre.groupby("target")
    }
    ss = pd.read_csv(reports / "phase6_robustness_season_checks.csv")
    med = ss.groupby("check")["value"].median()
    return {
        "contexts": int(fit[0]),
        "contexts_at_variance_floor": int(fit[1]),
        "contexts_passing_data_weight_check": int(gate[1] or 0),
        "data_weight_threshold": float(gate[2]),
        "pooled_odd_even_reliability": float(pooled[0]),
        "estimable_contexts": int(len(est)),
        "median_context_reliability": float(est["oe_sb"].median()),
        "reliability_ladder": ladder,
        "best_data_weight_any_option": float(best[0]),
        "improvement_options_examined": int(best[1]),
        "season_check_medians": {str(k): float(v) for k, v in med.items()},
    }


def reliability_checks(f: dict[str, Any]) -> list[dict[str, Any]]:
    lad = f["reliability_ladder"]
    thr = f["data_weight_threshold"]
    return [
        {
            "check_id": "variance_floor",
            "label": "Between-player variance above the shrinkage floor",
            "observed": f"at the floor in {f['contexts_at_variance_floor']} of {f['contexts']} contexts",
            "threshold": "above the floor",
            "status": "NOT_MET",
        },
        {
            "check_id": "data_weight",
            "label": "Marginal data weight of the shrunk estimate",
            "observed": f"{f['contexts_passing_data_weight_check']} of {f['contexts']} contexts pass",
            "threshold": f"at least {thr:g}",
            "status": "NOT_MET",
        },
        {
            "check_id": "pooled_reliability",
            "label": "Pooled odd/even reliability of the provisional definition",
            "observed": f"{f['pooled_odd_even_reliability']:.2f}",
            "threshold": "0.70 or higher for individual comparisons",
            "status": "NOT_MET",
        },
        {
            "check_id": "median_context_reliability",
            "label": f"Median reliability across {f['estimable_contexts']} estimable contexts",
            "observed": f"{f['median_context_reliability']:.2f}",
            "threshold": "0.50 or higher",
            "status": "NOT_MET",
        },
        {
            "check_id": "reliability_ladder",
            "label": "Reliability targets reached within the tested ball ladder",
            "observed": ", ".join(
                f"{k}: {v['reached']} of {v['cells']} cells" for k, v in sorted(lad.items())
            ),
            "threshold": "0.7 and 0.8 in every cell",
            "status": "NOT_MET",
        },
    ]


METHODOLOGY_SECTIONS = (
    (
        "What is published",
        "Descriptive batting and bowling profiles from official ball-by-ball data, for IPL and "
        "T20I separately, over the pre-test window (2022 to 2025). Counts, rates, splits and "
        "match-bootstrap uncertainty on the main rate. There is no composite score and no ordering "
        "of players.",
    ),
    (
        "What is not published",
        "A Top 10 list of pressure batters or bowlers. The pressure measure cannot separate "
        "individual players with the available data, so no list is shown and no list is padded.",
    ),
    (
        "Descriptive versus pressure statistics",
        "Runs, strike rate, economy and wickets are descriptive. They describe what happened and "
        "are not a statement about performance under pressure. The only pressure-related columns "
        "are counts of deliveries that fall in a provisional context definition.",
    ),
    (
        "Data rules",
        "Official ball-by-ball rows only; innings 3 and 4 (super overs) are excluded from "
        "regulation metrics; wides and the Penalty row are not balls faced or legal balls; "
        "bowler wickets are bowler-credited only; DLS-affected rows are kept and counted; "
        "OTHER_T20 is not profiled; TEST-period matches are never read.",
    ),
)


def build_context(
    frame_summary: dict[str, Any],
    official: Path | str = OFFICIAL_DB,
    store: Path | str = EXPLORATORY_DB,
    reports: Path | str = REPORTS,
) -> dict[str, Any]:
    oc = official_counts(official)
    sc = store_counts(store)
    rf = reliability_facts(store, reports)
    checks = reliability_checks(rf)
    why = [
        f"The between-player variance sits at the shrinkage floor in {rf['contexts_at_variance_floor']} "
        f"of {rf['contexts']} contexts, so the data cannot separate individual players.",
        f"The data-weight check ({rf['data_weight_threshold']:g}) passes in "
        f"{rf['contexts_passing_data_weight_check']} of {rf['contexts']} contexts.",
        f"Pooled odd/even reliability of the provisional definition is "
        f"{rf['pooled_odd_even_reliability']:.2f}; the median over {rf['estimable_contexts']} "
        f"estimable contexts is {rf['median_context_reliability']:.2f}.",
        f"The best of {rf['improvement_options_examined']} examined improvement options reaches a "
        f"marginal data weight of {rf['best_data_weight_any_option']:.2f} only by changing the "
        "methodology, which the project owner did not adopt.",
        "The provisional definition is not validated and no clean hold-out exists.",
    ]
    return {
        "version": "p7_descriptive_context_v1",
        "overview": {
            "official": oc,
            "analytical_store": sc,
            "descriptive_scope": frame_summary,
            "pending_official_inputs": [
                {
                    "item": "Official verification of 42 late T20I match dates",
                    "status": "PENDING",
                    "handling": "Dates are not changed or inferred; matches stay excluded from "
                    "pressure work.",
                },
                {
                    "item": "Authoritative cap-status source with stable player ids",
                    "status": "PENDING",
                    "handling": "Status is shown only with its verification label; Unknown stays Unknown.",
                },
                {
                    "item": "Official IPL retention list (expected 17 November 2026)",
                    "status": "PENDING",
                    "handling": "No retention status is assumed.",
                },
            ],
            "reliability_checks": checks,
            "why_no_ordered_lists": why,
            "lists_available": False,
        },
        "methodology": {
            "sections": [{"title": a, "text": b} for a, b in METHODOLOGY_SECTIONS],
            "reliability_facts": rf,
            "primary_definition": {
                "id": PRIMARY_DEFINITION,
                "label": "PROVISIONAL, not validated",
            },
        },
    }
