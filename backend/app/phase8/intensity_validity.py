"""Predeclared validity tests of the intensity candidates (criteria ``intensity.validity_tests``).

Deciles are formed within each stratum from the TRAIN values (equal-count bins on TRAIN edges) and
the same edges are applied to VALIDATION. Tests use only observable outcomes of deliveries; no
player identity is involved. Statistics are per delivery: runs charged to the bowler (bat runs and
wides/no-balls), any dismissal, and the variance of charged runs. Runs are expressed relative to the
TRAIN mean of the same (innings, phase) so the test measures what intensity adds beyond the phase.
Cells below 2,000 deliveries are NOT_ESTIMABLE. Test (d) needs the win-probability model and is not
available in this chunk (reported as NOT_AVAILABLE, not counted).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase8.constants import SEED
from app.phase8.stability import match_count_draws

MIN_CELL = 2000
N_BOOT = 500
STRATA = ("pooled", "innings_1", "innings_2", "powerplay", "middle", "death")


def _mask(df: pd.DataFrame, stratum: str) -> np.ndarray:
    if stratum == "pooled":
        return np.ones(len(df), dtype=bool)
    if stratum.startswith("innings_"):
        return (df["innings_number"] == int(stratum[-1])).to_numpy()
    return (df["innings_phase"] == stratum).to_numpy()


def decile_edges(x: np.ndarray, bins: int = 10) -> np.ndarray:
    """Interior edges of equal-count bins; duplicate edges (ties) are merged."""
    x = x[np.isfinite(x)]
    if x.size < MIN_CELL:
        return np.array([])
    return np.unique(np.quantile(x, np.linspace(0, 1, bins + 1)[1:-1]))


def assign_bins(x: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Bin index 0..len(edges) (NaN stays -1)."""
    b = np.searchsorted(edges, x, side="left")
    return np.where(np.isfinite(x), b, -1)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def outcome_frame(
    df: pd.DataFrame, base: pd.Series | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    """Per-delivery outcome columns: adjusted runs, wicket flag and the (innings, phase) baseline.

    ``base`` is the TRAIN mean of charged runs per (innings, phase); fitted here when not given.
    """
    key = list(zip(df["innings_number"], df["innings_phase"], strict=True))
    if base is None:
        tr = df["period"] == "TRAIN"
        ok = tr & df["ok_run_target"].astype(bool)
        base = (
            df.loc[ok]
            .groupby(["innings_number", "innings_phase"])["den_bowler_charged_runs"]
            .mean()
        )
    b = pd.Series(key, index=df.index).map(base)
    runs = df["den_bowler_charged_runs"].astype("float64").where(df["ok_run_target"].astype(bool))
    out = pd.DataFrame(
        {
            "runs_adj": (runs - b).to_numpy(),
            "runs": runs.to_numpy(),
            "wkt": df["out_is_wicket"]
            .astype("float64")
            .where(df["ok_wicket_target"].astype(bool))
            .to_numpy(),
        },
        index=df.index,
    )
    return out, base


def _bin_stats(vals: np.ndarray, bins: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    ok = np.isfinite(vals) & (bins >= 0)
    s = np.bincount(bins[ok], weights=vals[ok], minlength=k)
    c = np.bincount(bins[ok], minlength=k).astype(float)
    return s, c


def _contrast(s: np.ndarray, c: np.ndarray, hi: int, lo: int) -> float:
    if c[hi] == 0 or c[lo] == 0:
        return float("nan")
    return float(s[hi] / c[hi] - s[lo] / c[lo])


def _cell(
    x: np.ndarray, edges: np.ndarray, out: pd.DataFrame, match_ids: np.ndarray, boot: bool
) -> dict[str, Any]:
    """Decile statistics and bootstrap half-widths for one candidate, stratum and period."""
    bins = assign_bins(x, edges)
    use = bins >= 0
    # Dense relabel: ties can leave a bin empty (e.g. a binary candidate); lowest and highest
    # occupied bins are then "decile 1" and "decile 10".
    occupied = np.unique(bins[use])
    bins = np.where(use, np.searchsorted(occupied, bins), -1)
    k = len(occupied)
    res: dict[str, Any] = {"n_deliveries": int(use.sum()), "n_bins": k}
    stats = {}
    for name, col in (("runs", "runs_adj"), ("wkt", "wkt")):
        v = out[col].to_numpy()
        s, c = _bin_stats(v, bins, k)
        stats[name] = (s, c)
        means = np.where(c > 0, s / np.where(c > 0, c, 1), np.nan)
        res[f"{name}_by_bin"] = [float(m) for m in means]
        res[f"{name}_d1"] = float(means[0])
        res[f"{name}_d10"] = float(means[-1])
        res[f"{name}_diff"] = float(means[-1] - means[0])
        res[f"{name}_spearman"] = _spearman(
            np.arange(k)[np.isfinite(means)], means[np.isfinite(means)]
        )
    r = out["runs"].to_numpy()
    var = []
    for b in (0, k - 1):
        m = (bins == b) & np.isfinite(r)
        var.append(float(np.var(r[m], ddof=1)) if m.sum() > 2 else float("nan"))
    res["var_d1"], res["var_d10"] = var
    res["var_diff"] = var[1] - var[0]
    if boot:
        mids, inv = np.unique(match_ids[use], return_inverse=True)
        cnt = match_count_draws(mids, N_BOOT, SEED)
        for name, col in (("runs", "runs_adj"), ("wkt", "wkt")):
            v = out[col].to_numpy()[use]
            b = bins[use]
            ok = np.isfinite(v)
            ms = {}
            for tag, bb in (("hi", k - 1), ("lo", 0)):
                sel = ok & (b == bb)
                ms[tag + "_s"] = np.bincount(inv[sel], weights=v[sel], minlength=len(mids))
                ms[tag + "_c"] = np.bincount(inv[sel], minlength=len(mids)).astype(float)
            with np.errstate(all="ignore"):
                hi = (cnt @ ms["hi_s"]) / (cnt @ ms["hi_c"])
                lo = (cnt @ ms["lo_s"]) / (cnt @ ms["lo_c"])
            d = (hi - lo)[np.isfinite(hi - lo)]
            res[f"{name}_halfwidth"] = (
                float((np.percentile(d, 97.5) - np.percentile(d, 2.5)) / 2)
                if d.size > 20
                else float("nan")
            )
    return res


def run_validity_tests(df: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """One row per candidate, stratum and period with decile statistics and test flags.

    ``df`` carries ``period`` (TRAIN or VALIDATION) and the outcome columns; ``w`` has ``w_<id>``.
    The TRAIN edges of each (candidate, stratum) are applied to VALIDATION.
    """
    out, base = outcome_frame(df)
    rows: list[dict[str, Any]] = []
    is_train = (df["period"] == "TRAIN").to_numpy()
    mid = df["match_id"].to_numpy()
    for col in w.columns:
        cand = col[2:]
        x_all = w[col].to_numpy(dtype="float64")
        for st in STRATA:
            m = _mask(df, st) & np.isfinite(x_all)
            tr = m & is_train
            ntr = int(tr.sum())
            edges = decile_edges(x_all[tr]) if ntr >= MIN_CELL else np.array([])
            for per, sel in (("TRAIN", tr), ("VALIDATION", m & ~is_train)):
                row = {
                    "candidate": cand,
                    "stratum": st,
                    "period": per,
                    "n_cell": int(sel.sum()),
                    "n_train_cell": ntr,
                }
                if ntr < MIN_CELL or sel.sum() < MIN_CELL or len(edges) < 1:
                    row["status"] = "NOT_ESTIMABLE"
                    rows.append(row)
                    continue
                cell = _cell(x_all[sel], edges, out[sel], mid[sel], boot=True)
                row.update(
                    {
                        "status": "ESTIMATED",
                        **{k: v for k, v in cell.items() if not k.endswith("_by_bin")},
                    }
                )
                row["runs_by_bin"] = ";".join(f"{v:.5f}" for v in cell["runs_by_bin"])
                row["wkt_by_bin"] = ";".join(f"{v:.5f}" for v in cell["wkt_by_bin"])
                hw_a, hw_b = cell.get("runs_halfwidth", np.nan), cell.get("wkt_halfwidth", np.nan)
                row["test_a"] = bool(cell["runs_diff"] < -hw_a) if np.isfinite(hw_a) else False
                row["test_b"] = bool(cell["wkt_diff"] > hw_b) if np.isfinite(hw_b) else False
                row["test_c"] = bool(cell["var_diff"] > 0)
                row["test_e"] = (
                    bool((-cell["runs_spearman"] >= 0.7) and (cell["wkt_spearman"] >= 0.7))
                    if np.isfinite(cell["runs_spearman"]) and np.isfinite(cell["wkt_spearman"])
                    else False
                )
                row["sign_a"] = bool(cell["runs_diff"] < 0)
                row["sign_b"] = bool(cell["wkt_diff"] > 0)
                rows.append(row)
    return pd.DataFrame(rows)


def summarise_candidates(tests: pd.DataFrame, reference: tuple[str, ...] = ("P0",)) -> pd.DataFrame:
    """Pass rule and primary choice (criteria ``intensity.pass_rule`` and ``primary_choice``).

    PASS: tests a, b, e hold pooled on TRAIN, the same signs of a and b hold pooled on VALIDATION and
    tests a and b hold on TRAIN in at least two of the three phases. Tests a, b, c, e are counted
    pooled on TRAIN (d is unavailable here). Innings coverage counts innings where a and b hold on
    TRAIN. Reference candidates are reported but never primary.
    """
    rows = []
    for cand, g in tests.groupby("candidate", sort=True):

        def cell(st: str, per: str, g: pd.DataFrame = g) -> pd.Series | None:
            r = g[(g["stratum"] == st) & (g["period"] == per) & (g["status"] == "ESTIMATED")]
            return None if r.empty else r.iloc[0]

        pt, pv = cell("pooled", "TRAIN"), cell("pooled", "VALIDATION")
        tests_a = bool(pt is not None and pt["test_a"])
        tests_b = bool(pt is not None and pt["test_b"])
        tests_c = bool(pt is not None and pt["test_c"])
        tests_e = bool(pt is not None and pt["test_e"])
        val_ok = bool(pv is not None and pv["sign_a"] and pv["sign_b"])
        phases = sum(
            1
            for st in ("powerplay", "middle", "death")
            if (c := cell(st, "TRAIN")) is not None and c["test_a"] and c["test_b"]
        )
        innings = sum(
            1
            for st in ("innings_1", "innings_2")
            if (c := cell(st, "TRAIN")) is not None and c["test_a"] and c["test_b"]
        )
        passed = tests_a and tests_b and tests_e and val_ok and phases >= 2
        rows.append(
            {"candidate": cand, "pass": bool(passed), "test_a": tests_a, "test_b": tests_b,
             "test_c": tests_c, "test_e": tests_e, "test_d": "NOT_AVAILABLE_NO_WP_MODEL",
             "n_tests_passed": int(tests_a + tests_b + tests_c + tests_e),
             "validation_signs_ok": val_ok, "phases_passing": int(phases),
             "innings_coverage": int(innings), "reference_only": cand in reference,
             "runs_diff_pooled_train": None if pt is None else float(pt["runs_diff"]),
             "wkt_diff_pooled_train": None if pt is None else float(pt["wkt_diff"])}
        )  # fmt: skip
    s = pd.DataFrame(rows)
    order = ["n_tests_passed", "innings_coverage", "candidate"]
    asc = [False, False, True]
    non_ref = s[~s["reference_only"]]
    passing = non_ref[non_ref["pass"]].sort_values(order, ascending=asc)
    s["primary"] = False
    s["primary_basis"] = ""
    if len(passing):
        pick, basis = passing.iloc[0]["candidate"], "PASSING"
    elif len(non_ref):
        # No candidate meets the predeclared pass rule. The same ordering is applied to the
        # non-reference candidates and the basis is stated; the list can then never exceed
        # EXPLORATORY for the intensity definition.
        pick = non_ref.sort_values(order, ascending=asc).iloc[0]["candidate"]
        basis = "BEST_AVAILABLE_NOT_PASSING"
    else:
        return s
    s.loc[s["candidate"] == pick, ["primary", "primary_basis"]] = [True, basis]
    return s
