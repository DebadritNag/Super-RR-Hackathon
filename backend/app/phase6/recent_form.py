"""Separate recent-form analyses (2024-onward and 2025-onward), EXPERIMENTAL_NOT_VALIDATED.

Each window is a date filter on the pre-test frame (TEST rows are never loaded). The residual
baseline B0 and the pressure thresholds stay the TRAIN-fitted ones of ``Study``, so a match has the
same residual in every window. Everything that depends on the window itself is refitted on the
window's own rows, in-sample: the within-cell variance components and shrinkage ``k``, the
eligibility ratio, the bootstrap weights and the split-half reliability. A window never borrows a
primary ``k`` or ``tau2`` and never writes into a primary table; its rows carry
``analysis_label = RECENT_FORM_SEPARATE_ANALYSIS``. No player-level score is produced here.

Eligibility thresholds are the four Phase 4 frozen ball thresholds, scaled from the TRAIN scale to
the window as ``ceil(t * window_balls / TRAIN_balls)`` (never below 1). They are provisional (OD-2).
The data weight of a cell is ``B = n_eff / (n_eff + k)`` for its least-experienced eligible
individual under ``shrink_tau4`` (the frozen configuration). The 0.5 gate is read from
``app.phase4.eligibility.GATE_B`` and only compared against; it is never changed.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import shrink as sh
from app.phase4.baseline import STREAMS
from app.phase4.constants import SCOPE
from app.phase5 import pipeline as pl
from app.phase5 import reliability as rb
from app.phase5.reliability import NOT_ESTIMABLE
from app.phase6 import split_half as sp
from app.phase6.lockguard import assert_no_test_rows

LABEL = "RECENT_FORM_SEPARATE_ANALYSIS"
FIT_ON = "WINDOW_IN_SAMPLE"
GATE = el.GATE_B  # read, never assigned or changed here
MIN_PLAYERS_FIT = 8
WINDOWS = {"2024": "2024-01-01", "2025": "2025-01-01"}


def filter_window(df: pd.DataFrame, start: str, date_col: str = "match_date") -> pd.DataFrame:
    """Rows with ``date >= start`` (calendar date). Never returns a row from before ``start``."""
    dates = pd.to_datetime(df[date_col]).dt.normalize()
    return df[dates >= pd.Timestamp(start).normalize()]


def scaled_threshold(
    threshold_balls: int | None, window_balls: float, train_balls: float
) -> int | None:
    """Frozen TRAIN-scale threshold scaled to a window: ``ceil(t * window / TRAIN)``, at least 1."""
    if threshold_balls is None or not train_balls or not np.isfinite(window_balls):
        return None
    return max(1, math.ceil(threshold_balls * window_balls / train_balls))


def window_counts(d: pd.DataFrame, start: str) -> pd.DataFrame:
    """Matches and delivery rows per format inside the window (from the pre-test frame)."""
    w = filter_window(d, start)
    assert_no_test_rows(w)
    g = w.groupby("competition_type")
    return pd.DataFrame(
        {
            "format": g.size().index,
            "matches": g["match_id"].nunique().to_numpy(),
            "delivery_rows": g.size().to_numpy(),
            "first_date": g["match_date"].min().dt.strftime("%Y-%m-%d").to_numpy(),
            "last_date": g["match_date"].max().dt.strftime("%Y-%m-%d").to_numpy(),
        }
    )


def window_cells(
    study: pl.Study, defn: str, start: str
) -> dict[tuple[str, str, str], tuple[en.Cell, en.Cell]]:
    """(format, role, stream) -> (window cell, full pre-test cell) for pressure rows >= start."""
    out = {}
    for role, stream, _ in STREAMS:
        press = study.pressure_rows(defn, role, stream)
        win = filter_window(press, start, "date")
        assert_no_test_rows(win)
        for comp in SCOPE:
            full = en.build_cell(press, comp, role, stream)
            c = en.build_cell(win, comp, role, stream)
            if c is not None and full is not None:
                out[(comp, role, stream)] = (c, full)
    return out


def cell_summary(
    cell: en.Cell, full: en.Cell, rule: dict[str, Any] | None, config: str, train_balls: float
) -> dict[str, Any]:
    """Sample counts, own-window fit, eligibility and informational data weight of one cell."""
    pt = sh.player_table(cell.ms)
    row: dict[str, Any] = {
        "matches": int(len(cell.matches)),
        "pressure_observations": int(len(cell.rows)),
        "players_with_pressure_balls": int(len(pt)),
        "median_player_balls": float(pt["n"].median()) if len(pt) else None,
        "share_rows_in_b0_fit_window": float((cell.rows["period"] == "TRAIN").mean()),
    }
    if len(pt) < MIN_PLAYERS_FIT:
        return {**row, "status": NOT_ESTIMABLE, "reason": f"fewer than {MIN_PLAYERS_FIT} players"}
    fit = sh.fit_cell(pt)
    kinfo = sh.k_for(fit, config)
    row.update(sigma2_within=fit["sigma2"], between_moment=fit["between"], k=kinfo["k"],
               floor_hit=kinfo["floor_hit"], tau2_used=kinfo["tau2"])  # fmt: skip
    thr = (
        None
        if rule is None
        else scaled_threshold(rule["threshold_balls"], float(cell.N.sum()), train_balls)
    )
    row.update(frozen_threshold_balls=None if rule is None else rule["threshold_balls"],
               scaled_threshold_balls=thr,
               threshold_label=None if rule is None else rule["label"])  # fmt: skip
    if thr is None:
        return {**row, "status": "NO_FROZEN_THRESHOLD", "eligible_players": 0}
    elig = pt["n"].to_numpy() >= thr
    row["eligible_players"] = int(elig.sum())
    if not elig.any():
        return {**row, "status": NOT_ESTIMABLE, "reason": "no individual reaches the threshold"}
    ne_min = float(pt["n_eff"].to_numpy()[elig].min())
    k = float(kinfo["k"])
    b = ne_min / (ne_min + k) if (ne_min + k) > 0 else None
    row.update(status="ESTIMATED", marginal_n_eff=ne_min, marginal_data_weight=b,
               median_data_weight=float(np.median(pt["n_eff"].to_numpy()[elig]
                                                  / (pt["n_eff"].to_numpy()[elig] + k))),
               gate=GATE, passes_gate_informational=bool(b is not None and b >= GATE))  # fmt: skip
    return row


def reliability_rows(
    cell: en.Cell, meta: dict[str, Any], cfg: dict[str, Any], gm: pd.Index, W: np.ndarray, seed: int
) -> list[dict[str, Any]]:
    """Odd/even and early/late split-half rows of one window cell with player and match CIs."""
    sh_cfg = cfg["split_half"]
    cd = rb.from_cell(cell)
    w = en.cell_weights(cell, gm, W)
    mask = np.ones(cd.N.shape[1], dtype=bool)
    rows = []
    for mode in ("odd_even", "early_late"):
        s = sp.unit_seed(
            seed, meta["window_start"], meta["format"], meta["role"], meta["stream"], mode
        )
        r, ci = sp.split_half_unit(cd, w, mask, mode, sh_cfg["min_balls_per_half"], s, 1,
                                   sh_cfg["bootstrap_draws"], sh_cfg["min_players_estimable"])  # fmt: skip
        rec = {**meta, **r}
        for c in ci:
            m = "players" if c["ci_method"].startswith("player") else "matches"
            rec[f"sb_lo_{m}"], rec[f"sb_hi_{m}"] = c["lo"], c["hi"]
        rows.append(rec)
    return rows


def run(study: pl.Study, defn: str, cfg: dict[str, Any], config: str = "shrink_tau4") -> dict:
    """Both windows. Returns ``{"summary": {key: DataFrame}, "reliability": DataFrame, ...}``."""
    summary: dict[str, pd.DataFrame] = {}
    rel: list[dict[str, Any]] = []
    counts: dict[str, pd.DataFrame] = {}
    match_sets: dict[str, set] = {}
    prim_rules = study.frozen["eligibility"]
    for key, start in WINDOWS.items():
        wd = filter_window(study.d, start)
        assert_no_test_rows(wd)
        match_sets[key] = set(wd["match_id"].unique())
        counts[key] = window_counts(study.d, start)
        gm, W = en.global_weights(wd["match_id"].to_numpy(), study.n_boot, study.seed)
        rows = []
        for (comp, role, stream), (cell, full) in window_cells(study, defn, start).items():
            primary = stream == en.PRIMARY[role][0]
            rule = prim_rules[f"{comp}|{role}"]["analysis"] if primary else None
            train_balls = float(full.N[:, full.match_period == "TRAIN"].sum())
            meta = {"analysis_label": LABEL, "window_start": start, "fit_on": FIT_ON,
                    "definition": defn, "format": comp, "role": role, "stream": stream,
                    "is_primary_stream": primary}  # fmt: skip
            rows.append(
                {
                    **meta,
                    **cell_summary(cell, full, rule, config, train_balls),
                    "shrinkage_config": config,
                    "seed": study.seed,
                    "n_boot": study.n_boot,
                }
            )
            rel += [{**r, "n_boot": study.n_boot, "seed": study.seed}
                    for r in reliability_rows(cell, meta, cfg, gm, W, study.seed)]  # fmt: skip
        summary[key] = pd.DataFrame(rows)
    primary_counts = study.d.groupby("competition_type")["match_id"].nunique().to_dict()
    return {
        "summary": summary,
        "reliability": pd.DataFrame(rel),
        "counts": counts,
        "match_sets": match_sets,
        "primary_matches": primary_counts,
    }
