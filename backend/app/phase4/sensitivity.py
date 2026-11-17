"""Phase 4 Stages D and E: one-factor-at-a-time sensitivity and ranking-stability experiments.

Every analysis varies ONE factor and holds the others at the frozen defaults: shrinkage strength,
eligibility threshold, format weight, baseline variant. Definition sensitivity lives in
``definitions.py`` and is never crossed with these. All outputs are EXPERIMENTAL_NOT_VALIDATED
rankings of the PRE_TEST window (TRAIN + VALIDATION); nothing is padded to ten players.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics import ranking as rk
from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4 import shrink as sh
from app.phase4.baseline import STREAMS, BaselineSet, fit_baseline_set
from app.phase4.constants import SCOPE
from app.phase4.split import TestLock

BASELINE_VARIANTS: dict[str, dict[str, Any]] = {
    "B0": {},
    "B_coarse_L1": {"first_level": 1},
    "B_coarse_L2": {"first_level": 2},
    "B_no_format_offset": {"no_offset": True},
}


# ---------------------------------------------------------------- shared set-up
def build_cells(
    d: pd.DataFrame, bs: BaselineSet, defn: str, thr: dict[str, float], lock: TestLock
) -> dict[tuple[str, str], en.Cell]:
    """Primary-stream pressure cells for the four (format, role) pairs."""
    cells = {}
    for role in ("batter", "bowler"):
        stream, _ = en.PRIMARY[role]
        tagged = en.tag_rows(en.base_rows(d, bs, role, stream, lock), d, defn, thr)
        press = tagged[tagged["press"]]
        for comp in SCOPE:
            c = en.build_cell(press, comp, role, stream)
            if c is not None:
                cells[(comp, role)] = c
    return cells


def selection_cells(
    d: pd.DataFrame, bs: BaselineSet, defn: str, thr: dict[str, float], lock: TestLock
) -> list[dict[str, Any]]:
    """Cells (all four streams x two formats) for the TRAIN-vs-VALIDATION shrinkage choice."""
    out = []
    for role, stream, _ in STREAMS:
        rows = sc.residual_rows(d, bs, defn, thr, role, stream, lock)
        for comp in SCOPE:
            r = rows[rows["comp"] == comp]
            tpt = sh.player_table(sh.match_stats(r[r["period"] == "TRAIN"]))
            out.append(
                {
                    "cell": f"{role}:{stream}:{comp}",
                    "fit": sh.fit_cell(tpt),
                    "train_pt": tpt,
                    "val_ms": sh.match_stats(r[r["period"] == "VALIDATION"]),
                }
            )
    return out


def analysis_rules(
    cells: dict[tuple[str, str], en.Cell], decisions: dict[tuple[str, str], dict[str, Any]]
) -> dict[tuple[str, str], dict[str, Any]]:
    """Frozen analysis rule per cell with its window ratio W."""
    out = {}
    for key, cell in cells.items():
        rule = el.analysis_rule(decisions[key])
        rule["wr"] = el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
        out[key] = rule
    return out


def _point_top(score: np.ndarray, present: np.ndarray, ids: np.ndarray, k: int = 10) -> set:
    t = pd.DataFrame({"player_id": ids[present], "score": score[present]})
    return set(rk.top_k(t, k)) if len(t) else set()


# ---------------------------------------------------------------- shrinkage sensitivity
def shrinkage_sensitivity(
    cells: dict[tuple[str, str], en.Cell],
    fits: dict[tuple[str, str], dict[str, Any]],
    rules: dict[tuple[str, str], dict[str, Any]],
    gm: pd.Index,
    W: np.ndarray,
    val_cells: dict[tuple[str, str], dict[str, Any]],
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    """Per cell and shrinkage configuration: strength, data weight, ranking, interval, loss."""
    rows = []
    for (comp, role), cell in cells.items():
        sign = en.PRIMARY[role][1]
        rule = rules[(comp, role)]
        fit = fits[(comp, role)]
        w = en.cell_weights(cell, gm, W)
        ref_est = en.point_estimates(cell, fit, sh.DEFAULT_CONFIG)
        pool = el.eligible_mask(ref_est, rule, rule["wr"])
        ref_score = sign * ref_est["shrunk"].to_numpy()
        ref_top = _point_top(ref_score, pool, cell.players)
        loss = (
            sh.choose_shrinkage([val_cells[(comp, role)]], n_boot, seed)["losses"]
            if (comp, role) in val_cells
            else {}
        )
        for cfg in sh.CONFIGS:
            est = en.point_estimates(cell, fit, cfg)
            score = sign * est["shrunk"].to_numpy()
            nb, dr = en.draws(cell, est, w)
            present = pool[:, None] & (nb >= (rule["threshold_balls"] or 0) * rule["wr"])
            present &= np.isfinite(dr)
            rs = en.rank_summary(np.where(present, sign * dr, np.nan), score, pool)
            sm = en.summarize_ranking(rs)
            raw = est["mean"].to_numpy()
            if pool.sum() >= 3:
                rho = rk.spearman_common(
                    pd.DataFrame({"player_id": cell.players[pool], "score": score[pool]}),
                    pd.DataFrame({"player_id": cell.players[pool], "score": ref_score[pool]}),
                )["rho"]
            else:
                rho = None
            lo = np.nanpercentile(dr[pool], 2.5, axis=1) if pool.any() else np.array([])
            hi = np.nanpercentile(dr[pool], 97.5, axis=1) if pool.any() else np.array([])
            top = _point_top(score, pool, cell.players)
            rows.append(
                {
                    "format": comp,
                    "role": role,
                    "stream": cell.stream,
                    "shrinkage_config": cfg,
                    "k": float(est["k"].iloc[0]),
                    "tau2": float(est["tau2"].iloc[0]),
                    "floor_hit": bool(est["floor_hit"].iloc[0]),
                    "eligibility_label": rule["label"],
                    "pool_size": int(pool.sum()),
                    "median_data_weight_pool": float(np.median(est["B"].to_numpy()[pool]))
                    if pool.any()
                    else None,
                    "mean_abs_shift_from_raw_pool": float(
                        np.mean(np.abs(est["shrunk"].to_numpy()[pool] - raw[pool]))
                    )
                    if pool.any()
                    else None,
                    "spearman_vs_shrink_eb": rho,
                    "top10_overlap_vs_shrink_eb": len(top & ref_top),
                    "top10_trivial_full_pool": bool(pool.sum() <= 10),
                    "median_interval_width_pool": float(np.nanmedian(hi - lo))
                    if pool.any()
                    else None,
                    "expected_top10_overlap_bootstrap": sm["expected_top10_overlap"],
                    "mean_bootstrap_spearman": sm["mean_spearman"],
                    "validation_loss_cell": loss.get(cfg, {}).get("loss"),
                    "validation_loss_diff_vs_eb": loss.get(cfg, {}).get("diff_vs_eb"),
                    "validation_loss_bootstrap_se": loss.get(cfg, {}).get("bootstrap_se"),
                    "choosable_as_primary": cfg in sh.CHOOSABLE,
                }  # fmt: skip
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- ranking stability (Stage E)
def ranking_stability(
    cells: dict[tuple[str, str], en.Cell],
    fits: dict[tuple[str, str], dict[str, Any]],
    rules: dict[tuple[str, str], dict[str, Any]],
    gm: pd.Index,
    W: np.ndarray,
    cfg: str,
    threshold_rows: dict[tuple[str, str], list[dict[str, Any]]],
    shrink_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Baseline-configuration distributions plus threshold- and shrinkage-variant summaries."""
    players, summ, thr_var = [], [], []
    for (comp, role), cell in cells.items():
        sign = en.PRIMARY[role][1]
        rule = rules[(comp, role)]
        est = en.point_estimates(cell, fits[(comp, role)], cfg)
        w = en.cell_weights(cell, gm, W)
        nb, dr = en.draws(cell, est, w)
        pool = el.eligible_mask(est, rule, rule["wr"])
        thr_b = (rule["threshold_balls"] or 0) * rule["wr"]
        present = pool[:, None] & (nb >= thr_b) & np.isfinite(dr)
        rs = en.rank_summary(np.where(present, sign * dr, np.nan), sign * est["shrunk"].to_numpy(),
                             pool)  # fmt: skip
        tab = en.player_ranking_table(cell, est, rs, sign, pool)
        tab.insert(0, "scope", comp)
        tab.insert(1, "role", role)
        tab["eligibility_label"] = rule["label"]
        players.append(tab)
        summ.append({"scope": comp, "role": role, "eligibility_label": rule["label"],
                     "threshold_balls": rule["threshold_balls"], **en.summarize_ranking(rs)})  # fmt: skip
        base_score = sign * est["shrunk"].to_numpy()
        base_top = _point_top(base_score, pool, cell.players)
        for r in threshold_rows.get((comp, role), []):
            t = r["threshold_balls"]
            p2 = (est["n"].to_numpy() >= t * rule["wr"]) & np.isfinite(base_score)
            top2 = _point_top(base_score, p2, cell.players)
            both = pool & p2
            thr_var.append(
                {
                    "scope": comp, "role": role, "threshold_balls": t, "source": r["source"],
                    "is_analysis_threshold": t == rule["threshold_balls"],
                    "pool_size": int(p2.sum()),
                    "top10_overlap_with_analysis_pool": len(top2 & base_top),
                    "trivial_full_pool": bool(p2.sum() <= 10),
                    "common_players_with_analysis_pool": int(both.sum()),
                    "expected_top10_overlap_bootstrap": r.get("expected_top10_overlap"),
                    "bootstrap_mean_jaccard_top10": r.get("boot_mean_jaccard_top10"),
                    "bootstrap_mean_spearman": r.get("boot_mean_spearman"),
                    "reproducibility_spearman": r.get("reproducibility_spearman"),
                }
            )  # fmt: skip
    return {
        "players": pd.concat(players, ignore_index=True) if players else pd.DataFrame(),
        "summary": pd.DataFrame(summ),
        "threshold_variants": pd.DataFrame(thr_var),
        "shrinkage_variants": shrink_df[
            ["format", "role", "shrinkage_config", "pool_size", "top10_overlap_vs_shrink_eb",
             "spearman_vs_shrink_eb", "expected_top10_overlap_bootstrap",
             "mean_bootstrap_spearman", "top10_trivial_full_pool"]
        ].copy(),
    }  # fmt: skip


