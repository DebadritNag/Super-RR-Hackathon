"""Phase 4 Stage D: comparison of the nine full-eligibility pressure definitions.

The selection rule lives in ``config/phase4_definition_rule_v1.json`` and is fixed before any
metric is computed (its SHA-256 is recorded in the output). Only TRAIN and VALIDATION rows are
used. The eligible population is a Gate 1 floor, never the objective. The winner is PROVISIONAL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4.baseline import STREAMS, BaselineSet
from app.phase4.config import file_sha256
from app.phase4.constants import CONFIG_DIR, SCOPE
from app.phase4.split import TestLock

RULE_PATH = CONFIG_DIR / "phase4_definition_rule_v1.json"
EXPECTED_SIGN = {"batter": -1, "bowler": +1}  # residual sign expected under pressure


def load_rule(path: Path | str = RULE_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def definition_ids(rule: dict[str, Any]) -> list[str]:
    c = rule["candidates"]
    return [f"{ctx}|q{q}" for ctx in c["contexts"] for q in c["q"]]


def fisher(r: np.ndarray, clip: float) -> np.ndarray:
    return np.arctanh(np.clip(r, -clip, clip))


def spearman_brown(r: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(r > -1.0, 2.0 * r / (1.0 + r), np.nan)


def rs_stats(cell: en.Cell, w: np.ndarray, p: dict[str, Any]) -> dict[str, np.ndarray]:
    """Split-half reliability R (TRAIN) and TRAIN-to-VALIDATION stability S for weights ``w``.

    ``w`` has shape (n_cell_matches, B); ``B = 1`` with all ones gives the point estimate.
    """
    tr = cell.match_period == "TRAIN"
    va = cell.match_period == "VALIDATION"
    Ntr, Str = cell.N[:, tr], cell.S[:, tr]
    present = Ntr > 0
    cs = np.cumsum(present, axis=1)
    odd, even = present & (cs % 2 == 1), present & (cs % 2 == 0)
    wtr, wva = w[tr], w[va]
    n1, s1 = (Ntr * odd) @ wtr, (Str * odd) @ wtr
    n2, s2 = (Ntr * even) @ wtr, (Str * even) @ wtr
    ntr, st = Ntr @ wtr, Str @ wtr
    nva, sv = cell.N[:, va] @ wva, cell.S[:, va] @ wva
    with np.errstate(invalid="ignore", divide="ignore"):
        m1, m2 = s1 / n1, s2 / n2
        mtr, mva = st / ntr, sv / nva
    qr = (ntr >= p["min_balls_R"]) & (n1 > 0) & (n2 > 0)
    qs = (ntr >= p["min_balls_S_train"]) & (nva >= p["min_balls_S_validation"])
    return {
        "r_half": en.masked_pearson(m1, m2, qr),
        "n_R": qr.sum(0),
        "r_S": en.masked_pearson(mtr, mva, qs),
        "n_S": qs.sum(0),
    }


def pooled_sc(cell_stats: list[dict[str, np.ndarray]], p: dict[str, Any]) -> np.ndarray:
    """Pooled Sc on the correlation scale per resample, from per-cell R/S statistics."""
    clip, nmin = p["corr_clip"], p["min_players_for_RS"]
    num_r = den_r = num_s = den_s = 0.0
    for st in cell_stats:
        zr = fisher(spearman_brown(st["r_half"]), clip)
        zs = fisher(st["r_S"], clip)
        wr = np.where((st["n_R"] >= nmin) & np.isfinite(zr), st["n_R"] - 3.0, 0.0)
        ws = np.where((st["n_S"] >= nmin) & np.isfinite(zs), st["n_S"] - 3.0, 0.0)
        num_r, den_r = num_r + wr * np.nan_to_num(zr), den_r + wr
        num_s, den_s = num_s + ws * np.nan_to_num(zs), den_s + ws
    with np.errstate(invalid="ignore", divide="ignore"):
        zbar_r = np.where(den_r > 0, num_r / den_r, np.nan)
        zbar_s = np.where(den_s > 0, num_s / den_s, np.nan)
    return np.tanh(0.5 * (zbar_r + zbar_s))


def contrast(rows: pd.DataFrame, gm: pd.Index, W: np.ndarray) -> dict[str, Any]:
    """VALIDATION pressure vs non-pressure contrast of residuals with a match-cluster bootstrap."""
    v = rows[(rows["period"] == "VALIDATION") & rows["in_pop"]]
    if v.empty or not v["press"].any() or v["press"].all():
        return {"D": None, "D_lo": None, "D_hi": None, "mean_diff": None, "diff_lo": None,
                "diff_hi": None, "n_press": int(v["press"].sum())}  # fmt: skip
    g = v.assign(r2=v["resid"] ** 2, one=1.0).groupby(["match_id", "press"])
    a = g.agg(n=("one", "sum"), s=("resid", "sum"), ss=("r2", "sum")).unstack("press", fill_value=0)
    mids = a.index.to_numpy()
    w = W[:, gm.get_indexer(mids)]

    def grp(flag: bool):
        return (a[("n", flag)].to_numpy(), a[("s", flag)].to_numpy(), a[("ss", flag)].to_numpy())

    (npr, spr, ssp), (nnp, snp, ssn) = grp(True), grp(False)

    def stat(wt: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        n1, n0 = wt @ npr, wt @ nnp
        with np.errstate(invalid="ignore", divide="ignore"):
            m1, m0 = (wt @ spr) / n1, (wt @ snp) / n0
            var = ((wt @ ssp) - n1 * m1**2 + (wt @ ssn) - n0 * m0**2) / (n1 + n0 - 2)
            return (m1 - m0) / np.sqrt(var), m1 - m0

    d0, diff0 = stat(np.ones((1, len(mids))))
    db, diffb = stat(w)
    q = lambda x, p: float(np.nanpercentile(x, p))  # noqa: E731
    return {"D": float(d0[0]), "D_lo": q(db, 2.5), "D_hi": q(db, 97.5), "mean_diff": float(diff0[0]),
            "diff_lo": q(diffb, 2.5), "diff_hi": q(diffb, 97.5), "n_press": int(v["press"].sum())}  # fmt: skip


def evaluate_definitions(
    d: pd.DataFrame,
    bs: BaselineSet,
    lock: TestLock,
    rule: dict[str, Any] | None = None,
    n_boot: int | None = None,
) -> dict[str, Any]:
    """All nine candidates x four cells; the rule is applied to the resulting table."""
    rule = rule or load_rule()
    p = rule["parameters"]
    B = int(n_boot or rule["n_boot"])
    seed = int(rule["seed"])
    ids = definition_ids(rule)
    d_train = d[d["period"] == "TRAIN"]
    thr_by_q = {q: sc.fit_thresholds(d_train, q) for q in rule["candidates"]["q"]}
    base = {(role, st): en.base_rows(d, bs, role, st, lock) for role, st, _ in STREAMS}
    gm, W = en.global_weights(d["match_id"].to_numpy(), B, seed)
    rows_out: list[dict[str, Any]] = []
    boot_sc: dict[str, list[dict[str, np.ndarray]]] = {i: [] for i in ids}
    point_stats: dict[str, list[dict[str, np.ndarray]]] = {i: [] for i in ids}
    for defn in ids:
        _, q = sc.parse_definition(defn)
        thr = thr_by_q[q]
        for role in ("batter", "bowler"):
            primary, sign = en.PRIMARY[role]
            second = en.SECONDARY[role]
            tagged = en.tag_rows(base[(role, primary)], d, defn, thr)
            tagged2 = en.tag_rows(base[(role, second)], d, defn, thr)
            for comp in SCOPE:
                t = tagged[tagged["comp"] == comp]
                press = t[t["press"]]
                cell = en.build_cell(press, comp, role, primary)
                ctx = sc.parse_definition(defn)[0]
                rec: dict[str, Any] = {
                    "definition_id": defn,
                    "format": comp,
                    "role": role,
                    "stream": primary,
                }
                if ctx == "any":
                    thr_val = {"chase": thr[f"chase|{comp}"], "inn1": thr[f"inn1|{comp}"]}
                    rec["threshold"] = json.dumps(thr_val)
                else:
                    rec["threshold"] = thr[f"{ctx}|{comp}"]
                for per in ("TRAIN", "VALIDATION"):
                    pp = press[press["period"] == per]
                    rec[f"pressure_balls_{per}"] = int(len(pp))
                    rec[f"distinct_matches_{per}"] = int(pp["match_id"].nunique())
                    rec[f"players_{per}"] = int(pp["player_id"].nunique())
                popc = d["competition_type"] == comp
                if ctx != "chase":
                    i1 = d["inn1_pop"] & popc & (d["period"] == "TRAIN")
                    un = d["par_unavailable_insufficient_prior"].fillna(False).astype(bool)
                    rec["par_unavailable_share_inn1_TRAIN"] = float(
                        (i1 & un).sum() / max(i1.sum(), 1)
                    )
                else:
                    rec["par_unavailable_share_inn1_TRAIN"] = None
                rec["expected_direction"] = EXPECTED_SIGN[role]
                c1 = contrast(t, gm, W)
                c2 = contrast(tagged2[tagged2["comp"] == comp], gm, W)
                rec.update(
                    {k: c1[k] for k in ("D", "D_lo", "D_hi", "mean_diff", "diff_lo", "diff_hi")}
                )
                rec["secondary_stream"] = second
                rec["secondary_mean_diff"] = c2["mean_diff"]
                rec["secondary_diff_lo"] = c2["diff_lo"]
                rec["secondary_diff_hi"] = c2["diff_hi"]
                rec["D_in_expected_direction"] = (
                    None if rec["D"] is None else bool(np.sign(rec["D"]) == EXPECTED_SIGN[role])
                )
                if cell is None:
                    rec.update({"P_players_ge_min_balls": 0, "R_split_half": None, "n_R": 0,
                                "S_train_validation": None, "n_S": 0, "snr": None,
                                "expected_top10_overlap": None, "top10_pool": 0})  # fmt: skip
                    rows_out.append(rec)
                    for store in (point_stats, boot_sc):
                        store[defn].append(
                            {"r_half": np.array([np.nan]), "n_R": np.array([0]),
                             "r_S": np.array([np.nan]), "n_S": np.array([0])}
                        )  # fmt: skip
                    continue
                tp = cell.train_pt()
                rec["P_players_ge_min_balls"] = int((tp["n"] >= p["min_balls_P"]).sum())
                ps = rs_stats(cell, np.ones((len(cell.matches), 1)), p)
                rec["R_split_half_raw"] = float(ps["r_half"][0])
                rec["R_split_half"] = float(spearman_brown(ps["r_half"])[0])
                rec["n_R"] = int(ps["n_R"][0])
                rec["S_train_validation"] = float(ps["r_S"][0])
                rec["n_S"] = int(ps["n_S"][0])
                fit = cell.fit()
                if len(tp) >= 2 and np.isfinite(fit["sigma2"]):
                    noise = (fit["sigma2"] / tp["n_eff"].clip(lower=1e-9)).mean()
                    rec["snr"] = float(fit["between"] / noise) if noise > 0 else None
                else:
                    rec["snr"] = None
                w = en.cell_weights(cell, gm, W)
                point_stats[defn].append(ps)
                boot_sc[defn].append(rs_stats(cell, w, p))
                est = en.point_estimates(cell, fit, "shrink_eb")
                present = (est["n"].to_numpy() >= p["report_pool_min_balls"]) & np.isfinite(
                    est["shrunk"].to_numpy()
                )
                nb, dr = en.draws(cell, est, w)
                score = sign * dr
                pres = present[:, None] & (nb >= p["report_pool_min_balls"])
                rs = en.rank_summary(np.where(pres, score, np.nan), sign * est["shrunk"].to_numpy(),
                                     present)  # fmt: skip
                sm = en.summarize_ranking(rs)
                rec["expected_top10_overlap"] = sm["expected_top10_overlap"]
                rec["top10_pool"] = sm["pool_size"]
                rows_out.append(rec)
    table = pd.DataFrame(rows_out)
    cands = []
    for defn in ids:
        sub = table[table["definition_id"] == defn]
        sc_point = float(pooled_sc(point_stats[defn], p)[0])
        sc_boot = pooled_sc(boot_sc[defn], p)
        gate1 = bool((sub["P_players_ge_min_balls"] >= p["gate1_min_players_P"]).all())
        est_ok = bool(
            (
                (sub["n_R"] >= p["min_players_for_RS"]) & (sub["n_S"] >= p["min_players_for_RS"])
            ).all()
        )
        cands.append(
            {
                "definition_id": defn,
                "gate1_pass": gate1,
                "rankable": est_ok,
                "Sc": sc_point if np.isfinite(sc_point) else None,
                "Sc_boot_se": float(np.nanstd(sc_boot, ddof=1)),
                "min_P": int(sub["P_players_ge_min_balls"].min()),
                "total_P": int(sub["P_players_ge_min_balls"].sum()),
                "total_pressure_balls_TRAIN": int(sub["pressure_balls_TRAIN"].sum()),
                "_boot": sc_boot,
            }
        )
    return {"table": table, "candidates": apply_rule(cands, rule), "rule": rule,
            "rule_sha256": file_sha256(RULE_PATH), "n_boot": B, "seed": seed}  # fmt: skip


def apply_rule(cands: list[dict[str, Any]], rule: dict[str, Any]) -> dict[str, Any]:
    """Apply the pre-declared selection rule to candidate summaries (no population objective)."""
    p = rule["parameters"]
    leading = rule["candidates"]["leading_provisional"]
    ok = [c for c in cands if c["gate1_pass"] and c["rankable"] and c["Sc"] is not None]
    boots = {c["definition_id"]: c["_boot"] for c in cands}
    wins = {c["definition_id"]: 0 for c in cands}
    if ok:
        mat = np.vstack([boots[c["definition_id"]] for c in ok])
        mat = np.where(np.isfinite(mat), mat, -np.inf)
        best_idx = np.argmax(mat, axis=0)
        for i in best_idx:
            wins[ok[int(i)]["definition_id"]] += 1
    nb = max(len(next(iter(boots.values()))), 1) if boots else 1
    out_c = []
    for c in cands:
        reason = (
            "GATE1_FAIL" if not c["gate1_pass"] else "NOT_RANKABLE" if not c["rankable"] else "OK"
        )
        out_c.append({**{k: v for k, v in c.items() if k != "_boot"}, "status": reason,
                      "selection_share": wins[c["definition_id"]] / nb})  # fmt: skip
    result: dict[str, Any] = {"candidates": out_c, "leading_provisional": leading}
    if len(ok) >= 3:
        rho = spearmanr([c["Sc"] for c in ok], [c["total_pressure_balls_TRAIN"] for c in ok])
        result["sample_size_confound_spearman"] = float(rho.statistic)
        result["sample_size_confound_n"] = len(ok)
    if not ok:
        result.update({"winner": None, "top_group": [], "leading_status": "NO_RANKABLE_CANDIDATE",
                       "label": "NO_RULE_WINNER; leading default retained, not validated"})  # fmt: skip
        return result
    best = max(ok, key=lambda c: c["Sc"])
    margin = max(p["tie_margin"], best["Sc_boot_se"])
    top = sorted(c["definition_id"] for c in ok if c["Sc"] >= best["Sc"] - margin)
    result.update(
        {
            "winner": top[0],
            "best_Sc_candidate": best["definition_id"],
            "tie_margin_used": margin,
            "top_group": top,
            "label": rule["winner_label"],
            "leading_status": next(
                (x["status"] for x in out_c if x["definition_id"] == leading), "UNKNOWN"
            ),
            "leading_in_top_group": leading in top,
        }
    )
    return result
