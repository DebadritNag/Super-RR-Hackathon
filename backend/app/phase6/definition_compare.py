"""Definition comparison on pre-declared reliability criteria (EXPERIMENTAL_NOT_VALIDATED).

The nine candidate pressure definitions are compared ONLY on the metrics and the rule written to
``config/phase6_selection_criteria_v1.json`` before any estimator output existed (its SHA-256 is
logged as ``p6_run_log`` row 1). Nothing here reads, receives or emits a player identity beyond the
join key that aligns two orderings of the same players inside one function call; the output
tables carry no player column. No score level, rank or Top-10 membership is an input.

The result is a pass list and a provisional top group. It is not a selection: ``any|q0.75`` stays
the provisional definition whatever happens here. Everything is in-sample on TRAIN and VALIDATION.
TEST rows cannot enter (``Study`` drops them and every frame is guarded).
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from app.phase4 import engine as en
from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6 import criteria as cr
from app.phase6 import split_half as sp
from app.phase6.constants import (
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    IN_SAMPLE_LABEL,
    INVESTIGATION_CONFIG,
)
from app.phase6.lockguard import assert_no_test_rows
from app.services.pressure_service import EXPLORATORY_DB

WINDOWS = ("PRE_TEST", "TRAIN")
DEFINITION_TABLES = (
    "p6_definition_reliability",
    "p6_definition_summary",
    "p6_definition_resampling",
    "p6_definition_outcome",
)
CONFOUNDED = "COMPARISON_CONFOUNDED"
NOT_STABLE = "DEFINITION_ORDER_NOT_STABLE"
TOP_PROVISIONAL = "TOP_GROUP_PROVISIONAL"
NO_PASS = "NO_DEFINITION_PASSES"
MIN_INTERSECTION = 30
MIN_CELLS_LO_POSITIVE = 3
FORBIDDEN_COLUMNS = ("player_id", "player", "player_name", "name", "ids")


class ResultsHashError(cr.CriteriaError):
    """Stored comparison results were made under a different criteria hash."""


# ---------------------------------------------------------------- run guard
def stored_result_hashes(store_path: Path | str) -> dict[str, set[str]]:
    """Distinct ``criteria_sha256`` values found in each existing definition result table."""
    out: dict[str, set[str]] = {}
    if not Path(store_path).exists():
        return out
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        for t in DEFINITION_TABLES:
            has = con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [t]
            ).fetchone()[0]
            if not has:
                continue
            cols = con.execute(f"DESCRIBE {t}").df()["column_name"].tolist()
            if "criteria_sha256" not in cols:
                out[t] = {"<column missing>"}
                continue
            vals = con.execute(f"SELECT DISTINCT criteria_sha256 FROM {t}").fetchall()
            out[t] = {str(v[0]) for v in vals}
    finally:
        con.close()
    return out


def begin_comparison(
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    config_path: Path | str = INVESTIGATION_CONFIG,
    store_path: Path | str = EXPLORATORY_DB,
) -> dict[str, Any]:
    """Verify the criteria (a missing or changed file or hash raises) and that no stored result
    was made under another hash, then append the ``definition_compare`` run-log row."""
    info = cr.verify_criteria(criteria_path, hash_path, store_path)
    for table, hashes in stored_result_hashes(store_path).items():
        if hashes != {info["sha256"]}:
            raise ResultsHashError(
                f"{table} holds results made under criteria hash(es) {sorted(hashes)}, but the "
                f"criteria file now hashes to {info['sha256']}: refusing to run"
            )
    return cr.begin_step("definition_compare", criteria_path, hash_path, config_path, store_path)


# ---------------------------------------------------------------- metrics
def spearman_draws(draws: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Spearman correlation of each column of ``draws`` (players, draws) with ``ref``.

    Players are matched by position; non-finite entries drop out per draw. Ties get average
    ranks. Returns NaN for draws with fewer than 3 common players or no spread.
    """
    out = np.full(draws.shape[1], np.nan)
    for j in range(draws.shape[1]):
        ok = np.isfinite(draws[:, j]) & np.isfinite(ref)
        if ok.sum() < 3:
            continue
        a, b = rankdata(draws[ok, j]), rankdata(ref[ok])
        sa, sb_ = a.std(), b.std()
        if sa == 0 or sb_ == 0:
            continue
        out[j] = float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb_))
    return out