# ---------------------------------------------------------------- format weights
def format_weight_analysis(
    cells: dict[tuple[str, str], en.Cell],
    fits: dict[tuple[str, str], dict[str, Any]],
    rules: dict[tuple[str, str], dict[str, Any]],
    gm: pd.Index,
    W: np.ndarray,
    cfg: str,
    weight_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Eight-configuration format-weight sensitivity over ONE shared eligibility rule set.

    The combined pool is the players eligible in BOTH formats under the same frozen rules for
    every configuration. A player eligible in one format is never zero-filled into a combination.
    """
    rows, pair_rows, players, singles = [], [], [], []
    default_id = weight_cfg["default_config_id"]
    for role in ("batter", "bowler"):
        sign = en.PRIMARY[role][1]
        if ("IPL", role) not in cells or ("T20I", role) not in cells:
            continue
        parts = {}
        for comp in SCOPE:
            cell = cells[(comp, role)]
            est = en.point_estimates(cell, fits[(comp, role)], cfg)
            rule = rules[(comp, role)]
            w = en.cell_weights(cell, gm, W)
            nb, dr = en.draws(cell, est, w)
            pool = el.eligible_mask(est, rule, rule["wr"])
            thr_b = (rule["threshold_balls"] or 0) * rule["wr"]
            ok = pool[:, None] & (nb >= thr_b) & np.isfinite(dr)
            parts[comp] = {"cell": cell, "est": est, "dr": np.where(ok, sign * dr, np.nan),
                           "pool": pool, "score": sign * est["shrunk"].to_numpy(), "rule": rule}  # fmt: skip
            rs = en.rank_summary(parts[comp]["dr"], parts[comp]["score"], pool)
            sm = en.summarize_ranking(rs)
            singles.append({"role": role, "scope": f"{comp}_ONLY", "eligibility_label": rule["label"],
                            "threshold_balls": rule["threshold_balls"], **sm})  # fmt: skip
        ids_i, ids_t = parts["IPL"]["cell"].players, parts["T20I"]["cell"].players
        both = np.intersect1d(ids_i[parts["IPL"]["pool"]], ids_t[parts["T20I"]["pool"]])
        ix_i, ix_t = pd.Index(ids_i).get_indexer(both), pd.Index(ids_t).get_indexer(both)
        s_i, s_t = parts["IPL"]["score"][ix_i], parts["T20I"]["score"][ix_t]
        d_i, d_t = parts["IPL"]["dr"][ix_i], parts["T20I"]["dr"][ix_t]
        n_boot = d_i.shape[1] if d_i.ndim == 2 and d_i.size else 0
        ref = next(c for c in weight_cfg["configurations"] if c["id"] == default_id)
        ref_point = ref["ipl_weight"] * s_i + ref["t20i_weight"] * s_t
        ref_df = pd.DataFrame({"player_id": both, "score": ref_point})
        point_scores = {}
        for c in weight_cfg["configurations"]:
            wi, wt = c["ipl_weight"], c["t20i_weight"]
            point = wi * s_i + wt * s_t
            point_scores[c["id"]] = point
            df = pd.DataFrame({"player_id": both, "score": point})
            row: dict[str, Any] = {
                "role": role, "config_id": c["id"], "ipl_weight": wi, "t20i_weight": wt,
                "is_default_provisional": c["id"] == default_id,
                "pool_definition": "eligible in both formats under the same frozen rules",
                "pool_size": int(len(both)),
                "ipl_eligibility_label": parts["IPL"]["rule"]["label"],
                "t20i_eligibility_label": parts["T20I"]["rule"]["label"],
                "ipl_threshold_balls": parts["IPL"]["rule"]["threshold_balls"],
                "t20i_threshold_balls": parts["T20I"]["rule"]["threshold_balls"],
            }  # fmt: skip
            if len(both) >= 3:
                k = min(10, len(both))
                row["top10_overlap_vs_default"] = rk.topk_overlap(
                    rk.top_k(df, k), rk.top_k(ref_df, k), k
                )
                row["top10_size"] = k
                row["top10_trivial_full_pool"] = bool(len(both) <= 10)
                row["spearman_vs_default"] = rk.spearman_common(df, ref_df)["rho"]
                mv = rk.movement(ref_df, df)
                row["mean_abs_rank_change_vs_default"] = mv["mean_abs_change"]
                row["max_abs_rank_change_vs_default"] = mv["max_abs_change"]
            if len(both) and n_boot:
                with np.errstate(invalid="ignore"):
                    t_i = np.where(wi > 0, wi * d_i, 0.0)
                    t_t = np.where(wt > 0, wt * d_t, 0.0)
                    okb = (np.isfinite(d_i) | (wi == 0)) & (np.isfinite(d_t) | (wt == 0))
                    comb = np.where(okb, np.nan_to_num(t_i) + np.nan_to_num(t_t), np.nan)
                rs = en.rank_summary(comb, point, np.ones(len(both), dtype=bool))
                row.update(
                    {
                        f"bootstrap_{k}": v
                        for k, v in en.summarize_ranking(rs).items()
                        if k
                        in (
                            "expected_top10_overlap",
                            "mean_jaccard",
                            "mean_spearman",
                            "spearman_p2_5",
                            "spearman_p97_5",
                        )
                    }  # fmt: skip
                )
                tab = pd.DataFrame(
                    {"role": role, "config_id": c["id"], "player_id": both,
                     "point_score": point, "point_rank": rs["point_rank"],
                     "top10_inclusion_prob": rs["inclusion_prob"], "rank_lo": rs["rank_lo"],
                     "rank_median": rs["rank_med"], "rank_hi": rs["rank_hi"]}
                )  # fmt: skip
                players.append(tab.sort_values(["point_rank", "player_id"]))
            rows.append(row)
        ids = [c["id"] for c in weight_cfg["configurations"]]
        for a in ids:
            for b in ids:
                rho = (
                    rk.spearman_common(
                        pd.DataFrame({"player_id": both, "score": point_scores[a]}),
                        pd.DataFrame({"player_id": both, "score": point_scores[b]}),
                    )["rho"]
                    if len(both) >= 3
                    else None
                )
                pair_rows.append({"role": role, "config_a": a, "config_b": b, "spearman": rho})
    return {
        "configs": pd.DataFrame(rows),
        "pairwise": pd.DataFrame(pair_rows),
        "players": pd.concat(players, ignore_index=True) if players else pd.DataFrame(),
        "single_format": pd.DataFrame(singles),
    }


# ---------------------------------------------------------------- baseline alternatives
def baseline_alternatives(
    d: pd.DataFrame,
    defn: str,
    thr: dict[str, float],
    cfg: str,
    rules: dict[tuple[str, str], dict[str, Any]],
    ref_cells: dict[tuple[str, str], en.Cell],
    lock: TestLock,
    params: dict[str, Any],
) -> pd.DataFrame:
    """Alternative baselines fitted on TRAIN only; VALIDATION fit and score agreement with B0."""
    out = []
    ref_est = {key: en.point_estimates(c, c.fit(), cfg) for key, c in ref_cells.items()}
    for name, extra in BASELINE_VARIANTS.items():
        bs = fit_baseline_set(d, {**params, **extra}, version=f"p4_{name}")
        cells = build_cells(d, bs, defn, thr, lock)
        for role in ("batter", "bowler"):
            stream, sign = en.PRIMARY[role]
            allr = en.base_rows(d, bs, role, stream, lock)
            val = allr[allr["period"] == "VALIDATION"]
            for comp in SCOPE:
                v = val[val["comp"] == comp]
                row: dict[str, Any] = {
                    "baseline": name, "format": comp, "role": role, "stream": stream,
                    "validation_rows": int(len(v)),
                    "validation_mean_residual": float(v["resid"].mean()),
                    "validation_rmse": float(np.sqrt((v["resid"] ** 2).mean())),
                    "validation_mae": float(v["resid"].abs().mean()),
                }  # fmt: skip
                key = (comp, role)
                if key in cells and key in ref_cells:
                    est = en.point_estimates(cells[key], cells[key].fit(), cfg)
                    rule = rules[key]
                    a = est["n"].to_numpy() >= (rule["threshold_balls"] or 0) * rule["wr"]
                    if rule["threshold_balls"] is None:
                        a = np.zeros(len(est), dtype=bool)
                    mine = pd.Series(sign * est["shrunk"].to_numpy(), index=cells[key].players)[a]
                    ref = pd.Series(
                        sign * ref_est[key]["shrunk"].to_numpy(), index=ref_cells[key].players
                    )
                    ref = ref[el.eligible_mask(ref_est[key], rule, rule["wr"])]
                    common = mine.index.intersection(ref.index)
                    row["pool_size_B0"] = int(len(ref))
                    row["pool_size_variant"] = int(len(mine))
                    row["common_players"] = int(len(common))
                    if len(common) >= 3:
                        rho = rk.spearman_common(
                            pd.DataFrame({"player_id": common, "score": mine[common].to_numpy()}),
                            pd.DataFrame({"player_id": common, "score": ref[common].to_numpy()}),
                        )["rho"]
                        row["spearman_vs_B0"] = rho
                    k = min(10, len(common))
                    if k:
                        ta = rk.top_k(
                            pd.DataFrame({"player_id": ref.index, "score": ref.to_numpy()}), k
                        )
                        tb = rk.top_k(
                            pd.DataFrame({"player_id": mine.index, "score": mine.to_numpy()}), k
                        )
                        row["top10_overlap_vs_B0"] = rk.topk_overlap(ta, tb, k)
                        row["top10_size"] = k
                        row["top10_trivial_full_pool"] = bool(len(ref) <= 10 and len(mine) <= 10)
                out.append(row)
    return pd.DataFrame(out)
