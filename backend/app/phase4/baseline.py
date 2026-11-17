"""Phase 4 Stage B: train-frozen calibrated stratified empirical-Bayes baselines (B0).

Cell hierarchy and shrinkage strengths follow ``app.analytics.baseline_engine``
(``comp|role|phase|wbin`` -> ``comp|role|phase`` -> ``comp|role`` -> ``comp``). All cell tables,
shrinkage strengths, wickets-remaining bins and format offsets are fitted on TRAIN rows only and
applied unchanged to later periods. TRAIN rows use the engine's leave-player-out expectation, so a
player's own deliveries never enter the expectation of that player's own residual.

Calibration identity: one additive offset per format is fitted on TRAIN so that, on TRAIN, the
pooled expectation sums to the actual outcome in each format. Out-of-period calibration is then
measured on VALIDATION. B0 has no pressure term.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.analytics import baseline_engine as be
from app.analytics import pressure_features as pf
from app.analytics.shrinkage import beta_binomial_shrink, k_from_children, shrink_to_parent
from app.phase4.lockguard import guard_frame
from app.phase4.split import Split, TestLock, attach_period

BASELINE_VERSION = "p4_baseline_b0_train_frozen_v1"
DEFAULT_PARAMS = {"min_cell_innings": 30, "tau2_floor": 0.01}
STREAMS = (
    ("batter", "runs", False),
    ("batter", "dismissal", True),
    ("bowler", "charged", False),
    ("bowler", "wkt", True),
)


def prepare_frame(df_raw: pd.DataFrame, split: Split, min_cell_innings: int = 30):
    """Attach period, populations and TRAIN-only wickets-remaining bins to a state frame."""
    d = pf.add_populations(attach_period(df_raw, split)).reset_index(drop=True)
    wb = pf.wicket_bins_for(d[d["period"] == "TRAIN"], min_cell_innings)
    d["wbin"] = d["wickets_remaining"].map(wb["labels"])
    return d, wb


def role_frame(role: str, d: pd.DataFrame) -> pd.DataFrame:
    return be.batter_frame(d) if role == "batter" else be.bowler_frame(d)


def level_keys(d: pd.DataFrame, first_level: int = 0) -> list[np.ndarray]:
    comp = d["competition_type"].astype(str)
    role = d["role_ctx"].astype(str)
    ph = d["innings_phase"].astype(str)
    wb = d["wbin"].astype(str)
    return [
        (comp + "|" + role + "|" + ph + "|" + wb).to_numpy(),
        (comp + "|" + role + "|" + ph).to_numpy(),
        (comp + "|" + role).to_numpy(),
        comp.to_numpy(),
    ][first_level:]


@dataclass
class FrozenBaseline:
    """Cell tables fitted on one set of rows. ``apply`` never refits."""

    stream: str
    binary: bool
    min_cell_innings: int
    tau2_floor: float
    uniques: list[pd.Index]
    value: list[np.ndarray]
    distinct: list[np.ndarray]
    offsets: dict[str, float] = field(default_factory=dict)
    first_level: int = 0
    use_offsets: bool = True

    @classmethod
    def fit(cls, d: pd.DataFrame, stream: str, binary: bool, params: dict) -> FrozenBaseline:
        y = d[stream].to_numpy(dtype=float)
        inn = pd.factorize(d["inn_key"])[0]
        codes, uniques = [], []
        first = int(params.get("first_level", 0))
        for kk in level_keys(d, first):
            c, u = pd.factorize(kk, sort=True)
            codes.append(c)
            uniques.append(pd.Index(u))
        nL = len(codes)
        floor = float(params["tau2_floor"])
        n_l, s_l, s2_l, kish_l, dist_l = [], [], [], [], []
        for c in codes:
            K = int(c.max()) + 1
            n_l.append(np.bincount(c, minlength=K).astype(float))
            s_l.append(np.bincount(c, weights=y, minlength=K))
            s2_l.append(np.bincount(c, weights=y * y, minlength=K))
            kish, dist = be._kish_per_cell(c, inn, K)
            kish_l.append(kish)
            dist_l.append(dist)
        mean_l = [s / np.where(n > 0, n, 1) for s, n in zip(s_l, n_l, strict=True)]
        k_l = [np.zeros(len(n)) for n in n_l]
        parent = []
        for li in range(nL - 1):
            par = np.zeros(len(n_l[li]), dtype=np.int64)
            par[codes[li]] = codes[li + 1]
            parent.append(par)
            for p in np.unique(par):
                ch = np.where(par == p)[0]
                ss = s2_l[li][ch] - s_l[li][ch] ** 2 / np.where(n_l[li][ch] > 0, n_l[li][ch], 1)
                kk = k_from_children(n_l[li][ch], kish_l[li][ch], mean_l[li][ch], ss, floor)
                k_l[li][ch] = kk["k"]
        value: list[np.ndarray] = [np.empty(0)] * nL
        value[-1] = mean_l[-1]
        for li in range(nL - 2, -1, -1):
            vp = value[li + 1][parent[li]]
            if binary:
                value[li] = beta_binomial_shrink(s_l[li], n_l[li], kish_l[li], vp, k_l[li])
            else:
                value[li] = shrink_to_parent(kish_l[li], mean_l[li], vp, k_l[li])
        return cls(
            stream,
            binary,
            int(params["min_cell_innings"]),
            floor,
            uniques,
            value,
            dist_l,
            first_level=first,
            use_offsets=not params.get("no_offset", False),
        )

    def apply(self, d: pd.DataFrame) -> dict[str, np.ndarray]:
        """Frozen expected value per row (before the format offset), level used, coverage."""
        keys = level_keys(d, self.first_level)
        nL = len(keys)
        idx = [self.uniques[li].get_indexer(keys[li]) for li in range(nL)]
        seen = [i >= 0 for i in idx]
        res: list[np.ndarray] = [np.empty(0)] * nL
        res[-1] = np.where(seen[-1], self.value[-1][np.maximum(idx[-1], 0)], np.nan)
        for li in range(nL - 2, -1, -1):
            res[li] = np.where(seen[li], self.value[li][np.maximum(idx[li], 0)], res[li + 1])
        chosen = np.full(len(d), nL - 1)
        done = np.zeros(len(d), dtype=bool)
        for li in range(nL):
            ok = seen[li] & (self.distinct[li][np.maximum(idx[li], 0)] >= self.min_cell_innings)
            take = ok & ~done
            chosen[take] = li
            done |= take
        return {
            "expected": np.choose(chosen, res),
            "level_used": chosen,
            "finest_cell_seen": seen[0],
        }

    def set_offsets(self, d: pd.DataFrame, expected: np.ndarray) -> None:
        y = d[self.stream].to_numpy(dtype=float)
        comp = d["competition_type"].to_numpy()
        for c in np.unique(comp):
            m = comp == c
            self.offsets[str(c)] = float(np.mean(y[m] - expected[m]))

    def calibrate(self, d: pd.DataFrame, expected: np.ndarray) -> np.ndarray:
        off = d["competition_type"].astype(str).map(self.offsets).to_numpy(dtype=float)
        off = np.where(np.isfinite(off), off, 0.0) if self.use_offsets else np.zeros(len(d))
        out = expected + off
        return np.clip(out, 0.0, 1.0) if self.binary else out


@dataclass
class BaselineSet:
    """Frozen baselines for every (role, stream), with TRAIN leave-player-out expectations."""

    frozen: dict[tuple[str, str], FrozenBaseline]
    train_lpo: dict[tuple[str, str], pd.Series]
    params: dict[str, Any]
    wickets_bins: dict[str, Any]
    version: str = BASELINE_VERSION

    def expected(
        self, role: str, stream: str, frame: pd.DataFrame, lock: TestLock | None = None
    ) -> pd.DataFrame:
        """Calibrated expectation per row; TRAIN rows use leave-player-out values."""
        if lock is not None:
            guard_frame(frame, lock, "BaselineSet.expected")
        fb = self.frozen[(role, stream)]
        app = fb.apply(frame)
        exp = fb.calibrate(frame, app["expected"])
        basis = np.full(len(frame), "FROZEN_TRAIN_TABLES", dtype=object)
        is_train = (frame["period"] == "TRAIN").to_numpy()
        if is_train.any():
            lpo = self.train_lpo[(role, stream)].reindex(frame["_src_index"].to_numpy())
            lpo_v = fb.calibrate(frame, lpo.to_numpy())
            exp = np.where(is_train, lpo_v, exp)
            basis[is_train] = "TRAIN_LEAVE_PLAYER_OUT"
        return pd.DataFrame(
            {
                "expected": exp,
                "level_used": app["level_used"],
                "finest_cell_seen": app["finest_cell_seen"],
                "basis": basis,
            },
            index=frame.index,
        )


def fit_baseline_set(
    d: pd.DataFrame, params: dict | None = None, version: str = BASELINE_VERSION
) -> BaselineSet:
    """Fit all streams on TRAIN rows of a prepared frame (refuses any other period)."""
    params = params or DEFAULT_PARAMS
    train = d[d["period"] == "TRAIN"]
    frozen: dict = {}
    lpo: dict = {}
    for role, stream, binary in STREAMS:
        fr = role_frame(role, train)
        fb = FrozenBaseline.fit(fr, stream, binary, params)
        fb.set_offsets(fr, fb.apply(fr)["expected"])
        frozen[(role, stream)] = fb
        pl = pd.factorize(fr["competition_type"] + "|" + fr["player_id"].astype(str))[0]
        e = be.expected_values(
            fr[stream].to_numpy(dtype=float),
            be.level_codes(fr)[int(params.get("first_level", 0)) :],
            pd.factorize(fr["inn_key"])[0],
            pl,
            binary,
            params["min_cell_innings"],
            params["tau2_floor"],
        )["expected"]
        lpo[(role, stream)] = pd.Series(e, index=fr["_src_index"].to_numpy())
    wb = pf.wicket_bins_for(train, params["min_cell_innings"])
    return BaselineSet(
        frozen, lpo, dict(params), {k: v for k, v in wb.items() if k != "cells"}, version
    )


# ---------------------------------------------------------------- diagnostics
def _grp(t: pd.DataFrame, by) -> list[dict]:
    g = t.groupby(by, observed=True).agg(
        rows=("y", "size"), actual=("y", "mean"), expected=("e", "mean")
    )
    g["residual"] = g["actual"] - g["expected"]
    return [{"group": str(i), **{k: float(v) for k, v in r.items()}} for i, r in g.iterrows()]


def calibration_report(bs: BaselineSet, d: pd.DataFrame) -> dict[str, Any]:
    """Identity, out-of-period calibration, residual distribution, coverage, drift."""
    out: dict[str, Any] = {"baseline_version": bs.version, "streams": {}}
    for role, stream, _ in STREAMS:
        fr = role_frame(role, d)
        ex = bs.expected(role, stream, fr)
        t = pd.DataFrame(
            {
                "y": fr[stream].to_numpy(dtype=float),
                "e": ex["expected"].to_numpy(),
                "period": fr["period"].to_numpy(),
                "fmt": fr["competition_type"].to_numpy(),
                "phase": fr["innings_phase"].astype(str).to_numpy(),
                "wbin": fr["wbin"].astype(str).to_numpy(),
                "year": fr["match_date"].dt.year.to_numpy(),
                "level": ex["level_used"].to_numpy(),
                "seen": ex["finest_cell_seen"].to_numpy(),
            }
        )
        t["r"] = t["y"] - t["e"]
        fb = bs.frozen[(role, stream)]
        tr = fr[fr["period"] == "TRAIN"]
        pooled = fb.calibrate(tr, fb.apply(tr)["expected"])
        ident = {}
        for c in sorted(tr["competition_type"].unique()):
            m = (tr["competition_type"] == c).to_numpy()
            a, e = float(tr[stream].to_numpy()[m].sum()), float(pooled[m].sum())
            ident[c] = {"sum_actual": a, "sum_expected": e, "rel_diff": abs(a - e) / max(a, 1e-12)}
        s: dict[str, Any] = {"calibration_identity_train_pooled": ident, "periods": {}}
        for p in sorted(t["period"].unique()):
            tp = t[t["period"] == p]
            qs = tp["r"].quantile([0.01, 0.25, 0.5, 0.75, 0.99])
            blk: dict[str, Any] = {
                "rows": int(len(tp)),
                "mean_residual": float(tp["r"].mean()),
                "residual_sd": float(tp["r"].std()),
                "residual_quantiles": {str(k): float(v) for k, v in qs.items()},
                "level_usage": {str(k): int(v) for k, v in tp["level"].value_counts().items()},
                "fallback_rows_finest_cell_unseen": int((~tp["seen"]).sum()),
                "by_format": _grp(tp, "fmt"),
                "by_phase": _grp(tp, ["fmt", "phase"]),
                "by_wickets_remaining_bin": _grp(tp, ["fmt", "wbin"]),
                "by_year": _grp(tp, ["fmt", "year"]),
            }
            dec = pd.qcut(tp["e"].rank(method="first"), 10, labels=False, duplicates="drop")
            blk["by_expected_decile"] = _grp(tp.assign(dec=dec), "dec")
            s["periods"][p] = blk
        out["streams"][f"{role}:{stream}"] = s
    return out


def identity_ok(report: dict[str, Any], tol: float = 1e-6) -> bool:
    return all(
        v["rel_diff"] <= tol
        for s in report["streams"].values()
        for v in s["calibration_identity_train_pooled"].values()
    )
