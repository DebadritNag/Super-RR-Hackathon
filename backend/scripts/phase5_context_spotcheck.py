"""Phase 5 Chunk 4 spot check: context-specific n and actual-runs sum recomputed from raw state rows.

For the top-ranked player of two real contexts (IPL batter death chase, T20I bowler middle chase)
this recomputes, with plain SQL/pandas over ``exp_pre_delivery_state`` joined to ``p4_match_period``
(TEST matches excluded), the number of pressure deliveries and the sum of actual outcome runs, and
compares them with the stored context rows (``p5_context_stats``) and the engine's response. The
expected-runs sum is compared with a second path through the Phase 5 study (baseline refit). The
chase threshold comes from the frozen Phase 4 choices. EXPERIMENTAL; read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.main import create_app  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

BASE = (
    "COALESCE(s.regulation_pressure_eligible, false) AND NOT COALESCE(s.format_out_of_scope, false) "
    "AND NOT COALESCE(s.dls_exclude_primary, false) AND s.innings_number IN (1, 2) "
    "AND s.competition_type = ? AND p.period <> 'TEST'"
)
CHASE = (
    "COALESCE(s.chase_flag, false) AND NOT COALESCE(s.target_basis_unverified, false) "
    "AND NOT COALESCE(s.req_nonpositive_flag, false) AND s.rrr IS NOT NULL AND s.rrr >= ?"
)


def independent(con, comp: str, role: str, phase: str, pid: int, thr: float) -> dict:
    if role == "batter":
        who, extra, actual = (
            "s.striker_id",
            "AND s.den_counts_as_ball_faced = 1",
            "s.out_batter_runs",
        )
    else:
        who, extra, actual = (
            "s.bowler_id",
            "AND s.den_bowler_counts_row = 1",
            "s.den_bowler_charged_runs",
        )
    sql = (
        f"SELECT count(*), sum({actual}), count(DISTINCT s.match_id) FROM exp_pre_delivery_state s "
        f"JOIN p4_match_period p USING (match_id) WHERE {BASE} AND {CHASE} AND s.innings_number = 2 "
        f"AND s.innings_phase = ? AND {who} = ? {extra}"
    )
    n, a, m = con.execute(sql, [comp, thr, phase, pid]).fetchone()
    # innings-2 rows that would fall into the innings-1 population (no chase flag) are not counted
    odd = con.execute(
        f"SELECT count(*) FROM exp_pre_delivery_state s JOIN p4_match_period p USING (match_id) "
        f"WHERE {BASE} AND s.innings_number = 2 AND NOT COALESCE(s.chase_flag, false) "
        f"AND s.innings_phase = ? AND {who} = ? {extra}",
        [comp, phase, pid],
    ).fetchone()[0]
    return {
        "n": int(n),
        "actual_sum": float(a),
        "matches": int(m),
        "innings2_without_chase_flag": int(odd),
    }


def main() -> int:
    frozen = pl.load_frozen()
    thr = frozen["definition"]["train_only_thresholds"]
    c = TestClient(create_app(admin_token="spot"))
    h = {"X-Admin-Token": "spot"}
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    study = None
    out = {}
    try:
        for comp, role, phase in (("IPL", "batter", "death"), ("T20I", "bowler", "middle")):
            body = {"role": role, "format": comp, "phase": phase, "situation": "chase", "limit": 1}
            row = c.post("/api/v1/internal/rankings/dynamic", json=body, headers=h).json()["page"][
                "items"
            ][0]
            pid = row["player_id"]
            ind = independent(con, comp, role, phase, pid, thr[f"chase|{comp}"])
            st = con.execute(
                "SELECT sum(n), sum(s), sum(e), count(DISTINCT match_id) FROM p5_context_stats "
                "WHERE player_id = ? AND comp = ? AND role = ? AND phase = ? AND situation = 'chase'",
                [pid, comp, role, phase],
            ).fetchone()
            if study is None:
                study = pl.load_study()
            rows = study.pressure_rows(
                frozen["definition"]["id"], role, "runs" if role == "batter" else "charged"
            )
            src = rows["src"].to_numpy()
            ph = study.d["innings_phase"].reindex(src).to_numpy()
            inn = study.d["innings_number"].reindex(src).to_numpy()
            sel = rows[
                (rows["player_id"] == pid) & (rows["comp"] == comp) & (ph == phase) & (inn == 2)
            ]
            engine_n, engine_resid = row["n"], row["residual"] * row["n"]
            res = {
                "player_id": pid,
                "name": row["name"],
                "engine_response": {"n": engine_n, "matches": row["matches"], "raw_mean": row["raw"],
                                    "expected_mean": row["expected"], "residual_sum": engine_resid},
                "independent_state_table": ind,
                "stored_context_rows": {"n": st[0], "residual_sum": st[1], "expected_sum": st[2], "matches": st[3]},
                "study_second_path": {"n": int(len(sel)), "residual_sum": float(sel["resid"].sum()),
                                      "expected_sum": float(sel["expected"].sum())},
            }  # fmt: skip
            res["n_agrees"] = bool(
                ind["n"] == engine_n == int(st[0]) == res["study_second_path"]["n"]
            )
            res["matches_agree"] = bool(ind["matches"] == row["matches"] == int(st[3]))
            res["actual_sum_agrees"] = bool(
                np.isclose(ind["actual_sum"], row["raw"] * engine_n, rtol=0, atol=1e-6)
            )
            res["residual_agrees"] = bool(
                np.isclose(engine_resid, st[1], atol=1e-6)
                and np.isclose(st[1], res["study_second_path"]["residual_sum"], atol=1e-6)
            )
            res["expected_agrees"] = bool(
                np.isclose(st[2], res["study_second_path"]["expected_sum"], atol=1e-6)
            )
            out[f"{comp}|{role}|{phase}|chase"] = res
    finally:
        con.close()
    ok = all(v[k] for v in out.values() for k in ("n_agrees", "matches_agree", "actual_sum_agrees",
                                                  "residual_agrees", "expected_agrees"))  # fmt: skip
    write_json_deterministic(
        REPORTS_DIR / "phase5_context_spotcheck.json", {"all_agree": ok, "checks": out}
    )
    print(json.dumps({"all_agree": ok, "checks": out}, indent=1, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
