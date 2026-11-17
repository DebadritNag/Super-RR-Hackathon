"""Context-specific fits, eligibility rules and score tables (analytics layer, computed once).

For each atomic context (competition x role x phase x situation = 48 cells) this module:

1. builds the context cell from the stored rows (``context_stats``);
2. estimates the between-player variance ``tau2`` and the shrinkage strength ``k`` with the Phase 4
   estimator (``shrink.fit_cell``) on TRAIN rows of that context only. VALIDATION rows never enter
   a fitted parameter; they only receive scores;
3. derives the context's own ball threshold with the Phase 4 method (percentile candidates of the
   context's TRAIN ball counts, ``evaluate_cell``, ``decide``, ``analysis_rule``), never borrowing
   the overall cell's numbers;
4. stores per-player raw, expected, residual and shrunk values with sample sizes and eligibility.

A context with too few TRAIN players is ``CONTEXT_NOT_ESTIMABLE`` (the parent cell's variance is
never borrowed). ``fit_cell`` is called once per atomic context here and never from the request
path: requests only aggregate and rank the stored results. All thresholds are working values and
are NOT validated (the multiple-derivation caveat applies: 48 separate derivations).
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase5 import context_stats as cs

CONTEXT_ELIGIBLE = "ELIGIBLE_WORKING_POOL_NOT_VALIDATED"
NOT_ESTIMABLE = "CONTEXT_NOT_ESTIMABLE"
NO_THRESHOLD = "NO_ELIGIBILITY_THRESHOLD_FOR_CONTEXT"
INSUFFICIENT = "INSUFFICIENT_SAMPLE_FOR_CONTEXT"
KEY_COLS = ["comp", "role", "phase", "situation"]


def atomic_contexts(cfg: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    comps = [f for f in cfg["formats"] if f in ("IPL", "T20I")]
    return [
        (c, r, p, s)
        for c in comps
        for r in cfg["roles"]
        for p in cfg["phases"]
        for s in cfg["situations"]
    ]


def build_context(
    stats: pd.DataFrame,
    key: tuple[str, str, str, str],
    cfg: dict[str, Any],
    ladders: dict[str, Any],
    shrink_config: str,
    gm: pd.Index,
    W: np.ndarray,
) -> dict[str, Any]:
    """Fit, eligibility rule and per-player scores of one atomic context."""
    comp, role, phase, situation = key
    stream, sign = en.PRIMARY[role]
    head = {"comp": comp, "role": role, "phase": phase, "situation": situation}
    sub = cs.select(stats, comp, role, phase, situation)
    cell = cs.cell_from_stats(sub, comp, role, stream)
    rule_row: dict[str, Any] = {**head, "players_with_balls": 0, "train_players": 0,
                                "pressure_balls_pre_test": 0}  # fmt: skip
    fit_row: dict[str, Any] = {**head, "train_players": 0}
    if cell is None:
        rule_row["context_status"] = NOT_ESTIMABLE
        rule_row["reason"] = "NO_PRESSURE_ROWS"
        return {"rule": rule_row, "fit": fit_row, "scores": pd.DataFrame()}
    fit = cell.fit()
    train_players = int(fit["players"])
    rule_row.update(
        players_with_balls=int(len(cell.players)),
        train_players=train_players,
        pressure_balls_pre_test=int(cell.N.sum()),
    )
    fit_row["train_players"] = train_players
    wr = el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
    if (
        train_players < int(cfg["min_train_players_for_fit"])
        or not np.isfinite(fit["sigma2"])
        or not np.isfinite(wr)
        or wr <= 0
    ):
        rule_row["context_status"] = NOT_ESTIMABLE
        rule_row["reason"] = "TOO_FEW_TRAIN_PLAYERS_OR_NO_VARIANCE"
        fit_row.update(sigma2=_f(fit["sigma2"]), between=_f(fit["between"]))
        return {"rule": rule_row, "fit": fit_row, "scores": pd.DataFrame()}
    kinfo = sh.k_for(fit, shrink_config)
    est = en.point_estimates(cell, fit, shrink_config)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ev = el.evaluate_cell(cell, fit, shrink_config, gm, W, ladders[role]["balls"], sign)
    decision = ev["decision"]
    rule = el.analysis_rule(decision)
    elig = el.eligible_mask(est, rule, wr)
    fit_row.update(
        sigma2=_f(fit["sigma2"]),
        between=_f(fit["between"]),
        tau2=_f(kinfo["tau2"]),
        k=_f(kinfo["k"]),
        floor_hit=bool(kinfo["floor_hit"]),
        shrink_config=shrink_config,
        train_balls=_f(fit["total_n"]),
        train_sum_residual=_f(fit["total_s"]),
    )
    ctx_status = CONTEXT_ELIGIBLE if rule["threshold_balls"] is not None else NO_THRESHOLD
    marginal_b = None
    if elig.any():
        ne_min = float(est["n_eff"].to_numpy()[elig].min())
        marginal_b = ne_min / (ne_min + kinfo["k"]) if kinfo["k"] > 0 else 1.0
    thr = rule["threshold_balls"]
    rule_row.update(
        context_status=ctx_status,
        decision_status=decision["status"],
        threshold_balls=thr,
        label=rule["label"],
        window_ratio=_f(wr),
        scaled_threshold=_f(thr * wr) if thr is not None else None,
        working_pool_threshold_balls=decision.get("working_pool_threshold_balls"),
        k=_f(kinfo["k"]),
        tau2=_f(kinfo["tau2"]),
        floor_hit=bool(kinfo["floor_hit"]),
        eligible_players=int(elig.sum()),
        matches_in_context=int(len(cell.matches)),
        median_data_weight_eligible=_f(np.median(est["B"].to_numpy()[elig])) if elig.any() else None,
        marginal_n_eff_eligible=_f(est["n_eff"].to_numpy()[elig].min()) if elig.any() else None,
        marginal_data_weight=_f(marginal_b) if marginal_b is not None else None,
        data_weight_gate_passed=bool(marginal_b is not None and marginal_b >= el.GATE_B),
        n_candidates=len(ev["candidates"]),
        reason=None,
    )  # fmt: skip
    ex = cs.expected_sums(sub).reindex(cell.players)
    n = est["n"].to_numpy()
    mean_exp = ex["e"].to_numpy() / n
    mean_resid = est["mean"].to_numpy()
    status = np.where(elig, CONTEXT_ELIGIBLE if thr is not None else NO_THRESHOLD, INSUFFICIENT)
    if thr is None:
        status = np.full(len(n), NO_THRESHOLD, dtype=object)
    scores = pd.DataFrame(
        {
            **head,
            "player_id": cell.players,
            "n": n,
            "matches": est["matches"].to_numpy(),
            "n_eff": est["n_eff"].to_numpy(),
            "mean_expected": mean_exp,
            "mean_residual": mean_resid,
            "mean_raw": mean_exp + mean_resid,
            "target": est["target"].to_numpy(),
            "shrink_weight": est["B"].to_numpy(),
            "k": est["k"].to_numpy(),
            "tau2": est["tau2"].to_numpy(),
            "floor_hit": est["floor_hit"].to_numpy(),
            "shrunk": est["shrunk"].to_numpy(),
            "score": sign * est["shrunk"].to_numpy(),
            "eligible": elig,
            "eligibility_status": status,
            "threshold_balls": thr,
            "scaled_threshold": thr * wr if thr is not None else np.nan,
            "label": rule["label"],
        }
    )
    return {"rule": rule_row, "fit": fit_row, "scores": scores}


def build_artifacts(
    stats: pd.DataFrame,
    cfg: dict[str, Any],
    ladders: dict[str, Any],
    shrink_config: str,
) -> dict[str, pd.DataFrame]:
    """All 48 atomic contexts: rules, fits and scores (pure; no database access)."""
    cs.check_stats(stats)
    gm, W = cs.global_match_weights(stats, int(cfg["n_boot"]), int(cfg["seed"]))
    rules, fits, scores = [], [], []
    for key in atomic_contexts(cfg):
        out = build_context(stats, key, cfg, ladders, shrink_config, gm, W)
        rules.append(out["rule"])
        fits.append(out["fit"])
        if len(out["scores"]):
            scores.append(out["scores"])
    return {
        "rules": pd.DataFrame(rules),
        "fit": pd.DataFrame(fits),
        "scores": pd.concat(scores, ignore_index=True) if scores else pd.DataFrame(),
    }


def _f(v: Any) -> float | None:
    if v is None:
        return None
    x = float(v)
    return x if np.isfinite(x) else None
