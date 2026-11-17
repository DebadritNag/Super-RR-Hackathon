"""Phase 4 Stage D: data-derived pressure eligibility thresholds per format and role.

IPL batters, IPL bowlers, T20I batters and T20I bowlers are handled separately. Candidate
thresholds come from the observed TRAIN distribution of per-player pressure balls (percentiles)
plus the nominal ladder rungs of ``pressure_eligibility_rules_v1.json``. A threshold ``t`` is
expressed on the TRAIN scale: a PRE_TEST player qualifies when PRE_TEST pressure balls >= t * W,
with W = PRE_TEST balls / TRAIN balls of the cell (from the pressure sample only).

Selection rule (fixed before the run; TRAIN and VALIDATION only):
1. Data-weight gate on the marginal player: B(t) = n_t / (n_t + k) >= 0.5, n_t = smallest n_eff
   among qualifying players and k the shrinkage strength of the chosen configuration.
2. Smallest passing candidate, unless TRAIN-to-VALIDATION reproducibility is significantly
   negative (bootstrap 95% interval below zero).
3. No passing candidate: THRESHOLD_NOT_VALIDATED. A PROVISIONAL_LOW_DATA_WEIGHT fallback is named
   only if some candidate has estimable reproducibility (>= 15 players) with an interval above 0
   AND a marginal data weight of at least 0.1 (so a near-zero threshold can never be named); the
   smallest such candidate is named.
4. Thresholds are never lowered to reach ten players; the pool is whatever remains.

When a cell has no validated threshold, downstream experiments may run on an explicitly labelled
EXPLORATORY_WORKING_POOL (the TRAIN median of per-player pressure balls). That pool is never
described as validated.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en

MIN_REPRO_PLAYERS = 15
GATE_B = 0.5
ALT_GATES = (0.3, 0.1)
PCTS = (10, 25, 50, 60, 75)
PLACEHOLDERS = {"batter": 24, "bowler": 36}
LABEL_SELECTED = "ELIGIBLE_THRESHOLD_SELECTED_PROVISIONAL"
LABEL_FALLBACK = "ELIGIBLE_PROVISIONAL_LOW_DATA_WEIGHT"
LABEL_WORKING = "ELIGIBLE_WORKING_POOL_NOT_VALIDATED"
LABEL_NO = "NOT_ELIGIBLE"


def candidate_thresholds(
    train_balls: np.ndarray, ladder: list[int], pcts: tuple[int, ...] = PCTS
) -> list[dict[str, Any]]:
    """Candidate ball thresholds: ceilings of TRAIN percentiles plus ladder rungs in range."""
    out: dict[int, set[str]] = {}
    if len(train_balls):
        for pc in pcts:
            t = max(1, math.ceil(float(np.percentile(train_balls, pc))))
            out.setdefault(t, set()).add(f"P{pc}")
        mx = float(np.max(train_balls))
        for r in ladder:
            if 1 <= r <= mx:
                out.setdefault(int(r), set()).add("ladder")
    return [{"threshold": t, "source": "+".join(sorted(s))} for t, s in sorted(out.items())]


def window_ratio(cell: en.Cell, num_periods: tuple[str, ...], den_period: str) -> float:
    den = cell.N[:, cell.match_period == den_period].sum()
    num = sum(cell.N[:, cell.match_period == p].sum() for p in num_periods)
    return float(num / den) if den > 0 else float("nan")


def evaluate_cell(
    cell: en.Cell,
    fit: dict[str, Any],
    config: str,
    gm: pd.Index,
    W: np.ndarray,
    ladder: list[int],
    sign: float,
) -> dict[str, Any]:
    """All candidate thresholds of one (format, role) cell and the selection decision."""
    tp = cell.train_pt()
    est = en.point_estimates(cell, fit, config)
    w = en.cell_weights(cell, gm, W)
    nb, dr = en.draws(cell, est, w)
    k = float(est["k"].iloc[0])
    wr = window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
    rr = window_ratio(cell, ("VALIDATION",), "TRAIN")
    tr, va = cell.match_period == "TRAIN", cell.match_period == "VALIDATION"
    ntr, nva = cell.N[:, tr].sum(1), cell.N[:, va].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mtr = cell.S[:, tr].sum(1) / ntr
        mva = cell.S[:, va].sum(1) / nva
    ntr_b, nva_b = cell.N[:, tr] @ w[tr], cell.N[:, va] @ w[va]
    with np.errstate(invalid="ignore", divide="ignore"):
        mtr_b, mva_b = (cell.S[:, tr] @ w[tr]) / ntr_b, (cell.S[:, va] @ w[va]) / nva_b
    score = sign * est["shrunk"].to_numpy()
    rows = []
    for cand in candidate_thresholds(tp["n"].to_numpy(), ladder):
        t = cand["threshold"]
        scaled = t * wr
        elig = (est["n"].to_numpy() >= scaled) & np.isfinite(score)
        row: dict[str, Any] = {
            "threshold_balls": t,
            "source": cand["source"],
            "scaled_threshold_pre_test": scaled,
            "window_ratio_W": wr,
            "is_phase3_placeholder_value": t == PLACEHOLDERS[cell.role],
            "eligible_players": int(elig.sum()),
        }
        if elig.sum() == 0:
            rows.append(row)
            continue
        n_eff = est["n_eff"].to_numpy()[elig]
        row.update(
            {
                "pressure_opportunities": int(est["n"].to_numpy()[elig].sum()),
                "distinct_matches": int((cell.N[elig] > 0).any(0).sum()),
                "effective_sample_size_median": float(np.median(n_eff)),
                "marginal_n_eff": float(n_eff.min()),
                "marginal_data_weight": float(n_eff.min() / (n_eff.min() + k)) if k > 0 else 1.0,
                "median_data_weight": float(np.median(est["B"].to_numpy()[elig])),
            }
        )
        with np.errstate(all="ignore"):
            lo = np.nanpercentile(dr[elig], 2.5, axis=1)
            hi = np.nanpercentile(dr[elig], 97.5, axis=1)
        row["median_interval_width"] = float(np.nanmedian(hi - lo))
        present = elig[:, None] & (nb >= scaled) & np.isfinite(dr)
        rs = en.rank_summary(np.where(present, sign * dr, np.nan), score, elig)
        sm = en.summarize_ranking(rs)
        row.update(
            {
                "pool_size_p2_5": sm["pool_size_p2_5"],
                "pool_size_p97_5": sm["pool_size_p97_5"],
                "boot_mean_jaccard_top10": sm["mean_jaccard"],
                "expected_top10_overlap": sm["expected_top10_overlap"],
                "max_top10_overlap": sm["top10_size"],
                "boot_mean_spearman": sm["mean_spearman"],
                "trivial_full_pool": sm["trivial_full_pool"],
            }
        )
        q = (ntr >= t) & (nva >= math.ceil(t * rr)) & np.isfinite(mtr) & np.isfinite(mva)
        row["reproducibility_players"] = int(q.sum())
        if q.sum() >= MIN_REPRO_PLAYERS:
            rho = float(en.masked_spearman(mtr[:, None], mva[:, None], q[:, None])[0])
            mask_b = q[:, None] & (ntr_b > 0) & (nva_b > 0)
            rb = en.masked_spearman(mtr_b, mva_b, mask_b)
            rb = rb[np.isfinite(rb)]
            row.update(
                {
                    "reproducibility_spearman": rho,
                    "reproducibility_lo": float(np.percentile(rb, 2.5)) if rb.size else None,
                    "reproducibility_hi": float(np.percentile(rb, 97.5)) if rb.size else None,
                    "reproducibility_status": "ESTIMABLE",
                }
            )
        else:
            row["reproducibility_status"] = "REPRODUCIBILITY_NOT_ESTIMABLE"
        rows.append(row)
    return {"candidates": rows, "k": k, "window_ratio": wr, "validation_ratio": rr,
            "decision": decide(rows, tp, wr)}  # fmt: skip


def decide(rows: list[dict[str, Any]], tp: pd.DataFrame, wr: float) -> dict[str, Any]:
    """Apply the pre-declared threshold rule to evaluated candidates."""

    def b_ok(r: dict[str, Any], gate: float) -> bool:
        return r.get("marginal_data_weight") is not None and r["marginal_data_weight"] >= gate

    def sig_neg(r: dict[str, Any]) -> bool:
        return r.get("reproducibility_status") == "ESTIMABLE" and (
            r.get("reproducibility_hi") is not None and r["reproducibility_hi"] < 0
        )

    def sig_pos(r: dict[str, Any]) -> bool:
        return r.get("reproducibility_status") == "ESTIMABLE" and (
            r.get("reproducibility_lo") is not None and r["reproducibility_lo"] > 0
        )

    passing = [r for r in rows if b_ok(r, GATE_B) and not sig_neg(r)]
    work = [r for r in rows if "P50" in r["source"]]
    working_t = work[0]["threshold_balls"] if work else None
    dec: dict[str, Any] = {
        "gate_marginal_data_weight": GATE_B,
        "working_pool_threshold_balls": working_t,
        "window_ratio_W": wr,
        "alt_gate_smallest_threshold": {
            str(g): next((r["threshold_balls"] for r in rows if b_ok(r, g)), None)
            for g in ALT_GATES
        },
    }
    if passing:
        t = passing[0]["threshold_balls"]
        dec.update({"status": "THRESHOLD_SELECTED_PROVISIONAL", "threshold_balls": t,
                    "label": LABEL_SELECTED, "fallback_threshold_balls": None})  # fmt: skip
        return dec
    floor = ALT_GATES[-1]
    fb = [r for r in rows if r["eligible_players"] >= 5 and b_ok(r, floor) and sig_pos(r)]
    dec["status"] = "THRESHOLD_NOT_VALIDATED"
    dec["threshold_balls"] = None
    if fb:
        dec["fallback_threshold_balls"] = fb[0]["threshold_balls"]
        dec["label"] = LABEL_FALLBACK
    else:
        dec["fallback_threshold_balls"] = None
        dec["label"] = LABEL_WORKING if working_t is not None else LABEL_NO
    return dec


def analysis_rule(decision: dict[str, Any]) -> dict[str, Any]:
    """Threshold and label used for downstream experiments on one cell (never 'validated')."""
    if decision.get("threshold_balls") is not None:
        return {"threshold_balls": decision["threshold_balls"], "label": LABEL_SELECTED}
    if decision.get("fallback_threshold_balls") is not None:
        return {"threshold_balls": decision["fallback_threshold_balls"], "label": LABEL_FALLBACK}
    if decision.get("working_pool_threshold_balls") is not None:
        return {"threshold_balls": decision["working_pool_threshold_balls"], "label": LABEL_WORKING}
    return {"threshold_balls": None, "label": LABEL_NO}


def eligible_mask(est: pd.DataFrame, rule: dict[str, Any], wr: float) -> np.ndarray:
    """PRE_TEST eligibility under an analysis rule; empty when no threshold exists."""
    t = rule["threshold_balls"]
    if t is None:
        return np.zeros(len(est), dtype=bool)
    return (est["n"].to_numpy() >= t * wr) & np.isfinite(est["shrunk"].to_numpy())
