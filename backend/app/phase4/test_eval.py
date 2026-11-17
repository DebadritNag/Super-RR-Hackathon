"""Phase 4 final TEST-period evaluation of the frozen configuration. EXPERIMENTAL_NOT_VALIDATED.

Runs once, inside ``evaluate_on_test`` (the only function that opens the test lock). Nothing here
changes a choice: the definition, thresholds, shrinkage configuration and eligibility rules are
read from the frozen-choices file whose SHA-256 the lock log recorded before the lock opened.

Population level (always): B0 calibration on TEST and the pressure effect, the mean B0 residual of
pressure rows minus non-pressure rows of the same definition population, with a seeded
match-cluster bootstrap interval. Player level (only when at least ``MIN_PLAYERS`` players qualify):
how well the PRE_TEST shrunk estimate predicts the TEST mean residual, compared with the raw
PRE_TEST mean and with a zero prediction. Cells with fewer qualifying players are reported as
``INSUFFICIENT_FOR_PLAYER_LEVEL_TEST`` and are never padded or relaxed.

Par for TEST matches is strictly prior and may include earlier TEST first innings (they precede the
evaluated match). Sensitivity ``TEST_CORE`` limits TEST to dates up to the configured core end.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4 import shrink as sh
from app.phase4.baseline import STREAMS, fit_baseline_set, prepare_frame
from app.phase4.constants import SCOPE, SEED, STATUS
from app.phase4.data import load_state_with_period
from app.phase4.split import Split, TestLock, evaluate_on_test

MIN_PLAYERS = 15  # design notes: player-level TEST evaluation needs at least 15 qualifying players
MIN_TEST_BALLS = 6  # a qualifying player needs this many TEST pressure balls (fixed a priori)
N_BOOT = 1000
SCOPES = ("TEST", "TEST_CORE")


def _num(x: float) -> float | None:
    return None if x is None or not np.isfinite(x) else float(x)


def pressure_effect(rows: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    """Mean residual of pressure rows minus non-pressure rows, match-cluster bootstrap interval.

    ``rows`` needs ``match_id``, ``press`` (bool) and ``resid``; only definition-population rows.
    """
    n_press, n_non = int(rows["press"].sum()), int((~rows["press"]).sum())
    out: dict[str, Any] = {
        "pressure_rows": n_press,
        "non_pressure_rows": n_non,
        "matches": int(rows["match_id"].nunique()),
        "effect": None,
        "ci_low": None,
        "ci_high": None,
    }
    if n_press == 0 or n_non == 0:
        out["status"] = "INSUFFICIENT_ROWS"
        return out
    g = rows.groupby(["match_id", "press"])["resid"].agg(["size", "sum"]).unstack(fill_value=0)
    n_p, s_p = g[("size", True)].to_numpy(float), g[("sum", True)].to_numpy(float)
    n_n, s_n = g[("size", False)].to_numpy(float), g[("sum", False)].to_numpy(float)
    out["effect"] = float(s_p.sum() / n_p.sum() - s_n.sum() / n_n.sum())
    W = sh.match_weights(len(g), n_boot, seed).astype(float)
    with np.errstate(all="ignore"):
        eff = (W @ s_p) / (W @ n_p) - (W @ s_n) / (W @ n_n)
    eff = eff[np.isfinite(eff)]
    if len(eff):
        out["ci_low"], out["ci_high"] = (
            float(np.percentile(eff, 2.5)),
            float(np.percentile(eff, 97.5)),
        )
    out["status"] = "OK"
    return out


def _spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return _num(float(pd.Series(a).rank().corr(pd.Series(b).rank())))


def player_level(
    press: pd.DataFrame,
    comp: str,
    role: str,
    cfg: str,
    elig: dict[str, Any],
    test_scope: str,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    """Player-level TEST check for one cell (primary stream). ``press`` has period and resid."""
    r = press[press["comp"] == comp]
    pre = r[r["period"].isin(["TRAIN", "VALIDATION"])]
    test = r[r["period"] == "TEST"]
    t = elig.get("threshold_balls")
    base = {"format": comp, "role": role, "test_scope": test_scope, "shrinkage_config": cfg}
    if t is None:
        return {**base, "status": "NO_ELIGIBILITY_THRESHOLD", "qualifying_players": 0}
    fit = sh.fit_cell(sh.player_table(sh.match_stats(r[r["period"] == "TRAIN"])))
    pt_pre = sh.player_table(sh.match_stats(pre))
    if pt_pre.empty or test.empty:
        return {**base, "status": "NO_DATA", "qualifying_players": 0}
    est = sh.estimate(pt_pre, fit, cfg)
    ms_test = sh.match_stats(test)
    pt_test = sh.player_table(ms_test)
    ok = (pt_pre["n"] >= float(t) * float(elig["wr"])).reindex(pt_test.index, fill_value=False)
    elig_n = int(ok.sum())
    q = pt_test.index[(ok & (pt_test["n"] >= MIN_TEST_BALLS)).to_numpy()]
    base.update(
        {
            "pre_test_eligible_players_with_test_balls": elig_n,
            "qualifying_players": int(len(q)),
            "min_test_balls": MIN_TEST_BALLS,
            "min_players_required": MIN_PLAYERS,
        }
    )
    if len(q) < MIN_PLAYERS:
        return {**base, "status": "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST"}
    y = pt_test.loc[q, "mean"].to_numpy()
    w = pt_test.loc[q, "n"].to_numpy()
    raw = pt_pre.loc[q, "mean"].to_numpy()
    shr = est.loc[q, "shrunk"].to_numpy()
    losses = {
        "shrunk": float(np.average((y - shr) ** 2, weights=w)),
        "raw": float(np.average((y - raw) ** 2, weights=w)),
        "zero": float(np.average(y**2, weights=w)),
    }
    # paired match-cluster bootstrap of loss(shrunk) - loss(raw) over TEST matches
    plab, N, S = sh._match_matrices(ms_test[ms_test["player_id"].isin(q)])
    pos = pd.Index(plab).get_indexer(q)
    N, S = N[pos], S[pos]
    W = sh.match_weights(N.shape[1], n_boot, seed).astype(float)
    nb, sb = N @ W.T, S @ W.T
    with np.errstate(all="ignore"):
        yb = np.where(nb > 0, sb / np.where(nb > 0, nb, 1), np.nan)
    diff = []
    for j in range(yb.shape[1]):
        m = np.isfinite(yb[:, j]) & (nb[:, j] > 0)
        if m.sum() >= 3:
            ws = nb[m, j]
            diff.append(
                np.average((yb[m, j] - shr[m]) ** 2, weights=ws)
                - np.average((yb[m, j] - raw[m]) ** 2, weights=ws)
            )
    d = np.array(diff)
    return {
        **base,
        "status": "OK",
        "loss_weighted_mse": losses,
        "loss_diff_shrunk_minus_raw": float(losses["shrunk"] - losses["raw"]),
        "loss_diff_ci_low": _num(np.percentile(d, 2.5)) if len(d) else None,
        "loss_diff_ci_high": _num(np.percentile(d, 97.5)) if len(d) else None,
        "spearman_shrunk_vs_test": _spearman(shr, y),
        "spearman_raw_vs_test": _spearman(raw, y),
    }


def evaluate_frozen(
    frozen_path: Path | str,
    lock: TestLock,
    split: Split,
    store: Path | str,
    n_boot: int = N_BOOT,
) -> dict[str, Any]:
    """Open the lock once (via ``evaluate_on_test``) and evaluate the frozen configuration."""

    def run(open_lock: TestLock) -> dict[str, Any]:
        # the frozen file is read only after evaluate_on_test verified its hash against FREEZE
        frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
        defn = frozen["definition"]["id"]
        cfg = frozen["shrinkage"]["config"]
        thr_frozen = frozen["definition"]["train_only_thresholds"]
        elig_rules = {k: v["analysis"] for k, v in frozen["eligibility"].items()}
        raw = load_state_with_period(split, store)
        d, _ = prepare_frame(raw, split)
        d = sc.add_signals(d, open_lock)
        bs = fit_baseline_set(d)
        _, q = sc.parse_definition(defn)
        thr = sc.fit_thresholds(d[d["period"] == "TRAIN"], q)
        thr_match = all(abs(thr[k] - float(v)) < 1e-6 for k, v in thr_frozen.items())
        result: dict[str, Any] = {
            "status": STATUS,
            "official_ranking": False,
            "definition_id": defn,
            "shrinkage_config": cfg,
            "baseline_version": bs.version,
            "frozen_thresholds_reproduced": bool(thr_match),
            "test_rows_total": int((d["period"] == "TEST").sum()),
            "test_matches": int(d.loc[d["period"] == "TEST", "match_id"].nunique()),
            "min_players_player_level": MIN_PLAYERS,
            "min_test_balls": MIN_TEST_BALLS,
            "calibration": [],
            "population": [],
            "player_level": [],
        }
        core_end = split.test_core_end
        result["test_core_end"] = None if core_end is None else str(core_end.date())
        for role, stream, _ in STREAMS:
            tagged = en.tag_rows(en.base_rows(d, bs, role, stream, open_lock), d, defn, thr)
            for scope in SCOPES:
                t = tagged
                if scope == "TEST_CORE" and core_end is not None:
                    t = tagged[(tagged["period"] != "TEST") | (tagged["date"] <= core_end)]
                for comp in SCOPE:
                    rc = t[(t["comp"] == comp) & (t["period"] == "TEST")]
                    if rc.empty:
                        continue
                    result["calibration"].append(
                        {
                            "test_scope": scope,
                            "format": comp,
                            "role": role,
                            "stream": stream,
                            "rows": int(len(rc)),
                            "matches": int(rc["match_id"].nunique()),
                            "mean_actual": float(rc["actual"].mean()),
                            "mean_expected": float(rc["expected"].mean()),
                            "mean_residual": float(rc["resid"].mean()),
                        }
                    )
                    pop = rc[rc["in_pop"]]
                    result["population"].append(
                        {
                            "test_scope": scope,
                            "format": comp,
                            "role": role,
                            "stream": stream,
                            **pressure_effect(pop, n_boot),
                        }
                    )
                if stream == en.PRIMARY[role][0]:
                    pr = t[t["press"]]
                    for comp in SCOPE:
                        e = elig_rules.get(f"{comp}|{role}")
                        if e is None:
                            continue
                        result["player_level"].append(
                            player_level(pr, comp, role, cfg, e, scope, n_boot)
                        )
        return result

    return evaluate_on_test(frozen_path, lock, run)
