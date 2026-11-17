"""Phase 4 shrinkage of player pressure residuals towards the pooled mean of OTHER players.

Estimator (one cell = role x format x stream; batter and bowler populations and the IPL and T20I
populations are never mixed; formats are combined only after shrinkage):

    m_i = mu_{-i} + B_i (r_i - mu_{-i}),   B_i = n_eff_i / (n_eff_i + k)

* r_i: player i's mean residual in the scoring window; n_eff_i: Kish effective number of balls
  over the player's matches.
* mu_{-i}: pooled (ball-weighted) mean residual of all other players, from TRAIN rows only, so the
  player's own deliveries never enter the target (leave-one-player-out).
* k = sigma2_within / tau2 from the method of moments in ``analytics.shrinkage.k_from_children``,
  with tau2 floored at ``floor * sigma2_within`` (so k <= 1 / floor), fitted on TRAIN only.

Assumptions: residual means are approximately normal, matches are independent clusters, players
are exchangeable within a cell, noise is homoscedastic after n_eff, tau2 is constant over the
window, tau2 estimation error is not propagated into intervals. A floor hit means the data show
less between-player spread than the floor, so shrinkage is weaker than the data support.

Configurations: ``shrink_none`` (zero shrinkage, sensitivity), ``shrink_eb`` (fitted, default),
``shrink_tau0.5`` / ``shrink_tau2`` / ``shrink_tau4`` (tau2 multiplied after the floor),
``shrink_floor0.001`` (floor 0.001), ``shrink_target0`` (target 0, sensitivity).
Parameters are chosen on TRAIN and VALIDATION only; TEST outcomes are never an input.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.shrinkage import k_from_children, n_eff_kish, pooled_other_mean
from app.phase4.constants import SEED

CONFIGS: dict[str, dict[str, Any]] = {
    "shrink_none": {"floor": 0.01, "mult": 1.0, "target": "pooled_other", "zero": True},
    "shrink_eb": {"floor": 0.01, "mult": 1.0, "target": "pooled_other", "zero": False},
    "shrink_tau0.5": {"floor": 0.01, "mult": 0.5, "target": "pooled_other", "zero": False},
    "shrink_tau2": {"floor": 0.01, "mult": 2.0, "target": "pooled_other", "zero": False},
    "shrink_tau4": {"floor": 0.01, "mult": 4.0, "target": "pooled_other", "zero": False},
    "shrink_floor0.001": {"floor": 0.001, "mult": 1.0, "target": "pooled_other", "zero": False},
    "shrink_target0": {"floor": 0.01, "mult": 1.0, "target": "zero", "zero": False},
}
DEFAULT_CONFIG = "shrink_eb"
CHOOSABLE = ("shrink_eb", "shrink_tau0.5", "shrink_tau2", "shrink_tau4", "shrink_floor0.001")
SHRINKAGE_CHOICE_PATH = None  # set by the scripts; the choice is written before any TEST read


def match_stats(rows: pd.DataFrame) -> pd.DataFrame:
    """Per (player, match) sufficient statistics of residuals: n, s, s2.

    ``rows`` needs ``player_id``, ``match_id``, ``resid``.
    """
    t = rows[["player_id", "match_id"]].copy()
    t["n"] = 1.0
    t["s"] = rows["resid"].to_numpy(dtype=float)
    t["s2"] = t["s"] ** 2
    return t.groupby(["player_id", "match_id"], as_index=False).agg(
        n=("n", "sum"), s=("s", "sum"), s2=("s2", "sum")
    )


def player_table(ms: pd.DataFrame) -> pd.DataFrame:
    """Per player: n, s, s2, mean, matches and Kish effective n (over per-match ball counts)."""
    if ms.empty:
        return pd.DataFrame(columns=["n", "s", "s2", "mean", "matches", "n_eff"])
    g = ms.groupby("player_id")
    pt = g.agg(n=("n", "sum"), s=("s", "sum"), s2=("s2", "sum"), matches=("match_id", "nunique"))
    pt["mean"] = pt["s"] / pt["n"]
    pt["n_eff"] = g["n"].apply(lambda x: n_eff_kish(x.to_numpy()))
    return pt


def fit_cell(train_pt: pd.DataFrame) -> dict[str, Any]:
    """TRAIN-only variance components and pooled sums for one cell."""
    if len(train_pt) < 2:
        return {"sigma2": float("nan"), "between": float("nan"), "players": int(len(train_pt)),
                "total_s": float(train_pt["s"].sum()), "total_n": float(train_pt["n"].sum()),
                "train_s": train_pt["s"], "train_n": train_pt["n"]}  # fmt: skip
    ss = (train_pt["s2"] - train_pt["s"] ** 2 / train_pt["n"]).to_numpy()
    kk = k_from_children(
        train_pt["n"].to_numpy(), train_pt["n_eff"].to_numpy(), train_pt["mean"].to_numpy(), ss
    )
    return {
        "sigma2": kk["sigma2_within"],
        "between": kk["between_moment"],
        "players": int(len(train_pt)),
        "total_s": float(train_pt["s"].sum()),
        "total_n": float(train_pt["n"].sum()),
        "train_s": train_pt["s"],
        "train_n": train_pt["n"],
    }


def k_for(fit: dict[str, Any], config: str) -> dict[str, Any]:
    """Shrinkage strength k for a configuration (0 for zero shrinkage), with floor-hit flag."""
    cfg = CONFIGS[config]
    if cfg["zero"]:
        return {"k": 0.0, "tau2": float("nan"), "floor_hit": False}
    s2, between = fit["sigma2"], fit["between"]
    if not (np.isfinite(s2) and s2 > 0 and np.isfinite(between)):
        return {"k": 1.0 / cfg["floor"], "tau2": float("nan"), "floor_hit": True}
    floor_abs = cfg["floor"] * s2
    tau2 = max(max(between, floor_abs) * cfg["mult"], floor_abs)
    return {"k": float(s2 / tau2), "tau2": float(tau2), "floor_hit": bool(between <= floor_abs)}


def lpo_target(fit: dict[str, Any], player_ids: pd.Index) -> np.ndarray:
    """Pooled mean residual of all OTHER players (TRAIN); a player's own TRAIN data is removed."""
    own_s = fit["train_s"].reindex(player_ids).fillna(0.0).to_numpy()
    own_n = fit["train_n"].reindex(player_ids).fillna(0.0).to_numpy()
    return np.asarray(pooled_other_mean(fit["total_s"], fit["total_n"], own_s, own_n))


