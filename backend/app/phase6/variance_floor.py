"""Variance-component and floor-behaviour investigation (EXPERIMENTAL_NOT_VALIDATED).

Question: in all 48 contexts the Phase 4 moment estimate of the between-player variance is
negative and the shrinkage floor decides ``k``. Is the true between-player variance about zero,
is the noise model misspecified, or are the samples too small to tell?

Everything is descriptive, in-sample on TRAIN and VALIDATION, and never reads TEST rows or
Cricsheet. The verdict thresholds come from the pre-declared criteria file, not from this module.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase5 import context_stats as cs
from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6 import estimators as es
from app.phase6.lockguard import assert_no_test_rows

PERIODS = {"TRAIN": ["TRAIN"], "PRE_TEST": ["TRAIN", "VALIDATION"]}
LABEL = "IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION"
VERDICTS = ("H-A_SUPPORTED", "H-B_SUPPORTED", "H-C_SUPPORTED", "MIXED", "UNIDENTIFIED")
IDENTIFICATION = ("identified_positive", "weakly_identified", "not_identified")
CONTEXT_PHASES = (cs.ALL, *cs.PHASES)
CONTEXT_SITUATIONS = (cs.ALL, *cs.SITUATIONS)


# ---------------------------------------------------------------- floor arithmetic
def floor_arithmetic_table() -> pd.DataFrame:
    """``k_for`` on a floor-hit fit (between = -1, sigma2 = 3) and on the non-finite branch.

    ``k_hand`` is computed independently of ``k_for``: ``sigma2 / (max(mult*floor, floor) *
    sigma2)`` after the floor (the multiplier is applied after the floor, so a multiplier below 1
    cannot go under the floor). Zero-shrinkage configurations give 0.
    """
    rows = []
    for name, cfg in sh.CONFIGS.items():
        for branch, fit in (
            ("floor_hit", {"sigma2": 3.0, "between": -1.0}),
            ("non_finite", {"sigma2": float("nan"), "between": float("nan")}),
        ):
            got = sh.k_for(fit, name)
            if cfg["zero"]:
                hand = 0.0
            elif branch == "floor_hit":
                hand = 3.0 / (max(cfg["mult"] * cfg["floor"], cfg["floor"]) * 3.0)
            else:
                hand = 1.0 / cfg["floor"]
            rows.append(
                {
                    "config": name, "branch": branch, "floor": cfg["floor"], "mult": cfg["mult"],
                    "k_for": float(got["k"]), "k_hand": float(hand),
                    "floor_hit": bool(got["floor_hit"]),
                    "agrees": bool(abs(got["k"] - hand) < 1e-9),
                }
            )  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- data helpers
def cd_from_context(sub: pd.DataFrame) -> tuple[rb.CellData | None, Any]:
    """``CellData`` and the ``ContextCell`` of one stored context (None when empty)."""
    if sub.empty:
        return None, None
    assert_no_test_rows(sub)
    stream = sub["stream"].iloc[0]
    cell = cs.cell_from_stats(sub, sub["comp"].iloc[0], sub["role"].iloc[0], stream)
    pi = pd.Index(cell.players).get_indexer(cell.ms["player_id"])
    mi = pd.Index(cell.matches).get_indexer(cell.ms["match_id"])
    S2 = np.zeros_like(cell.N)
    np.add.at(S2, (pi, mi), cell.ms["s2"].to_numpy(float))
    dates = sub.groupby("match_id")["match_date"].first().reindex(cell.matches).to_numpy()
    cd = rb.CellData(cell.players, cell.matches, dates, cell.match_period, cell.N.copy(),
                     cell.S.copy(), S2)  # fmt: skip
    return cd, cell


def fit_from_cd(cd: rb.CellData) -> dict[str, Any]:
    """Phase 4 ``fit_cell`` on the player table of a window (``cd`` already window-cut)."""
    n, s, s2 = cd.N.sum(1), cd.S.sum(1), cd.S2.sum(1)
    keep = n > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        n2 = (cd.N**2).sum(1)
        neff = np.where(n2 > 0, n**2 / np.where(n2 > 0, n2, 1.0), 0.0)
    pt = pd.DataFrame(
        {"n": n, "s": s, "s2": s2, "mean": s / np.where(n > 0, n, 1.0),
         "matches": (cd.N > 0).sum(1), "n_eff": neff},
        index=pd.Index(cd.players, name="player_id"),
    )[keep]  # fmt: skip
    return sh.fit_cell(pt)


def player_aggregate(
    df: pd.DataFrame, periods: list[str], value: str, count: str | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Per player sum of ``value`` and ball count within the periods (ball rows or stat rows)."""
    d = df[df["period"].isin(periods)]
    if count is None:
        g = d.groupby("player_id").agg(x=(value, "sum"), n=(value, "size"))
    else:
        g = d.groupby("player_id").agg(x=(value, "sum"), n=(count, "sum"))
    return g["x"].to_numpy(float), g["n"].to_numpy(float)


