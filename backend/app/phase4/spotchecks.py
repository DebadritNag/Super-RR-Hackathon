"""Independent spot checks of stored Phase 4 numbers, each by a different method.

Raw CSV checks use only the standard ``csv`` module. Pandas checks recompute from stored tables
without the scoring code path. Every check returns ``{id, description, method, ok, ...}``; nothing
is hand-typed and a failure is reported, never hidden. EXPERIMENTAL_NOT_VALIDATED.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.phase4.constants import STATUS
from app.services.pressure_service import STATE_TABLE

NON_LEGAL = {"wide", "Overstep", "other", "Penalty"}
MIN_PRIOR = 30


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check_strictly_prior_par(store: Path, data_root: Path, min_prior: int = MIN_PRIOR) -> dict:
    """Par for one IPL VALIDATION innings recomputed from the raw CSV (prior matches only)."""
    con = duckdb.connect(str(store), read_only=True)
    try:
        row = con.execute(
            f"SELECT e.match_id, e.match_date, e.innings_ball_num, p.par_runs_prior "
            f"FROM {STATE_TABLE} e JOIN exp_pressure_signals p USING "
            "(match_id, innings_number, innings_ball_num) "
            "WHERE e.competition_type = 'IPL' AND e.innings_number = 1 "
            "AND e.legal_balls_bowled_before = 60 "
            "AND e.match_date BETWEEN DATE '2025-03-01' AND DATE '2025-12-31' "
            "ORDER BY e.match_date, e.match_id, e.innings_ball_num LIMIT 1"
        ).fetchone()
        ipl = con.execute(
            f"SELECT DISTINCT match_id, match_date FROM {STATE_TABLE} "
            "WHERE competition_type = 'IPL'"
        ).fetchall()
    finally:
        con.close()
    mid, mdate, ball, stored = row
    prior_ids = {m for m, d in ipl if pd.Timestamp(d) < pd.Timestamp(mdate)}
    same_day = {m for m, d in ipl if pd.Timestamp(d) == pd.Timestamp(mdate)} - {mid}
    matches = {int(r["match_id"]): r for r in _read_csv(data_root / "matches.csv")}
    inn: dict[int, list[dict]] = defaultdict(list)
    for r in _read_csv(data_root / "updated_ball_by_ball.csv"):
        if r["innings"] == "1" and int(r["match_id"]) in prior_ids:
            inn[int(r["match_id"])].append(r)
    values = []
    for m, rows in inn.items():
        if matches[m]["first_inn_revised_overs"] != "":
            continue
        rows.sort(key=lambda r: int(r["innings_ball_num"]))
        runs = wk = lb = 0
        at: dict[int, int] = {}
        for r in rows:
            at.setdefault(lb, runs)
            runs += int(r["runs"]) + int(r["extras1_runs"]) + int(r["extras_2_runs"])
            wk += 1 if r["is_wicket"].lower() == "true" else 0
            lb += 0 if r["extras_type"] in NON_LEGAL else 1
        at[lb] = runs
        if not (wk == 10 or lb == 120) or lb > 120:
            continue
        values.append(at[max(b for b in at if b <= 60)])
    n = len(values)
    indep = float(np.mean(values)) if n >= min_prior else None
    ok = (indep is None and stored is None) or (
        indep is not None and stored is not None and abs(indep - float(stored)) < 1e-9
    )
    return {
        "id": "strictly_prior_par_from_raw_csv",
        "description": f"IPL first-innings par at legal ball 60 for match {mid} ({mdate})",
        "method": "csv module on updated_ball_by_ball.csv and matches.csv; prior dates only",
        "match_id": int(mid),
        "stored_innings_ball_num": int(ball),
        "stored_par": None if stored is None else float(stored),
        "independent_par": indep,
        "prior_source_innings_independent": n,
        "same_day_matches_excluded": len(same_day),
        "ok": bool(ok),
    }


def check_period_counts(store: Path, data_root: Path, manifest: dict, split_cfg: dict) -> dict:
    """Matches per format and period from raw match dates versus the stored manifest."""
    con = duckdb.connect(str(store), read_only=True)
    try:
        comp = dict(
            con.execute(f"SELECT DISTINCT match_id, competition_type FROM {STATE_TABLE}").fetchall()
        )
    finally:
        con.close()
    p = split_cfg["periods"]
    tr_end, va_end = p["TRAIN"]["end"], p["VALIDATION"]["end"]
    got: dict[str, int] = defaultdict(int)
    for r in _read_csv(data_root / "matches.csv") + _read_csv(data_root / "matches 2026.csv"):
        m = int(r["match_id"])
        if m not in comp:
            continue
        d = r["match_date"][:10]
        per = "TRAIN" if d <= tr_end else "VALIDATION" if d <= va_end else "TEST"
        got[f"{comp[m]}|{per}"] += 1
    stored = {
        f"{r['competition_type']}|{r['period']}": int(r["matches"])
        for r in manifest["matches_by_format_period"]
    }
    diffs = {k: [got.get(k, 0), v] for k, v in stored.items() if got.get(k, 0) != v}
    return {
        "id": "period_match_counts_from_raw_csv",
        "description": "matches per format and period from raw match dates",
        "method": "csv module on matches.csv and matches 2026.csv; boundaries from split config",
        "independent": dict(sorted(got.items())),
        "stored": dict(sorted(stored.items())),
        "differences_independent_vs_stored": diffs,
        "ok": not diffs,
    }


def check_player_pressure_balls(store: Path, scores: pd.DataFrame, frozen: dict) -> dict:
    """One eligible player's pressure balls and raw outcome recomputed by direct SQL."""
    defn = frozen["definition"]["id"]
    ctx = defn.split("|")[0]
    thr = frozen["definition"]["train_only_thresholds"]
    cfg = frozen["shrinkage"]["config"]
    rec = scores[
        (scores["definition_id"] == defn)
        & (scores["shrinkage_config"] == cfg)
        & (scores["format"] == "IPL")
        & (scores["role"] == "batter")
        & (scores["stream"] == "runs")
        & scores["eligibility_status"].str.startswith("ELIGIBLE")
    ].sort_values(["pressure_opportunities", "player_id"], ascending=[False, True])
    r = rec.iloc[0]
    base = (
        "e.regulation_pressure_eligible AND NOT COALESCE(e.format_out_of_scope, false) "
        "AND NOT COALESCE(e.dls_exclude_primary, false) AND e.innings_number IN (1, 2) "
        "AND e.competition_type = 'IPL'"
    )
    chase = (
        f"({base} AND COALESCE(e.chase_flag, false) AND NOT COALESCE(e.target_basis_unverified, "
        "false) AND NOT COALESCE(e.req_nonpositive_flag, false) AND e.rrr IS NOT NULL "
        f"AND e.rrr >= {float(thr['chase|IPL'])!r})"
    )
    inn1 = (
        f"({base} AND NOT COALESCE(e.chase_flag, false) AND p.par_runs_prior IS NOT NULL "
        f"AND -(e.team_runs_before - p.par_runs_prior) >= {float(thr['inn1|IPL'])!r})"
    )
    cond = chase if ctx == "chase" else inn1 if ctx == "inn1" else f"({chase} OR {inn1})"
    con = duckdb.connect(str(store), read_only=True)
    try:
        n, runs, matches = con.execute(
            "SELECT count(*), sum(e.out_batter_runs), count(DISTINCT e.match_id) "
            f"FROM {STATE_TABLE} e JOIN exp_pressure_signals p USING "
            "(match_id, innings_number, innings_ball_num) "
            f"WHERE e.striker_id = {int(r['player_id'])} AND e.den_counts_as_ball_faced = 1 "
            f"AND e.match_date <= DATE '2025-12-31' AND {cond}"
        ).fetchone()
    finally:
        con.close()
    raw = None if not n else float(runs) / float(n)
    ok = (
        int(n) == int(r["pressure_opportunities"])
        and int(matches) == int(r["distinct_matches"])
        and raw is not None
        and abs(raw - float(r["raw_pressure_outcome"])) < 1e-9
    )
    return {
        "id": "player_pressure_balls_direct_sql",
        "description": f"IPL batter {int(r['player_id'])} pressure balls, matches and runs per ball",
        "method": "DuckDB SQL on the stored state table, definition rebuilt from frozen thresholds",
        "player_id": int(r["player_id"]),
        "stored": {
            "pressure_opportunities": int(r["pressure_opportunities"]),
            "distinct_matches": int(r["distinct_matches"]),
            "raw_pressure_outcome": float(r["raw_pressure_outcome"]),
        },
        "independent": {
            "pressure_opportunities": int(n),
            "distinct_matches": int(matches),
            "raw_pressure_outcome": raw,
        },  # fmt: skip
        "ok": bool(ok),
    }


