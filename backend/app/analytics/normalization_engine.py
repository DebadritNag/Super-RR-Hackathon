"""IPL/T20I format scores, combination engine and weight sensitivity metrics (PROXY run).

Format scores are computed independently. A combined score exists only for players eligible in
both formats; everyone else gets NULL plus an explicit status. Nothing is zero-filled or imputed.
The ADJUSTED_ESTIMATE is a separate, clearly labelled column and never enters the default ranking.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.confidence_engine import ROLES, Prepared, player_table
from app.analytics.format_config import config_hash
from app.analytics.proxy_samples import ProxySamples
from app.analytics.ranking import movement, rank_players, spearman_common, topk_overlap
from app.analytics.reporting import PROXY_FIELDS
from app.analytics.shrinkage import zscore_within

FORMATS = ("IPL", "T20I")
ELIGIBLE = "ELIGIBLE"
OBSERVED_NOT_ELIGIBLE = "OBSERVED_NOT_ELIGIBLE"
NOT_OBSERVED = "NOT_OBSERVED"
BOTH = "BOTH_FORMATS_VALID"
IPL_ONLY = "SINGLE_FORMAT_IPL_ONLY"
T20I_ONLY = "SINGLE_FORMAT_T20I_ONLY"
NONE_VALID = "NO_VALID_FORMAT"
COMBINED_STATUSES = (BOTH, IPL_ONLY, T20I_ONLY, NONE_VALID)


def parse_level(label: str) -> float:
    """'P25' -> 25.0."""
    if not label.startswith("P"):
        raise ValueError(f"bad eligibility level: {label}")
    return float(label[1:])


def format_tables(
    samples: ProxySamples, level: str
) -> tuple[dict[str, dict[str, pd.DataFrame]], dict[str, dict[str, int]]]:
    """Per role and format: player table with `eligible` from the data-driven percentile rule
    on the balls measure (ceil of the level percentile over observed players of that format)."""
    pct = parse_level(level)
    frames = {"batter": samples.batter, "bowler": samples.bowler}
    tables: dict[str, dict[str, pd.DataFrame]] = {}
    thresholds: dict[str, dict[str, int]] = {}
    for role in ROLES:
        tables[role], thresholds[role] = {}, {}
        for fmt in FORMATS:
            rows = frames[role][frames[role]["format"] == fmt]
            if rows.empty:
                tables[role][fmt] = pd.DataFrame(
                    columns=["player_id", "balls", "score", "eligible"]
                )
                thresholds[role][fmt] = 1
                continue
            t = player_table(Prepared(rows, role))[["player_id", "balls", "score"]].copy()
            thr = max(1, int(math.ceil(np.percentile(t["balls"].to_numpy(), pct))))
            t["eligible"] = t["balls"] >= thr
            tables[role][fmt] = t
            thresholds[role][fmt] = thr
    return tables, thresholds


def build_player_frame(tables_role: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per player seen in either format with independent format statuses and z-scores."""
    parts = {}
    for fmt in FORMATS:
        t = tables_role[fmt].copy()
        t["z"] = np.nan
        if len(t) and t["eligible"].any():
            mask = t["eligible"].to_numpy(dtype=bool)
            z = zscore_within(t.loc[mask, "score"].to_numpy())
            t.loc[mask, "z"] = z
        t["status"] = np.where(t["eligible"], ELIGIBLE, OBSERVED_NOT_ELIGIBLE)
        parts[fmt] = t.rename(
            columns={c: f"{fmt.lower()}_{c}" for c in ("balls", "score", "eligible", "z", "status")}
        )[["player_id"] + [f"{fmt.lower()}_{c}" for c in ("balls", "score", "z", "status")]]
    df = parts["IPL"].merge(parts["T20I"], on="player_id", how="outer")
    df = df.sort_values("player_id", kind="mergesort").reset_index(drop=True)
    for fmt in ("ipl", "t20i"):
        df[f"{fmt}_status"] = df[f"{fmt}_status"].fillna(NOT_OBSERVED)
    ie = df["ipl_status"] == ELIGIBLE
    te = df["t20i_status"] == ELIGIBLE
    df["combined_status"] = np.select(
        [ie & te, ie & ~te, ~ie & te], [BOTH, IPL_ONLY, T20I_ONLY], default=NONE_VALID
    )
    return df