def estimate(pt: pd.DataFrame, fit: dict[str, Any], config: str = DEFAULT_CONFIG) -> pd.DataFrame:
    """Shrunk estimate per player of ``pt`` (scoring-window table)."""
    kinfo = k_for(fit, config)
    out = pt.copy()
    tgt = lpo_target(fit, pt.index)
    if CONFIGS[config]["target"] == "zero":
        tgt = np.zeros(len(pt))
    k = kinfo["k"]
    den = pt["n_eff"].to_numpy() + k
    B = np.where(den > 0, pt["n_eff"].to_numpy() / np.where(den > 0, den, 1.0), 0.0)
    tgt = np.where(np.isfinite(tgt), tgt, 0.0)
    out["target"] = tgt
    out["B"] = B
    out["shrunk"] = tgt + B * (pt["mean"].to_numpy() - tgt)
    out["k"] = k
    out["tau2"] = kinfo["tau2"]
    out["floor_hit"] = kinfo["floor_hit"]
    out["posterior_sd"] = np.sqrt(np.maximum(B * fit["sigma2"] / np.maximum(pt["n_eff"], 1e-12), 0))
    return out


def _match_matrices(ms: pd.DataFrame):
    pid, plab = pd.factorize(ms["player_id"], sort=True)
    mid, mlab = pd.factorize(ms["match_id"], sort=True)
    N = np.zeros((len(plab), len(mlab)))
    S = np.zeros_like(N)
    np.add.at(N, (pid, mid), ms["n"].to_numpy(float))
    np.add.at(S, (pid, mid), ms["s"].to_numpy(float))
    return plab, N, S


def match_weights(n_matches: int, n_boot: int, seed: int) -> np.ndarray:
    """Seeded multinomial match-resample counts, shape (n_boot, n_matches)."""
    rng = np.random.default_rng(seed)
    return rng.multinomial(n_matches, np.full(n_matches, 1.0 / n_matches), size=n_boot)


def bootstrap_draws(
    ms: pd.DataFrame, est: pd.DataFrame, n_boot: int = 1000, seed: int = SEED
) -> pd.DataFrame:
    """Match-cluster bootstrap draws of the shrunk estimate (k and mu_{-i} held fixed).

    Returns a frame (players x n_boot); NaN where a player has no balls in a resample.
    """
    plab, N, S = _match_matrices(ms)
    W = match_weights(N.shape[1], n_boot, seed).astype(float)
    nb, sb = N @ W.T, S @ W.T
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(nb > 0, sb / np.where(nb > 0, nb, 1), np.nan)
    e = est.reindex(plab)
    # n_eff in a resample: the player's n_eff scaled by resampled / original ball count
    ne = e["n_eff"].to_numpy()[:, None] * nb / np.maximum(N.sum(1)[:, None], 1.0)
    k = float(e["k"].iloc[0]) if len(e) else 0.0
    B = np.where(ne + k > 0, ne / np.where(ne + k > 0, ne + k, 1), 0.0)
    tgt = e["target"].to_numpy()[:, None]
    draws = np.where(nb > 0, tgt + B * (r - tgt), np.nan)
    return pd.DataFrame(draws, index=plab)