def check_shrunk_by_hand(scores: pd.DataFrame, frozen: dict) -> dict:
    """Shrunk estimate rebuilt from stored components: B = n_eff / (n_eff + k) and bracketing."""
    cfg = frozen["shrinkage"]["config"]
    s = scores[
        (scores["definition_id"] == frozen["definition"]["id"])
        & (scores["shrinkage_config"] == cfg)
        & scores["data_weight"].notna()
        & scores["residual"].notna()
        & ~scores["format"].str.startswith("COMBINED")
    ].copy()
    B = s["effective_sample_size"] / (s["effective_sample_size"] + s["shrinkage_k"])
    err_B = (B - s["data_weight"]).abs().max()
    tgt = (s["shrunk_estimate"] - B * s["residual"]) / (1 - B).where(1 - B > 1e-9)
    by = s.assign(target=tgt).groupby(["format", "role", "stream"])["target"]
    spread = by.agg(lambda x: float(x.max() - x.min()))
    ident = (s["residual"] - (s["raw_pressure_outcome"] - s["expected_baseline_outcome"])).abs()
    inside = (
        (s["interval_low"] <= s["shrunk_estimate"] + 1e-9)
        & (s["shrunk_estimate"] <= s["interval_high"] + 1e-9)
    ).mean()
    return {
        "id": "shrunk_estimate_from_stored_components",
        "description": "B = n_eff / (n_eff + k); implied shrink target is near-constant per cell",
        "method": "pandas on the stored frozen-rules score table",
        "records_checked": int(len(s)),
        "max_abs_B_error": float(err_B),
        "max_abs_residual_identity_error": float(ident.max()),
        "max_implied_target_range_within_cell": float(spread.max()),
        "share_point_estimate_inside_interval": float(inside),
        "ok": bool(err_B < 1e-9 and ident.max() < 1e-9 and spread.max() < 0.1),
    }