def combined_scores(df: pd.DataFrame, w_ipl: float, w_t20i: float) -> pd.Series:
    """w_ipl * z_ipl + w_t20i * z_t20i for BOTH_FORMATS_VALID players; NaN (NULL) otherwise."""
    both = df["combined_status"] == BOTH
    out = pd.Series(np.nan, index=df.index, dtype=float)
    out[both] = w_ipl * df.loc[both, "ipl_z"] + w_t20i * df.loc[both, "t20i_z"]
    return out


def adjusted_estimate(df: pd.DataFrame, w_ipl: float, w_t20i: float) -> pd.Series:
    """ADJUSTED_ESTIMATE: weights renormalised over the eligible formats. Separate from the
    combined score; single-format players only get their one available z-score."""
    num = pd.Series(0.0, index=df.index)
    den = pd.Series(0.0, index=df.index)
    for fmt, w in (("ipl", w_ipl), ("t20i", w_t20i)):
        ok = df[f"{fmt}_status"] == ELIGIBLE
        num[ok] += w * df.loc[ok, f"{fmt}_z"]
        den[ok] += w
    out = pd.Series(np.nan, index=df.index, dtype=float)
    ok = den > 0
    out[ok] = num[ok] / den[ok]
    return out


def _cfg_fields(c: dict, version: str, chash: str) -> dict:
    return {
        "config_id": c["id"],
        "config_version": version,
        "ipl_weight": c["ipl_weight"],
        "t20i_weight": c["t20i_weight"],
        "config_hash": chash,
    }


def _rows(df: pd.DataFrame, cols: list[str], extra: dict) -> list[dict]:
    out = []
    for rec in df[cols].to_dict("records"):
        row = {}
        for k, v in rec.items():
            if isinstance(v, float) and v != v:
                row[k] = None
            elif isinstance(v, (np.integer,)):
                row[k] = int(v)
            elif isinstance(v, (np.floating,)):
                row[k] = float(v)
            else:
                row[k] = v
        out.append({**extra, **row})
    return out


def _matrix(ranked: dict[str, pd.DataFrame], ids: list[str], k: int) -> dict:
    overlap, rho, n = [], [], []
    for a in ids:
        o_row, r_row, n_row = [], [], []
        for b in ids:
            o_row.append(topk_overlap(ranked[a]["player_id"], ranked[b]["player_id"], k))
            sp = spearman_common(ranked[a], ranked[b])
            r_row.append(sp["rho"])
            n_row.append(sp["n"])
        overlap.append(o_row)
        rho.append(r_row)
        n.append(n_row)
    return {"config_ids": ids, "top_k_overlap": overlap, "spearman": rho, "n_common": n}


def evaluate_role(frame: pd.DataFrame, cfg: dict, k: int, full: bool = True) -> dict[str, Any]:
    """Rank every configuration for one role and compare it with the default configuration."""
    version, chash = cfg["version"], config_hash(cfg)
    default_id = cfg["default_config_id"]
    both = frame[frame["combined_status"] == BOTH]
    ranked: dict[str, pd.DataFrame] = {}
    configs: dict[str, Any] = {}
    for c in cfg["configurations"]:
        sc = combined_scores(frame, c["ipl_weight"], c["t20i_weight"])
        pop = pd.DataFrame(
            {
                "player_id": frame["player_id"],
                "score": sc,
                "ipl_z": frame["ipl_z"],
                "t20i_z": frame["t20i_z"],
                "combined_status": frame["combined_status"],
            }
        )
        pop = pop[pop["combined_status"] == BOTH]
        ranked[c["id"]] = rank_players(pop, "score")
    default = ranked[default_id]
    for c in cfg["configurations"]:
        r = ranked[c["id"]]
        sp = spearman_common(default, r)
        entry: dict[str, Any] = {
            **_cfg_fields(c, version, chash),
            "n_ranked": int(len(r)),
            "top10_player_ids": [int(x) for x in r["player_id"].head(k)],
            "overlap_with_default": topk_overlap(default["player_id"], r["player_id"], k),
            "spearman_with_default": sp["rho"],
            "spearman_n": sp["n"],
            "movement_vs_default": movement(default, r, k),
        }
        if full:
            entry["ranking"] = _rows(
                r.rename(columns={"score": "combined_score"}),
                ["player_id", "rank", "combined_score", "ipl_z", "t20i_z", "combined_status"],
                _cfg_fields(c, version, chash),
            )
        configs[c["id"]] = entry
    ids = [c["id"] for c in cfg["configurations"]]
    out: dict[str, Any] = {
        "combined_population": int(len(both)),
        "configs": configs,
    }
    if full:
        out["pairwise"] = _matrix(ranked, ids, k)
    # degenerate configurations rank by one format's z-score within the same population
    deg = {}
    for cid, col in (("w100_0", "ipl_z"), ("w0_100", "t20i_z")):
        ref = rank_players(both[["player_id", col]].rename(columns={col: "score"}), "score")
        deg[cid] = {
            "ranks_equal_single_format_zscore_ranks": bool(
                list(ref["player_id"]) == list(ranked[cid]["player_id"])
            ),
            "population": int(len(both)),
        }
    out["degenerate_check"] = deg
    return out


