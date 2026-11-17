"""Approach C: Pressure Response Index (PRI) and the IPL/T20I combination study.

PRI is an observable-performance index, not a psychological score. For one role it combines three
scored components, each estimated on the same pressure units (intensity >= 0.5, one unit per
player-match-innings) and each shrunk by REML on those match-level units:

* ``A``     context-adjusted performance (Approach A residual),
* ``B``     match impact (leverage-adjusted win-probability-added residual, Approach B),
* ``CONS``  consistency: share of pressure units with a positive A residual, minus 0.5.

Exposure (count and mean intensity) and the shrinkage factor (sample reliability) are reported
and used by the evidence classes; they are not scored (a score for "faced a lot of pressure" would
reward opportunity, not response).

Weights are derived from data and fixed on the TRAIN odd-parity matches (``FIT``); everything
reported about reliability uses the other matches (``HELD``: TRAIN even-parity plus VALIDATION):

1. per component, split-half reliability ``r`` (Spearman-Brown) on FIT gives ``w = r / (1 - r)``
   (``r`` clipped to 0.99); a non-positive or non-estimable ``r`` or a REML floor gives weight 0 and
   the label ``NO_SIGNAL_*``;
2. when two active components correlate above 0.5 (Spearman, FIT) the first principal component
   of the standardised active components defines the weights (loadings reported); otherwise the
   normalised reliability weights are used;
3. when every component is ``NO_SIGNAL`` the PRI is ``NOT_DEFINED`` and no ranking is produced.

PRI = sum_c w_c * level_c / sd_c with ``level_c`` the REML posterior (or unshrunk mean when the
cell hits the floor, the predeclared rule) and ``sd_c`` the cohort standard deviation of the level.
Each ``level_c`` is centred on the eligible cohort mean, so PRI 0 is the typical eligible player\nand the sign says better or worse than that cohort (not better than a fixed benchmark; the share of\npositive units is below 0.5 for almost everyone because ball outcomes are right-skewed).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.phase8.approach_a import Boot, centre_by_format, player_bootstrap_spearman
from app.phase8.constants import SEED
from app.phase8.reliability import (
    assign_halves,
    out_of_time_correlation,
    precision_weighted_means,
    split_half,
)
from app.phase8.reml import RemlError, fit_reml
from app.phase8.stability import point_ranking, rank_stability

COMPONENTS = ("A", "B", "CONS")
R_CLIP = 0.99
CORR_PCA = 0.5
ALL_NO_SIGNAL = "NOT_DEFINED"


# ---------------------------------------------------------------------------------------------
# units and splits
# ---------------------------------------------------------------------------------------------
def rel_units(units: pd.DataFrame) -> pd.DataFrame:
    """Unit table for ``reliability.py`` (weight = precision, as in the REML)."""
    return units.assign(w=units["prec"])[["player_id", "match_id", "match_date", "y", "w"]]


def consistency_units(units: pd.DataFrame) -> pd.DataFrame:
    """Binary consistency units: +0.5 when the unit's A residual is positive, else -0.5."""
    return units.assign(y=np.where(units["y"] > 0, 0.5, -0.5), prec=1.0)