# ---------------------------------------------------------------- flags and verdicts
def identification_status(e7: dict, e6: dict, share_min: float) -> str:
    """Identification of the between variance: E7 interval and E6 share of positive draws."""
    if e7.get("status") == NOT_ESTIMABLE or e6.get("status") == NOT_ESTIMABLE:
        return NOT_ESTIMABLE
    lo, hi, share = e7.get("lo"), e7.get("hi"), e6.get("share_positive")
    if lo is None or hi is None or share is None:
        return NOT_ESTIMABLE
    if lo > 0 and share >= share_min:
        return "identified_positive"
    if lo <= 0 <= hi and share < share_min:
        return "not_identified"
    return "weakly_identified"


def verdict_from_flags(a_null: bool, a_power: bool, b_overall: bool, c: bool) -> str:
    """Flag-to-verdict table of the criteria file, evaluated in its order."""
    if a_null and a_power and not b_overall:
        return "H-A_SUPPORTED"
    if a_null and not a_power:
        return "UNIDENTIFIED"
    if b_overall and c:
        return "MIXED"
    if b_overall:
        return "H-B_SUPPORTED"
    if c:
        return "H-C_SUPPORTED"
    return "UNIDENTIFIED"


def compute_flags(
    fl: dict[str, Any],
    e7: dict,
    e6: dict,
    diag: dict,
    power: float | None,
    kish_between: float | None,
    cluster_between: float | None,
    n_star: float | str | None,
    median_balls: float | None,
) -> dict[str, Any]:
    """All H-A, H-B and H-C flags and the verdict, thresholds from the criteria ``flags``."""
    share = e6.get("share_positive")
    a_null = bool(
        e7.get("lo") is not None
        and e7["lo"] <= 0 <= e7["hi"]
        and share is not None
        and share < fl["positive_draw_share_min"]
    )
    a_power = bool(power is not None and power >= fl["power_min"])
    r = diag.get("kish_ratio_over_balls_per_match")
    hb1 = bool(
        r is not None and np.isfinite(r)
        and fl["kish_ratio_to_balls_per_match_lo"] <= r <= fl["kish_ratio_to_balls_per_match_hi"]
    )  # fmt: skip
    hb2 = bool(
        kish_between is not None
        and cluster_between is not None
        and (kish_between > 0) != (cluster_between > 0)
    )
    tv = diag.get("tercile_variance_ratio")
    hb3 = bool(
        tv is not None and np.isfinite(tv)
        and (tv > fl["tercile_variance_ratio_hi"] or tv < fl["tercile_variance_ratio_lo"])
    )  # fmt: skip

    def _gt(v: Any, t: float) -> bool:
        return bool(v is not None and np.isfinite(v) and v > t)

    hb4 = bool(
        _gt(diag.get("icc_match"), fl["icc_min"])
        or _gt(diag.get("icc_player_match"), fl["icc_min"])
        or _gt(diag.get("pearson_dispersion"), fl["pearson_dispersion_min"])
    )
    n_ok = hb1 + hb2 + hb3 + hb4
    hb_overall = bool(
        n_ok >= fl["min_supported_of_hb_i_to_iv"] and (hb2 or not fl["hb_overall_requires_hb_ii"])
    )
    lower_pos = bool(
        (e7.get("lo") is not None and e7["lo"] > 0) or (e6.get("lo") is not None and e6["lo"] > 0)
    )
    hc = bool(
        lower_pos
        and isinstance(n_star, (int, float))
        and np.isfinite(n_star)
        and median_balls is not None
        and n_star > median_balls
    )
    return {
        "flag_H-A_null": a_null, "flag_H-A_power": a_power, "flag_H-B_i": hb1,
        "flag_H-B_ii": hb2, "flag_H-B_iii": hb3, "flag_H-B_iv": hb4,
        "flag_H-B_overall": hb_overall, "flag_H-C": hc,
        "verdict": verdict_from_flags(a_null, a_power, hb_overall, hc),
    }  # fmt: skip


