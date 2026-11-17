"""Context-specific reliability and data weight of the 48 atomic contexts (EXPERIMENTAL_NOT_VALIDATED).

A context is format x role x phase {ALL, powerplay, middle, death} x situation {ALL, chase,
first_innings} of the provisional definition's pressure rows, read from the stored
``p5_context_stats`` (TRAIN and VALIDATION only). Per context this module computes split-half
reliability (odd/even and repeated random splits, with player and match bootstrap intervals), the
model-free signal share, and recomputes the Phase 5 data weight of the marginal eligible player
from the stored eligibility threshold. The recomputed weight must equal the stored one; the
pass/fail against the 0.5 gate is read from ``app.phase4.eligibility.GATE_B`` and compared with
the stored Phase 5 state. This module never sets a gate state; contexts that fail stay restricted.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase5 import context_stats as cs
from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6 import split_half as sp
from app.phase6 import variance_floor as vf
from app.phase6.constants import IN_SAMPLE_LABEL
from app.phase6.lockguard import assert_no_test_rows

GATE = el.GATE_B  # read, never assigned or changed here
TOL = 1e-9
SHRINK_CONFIG = "shrink_tau4"


def signal_share(cd: rb.CellData, mask: np.ndarray, min_half: int) -> dict[str, Any]:
    """cov(half1, half2) / var(individual means) over individuals estimable for the odd/even split."""
    sub = cd.select_cols(mask)
    if sub.N.shape[0] == 0 or sub.N.shape[1] < 2:
        return {"players": 0, "share": None}
    A, B = rb.half_masks(sub.N > 0, "odd_even")
    h = rb.half_stats(sub.N, sub.S, A, B, np.ones((sub.N.shape[1], 1)), min_half)
    ok = h["ok"][:, 0]
    n_ok = int(ok.sum())
    if n_ok < 3:
        return {"players": n_ok, "share": None}
    n_tot, s_tot = sub.N.sum(1)[ok], sub.S.sum(1)[ok]
    var_m = float(np.var(s_tot / n_tot, ddof=1))
    cov = float(h["cov"][0])
    return {"players": n_ok, "share": cov / var_m if var_m > 0 and np.isfinite(cov) else None}


def eligibility_recompute(
    cell: Any, rule: dict[str, Any], shrink_config: str = SHRINK_CONFIG
) -> dict[str, Any]:
    """Phase 5 eligibility and marginal data weight of a context from its stored threshold."""
    fit = cell.fit()
    kinfo = sh.k_for(fit, shrink_config)
    est = en.point_estimates(cell, fit, shrink_config)
    wr = el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
    thr = rule.get("threshold_balls")
    thr = None if thr is None or pd.isna(thr) else float(thr)
    elig = (
        el.eligible_mask(est, {"threshold_balls": thr}, wr)
        if np.isfinite(wr)
        else np.zeros(len(est), dtype=bool)
    )
    out: dict[str, Any] = {"fit": fit, "kinfo": kinfo, "est": est, "elig": elig, "wr": wr,
                           "threshold_balls": thr, "eligible_players": int(elig.sum())}  # fmt: skip
    if elig.any():
        ne = est["n_eff"].to_numpy()[elig]
        k = float(kinfo["k"])
        out.update(
            marginal_n_eff=float(ne.min()),
            marginal_b=float(ne.min() / (ne.min() + k)) if k > 0 else 1.0,
            median_n_eff=float(np.median(ne)),
            p90_n_eff=float(np.percentile(ne, 90)),
            max_n_eff=float(ne.max()),
        )
    return out


def context_row(
    stats: pd.DataFrame,
    key: tuple[str, str, str, str],
    rule_row: pd.Series,
    gm: pd.Index,
    W: np.ndarray,
    spec: dict[str, Any],
    seed: int,
    n_boot: int,
) -> dict[str, Any]:
    """All reliability and data-weight columns of one atomic context (no player identity)."""
    comp, role, phase, situation = key
    row: dict[str, Any] = {"format": comp, "role": role, "phase": phase, "situation": situation,
                           "stream": en.PRIMARY[role][0], "window": "PRE_TEST",
                           "label": IN_SAMPLE_LABEL,
                           "stored_context_status": rule_row.get("context_status")}  # fmt: skip
    sub = cs.select(stats, comp, role, phase, situation)
    cd, cell = vf.cd_from_context(sub)
    if cd is None:
        return {**row, "status": NOT_ESTIMABLE, "reason": "NO_PRESSURE_ROWS"}
    assert_no_test_rows(sub)
    w = en.cell_weights(cell, gm, W)
    mask = sp.window_mask(cd, "PRE_TEST")
    min_half, min_pl = int(spec["min_balls_per_half"]), int(spec["min_individuals_estimable"])
    row.update(matches=int(cd.N.shape[1]), players_with_balls=int((cd.total_balls > 0).sum()),
               pressure_balls=int(cd.N.sum()))  # fmt: skip
    for mode in ("odd_even", "random"):
        unit_seed = sp.unit_seed(seed, "context", comp, role, phase, situation, mode)
        r, ci = sp.split_half_unit(cd, w, mask, mode, min_half, unit_seed,
                                   int(spec["random_splits"]), n_boot, min_pl)  # fmt: skip
        tag = "oe" if mode == "odd_even" else "rnd"
        row.update({f"{tag}_status": r["status"], f"{tag}_players": r["players"],
                    f"{tag}_r": r.get("r_pearson"), f"{tag}_sb": r.get("sb_pearson")})  # fmt: skip
        for c in ci:
            meth = c["ci_method"]
            m = ("players" if meth.startswith("player") else
                 "matches" if meth.startswith("match") else "repeats")  # fmt: skip
            row[f"{tag}_sb_lo_{m}"], row[f"{tag}_sb_hi_{m}"] = c["lo"], c["hi"]
    ss = signal_share(cd, mask, min_half)
    row["signal_share_m2"] = ss["share"]
    rec = eligibility_recompute(cell, rule_row)
    row.update(threshold_balls=rec["threshold_balls"], window_ratio=_f(rec["wr"]),
               eligible_players=rec["eligible_players"], k=_f(rec["kinfo"]["k"]),
               floor_hit=bool(rec["kinfo"]["floor_hit"]), gate=GATE)  # fmt: skip
    for c in ("marginal_n_eff", "marginal_b", "median_n_eff", "p90_n_eff", "max_n_eff"):
        row[c] = _f(rec.get(c))
    k = rec["kinfo"]["k"]
    row["n_eff_required_for_gate"] = float(GATE / (1.0 - GATE) * k) if k > 0 else 0.0
    row["marginal_gap_n_eff"] = (
        max(0.0, row["n_eff_required_for_gate"] - rec["marginal_n_eff"])
        if "marginal_n_eff" in rec else None
    )  # fmt: skip
    row["gate_passed_recomputed"] = bool(
        rec.get("marginal_b") is not None and rec["marginal_b"] >= GATE
    )
    row["status"] = ESTIMATED if row.get("oe_status") == ESTIMATED else NOT_ESTIMABLE
    stored_b = rule_row.get("marginal_data_weight")
    row["stored_marginal_b"] = _f(stored_b)
    row["stored_gate_passed"] = (
        None if pd.isna(rule_row.get("data_weight_gate_passed"))
        else bool(rule_row.get("data_weight_gate_passed"))
    )  # fmt: skip
    row["stored_eligible_players"] = (
        None if pd.isna(rule_row.get("eligible_players")) else int(rule_row["eligible_players"])
    )  # fmt: skip
    row["marginal_b_abs_diff_vs_stored"] = (
        abs(row["marginal_b"] - row["stored_marginal_b"])
        if row["marginal_b"] is not None and row["stored_marginal_b"] is not None
        else None
    )  # fmt: skip
    return row


def _f(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def regression_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Recomputed data weight and eligibility against the stored Phase 5 rules (all 48 contexts)."""
    both = df[df["marginal_b_abs_diff_vs_stored"].notna()]
    n_gate_diff = int(
        (df["gate_passed_recomputed"].astype(bool) != df["stored_gate_passed"].astype(bool)).sum()
    )
    n_elig_diff = int((df["eligible_players"] != df["stored_eligible_players"]).sum())
    worst = float(both["marginal_b_abs_diff_vs_stored"].max()) if len(both) else float("nan")
    return {"contexts": int(len(df)), "compared": int(len(both)), "max_abs_diff_b": worst,
            "gate_state_differences": n_gate_diff, "eligible_count_differences": n_elig_diff,
            "reproduces": bool(len(both) == len(df) and worst <= TOL and n_gate_diff == 0
                               and n_elig_diff == 0)}  # fmt: skip


