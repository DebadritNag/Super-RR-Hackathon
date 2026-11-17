"""Phase 4 Stage C: experimental player pressure scoring. EXPERIMENTAL_NOT_VALIDATED.

Pressure sample by definition id (``chase|q0.9`` is the provisional leading candidate, never
the validated one). Quantile thresholds are computed on TRAIN rows only. The chase signal is the
pre-delivery required rate; the innings-1 signal is the deviation from the STRICTLY PRIOR par
(rows without enough prior matches are never flagged). Batters and bowlers use the same state
signals here (the bowler-specific signal of the design notes is a Chunk 3 item).

Residual = actual minus the calibrated B0 expectation. Scoring window = TRAIN + VALIDATION
(PRE_TEST); k and the shrink target come from TRAIN only. TEST rows are refused unless
``evaluate_on_test`` has opened the lock. Eligibility here is the Phase 3 PLACEHOLDER rule.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.analytics import pressure_features as pf
from app.phase4 import shrink as sh
from app.phase4.baseline import STREAMS, BaselineSet, role_frame
from app.phase4.constants import OFFICIAL_RANKING, SCOPE, SEED, STATUS
from app.phase4.lockguard import guard_frame
from app.phase4.par import LeakageGuard, strictly_prior_par
from app.phase4.split import TestLock, evaluate_on_test

DEFINITION_VERSION = "p4_pressure_def_v1"
LEADING_DEFINITION = "chase|q0.9"
WINDOW_PRE_TEST = "PRE_TEST"
PLACEHOLDER_MIN_BALLS = {"batter": 24, "bowler": 36}
ELIG_PLACEHOLDER = "PHASE3_PLACEHOLDER"
SIGNAL_COLUMNS = ("rrr", "neg_par_dev_prior")


class PressureRecord(BaseModel):
    """Full experimental record schema (Stage C)."""

    status: str = STATUS
    official_ranking: bool = OFFICIAL_RANKING
    player_id: int
    role: str
    stream: str
    format: str
    window: str
    definition_id: str
    definition_version: str = DEFINITION_VERSION
    baseline_version: str
    shrinkage_config: str
    raw_pressure_outcome: float | None
    expected_baseline_outcome: float | None
    residual: float | None
    shrunk_estimate: float | None
    interval_low: float | None
    interval_high: float | None
    posterior_sd: float | None
    data_weight: float | None
    shrinkage_k: float | None
    shrinkage_floor_hit: bool | None
    pressure_opportunities: int
    distinct_matches: int
    effective_sample_size: float
    eligibility_status: str
    eligibility_basis: str = ELIG_PLACEHOLDER
    applied_restrictions: str


RESTRICTIONS = (
    "innings 1-2 only; IPL/T20I only; DLS-affected innings excluded (not imputed); "
    "innings-1 par strictly prior (insufficient prior => not flagged); thresholds TRAIN-only; "
    "TEST excluded"
)


def parse_definition(defn_id: str) -> tuple[str, float]:
    ctx, q = defn_id.split("|q")
    if ctx not in ("chase", "inn1", "any"):
        raise ValueError(f"unknown context in definition '{defn_id}'")
    return ctx, float(q)


def add_signals(d: pd.DataFrame, lock: TestLock | None = None) -> pd.DataFrame:
    """Add the strictly prior par deviation; no LOMO column is read or created."""
    if lock is not None:
        guard_frame(d, lock, "add_signals")
    LeakageGuard.check_columns(list(SIGNAL_COLUMNS))
    par = strictly_prior_par(d)
    out = d.copy()
    out["neg_par_dev_prior"] = -(out["team_runs_before"] - par["par_runs_prior"])
    out["par_unavailable_insufficient_prior"] = par["par_unavailable_insufficient_prior"]
    return out


def fit_thresholds(d: pd.DataFrame, q: float) -> dict[str, float]:
    """Lower-quantile thresholds per format and context from TRAIN base populations only."""
    if not (d["period"] == "TRAIN").all():
        raise ValueError("thresholds must be fitted on TRAIN rows only")
    thr: dict[str, float] = {}
    for comp in SCOPE:
        c = d[d["chase_pop"] & (d["competition_type"] == comp)]["rrr"].dropna().to_numpy()
        i = d[d["inn1_pop"] & (d["competition_type"] == comp)]["neg_par_dev_prior"].dropna()
        thr[f"chase|{comp}"] = pf.lower_quantile(c, q) if len(c) else float("nan")
        thr[f"inn1|{comp}"] = pf.lower_quantile(i.to_numpy(), q) if len(i) else float("nan")
    return thr


def pressure_flag(d: pd.DataFrame, defn_id: str, thr: dict[str, float]) -> pd.Series:
    ctx, _ = parse_definition(defn_id)
    flag = pd.Series(False, index=d.index)
    for comp in SCOPE:
        inc = d["competition_type"] == comp
        if ctx in ("chase", "any"):
            t = thr[f"chase|{comp}"]
            flag |= d["chase_pop"] & inc & (d["rrr"] >= t)
        if ctx in ("inn1", "any"):
            t = thr[f"inn1|{comp}"]
            flag |= d["inn1_pop"] & inc & (d["neg_par_dev_prior"] >= t)
    return flag.fillna(False)


def residual_rows(
    d: pd.DataFrame,
    bs: BaselineSet,
    defn_id: str,
    thr: dict[str, float],
    role: str,
    stream: str,
    lock: TestLock,
) -> pd.DataFrame:
    """Pressure rows of one role/stream with actual, expected and residual."""
    guard_frame(d, lock, "residual_rows")
    flag = pressure_flag(d, defn_id, thr)
    fr = role_frame(role, d)
    ex = bs.expected(role, stream, fr)
    keep = flag.reindex(fr["_src_index"]).to_numpy()
    t = pd.DataFrame(
        {
            "player_id": fr["player_id"].to_numpy(),
            "match_id": fr["match_id"].to_numpy(),
            "comp": fr["competition_type"].to_numpy(),
            "period": fr["period"].to_numpy(),
            "actual": fr[stream].to_numpy(dtype=float),
            "expected": ex["expected"].to_numpy(),
        }
    )[keep]
    t["resid"] = t["actual"] - t["expected"]
    return t.reset_index(drop=True)


def _num(x: float) -> float | None:
    return None if x is None or not np.isfinite(x) else float(x)


def score_cell(
    rows: pd.DataFrame,
    role: str,
    stream: str,
    comp: str,
    defn_id: str,
    baseline_version: str,
    config: str,
    n_boot: int = 1000,
    seed: int = SEED,
    window: str = WINDOW_PRE_TEST,
    min_balls: int | None = None,
    elig: dict[str, Any] | None = None,
) -> tuple[list[PressureRecord], dict[str, Any]]:
    """Records for one (role, stream, format) cell. TRAIN rows give k and mu_{-i}."""
    r = rows[rows["comp"] == comp]
    tr = r[r["period"] == "TRAIN"]
    fit = sh.fit_cell(sh.player_table(sh.match_stats(tr)))
    ms = sh.match_stats(r)
    pt = sh.player_table(ms)
    if pt.empty:
        return [], {"fit": fit, "est": pt, "draws": pd.DataFrame()}
    est = sh.estimate(pt, fit, config)
    draws = sh.bootstrap_draws(ms, est, n_boot, seed)
    lo, hi = sh.interval(draws)
    exp_mean = r.groupby("player_id")["expected"].mean()
    act_mean = r.groupby("player_id")["actual"].mean()
    floor = PLACEHOLDER_MIN_BALLS[role] if min_balls is None else min_balls
    out = []
    for pid, row in est.iterrows():
        if elig is None:
            status = "ELIGIBLE_PLACEHOLDER" if row["n"] >= floor else "NOT_ELIGIBLE_PLACEHOLDER"
            basis = ELIG_PLACEHOLDER
        else:
            t = elig["threshold_balls"]
            ok = t is not None and row["n"] >= t * elig["wr"]
            status = elig["label"] if ok else "NOT_ELIGIBLE"
            basis = elig["basis"]
        out.append(
            PressureRecord(
                player_id=int(pid),
                role=role,
                stream=stream,
                format=comp,
                window=window,
                definition_id=defn_id,
                baseline_version=baseline_version,
                shrinkage_config=config,
                raw_pressure_outcome=_num(act_mean[pid]),
                expected_baseline_outcome=_num(exp_mean[pid]),
                residual=_num(row["mean"]),
                shrunk_estimate=_num(row["shrunk"]),
                interval_low=_num(lo[pid]),
                interval_high=_num(hi[pid]),
                posterior_sd=_num(row["posterior_sd"]),
                data_weight=_num(row["B"]),
                shrinkage_k=_num(row["k"]),
                shrinkage_floor_hit=bool(row["floor_hit"]),
                pressure_opportunities=int(row["n"]),
                distinct_matches=int(row["matches"]),
                effective_sample_size=float(row["n_eff"]),
                eligibility_status=status,
                eligibility_basis=basis,
                applied_restrictions=RESTRICTIONS,
            )
        )
    return out, {"fit": fit, "est": est, "draws": draws}


def combine_formats(
    ipl: tuple[pd.DataFrame, pd.DataFrame], t20i: tuple[pd.DataFrame, pd.DataFrame], w_ipl: float
) -> pd.DataFrame:
    """Format-combined shrunk estimate for players present and eligible in BOTH formats.

    Each argument is (estimate table, draws). A player missing in a format is never zero-filled:
    the combined value is not produced for that player.
    """
    w_t = 1.0 - w_ipl
    both = ipl[0].index.intersection(t20i[0].index)
    est = w_ipl * ipl[0].loc[both, "shrunk"] + w_t * t20i[0].loc[both, "shrunk"]
    comb = w_ipl * ipl[1].loc[both].to_numpy() + w_t * t20i[1].loc[both].to_numpy()
    with np.errstate(all="ignore"):
        lo = np.nanpercentile(comb, 2.5, axis=1) if len(both) else np.array([])
        hi = np.nanpercentile(comb, 97.5, axis=1) if len(both) else np.array([])
    return pd.DataFrame({"shrunk": est, "interval_low": lo, "interval_high": hi}, index=both)


def score_all(
    d: pd.DataFrame,
    bs: BaselineSet,
    defn_id: str,
    thr: dict[str, float],
    configs: list[str],
    lock: TestLock,
    w_ipl: float = 0.7,
    n_boot: int = 1000,
    elig_rules: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """All single-format and default-weight combined records, for each shrinkage config."""
    guard_frame(d, lock, "score_all")
    recs: list[dict] = []
    for role, stream, _ in STREAMS:
        rows = residual_rows(d, bs, defn_id, thr, role, stream, lock)
        for cfg in configs:
            parts: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
            elig: dict[str, set] = {}
            byc: dict[str, dict[int, PressureRecord]] = {}
            for comp in SCOPE:
                er = None if elig_rules is None else elig_rules.get((comp, role))
                rr, info = score_cell(
                    rows, role, stream, comp, defn_id, bs.version, cfg, n_boot, elig=er
                )
                recs += [r.model_dump() for r in rr]
                if len(info["est"]):
                    parts[comp] = (info["est"], info["draws"])
                    byc[comp] = {r.player_id: r for r in rr}
                    elig[comp] = {r.player_id for r in rr if r.eligibility_status.startswith("EL")}
            if len(parts) == 2:
                both = sorted(elig["IPL"] & elig["T20I"])
                sub = {c: (parts[c][0].loc[both], parts[c][1].loc[both]) for c in SCOPE}
                comb = combine_formats(sub["IPL"], sub["T20I"], w_ipl)
                for pid, row in comb.iterrows():
                    comps = (byc["IPL"][int(pid)], byc["T20I"][int(pid)])
                    recs.append(
                        _combined_record(
                            pid, role, stream, defn_id, bs.version, cfg, w_ipl, row, comps
                        )
                    )
    return pd.DataFrame(recs)


def _combined_record(pid, role, stream, defn_id, bver, cfg, w_ipl, row, comps) -> dict:
    """Combined row built from the two per-format records.

    Raw, expected and residual are the format-weighted means of the per-format values (linear,
    so residual = raw - expected still holds). Opportunities and distinct matches are sums across
    formats (match ids are format-disjoint). Effective sample size is the weight-implied n,
    1 / (w^2 / n_ipl + (1 - w)^2 / n_t20i).
    """
    a, b = comps
    w = w_ipl

    def wavg(x, y):
        return None if x is None or y is None else w * x + (1 - w) * y

    inv = w**2 / a.effective_sample_size + (1 - w) ** 2 / b.effective_sample_size
    return PressureRecord(
        player_id=int(pid),
        role=role,
        stream=stream,
        format=f"COMBINED_w{round(w_ipl * 100)}_{round((1 - w_ipl) * 100)}",
        window=WINDOW_PRE_TEST,
        definition_id=defn_id,
        baseline_version=bver,
        shrinkage_config=cfg,
        raw_pressure_outcome=wavg(a.raw_pressure_outcome, b.raw_pressure_outcome),
        expected_baseline_outcome=wavg(a.expected_baseline_outcome, b.expected_baseline_outcome),
        residual=wavg(a.residual, b.residual),
        shrunk_estimate=_num(row["shrunk"]),
        interval_low=_num(row["interval_low"]),
        interval_high=_num(row["interval_high"]),
        posterior_sd=None,
        data_weight=None,
        shrinkage_k=None,
        shrinkage_floor_hit=None,
        pressure_opportunities=a.pressure_opportunities + b.pressure_opportunities,
        distinct_matches=a.distinct_matches + b.distinct_matches,
        effective_sample_size=1.0 / inv if inv > 0 else 0.0,
        eligibility_status=(
            "ELIGIBLE_PLACEHOLDER_BOTH_FORMATS"
            if a.eligibility_status == "ELIGIBLE_PLACEHOLDER"
            else f"{a.eligibility_status}|{b.eligibility_status}"
        ),
        eligibility_basis=a.eligibility_basis,
        applied_restrictions=RESTRICTIONS + "; combined only where eligible in both formats",
    ).model_dump()


def evaluate_test_scores(
    frozen_path: Path | str,
    lock: TestLock,
    d_test_provider,
    bs: BaselineSet,
    defn_id: str,
    thr: dict[str, float],
    configs: list[str],
    n_boot: int = 1000,
) -> pd.DataFrame:
    """The only route to TEST scoring: opens the lock once via ``evaluate_on_test``."""

    def run(open_lock: TestLock) -> pd.DataFrame:
        d = d_test_provider()
        return score_all(d, bs, defn_id, thr, configs, open_lock, n_boot=n_boot)

    return evaluate_on_test(frozen_path, lock, run)


def write_scores(df: pd.DataFrame, csv_path: Path | str, json_path: Path | str) -> None:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    Path(json_path).write_text(
        json.dumps(
            {"status": STATUS, "official_ranking": OFFICIAL_RANKING,
             "records": json.loads(df.to_json(orient="records"))},
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )  # fmt: skip