def pooled_sb_draws(
    r_draws: list[np.ndarray], n_players: list[int], clip: float = 0.99
) -> np.ndarray:
    """Fisher-z pooled correlation per draw over cells (weights n - 3), Spearman-Brown corrected."""
    if not r_draws:
        return np.array([])
    z = np.stack([np.arctanh(np.clip(np.asarray(r, float), -clip, clip)) for r in r_draws])
    wt = (np.asarray(n_players, float) - 3.0)[:, None]
    valid = np.isfinite(z) & (wt > 0)
    num = np.where(valid, wt * np.where(valid, z, 0.0), 0.0).sum(0)
    den = np.where(valid, wt, 0.0).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        pr = np.where(den > 0, np.tanh(num / np.where(den > 0, den, 1.0)), np.nan)
    return np.asarray(rb.sb(pr))


def _pct(x: np.ndarray, q: float) -> float | None:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if x.size >= 20 else None


def unit_metrics(
    cd: rb.CellData,
    w: np.ndarray,
    mask: np.ndarray,
    min_half: int = 6,
    min_players: int = 10,
    keep: np.ndarray | None = None,
) -> dict[str, Any]:
    """R, M2, M3, M4 and M5 of one definition x (format, role) cell and window.

    ``w`` are full-width match-bootstrap weights (matches of ``cd`` by draws); ``mask`` selects the
    window columns; ``keep`` (boolean over ``cd.players``) restricts to a player subset (used for
    the intersection version). The returned dict holds arrays for pooling but no player ids other
    than ``ok_ids`` (used only to build the intersection set inside the caller).
    """
    sub = cd.select_cols(mask)
    ws = w[mask]
    if keep is not None:
        sub = sub.select_players(keep)
    out: dict[str, Any] = {"matches": int(sub.N.shape[1]), "status": NOT_ESTIMABLE, "players": 0,
                           "ok_ids": np.array([], dtype=sub.players.dtype)}  # fmt: skip
    if sub.N.shape[0] == 0 or sub.N.shape[1] < 2:
        return out
    present = sub.N > 0
    A, B = rb.half_masks(present, "odd_even")
    one = np.ones((sub.N.shape[1], 1))
    h = rb.half_stats(sub.N, sub.S, A, B, one, min_half)
    ok = h["ok"][:, 0]
    n_ok = int(ok.sum())
    r = float(h["pearson"][0])
    out.update(players=n_ok, ok_ids=sub.players[ok])
    if n_ok < min_players or not np.isfinite(r):
        return out
    hb = rb.half_stats(sub.N, sub.S, A, B, ws, min_half)
    r_draws = np.asarray(hb["pearson"], float)
    sb_draws = np.asarray(rb.sb(r_draws), float)
    n_tot, s_tot = sub.N.sum(1), sub.S.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_pt = np.where(n_tot > 0, s_tot / np.where(n_tot > 0, n_tot, 1.0), np.nan)
    idx = np.where(ok)[0]
    nb, sbm = sub.N[idx] @ ws, sub.S[idx] @ ws
    with np.errstate(invalid="ignore", divide="ignore"):
        means_b = np.where(nb > 0, sbm / np.where(nb > 0, nb, 1.0), np.nan)
    var_means = float(np.var(mean_pt[idx], ddof=1)) if n_ok > 1 else float("nan")
    cov = float(h["cov"][0])
    cell_mean = float(s_tot.sum() / n_tot.sum()) if n_tot.sum() > 0 else float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        lo_i = np.nanpercentile(means_b, 2.5, axis=1)
        hi_i = np.nanpercentile(means_b, 97.5, axis=1)
    fin = np.isfinite(means_b).sum(1) >= 20
    m3 = float((((lo_i > cell_mean) | (hi_i < cell_mean))[fin]).mean()) if fin.any() else None
    m5 = spearman_draws(means_b, mean_pt[idx])
    sbd = sb_draws[np.isfinite(sb_draws)]
    out.update(
        status=ESTIMATED,
        r_pearson=r,
        sb=float(rb.sb(r)),
        sb_lo=_pct(sb_draws, 2.5),
        sb_hi=_pct(sb_draws, 97.5),
        share_nonpositive=float((sbd <= 0).mean()) if sbd.size else None,
        draws=int(sbd.size),
        r_draws=r_draws,
        m2=float(cov / var_means) if np.isfinite(var_means) and var_means > 0 else None,
        m3=m3,
        m4_median_balls=float(np.median(n_tot[idx])),
        m4_all_median_balls=float(np.median(n_tot[n_tot > 0])) if (n_tot > 0).any() else None,
        balls_ok=n_tot[idx].astype(float),
        m5_median=float(np.nanmedian(m5)) if np.isfinite(m5).any() else None,
        m5_p5=_pct(m5, 5.0),
        m5_draws=int(np.isfinite(m5).sum()),
    )
    return out


