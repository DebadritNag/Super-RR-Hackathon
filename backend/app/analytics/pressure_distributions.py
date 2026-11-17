"""Pressure feature distributions and candidate-population effects (Phase 3 prep, Stage 3).

EXPLORATORY_NOT_VALIDATED. Describes observed distributions and the population each candidate
selects. It does not choose a threshold and it does not score any player.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.pressure_features import SCOPE, param

PCTS = [5, 10, 25, 50, 75, 90, 95, 99]
FLOORS = {  # Phase 2.5 eligibility_rules_v1 ladders (first two balls rungs, first matches rung)
    "batter": {"balls": [30, 60], "matches": [3, 5]},
    "bowler": {"balls": [24, 48], "matches": [3, 5]},
}


def describe(x: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    ok = x[np.isfinite(x)]
    out: dict[str, Any] = {"n": int(len(x)), "n_null": int(len(x) - len(ok))}
    if len(ok) == 0:
        return out
    out.update(mean=float(ok.mean()), sd=float(ok.std()), min=float(ok.min()), max=float(ok.max()))
    for p in PCTS:
        out[f"p{p}"] = float(np.percentile(ok, p))
    mn = ok.min()
    out["share_at_min"] = float((ok == mn).mean())
    return out


def kish(counts) -> float:
    a = np.asarray(counts, dtype=float)
    a = a[a > 0]
    return float(a.sum() ** 2 / (a**2).sum()) if a.size else 0.0


def player_counts(df: pd.DataFrame, mask: np.ndarray, role: str) -> pd.DataFrame:
    """Per player sufficient counts of pressure opportunities (player id, never names)."""
    if role == "batter":
        m = (
            mask
            & (df["den_counts_as_ball_faced"].to_numpy() == 1)
            & df["striker_id"].notna().to_numpy()
        )
        pid = "striker_id"
    else:
        m = (
            mask
            & (df["den_bowler_counts_row"].to_numpy() == 1)
            & df["bowler_id"].notna().to_numpy()
        )
        pid = "bowler_id"
    sub = df.loc[m, [pid, "match_id", "inn_key", "den_legal_inc"]].copy()
    sub["one"] = 1
    sub["legal"] = (sub["den_legal_inc"] == 1).astype(int)
    pm = sub.groupby([pid, "match_id"]).agg(
        n=("one", "sum"), legal=("legal", "sum"), inn=("inn_key", "nunique")
    )
    pm["measure"] = pm["n"] if role == "batter" else pm["legal"]
    pm["m2"] = pm["measure"].astype(float) ** 2
    g = pm.groupby(level=0).agg(
        n=("n", "sum"), legal=("legal", "sum"), matches=("n", "size"), innings=("inn", "sum"),
        measure=("measure", "sum"), m2=("m2", "sum"),
    )  # fmt: skip
    g["n_eff_kish"] = np.where(g["m2"] > 0, g["measure"] ** 2 / g["m2"].where(g["m2"] > 0, 1), 0.0)
    g.index.name = "player_id"
    return g.reset_index()


def effect_row(df: pd.DataFrame, spec: dict, flag: np.ndarray) -> dict[str, Any]:
    role = spec["role"]
    pc = player_counts(df, flag, role)
    rows = df.loc[flag]
    inn_counts = rows.groupby("inn_key").size().to_numpy()
    f = FLOORS[role]
    b1, b2 = f["balls"]
    m1, m2 = f["matches"]
    meas = pc["measure"].to_numpy()
    mt = pc["matches"].to_numpy()
    out = {
        "id": spec["id"],
        "family": spec["family"],
        "ctx": spec["ctx"],
        "comp": spec["comp"],
        "role": role,
        "signal": spec["signal"],
        "view": spec["view"],
        "q": spec["q"],
        "threshold": spec["threshold"],
        "pressure_rows": int(flag.sum()),
        "pressure_unit_rows": int(pc["n"].sum()),
        "pressure_legal_balls": int(pc["legal"].sum()),
        "matches": int(rows["match_id"].nunique()),
        "innings": int(rows["inn_key"].nunique()),
        "n_eff_innings_kish": kish(inn_counts),
        "players_any": int((meas > 0).sum()),
        "players_ge_floor1": int((meas >= b1).sum()),
        "players_ge_floor2": int((meas >= b2).sum()),
        "players_ge_floor2_m3": int(((meas >= b2) & (mt >= m1)).sum()),
        "players_ge_floor2_m5": int(((meas >= b2) & (mt >= m2)).sum()),
        "floors": {
            "measure": "balls" if role == "batter" else "legal_balls",
            "floor1": b1,
            "floor2": b2,
            "matches1": m1,
            "matches2": m2,
        },  # fmt: skip
    }
    sel = meas >= b2
    out["median_player_measure"] = float(np.median(meas[meas > 0])) if (meas > 0).any() else None
    out["median_n_eff_kish_ge_floor2"] = (
        float(np.median(pc["n_eff_kish"].to_numpy()[sel])) if sel.any() else None
    )
    return out


def candidate_effects(
    df: pd.DataFrame, specs: list[dict], flags: dict[str, np.ndarray]
) -> list[dict]:
    return [effect_row(df, s, flags[s["id"]]) for s in specs]


# ---------------------------------------------------------------- family (c): data-derived breaks
def knee_point(x: np.ndarray, grid_points: int = 400) -> dict[str, Any]:
    """Knee of the curve 'share of rows with signal >= x' (max distance to the chord)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 50 or x.min() == x.max():
        return {"available": False}
    xs = np.unique(np.quantile(x, np.linspace(0, 1, grid_points)))
    share = np.array([(x >= v).mean() for v in xs])
    xn = (xs - xs.min()) / (xs.max() - xs.min())
    yn = (share - share.min()) / (share.max() - share.min()) if share.max() > share.min() else share
    p0, p1 = np.array([xn[0], yn[0]]), np.array([xn[-1], yn[-1]])
    d = p1 - p0
    norm = np.hypot(*d)
    dist = np.abs(d[0] * (yn - p0[1]) - d[1] * (xn - p0[0])) / norm
    i = int(np.argmax(dist))
    return {"available": True, "value": float(xs[i]), "quantile_position": float(1 - share[i]),
            "max_distance": float(dist[i])}  # fmt: skip