def component_units(unit_a: pd.DataFrame, unit_b: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The three component unit tables of one role (A and B units already carry ``prec``)."""
    return {"A": unit_a, "B": unit_b, "CONS": consistency_units(unit_a)}


def fit_match_split(matches: pd.DataFrame) -> pd.Series:
    """``FIT`` = TRAIN matches at odd positions in (date, id) order; every other match is ``HELD``.

    ``matches`` has one row per match with ``match_id, match_date, period``. TEST is not present.
    """
    m = matches.drop_duplicates("match_id")
    if set(m["period"]) - {"TRAIN", "VALIDATION"}:
        raise ValueError("only TRAIN and VALIDATION matches may enter Approach C")
    tr = m[m["period"] == "TRAIN"].sort_values(["match_date", "match_id"])
    fit_ids = set(tr["match_id"].to_numpy()[1::2].tolist())
    lab = np.where(m["match_id"].isin(fit_ids), "FIT", "HELD")
    return pd.Series(lab, index=m["match_id"].to_numpy(), name="split")


# ---------------------------------------------------------------------------------------------
# weights
# ---------------------------------------------------------------------------------------------
def reliability_weight(r: float | None, floor: bool) -> tuple[float, str]:
    """Noise-aware weight ``r / (1 - r)`` and its status; 0 for anything without signal."""
    if r is None or not np.isfinite(r):
        return 0.0, "NO_SIGNAL_NOT_ESTIMABLE"
    if floor:
        return 0.0, "NO_SIGNAL_FLOOR"
    if r <= 0:
        return 0.0, "NO_SIGNAL_NONPOSITIVE_RELIABILITY"
    r = min(float(r), R_CLIP)
    return r / (1.0 - r), "ACTIVE"


def combine_weights(raw: dict[str, float], fit_means: pd.DataFrame) -> dict[str, Any]:
    """Final weights from the reliability weights and the FIT-half component correlations.

    ``fit_means`` has one column per component (unshrunk FIT means, one row per player).
    """
    active = [c for c in COMPONENTS if raw.get(c, 0.0) > 0]
    out: dict[str, Any] = {"weights": dict.fromkeys(COMPONENTS, 0.0), "pca": False,
                           "max_abs_corr": float("nan"), "loadings": {}, "defined": bool(active)}  # fmt: skip
    if not active:
        return out
    if len(active) == 1:
        out["weights"][active[0]] = 1.0
        return out
    x = fit_means[active].dropna()
    corr = x.corr(method="spearman").to_numpy()
    off = np.abs(corr[~np.eye(len(active), dtype=bool)])
    out["max_abs_corr"] = float(off.max())
    if out["max_abs_corr"] > CORR_PCA and len(x) >= 5:
        z = (x - x.mean()) / x.std(ddof=1)
        vals, vecs = np.linalg.eigh(np.corrcoef(z.to_numpy().T))
        v = vecs[:, int(np.argmax(vals))]
        if v.sum() < 0:
            v = -v
        # All components are oriented "higher is better": a negative loading would reward worse
        # performance, so it is set to 0 (reported in ``loadings`` before clipping).
        raw_load = dict(zip(active, (v / np.abs(v).sum()).tolist(), strict=True))
        v = np.clip(v, 0.0, None)
        if v.sum() <= 0:
            v = np.array([raw[c] for c in active])
        v = v / np.abs(v).sum()
        out["pca"] = True
        out["loadings"] = raw_load
        for c, val in zip(active, v, strict=True):
            out["weights"][c] = float(val)
    else:
        tot = sum(raw[c] for c in active)
        for c in active:
            out["weights"][c] = float(raw[c] / tot)
    return out


def derive_weights(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, fit_ids: set[int], min_half: int = 2
) -> dict[str, Any]:
    """Reliability, floor flag, reliability weight and final weights, all from FIT matches only."""
    rows, means = [], {}
    raw: dict[str, float] = {}
    for c in COMPONENTS:
        u = cunits[c]
        f = u[u["player_id"].isin(players) & u["match_id"].isin(fit_ids)]
        row: dict[str, Any] = {"component": c, "n_units_fit": int(len(f)),
                               "n_players_fit": int(f["player_id"].nunique())}  # fmt: skip
        r = float("nan")
        try:
            sh = split_half(rel_units(f), "parity", min_half)
            r, row["split_half_r"], row["n_split_players"] = (
                sh["spearman_brown"], sh["r"], sh["n_players"],
            )  # fmt: skip
        except (ValueError, KeyError):
            row["split_half_r"], row["n_split_players"] = float("nan"), 0
        try:
            fit = fit_reml(f)
            floor, row["tau2_fit"], row["sigma2_fit"] = fit["floor"], fit["tau2"], fit["sigma2"]
        except RemlError:
            floor, row["tau2_fit"], row["sigma2_fit"] = True, float("nan"), float("nan")
        row["floor_fit"], row["split_half_sb"] = bool(floor), r
        w, status = reliability_weight(r, floor)
        row["reliability_weight"], row["status"] = w, status
        raw[c] = w
        rows.append(row)
        if len(f):
            means[c] = precision_weighted_means(rel_units(f)).set_index("player_id")["ybar"]
    fit_means = pd.DataFrame(means)
    comb = combine_weights(raw, fit_means)
    for row in rows:
        row["final_weight"] = comb["weights"][row["component"]]
        row["pca_loading"] = comb["loadings"].get(row["component"], float("nan"))
    corr = (
        fit_means.corr(method="spearman")
        if fit_means.shape[1] > 1
        else pd.DataFrame(index=fit_means.columns, columns=fit_means.columns)
    )
    return {"table": pd.DataFrame(rows), "corr": corr, "combine": comb,
            "weights": comb["weights"], "defined": comb["defined"]}  # fmt: skip


# ---------------------------------------------------------------------------------------------
# point estimates
# ---------------------------------------------------------------------------------------------
def pri_point(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, weights: dict[str, float],
    centre: bool = True,
) -> dict[str, Any]:  # fmt: skip
    """REML level of every component and the PRI of the players that have every active component.

    ``centre`` subtracts the format mean (COMBINED scope); ``shift`` adds back the mean of those
    format means so that 0 stays "as expected".
    """
    comps: dict[str, dict[str, Any]] = {}
    for c in COMPONENTS:
        eu = cunits[c][cunits[c]["player_id"].isin(players)]
        shift = 0.0
        if centre:
            cu, mu = centre_by_format(eu)
            shift = float(
                np.average(cu["y_raw"], weights=cu["prec"])
                - np.average(cu["y"], weights=cu["prec"])
            )
            eu = cu
        fit = fit_reml(eu)
        ps = fit["players"]
        basis = ps["ybar"] if fit["floor"] else ps["theta"]
        comps[c] = {"fit": fit, "units": eu, "level": basis + shift, "shift": shift,
                    "unshrunk": ps["ybar"] + shift, "B": ps["B"], "se": ps["se"]}  # fmt: skip
    active = [c for c in COMPONENTS if weights.get(c, 0.0) != 0.0]
    levels = pd.DataFrame({c: comps[c]["level"] for c in COMPONENTS})
    sds = {c: float(levels[c].std(ddof=1)) for c in COMPONENTS}
    for c in COMPONENTS:
        comps[c]["centre"] = float(levels[c].mean())
    out: dict[str, Any] = {"comps": comps, "levels": levels, "sds": sds, "active": active}
    if not active or any(not np.isfinite(sds[c]) or sds[c] < 1e-12 for c in active):
        out["pri"] = pd.Series(np.nan, index=levels.index, name="pri")
        return out
    pri = sum(weights[c] * (levels[c] - comps[c]["centre"]) / sds[c] for c in active)
    ok = levels[active].notna().all(axis=1)
    out["pri"] = pri.where(ok).rename("pri")
    return out


def refit_draws_floor(
    units: pd.DataFrame, players: np.ndarray, boot: Boot
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """REML refit per match-cluster draw: ranking basis, posterior mean and floor flag.

    The ranking basis is the posterior mean, or the unshrunk mean in a draw whose refit hits the
    floor (the predeclared rule, same as ``refit_draws``). ``post`` keeps the posterior only
    (NaN in floor draws) so intervals are not mixed across the two scales.
    """
    u = units[units["player_id"].isin(players)].reset_index(drop=True)
    pos = boot.pos(u["match_id"].to_numpy())
    shape = (boot.n_draws, len(players))
    basis, post = np.full(shape, np.nan), np.full(shape, np.nan)
    floor = np.zeros(boot.n_draws, dtype=bool)
    for d in range(boot.n_draws):
        try:
            f = fit_reml(u.assign(mult=boot.counts[d, pos]))
        except RemlError:
            floor[d] = True
            continue
        p = f["players"]
        cols = np.searchsorted(players, p.index.to_numpy())
        floor[d] = f["floor"]
        basis[d, cols] = (p["ybar"] if f["floor"] else p["theta"]).to_numpy()
        if not f["floor"]:
            post[d, cols] = p["theta"].to_numpy()
    return basis, post, floor


def bootstrap_pri(
    comps: dict[str, dict[str, Any]], players: np.ndarray, boot: Boot, weights: dict[str, float],
    sds: dict[str, float], top_k: int = 10,
) -> dict[str, Any]:  # fmt: skip
    """PRI per match-cluster draw with a full REML refit of each active component per draw.

    Weights, scale (``sd``) and centre are held at their full-sample values so the interval
    describes the same quantity as the point estimate. Ranks and Top-10 inclusion use every draw
    (floor draws use the unshrunk mean by the predeclared rule); the estimate interval uses only
    draws in which no active component hit the floor and reports how many that is.
    """
    players = np.sort(np.asarray(players))
    total = np.zeros((boot.n_draws, len(players)))
    total_post = np.zeros((boot.n_draws, len(players)))
    floor_share: dict[str, float] = {}
    for c, w in weights.items():
        if w == 0.0:
            continue
        basis, post, fl = refit_draws_floor(comps[c]["units"], players, boot)
        k = comps[c]["shift"] - comps[c]["centre"]
        total += w * (basis + k) / sds[c]
        total_post += w * (post + k) / sds[c]
        floor_share[c] = float(fl.mean())
    idx = pd.Index(players, name="player_id")
    stab = rank_stability(total, idx, top_k=top_k)
    ok = np.isfinite(total_post).any(axis=1)
    with np.errstate(all="ignore"):
        stab["est_low"] = np.nanpercentile(total_post[ok], 2.5, axis=0) if ok.any() else np.nan
        stab["est_high"] = np.nanpercentile(total_post[ok], 97.5, axis=0) if ok.any() else np.nan
        stab["pri_se"] = np.nanstd(total_post[ok], axis=0, ddof=1) if ok.any() else np.nan
    stab["interval_draws"] = int(ok.sum())
    return {"stability": stab, "draws": total, "floor_draw_share": floor_share}


# ---------------------------------------------------------------------------------------------
# held-out reliability of the PRI itself
# ---------------------------------------------------------------------------------------------
def _master_halves(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, ids: set[int], mode: str
) -> pd.DataFrame:
    frames = [
        u[u["player_id"].isin(players) & u["match_id"].isin(ids)][
            ["player_id", "match_id", "match_date"]
        ]
        for u in cunits.values()
    ]
    m = pd.concat(frames).drop_duplicates(["player_id", "match_id"]).reset_index(drop=True)
    m = m.assign(y=0.0, w=1.0)
    m["half"] = assign_halves(m, mode).to_numpy()
    return m[["player_id", "match_id", "half"]]


def pri_split_half(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, ids: set[int],
    weights: dict[str, float], sds: dict[str, float], mode: str = "parity", min_half: int = 2,
    n_boot: int = 500, seed: int = SEED,
) -> dict[str, Any]:  # fmt: skip
    """Split-half reliability of the unshrunk PRI on the given matches, with a match bootstrap.

    The weights and scales are fixed beforehand, so the halves are an out-of-sample check of the
    index and not a refit.
    """
    act = [c for c, w in weights.items() if w != 0.0]
    players = np.sort(np.asarray(players))
    n_pl = len(players)
    if not act or n_pl < 3:
        return {"mode": mode, "n_players": 0, "r": float("nan"), "spearman_brown": float("nan")}
    master = _master_halves(cunits, players, ids, mode)
    mids = np.sort(master["match_id"].unique())
    m_p = np.searchsorted(players, master["player_id"].to_numpy())
    m_m = np.searchsorted(mids, master["match_id"].to_numpy())
    m_key = m_p * 2 + master["half"].to_numpy()
    arrs = {}
    for c in act:
        u = cunits[c]
        u = u[u["player_id"].isin(players) & u["match_id"].isin(ids)].merge(
            master, on=["player_id", "match_id"], how="inner"
        )
        pp = np.searchsorted(players, u["player_id"].to_numpy())
        arrs[c] = (pp * 2 + u["half"].to_numpy(), np.searchsorted(mids, u["match_id"].to_numpy()),
                   u["prec"].to_numpy(), (u["prec"] * u["y"]).to_numpy())  # fmt: skip

    def stat(cnt: np.ndarray) -> tuple[float, int]:
        score = np.zeros((n_pl, 2))
        for c in act:
            key, mp, prec, py = arrs[c]
            den = np.bincount(key, weights=cnt[mp] * prec, minlength=2 * n_pl).reshape(n_pl, 2)
            num = np.bincount(key, weights=cnt[mp] * py, minlength=2 * n_pl).reshape(n_pl, 2)
            with np.errstate(divide="ignore", invalid="ignore"):
                score += weights[c] * np.where(den > 0, num / den, np.nan) / sds[c]
        nh = np.bincount(m_key, weights=(cnt[m_m] > 0).astype(float), minlength=2 * n_pl).reshape(
            n_pl, 2
        )
        ok = np.isfinite(score).all(axis=1) & (nh >= min_half).all(axis=1)
        if ok.sum() < 3 or score[ok, 0].std() == 0 or score[ok, 1].std() == 0:
            return float("nan"), int(ok.sum())
        return float(np.corrcoef(score[ok, 0], score[ok, 1])[0, 1]), int(ok.sum())

    r, n = stat(np.ones(len(mids)))
    sb = float(2 * r / (1 + r)) if np.isfinite(r) and r > -1 else float("nan")
    res: dict[str, Any] = {"mode": mode, "n_players": n, "r": r, "spearman_brown": sb}
    if n_boot > 0 and np.isfinite(r):
        rng = np.random.default_rng(seed)
        vals = []
        for _ in range(n_boot):
            cnt = np.bincount(rng.integers(0, len(mids), len(mids)), minlength=len(mids)).astype(
                float
            )
            rb, _n = stat(cnt)
            if np.isfinite(rb) and rb > -1:
                vals.append(2 * rb / (1 + rb))
        v = np.asarray(vals)
        res["sb_low"] = float(np.percentile(v, 2.5)) if v.size >= 20 else None
        res["sb_high"] = float(np.percentile(v, 97.5)) if v.size >= 20 else None
        res["boot_draws"] = int(v.size)
    return res


def pri_window(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, ids: set[int], weights: dict[str, float],
    sds: dict[str, float], min_matches: int,
) -> pd.DataFrame:  # fmt: skip
    """Unshrunk PRI per player over the given matches (``ybar`` column) with its match count."""
    act = [c for c, w in weights.items() if w != 0.0]
    parts, nm = [], None
    for c in act:
        u = cunits[c]
        u = u[u["player_id"].isin(players) & u["match_id"].isin(ids)]
        pw = precision_weighted_means(rel_units(u)).set_index("player_id")
        parts.append(weights[c] * pw["ybar"] / sds[c])
        if nm is None:
            nm = pw["n_matches"]
    if not parts:
        return pd.DataFrame(columns=["player_id", "ybar", "n_matches"])
    s = pd.concat(parts, axis=1).sum(axis=1, min_count=len(parts))
    out = pd.DataFrame({"ybar": s, "n_matches": nm}).dropna().reset_index()
    return out[out["n_matches"] >= min_matches].reset_index(drop=True)


def pri_out_of_time(
    cunits: dict[str, pd.DataFrame], players: np.ndarray, early: set[int], late: set[int],
    weights: dict[str, float], sds: dict[str, float], min_early: int, min_late: int,
    min_players: int,
) -> dict[str, Any]:  # fmt: skip
    pe = pri_window(cunits, players, early, weights, sds, min_early)
    pl = pri_window(cunits, players, late, weights, sds, min_late)
    oot = out_of_time_correlation(pe, pl, min_players)
    if oot["status"] == "ESTIMATED":
        j = (
            pe.set_index("player_id")["ybar"].to_frame("a")
            .join(pl.set_index("player_id")["ybar"].rename("b"), how="inner")
        )  # fmt: skip
        _, lo, hi = player_bootstrap_spearman(j["a"], j["b"])
        oot.update({"low": lo, "high": hi})
    else:
        oot.update({"low": None, "high": None})
    return oot


# ---------------------------------------------------------------------------------------------
# IPL / T20I combination study
# ---------------------------------------------------------------------------------------------
def format_means(units: pd.DataFrame, half_min: int) -> pd.DataFrame:
    """Unshrunk precision-weighted mean and precision per player and format (``ipl``, ``t20i``)."""
    out = {}
    for f in ("IPL", "T20I"):
        uf = units[units["competition_type"] == f]
        g = uf.assign(py=uf["prec"] * uf["y"]).groupby("player_id")
        t = pd.DataFrame({"m": g["match_id"].nunique(), "P": g["prec"].sum(), "py": g["py"].sum()})
        t["ybar"] = t["py"] / t["P"]
        out[f] = t[t["m"] >= half_min]
    return out["IPL"][["ybar", "P"]].join(out["T20I"][["ybar", "P"]], lsuffix="_ipl",
                                         rsuffix="_t20i", how="inner")  # fmt: skip


def cross_format(
    per_format: pd.DataFrame, rel_ipl: float | None, rel_t20i: float | None, n_boot: int = 500,
    seed: int = SEED,
) -> dict[str, Any]:  # fmt: skip
    """Spearman (player-bootstrap interval), precision-weighted Pearson and disattenuated r."""
    n = len(per_format)
    if n < 5:
        return {"players_both_formats": n, "spearman": float("nan"), "spearman_low": float("nan"),
                "spearman_high": float("nan"), "pearson_pw": float("nan"),
                "disattenuated": float("nan"), "disattenuation_note": "TOO_FEW_PLAYERS"}  # fmt: skip
    rho, lo, hi = player_bootstrap_spearman(
        per_format["ybar_ipl"], per_format["ybar_t20i"], n=n_boot, seed=seed
    )
    w = 1.0 / (1.0 / per_format["P_ipl"] + 1.0 / per_format["P_t20i"])
    mx = np.average(per_format["ybar_ipl"], weights=w)
    my = np.average(per_format["ybar_t20i"], weights=w)
    cov = np.average((per_format["ybar_ipl"] - mx) * (per_format["ybar_t20i"] - my), weights=w)
    vx = np.average((per_format["ybar_ipl"] - mx) ** 2, weights=w)
    vy = np.average((per_format["ybar_t20i"] - my) ** 2, weights=w)
    pear = float(cov / np.sqrt(vx * vy)) if vx > 0 and vy > 0 else float("nan")
    dis, note = float("nan"), ""
    if rel_ipl and rel_t20i and rel_ipl > 0 and rel_t20i > 0 and np.isfinite(pear):
        dis = float(pear / np.sqrt(rel_ipl * rel_t20i))
        if abs(dis) > 1.0:  # a correlation cannot exceed 1: the reliabilities are too noisy to use
            dis, note = float("nan"), "OUT_OF_RANGE_RELIABILITY_TOO_NOISY"
    elif rel_ipl is not None or rel_t20i is not None:
        note = "NOT_ESTIMABLE_NONPOSITIVE_RELIABILITY"
    return {"players_both_formats": n, "spearman": rho, "spearman_low": lo, "spearman_high": hi,
            "pearson_pw": pear, "disattenuated": dis, "disattenuation_note": note}  # fmt: skip


def _cells(units: pd.DataFrame, players: np.ndarray) -> tuple[list[dict[str, Any]], float, int]:
    u = units[units["player_id"].isin(players)]
    g = u.assign(py=u["prec"] * u["y"]).groupby(["player_id", "competition_type"])
    c = pd.DataFrame({"P": g["prec"].sum(), "n": g.size(), "py": g["py"].sum()})
    c["ybar"] = c["py"] / c["P"]
    u = u.join(c["ybar"].rename("cell_mean"), on=["player_id", "competition_type"])
    ss = float((u["prec"] * (u["y"] - u["cell_mean"]) ** 2).sum())
    dof = int((c["n"] - 1).sum())
    cells = []
    for pid, d in c.reset_index().groupby("player_id", sort=True):
        f = (d["competition_type"] == "T20I").astype(int).to_numpy()
        cells.append({"player_id": pid, "f": f, "y": d["ybar"].to_numpy(), "P": d["P"].to_numpy()})
    return cells, ss, dof


def _format_nll(
    tu2: float, tv2: float, cells: list[dict[str, Any]], sigma2: float, detail: bool = False
) -> Any:  # fmt: skip
    xsx, xsy, logdet, yvy = np.zeros((2, 2)), np.zeros(2), 0.0, 0.0
    store = []
    for c in cells:
        k = len(c["y"])
        v = tu2 * np.ones((k, k)) + np.diag(tv2 + sigma2 / c["P"])
        vi = np.linalg.inv(v)
        x = np.eye(2)[c["f"]]
        xsx += x.T @ vi @ x
        xsy += x.T @ vi @ c["y"]
        yvy += float(c["y"] @ vi @ c["y"])
        logdet += float(np.linalg.slogdet(v)[1])
        store.append((vi, x))
    mu = np.linalg.solve(xsx, xsy)
    quad = yvy - 2 * mu @ xsy + mu @ xsx @ mu
    nll = 0.5 * (logdet + float(np.linalg.slogdet(xsx)[1]) + quad)
    return (nll, mu, store) if detail else nll


def fit_format_model(units: pd.DataFrame, players: np.ndarray) -> dict[str, Any]:
    """REML for ``y_if = mu_f + u_i + v_if + e_if``: common player effect and format deviation.

    ``sigma2`` is the pooled within-cell variance; ``tau_u2`` and ``tau_v2`` are estimated by REML
    (no floor imposed; a variance whose removal costs less than 1e-6 in REML deviance is reported
    as 0 with ``floor_*`` flags). The precision each format receives follows from the fit.
    """
    cells, ss, dof = _cells(units, players)
    if dof < 1:
        raise RemlError("no player has two units in a format")
    sigma2 = ss / dof
    if (
        sum(1 for c in cells if (c["f"] == 0).any()) < 3
        or sum(1 for c in cells if (c["f"] == 1).any()) < 3
    ):  # noqa: E501
        raise RemlError("fewer than three players in a format")
    scale = float(np.var(np.concatenate([c["y"] for c in cells]))) + sigma2

    def obj(t: np.ndarray) -> float:
        t = np.clip(t, -25, 3)
        return float(_format_nll(scale * np.exp(t[0]), scale * np.exp(t[1]), cells, sigma2))

    best = None
    for start in ([-3.0, -3.0], [-1.0, -4.0], [-4.0, -1.0]):
        r = minimize(
            obj,
            np.array(start),
            method="Nelder-Mead",
            options={"xatol": 1e-3, "fatol": 1e-7, "maxiter": 400},
        )  # noqa: E501
        if best is None or r.fun < best.fun:
            best = r
    tu2, tv2 = (scale * np.exp(np.clip(best.x, -25, 3))).tolist()
    nll_best = _format_nll(tu2, tv2, cells, sigma2)
    floor_u = _format_nll(0.0, tv2, cells, sigma2) - nll_best < 1e-6
    floor_v = _format_nll(tu2, 0.0, cells, sigma2) - nll_best < 1e-6
    tu2, tv2 = (0.0 if floor_u else tu2), (0.0 if floor_v else tv2)
    nll, mu, store = _format_nll(tu2, tv2, cells, sigma2, detail=True)
    rows = []
    for c, (vi, x) in zip(cells, store, strict=True):
        resid = c["y"] - x @ mu
        a = tu2 * (vi @ np.ones(len(c["y"])))
        u_hat = float(a @ resid)
        var = max(tu2 - tu2**2 * float(np.ones(len(c["y"])) @ vi @ np.ones(len(c["y"]))), 0.0)
        wf = {0: 0.0, 1: 0.0}
        for fi, ai in zip(c["f"], a, strict=True):
            wf[int(fi)] = float(ai)
        rows.append({"player_id": c["player_id"], "u_hat": u_hat, "u_se": float(np.sqrt(var)),
                     "w_ipl": wf[0], "w_t20i": wf[1], "formats": int(len(c["f"]))})  # fmt: skip
    share = tu2 / (tu2 + tv2) if tu2 + tv2 > 0 else float("nan")
    return {"tau_u2": float(tu2), "tau_v2": float(tv2), "sigma2": float(sigma2),
            "mu_ipl": float(mu[0]), "mu_t20i": float(mu[1]), "floor_common": bool(floor_u),
            "floor_format_dev": bool(floor_v), "common_share": float(share),
            "n_players": len(cells), "players": pd.DataFrame(rows).set_index("player_id")}  # fmt: skip


def combination_decision(
    spearman_low: float, n_both: int, min_players: int, threshold: float = 0.3
) -> tuple[bool, str]:  # fmt: skip
    """Predeclared rule: combine when the lower 95% bound is at least 0.3 with enough players."""
    ok = bool(np.isfinite(spearman_low) and spearman_low >= threshold and n_both >= min_players)
    return ok, (
        "COMMON_EFFECT_FORMAT_CENTRED"
        if ok
        else "FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED"
    )


# ---------------------------------------------------------------------------------------------
# rank helpers
# ---------------------------------------------------------------------------------------------
def rank_of(pri: pd.Series) -> pd.Series:
    """Deterministic rank of a PRI series (NaN stays unranked); ties by player id."""
    return point_ranking(pri.dropna()).reindex(pri.index)
