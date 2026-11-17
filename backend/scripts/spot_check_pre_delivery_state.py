"""Independent spot-check of the exploratory pre-delivery state against the raw CSV files.

The check uses only the standard library `csv` module on `updated_ball_by_ball.csv` and
`matches.csv` (no pandas, no DuckDB, no engine code) to recompute counters and compares them with
the exploratory store. EXPLORATORY_NOT_VALIDATED. Exit code 1 on any mismatch.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB, STATE_TABLE  # noqa: E402
from app.utils.jsonio import write_json  # noqa: E402

NON_LEGAL = {"wide", "Overstep", "other", "Penalty"}


def read_raw(data_root: Path):
    inn = defaultdict(list)
    with open(data_root / "updated_ball_by_ball.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            inn[(int(r["match_id"]), int(r["innings"]))].append(r)
    for rows in inn.values():
        rows.sort(key=lambda r: int(r["innings_ball_num"]))
    matches = {}
    with open(data_root / "matches.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            matches[int(r["match_id"])] = r
    return inn, matches


def num(x):
    return float(x) if x not in ("", None) else None


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument(
        "--out", type=Path, default=s.phase25_reports_dir / "pre_delivery_state_spot_check.json"
    )
    args = ap.parse_args(argv)
    inn, matches = read_raw(s.data_root)
    con = duckdb.connect(str(args.store), read_only=True)
    st = {
        (a, b, c): (r, w, lb, req, brem)
        for a, b, c, r, w, lb, req, brem in con.execute(
            f"SELECT match_id, innings_number, innings_ball_num, team_runs_before, team_wickets_before, "
            f"legal_balls_bowled_before, runs_required, legal_balls_remaining FROM {STATE_TABLE}"
        ).fetchall()
    }
    death_store = con.execute(
        f"SELECT count(*) FROM {STATE_TABLE} WHERE innings_phase = 'death' AND innings_limit_balls = 120"
    ).fetchone()[0]
    con.close()

    mism, rows_checked, death_indep = [], 0, 0
    totals, legal_tot = {}, {}
    for (mid, n), rows in inn.items():
        r = w = lb = 0
        for row in rows:
            k = int(row["innings_ball_num"])
            exp = (r, w, lb)
            got = st.get((mid, n, k))
            rows_checked += 1
            if got is None or tuple(got[:3]) != exp:
                mism.append({"key": (mid, n, k), "expected": exp, "store": got and got[:3]})
            if n in (1, 2) and lb >= 90:
                rev = matches[mid][
                    "first_inn_revised_overs" if n == 1 else "second_inn_revised_overs"
                ]
                if rev == "":
                    death_indep += 1
            et = row["extras_type"]
            r += int(row["runs"]) + int(row["extras1_runs"]) + int(row["extras_2_runs"])
            w += 1 if row["is_wicket"].lower() == "true" else 0
            lb += 0 if et in NON_LEGAL else 1
        totals[(mid, n)] = r
        legal_tot[(mid, n)] = lb

    # target = innings-1 total + 1 (raw CSV), or matches.csv revised_target, for every chase
    tgt_mism, tgt_checked, revised_checked = [], 0, 0
    con = duckdb.connect(str(args.store), read_only=True)
    store_t = dict(
        con.execute(
            f"SELECT match_id, any_value(target) FROM {STATE_TABLE} WHERE innings_number = 2 GROUP BY 1"
        ).fetchall()
    )
    store_rrr = con.execute(
        f"SELECT match_id, innings_ball_num, runs_required, legal_balls_remaining, rrr, wickets_remaining "
        f"FROM {STATE_TABLE} WHERE innings_number = 2 AND match_id IN (SELECT match_id FROM {STATE_TABLE} "
        f"WHERE innings_number = 2 GROUP BY 1 ORDER BY 1 LIMIT 3) AND innings_ball_num IN (30, 60, 100) "
        f"ORDER BY 1, 2"
    ).fetchall()
    con.close()
    for mid, t in store_t.items():
        rev = matches[mid]["revised_target"]
        if rev != "":
            exp_t = int(float(rev))
            revised_checked += 1
        elif (mid, 1) in totals:
            exp_t = totals[(mid, 1)] + 1
        else:
            exp_t = None
        tgt_checked += 1
        if (t is None and exp_t is not None) or (t is not None and t != exp_t):
            tgt_mism.append({"match_id": mid, "expected": exp_t, "store": t})

    # runs required / RRR / wickets remaining at fixed balls, recomputed by hand from raw rows
    spot = []
    for mid, k, req_s, brem_s, rrr_s, wrem_s in store_rrr:
        rows = inn[(mid, 2)]
        pre = [x for x in rows if int(x["innings_ball_num"]) < k]
        runs = sum(int(x["runs"]) + int(x["extras1_runs"]) + int(x["extras_2_runs"]) for x in pre)
        wk = sum(1 for x in pre if x["is_wicket"].lower() == "true")
        legal = sum(1 for x in pre if x["extras_type"] not in NON_LEGAL)
        rev = matches[mid]["revised_target"]
        tgt = int(float(rev)) if rev != "" else totals[(mid, 1)] + 1
        lim_f = matches[mid]["second_inn_revised_overs"]
        lim = int(float(lim_f)) if lim_f != "" else 120
        req, brem = tgt - runs, lim - legal
        rrr = req / brem * 6 if brem > 0 and req > 0 else None
        ok = (req, brem, 10 - wk) == (req_s, brem_s, wrem_s) and (
            (rrr is None and rrr_s is None) or abs(rrr - rrr_s) < 1e-9
        )
        spot.append({"match_id": mid, "ball": k, "runs_required": req, "legal_balls_remaining": brem,
                     "rrr": rrr, "wickets_remaining": 10 - wk, "matches_store": ok})  # fmt: skip
    result = {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "method": "stdlib csv on updated_ball_by_ball.csv and matches.csv; no engine code, no pandas, no DuckDB",
        "rows_checked_all_rows_independent_counters": rows_checked,
        "counter_mismatches": len(mism),
        "counter_mismatch_examples": mism[:5],
        "chase_targets_checked": tgt_checked,
        "revised_targets_checked_against_matches_csv": revised_checked,
        "target_mismatches": len(tgt_mism),
        "target_mismatch_examples": tgt_mism[:5],
        "fixed_ball_spot_checks": spot,
        "death_rows_independent_unrevised_innings": death_indep,
        "death_rows_store_L120": death_store,
    }
    write_json(args.out, result)
    bad = bool(mism or tgt_mism or not all(x["matches_store"] for x in spot))
    bad = bad or death_indep != death_store
    print({k: v for k, v in result.items() if k not in ("fixed_ball_spot_checks",)})
    for x in spot:
        print(x)
    print("PASS" if not bad else "FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