def break_candidates(df: pd.DataFrame, rules: dict) -> list[dict]:
    tol = float(param(rules, "break_reproducibility_tol"))
    zshare = float(param(rules, "zero_inflation_share"))
    out = []
    ctx_signals = {
        "chase": ["rrr", "runs_required", "gap", "req_to_exp", "neg_resource_ratio",
                  "bowl_signal_B"],
        "inn1": ["neg_par_dev", "neg_proj_gap", "neg_resource_ratio", "bowl_signal_B"],
    }  # fmt: skip
    for ctx, signals in ctx_signals.items():
        for s in signals:
            per = {}
            for comp in SCOPE:
                pop = (df["chase_pop"] if ctx == "chase" else df["inn1_pop"]) & (
                    df["competition_type"] == comp
                )
                x = df.loc[pop, s].to_numpy(dtype=float)
                per[comp] = knee_point(x)
                finite = x[np.isfinite(x)]
                if finite.size:
                    per[comp]["share_at_min"] = float((finite == finite.min()).mean())
                    per[comp]["min_value"] = float(finite.min())
                    per[comp]["zero_inflated"] = bool(per[comp]["share_at_min"] > zshare)
            qa = [per[c].get("quantile_position") for c in SCOPE]
            repro_fmt = all(v is not None for v in qa) and abs(qa[0] - qa[1]) <= tol
            entry = {"ctx": ctx, "signal": s, "per_comp": per,
                     "reproduced_across_ipl_t20i": bool(repro_fmt)}  # fmt: skip
            if s == "neg_par_dev":
                # LOMO versus strictly prior (T20I and IPL separately)
                prior = {}
                for comp in SCOPE:
                    pop = df["inn1_pop"] & (df["competition_type"] == comp)
                    kp = knee_point(df.loc[pop, "neg_par_dev_prior"].to_numpy(dtype=float))
                    prior[comp] = kp
                entry["strictly_prior"] = prior
                entry["reproduced_lomo_vs_prior"] = bool(
                    all(
                        prior[c].get("available") and per[c].get("available")
                        and abs(prior[c]["quantile_position"] - per[c]["quantile_position"]) <= tol
                        for c in SCOPE
                    )
                )  # fmt: skip
            else:
                entry["reproduced_lomo_vs_prior"] = None  # signal does not depend on par
            entry["usable_candidate"] = bool(
                repro_fmt and entry["reproduced_lomo_vs_prior"] is not False
            )
            out.append(entry)
    return out