def status_counts(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "players_total": int(len(frame)),
        "combined_status": {
            s: int((frame["combined_status"] == s).sum()) for s in COMBINED_STATUSES
        },
        "ipl_status": {
            s: int((frame["ipl_status"] == s).sum())
            for s in (ELIGIBLE, OBSERVED_NOT_ELIGIBLE, NOT_OBSERVED)
        },
        "t20i_status": {
            s: int((frame["t20i_status"] == s).sum())
            for s in (ELIGIBLE, OBSERVED_NOT_ELIGIBLE, NOT_OBSERVED)
        },
    }


def format_rankings(frame: pd.DataFrame, cfg: dict) -> dict[str, list[dict]]:
    """Format-specific rankings among players eligible in that format (config independent)."""
    meta = {
        "config_id": "FORMAT_SPECIFIC_NOT_WEIGHTED",
        "config_version": cfg["version"],
        "ipl_weight": None,
        "t20i_weight": None,
        "config_hash": config_hash(cfg),
    }
    out = {}
    for fmt in ("ipl", "t20i"):
        sub = frame[frame[f"{fmt}_status"] == ELIGIBLE]
        r = rank_players(
            sub[["player_id", f"{fmt}_score", f"{fmt}_z", f"{fmt}_balls"]].rename(
                columns={f"{fmt}_score": "score"}
            ),
            "score",
        ).rename(columns={f"{fmt}_z": "z", f"{fmt}_balls": "balls"})
        out[fmt.upper()] = _rows(r, ["player_id", "rank", "score", "z", "balls"], meta)
    return out


def adjusted_section(frame: pd.DataFrame, cfg: dict) -> dict[str, Any]:
    default = next(c for c in cfg["configurations"] if c["id"] == cfg["default_config_id"])
    est = adjusted_estimate(frame, default["ipl_weight"], default["t20i_weight"])
    sub = pd.DataFrame(
        {"player_id": frame["player_id"], "score": est, "combined_status": frame["combined_status"]}
    )
    sub = sub[sub["score"].notna()]
    r = rank_players(sub, "score").rename(columns={"score": "adjusted_estimate"})
    return {
        "label": "ADJUSTED_ESTIMATE",
        "note": (
            "Weights renormalised over the eligible formats of each player. Not a combined "
            "score, not used in the default ranking, and not comparable across single-format "
            "and two-format players."
        ),
        "config_id": default["id"],
        "n_players": int(len(r)),
        "ranking": _rows(
            r,
            ["player_id", "rank", "adjusted_estimate", "combined_status"],
            _cfg_fields(default, cfg["version"], config_hash(cfg)),
        ),
    }


