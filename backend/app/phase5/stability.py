"""Phase 5 ranking stability: seeded match-cluster bootstrap of the Top 10 in each context.

EXPERIMENTAL_NOT_VALIDATED and descriptive. Contexts are (format x role) cells for each of the four
definitions, the format-combined pool (players eligible in both formats), and the 12 phase x
situation atomic contexts of the primary definition. No ranking is padded: a context with fewer
than ``min_pool_for_stability`` eligible players reports ``POOL_TOO_SMALL`` and no statistics.
Context eligibility is the context's own working pool (the P50 candidate of that context's TRAIN
ball counts), not a number borrowed from another context, and it is not validated.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4.constants import SCOPE
from app.phase5.pipeline import ELIG_RULES, Study
from app.phase5.sensitivity import compare

LABEL = "EXPERIMENTAL_NOT_VALIDATED_DESCRIPTIVE"
MIN_TRAIN_PLAYERS_FOR_FIT = 8  # provisional; same number as the design document's fit floor


def paired_overlap(score_draws: np.ndarray, present: np.ndarray, k: int = en.TOP_K) -> np.ndarray:
    """Top-k overlap between independent bootstrap draws j and j + B/2 (different resamples)."""
    ranks = en.col_ranks(score_draws, present)
    incl = ranks <= k
    h = incl.shape[1] // 2
    if h == 0:
        return np.array([])
    return (incl[:, :h] & incl[:, h : 2 * h]).sum(0).astype(float)


def cell_stability(
    cell: en.Cell,
    rule: dict[str, Any],
    config: str,
    gm: pd.Index,
    W: np.ndarray,
    fit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bootstrap ranking distribution of one cell under an eligibility rule (never padded)."""
    fit = fit or cell.fit()
    sign = en.PRIMARY[cell.role][1]
    est = en.point_estimates(cell, fit, config)
    pool = el.eligible_mask(est, rule, rule["wr"])
    base: dict[str, Any] = {"pool_size": int(pool.sum()), "eligibility_label": rule["label"],
                            "threshold_balls": rule["threshold_balls"]}  # fmt: skip
    if pool.sum() == 0:
        return {
            "summary": {**base, "status": "POOL_EMPTY"},
            "players": pd.DataFrame(),
            "pool": pool,
            "est": est,
        }
    w = en.cell_weights(cell, gm, W)
    nb, dr = en.draws(cell, est, w)
    thr_b = (rule["threshold_balls"] or 0) * rule["wr"]
    present = pool[:, None] & (nb >= thr_b) & np.isfinite(dr)
    sd = np.where(present, sign * dr, np.nan)
    rs = en.rank_summary(sd, sign * est["shrunk"].to_numpy(), pool)
    sm = en.summarize_ranking(rs)
    tab = en.player_ranking_table(cell, est, rs, sign, pool)
    po = paired_overlap(sd, present & np.isfinite(sd))
    top = tab[tab["point_rank"] <= en.TOP_K]
    base.update(
        {
            "status": "ESTIMATED", "top10_size": sm["top10_size"],
            "trivial_full_pool": sm["trivial_full_pool"],
            "expected_overlap_with_point_top10": sm["expected_top10_overlap"],
            "expected_overlap_two_independent_bootstrap_top10": float(po.mean()) if po.size else None,
            "mean_jaccard": sm["mean_jaccard"], "mean_spearman_vs_point": sm["mean_spearman"],
            "spearman_p2_5": sm["spearman_p2_5"], "spearman_p97_5": sm["spearman_p97_5"],
            "point_top10_with_inclusion_ge_0_5": int((top["top10_inclusion_prob"] >= 0.5).sum()),
            "point_top10_with_inclusion_lt_0_5": int((top["top10_inclusion_prob"] < 0.5).sum()),
            "players_with_inclusion_between_0_2_and_0_8": int(
                ((tab["top10_inclusion_prob"] > 0.2) & (tab["top10_inclusion_prob"] < 0.8)).sum()),
            "median_rank_interval_width_point_top10": float((top["rank_hi"] - top["rank_lo"]).median()) if len(top) else None,
            "median_rank_interval_width_pool": float((tab["rank_hi"] - tab["rank_lo"]).median()),
            "label": LABEL,
        }
    )  # fmt: skip
    return {"summary": base, "players": tab, "pool": pool, "est": est}