def break_effects(df: pd.DataFrame, breaks: list[dict]) -> list[dict]:
    """Population effect of each reproducible break (abs threshold per competition type)."""
    res = []
    for b in breaks:
        if not b["usable_candidate"]:
            continue
        for comp in SCOPE:
            k = b["per_comp"][comp]
            ctx = b["ctx"]
            pop = (df["chase_pop"] if ctx == "chase" else df["inn1_pop"]) & (
                df["competition_type"] == comp
            )
            x = df[b["signal"]].to_numpy(dtype=float)
            flag = pop.to_numpy() & np.isfinite(x) & (x >= k["value"])
            role = "bowler" if b["signal"] == "bowl_signal_B" else "batter"
            spec = {"id": f"c|{ctx}|{comp}|{role}|{b['signal']}|abs|knee", "family": "c",
                    "ctx": ctx, "comp": comp, "role": role, "signal": b["signal"], "view": "abs",
                    "q": k["quantile_position"], "threshold": k["value"]}  # fmt: skip
            res.append(effect_row(df, spec, flag))
    return res


# ---------------------------------------------------------------- strictly prior versus LOMO
def prior_vs_lomo(df: pd.DataFrame, rules: dict) -> list[dict]:
    """Innings-1 par candidates: population under LOMO versus strictly prior par."""
    grid = list(param(rules, "quantile_grid"))
    out = []
    for comp in SCOPE:
        pop = df["inn1_pop"] & (df["competition_type"] == comp)
        for q in grid:
            row: dict[str, Any] = {"comp": comp, "q": q}
            for tag, col in (("lomo", "neg_par_dev"), ("prior", "neg_par_dev_prior")):
                x = df[col].to_numpy(dtype=float)
                ok = pop.to_numpy() & np.isfinite(x)
                thr = float(np.quantile(x[ok], q)) if ok.any() else np.nan
                flag = ok & (x >= thr)
                rows = df.loc[flag]
                row[f"{tag}_threshold"] = thr
                row[f"{tag}_rows"] = int(flag.sum())
                row[f"{tag}_matches"] = int(rows["match_id"].nunique())
                row[f"{tag}_innings"] = int(rows["inn_key"].nunique())
                row[f"{tag}_population_rows"] = int(ok.sum())
            out.append(row)
    return out