# ---------------------------------------------------------------- control sample (M6)
def control_cd(
    tagged: pd.DataFrame, cell: en.Cell, comp: str, role: str, stream: str, seed: int
) -> rb.CellData | None:
    """Non-pressure balls matched on balls per player-match to the pressure sample (M6).

    For each (player, match) of the pressure cell the same number of non-pressure balls of that
    player in that match (same comparison population) is drawn without replacement, or all of
    them when fewer exist. Descriptive only; never a selection input.
    """
    rows = tagged[(tagged["comp"] == comp) & tagged["in_pop"] & ~tagged["press"]]
    if rows.empty:
        return None
    tgt = cell.ms[["player_id", "match_id", "n"]].rename(columns={"n": "target_n"})
    rows = rows.merge(tgt, on=["player_id", "match_id"], how="inner")
    if rows.empty:
        return None
    rng = np.random.default_rng(seed)
    rows = rows.assign(_u=rng.random(len(rows))).sort_values(
        ["player_id", "match_id", "_u"], kind="mergesort"
    )
    rows["_k"] = rows.groupby(["player_id", "match_id"]).cumcount()
    sel = rows[rows["_k"] < rows["target_n"]].drop(columns=["_u", "_k", "target_n"])
    cc = en.build_cell(sel, comp, role, stream)
    return None if cc is None else rb.from_cell(cc)


# ---------------------------------------------------------------- pass list, top group
def pass_table(
    cells: pd.DataFrame, n_cells: int, min_lo_cells: int = MIN_CELLS_LO_POSITIVE
) -> pd.DataFrame:
    """PASS(d): R estimable in all ``n_cells`` cells and lower bound above 0 in >= 3 cells."""
    rows = []
    for d, g in cells.groupby("definition", sort=True):
        est = g[g["status"] == ESTIMATED]
        n_est = int(len(est))
        n_lo = int((est["sb_lo"].dropna() > 0).sum())
        rows.append({"definition": d, "cells_estimable": n_est, "cells_lo_positive": n_lo,
                     "passes": bool(n_est == n_cells and n_lo >= min_lo_cells)})  # fmt: skip
    return pd.DataFrame(rows)


