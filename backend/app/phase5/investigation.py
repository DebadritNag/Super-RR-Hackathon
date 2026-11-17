"""Phase 5 reliability investigation runner. EXPERIMENTAL_NOT_VALIDATED, descriptive only.

Builds the tables of ``phase5_investigation_report.md`` from the pre-test pressure cells of the
carried definition (``any|q0.75``, PROVISIONAL) and its three sensitivity alternatives. TEST rows
are never loaded. Every number comes from running code.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en
from app.phase4.constants import SCOPE
from app.phase5 import pressure_signals as ps
from app.phase5 import reliability as rb
from app.phase5.pipeline import Study

PROVISIONAL_NOTE = (
    "PROVISIONAL / EXPERIMENTAL_NOT_VALIDATED. any|q0.75 is the Phase 4 rule winner among nine "
    "candidates, not shown to be valid or superior."
)


def definitions(study: Study) -> list[str]:
    d = study.cfg["definitions"]
    return [d["primary"], *d["alternatives"]]


def _keys(defn: str, key: tuple[str, str, str], study: Study) -> dict[str, Any]:
    comp, role, stream = key
    return {
        "definition": defn,
        "is_primary_definition": defn == study.cfg["definitions"]["primary"],
        "format": comp,
        "role": role,
        "stream": stream,
        "is_primary_stream": stream == en.PRIMARY[role][0],
    }


def cell_data(
    study: Study, defn: str
) -> dict[tuple[str, str, str], tuple[rb.CellData, np.ndarray]]:
    """(format, role, stream) -> (matrices, bootstrap weights aligned to the cell's matches)."""
    out = {}
    for key, cell in study.all_cells(defn).items():
        cd = rb.from_cell(cell)
        out[key] = (cd, en.cell_weights(cell, study.gm, study.W))
    return out


# ---------------------------------------------------------------- variance decomposition
def run_variance(study: Study, defns: list[str]) -> pd.DataFrame:
    rows = []
    mbs = list(study.cfg["min_balls_variants"])
    for defn in defns:
        for key, (cd, w) in cell_data(study, defn).items():
            for window in study.cfg["windows"]:
                for r in rb.variance_rows(cd, w, window, mbs) + rb.split_cov_rows(
                    cd, w, window, mbs
                ):
                    rows.append({**_keys(defn, key, study), **r})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- split-half
def run_split_half(study: Study, defns: list[str]) -> pd.DataFrame:
    sh = study.cfg["split_half"]
    rows = []
    for defn in defns:
        for key, (cd, w) in cell_data(study, defn).items():
            for window in study.cfg["windows"]:
                for mode in sh["modes"]:
                    r = rb.split_half(cd, window, mode, sh["min_balls_per_half"], w, study.seed,
                                      sh["random_splits"], sh["min_players_estimable"])  # fmt: skip
                    rows.append({**_keys(defn, key, study), **r})
    return pd.DataFrame(rows)


def run_opportunity(study: Study, defns: list[str]) -> pd.DataFrame:
    sh = study.cfg["split_half"]
    rows = []
    for defn in defns:
        for key, (cd, w) in cell_data(study, defn).items():
            if key[2] != en.PRIMARY[key[1]][0]:
                continue
            ladder = study.cfg["opportunity_ladders"][key[1]]
            for r in rb.reliability_by_opportunity(cd, "PRE_TEST", ladder, sh["min_balls_per_half"], w,
                                                   sh["min_players_estimable"]):  # fmt: skip
                rows.append({**_keys(defn, key, study), **r})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- projection
def run_projection(study: Study, var_df: pd.DataFrame, defns: list[str]) -> pd.DataFrame:
    """Required sample for reliability targets from each noise basis (DESCRIPTIVE_PROJECTION)."""
    targets = tuple(study.cfg["reliability_targets"])
    data = {d: cell_data(study, d) for d in defns}
    rows = []
    sub = var_df[(var_df["min_balls"] == 1) & var_df["is_primary_stream"]]
    for _, v in sub.iterrows():
        cd, _ = data[v["definition"]][(v["format"], v["role"], v["stream"])]
        balls = cd.select_cols(rb.window_cols(cd, v["window"])).total_balls
        balls = balls[balls > 0]
        unit = "kish_effective_units" if v["noise_basis"] == "phase4_kish" else "balls"
        tau2, tau2_opt = v["tau2_moment"], v["tau2_boot_p90"]
        point = rb.required_sample(tau2, v["sigma_eff_for_projection"], targets, unit)
        opt = rb.required_sample(tau2_opt, v["sigma_eff_for_projection"], targets, unit)
        for p, o in zip(point, opt, strict=True):
            req = p["required_n"]
            rows.append(
                {
                    **{k: v[k] for k in ("definition", "is_primary_definition", "format", "role",
                                         "stream", "window", "noise_basis", "status")},
                    "target_reliability": p["target_reliability"], "unit": unit,
                    "tau2_used": tau2, "sigma_eff_used": v["sigma_eff_for_projection"],
                    "required_n_point": req, "tau2_bootstrap_p90": tau2_opt,
                    "required_n_if_tau2_at_bootstrap_p90": o["required_n"],
                    "observed_median_player_balls": float(np.median(balls)) if balls.size else None,
                    "observed_p90_player_balls": float(np.percentile(balls, 90)) if balls.size else None,
                    "share_players_at_or_above_required": (
                        float((balls >= req).mean())
                        if unit == "balls" and isinstance(req, float) and balls.size
                        else None
                    ),
                    "label": "DESCRIPTIVE_PROJECTION",
                }
            )  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- detectability
def run_detectability(study: Study, defn: str) -> pd.DataFrame:
    det = study.cfg["detectability"]
    rows = []
    for key, (cd, _) in cell_data(study, defn).items():
        if key[2] != en.PRIMARY[key[1]][0]:
            continue
        sub = cd.select_cols(rb.window_cols(cd, "PRE_TEST"))
        if sub.N.shape[0] == 0:
            continue
        dec = rb.decompose_moments(rb.boot_moments(sub, np.ones((sub.N.shape[1], 1))), 12)
        for basis in ("ball_independent", "match_cluster"):
            ok = dec[f"{basis}_ok"][:, 0]
            noise = dec[f"{basis}_noise_i"][ok, 0]
            for r in rb.simulate_detectability(noise, float(dec["sigma2"][0]), det["tau2_over_sigma2_grid"],
                                               det["replications"], study.seed):  # fmt: skip
                rows.append(
                    {**_keys(defn, key, study), "noise_basis": basis, "window": "PRE_TEST", **r}
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- multi-format pooling
def run_pooling(study: Study, defns: list[str]) -> pd.DataFrame:
    sh = study.cfg["split_half"]
    rows = []
    for defn in defns:
        data = cell_data(study, defn)
        for role in ("batter", "bowler"):
            stream = en.PRIMARY[role][0]
            if ("IPL", role, stream) not in data or ("T20I", role, stream) not in data:
                continue
            a, b = data[("IPL", role, stream)][0], data[("T20I", role, stream)][0]
            for window in study.cfg["windows"]:
                r = rb.multi_format_pooling(
                    a, b, window, sh["min_balls_per_half"], sh["min_players_estimable"]
                )
                rows.append({"definition": defn, "is_primary_definition": defn == definitions(study)[0],
                             "role": role, "stream": stream, **r})  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- bowler-specific signals
def run_bowler_signals(study: Study) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Bowler candidates versus the primary (batter-state) definition. SENSITIVITY_ONLY."""
    cfg = study.cfg["bowler_signal_candidates"]
    built = ps.build_flags(study.d, cfg)
    base = study.base("bowler", "charged")
    primary = study.cfg["definitions"]["primary"]
    sh = study.cfg["split_half"]
    sets: dict[str, dict[str, en.Cell]] = {"primary_batter_state_signals": {
        comp: study.primary_cells(primary)[(comp, "bowler")] for comp in SCOPE
        if (comp, "bowler") in study.primary_cells(primary)}}  # fmt: skip
    for cid, (flag, pop, _) in built.items():
        press = ps.candidate_pressure_rows(base, flag, pop)
        sets[cid] = {}
        for comp in SCOPE:
            c = en.build_cell(press, comp, "bowler", "charged")
            if c is not None:
                sets[cid][comp] = c
    rows = []
    for cid, cells in sets.items():
        for comp, cell in cells.items():
            cd = rb.from_cell(cell)
            w = en.cell_weights(cell, study.gm, study.W)
            tr = cell.rows[cell.rows["period"] == "TRAIN"]
            head = {
                "candidate": cid, "format": comp, "is_primary_signal": cid == "primary_batter_state_signals",
                "pressure_balls_TRAIN": int(len(tr)), "pressure_balls_total": int(len(cell.rows)),
                "players_total": int(len(cell.players)),
                "players_ge_18_balls_TRAIN": int((tr.groupby("player_id").size() >= 18).sum()),
                "label": ps.LABEL,
            }  # fmt: skip
            for window in ("TRAIN", "PRE_TEST"):
                for r in rb.variance_rows(cd, w, window, [12]) + rb.split_cov_rows(
                    cd, w, window, [12]
                ):
                    rows.append({**head, "kind": "variance_decomposition", **r})
                for mode in ("odd_even", "early_late"):
                    r = rb.split_half(cd, window, mode, sh["min_balls_per_half"], w, study.seed,
                                      sh["random_splits"], sh["min_players_estimable"])  # fmt: skip
                    rows.append({**head, "kind": "split_half", **r})
    meta = {
        "thresholds_train_only": {cid: thr for cid, (_, _, thr) in built.items()},
        "not_buildable": ps.not_buildable(cfg, built),
        "note": cfg["label"],
    }
    return pd.DataFrame(rows), meta