# ---------------------------------------------------------------- descriptive tables
def signal_distributions(df: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ctx, popcol, signals in (
        ("chase", "chase_pop", ["rrr", "runs_required", "gap", "req_to_exp", "neg_resource_ratio",
                                "projected_surplus", "legal_balls_remaining", "wickets_remaining"]),
        ("inn1", "inn1_pop", ["neg_par_dev", "neg_proj_gap", "neg_resource_ratio",
                              "legal_balls_remaining", "wickets_remaining", "par_deviation_lomo"]),
    ):  # fmt: skip
        for comp in SCOPE:
            pop = df[popcol] & (df["competition_type"] == comp)
            for s in signals:
                out[f"{ctx}|{comp}|{s}"] = describe(df.loc[pop, s].to_numpy(dtype=float))
            if ctx == "chase":
                for ph in ("powerplay", "middle", "death"):
                    p2 = pop & (df["innings_phase"] == ph)
                    out[f"{ctx}|{comp}|rrr|phase={ph}"] = describe(
                        df.loc[p2, "rrr"].to_numpy(float)
                    )
    return out


def rrr_cap_report(df: pd.DataFrame) -> dict[str, Any]:
    out = {}
    for comp in SCOPE + ("pooled",):
        pop = df["chase_pop"] & ((df["competition_type"] == comp) if comp != "pooled" else True)
        x = df.loc[pop, "rrr"].to_numpy(dtype=float)
        cap = float(np.percentile(x, 99))
        short = pop & (df["legal_balls_remaining"] < 6)
        out[comp] = {
            "p99_cap": cap,
            "uncapped": {
                "mean": float(x.mean()),
                "p90": float(np.percentile(x, 90)),
                "max": float(x.max()),
            },  # fmt: skip
            "capped": {
                "mean": float(np.minimum(x, cap).mean()),
                "p90": float(np.percentile(np.minimum(x, cap), 90)),
            },  # fmt: skip
            "rows_above_cap": int((x > cap).sum()),
            "rows_brem_lt_6": int(short.sum()),
            "rrr_brem_ge_6_p90": float(np.percentile(df.loc[pop & ~short, "rrr"], 90)),
        }
    return out


def histogram(x: np.ndarray, edges: list[float]) -> list[dict]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    c, _ = np.histogram(x, bins=edges)
    return [{"lo": edges[i], "hi": edges[i + 1], "n": int(c[i]), "share": float(c[i] / max(len(x), 1))}
            for i in range(len(c))]  # fmt: skip


def balls_remaining_table(df: pd.DataFrame) -> list[dict]:
    out = []
    for ctx, col in (("chase", "chase_pop"), ("inn1", "inn1_pop")):
        for comp in SCOPE:
            pop = df[col] & (df["competition_type"] == comp)
            sub = df[pop]
            for ph, g in sub.groupby("innings_phase"):
                out.append({"ctx": ctx, "comp": comp, "phase": ph, "rows": int(len(g)),
                            "innings": int(g["inn_key"].nunique()),
                            "wickets_remaining_mean": float(g["wickets_remaining"].mean()),
                            "balls_remaining_mean": float(g["legal_balls_remaining"].mean())})  # fmt: skip
    return out


def runs_required_by_balls(df: pd.DataFrame) -> list[dict]:
    pop = df[df["chase_pop"]].copy()
    pop["brem_bin"] = (pop["legal_balls_remaining"].astype(float) - 1) // 6
    rows = []
    for (comp, b), g in pop.groupby(["competition_type", "brem_bin"]):
        if int(b) % 3 != 0:
            continue
        rows.append({"comp": comp, "balls_remaining_lo": int(b * 6 + 1), "balls_remaining_hi": int(b * 6 + 6),
                     "rows": int(len(g)), "req_p25": float(g["runs_required"].quantile(0.25)),
                     "req_p50": float(g["runs_required"].quantile(0.5)),
                     "req_p75": float(g["runs_required"].quantile(0.75)),
                     "rrr_p50": float(g["rrr"].quantile(0.5)),
                     "rrr_p90": float(g["rrr"].quantile(0.9))})  # fmt: skip
    return rows


def cell_innings_counts(df: pd.DataFrame) -> list[dict]:
    out = []
    for ctx, col in (("chase", "chase_pop"), ("inn1", "inn1_pop")):
        sub = df[df[col]]
        g = sub.groupby(["competition_type", "innings_phase", "wbin"]).agg(
            rows=("inn_key", "size"),
            innings=("inn_key", "nunique"),
            matches=("match_id", "nunique"),
        )
        for (comp, ph, wb), r in g.iterrows():
            out.append(
                {
                    "ctx": ctx,
                    "comp": comp,
                    "phase": ph,
                    "wbin": wb,
                    **{k: int(v) for k, v in r.items()},
                }
            )
    return out


def season_counts(df: pd.DataFrame) -> list[dict]:
    pop = df[df["chase_pop"] | df["inn1_pop"]]
    g = pop.groupby(["competition_type", "season_label"]).agg(
        rows=("inn_key", "size"), innings=("inn_key", "nunique"), matches=("match_id", "nunique")
    )
    return [
        {"comp": c, "season": s, **{k: int(v) for k, v in r.items()}} for (c, s), r in g.iterrows()
    ]
