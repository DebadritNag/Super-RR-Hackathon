"""Pressure-specific eligibility experiment (Phase 3 prep, Stage 5). EXPLORATORY_NOT_VALIDATED.

Builds per (format, player, match) sufficient statistics from PRESSURE deliveries only, with the
actual-minus-expected residual of the Stage 4 baseline as the measured stream, and feeds them to the
Phase 2.5 threshold harness (`confidence_engine`) unchanged. Batters and bowlers are evaluated
independently, formats are evaluated independently. Nothing here ranks players for publication:
the residual score exists only so that ranking stability and interval widths can be measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics import baseline_engine as be
from app.analytics import confidence_engine as ce
from app.analytics import pressure_features as pf
from app.analytics.proxy_samples import ProxySamples

STATUS = {
    "status": "EXPLORATORY_NOT_VALIDATED",
    "official_ranking": False,
    "not_for_publication": True,
}
ROLES = ("batter", "bowler")
FORMATS = tuple(pf.SCOPE)
BATTER_STREAM = ("runs", False)
BOWLER_STREAMS = (("charged", False), ("wkt", True))


def load_rules(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ definitions and flags
def definitions(cfg: dict) -> list[dict]:
    """Pre-declared grid of pressure definitions (context x quantile). No selection here."""
    g = cfg["definition_grid"]
    return [
        {"id": f"{c}|q{q}", "ctx": c, "q": float(q), "view": g["view"]}
        for q in g["q"]
        for c in g["contexts"]
    ]


def definition_flag(flags: dict[str, np.ndarray], cfg: dict, definition: dict, role: str):
    """Boolean flag over the state frame: union over IPL/T20I of the Stage 3 candidate flag.

    'any' is the OR of the chase and innings-1 flags at the same q. Each comp uses its own
    quantile threshold (Stage 3 convention), so the union does not mix thresholds across comps.
    """
    g = cfg["definition_grid"]
    ctxs = ["chase", "inn1"] if definition["ctx"] == "any" else [definition["ctx"]]
    out = None
    for ctx in ctxs:
        sig = g["batter_signal"][ctx] if role == "batter" else g["bowler_signal"]
        for comp in FORMATS:
            f = flags[f"a|{ctx}|{comp}|{role}|{sig}|{g['view']}|{definition['q']}"]
            out = f.copy() if out is None else (out | f)
    return out


def context_matches(df: pd.DataFrame, ctx: str) -> dict[str, int]:
    """Matches in which pressure of this context could occur, per format (coverage denominator)."""
    if ctx == "chase":
        pop = df["chase_pop"]
    elif ctx == "inn1":
        pop = df["inn1_pop"]
    else:
        pop = df["chase_pop"] | df["inn1_pop"]
    return {
        c: int(df.loc[pop & (df["competition_type"] == c), "match_id"].nunique()) for c in FORMATS
    }


# ------------------------------------------------------------------ residuals
def lpo_residual(
    d: pd.DataFrame,
    stream: str,
    binary: bool,
    params: dict,
    pressure: np.ndarray | None = None,
) -> np.ndarray:
    """Actual minus leave-player-out expected value for every row of a batter/bowler frame."""
    y = d[stream].to_numpy(dtype=float)
    lv = be.level_codes(d, pressure)
    inn = pd.factorize(d["inn_key"])[0]
    pl = pd.factorize(d["competition_type"] + "|" + d["player_id"].astype(str))[0]
    e = be.expected_values(
        y,
        lv,
        inn,
        pl,
        binary,
        min_cell_innings=int(params["min_cell_innings"]),
        tau2_floor=float(params["tau2_floor"]),
    )
    return y - e["expected"]


# ------------------------------------------------------------------ pressure samples
def _agg(t: pd.DataFrame, streams: dict[str, str]) -> pd.DataFrame:
    g = t.groupby(["format", "player_id", "match_id"], sort=True)
    out = g.agg(
        n=("one", "sum"), legal_balls=("legal", "sum"), innings=("inn", "nunique")
    ).reset_index()
    for name, col in streams.items():
        s = g[col].sum().to_numpy()
        s2 = g[col + "_sq"].sum().to_numpy()
        out[f"{name}_sum"] = s
        out[f"{name}_sum2"] = s2
    for c in ("player_id", "match_id"):
        out[c] = out[c].astype("int64")
    for c in ("n", "legal_balls", "innings"):
        out[c] = out[c].astype("int64")
    return out


def batter_samples(bat: pd.DataFrame, flag: np.ndarray, resid: np.ndarray) -> pd.DataFrame:
    """Pressure samples of batters. `flag`/`resid` are aligned to the rows of `bat`."""
    m = np.asarray(flag, dtype=bool)
    t = pd.DataFrame(
        {
            "format": bat["competition_type"].to_numpy()[m],
            "player_id": bat["player_id"].to_numpy()[m],
            "match_id": bat["match_id"].to_numpy()[m],
            "inn": bat["inn_key"].to_numpy()[m],
            "one": 1,
            "legal": (bat["den_legal_inc"].to_numpy()[m] == 1).astype(int),
            "r": np.asarray(resid, dtype=float)[m],
        }
    )
    t["r_sq"] = t["r"] ** 2
    return _agg(t, {"runs": "r"})


def bowler_samples(
    bowl: pd.DataFrame, flag: np.ndarray, resid_charged: np.ndarray, resid_wkt: np.ndarray
) -> pd.DataFrame:
    m = np.asarray(flag, dtype=bool)
    t = pd.DataFrame(
        {
            "format": bowl["competition_type"].to_numpy()[m],
            "player_id": bowl["player_id"].to_numpy()[m],
            "match_id": bowl["match_id"].to_numpy()[m],
            "inn": bowl["inn_key"].to_numpy()[m],
            "one": 1,
            "legal": (bowl["den_legal_inc"].to_numpy()[m] == 1).astype(int),
            "c": np.asarray(resid_charged, dtype=float)[m],
            "w": np.asarray(resid_wkt, dtype=float)[m],
        }
    )
    t["c_sq"] = t["c"] ** 2
    t["w_sq"] = t["w"] ** 2
    return _agg(t, {"econ": "c", "wkt": "w"})


def residual_sets(
    bat: pd.DataFrame,
    bowl: pd.DataFrame,
    fb: np.ndarray | None,
    fw: np.ndarray | None,
    params: dict,
) -> dict[str, np.ndarray]:
    """Residual arrays for one baseline: per-candidate (flags given) or B0 (flags None)."""
    return {
        "runs": lpo_residual(bat, "runs", False, params, fb),
        "charged": lpo_residual(bowl, "charged", False, params, fw),
        "wkt": lpo_residual(bowl, "wkt", True, params, fw),
    }


def window_for(matches_by_fmt: dict[str, int]) -> dict[str, dict]:
    return {f: {"matches_with_deliveries": int(n)} for f, n in matches_by_fmt.items()}


# ------------------------------------------------------------------ Phase 2.5 comparison
def phase25_thresholds(report: dict) -> dict[str, dict[str, dict]]:
    """All-situation data-weight thresholds from the Phase 2.5 experiment JSON (read only)."""
    out: dict[str, dict[str, dict]] = {}
    for fmt, roles in report["recommendation_inputs"].items():
        out[fmt] = {}
        for role, rec in roles.items():
            fam = rec["families"][rec["primary_family"]]
            rid = fam["data_weight_rule"]
            ent = next((e for e in fam["ladder"] if e["rule_id"] == rid), None)
            out[fmt][role] = {
                "rule_id": rid,
                "min_balls": None if ent is None else ent["min_value"],
                "eligible_all_situation": None if ent is None else ent["eligible"],
                "required_balls_for_data_weight": fam["required_balls_for_data_weight"],
            }
    return out


def players_passing(table: pd.DataFrame, min_balls: float | None) -> int | None:
    if min_balls is None:
        return None
    return int((table["balls"] >= min_balls).sum())


# ------------------------------------------------------------------ per-definition experiment
def summarize_cell(
    exp_cell: dict, rec_inputs: dict, prep: ce.Prepared, table: pd.DataFrame, cfg: dict
) -> dict[str, Any]:
    """Population-level and recommendation summary of one (definition, format, role) cell."""
    prim = cfg["recommendation"]["primary_family"]
    fam = rec_inputs["families"][prim]
    dw = fam["data_weight_rule"]
    rules = {r["rule_id"]: r for r in exp_cell["rules"]}
    cell: dict[str, Any] = {
        "observed_players": int(len(table)),
        "pressure_unit_rows": int(prep.n.sum()),
        "pressure_matches": int(len(prep.match_ids)),
        "required_balls_for_data_weight": fam["required_balls_for_data_weight"],
        "data_weight_rule": dw,
        "highest_sufficient_pool_rule": fam["highest_sufficient_pool_rule"],
        "stability_discriminates": fam["stability_discriminates"],
        "recommended": None,
    }
    if dw is None:
        cell["verdict"] = "NO_RULE_WITH_SUFFICIENT_POOL_AT_DATA_WEIGHT_FLOOR"
        return cell
    rec = rules[dw]
    mask = ce.eligible_mask(table, {"clauses": rec["clauses"]})
    sel = table[mask]
    rows_in = mask[prep.pidx] if len(prep.pidx) else np.zeros(0, bool)
    ladder = {e["rule_id"]: e for e in fam["ladder"]}
    bs = rec["bootstrap"]
    cell["verdict"] = "RULE_FOUND_PROVISIONAL_NOT_VALIDATED"
    cell["recommended"] = {
        "rule_id": dw,
        "min_balls": rec["clauses"][0]["min"],
        "eligible_players": int(mask.sum()),
        "pool": rec["pool"],
        "pressure_unit_rows": int(prep.n[rows_in].sum()),
        "pressure_balls_measure": float(sel["balls"].sum()),
        "distinct_matches": rec["match_coverage"]["matches_covered"],
        "match_coverage_pct": rec["match_coverage"]["coverage_pct"],
        "innings_sum": float(sel["innings"].sum()),
        "n_eff_shrink": ce.describe(sel["n_eff_shrink"]),
        "n_eff_kish": ce.describe(sel["n_eff_kish"]),
        "n_eff_shrink_total": float(sel["n_eff_shrink"].sum()),
        "bootstrap": {k: v for k, v in bs.items() if not k.startswith("_")},
        "spearman_vs_next": ladder[dw].get("spearman_vs_next"),
        "overlap_vs_next": ladder[dw].get("overlap_vs_next"),
        "fewer_than_list_size": rec["pool"]["fewer_than_list_size"],
    }
    return cell


def rule_uncertainty(
    prep: ce.Prepared, mask: np.ndarray, rng: np.random.Generator, n_boot: int, role: str
) -> dict[str, Any]:
    """Per-player 95% bootstrap interval summary for the eligible set (match resampling).

    Aggregate only: no player is listed. For batters the score is 100 x shrunk AvE runs per ball,
    so 'interval excludes zero' is meaningful; the bowler z-composite has no natural zero.
    """
    m = int(mask.sum())
    if m == 0:
        return {"eligible": 0, "evaluated": False}
    full = ce.score_from_agg(role, prep.aggregate())["score"]
    mat = ce.bootstrap_score_matrix(prep, rng, n_boot)
    sub = mat[:, mask]
    lo, hi = np.percentile(sub, [2.5, 97.5], axis=0)
    out: dict[str, Any] = {
        "eligible": m,
        "evaluated": True,
        "n_boot": int(n_boot),
        "ci_width_median": float(np.median(hi - lo)),
        "ci_width_p90": float(np.percentile(hi - lo, 90)),
        "point_inside_interval_share": float(((full[mask] >= lo) & (full[mask] <= hi)).mean()),
    }
    if role == "batter":
        out["interval_excludes_zero_share"] = float(((lo > 0) | (hi < 0)).mean())
        out["score_unit"] = "100 x runs per ball, actual minus expected"
    else:
        out["interval_excludes_zero_share"] = None
        out["score_unit"] = "z-composite, no natural zero"
    return out


def run_definition(
    definition: dict,
    bat: pd.DataFrame,
    bowl: pd.DataFrame,
    fb_full: np.ndarray,
    fw_full: np.ndarray,
    cfg: dict,
    matches_by_fmt: dict[str, int],
    params: dict,
    n_boot: int | None = None,
    b0: dict[str, np.ndarray] | None = None,
) -> dict[str, Any]:
    """Run the Phase 2.5 threshold harness on the pressure samples of one definition.

    fb_full / fw_full are flags over the full state frame already restricted to the rows of `bat`
    / `bowl` (aligned to their rows). The per-candidate baseline is primary; B0 is a sensitivity.
    """
    res_c = residual_sets(bat, bowl, fb_full, fw_full, params)
    bsamp = batter_samples(bat, fb_full, res_c["runs"])
    wsamp = bowler_samples(bowl, fw_full, res_c["charged"], res_c["wkt"])
    samples = ProxySamples(bsamp, wsamp, window_for(matches_by_fmt), {}, [])
    dist, exp = ce.run_experiment(samples, cfg, n_boot)
    exp.pop("technical_appendix", None)
    exp.pop("narrative", None)
    exp.pop("rules", None)
    summary: dict[str, Any] = {}
    unc: dict[str, Any] = {}
    seeds = np.random.SeedSequence(int(cfg["seed"]) + 1).spawn(len(FORMATS) * len(ROLES))
    si = 0
    tables: dict[tuple[str, str], pd.DataFrame] = {}
    for fmt in FORMATS:
        summary[fmt], unc[fmt] = {}, {}
        for role in ROLES:
            frame = samples.batter if role == "batter" else samples.bowler
            rows = frame[frame["format"] == fmt]
            prep = ce.Prepared(rows, role)
            table = ce.player_table(prep)
            tables[(fmt, role)] = table
            cell = summarize_cell(
                exp["formats"][fmt][role], exp["recommendation_inputs"][fmt][role], prep, table, cfg
            )
            summary[fmt][role] = cell
            rec = cell["recommended"]
            rng = np.random.default_rng(seeds[si])
            si += 1
            if rec is not None:
                mask = table["balls"].to_numpy() >= rec["min_balls"]
                unc[fmt][role] = rule_uncertainty(
                    prep, mask, rng, int(n_boot or cfg["n_boot"]), role
                )
            else:
                unc[fmt][role] = {"evaluated": False, "reason": cell["verdict"]}
    out = {
        "definition": definition,
        "combined_both_formats": combined_both_formats(summary, tables, cfg["list_size"]),
        "pressure_rows": {
            "batter": int(np.asarray(fb_full, bool).sum()),
            "bowler": int(np.asarray(fw_full, bool).sum()),
        },
        "pressure_unit_rows_by_cell": {
            fmt: {r: summary[fmt][r]["pressure_unit_rows"] for r in ROLES} for fmt in FORMATS
        },
        "baseline": "per-candidate baseline, leave-player-out (primary)",
        "summary": summary,
        "uncertainty": unc,
        "distributions": dist["formats"],
        "experiment": exp,
    }
    if b0 is not None:
        out["baseline_sensitivity_b0"] = baseline_sensitivity(
            bat, bowl, fb_full, fw_full, b0, summary, samples, cfg
        )
    out["_tables"] = tables  # stripped before writing
    out["_samples"] = samples
    return out


def combined_both_formats(summary: dict, tables: dict, list_size: int) -> dict[str, Any]:
    """Players eligible in BOTH formats at the recommended rules (no padding, no imputation)."""
    out: dict[str, Any] = {}
    for role in ROLES:
        ids = []
        for fmt in FORMATS:
            rec = summary[fmt][role]["recommended"]
            if rec is None:
                ids = None
                break
            t = tables[(fmt, role)]
            ids.append(set(t.loc[t["balls"] >= rec["min_balls"], "player_id"].astype(int)))
        if ids is None:
            out[role] = {"eligible_both_formats": None, "fewer_than_list_size": None}
        else:
            n = len(ids[0] & ids[1])
            out[role] = {"eligible_both_formats": n, "fewer_than_list_size": n < list_size}
    return out


def baseline_sensitivity(bat, bowl, fb, fw, b0, summary, samples, cfg) -> dict[str, Any]:
    """Spearman of eligible-player scores under B0 residuals versus the per-candidate baseline."""
    from app.analytics.ranking import spearman_common

    bs0 = batter_samples(bat, fb, b0["runs"])
    ws0 = bowler_samples(bowl, fw, b0["charged"], b0["wkt"])
    out: dict[str, Any] = {}
    for fmt in FORMATS:
        out[fmt] = {}
        for role in ROLES:
            rec = summary[fmt][role]["recommended"]
            if rec is None:
                out[fmt][role] = {"evaluated": False}
                continue
            a_rows = samples.batter if role == "batter" else samples.bowler
            b_rows = bs0 if role == "batter" else ws0
            pa = ce.player_table(ce.Prepared(a_rows[a_rows["format"] == fmt], role))
            pb = ce.player_table(ce.Prepared(b_rows[b_rows["format"] == fmt], role))
            ea = pa[pa["balls"] >= rec["min_balls"]][["player_id", "score"]]
            eb = pb[pb["player_id"].isin(ea["player_id"])][["player_id", "score"]]
            sp = spearman_common(ea, eb)
            out[fmt][role] = {
                "evaluated": True,
                "eligible": int(len(ea)),
                "spearman_b0_vs_candidate": sp["rho"],
                "n": sp["n"],
            }
    return out


# ------------------------------------------------------------------ selection (population level)
def select_definition(results: list[dict], cfg: dict) -> dict[str, Any]:
    """Pre-declared rule: viable = a data-weight rule with a sufficient pool in all four cells.

    Highest q wins; ties go to the larger pressure population. Only population-level quantities
    (rule existence, eligible counts, pressure unit rows) are used, never scores or rankings.
    """
    rows = []
    for r in results:
        cells = [r["summary"][f][ro] for f in FORMATS for ro in ROLES]
        viable = all(c["recommended"] is not None for c in cells)
        pop = int(sum(c["pressure_unit_rows"] for c in cells))
        rows.append(
            {
                "id": r["definition"]["id"],
                "ctx": r["definition"]["ctx"],
                "q": r["definition"]["q"],
                "viable": bool(viable),
                "pressure_unit_rows_total": pop,
                "cells_with_rule": int(sum(c["recommended"] is not None for c in cells)),
                "eligible_by_cell": {
                    f"{f}|{ro}": (
                        None
                        if r["summary"][f][ro]["recommended"] is None
                        else r["summary"][f][ro]["recommended"]["eligible_players"]
                    )
                    for f in FORMATS
                    for ro in ROLES
                },
            }
        )
    viable = [x for x in rows if x["viable"]]
    chosen = None
    if viable:
        chosen = sorted(viable, key=lambda x: (-x["q"], -x["pressure_unit_rows_total"], x["id"]))[0]
    return {
        "rule": cfg["selection_rule"]["text"],
        "definitions_examined_in_experiment": len(rows),
        "table": rows,
        "viable_count": len(viable),
        "selected_id": None if chosen is None else chosen["id"],
        "status": "PROVISIONAL_NOT_VALIDATED_ONE_OF_N_EXAMINED",
    }


def compare_with_phase25(
    result: dict, tables: dict[tuple[str, str], pd.DataFrame], p25: dict
) -> dict[str, Any]:
    """How the Phase 2.5 all-situation thresholds behave on this definition's pressure samples."""
    out: dict[str, Any] = {}
    for fmt in FORMATS:
        out[fmt] = {}
        for role in ROLES:
            old = p25[fmt][role]
            t = tables[(fmt, role)]
            rec = result["summary"][fmt][role]["recommended"]
            out[fmt][role] = {
                "phase25_rule": old["rule_id"],
                "phase25_min_balls": old["min_balls"],
                "phase25_required_balls_for_data_weight": old["required_balls_for_data_weight"],
                "phase25_eligible_all_situation": old["eligible_all_situation"],
                "pressure_required_balls_for_data_weight": result["summary"][fmt][role][
                    "required_balls_for_data_weight"
                ],
                "players_with_pressure_sample": int(len(t)),
                "players_passing_phase25_threshold_on_pressure_samples": players_passing(
                    t, old["min_balls"]
                ),
                "pressure_specific_min_balls": None if rec is None else rec["min_balls"],
                "pressure_specific_eligible": None if rec is None else rec["eligible_players"],
            }
    return out
