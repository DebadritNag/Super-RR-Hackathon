"""Bowler-specific pressure signal candidates. SENSITIVITY_ONLY, never feeds the API.

The primary definition applies BATTER-state signals to bowler rows: it flags innings-1 rows where
the batting side is BEHIND the strictly prior par and chase rows with a high required rate. Those
are good states for a bowler, not hard ones. The three candidates below (declared in
``config/phase5_investigation_v1.json`` before any run) flag states in which the bowling side is
under pressure. Thresholds come from TRAIN rows only, per format. They do not replace the primary
definition and nothing is selected on their results.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics import pressure_features as pf
from app.phase4.constants import SCOPE

LABEL = "SENSITIVITY_ONLY_NOT_A_REPLACEMENT_NOT_VALIDATED"


class CandidateNotBuildable(RuntimeError):
    """A candidate needs a column that the state frame does not hold."""


def _need(d: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in d.columns]
    if missing:
        raise CandidateNotBuildable(f"missing columns {missing}")


def _q(x: pd.Series, q: float) -> float:
    x = x.dropna().to_numpy(float)
    return pf.lower_quantile(x, q) if len(x) else float("nan")


def build_flags(
    d: pd.DataFrame, cfg: dict[str, Any]
) -> dict[str, tuple[pd.Series, pd.Series, dict[str, float]]]:
    """candidate id -> (pressure flag, comparison population, TRAIN-only thresholds).

    Candidates whose columns are missing are omitted from the result and listed by
    ``not_buildable``.
    """
    q = float(cfg["quantile"])
    train = d["period"] == "TRAIN"
    unavail = d["par_unavailable_insufficient_prior"].fillna(False).astype(bool)
    dev = -d["neg_par_dev_prior"]
    out: dict[str, tuple[pd.Series, pd.Series, dict[str, float]]] = {}
    for c in cfg["candidates"]:
        cid = c["id"]
        try:
            if cid == "bowler_defence_margin":
                _need(d, ["projected_surplus", "neg_par_dev_prior", "chase_pop", "inn1_pop"])
                pop = d["chase_pop"] | (d["inn1_pop"] & ~unavail)
                flag = pd.Series(False, index=d.index)
                thr: dict[str, float] = {}
                for comp in SCOPE:
                    inc = d["competition_type"] == comp
                    tc = _q(d.loc[train & inc & d["chase_pop"], "projected_surplus"], q)
                    ti = _q(dev[train & inc & d["inn1_pop"] & ~unavail], q)
                    thr[f"chase_surplus|{comp}"], thr[f"inn1_par_dev|{comp}"] = tc, ti
                    flag |= d["chase_pop"] & inc & (d["projected_surplus"] >= tc)
                    flag |= d["inn1_pop"] & ~unavail & inc & (dev >= ti)
            elif cid == "bowler_death_close_gap":
                _need(d, ["gap", "innings_phase", "chase_pop"])
                pop = d["chase_pop"] & (d["innings_phase"] == "death")
                flag = pd.Series(False, index=d.index)
                thr = {}
                for comp in SCOPE:
                    inc = d["competition_type"] == comp
                    ag = d["gap"].abs()
                    t = _q(ag[train & inc & pop], 1.0 - q)
                    thr[f"abs_gap_q{1.0 - q:.2f}|{comp}"] = t
                    flag |= pop & inc & (ag <= t)
            elif cid == "bowler_death_wickets_in_hand":
                _need(d, ["wickets_remaining", "innings_phase", "base_pop"])
                pop = d["base_pop"] & (d["innings_phase"] == "death")
                flag = pd.Series(False, index=d.index)
                thr = {}
                for comp in SCOPE:
                    inc = d["competition_type"] == comp
                    t = _q(d.loc[train & inc & pop, "wickets_remaining"].astype(float), q)
                    thr[f"wickets_remaining|{comp}"] = t
                    flag |= pop & inc & (d["wickets_remaining"] >= t)
            else:
                raise CandidateNotBuildable(f"unknown candidate '{cid}'")
        except CandidateNotBuildable:
            continue
        out[cid] = (flag.fillna(False), pop.fillna(False), thr)
    return out


def not_buildable(cfg: dict[str, Any], built: dict[str, Any]) -> list[str]:
    return [c["id"] for c in cfg["candidates"] if c["id"] not in built]


def candidate_pressure_rows(
    base_rows: pd.DataFrame, flag: pd.Series, pop: pd.Series
) -> pd.DataFrame:
    """Tag a base-row table (from ``engine.base_rows``) with a candidate flag and population."""
    out = base_rows.copy()
    out["in_pop"] = pop.reindex(out["src"]).to_numpy()
    out["press"] = flag.reindex(out["src"]).to_numpy() & out["in_pop"].to_numpy()
    return out[out["press"]]