def top_group(summary: pd.DataFrame) -> list[str]:
    """TOP(d): PASS and M1 >= (max M1 over passing) - SE1 of the best; ordered M4 desc, M5 desc, id.

    ``summary`` needs ``definition``, ``passes``, ``m1``, ``se1``, ``m4``, ``m5``.
    """
    p = summary[summary["passes"] & summary["m1"].notna()]
    if p.empty:
        return []
    best = p.sort_values(["m1", "definition"], ascending=[False, True], kind="mergesort").iloc[0]
    se = float(best["se1"]) if pd.notna(best["se1"]) else 0.0
    thr = float(best["m1"]) - se
    t = p[p["m1"] >= thr].copy()
    t["_m4"] = t["m4"].fillna(-np.inf)
    t["_m5"] = t["m5"].fillna(-np.inf)
    t = t.sort_values(["_m4", "_m5", "definition"], ascending=[False, False, True],
                      kind="mergesort")  # fmt: skip
    return t["definition"].tolist()


def decide(summary: pd.DataFrame, intersection_sizes: dict[str, int | None], n_cells: int) -> dict:
    """Outcome of one window: pass list, top group and status (rule of the criteria file).

    The rule uses the intersection versions of M1 and M5 when the intersection holds at least
    ``MIN_INTERSECTION`` individuals in every cell; otherwise the status is COMPARISON_CONFOUNDED
    and only the pass list is reported.
    """
    pass_list = sorted(summary.loc[summary["passes"], "definition"].tolist())
    sizes = [intersection_sizes.get(k) for k in intersection_sizes]
    big = len(sizes) == n_cells and all(s is not None and s >= MIN_INTERSECTION for s in sizes)
    if not pass_list:
        return {"status": NO_PASS, "pass_list": [], "top_group": [], "confounded": not big}
    if not big:
        return {"status": CONFOUNDED, "pass_list": pass_list, "top_group": [], "confounded": True}
    use = summary.assign(m1=summary["m1_int"], se1=summary["se1_int"], m5=summary["m5_int"])
    return {"status": TOP_PROVISIONAL, "pass_list": pass_list, "top_group": top_group(use),
            "confounded": False}  # fmt: skip


def stability(pre: dict, train: dict) -> dict:
    """Final outcome: DEFINITION_ORDER_NOT_STABLE when the TOP sets of PRE_TEST and TRAIN differ."""
    same = set(pre["top_group"]) == set(train["top_group"])
    if pre["status"] == CONFOUNDED:
        return {
            **pre,
            "stability": "NOT_ASSESSED_CONFOUNDED",
            "train_top_group": train["top_group"],
        }
    if not same:
        return {"status": NOT_STABLE, "pass_list": pre["pass_list"], "top_group": [],
                "confounded": pre["confounded"], "stability": "TOP_SETS_DIFFER",
                "train_top_group": train["top_group"]}  # fmt: skip
    return {**pre, "stability": "TOP_SETS_EQUAL", "train_top_group": train["top_group"]}


# ---------------------------------------------------------------- one window
CellKey = tuple[str, str]