# ---------------------------------------------------------------- one unit
def _est_row(meta: dict, window: str, estimator: str, basis: str, r: dict, players: int) -> dict:
    return {
        **meta, "window": window, "estimator": estimator, "noise_basis": basis,
        "value": r.get("value"), "between_raw": r.get("between"), "status": r["status"],
        "converged": r.get("converged"), "lo": r.get("lo"), "hi": r.get("hi"),
        "share_positive": r.get("share_positive"), "players": players,
        "note": r.get("note"), "label": LABEL,
    }  # fmt: skip


def _f(x: Any) -> float | None:
    return None if x is None or not np.isfinite(x) else float(x)


def analyse_unit(
    cd: rb.CellData,
    w: np.ndarray,
    window: str,
    meta: dict[str, Any],
    crit: dict[str, Any],
    inv_cfg: dict[str, Any],
    seed: int,
    ball_counts: tuple[np.ndarray, np.ndarray] | None = None,
    binary: bool = False,
    count_stream: bool = False,
) -> tuple[list[dict], dict[str, Any]]:
    """Estimator rows (long format) and one diagnostics row for one unit and window.

    ``ball_counts`` are per-player (successes or counts, balls) for the window and feed E4 (when
    ``binary``) or E5 (when ``count_stream``); both are sensitivity only.
    """
    fl = crit["variance_floor"]["flags"]
    rows: list[dict] = []
    diag: dict[str, Any] = {**meta, "window": window, "label": LABEL}
    cols = rb.window_cols(cd, window)
    sub, ws = cd.select_cols(cols), w[cols]
    min_pl = int(inv_cfg["min_train_players_for_fit"])
    n_players = int((sub.total_balls > 0).sum()) if sub.N.size else 0
    diag.update(players=n_players, matches=int(sub.N.shape[1]))
    if n_players < min_pl or sub.N.shape[1] < 2:
        diag.update(verdict=NOT_ESTIMABLE, identification=NOT_ESTIMABLE,
                    reason="TOO_FEW_PLAYERS_OR_MATCHES")  # fmt: skip
        return rows, diag

    one = np.ones((sub.N.shape[1], 1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        pt = rb.boot_moments(sub, one)
        dp = rb.decompose_moments(pt, 1)
        e6 = es.cluster_bootstrap(sub, ws, 1)
        diagn = es.dispersion_diagnostics(sub, 1)
        e7_rows = {
            mb: rb.split_cov_rows(cd, w, window, [mb]) for mb in inv_cfg["min_balls_variants"]
        }
    sigma2 = float(dp["sigma2"][0])
    between_raw: dict[str, float | None] = {}
    for b in rb.BASES:
        ok = dp[f"{b}_ok"][:, 0]
        y, v = dp["mean"][ok, 0], dp[f"{b}_noise_i"][ok, 0]
        e1 = es.tau2_moments_floor(y, v, sigma2)
        between_raw[b] = e1.get("between")
        label = {"phase4_kish": "E1", "ball_independent": "E1b", "match_cluster": "E1c"}[b]
        rows.append(_est_row(meta, window, label, b, e1, int(ok.sum())))
        rows.append(_est_row(meta, window, "E2", b, es.tau2_reml(y, v), int(ok.sum())))
        rows.append(_est_row(meta, window, "E3", b, es.tau2_ml(y, v), int(ok.sum())))
        rows.append(_est_row(meta, window, "E6", b, e6[b], int(ok.sum())))
    for mb, rr in e7_rows.items():
        for r in rr:
            res = {"value": r["tau2_moment"], "status": r["status"], "converged": True,
                   "lo": r["tau2_boot_lo"], "hi": r["tau2_boot_hi"],
                   "share_positive": r["boot_share_tau2_positive"],
                   "note": f"min_balls={mb}"}  # fmt: skip
            rows.append(_est_row(meta, window, "E7", f"split_half_covariance|min_balls={mb}",
                                 res, int(r["players"])))  # fmt: skip
    # E4 and E5: sensitivity only, never a verdict input
    if ball_counts is not None and binary:
        r4 = es.tau2_beta_binomial(*ball_counts)
        rows.append(_est_row(meta, window, "E4", "beta_binomial", r4, len(ball_counts[0])))
    if ball_counts is not None and count_stream:
        r5 = es.tau2_gamma_poisson(*ball_counts)
        r5["note"] = "MISSPECIFIED_FOR_RUNS"
        rows.append(_est_row(meta, window, "E5", "gamma_poisson", r5, len(ball_counts[0])))

    # verdict inputs: E7 at 6 balls per half (12 total), E6 on the match-cluster basis
    mb_v = max(inv_cfg["min_balls_variants"])
    e7r = e7_rows[mb_v][0] if e7_rows[mb_v] else {}
    e7 = {"status": e7r.get("status", NOT_ESTIMABLE), "value": e7r.get("tau2_moment"),
          "lo": e7r.get("tau2_boot_lo"), "hi": e7r.get("tau2_boot_hi"),
          "sigma_eff": e7r.get("sigma_eff_for_projection")}  # fmt: skip
    e6c = e6["match_cluster"]
    ident = identification_status(e7, e6c, fl["positive_draw_share_min"])

    ratios = list(inv_cfg["detectability"]["tau2_over_sigma2_grid"])
    okc = dp["match_cluster_ok"][:, 0]
    sim = rb.simulate_detectability(dp["match_cluster_noise_i"][okc, 0], sigma2, ratios,
                                    int(inv_cfg["detectability"]["replications"]), seed)  # fmt: skip
    power = next((s.get("share_estimate_positive") for s in sim
                  if abs(s["tau2_over_sigma2"] - fl["power_ratio"]) < 1e-12), None)  # fmt: skip

    # H-C input: required balls for R = 0.5 from the source whose lower bound is positive
    src_tau2, src_sig = None, None
    if e7.get("lo") is not None and e7["lo"] > 0:
        src_tau2, src_sig = e7["value"], e7["sigma_eff"]
    elif e6c.get("lo") is not None and e6c["lo"] > 0:
        cl = next(
            (
                r
                for r in rb.variance_rows(cd, w, window, [1])
                if r["noise_basis"] == "match_cluster"
            ),
            {},
        )
        src_tau2, src_sig = cl.get("tau2_moment"), cl.get("sigma_eff_for_projection")
    proj = {t["target_reliability"]: t["required_n"]
            for t in rb.required_sample(src_tau2, src_sig, tuple(inv_cfg["reliability_targets"]), "balls")}  # fmt: skip
    n_star = proj.get(0.5)
    flags = compute_flags(fl, e7, e6c, diagn, power, between_raw.get("phase4_kish"),
                          between_raw.get("match_cluster"), n_star, diagn.get("median_balls"))  # fmt: skip

    if ident == NOT_ESTIMABLE:
        flags["verdict"] = NOT_ESTIMABLE
        flags["reason"] = "E7_OR_E6_NOT_ESTIMABLE"

    fit = fit_from_cd(sub)
    kcols: dict[str, Any] = {}
    for cfg_name in sh.CONFIGS:
        kk = sh.k_for(fit, cfg_name)
        kcols[f"k_{cfg_name}"] = _f(kk["k"])
    kinfo = sh.k_for(fit, inv_cfg["shrinkage_config"])
    diag.update(
        sigma2=_f(sigma2), between_kish=_f(between_raw.get("phase4_kish")),
        between_ball_independent=_f(between_raw.get("ball_independent")),
        between_match_cluster=_f(between_raw.get("match_cluster")),
        floor_hit=bool(kinfo["floor_hit"]), fit_between=_f(fit["between"]),
        fit_sigma2=_f(fit["sigma2"]), fit_players=int(fit["players"]),
        e7_value=_f(e7["value"]), e7_lo=_f(e7["lo"]), e7_hi=_f(e7["hi"]),
        e6_cluster_median=_f(e6c.get("value")), e6_cluster_lo=_f(e6c.get("lo")),
        e6_cluster_hi=_f(e6c.get("hi")), e6_share_positive=_f(e6c.get("share_positive")),
        power_at_declared_ratio=_f(power),
        **{k: (_f(v) if isinstance(v, float) else v) for k, v in diagn.items()
           if k not in ("status", "players_valid", "sigma2")},
        n_star_r050=n_star if isinstance(n_star, str) else _f(n_star),
        n_star_r070=proj.get(0.7) if isinstance(proj.get(0.7), str) else _f(proj.get(0.7)),
        n_star_r080=proj.get(0.8) if isinstance(proj.get(0.8), str) else _f(proj.get(0.8)),
        identification=ident, status=ESTIMATED, **kcols, **flags,
    )  # fmt: skip
    return rows, diag


# ---------------------------------------------------------------- runners
def context_keys() -> list[tuple[str, str, str, str]]:
    return [
        (c, r, p, s)
        for c in ("IPL", "T20I")
        for r in ("batter", "bowler")
        for p in CONTEXT_PHASES
        for s in CONTEXT_SITUATIONS
    ]


def run_contexts(
    stats: pd.DataFrame, crit: dict, inv_cfg: dict, n_boot: int, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """All 48 contexts, both windows. ``stats`` is ``p5_context_stats`` (TRAIN + VALIDATION)."""
    cs.check_stats(stats)
    gm, W = cs.global_match_weights(stats, n_boot, seed)
    est, dg = [], []
    for key in context_keys():
        comp, role, phase, situation = key
        meta = {"unit_kind": "context", "definition": "any|q0.75", "format": comp, "role": role,
                "stream": en.PRIMARY[role][0], "phase": phase, "situation": situation}  # fmt: skip
        sub = cs.select(stats, comp, role, phase, situation)
        cd, cell = cd_from_context(sub)
        for window in ("TRAIN", "PRE_TEST"):
            if cd is None:
                dg.append({**meta, "window": window, "players": 0, "verdict": NOT_ESTIMABLE,
                           "identification": NOT_ESTIMABLE, "reason": "NO_PRESSURE_ROWS"})  # fmt: skip
                continue
            w = en.cell_weights(cell, gm, W)
            counts = None
            if "e" in sub.columns:
                d = sub.assign(actual=sub["s"] + sub["e"])
                counts = player_aggregate(d, PERIODS[window], "actual", "n")
            r, d_ = analyse_unit(cd, w, window, meta, crit, inv_cfg, seed, counts,
                                 binary=False, count_stream=True)  # fmt: skip
            est += r
            dg.append(d_)
    return pd.DataFrame(est), pd.DataFrame(dg)


def run_stream_cells(
    study: Any, defns: list[str], crit: dict, inv_cfg: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every (definition, format, role, stream) cell of the study, both windows."""
    est, dg = [], []
    for defn in defns:
        for key, cell in study.all_cells(defn).items():
            comp, role, stream = key
            assert_no_test_rows(cell.rows)
            cd = rb.from_cell(cell)
            w = en.cell_weights(cell, study.gm, study.W)
            primary = stream == en.PRIMARY[role][0]
            binary = stream in ("dismissal", "wkt")
            meta = {"unit_kind": "stream_cell", "definition": defn, "format": comp, "role": role,
                    "stream": stream, "phase": "ALL", "situation": "ALL",
                    "is_primary_stream": primary}  # fmt: skip
            for window in ("PRE_TEST", "TRAIN"):
                counts = player_aggregate(cell.rows, PERIODS[window], "actual")
                r, d_ = analyse_unit(cd, w, window, meta, crit, inv_cfg, study.seed, counts,
                                     binary=binary, count_stream=not binary)  # fmt: skip
                est += r
                dg.append(d_)
    return pd.DataFrame(est), pd.DataFrame(dg)