def interval(draws: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    with np.errstate(all="ignore"):
        lo = np.nanpercentile(draws.to_numpy(), 2.5, axis=1)
        hi = np.nanpercentile(draws.to_numpy(), 97.5, axis=1)
    return pd.Series(lo, index=draws.index), pd.Series(hi, index=draws.index)


# ---------------------------------------------------------------- choice on VALIDATION only
def choose_shrinkage(
    cells: list[dict[str, Any]], n_boot: int = 1000, seed: int = SEED
) -> dict[str, Any]:
    """Pick a shrinkage configuration using TRAIN estimates against VALIDATION outcomes.

    Each cell dict has ``fit`` (TRAIN fit), ``train_pt`` (TRAIN player table) and ``val_ms``
    (VALIDATION player-match statistics). Loss: ball-weighted squared error between the
    TRAIN-based estimate and the VALIDATION mean residual, pooled over cells. A non-default
    configuration is chosen only when its paired loss difference to ``shrink_eb`` is below -1
    match-cluster-bootstrap SE.
    """
    configs = list(CONFIGS)
    parts = []
    for c in cells:
        tp, vm = c["train_pt"], c["val_ms"]
        plab, N, S = _match_matrices(vm) if len(vm) else (pd.Index([]), None, None)
        common = tp.index.intersection(pd.Index(plab))
        if len(common) == 0:
            continue
        pos = pd.Index(plab).get_indexer(common)
        preds = {
            cfg: estimate(tp.loc[common], c["fit"], cfg)["shrunk"].to_numpy() for cfg in configs
        }
        W = match_weights(N.shape[1], n_boot, seed).astype(float)
        nb, sb = N[pos] @ W.T, S[pos] @ W.T
        with np.errstate(invalid="ignore", divide="ignore"):
            vm_mean = np.where(nb > 0, sb / np.where(nb > 0, nb, 1), 0.0)
        n0, s0 = N[pos].sum(1), S[pos].sum(1)
        parts.append((preds, n0, s0 / np.where(n0 > 0, n0, 1), nb, vm_mean))
    if not parts:
        return {"chosen": DEFAULT_CONFIG, "reason": "NO_VALIDATION_OVERLAP", "losses": {}}
    loss, boot = {}, {}
    for cfg in configs:
        num = sum(float((n0 * (p[cfg] - m0) ** 2).sum()) for p, n0, m0, _, _ in parts)
        den = sum(float(n0.sum()) for _, n0, _, _, _ in parts)
        loss[cfg] = num / den if den > 0 else float("nan")
        bn = sum((nb * (p[cfg][:, None] - vmm) ** 2).sum(0) for p, _, _, nb, vmm in parts)
        bd = sum(nb.sum(0) for _, _, _, nb, _ in parts)
        boot[cfg] = bn / np.where(bd > 0, bd, np.nan)
    rows, best, best_gain = {}, DEFAULT_CONFIG, 0.0
    for cfg in configs:
        diff = boot[cfg] - boot[DEFAULT_CONFIG]
        se = float(np.nanstd(diff, ddof=1))
        d = loss[cfg] - loss[DEFAULT_CONFIG]
        rows[cfg] = {"loss": loss[cfg], "diff_vs_eb": d, "bootstrap_se": se,
                     "choosable": cfg in CHOOSABLE}  # fmt: skip
        if cfg in CHOOSABLE and cfg != DEFAULT_CONFIG and d < -se and -d > best_gain:
            best, best_gain = cfg, -d
    return {
        "chosen": best,
        "rule": "non-default only if paired loss difference < -1 bootstrap SE; none/target0 never chosen",
        "selection_data": ["TRAIN", "VALIDATION"],
        "test_outcomes_used": False,
        "n_boot": n_boot,
        "seed": seed,
        "losses": rows,
    }


def record_choice(choice: dict[str, Any], path: Path | str) -> Path:
    """Write the shrinkage choice (deterministic JSON). Must be called before any TEST read."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(choice, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