def evaluate_window(
    study: Any,
    defns: list[str],
    window: str,
    crit: dict[str, Any],
    control: bool = False,
    progress: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Cell table, definition summary and outcome of one window (primary streams only)."""
    spec = crit["split_half"]
    min_half, min_pl = int(spec["min_balls_per_half"]), int(spec["min_individuals_estimable"])
    clip = 0.99
    store: dict[tuple[str, CellKey], tuple[Any, np.ndarray, np.ndarray, en.Cell]] = {}
    cell_keys: list[CellKey] = [(c, r) for c in ("IPL", "T20I") for r in ("batter", "bowler")]
    for defn in defns:
        prim = study.primary_cells(defn)
        for key in cell_keys:
            cell = prim.get(key)
            if cell is None:
                continue
            assert_no_test_rows(cell.rows)
            cd = rb.from_cell(cell)
            w = en.cell_weights(cell, study.gm, study.W)
            store[(defn, key)] = (cd, w, sp.window_mask(cd, window), cell)
    first = {k: unit_metrics(cd, w, m, min_half, min_pl) for k, (cd, w, m, _) in store.items()}
    inter: dict[CellKey, np.ndarray] = {}
    for key in cell_keys:
        sets = [first[(d, key)]["ok_ids"] for d in defns if (d, key) in first]
        if len(sets) == len(defns) and sets:
            ids = sets[0]
            for s in sets[1:]:
                ids = np.intersect1d(ids, s)
            inter[key] = ids
    second: dict[tuple[str, CellKey], dict[str, Any]] = {}
    for k, (cd, w, m, _) in store.items():
        ids = inter.get(k[1])
        if ids is not None and len(ids) >= min_pl:
            second[k] = unit_metrics(cd, w, m, min_half, min_pl, keep=np.isin(cd.players, ids))
    rows = []
    for defn in defns:
        for key in cell_keys:
            comp, role = key
            stream = en.PRIMARY[role][0]
            base = {"definition": defn, "format": comp, "role": role, "stream": stream,
                    "window": window, "label": IN_SAMPLE_LABEL}  # fmt: skip
            m = first.get((defn, key))
            if m is None:
                rows.append(
                    {**base, "status": NOT_ESTIMABLE, "players": 0, "reason": "CELL_ABSENT"}
                )
                continue
            m2d = second.get((defn, key), {})
            row = {**base, "status": m["status"], "players": m["players"], "matches": m["matches"],
                   "intersection_players": int(len(inter[key])) if key in inter else None}  # fmt: skip
            if m["status"] == ESTIMATED:
                row.update(
                    r_pearson=m["r_pearson"], sb=m["sb"], sb_lo=m["sb_lo"], sb_hi=m["sb_hi"],
                    share_nonpositive=m["share_nonpositive"], draws=m["draws"],
                    m2_signal_share=m["m2"], m3_share_excluding_cell_mean=m["m3"],
                    m4_median_balls=m["m4_median_balls"],
                    m4_all_individuals_median_balls=m["m4_all_median_balls"],
                    m5_median=m["m5_median"], m5_p5=m["m5_p5"], m5_draws=m["m5_draws"],
                )  # fmt: skip
            if m2d.get("status") == ESTIMATED:
                row.update(sb_int=m2d["sb"], sb_int_lo=m2d["sb_lo"], sb_int_hi=m2d["sb_hi"],
                           m2_int=m2d["m2"], m5_int_median=m2d["m5_median"],
                           m5_int_p5=m2d["m5_p5"], players_int=m2d["players"])  # fmt: skip
            if control and m["status"] == ESTIMATED:
                cd, _, mask, cell = store[(defn, key)]
                tagged = study.tagged(defn, role, stream)
                ccd = control_cd(tagged, cell, comp, role, stream,
                                 sp.unit_seed(study.seed, "control", defn, comp, role))  # fmt: skip
                if ccd is not None:
                    cm = unit_metrics_point(ccd, sp.window_mask(ccd, window), min_half, min_pl)
                    row.update(m6_control_sb=cm.get("sb"), m6_control_players=cm.get("players"))
            rows.append(row)
        if progress:
            progress(f"{window} {defn}")
    cells = pd.DataFrame(rows)
    pt = pass_table(cells, len(cell_keys))
    srows = []
    for defn in defns:
        g = cells[(cells["definition"] == defn) & (cells["status"] == ESTIMATED)]
        rec: dict[str, Any] = {"definition": defn, "window": window, "label": IN_SAMPLE_LABEL}
        for tag, getter in (("", lambda k, d=defn: first.get((d, k))),
                            ("_int", lambda k, d=defn: second.get((d, k)))):  # fmt: skip
            ms = [(k, getter(k)) for k in cell_keys]
            ms = [(k, m) for k, m in ms if m and m["status"] == ESTIMATED]
            if not ms:
                rec[f"m1{tag}"], rec[f"se1{tag}"], rec[f"m5{tag}"] = None, None, None
                continue
            r_pt = np.array([m["r_pearson"] for _, m in ms])
            n_pl = np.array([m["players"] for _, m in ms])
            pooled = sp.fisher_pool(r_pt, n_pl, clip)
            dr = pooled_sb_draws([m["r_draws"] for _, m in ms], [m["players"] for _, m in ms], clip)
            dr = dr[np.isfinite(dr)]
            rec[f"m1{tag}"] = float(rb.sb(pooled["r"]))
            rec[f"se1{tag}"] = float(np.std(dr, ddof=1)) if dr.size > 1 else None
            m5s = [m["m5_median"] for _, m in ms if m["m5_median"] is not None]
            rec[f"m5{tag}"] = float(np.median(m5s)) if m5s else None
            rec[f"cells{tag}"] = len(ms)
        balls = [first[(defn, k)]["balls_ok"] for k in cell_keys
                 if (defn, k) in first and first[(defn, k)]["status"] == ESTIMATED]  # fmt: skip
        rec["m4"] = float(np.median(np.concatenate(balls))) if balls else None
        rec["m2_mean"] = float(g["m2_signal_share"].mean()) if len(g) else None
        rec["m3_mean"] = float(g["m3_share_excluding_cell_mean"].mean()) if len(g) else None
        if "m6_control_sb" in g.columns and g["m6_control_sb"].notna().any():
            rec["m6_mean"] = float(g["m6_control_sb"].mean())
        srows.append(rec)
    summary = pd.DataFrame(srows).merge(pt, on="definition", how="left")
    sizes: dict[str, int | None] = {f"{c}|{r}": (int(len(inter[(c, r)])) if (c, r) in inter else None)
                                    for c, r in cell_keys}  # fmt: skip
    outcome = decide(summary, sizes, len(cell_keys))
    outcome.update(window=window, intersection_sizes=sizes)
    return cells, summary, outcome


def unit_metrics_point(cd: rb.CellData, mask: np.ndarray, min_half: int, min_pl: int) -> dict:
    """Odd/even Spearman-Brown reliability without intervals (control sample)."""
    sub = cd.select_cols(mask)
    if sub.N.shape[0] == 0 or sub.N.shape[1] < 2:
        return {"status": NOT_ESTIMABLE, "players": 0}
    A, B = rb.half_masks(sub.N > 0, "odd_even")
    h = rb.half_stats(sub.N, sub.S, A, B, np.ones((sub.N.shape[1], 1)), min_half)
    n, r = int(h["n"][0]), float(h["pearson"][0])
    if n < min_pl or not np.isfinite(r):
        return {"status": NOT_ESTIMABLE, "players": n}
    return {"status": ESTIMATED, "players": n, "sb": float(rb.sb(r))}


def resampling_table(cells: pd.DataFrame) -> pd.DataFrame:
    """Resampling instability per definition x cell x window (no player column)."""
    keep = ["definition", "format", "role", "stream", "window", "status", "players",
            "m5_median", "m5_p5", "m5_draws", "intersection_players", "m5_int_median",
            "m5_int_p5", "players_int", "label"]  # fmt: skip
    return cells[[c for c in keep if c in cells.columns]].copy()


def assert_no_player_columns(df: pd.DataFrame) -> None:
    bad = [c for c in df.columns if c.lower() in FORBIDDEN_COLUMNS or "player_id" in c.lower()]
    if bad:
        raise ValueError(f"player-level columns in a definition table: {bad}")


def outcome_table(outcomes: dict[str, dict], final: dict, meta: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, o in {**outcomes, "FINAL": final}.items():
        rows.append({"window": name, "status": o["status"],
                     "pass_list": json.dumps(o["pass_list"]),
                     "top_group": json.dumps(o["top_group"]),
                     "confounded": bool(o.get("confounded")),
                     "stability": o.get("stability"),
                     "train_top_group": json.dumps(o.get("train_top_group", [])),
                     "intersection_sizes": json.dumps(o.get("intersection_sizes", {})),
                     **meta})  # fmt: skip
    return pd.DataFrame(rows)
