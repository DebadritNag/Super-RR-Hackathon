"""Pressure signals, par context and candidate definitions (Phase 3 prep, Stage 3).

EXPLORATORY_NOT_VALIDATED. Everything here describes the distribution of pre-delivery states.
Par and expectation tables are leave-one-match-out (LOMO, FULL_SAMPLE, descriptive) built from
official data only. A strictly-prior variant of the innings-1 par curve is also built. No cutoff is
chosen: candidate thresholds come from a quantile search grid and are evaluated, not selected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.analytics.shrinkage import k_from_children, shrink_to_parent

BACKEND = Path(__file__).resolve().parents[2]
RULES_PATH = BACKEND / "config" / "pressure_rules_v1.json"
SCOPE = ("IPL", "T20I")
BOWL_B_EARLY = 12

STATE_COLS = [
    "match_id", "innings_number", "innings_ball_num", "match_date", "competition_type",
    "season_label", "venue_id", "knock_out", "batting_team_id", "bowling_team_id", "striker_id",
    "bowler_id", "chase_flag", "team_runs_before", "wickets_remaining", "legal_balls_bowled_before",
    "innings_limit_balls", "legal_balls_remaining", "innings_phase", "crr", "target",
    "target_basis_unverified", "runs_required", "req_nonpositive_flag", "rrr", "gap",
    "projected_surplus", "resource_ratio", "dls_exclude_primary", "dls_flag",
    "regulation_pressure_eligible", "format_out_of_scope", "post_innings_legal_balls",
    "post_innings_wickets", "out_batter_runs", "out_is_four", "out_is_six", "out_is_wicket",
    "out_dismissal_type", "out_dismissed_player_id", "out_runs_row", "den_legal_inc",
    "den_counts_as_ball_faced", "den_bowler_counts_row", "den_bowler_charged_runs",
    "den_bowler_credited_wicket", "den_wicket_without_dismissed",
]  # fmt: skip


def load_rules(path: Path | str = RULES_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def param(rules: dict, name: str):
    return rules["parameters"][name]["value"]


def load_state(store_path: Path | str) -> pd.DataFrame:
    """Read the exploratory pre-delivery state (read-only) in deterministic order."""
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        cols = ", ".join(STATE_COLS)
        df = con.execute(
            f"SELECT {cols} FROM exp_pre_delivery_state "
            "ORDER BY match_id, innings_number, innings_ball_num"
        ).df()
    finally:
        con.close()
    return df


def add_populations(df: pd.DataFrame) -> pd.DataFrame:
    """Primary populations. Restricted innings 3/4 and OTHER_T20 are never in any population."""
    df = df.copy()
    chase = df["chase_flag"].fillna(False).astype(bool)
    reg = df["innings_number"].isin([1, 2])
    base = (
        df["regulation_pressure_eligible"].fillna(False).astype(bool)
        & ~df["format_out_of_scope"].fillna(False).astype(bool)
        & ~df["dls_exclude_primary"].fillna(False).astype(bool)
        & reg
        & df["competition_type"].isin(SCOPE)
    )
    df["base_pop"] = base
    df["chase_pop"] = (
        base
        & chase
        & ~df["target_basis_unverified"].fillna(False).astype(bool)
        & ~df["req_nonpositive_flag"].fillna(False).astype(bool)
        & df["rrr"].notna()
    )
    df["inn1_pop"] = base & ~chase
    df["role_ctx"] = np.where(chase, "chase", "inn1")
    df["inn_key"] = df["match_id"].astype("int64") * 10 + df["innings_number"].astype("int64")
    return df


# ---------------------------------------------------------------- wickets bins
def merge_wickets_bins(innings_by_wrem: pd.DataFrame, min_cell_innings: int) -> dict[str, Any]:
    """Deterministic global wickets-remaining partition (spec section 8, corrected rule).

    innings_by_wrem: columns cell, inn_key, wrem (one row per distinct innings and wrem value
    present in the cell). m(bin) = minimum over cells of distinct innings with a row whose wrem
    is in the bin. Merge rule: take the bin with the smallest m (ties toward wrem 1), merge it
    with the adjacent bin giving the larger combined m (ties toward wrem 1), repeat.
    """
    cells = sorted(innings_by_wrem["cell"].unique())
    sets = {(c, w): set(g["inn_key"]) for (c, w), g in innings_by_wrem.groupby(["cell", "wrem"])}
    bins: list[list[int]] = [[w] for w in range(10, 0, -1)]

    def m_of(bin_: list[int]) -> int:
        out = []
        for c in cells:
            s: set = set()
            for w in bin_:
                s |= sets.get((c, w), set())
            out.append(len(s))
        return min(out) if out else 0

    log = []
    while len(bins) > 1:
        ms = [m_of(b) for b in bins]
        if min(ms) >= min_cell_innings:
            break
        i = max(i for i, v in enumerate(ms) if v == min(ms))  # ties toward wrem 1
        cands = []
        if i > 0:
            cands.append((m_of(bins[i - 1] + bins[i]), i - 1))
        if i < len(bins) - 1:
            cands.append((m_of(bins[i] + bins[i + 1]), i))
        best = max(v for v, _ in cands)
        j = max(j for v, j in cands if v == best)  # ties toward wrem 1
        log.append({"deficient_bin": bins[i], "m": ms[i], "merged": bins[j] + bins[j + 1],
                    "combined_m": best})  # fmt: skip
        bins[j : j + 2] = [bins[j] + bins[j + 1]]
    ms = [m_of(b) for b in bins]
    failed = len(bins) == 1 and ms[0] < min_cell_innings
    labels = {w: f"{max(b)}-{min(b)}" if len(b) > 1 else f"{b[0]}" for b in bins for w in b}
    return {"bins": bins, "labels": labels, "m_per_bin": ms, "merge_log": log,
            "wickets_bins_failed": bool(failed), "cells": cells}  # fmt: skip


def wicket_bins_for(df: pd.DataFrame, min_cell_innings: int) -> dict[str, Any]:
    d = df[df["base_pop"]]
    cell = d["competition_type"] + "|" + d["role_ctx"] + "|" + d["innings_phase"].astype(str)
    t = pd.DataFrame({"cell": cell, "inn_key": d["inn_key"], "wrem": d["wickets_remaining"]})
    t = t.drop_duplicates()
    t = t[(t["wrem"] >= 1) & (t["wrem"] <= 10)]
    return merge_wickets_bins(t, min_cell_innings)


# ---------------------------------------------------------------- par and expectation (LOMO)
def source_innings(df: pd.DataFrame) -> pd.DataFrame:
    """Complete 120-ball innings 1 of IPL/T20I, one row per innings (spec section 6 rule 3)."""
    d = df[
        (df["innings_number"] == 1)
        & df["competition_type"].isin(SCOPE)
        & df["regulation_pressure_eligible"].fillna(False).astype(bool)
    ]
    g = d.groupby("match_id", sort=True)
    last = g.tail(1).set_index("match_id")
    out = pd.DataFrame(
        {
            "competition_type": last["competition_type"],
            "match_date": last["match_date"],
            "limit": last["innings_limit_balls"],
            "legal": last["post_innings_legal_balls"],
            "wk": last["post_innings_wickets"],
            "total": last["team_runs_before"] + last["out_runs_row"],
        }
    )
    out["complete"] = (out["limit"] == 120) & ((out["wk"] == 10) | (out["legal"] == 120))
    return out[out["complete"]].reset_index()


def par_matrix(df: pd.DataFrame, src: pd.DataFrame) -> np.ndarray:
    """Runs after exactly b legal balls (b = 0..120) per source innings, carried forward."""
    idx = {m: i for i, m in enumerate(src["match_id"])}
    d = df[(df["innings_number"] == 1) & df["match_id"].isin(idx)]
    first = d.drop_duplicates(["match_id", "legal_balls_bowled_before"], keep="first")
    M = np.full((len(src), 121), np.nan)
    ri = first["match_id"].map(idx).to_numpy()
    b = first["legal_balls_bowled_before"].to_numpy().astype(int)
    M[ri, np.clip(b, 0, 120)] = first["team_runs_before"].to_numpy(dtype=float)
    legal = src["legal"].to_numpy().astype(int)  # terminal point: final total at final ball count
    M[np.arange(len(src)), np.clip(legal, 0, 120)] = src["total"].to_numpy(dtype=float)
    return pd.DataFrame(M).ffill(axis=1).to_numpy()


def _first_in_bin(df: pd.DataFrame, src: pd.DataFrame, wmap: dict[int, str]) -> pd.DataFrame:
    """Observation per source innings: final_total - R at the first row of each bin."""
    d = df[(df["innings_number"] == 1) & df["match_id"].isin(set(src["match_id"]))].copy()
    tot = src.set_index("match_id")["total"]
    d["obs"] = d["match_id"].map(tot) - d["team_runs_before"]
    d["j"] = (d["legal_balls_remaining"] - 1) // 6
    d["w"] = d["wickets_remaining"].map(wmap)
    return d[["match_id", "competition_type", "j", "w", "obs"]]


def exp_remaining_lomo(
    df: pd.DataFrame, src: pd.DataFrame, wmap: dict[int, str], rules: dict
) -> pd.DataFrame:
    """E0 binned cell shrunk to E1 (Brem bin), E2 comp pooled; LOMO; level recorded per row."""
    min_n = int(param(rules, "min_cell_innings"))
    floor = float(param(rules, "tau2_floor"))
    fb = _first_in_bin(df, src, wmap)
    e0 = fb.drop_duplicates(["match_id", "j", "w"], keep="first")
    e1 = fb.drop_duplicates(["match_id", "j"], keep="first")
    e2 = src[["match_id", "competition_type", "total"]].rename(columns={"total": "obs"})

    def cells(t: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        g = t.groupby(keys)["obs"]
        return pd.DataFrame(
            {"n": g.size(), "s": g.sum(), "s2": g.apply(lambda x: float((x**2).sum()))}
        )

    c0 = cells(e0, ["competition_type", "j", "w"])
    c1 = cells(e1, ["competition_type", "j"])
    c2 = cells(e2, ["competition_type"])
    kpar = {}
    for (c, j), g in c0.reset_index().groupby(["competition_type", "j"]):
        mean = g["s"] / g["n"]
        ss = g["s2"] - g["s"] ** 2 / g["n"]
        kpar[(c, j)] = k_from_children(g["n"], g["n"], mean, ss, floor)
    rows = df[["match_id", "innings_number", "competition_type", "legal_balls_remaining",
               "wickets_remaining"]].copy()  # fmt: skip
    ok = (rows["innings_number"].isin([1, 2])) & rows["competition_type"].isin(SCOPE)
    ok &= rows["legal_balls_remaining"] >= 1
    rows["j"] = ((rows["legal_balls_remaining"].astype("float64") - 1) // 6).where(ok)
    rows["w"] = rows["wickets_remaining"].map(wmap)
    own0 = e0.set_index(["match_id", "competition_type", "j", "w"])["obs"]
    own1 = e1.set_index(["match_id", "competition_type", "j"])["obs"]
    own2 = e2.set_index(["match_id", "competition_type"])["obs"]

    def stats(c: pd.DataFrame, own: pd.Series, keys: list[str], with_match: list[str]):
        j = rows[keys].reset_index(drop=True)
        m = j.merge(c, how="left", left_on=keys, right_index=True)
        n = m["n"].fillna(0).to_numpy(dtype=float)
        s = m["s"].fillna(0).to_numpy(dtype=float)
        o = (
            rows[with_match]
            .reset_index(drop=True)
            .merge(own.rename("o"), how="left", left_on=with_match, right_index=True)["o"]
        )
        has = o.notna().to_numpy()
        n = n - has
        s = s - o.fillna(0).to_numpy(dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(n > 0, s / np.where(n > 0, n, 1), np.nan)
        return n, mean

    n0, m0 = stats(c0, own0, ["competition_type", "j", "w"],
                   ["match_id", "competition_type", "j", "w"])  # fmt: skip
    n1, m1 = stats(c1, own1, ["competition_type", "j"], ["match_id", "competition_type", "j"])
    n2, m2 = stats(c2, own2, ["competition_type"], ["match_id", "competition_type"])
    krow = np.array([kpar.get((c, j), {"k": 1 / floor})["k"] if j == j else np.nan
                     for c, j in zip(rows["competition_type"], rows["j"])])  # fmt: skip
    fhit = np.array([kpar.get((c, j), {"shrinkage_floor_hit": False})["shrinkage_floor_hit"]
                     if j == j else False
                     for c, j in zip(rows["competition_type"], rows["j"])])  # fmt: skip
    v0 = shrink_to_parent(n0, m0, m1, krow)
    use0 = n0 >= min_n
    use1 = ~use0 & (n1 >= min_n)
    use2 = ~use0 & ~use1 & (n2 >= min_n)
    val = np.where(use0, v0, np.where(use1, m1, np.where(use2, m2, np.nan)))
    lvl = np.where(use0, "E0_BINNED", np.where(use1, "E1_BREM_BIN",
                   np.where(use2, "E2_COMP_TYPE", "NONE")))  # fmt: skip
    val = np.where(ok.to_numpy(), val, np.nan)
    lvl = np.where(ok.to_numpy(), lvl, "NONE")
    out = pd.DataFrame({"exp_remaining": val, "exp_cell_level_used": lvl,
                        "shrinkage_floor_hit": fhit & use0}, index=df.index)  # fmt: skip
    out["exp_remaining"] = out["exp_remaining"].where(out["exp_remaining"] > 0)
    out.attrs["k_by_parent"] = {f"{c}|{j}": v for (c, j), v in kpar.items()}
    return out


def par_columns(df: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, dict]:
    """par_runs (LOMO and strictly prior), signals; returns (columns, meta)."""
    src = source_innings(df)
    F = par_matrix(df, src)
    par = pd.DataFrame(index=df.index, dtype=float)
    par["par_runs_lomo"] = np.nan
    par["par_total_lomo"] = np.nan
    par["par_runs_prior"] = np.nan
    inn1 = (df["innings_number"] == 1) & df["competition_type"].isin(SCOPE)
    min_prior = int(param(rules, "min_prior_innings"))
    meta: dict[str, Any] = {"source_innings": {}, "par_unavailable_prior_rows": 0}
    for c in SCOPE:
        sm = (src["competition_type"] == c).to_numpy()
        Fc = F[sm]
        mids = src.loc[sm, "match_id"].to_numpy()
        tot = src.loc[sm, "total"].to_numpy(dtype=float)
        sums, cnt = Fc.sum(axis=0), len(Fc)
        meta["source_innings"][c] = int(cnt)
        rmask = (inn1 & (df["competition_type"] == c)).to_numpy()
        b = df.loc[rmask, "legal_balls_bowled_before"].to_numpy().astype(int)
        mid = df.loc[rmask, "match_id"].to_numpy()
        local = {m: i for i, m in enumerate(mids)}
        own = np.array([local.get(m, -1) for m in mid])
        has = own >= 0
        own_val = np.where(has, Fc[np.where(has, own, 0), np.clip(b, 0, 120)], 0.0)
        par.loc[rmask, "par_runs_lomo"] = (sums[np.clip(b, 0, 120)] - own_val) / (cnt - has)
        own_t = np.where(has, tot[np.where(has, own, 0)], 0.0)
        par.loc[rmask, "par_total_lomo"] = (tot.sum() - own_t) / (cnt - has)
        # strictly prior: source innings with match_date strictly before the row's match date
        dts = src.loc[sm, "match_date"].to_numpy()
        order = np.argsort(dts, kind="stable")
        cum = np.vstack([np.zeros(121), np.cumsum(Fc[order], axis=0)])
        sd = dts[order]
        rdate = df.loc[rmask, "match_date"].to_numpy()
        k = np.searchsorted(sd, rdate, side="left")
        with np.errstate(invalid="ignore", divide="ignore"):
            prior = cum[k, np.clip(b, 0, 120)] / np.where(k > 0, k, 1)
        par.loc[rmask, "par_runs_prior"] = np.where(k >= min_prior, prior, np.nan)
    meta["par_unavailable_prior_rows"] = int((inn1 & par["par_runs_prior"].isna()).sum())
    par["par_deviation_lomo"] = df["team_runs_before"] - par["par_runs_lomo"]
    par["par_deviation_prior"] = df["team_runs_before"] - par["par_runs_prior"]
    return par, {"src": src, **meta}


def add_signals(df: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, dict]:
    """Attach wickets bins, par, expectation and signals. Returns (frame, meta)."""
    min_n = int(param(rules, "min_cell_innings"))
    wb = wicket_bins_for(df, min_n)
    df = df.copy()
    df["wbin"] = df["wickets_remaining"].map(wb["labels"])
    par, pmeta = par_columns(df, rules)
    src = pmeta["src"]
    exp = exp_remaining_lomo(df, src, wb["labels"], rules)
    df = pd.concat([df, par, exp], axis=1)
    chase = df["chase_flag"].fillna(False).astype(bool)
    df["req_to_exp"] = np.where(chase & (df["exp_remaining"] > 0),
                                df["runs_required"] / df["exp_remaining"], np.nan)  # fmt: skip
    df["proj_total_gap_lomo"] = df["team_runs_before"] + df["exp_remaining"] - df["par_total_lomo"]
    df["neg_par_dev"] = -df["par_deviation_lomo"]
    df["neg_par_dev_prior"] = -df["par_deviation_prior"]
    df["neg_proj_gap"] = -df["proj_total_gap_lomo"]
    df["neg_resource_ratio"] = -df["resource_ratio"]
    df["bowl_B_early_flag"] = df["legal_balls_bowled_before"] < BOWL_B_EARLY
    # bowling convention B signal: projected surplus (chase), par deviation (innings 1)
    df["bowl_signal_B"] = np.where(chase, df["projected_surplus"], df["par_deviation_lomo"])
    # s_bat: -par_dev (innings 1), RRR (chase)
    df["s_bat"] = np.where(chase, df["rrr"], df["neg_par_dev"])
    meta = {"wickets_bins": {k: v for k, v in wb.items() if k != "cells"},
            "wickets_bin_cells": wb["cells"], "par": {k: v for k, v in pmeta.items() if k != "src"},
            "source_innings_n": int(len(src)),
            "exp_k_by_parent": exp.attrs.get("k_by_parent", {})}  # fmt: skip
    return df, meta


# ---------------------------------------------------------------- relative pressure
def rank_pct_excl_match(
    values: np.ndarray, cell: np.ndarray, match: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    """rank_pct(x; cell, M) = (count(v<x) + 0.5*count(v==x)) / count(V), own match removed.

    V = non-NULL signal values of deliveries in `cell` that belong to other matches. Rows with a
    NULL signal or outside `valid` get NaN. Mid-rank ties. The positional index 0..n-1 is used.
    """
    out = np.full(len(values), np.nan)
    d = pd.DataFrame({"v": values, "c": cell, "m": match, "ok": valid & np.isfinite(values)})
    d = d[d["ok"]]
    for _, g in d.groupby("c", sort=False):
        sv = np.sort(g["v"].to_numpy())
        n_all = len(sv)
        for _, h in g.groupby("m", sort=False):
            x = h["v"].to_numpy()
            less = np.searchsorted(sv, x, "left")
            eq = np.searchsorted(sv, x, "right") - less
            ov = np.sort(x)
            ol = np.searchsorted(ov, x, "left")
            oe = np.searchsorted(ov, x, "right") - ol
            n_v = n_all - len(x)
            with np.errstate(invalid="ignore", divide="ignore"):
                r = np.where(n_v > 0, ((less - ol) + 0.5 * (eq - oe)) / max(n_v, 1), np.nan)
            out[h.index.to_numpy()] = r
    return out


def rank_pct_with_fallback(
    df: pd.DataFrame, signal: str, pop: pd.Series, min_cell_innings: int
) -> pd.DataFrame:
    """Relative pressure with cell fallback L0 (comp, ctx, phase, wbin) .. L3 (comp)."""
    vals = df[signal].to_numpy(dtype=float)
    ph = df["innings_phase"].astype(str)
    keys = [
        df["competition_type"] + "|" + df["role_ctx"] + "|" + ph + "|" + df["wbin"].astype(str),
        df["competition_type"] + "|" + df["role_ctx"] + "|" + ph,
        df["competition_type"] + "|" + df["role_ctx"],
        df["competition_type"],
    ]
    valid = pop.to_numpy() & np.isfinite(vals)
    res = np.full(len(df), np.nan)
    lvl = np.full(len(df), -1)
    chosen = np.zeros(len(df), dtype=bool)
    for li, key in enumerate(keys):
        inn = pd.Series(df["inn_key"].where(valid)).groupby(key).transform("nunique")
        sel = valid & ~chosen & (inn.to_numpy() >= min_cell_innings)
        if not sel.any():
            continue
        r = rank_pct_excl_match(vals, key.to_numpy(), df["match_id"].to_numpy(), valid)
        res[sel] = r[sel]
        lvl[sel] = li
        chosen |= sel
    return pd.DataFrame({f"rank_{signal}": res, f"rank_{signal}_level": lvl}, index=df.index)


def add_relative(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """bat_pressure_rel, bowl_rel_A (= 1 - bat_pressure_rel) and bowl_rel_B (relative views)."""
    min_n = int(param(rules, "min_cell_innings"))
    pop = df["chase_pop"] | df["inn1_pop"]
    a = rank_pct_with_fallback(df, "s_bat", pop, min_n).rename(
        columns=lambda c: c.replace("s_bat", "bat_pressure_rel")
    )
    b = rank_pct_with_fallback(
        df, "bowl_signal_B", pop & df["bowl_signal_B"].notna(), min_n
    ).rename(columns=lambda c: c.replace("bowl_signal_B", "bowl_rel_B"))
    out = pd.concat([df, a, b], axis=1)
    out["bowl_rel_A"] = 1.0 - out["rank_bat_pressure_rel"]
    return out


# ---------------------------------------------------------------- candidate definitions
CHASE_SIGNALS = ["rrr", "runs_required", "gap", "req_to_exp", "neg_resource_ratio"]
INN1_SIGNALS = ["neg_par_dev", "neg_proj_gap", "neg_resource_ratio"]
CONJ_PAIRS = [("rrr", "wrem"), ("rrr", "brem"), ("req_to_exp", "wrem"),
              ("neg_par_dev", "wrem"), ("neg_resource_ratio", "death")]  # fmt: skip


def lower_quantile(x: np.ndarray, q: float) -> float:
    return float(np.quantile(x, q, method="lower"))


def context_pop(df: pd.DataFrame, ctx: str, comp: str, drop_early: bool = False) -> pd.Series:
    pop = df["chase_pop"] if ctx == "chase" else df["inn1_pop"]
    pop = pop & (df["competition_type"] == comp)
    if drop_early:
        pop = pop & ~df["bowl_B_early_flag"]
    return pop


def build_candidates(df: pd.DataFrame, rules: dict) -> tuple[list[dict], dict[str, np.ndarray]]:
    """All candidate definitions of families (a) and (b). Returns (specs, boolean flags by id).

    Each spec: id, family, ctx, comp, role ('batter' | 'bowler'), signal, view, q, threshold.
    Flags are boolean arrays aligned to df. No definition is selected here.
    """
    grid = list(param(rules, "quantile_grid"))
    specs: list[dict] = []
    flags: dict[str, np.ndarray] = {}

    def add(spec: dict, flag: np.ndarray) -> None:
        spec["id"] = "|".join(str(spec[k]) for k in ("family", "ctx", "comp", "role", "signal",
                                                      "view", "q"))  # fmt: skip
        flags[spec["id"]] = flag
        specs.append(spec)

    rb = df["rank_bat_pressure_rel"].to_numpy(dtype=float)
    ra = df["bowl_rel_A"].to_numpy(dtype=float)
    rB = df["rank_bowl_rel_B"].to_numpy(dtype=float) if "rank_bowl_rel_B" in df else None
    xb = df["bowl_signal_B"].to_numpy(dtype=float)
    wrem = df["wickets_remaining"].to_numpy(dtype=float)
    brem = df["legal_balls_remaining"].to_numpy(dtype=float)
    death = (df["innings_phase"] == "death").to_numpy()
    for comp in SCOPE:
        for ctx, signals in (("chase", CHASE_SIGNALS), ("inn1", INN1_SIGNALS)):
            pop = context_pop(df, ctx, comp)
            pm = pop.to_numpy()
            for s in signals:
                x = df[s].to_numpy(dtype=float)
                ok = pm & np.isfinite(x)
                for q in grid:
                    thr = float(np.quantile(x[ok], q)) if ok.any() else np.nan
                    add({"family": "a", "ctx": ctx, "comp": comp, "role": "batter", "signal": s,
                         "view": "abs", "q": q, "threshold": thr}, ok & (x >= thr))  # fmt: skip
            for q in grid:  # relative views: batter on s_bat; bowler convention A
                add({"family": "a", "ctx": ctx, "comp": comp, "role": "batter", "signal": "s_bat",
                     "view": "rel", "q": q, "threshold": q}, pm & np.isfinite(rb) & (rb >= q))  # fmt: skip
                add({"family": "a", "ctx": ctx, "comp": comp, "role": "bowler",
                     "signal": "bowl_rel_A", "view": "rel", "q": q, "threshold": q},
                    pm & np.isfinite(ra) & (ra >= q))  # fmt: skip
            for early in (False, True):  # bowling convention B, with and without the first 12 balls
                bp = context_pop(df, ctx, comp, drop_early=early).to_numpy()
                okB = bp & np.isfinite(xb)
                tag = "noearly" if early else "all"
                for q in grid:
                    thr = float(np.quantile(xb[okB], q)) if okB.any() else np.nan
                    add({"family": "a", "ctx": ctx, "comp": comp, "role": "bowler",
                         "signal": f"bowl_signal_B_{tag}", "view": "abs", "q": q,
                         "threshold": thr}, okB & (xb >= thr))  # fmt: skip
                    if rB is not None:
                        add({"family": "a", "ctx": ctx, "comp": comp, "role": "bowler",
                             "signal": f"bowl_rel_B_{tag}", "view": "rel", "q": q,
                             "threshold": q}, bp & np.isfinite(rB) & (rB >= q))  # fmt: skip
            # family (b): conjunctions, same q in both conditions
            for a, bnd in CONJ_PAIRS:
                if (ctx == "chase" and a == "neg_par_dev") or (
                    ctx == "inn1" and a in ("rrr", "req_to_exp")
                ):
                    continue
                x = df[a].to_numpy(dtype=float)
                okx = pm & np.isfinite(x)
                for q in grid:
                    thr = float(np.quantile(x[okx], q)) if okx.any() else np.nan
                    first = okx & (x >= thr)
                    if bnd == "wrem":
                        t2 = lower_quantile(wrem[pm], 1 - q)
                        second = wrem <= t2
                    elif bnd == "brem":
                        t2 = lower_quantile(brem[pm], 1 - q)
                        second = brem <= t2
                    else:
                        t2 = "death"
                        second = death
                    add({"family": "b", "ctx": ctx, "comp": comp, "role": "batter",
                         "signal": f"{a}&{bnd}", "view": "abs", "q": q,
                         "threshold": f"{thr:.4g}&{t2}"}, first & second)  # fmt: skip
    return specs, flags