def run_sensitivity(
    samples: ProxySamples | None,
    cfg: dict,
    list_size: int = 10,
    names: dict | None = None,
    tables: dict | None = None,
    thresholds: dict | None = None,
    robustness: dict | None = None,
    eligibility_label: str | None = None,
) -> dict[str, Any]:
    """Full Decision 1 sensitivity result (without provenance).

    Default: all-situation percentile eligibility from `samples`. Optional (additive) injection
    for Phase 3: `tables` ({role: {format: DataFrame[player_id, balls, score, eligible]}}) with
    their `thresholds`, and `robustness` ({label: (tables, thresholds)}) replace the all-situation
    tables; the combination engine, rankings and ADJUSTED_ESTIMATE section are unchanged.
    """
    levels = cfg.get("eligibility_levels", {"primary": "P25", "robustness": ["P10", "P50"]})
    primary = eligibility_label or levels["primary"]
    result: dict[str, Any] = {
        **PROXY_FIELDS,
        "decision": "Decision 1: IPL/T20I weight sensitivity",
        "config": {
            "version": cfg["version"],
            "status": cfg["status"],
            "default_config_id": cfg["default_config_id"],
            "default_flag": cfg["default_flag"],
            "config_hash": config_hash(cfg),
            "configurations": [
                {k: c[k] for k in ("id", "ipl_weight", "t20i_weight")}
                for c in cfg["configurations"]
            ],
        },
        "method_notes": {
            "eligibility": (
                "Weight independent: percentile rule on the balls measure per format and role "
                "(batter balls faced, bowler legal balls), recomputed from the data."
                if tables is None
                else "Weight independent: injected eligibility tables (Phase 3 pressure-specific)."
            ),
            "format_scores": "Independent per format; z-score within the format's eligible pool.",
            "combined": "Only BOTH_FORMATS_VALID players; others NULL with an explicit status.",
            "missing_formats": "Never zero-filled and never imputed.",
            "degenerate": (
                "100:0 and 0:100 use the same combined population as every other configuration, "
                "so their ranks equal the IPL or T20I z-score ranks within that population."
            ),
        },
        "eligibility_level": primary,
        "roles": {},
        "robustness": {},
    }
    injected = tables is not None
    if not injected:
        tables, thresholds = format_tables(samples, primary)
    result["thresholds"] = thresholds
    for role in ROLES:
        frame = build_player_frame(tables[role])
        res = evaluate_role(frame, cfg, list_size, full=True)
        res["status_counts"] = status_counts(frame)
        res["format_rankings"] = format_rankings(frame, cfg)
        res["adjusted_estimate"] = adjusted_section(frame, cfg)
        res["eligibility_change_summary"] = {
            "combined_population_by_config": {
                cid: e["n_ranked"] for cid, e in res["configs"].items()
            },
            "eligibility_identical_across_configs": len(
                {e["n_ranked"] for e in res["configs"].values()}
            )
            == 1,
            "single_format_players_excluded_from_combined": {
                IPL_ONLY: res["status_counts"]["combined_status"][IPL_ONLY],
                T20I_ONLY: res["status_counts"]["combined_status"][T20I_ONLY],
                NONE_VALID: res["status_counts"]["combined_status"][NONE_VALID],
            },
        }
        if names is not None:
            default_id = cfg["default_config_id"]
            res["technical_appendix"] = {
                "label": "PROXY_NOT_PRESSURE, technical appendix, not for publication",
                "default_config_top10": [
                    {"player_id": pid, "name": names.get(pid)}
                    for pid in res["configs"][default_id]["top10_player_ids"]
                ],
            }
        result["roles"][role] = res
    # eligibility level robustness
    base_pop = {}
    for role in ROLES:
        f0 = build_player_frame(tables[role])
        base_pop[role] = set(f0.loc[f0["combined_status"] == BOTH, "player_id"])
    if injected:
        rob_items = list((robustness or {}).items())
    else:
        rob_items = [(lv, format_tables(samples, lv)) for lv in levels.get("robustness", [])]
    for level, (t2, th2) in rob_items:
        rob: dict[str, Any] = {"thresholds": th2, "roles": {}}
        for role in ROLES:
            frame = build_player_frame(t2[role])
            res = evaluate_role(frame, cfg, list_size, full=False)
            pop = set(frame.loc[frame["combined_status"] == BOTH, "player_id"])
            res["status_counts"] = status_counts(frame)
            res["eligibility_change_vs_primary"] = {
                "primary_level": primary,
                "combined_population_primary": len(base_pop[role]),
                "combined_population_this_level": len(pop),
                "entering": len(pop - base_pop[role]),
                "leaving": len(base_pop[role] - pop),
            }
            rob["roles"][role] = res
        result["robustness"][level] = rob
    return result
