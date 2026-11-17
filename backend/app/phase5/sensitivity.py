"""Phase 5 sensitivity grid. EXPERIMENTAL_NOT_VALIDATED; every comparison is against the PROVISIONAL
primary run (``any|q0.75``, ``shrink_tau4``, baseline B0, frozen working-pool ball thresholds).

Axes (one factor at a time unless stated): pressure definition (the nine full-eligibility
candidates, which include the primary and the three named alternatives, so thresholds of the
pressure quantile are covered), eligibility ball thresholds, shrinkage strength (7 configurations,
also crossed with the four named definitions), baseline alternatives, and the eight format
weights (primary definition only, same final eligibility rules, independent of the definition
axis). The date-restricted TEST sets are compared as set composition only; TEST outcomes are never
read. A high or low overlap here says how much a choice moves the ordering, not which choice is right.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import definitions as df_
from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import sensitivity as p4s
from app.phase4 import shrink as sh
from app.phase4.baseline import DEFAULT_PARAMS
from app.phase4.constants import SCOPE
from app.phase5.pipeline import ELIG_RULES, CellKey, Study

TOP_K = 10
W_IPL_DEFAULT = 0.7


# ---------------------------------------------------------------- comparison metrics
def topk_ids(scores: pd.Series, k: int = TOP_K) -> list[int]:
    """Top-k player ids by descending score; ties broken by player id (deterministic)."""
    if scores.empty:
        return []
    df = pd.DataFrame({"s": scores.to_numpy(float), "id": scores.index.to_numpy()})
    return (
        df.sort_values(["s", "id"], ascending=[False, True], kind="mergesort")["id"]
        .head(k)
        .tolist()
    )


def kendall_tau(a: np.ndarray, b: np.ndarray) -> float:
    """Kendall tau-b by pairwise sign agreement (O(n^2); pools here are a few hundred players)."""
    n = len(a)
    if n < 3:
        return float("nan")
    sa, sb = np.sign(a[:, None] - a[None, :]), np.sign(b[:, None] - b[None, :])
    iu = np.triu_indices(n, 1)
    x, y = sa[iu], sb[iu]
    conc = float((x * y).sum())
    den = float(np.sqrt((x != 0).sum() * (y != 0).sum()))
    return conc / den if den > 0 else float("nan")


def compare(ref: pd.Series, alt: pd.Series, k: int = TOP_K) -> dict[str, Any]:
    """Pool sizes, Top-k overlap, Spearman and Kendall on the players present in both."""
    common = ref.index.intersection(alt.index)
    kk = int(min(k, len(ref), len(alt)))
    out: dict[str, Any] = {
        "pool_ref": int(len(ref)), "pool_alt": int(len(alt)), "common_players": int(len(common)),
        "top_k": kk, "top_k_trivial_full_pool": bool(max(len(ref), len(alt)) <= k),
        "spearman": None, "kendall_tau": None, "top_k_overlap": None, "top_k_overlap_share": None,
    }  # fmt: skip
    if kk > 0:
        ov = len(set(topk_ids(ref, kk)) & set(topk_ids(alt, kk)))
        out["top_k_overlap"], out["top_k_overlap_share"] = ov, ov / kk
    if len(common) >= 3:
        a, b = ref[common].to_numpy(float), alt[common].to_numpy(float)
        ra, rb_ = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
        if ra.std() > 0 and rb_.std() > 0:
            out["spearman"] = float(np.corrcoef(ra, rb_)[0, 1])
        out["kendall_tau"] = kendall_tau(a, b)
    return out


def pool_scores(
    cell: en.Cell, rule: dict[str, Any], config: str, fit: dict[str, Any] | None = None
) -> tuple[pd.Series, pd.DataFrame, np.ndarray]:
    """Signed shrunk scores of the eligible pool (higher is better), the estimate frame and mask."""
    est = en.point_estimates(cell, fit or cell.fit(), config)
    mask = el.eligible_mask(est, rule, rule["wr"])
    sign = en.PRIMARY[cell.role][1]
    return pd.Series(sign * est["shrunk"].to_numpy(), index=cell.players)[mask], est, mask


def run_scores(
    cells: dict[CellKey, en.Cell], rules: dict[CellKey, dict[str, Any]], config: str
) -> dict[CellKey, dict[str, Any]]:
    return {
        key: dict(zip(("scores", "est", "mask"), pool_scores(c, rules[key], config), strict=True))
        for key, c in cells.items()
    }


def combined_scores(run: dict[CellKey, dict[str, Any]], role: str, w_ipl: float) -> pd.Series:
    """Combined score for players eligible in BOTH formats (never zero-filled)."""
    if ("IPL", role) not in run or ("T20I", role) not in run:
        return pd.Series(dtype=float)
    a, b = run[("IPL", role)]["scores"], run[("T20I", role)]["scores"]
    both = a.index.intersection(b.index)
    return w_ipl * a[both] + (1.0 - w_ipl) * b[both]


def _compare_runs(
    ref: dict[CellKey, dict[str, Any]], alt: dict[CellKey, dict[str, Any]], head: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for key, a in alt.items():
        comp, role = key
        r = ref.get(key)
        if r is None:
            continue
        rows.append({**head, "format": comp, "role": role, **compare(r["scores"], a["scores"])})
    for role in ("batter", "bowler"):
        rc, ac = (
            combined_scores(ref, role, W_IPL_DEFAULT),
            combined_scores(alt, role, W_IPL_DEFAULT),
        )
        rows.append({**head, "format": "COMBINED_w70_30", "role": role, **compare(rc, ac)})
    return rows


def _meta(run: dict[CellKey, dict[str, Any]], key: CellKey) -> dict[str, Any]:
    est, mask = run[key]["est"], run[key]["mask"]
    return {
        "k": float(est["k"].iloc[0]) if len(est) else None,
        "median_data_weight_pool": float(np.median(est["B"].to_numpy()[mask]))
        if mask.any()
        else None,
    }


# ---------------------------------------------------------------- definition grid
def definition_grid(study: Study) -> pd.DataFrame:
    """Nine definitions (quantile thresholds included) against the primary run."""
    rule = df_.load_rule()
    primary = study.cfg["definitions"]["primary"]
    named = set(study.cfg["definitions"]["alternatives"])
    cfg = study.frozen["shrinkage"]["config"]
    pcells = study.primary_cells(primary)
    ref = run_scores(pcells, study.frozen_rules(pcells), cfg)
    rows = []
    for defn in df_.definition_ids(rule):
        cells = study.primary_cells(defn)
        run = run_scores(cells, study.frozen_rules(cells), cfg)
        ctx, q = defn.split("|q")
        head = {"definition": defn, "context": ctx, "q": float(q), "is_primary": defn == primary,
                "is_named_alternative": defn in named, "shrinkage": cfg}  # fmt: skip
        part = _compare_runs(ref, run, head)
        for r in part:
            key = (r["format"], r["role"])
            if key in cells:
                r["pressure_balls_pre_test"] = int(cells[key].N.sum())
                r["players_with_pressure_balls"] = int(len(cells[key].players))
        rows += part
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- shrinkage x definition
def shrinkage_grid(study: Study) -> pd.DataFrame:
    """Seven shrinkage configurations for each of the four named definitions (28 combinations)."""
    primary = study.cfg["definitions"]["primary"]
    names = study.cfg["sensitivity"]["named_definitions_for_shrinkage_cross"]
    chosen = study.frozen["shrinkage"]["config"]
    pcells = study.primary_cells(primary)
    ref = run_scores(pcells, study.frozen_rules(pcells), chosen)
    rows = []
    for defn in names:
        cells = study.primary_cells(defn)
        rules = study.frozen_rules(cells)
        same_def_ref = run_scores(cells, rules, chosen)
        for config in sh.CONFIGS:
            run = run_scores(cells, rules, config)
            head = {"definition": defn, "is_primary_definition": defn == primary,
                    "shrinkage_config": config, "is_frozen_choice": config == chosen}  # fmt: skip
            vs_primary = _compare_runs(ref, run, {**head, "reference": "primary_run"})
            vs_same = _compare_runs(
                same_def_ref, run, {**head, "reference": "same_definition_frozen_shrinkage"}
            )
            for r in vs_primary + vs_same:
                key = (r["format"], r["role"])
                if key in run:
                    r.update(_meta(run, key))
            rows += vs_primary + vs_same
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- eligibility ball thresholds
def threshold_grid(study: Study) -> pd.DataFrame:
    """Alternative ball thresholds for the primary definition against the frozen working pool."""
    primary = study.cfg["definitions"]["primary"]
    chosen = study.frozen["shrinkage"]["config"]
    ladders = json.loads(ELIG_RULES.read_text(encoding="utf-8"))["ladders"]
    cells = study.primary_cells(primary)
    rules = study.frozen_rules(cells)
    rows = []
    for key, cell in cells.items():
        comp, role = key
        fit = cell.fit()
        ref_scores, est, _ = pool_scores(cell, rules[key], chosen, fit)
        tp = cell.train_pt()
        sign = en.PRIMARY[role][1]
        score = pd.Series(sign * est["shrunk"].to_numpy(), index=cell.players)
        k = float(est["k"].iloc[0])
        for cand in el.candidate_thresholds(tp["n"].to_numpy(), ladders[role]["balls"]):
            t = cand["threshold"]
            mask = (est["n"].to_numpy() >= t * rules[key]["wr"]) & np.isfinite(score.to_numpy())
            alt = score[mask]
            ne = est["n_eff"].to_numpy()[mask]
            rows.append(
                {"definition": primary, "format": comp, "role": role, "threshold_balls": t,
                 "source": cand["source"], "is_frozen_working_pool": t == rules[key]["threshold_balls"],
                 "marginal_data_weight": float(ne.min() / (ne.min() + k)) if mask.any() and k > 0 else None,
                 **compare(ref_scores, alt)}
            )  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- baseline alternatives
def baseline_grid(study: Study) -> pd.DataFrame:
    primary = study.cfg["definitions"]["primary"]
    cells = study.primary_cells(primary)
    rules = study.frozen_rules(cells)
    return p4s.baseline_alternatives(
        study.d, primary, study.thresholds(primary), study.frozen["shrinkage"]["config"], rules,
        cells, study.lock, DEFAULT_PARAMS,
    )  # fmt: skip


# ---------------------------------------------------------------- format weights
def format_weight_grid(study: Study) -> dict[str, pd.DataFrame]:
    """Eight weight configurations over ONE shared set of final eligibility rules (primary def)."""
    primary = study.cfg["definitions"]["primary"]
    cells = study.primary_cells(primary)
    rules = study.frozen_rules(cells)
    fits = {k: c.fit() for k, c in cells.items()}
    return p4s.format_weight_analysis(cells, fits, rules, study.gm, study.W,
                                      study.frozen["shrinkage"]["config"], study.format_weights())  # fmt: skip


# ---------------------------------------------------------------- date-restricted TEST sets
def test_set_comparison(manifest_path: Path | str) -> dict[str, Any]:
    """Set composition and counts only. No TEST outcome is read or evaluated."""
    p = Path(manifest_path)
    if not p.exists():
        return {"status": "MANIFEST_MISSING", "path": str(p), "sets": []}
    m = json.loads(p.read_text(encoding="utf-8"))
    sets = []
    for name, s in m["sets"].items():
        c = s["counts"]
        row = {"set": name, "rule": s["rule"], "matches": c["matches"], "deliveries": c["deliveries"],
               "players": c["players"]}  # fmt: skip
        for comp in SCOPE:
            row[f"matches_{comp}"] = (
                c.get("by_competition_type", {}).get(comp, {}).get("matches", 0)
            )
        sets.append(row)
    return {
        "status": "SET_DEFINITIONS_ONLY_NO_TEST_OUTCOMES",
        "manifest_status": m.get("status"),
        "test_evaluated_in_phase5": m.get("test_evaluated_in_phase5"),
        "sets": sets,
        "excluded_from_primary": m.get("excluded_from_primary"),
        "excluded_from_strict": m.get("excluded_from_strict"),
        "manifest_self_sha256": m.get("self_sha256"),
    }