def check_capped_count(data_root: Path, classification: pd.DataFrame) -> dict:
    """Capped players recounted from playing_eleven, matches and competitions CSVs."""
    as_of = str(classification["as_of_date"].iloc[0])[:10]
    t20i = {r["comp_id"] for r in _read_csv(data_root / "competitions.csv")
            if r["match_format"] == "T20I"}  # fmt: skip
    ids = {r["match_id"] for r in _read_csv(data_root / "matches.csv")
           if r["comp_id"] in t20i and r["match_date"][:10] <= as_of}  # fmt: skip
    players = {r["player_id"] for r in _read_csv(data_root / "playing_eleven.csv")
               if r["match_id"] in ids and r["is_played"].lower() == "true"}  # fmt: skip
    # Phase 4 table: "Capped"; Phase 5 table: DERIVED_CAPPED + VERIFIED_CAPPED (documented mapping).
    stored = int(
        classification["international_status"]
        .isin(["Capped", "DERIVED_CAPPED", "VERIFIED_CAPPED"])
        .sum()
    )
    return {
        "id": "capped_count_from_playing_eleven_csv",
        "description": f"players with a played T20I on or before {as_of}",
        "method": "csv module on competitions.csv, matches.csv and playing_eleven.csv",
        "independent": len(players),
        "stored_capped": stored,
        "ok": len(players) == stored,
    }


def check_inclusion_sums(distributions: pd.DataFrame, summary: pd.DataFrame) -> dict:
    """Top-10 inclusion probabilities sum to min(10, pool) in every pool."""
    out, ok = {}, True
    for (sc, role), g in distributions.groupby(["scope", "role"]):
        pool = int(
            summary[(summary["scope"] == sc) & (summary["role"] == role)]["pool_size"].iloc[0]
        )
        s = float(g["top10_inclusion_prob"].sum())
        out[f"{sc}|{role}"] = {"sum": s, "expected": float(min(10, pool))}
        ok &= abs(s - min(10, pool)) < 0.5
    return {
        "id": "top10_inclusion_probability_sums",
        "description": "inclusion probabilities sum to about min(10, pool size) per pool",
        "method": "pandas on the stored ranking distributions",
        "pools": out,
        "ok": bool(ok),
    }


def check_hashes(hash_before: Path, skip: tuple[str, ...] = ("exploratory.duckdb",)) -> dict:
    """Current SHA-256 of every file recorded before Phase 4 versus the recorded value."""
    import hashlib

    diffs, n = [], 0
    for line in hash_before.read_text(encoding="utf-8-sig").splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) != 2 or any(parts[1].endswith(s) for s in skip):
            continue
        h, p = parts[0], Path(parts[1].strip())
        n += 1
        now = hashlib.sha256(p.read_bytes()).hexdigest().upper() if p.exists() else "MISSING"
        if now != h.upper():
            diffs.append(str(p))
    return {
        "id": "official_data_hashes",
        "description": "superr.duckdb and source files equal the pre-Phase-4 hashes",
        "method": "SHA-256 against phase4_hash_before.txt",
        "files_checked": n,
        "changed": diffs,
        "ok": not diffs,
    }


def run_all(
    store: Path, reports: Path, data_root: Path, hash_before: Path | None
) -> dict[str, Any]:
    manifest = json.loads((reports / "phase4_split_manifest.json").read_text(encoding="utf-8"))
    frozen = json.loads((reports / "phase4_frozen_choices.json").read_text(encoding="utf-8"))
    split_cfg = json.loads(
        (Path(__file__).resolve().parents[2] / "config" / "phase4_split_v1.json").read_text("utf-8")
    )
    scores = pd.read_csv(reports / "phase4_pressure_scores_frozen_rules.csv")
    cls = pd.read_csv(reports / "phase4_classification.csv")
    dist = pd.read_csv(reports / "phase4_ranking_distributions.csv")
    summ = pd.read_csv(reports / "phase4_ranking_summary.csv")
    checks = [
        check_strictly_prior_par(store, data_root),
        check_period_counts(store, data_root, manifest, split_cfg),
        check_player_pressure_balls(store, scores, frozen),
        check_shrunk_by_hand(scores, frozen),
        check_capped_count(data_root, cls),
        check_inclusion_sums(dist, summ),
    ]
    if hash_before is not None and hash_before.exists():
        checks.append(check_hashes(hash_before))
    return {
        "status": STATUS,
        "official_ranking": False,
        "checks": checks,
        "all_ok": all(c["ok"] for c in checks),
    }