def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Reliability by phase, by situation, by format and by role (all 48 contexts overlap)."""
    rows = []
    est = df[df["oe_status"] == ESTIMATED]
    for dim in ("phase", "situation", "format", "role"):
        for val, g in est.groupby(dim):
            rows.append(
                {
                    "dimension": dim, "value": val, "contexts_estimable": int(len(g)),
                    "contexts_total": int((df[dim] == val).sum()),
                    "oe_sb_median": float(g["oe_sb"].median()),
                    "oe_sb_min": float(g["oe_sb"].min()), "oe_sb_max": float(g["oe_sb"].max()),
                    "contexts_player_lo_above_0": int((g["oe_sb_lo_players"] > 0).sum()),
                    "contexts_match_lo_above_0": int((g["oe_sb_lo_matches"] > 0).sum()),
                    "median_individuals": float(g["oe_players"].median()),
                    "median_pressure_balls": float(g["pressure_balls"].median()),
                    "label": IN_SAMPLE_LABEL,
                }
            )  # fmt: skip
    return pd.DataFrame(rows)


def all_all_check(df: pd.DataFrame, split_half: pd.DataFrame, definition: str) -> pd.DataFrame:
    """ALL/ALL context against the primary format x role cell of the same definition (odd/even)."""
    rows = []
    sh_ = split_half[
        (split_half["definition"] == definition) & (split_half["window"] == "PRE_TEST")
        & (split_half["mode"] == "odd_even") & (split_half["is_primary_stream"])
    ]  # fmt: skip
    for _, r in df[(df["phase"] == cs.ALL) & (df["situation"] == cs.ALL)].iterrows():
        m = sh_[(sh_["format"] == r["format"]) & (sh_["role"] == r["role"])]
        if m.empty:
            rows.append({"format": r["format"], "role": r["role"], "found": False})
            continue
        m = m.iloc[0]
        rows.append({"format": r["format"], "role": r["role"], "found": True,
                     "context_players": r["oe_players"], "cell_players": int(m["players"]),
                     "context_sb": r["oe_sb"], "cell_sb": float(m["sb_pearson"]),
                     "abs_diff_sb": abs(r["oe_sb"] - float(m["sb_pearson"])),
                     "equal": bool(abs(r["oe_sb"] - float(m["sb_pearson"])) <= TOL
                                   and r["oe_players"] == int(m["players"]))})  # fmt: skip
    return pd.DataFrame(rows)
