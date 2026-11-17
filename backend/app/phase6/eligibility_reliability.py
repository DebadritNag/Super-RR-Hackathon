"""Eligibility thresholds under the reliability lens (EXPERIMENTAL_NOT_VALIDATED, descriptive).

For each format x role cell of the provisional definition, individuals are pooled by a minimum
number of pressure balls ``t`` (the Phase 5 ladders, the frozen thresholds and the Phase 4
candidate thresholds) and the odd/even split-half reliability of each pool is computed with
bootstrap intervals. The smallest ``t`` at which the reliability reaches 0.5, 0.7 or 0.8 is read
off the ladder. Required sample sizes come from variance estimates with their intervals
(descriptive projections). Thresholds and the 0.5 data-weight gate are only read, never changed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6 import split_half as sp
from app.phase6.constants import IN_SAMPLE_LABEL

GATE = el.GATE_B  # read, never assigned or changed here
REACHED = "TARGET_REACHED"
NOT_REACHED = "TARGET_NOT_REACHED_WITHIN_LADDER"


def kish_n_eff(N: np.ndarray) -> np.ndarray:
    """Per-player Kish effective count over per-match ball counts: n^2 / sum n_m^2."""
    n = N.sum(1)
    n2 = (N**2).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n2 > 0, n**2 / np.where(n2 > 0, n2, 1.0), 0.0)


def pool_unit(
    cd: rb.CellData,
    w: np.ndarray,
    mask: np.ndarray,
    t: float,
    k: float,
    spec: dict[str, Any],
    seed: int,
    n_boot: int,
) -> dict[str, Any]:
    """Odd/even reliability, interval and data weight of the pool with at least ``t`` balls."""
    min_half, min_pl = int(spec["min_balls_per_half"]), int(spec["min_individuals_estimable"])
    sub = cd.select_cols(mask)
    tot = sub.N.sum(1)
    keep = tot >= t
    row: dict[str, Any] = {"min_total_balls": float(t), "players_ge_t": int(keep.sum()),
                           "k": float(k), "gate": GATE, "label": IN_SAMPLE_LABEL}  # fmt: skip
    if keep.sum():
        ne = kish_n_eff(sub.N[keep])
        row.update(marginal_n_eff=float(ne.min()), median_n_eff=float(np.median(ne)),
                   median_matches=float(np.median((sub.N[keep] > 0).sum(1))),
                   share_n_eff_at_least_k=float((ne >= k).mean()),
                   n_pool_n_eff_at_least_k=int((ne >= k).sum()))  # fmt: skip
        row["b_marginal"] = float(ne.min() / (ne.min() + k)) if k > 0 else 1.0
        row["b_median"] = float(np.median(ne) / (np.median(ne) + k)) if k > 0 else 1.0
    if keep.sum() < min_pl:
        return {**row, "status": NOT_ESTIMABLE}
    r, ci = sp.split_half_unit(cd.select_players(keep), w, mask, "odd_even", min_half, seed, 1,
                               n_boot, min_pl)  # fmt: skip
    row.update(status=r["status"], players_estimable=r["players"], r=r.get("r_pearson"),
               sb=r.get("sb_pearson"))  # fmt: skip
    for c in ci:
        m = "players" if c["ci_method"].startswith("player") else "matches"
        row[f"sb_lo_{m}"], row[f"sb_hi_{m}"] = c["lo"], c["hi"]
    return row


def target_table(ladder_rows: pd.DataFrame, targets: list[float]) -> pd.DataFrame:
    """Smallest ladder step whose reliability (point, then player- and match-interval lower
    bound) reaches each target, per cell and window."""
    out = []
    keys = ["format", "role", "window"]
    for key, g in ladder_rows[ladder_rows["source"] == "ladder"].groupby(keys):
        g = g.sort_values("min_total_balls")
        est = g[g["status"] == ESTIMATED]
        for tgt in targets:
            rec: dict[str, Any] = dict(zip(keys, key, strict=True))
            rec["target"] = tgt
            rec["label"] = "DESCRIPTIVE_IN_SAMPLE"
            if est.empty:
                rec.update(status=NOT_ESTIMABLE)
                out.append(rec)
                continue
            for name, col in (("point", "sb"), ("lo_players", "sb_lo_players"),
                              ("lo_matches", "sb_lo_matches")):  # fmt: skip
                hit = est[est[col] >= tgt]
                rec[f"min_balls_{name}"] = float(hit["min_total_balls"].min()) if len(hit) else None
            rec["status"] = REACHED if rec["min_balls_point"] is not None else NOT_REACHED
            rec["ladder_max_estimable"] = float(est["min_total_balls"].max())
            out.append(rec)
    return pd.DataFrame(out)


def projection_rows(
    cd: rb.CellData, w: np.ndarray, mask: np.ndarray, targets: list[float], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """Required pressure balls per individual for each target: ``R/(1-R) * sigma_eff / tau2``.

    Two variance sources: the model-free split-half covariance (E7) and the ball-independent
    moment estimate (E1b). Intervals use the bootstrap bounds of ``tau2`` (the lower bound gives
    the upper bound of the requirement; a non-positive lower bound gives no upper bound).
    """
    window = "PRE_TEST"
    rows: list[dict[str, Any]] = []
    srcs = []
    e7 = rb.split_cov_rows(cd, w, window, [12])
    if e7:
        srcs.append(("E7_split_half_covariance", e7[0]))
    vr = [r for r in rb.variance_rows(cd, w, window, [1]) if r["noise_basis"] == "ball_independent"]
    if vr:
        srcs.append(("E1b_ball_independent", vr[0]))
    for name, r in srcs:
        tau2, sig = r.get("tau2_moment"), r.get("sigma_eff_for_projection")
        lo, hi = r.get("tau2_boot_lo"), r.get("tau2_boot_hi")
        for tgt in targets:
            base = {**meta, "source": name, "target": tgt, "label": "DESCRIPTIVE_PROJECTION",
                    "tau2": tau2, "tau2_lo": lo, "tau2_hi": hi, "sigma_eff": sig,
                    "tau2_status": r.get("status")}  # fmt: skip
            req = rb.required_sample(tau2, sig, (tgt,), "balls")[0]["required_n"]
            base["required_balls"] = req if not isinstance(req, str) else None
            base["status"] = ESTIMATED if not isinstance(req, str) else NOT_ESTIMABLE
            if base["status"] == ESTIMATED and hi is not None and hi > 0:
                base["required_balls_lo"] = float(tgt / (1 - tgt) * sig / hi)
            if base["status"] == ESTIMATED and lo is not None and lo > 0:
                base["required_balls_hi"] = float(tgt / (1 - tgt) * sig / lo)
            elif base["status"] == ESTIMATED:
                base["required_balls_hi"] = None
                base["note"] = "tau2 lower bound not above 0: no upper bound on the requirement"
            rows.append(base)
    return rows


def balls_at_n_eff(cd: rb.CellData, mask: np.ndarray, k: float) -> dict[str, Any]:
    """Measured: individuals whose Kish count reaches ``k`` (B = 0.5) and their ball counts."""
    sub = cd.select_cols(mask)
    ne = kish_n_eff(sub.N)
    tot = sub.N.sum(1)
    hit = ne >= k
    return {"players_total": int((tot > 0).sum()), "players_n_eff_at_least_k": int(hit.sum()),
            "min_balls_among_them": float(tot[hit].min()) if hit.any() else None,
            "median_balls_among_them": float(np.median(tot[hit])) if hit.any() else None,
            "max_n_eff": float(ne.max()) if len(ne) else None,
            "label": "MEASURED_DESCRIPTIVE"}  # fmt: skip
