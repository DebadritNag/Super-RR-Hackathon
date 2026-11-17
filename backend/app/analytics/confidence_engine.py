"""Data-driven eligibility thresholds: distributions, candidates, stability and bootstrap.

Generic harness: it consumes per (format, player, match) sufficient statistics (see
`proxy_samples`) and a score function. Phase 3 can pass pressure samples unchanged.
Batter and bowler eligibility are always evaluated independently.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.proxy_samples import ProxySamples
from app.analytics.ranking import rank_players, spearman_common, topk_overlap
from app.analytics.reporting import PROXY_FIELDS
from app.analytics.shrinkage import eb_shrink

ROLE_STREAMS = {"batter": ("runs",), "bowler": ("econ", "wkt")}
ROLES = ("batter", "bowler")
PROB_KEYS = (5, 10, 25, 50, 75, 90, 95)


def load_rules(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- sample preparation


class Prepared:
    """Per-(player, match) rows of one format and role as arrays, with weighted aggregation."""

    def __init__(self, rows: pd.DataFrame, role: str) -> None:
        rows = rows.sort_values(["player_id", "match_id"], kind="mergesort")
        self.role = role
        self.player_ids = np.sort(rows["player_id"].unique()).astype("int64")
        self.match_ids = np.sort(rows["match_id"].unique()).astype("int64")
        self.pidx = np.searchsorted(self.player_ids, rows["player_id"].to_numpy())
        self.midx = np.searchsorted(self.match_ids, rows["match_id"].to_numpy())
        self.n = rows["n"].to_numpy(dtype=float)
        self.balls = rows["n" if role == "batter" else "legal_balls"].to_numpy(dtype=float)
        self.innings = rows["innings"].to_numpy(dtype=float)
        self.streams = {
            s: (rows[f"{s}_sum"].to_numpy(dtype=float), rows[f"{s}_sum2"].to_numpy(dtype=float))
            for s in ROLE_STREAMS[role]
        }

    @property
    def n_players(self) -> int:
        return len(self.player_ids)

    def aggregate(self, row_weights: np.ndarray | None = None) -> dict[str, np.ndarray]:
        w = np.ones(len(self.pidx)) if row_weights is None else row_weights
        P = self.n_players
        agg = {"n": np.bincount(self.pidx, weights=self.n * w, minlength=P)}
        for s, (a, b) in self.streams.items():
            agg[f"{s}_sum"] = np.bincount(self.pidx, weights=a * w, minlength=P)
            agg[f"{s}_sum2"] = np.bincount(self.pidx, weights=b * w, minlength=P)
        return agg


def _z_masked(values: np.ndarray, obs: np.ndarray) -> np.ndarray:
    out = np.zeros_like(values, dtype=float)
    if obs.sum() == 0:
        return out
    v = values[obs]
    sd = v.std()
    if not np.isfinite(sd) or sd == 0:
        return out
    return (values - v.mean()) / sd


def score_from_agg(role: str, agg: dict[str, np.ndarray]) -> dict[str, Any]:
    """Proxy score per player from aggregated sufficient statistics (PROXY_NOT_PRESSURE)."""
    n = agg["n"]
    obs = n > 0
    if role == "batter":
        sh = eb_shrink(n, agg["runs_sum"], agg["runs_sum2"])
        return {"score": 100.0 * sh["rate"], "n_eff": sh["n_eff"], "priors": {"runs": _prior(sh)}}
    e = eb_shrink(n, agg["econ_sum"], agg["econ_sum2"])
    w = eb_shrink(n, agg["wkt_sum"], agg["wkt_sum2"])
    score = -_z_masked(6.0 * e["rate"], obs) + _z_masked(w["rate"], obs)
    return {"score": score, "n_eff": e["n_eff"], "priors": {"econ": _prior(e), "wkt": _prior(w)}}


def _prior(sh: dict) -> dict:
    return {k: sh[k] for k in ("players", "total_n", "mu0", "sigma2", "tau2", "k")}


def player_table(prep: Prepared) -> pd.DataFrame:
    """Per-player sample-size measures over all observed players of the format."""
    P = prep.n_players
    agg = prep.aggregate()
    sc = score_from_agg(prep.role, agg)
    n_sum = np.bincount(prep.pidx, weights=prep.n, minlength=P)
    n_sq = np.bincount(prep.pidx, weights=prep.n**2, minlength=P)
    kish = np.where(n_sq > 0, n_sum**2 / np.where(n_sq > 0, n_sq, 1.0), 0.0)
    return pd.DataFrame(
        {
            "player_id": prep.player_ids,
            "balls": np.bincount(prep.pidx, weights=prep.balls, minlength=P),
            "matches": np.bincount(prep.pidx, minlength=P).astype(float),
            "innings": np.bincount(prep.pidx, weights=prep.innings, minlength=P),
            "n_eff_shrink": sc["n_eff"],
            "n_eff_kish": kish,
            "score": sc["score"],
        }
    )


# ------------------------------------------------------------------------------- distributions


def describe(values) -> dict[str, Any]:
    a = np.asarray(list(values), dtype=float)
    if a.size == 0:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    out: dict[str, Any] = {
        "count": int(a.size),
        "mean": float(a.mean()),
        "std": float(a.std(ddof=1)) if a.size > 1 else 0.0,
        "min": float(a.min()),
    }
    for p in PROB_KEYS:
        out[f"p{p}"] = float(np.percentile(a, p))
    out["max"] = float(a.max())
    return out


def histogram(values, edges: list[float]) -> list[dict]:
    counts, _ = np.histogram(np.asarray(list(values), dtype=float), bins=edges)
    return [
        {"lower": edges[i], "upper": None if i == len(edges) - 2 else edges[i + 1], "count": int(c)}
        for i, c in enumerate(counts)
    ]


def distribution_for(table: pd.DataFrame, rules: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"observed_players": int(len(table)), "measures": {}}
    for m in rules["measures"]:
        v = table[m].to_numpy()
        out["measures"][m] = {
            "summary": describe(v),
            "histogram": histogram(v, rules["histogram_edges"][m]),
        }
    out["zero_inflation"] = {
        "balls_le_5": int((table["balls"] <= 5).sum()),
        "single_match_players": int((table["matches"] == 1).sum()),
        "single_match_share": float((table["matches"] == 1).mean()) if len(table) else None,
    }
    return out


# ---------------------------------------------------------------------------------- candidates


def percentile_candidates(values, percentiles) -> list[dict]:
    a = np.asarray(list(values), dtype=float)
    if a.size == 0:
        return []
    return [
        {
            "label": f"P{p}",
            "kind": "percentile",
            "percentile": p,
            "observed_value": float(np.percentile(a, p)),
            "value": max(1, int(math.ceil(np.percentile(a, p)))),
        }
        for p in percentiles
    ]


def practical_candidates(nominal, values, pct_cands, tolerance) -> list[dict]:
    """Keep nominal ladder values between observed p10 and p90 and not within tolerance of a
    percentile candidate. Every nominal value is reported with the reason it was kept or dropped.
    """
    a = np.asarray(list(values), dtype=float)
    out = []
    if a.size == 0:
        return out
    lo, hi = float(np.percentile(a, 10)), float(np.percentile(a, 90))
    for x in nominal:
        reason = None
        if x < lo:
            reason = "below_observed_p10"
        elif x > hi:
            reason = "above_observed_p90"
        else:
            for c in pct_cands:
                if abs(x - c["value"]) <= tolerance * c["value"]:
                    reason = f"within_{int(tolerance * 100)}pct_of_{c['label']}"
                    break
        below = float((a < x).mean() * 100)
        elig = int((a >= x).sum())
        out.append(
            {
                "label": f"PR{x}",
                "kind": "practical",
                "value": int(x),
                "kept": reason is None,
                "drop_reason": reason,
                "percentile_rank": below,
                "eligible_count": elig,
                "justification": (
                    f"{x} lies at observed percentile {below:.1f} with {elig} of {a.size} "
                    f"players at or above it (observed p10={lo:.1f}, p90={hi:.1f})"
                ),
            }
        )
    return out


def build_ladder(pct_cands: list[dict], practical: list[dict]) -> list[dict]:
    """Ascending ladder of unique threshold values; aliases record merged labels."""
    items = list(pct_cands) + [p for p in practical if p["kept"]]
    items.sort(key=lambda c: (c["value"], 0 if c["kind"] == "percentile" else 1, c["label"]))
    ladder: list[dict] = []
    for c in items:
        if ladder and ladder[-1]["value"] == c["value"]:
            ladder[-1]["aliases"].append(c["label"])
        else:
            ladder.append(
                {"label": c["label"], "kind": c["kind"], "value": c["value"], "aliases": []}
            )
    return ladder


def build_rules(ladders: dict[str, list[dict]], practical: dict[str, list[dict]], max_pairs: int):
    """Single-measure rules for every ladder entry, plus balls AND matches conjunctions."""
    rules = []
    for measure, ladder in ladders.items():
        for i, e in enumerate(ladder):
            rules.append(
                {
                    "id": f"{measure}:{e['label']}",
                    "family": measure,
                    "label": e["label"],
                    "clauses": [{"measure": measure, "min": e["value"]}],
                    "ladder_index": i,
                }
            )
    pb = [p for p in practical.get("balls", []) if p["kept"]]
    pm = [p for p in practical.get("matches", []) if p["kept"]]
    pairs = list(itertools.product(pb, pm))
    pairs.sort(key=lambda t: (pb.index(t[0]) + pm.index(t[1]), pb.index(t[0])))
    if len(pairs) > max_pairs:
        idx = np.unique(np.linspace(0, len(pairs) - 1, max_pairs).round().astype(int))
        pairs = [pairs[i] for i in idx]
    for i, (b, m) in enumerate(pairs):
        rules.append(
            {
                "id": f"balls+matches:{b['label']}&{m['label']}",
                "family": "balls+matches",
                "label": f"{b['label']}&{m['label']}",
                "clauses": [
                    {"measure": "balls", "min": b["value"]},
                    {"measure": "matches", "min": m["value"]},
                ],
                "ladder_index": i,
            }
        )
    return rules


def eligible_mask(table: pd.DataFrame, rule: dict) -> np.ndarray:
    mask = np.ones(len(table), dtype=bool)
    for c in rule["clauses"]:
        mask &= table[c["measure"]].to_numpy() >= c["min"]
    return mask


def pool_verdict(n_eligible: int, list_size: int, pool_min_absolute: int, multiplier: int) -> dict:
    required = max(int(pool_min_absolute), int(multiplier) * int(list_size))
    sufficient = n_eligible >= required
    fewer = n_eligible < list_size
    if fewer:
        msg = (
            f"INSUFFICIENT: {n_eligible} eligible, fewer than the list size of {list_size}; "
            f"no list of {list_size} can be formed and none is padded"
        )
    elif not sufficient:
        msg = f"INSUFFICIENT: {n_eligible} eligible, below the required pool of {required}"
    else:
        msg = f"SUFFICIENT: {n_eligible} eligible, at or above the required pool of {required}"
    return {
        "eligible": int(n_eligible),
        "required": required,
        "sufficient": bool(sufficient),
        "fewer_than_list_size": bool(fewer),
        "message": msg,
    }


def match_coverage(prep: Prepared, mask: np.ndarray, total_matches: int | None) -> dict:
    row_mask = mask[prep.pidx] if len(prep.pidx) else np.zeros(0, dtype=bool)
    covered = int(len(np.unique(prep.midx[row_mask]))) if row_mask.any() else 0
    total = total_matches if total_matches else len(prep.match_ids)
    return {
        "matches_covered": covered,
        "format_matches_with_deliveries": int(total),
        "coverage_pct": 100.0 * covered / total if total else None,
    }


# ------------------------------------------------------------------------------------ bootstrap


def bootstrap_score_matrix(prep: Prepared, rng: np.random.Generator, n_boot: int) -> np.ndarray:
    """B x P matrix of population-level scores; matches are resampled with replacement.

    Every row of a match gets the match's multiplicity, so deliveries are never resampled alone.
    """
    M = len(prep.match_ids)
    out = np.empty((n_boot, prep.n_players))
    if M == 0:
        return out
    mult = rng.multinomial(M, np.full(M, 1.0 / M), size=n_boot).astype(float)
    for b in range(n_boot):
        agg = prep.aggregate(mult[b][prep.midx])
        out[b] = score_from_agg(prep.role, agg)["score"]
    return out


def bootstrap_rule(
    matrix: np.ndarray, orig: np.ndarray, sel: np.ndarray, k: int = 10, detail: bool = False
) -> dict[str, Any]:
    """Interval widths, Top-k membership and rank stability for a fixed eligible set."""
    m = int(sel.sum())
    if m == 0 or matrix.shape[0] == 0:
        return {"eligible": m, "evaluated": False}
    sub = matrix[:, sel]
    o = orig[sel]
    lo, hi = np.percentile(sub, [2.5, 97.5], axis=0)
    width = hi - lo
    kk = min(k, m)
    base = np.argsort(-o, kind="stable")[:kk]
    top = np.argsort(-sub, axis=1, kind="stable")[:, :kk]
    freq = np.bincount(top.ravel(), minlength=m) / sub.shape[0]
    res: dict[str, Any] = {
        "eligible": m,
        "evaluated": True,
        "n_boot": int(sub.shape[0]),
        "interval_width_median": float(np.median(width)),
        "interval_width_p95": float(np.percentile(width, 95)),
        "top_k": kk,
        "top_k_mean_membership_freq": float(freq[base].mean()),
        "top_k_players_freq_ge_half": int((freq[base] >= 0.5).sum()),
        "expected_top_k_overlap": float(freq[base].sum()),
    }
    if m >= 3:
        ro = np.argsort(np.argsort(-o, kind="stable"), kind="stable")
        rb = np.argsort(np.argsort(-sub, axis=1, kind="stable"), axis=1, kind="stable")
        rho = 1.0 - 6.0 * ((rb - ro) ** 2).sum(axis=1) / (m * (m * m - 1.0))
        res["spearman_vs_original_mean"] = float(rho.mean())
        res["spearman_vs_original_p5"] = float(np.percentile(rho, 5))
    else:
        res["spearman_vs_original_mean"] = None
        res["spearman_vs_original_p5"] = None
    if detail:
        res["_lo"], res["_hi"], res["_freq"], res["_base"] = lo, hi, freq, base
    return res


# ----------------------------------------------------------------------------- recommendation


def recommend(
    entries: list[dict], cfg: dict, required_balls: float | None = None
) -> dict[str, Any]:
    """Recommendation inputs for one rule family; entries run from loosest to strictest.

    Primary rule (data weight): the lowest entry whose minimum is at least `required_balls`
    (the sample size at which a player's data outweighs the empirical-Bayes prior) and whose pool
    is sufficient. The generic stability conditions (Spearman and Top 10 overlap versus the next
    higher rule, interval-width plateau) are kept as diagnostics; `stability_discriminates` is
    False when every step passes them, i.e. they cannot separate thresholds.
    """
    stable = []
    for i, e in enumerate(entries[:-1]):
        nxt = entries[i + 1]
        w0, w1 = e.get("width_median"), nxt.get("width_median")
        drop = (w0 - w1) / w0 if w0 and w1 is not None and w0 > 0 else None
        rho, ov = e.get("spearman_vs_next"), e.get("overlap_vs_next")
        need_ov = min(cfg["overlap_min"], nxt["eligible"], 10)
        ok = (
            e["pool_sufficient"]
            and nxt["pool_sufficient"]
            and rho is not None
            and rho >= cfg["spearman_min"]
            and ov is not None
            and ov >= need_ov
            and drop is not None
            and drop <= cfg["ci_width_drop_max"]
        )
        stable.append({"rule_id": e["rule_id"], "width_drop_to_next": drop, "stable": bool(ok)})
    suff = [e for e in entries if e["pool_sufficient"]]
    first_stable = next((s["rule_id"] for s in stable if s["stable"]), None)
    dw = None
    if required_balls is not None:
        dw = next(
            (
                e["rule_id"]
                for e in entries
                if e.get("min_value") is not None
                and e["min_value"] >= required_balls
                and e["pool_sufficient"]
            ),
            None,
        )
    return {
        "ladder": entries,
        "stability_checks": stable,
        "stability_discriminates": not (stable and all(s["stable"] for s in stable)),
        "lowest_stable_rule": first_stable,
        "required_balls_for_data_weight": required_balls,
        "min_data_weight": cfg.get("min_data_weight"),
        "data_weight_rule": dw,
        "highest_sufficient_pool_rule": suff[-1]["rule_id"] if suff else None,
        "rule_satisfied": dw is not None,
    }


def _required_balls(prep: Prepared, role: str, cfg: dict) -> float | None:
    """Balls at which data weight n/(n+k) reaches min_data_weight, using the primary stream."""
    w = cfg.get("min_data_weight")
    if w is None:
        return None
    pri = score_from_agg(role, prep.aggregate())["priors"]["runs" if role == "batter" else "econ"]
    total_n = prep.n.sum()
    if not pri["k"] or total_n <= 0:
        return None
    return float(pri["k"] * w / (1.0 - w) * prep.balls.sum() / total_n)


# ----------------------------------------------------------------------------- main experiment


def _scores_df(prep: Prepared, scores: np.ndarray, sel: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"player_id": prep.player_ids[sel], "score": scores[sel]})


def _compare(a: pd.DataFrame, b: pd.DataFrame, k: int) -> dict:
    ids_a = list(rank_players(a)["player_id"])
    ids_b = list(rank_players(b)["player_id"])
    return {
        "overlap": topk_overlap(ids_a, ids_b, k),
        "spearman": spearman_common(a, b),
        "n_a": int(len(a)),
        "n_b": int(len(b)),
    }


def run_experiment(
    samples: ProxySamples, rules_cfg: dict, n_boot: int | None = None
) -> tuple[dict, dict]:
    """Return (distribution_json, experiment_json) for batter and bowler, IPL and T20I."""
    n_boot = int(rules_cfg["n_boot"] if n_boot is None else n_boot)
    seed = int(rules_cfg["seed"])
    k = int(rules_cfg["list_size"])
    formats = list(rules_cfg["formats"])
    frames = {"batter": samples.batter, "bowler": samples.bowler}
    streams = np.random.SeedSequence(seed).spawn(len(formats) * len(ROLES))

    dist: dict[str, Any] = {
        **PROXY_FIELDS,
        "window": samples.window,
        "formats": {},
        "distinct_dismissal_types": samples.distinct_dismissal_types,
    }
    exp: dict[str, Any] = {
        **PROXY_FIELDS,
        "rules_version": rules_cfg["version"],
        "rules": {k_: v for k_, v in rules_cfg.items() if k_ != "histogram_edges"},
        "n_boot": n_boot,
        "bootstrap_notes": (
            "Unit is the match, stratified by format, with replacement. Eligibility is held "
            "fixed at the original sample; its sampling variability is not modelled."
        ),
        "formats": {},
        "combined": {},
        "recommendation_inputs": {},
        "technical_appendix": {},
    }
    eligible_sets: dict[tuple[str, str], dict[str, set]] = {}
    stream_i = 0
    for fmt in rules_cfg["distribution_formats"]:
        dist["formats"][fmt] = {}
        for role in ROLES:
            rows = frames[role]
            rows = rows[rows["format"] == fmt]
            prep = Prepared(rows, role)
            table = player_table(prep)
            dist["formats"][fmt][role] = distribution_for(table, rules_cfg)
            dist["formats"][fmt][role]["prior_parameters"] = score_from_agg(role, prep.aggregate())[
                "priors"
            ]
            dist["formats"][fmt][role]["matches_in_sample"] = int(len(prep.match_ids))
            if fmt not in formats:
                continue
            rng = np.random.default_rng(streams[stream_i])
            stream_i += 1
            res = _evaluate_format_role(fmt, role, prep, table, rules_cfg, samples, rng, n_boot, k)
            exp["formats"].setdefault(fmt, {})[role] = res["result"]
            eligible_sets[(fmt, role)] = res["eligible_by_rule"]
    # combined eligibility: rule ids present in both formats, eligible in both
    for role in ROLES:
        comb = {}
        a, b = (
            (eligible_sets.get((f, role), {}) for f in formats[:2])
            if len(formats) >= 2
            else ({}, {})
        )
        for rid in sorted(set(a) & set(b)):
            n = len(a[rid] & b[rid])
            comb[rid] = {
                "eligible_both_formats": n,
                "pool": pool_verdict(
                    n, k, rules_cfg["pool_min_absolute"], rules_cfg["pool_min_multiplier"]
                ),
            }
        exp["combined"][role] = comb
    for fmt in formats:
        for role in ROLES:
            res = exp["formats"][fmt][role]
            exp["recommendation_inputs"].setdefault(fmt, {})[role] = res.pop("recommendation")
            exp["technical_appendix"].setdefault(fmt, {})[role] = res.pop("appendix")
    exp["narrative"] = generate_narrative(exp, rules_cfg)
    return dist, exp


def _evaluate_format_role(fmt, role, prep, table, cfg, samples, rng, n_boot, k) -> dict:
    pct = cfg["percentiles"]
    tol = cfg["practical_tolerance"]
    ladders: dict[str, list[dict]] = {}
    cands: dict[str, Any] = {}
    practical_by_measure: dict[str, list[dict]] = {}
    for m in cfg["measures"]:
        vals = table[m].to_numpy()
        pc = percentile_candidates(vals, pct)
        nominal = cfg["ladders"][role].get(m, [])
        pr = practical_candidates(nominal, vals, pc, tol)
        practical_by_measure[m] = pr
        ladders[m] = build_ladder(pc, pr)
        cands[m] = {"percentile": pc, "practical": pr, "ladder": ladders[m]}
    rules = build_rules(ladders, practical_by_measure, cfg["max_conjunction_pairs"])

    total_matches = samples.window.get(fmt, {}).get("matches_with_deliveries")
    all_scores = score_from_agg(role, prep.aggregate())["score"]
    matrix = bootstrap_score_matrix(prep, rng, n_boot)
    pool_scores: dict[str, pd.DataFrame] = {}
    records: dict[str, dict] = {}
    eligible_by_rule: dict[str, set] = {}
    for rule in rules:
        mask = eligible_mask(table, rule)
        ids = set(int(x) for x in prep.player_ids[mask])
        eligible_by_rule[rule["id"]] = ids
        row_w = mask[prep.pidx].astype(float) if len(prep.pidx) else np.zeros(0)
        pool_sc = score_from_agg(role, prep.aggregate(row_w))["score"]
        pool_scores[rule["id"]] = _scores_df(prep, pool_sc, mask)
        sel_tab = table[mask]
        rec = {
            "rule_id": rule["id"],
            "family": rule["family"],
            "label": rule["label"],
            "clauses": rule["clauses"],
            "eligible": int(mask.sum()),
            "match_coverage": match_coverage(prep, mask, total_matches),
            "sample_size_distribution": {
                m: describe(sel_tab[m]) for m in ("balls", "matches", "n_eff_shrink")
            },
            "pool": pool_verdict(
                int(mask.sum()), k, cfg["pool_min_absolute"], cfg["pool_min_multiplier"]
            ),
            "bootstrap": bootstrap_rule(matrix, all_scores, mask, k),
        }
        records[rule["id"]] = rec
    # neighbours and reference, per family (ascending strictness)
    families: dict[str, list[dict]] = {}
    for rule in rules:
        families.setdefault(rule["family"], []).append(rule)
    ref_ids: dict[str, str] = {}
    for fam, frs in families.items():
        if fam == "balls+matches":
            frs.sort(key=lambda r: -records[r["id"]]["eligible"])
        ref = next(
            (r for r in frs if r["label"].startswith("PR") or "&" in r["label"]),
            frs[0],
        )
        ref_ids[fam] = ref["id"]
        for i, r in enumerate(frs):
            rec = records[r["id"]]
            rec["reference_rule"] = ref["id"]
            rec["vs_reference"] = {
                "rule_id": ref["id"],
                **_compare(pool_scores[r["id"]], pool_scores[ref["id"]], k),
            }
            if i + 1 < len(frs):
                nxt = frs[i + 1]
                rec["vs_next"] = {
                    "rule_id": nxt["id"],
                    **_compare(pool_scores[r["id"]], pool_scores[nxt["id"]], k),
                }
            else:
                rec["vs_next"] = None
    # recommendation inputs per family
    recs: dict[str, Any] = {}
    for fam, frs in families.items():
        entries = []
        for r in frs:
            rec = records[r["id"]]
            vn = rec["vs_next"]
            entries.append(
                {
                    "rule_id": r["id"],
                    "min_value": r["clauses"][0]["min"] if len(r["clauses"]) == 1 else None,
                    "eligible": rec["eligible"],
                    "expected_top_k_overlap": rec["bootstrap"].get("expected_top_k_overlap"),
                    "top_k": rec["bootstrap"].get("top_k"),
                    "pool_sufficient": rec["pool"]["sufficient"],
                    "spearman_vs_next": vn["spearman"]["rho"] if vn else None,
                    "overlap_vs_next": vn["overlap"] if vn else None,
                    "width_median": rec["bootstrap"].get("interval_width_median"),
                    "coverage_pct": rec["match_coverage"]["coverage_pct"],
                }
            )
        req = None
        if fam == cfg["recommendation"]["primary_family"]:
            req = _required_balls(prep, role, cfg["recommendation"])
        recs[fam] = recommend(entries, cfg["recommendation"], req)
    # appendix: top players at the reference rule of the primary family (proxy, flagged)
    prim = cfg["recommendation"]["primary_family"]
    ref_rule = next((r for r in rules if r["id"] == ref_ids.get(prim)), None)
    appendix = {
        "flag": "PROXY_NOT_PRESSURE",
        "reference_rule": ref_rule["id"] if ref_rule else None,
        "players": [],
    }
    detail: dict = {}
    if ref_rule:
        mask = eligible_mask(table, ref_rule)
        detail = bootstrap_rule(matrix, all_scores, mask, k, detail=True)
    if detail.get("evaluated"):
        sel_ids = prep.player_ids[mask]
        sel_tab = table[mask].reset_index(drop=True)
        for pos in detail["_base"]:
            pid = int(sel_ids[pos])
            appendix["players"].append(
                {
                    "player_id": pid,
                    "name": samples.names.get(pid),
                    "proxy_score": float(sel_tab.loc[pos, "score"]),
                    "ci95_low": float(detail["_lo"][pos]),
                    "ci95_high": float(detail["_hi"][pos]),
                    "top_k_freq": float(detail["_freq"][pos]),
                    "balls": float(sel_tab.loc[pos, "balls"]),
                    "matches": int(sel_tab.loc[pos, "matches"]),
                    "flag": "PROXY_NOT_PRESSURE",
                }
            )
    return {
        "result": {
            "observed_players": int(len(table)),
            "candidates": cands,
            "reference_rules": ref_ids,
            "rules": [records[r["id"]] for r in rules],
            "recommendation": {"primary_family": prim, "families": recs},
            "appendix": appendix,
        },
        "eligible_by_rule": eligible_by_rule,
    }


# --------------------------------------------------------------------------------- narrative


def generate_narrative(exp: dict, cfg: dict) -> dict[str, list[str]]:
    """Plain-language PROVISIONAL recommendation text built only from recommendation_inputs."""
    prim = cfg["recommendation"]["primary_family"]
    k = cfg["list_size"]
    out: dict[str, list[str]] = {}
    for fmt, roles in exp["recommendation_inputs"].items():
        lines = []
        for role, rec in roles.items():
            fam = rec["families"].get(prim)
            if fam is None:
                lines.append(f"PROVISIONAL {fmt} {role}: no observations, no recommendation.")
                continue
            ladder = {e["rule_id"]: e for e in fam["ladder"]}
            dw, hi = fam["data_weight_rule"], fam["highest_sufficient_pool_rule"]
            req = fam["required_balls_for_data_weight"]
            if dw:
                e = ladder[dw]
                txt = (
                    f"PROVISIONAL {fmt} {role}: {dw} (data outweighs the prior from about "
                    f"{req:.0f} balls); {e['eligible']} eligible, match coverage "
                    f"{e['coverage_pct']:.1f}%, bootstrap expected Top {e['top_k']} overlap "
                    f"{e['expected_top_k_overlap']:.1f}"
                )
            else:
                txt = (
                    f"PROVISIONAL {fmt} {role}: no {prim} rule reaches the data-weight floor "
                    f"with a sufficient pool"
                )
            if hi:
                txt += (
                    f"; the strictest rule with a sufficient pool is {hi} "
                    f"({ladder[hi]['eligible']} eligible)"
                )
            if fam["ladder"] and fam["ladder"][-1]["eligible"] < k:
                txt += f"; the strictest rule leaves fewer than {k} eligible"
            if not fam["stability_discriminates"]:
                txt += (
                    "; the generic stability checks pass at every step and do not discriminate, "
                    "so the choice rests on the single data-weight criterion and must be "
                    "re-confirmed with pressure samples in Phase 3"
                )
            if dw and ladder[dw]["expected_top_k_overlap"] < 0.5 * k:
                txt += (
                    f"; Top {k} membership is unstable under resampling (expected overlap "
                    f"below {0.5 * k:.0f}) even though the pool is sufficient"
                )
            lines.append(txt + ".")
        out[fmt] = lines
    return out
