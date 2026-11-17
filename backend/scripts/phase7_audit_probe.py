"""Phase 7 audit probe: read-only recomputation of reported Phase 6 figures.

Opens exploratory.duckdb read-only and reads stored Phase 6 CSVs. Writes
data/reports/phase7_audit_probe.json. Nothing in the protected files is modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path("d:/Data/backend")
REP = ROOT / "data/reports"
EXP = ROOT / "data/database/exploratory.duckdb"


def main() -> None:
    out: dict = {}
    con = duckdb.connect(str(EXP), read_only=True)

    pooled = con.execute(
        "SELECT pooled_r, pooled_sb, players_total, cells FROM p6_split_half_pooled "
        "WHERE definition='any|q0.75' AND stream_group='primary' AND \"window\"='PRE_TEST' "
        "AND \"mode\"='odd_even'"
    ).fetchall()
    out["pooled_odd_even"] = [
        {"pooled_r": r[0], "pooled_sb": r[1], "players_total": r[2], "cells": r[3]} for r in pooled
    ]

    ctx = pd.read_csv(REP / "phase6_context_reliability.csv")
    est = ctx[ctx["oe_status"] == "ESTIMATED"]
    out["context_rows"] = int(len(ctx))
    out["estimable_contexts"] = int(len(est))
    out["median_oe_sb"] = float(est["oe_sb"].median())
    out["csv_floor_hit_contexts"] = int(ctx["floor_hit"].astype(bool).sum())
    out["csv_gate_passed_recomputed_contexts"] = int(
        ctx["gate_passed_recomputed"].astype(bool).sum()
    )

    fit = con.execute(
        "SELECT count(*), sum(CAST(floor_hit AS INTEGER)) FROM p5_context_fit"
    ).fetchone()
    out["p5_context_fit"] = {"contexts": int(fit[0]), "floor_hit": int(fit[1])}

    gate = con.execute(
        "SELECT count(*), sum(CAST(data_weight_gate_passed AS INTEGER)), min(gate_used), max(gate_used) "
        "FROM p6_data_weight_gate_status"
    ).fetchone()
    out["p6_gate_status"] = {
        "contexts": int(gate[0]),
        "passed": int(gate[1] or 0),
        "gate_min": gate[2],
        "gate_max": gate[3],
    }

    opt = con.execute(
        "SELECT option_id, data_weight, passes_gate, passes_on_estimable_subset, applicable "
        "FROM p6_data_weight_options"
    ).df()
    app = opt[opt["applicable"].astype(bool)]
    out["options"] = {
        "rows_total": int(len(opt)),
        "rows_applicable": int(len(app)),
        "applicable_rows_passing_gate": int(app["passes_gate"].astype(bool).sum()),
        "rows_passing_only_on_estimable_subset": int(
            app["passes_on_estimable_subset"].fillna(False).astype(bool).sum()
        ),
        "distinct_option_ids": int(app["option_id"].nunique()),
        "best_data_weight": float(app["data_weight"].max()),
        "best_option_id": str(app.loc[app["data_weight"].idxmax(), "option_id"]),
        "methodology_changing_option_ids": sorted(
            con.execute(
                "SELECT DISTINCT option_id FROM p6_data_weight_options "
                "WHERE requires_methodology_decision"
            )
            .df()["option_id"]
            .tolist()
        ),
    }
    summ = pd.read_csv(REP / "phase6_data_weight_improvement_options_summary.csv")
    out["options_summary_csv"] = {
        "rows": int(len(summ)),
        "sum_rows_passing_gate": int(summ["rows_passing_gate"].sum()),
        "best_data_weight": float(summ["best_data_weight"].max()),
    }

    tg = pd.read_csv(REP / "phase6_eligibility_reliability_targets.csv")
    pre = tg[tg["window"] == "PRE_TEST"]
    out["ladder_pre_test"] = {
        str(t): {
            "cells": int(len(g)),
            "reached": int((g["status"] == "TARGET_REACHED").sum()),
        }
        for t, g in pre.groupby("target")
    }

    ss = pd.read_csv(REP / "phase6_robustness_season_checks.csv")
    med = ss.groupby("check")["value"].agg(["median", "count"])
    out["season_checks"] = {
        k: {"median": float(v["median"]), "units": int(v["count"])} for k, v in med.iterrows()
    }

    rf = {}
    for y in ("2024", "2025"):
        d = pd.read_csv(REP / f"phase6_recent_form_analyses_{y}.csv")
        cols = [c for c in d.columns if "data_weight" in c or c.endswith("marginal_b")]
        rf[y] = {c: float(pd.to_numeric(d[c], errors="coerce").max()) for c in cols}
    out["recent_form_max_data_weight"] = rf

    out["gate_config_sha256"] = hashlib.sha256(
        (ROOT / "config/phase5_gates_v1.json").read_bytes()
    ).hexdigest()
    guard = json.loads((REP / "phase6_gate_guard.json").read_text(encoding="utf-8-sig"))
    out["gate_guard_file_hash_match"] = {
        k: hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == v
        for k, v in guard["files_sha256"].items()
    }
    (REP / "phase7_audit_probe.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