# ---------------------------------------------------------------- definition cells
def definition_stability(study: Study, defns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = study.frozen["shrinkage"]["config"]
    summ, players = [], []
    for defn in defns:
        cells = study.primary_cells(defn)
        rules = study.frozen_rules(cells)
        for (comp, role), cell in cells.items():
            r = cell_stability(cell, rules[(comp, role)], config, study.gm, study.W)
            head = {
                "definition": defn,
                "is_primary_definition": defn == defns[0],
                "format": comp,
                "role": role,
            }
            summ.append({**head, **r["summary"]})
            if len(r["players"]):
                players.append(
                    pd.DataFrame(
                        {
                            **{k: v for k, v in head.items()},
                            **{c: r["players"][c] for c in r["players"]},
                        }
                    )
                )
    return pd.DataFrame(summ), (
        pd.concat(players, ignore_index=True) if players else pd.DataFrame()
    )


def combined_stability(
    study: Study, fw: dict[str, pd.DataFrame], default_id: str = "w70_30"
) -> pd.DataFrame:
    """Format-combined Top-10 bootstrap rows (from the Phase 4 format-weight analysis)."""
    cf = fw["configs"]
    cf = cf[cf["config_id"] == default_id]
    rows = []
    for _, r in cf.iterrows():
        rows.append(
            {
                "definition": study.cfg["definitions"]["primary"], "format": "COMBINED_w70_30",
                "role": r["role"], "pool_size": int(r["pool_size"]), "status": "ESTIMATED" if r["pool_size"] >= 5 else "POOL_TOO_SMALL",
                "expected_overlap_with_point_top10": r.get("bootstrap_expected_top10_overlap"),
                "mean_jaccard": r.get("bootstrap_mean_jaccard"),
                "mean_spearman_vs_point": r.get("bootstrap_mean_spearman"),
                "trivial_full_pool": bool(r.get("top10_trivial_full_pool", False)), "label": LABEL,
            }
        )  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- phase x situation contexts
def context_rows(study: Study, defn: str, role: str, stream: str) -> pd.DataFrame:
    """Pressure rows of the definition with phase and situation labels from the state frame."""
    rows = study.pressure_rows(defn, role, stream).copy()
    src = rows["src"].to_numpy()
    rows["phase"] = study.d["innings_phase"].reindex(src).to_numpy()
    rows["situation"] = np.where(
        study.d["innings_number"].reindex(src).to_numpy() == 2, "chase", "first_innings"
    )
    return rows


def context_rule(cell: en.Cell, ladder: list[int]) -> dict[str, Any]:
    """Working-pool rule of one context: the P50 candidate of its own TRAIN ball counts."""
    tp = cell.train_pt()
    cands = el.candidate_thresholds(tp["n"].to_numpy(), ladder)
    p50 = [c["threshold"] for c in cands if "P50" in c["source"]]
    wr = el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
    return {"threshold_balls": p50[0] if p50 and np.isfinite(wr) else None,
            "label": el.LABEL_WORKING if p50 and np.isfinite(wr) else el.LABEL_NO,
            "wr": wr if np.isfinite(wr) else 1.0}  # fmt: skip


def atomic_contexts(study: Study) -> dict[str, Any]:
    """Stability and cross-context Spearman for the phase x situation contexts of the primary."""
    import json

    sc = study.cfg["stability"]
    defn = study.cfg["definitions"]["primary"]
    config = study.frozen["shrinkage"]["config"]
    ladders = json.loads(ELIG_RULES.read_text(encoding="utf-8"))["ladders"]
    phases = ["ALL", *sc["phases"]]
    sits = ["ALL", *sc["situations"]]
    summ, scores = [], {}
    for role in ("batter", "bowler"):
        stream = en.PRIMARY[role][0]
        rows = context_rows(study, defn, role, stream)
        for comp in SCOPE:
            for ph in phases:
                for si in sits:
                    r = rows
                    if ph != "ALL":
                        r = r[r["phase"] == ph]
                    if si != "ALL":
                        r = r[r["situation"] == si]
                    name = f"{ph}|{si}"
                    head = {
                        "definition": defn,
                        "format": comp,
                        "role": role,
                        "phase": ph,
                        "situation": si,
                    }
                    cell = en.build_cell(r, comp, role, stream)
                    if cell is None:
                        summ.append({**head, "status": "NO_PRESSURE_ROWS", "pool_size": 0})
                        continue
                    fit = cell.fit()
                    tr_players = int(fit["players"])
                    head.update({"players_with_balls": int(len(cell.players)), "train_players": tr_players,
                                 "pressure_balls_pre_test": int(cell.N.sum())})  # fmt: skip
                    if tr_players < MIN_TRAIN_PLAYERS_FOR_FIT or not np.isfinite(fit["sigma2"]):
                        summ.append({**head, "status": "CONTEXT_NOT_ESTIMABLE", "pool_size": 0})
                        continue
                    rule = context_rule(cell, ladders[role]["balls"])
                    st = cell_stability(cell, rule, config, study.gm, study.W, fit)
                    s = st["summary"]
                    s["fit_floor_hit"] = bool(st["est"]["floor_hit"].iloc[0])
                    if s["pool_size"] < sc["min_pool_for_stability"]:
                        s = {
                            k: v
                            for k, v in s.items()
                            if k
                            in (
                                "pool_size",
                                "eligibility_label",
                                "threshold_balls",
                                "fit_floor_hit",
                            )
                        }
                        s["status"] = "POOL_TOO_SMALL"
                    summ.append({**head, **s})
                    sign = en.PRIMARY[role][1]
                    mask = st["pool"]
                    scores[(comp, role, name)] = pd.Series(
                        sign * st["est"]["shrunk"].to_numpy(), index=cell.players
                    )[mask]
    cross = []
    keys = sorted(scores)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if a[:2] != b[:2]:
                continue
            c = compare(scores[a], scores[b])
            ok = c["common_players"] >= sc["min_common_for_cross_context_spearman"]
            cross.append({"format": a[0], "role": a[1], "context_a": a[2], "context_b": b[2],
                          "status": "ESTIMATED" if ok else "NOT_ESTIMABLE_TOO_FEW_COMMON_PLAYERS",
                          "common_players": c["common_players"], "pool_a": c["pool_ref"], "pool_b": c["pool_alt"],
                          "spearman": c["spearman"] if ok else None,
                          "top10_overlap_share": c["top_k_overlap_share"] if ok else None})  # fmt: skip
    return {"summary": pd.DataFrame(summ), "cross": pd.DataFrame(cross)}
