"""Legitimate options for improving data coverage and reliability, each quantified against the
0.5 data-weight gate (EXPERIMENTAL_NOT_VALIDATED).

Data weight here is ``B = n_eff / (n_eff + k)`` for the marginal (least-experienced) eligible
individual of a context or cell. On the Phase 4 basis ``n_eff`` is the Kish count over per-match
ball counts and ``k`` is set by the shrinkage floor (25 under ``shrink_tau4``). On the
match-cluster basis the noise of a player's mean is ``v_i`` and ``B_i = tau2 / (tau2 + v_i)``,
which equals ``n_eff_cluster / (n_eff_cluster + k)`` with ``n_eff_cluster = sigma_eff / v_i`` and
``k = sigma_eff / tau2``.

The gate is ``app.phase4.eligibility.GATE_B`` (0.5). It is read, never assigned, lowered or bypassed
here. An option that lowers the gate, changes the 0.5 requirement, scales ``tau2`` by an assumed
multiplier, uses TEST outcomes or pads a pool is not an option and cannot appear in the table
(``validate_options_table`` rejects it). No gate state is written anywhere; ``passes_gate`` is
informational. Options that change the shrinkage methodology (match-cluster ``tau2``, pooled
``tau2``) are flagged ``requires_methodology_decision``.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase5 import reliability as rb
from app.phase5.reliability import NOT_ESTIMABLE

GATE = el.GATE_B  # read, never assigned or changed here
LABELS = ("ACTUAL_RE_ESTIMATE", "DESCRIPTIVE_PROJECTION")
BASES = ("KISH_MATCH", "MATCH_CLUSTER")
FORBIDDEN_ID = re.compile(r"lower|relax|bypass|multiplier|tau_mult|gate", re.I)
FORBIDDEN_K_SOURCE = ("ASSUMED_MULTIPLIER",)
REQUIRED_COLUMNS = (
    "option_id", "option_group", "label", "scope", "window", "n_eff_marginal", "k_used",
    "k_source", "data_weight", "data_weight_lo", "data_weight_hi", "gate_used", "passes_gate",
    "extra_n_eff_required", "extra_matches_required", "pool_size_after",
    "requires_methodology_decision", "n_eff_basis", "notes",
)  # fmt: skip
EXCLUDED_BY_RULE = (
    "lowering the 0.5 gate or changing the 0.5 requirement",
    "a larger tau multiplier (shrink_tau0.5, shrink_tau2, shrink_tau4 are assumption-driven)",
    "lowering the frozen eligibility thresholds",
    "using TEST outcomes",
    "padding a pool to reach the minimum size",
)  # fmt: skip


class OptionsTableError(ValueError):
    """The options table contains a forbidden option or an inconsistent row."""


def validate_options_table(df: pd.DataFrame) -> None:
    """Reject any table that lowers the gate, uses a forbidden option or mixes bases."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise OptionsTableError(f"options table lacks columns {missing}")
    if not (df["gate_used"].astype(float) == 0.5).all() or GATE != 0.5:
        raise OptionsTableError("gate_used must be 0.5 in every row and GATE_B must be 0.5")
    bad = df[df["option_id"].astype(str).str.contains(FORBIDDEN_ID)]
    if len(bad):
        raise OptionsTableError(f"forbidden option ids: {sorted(bad['option_id'].unique())}")
    if df["k_source"].isin(FORBIDDEN_K_SOURCE).any():
        raise OptionsTableError("k_source ASSUMED_MULTIPLIER is not a legitimate option")
    if not df["label"].isin(LABELS).all():
        raise OptionsTableError("every option needs a label from " + ", ".join(LABELS))
    if not df["n_eff_basis"].isin(BASES).all():
        raise OptionsTableError("n_eff_basis must be KISH_MATCH or MATCH_CLUSTER")
    cluster_k = df["k_source"].astype(str).str.startswith("MATCH_CLUSTER")
    if ((cluster_k) != (df["n_eff_basis"] == "MATCH_CLUSTER")).any():
        raise OptionsTableError("a match-cluster k must pair with the MATCH_CLUSTER basis")


def option_row(**kw: Any) -> dict[str, Any]:
    """One options-table row with defaults; ``gate_used`` is always the gate constant."""
    base: dict[str, Any] = {
        "option_group": None, "n_eff_marginal": None, "k_used": None, "data_weight": None,
        "data_weight_lo": None, "data_weight_hi": None, "passes_gate": False,
        "extra_n_eff_required": None, "extra_matches_required": None, "pool_size_after": None,
        "requires_methodology_decision": False, "n_eff_basis": "KISH_MATCH", "notes": "",
        "baseline_data_weight": None, "applicable": True, "estimate_status": "ESTIMATED",
        "passes_on_estimable_subset": None,
    }  # fmt: skip
    base.update(kw)
    base["gate_used"] = GATE
    return base


def _f(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


# ---------------------------------------------------------------- Phase 4 basis helpers
def kish_stats(est: pd.DataFrame, elig: np.ndarray, k: float) -> dict[str, Any]:
    """Marginal Kish ``n_eff``, data weight and the extra matches the marginal player needs."""
    if not elig.any():
        return {"eligible": 0}
    ne = est["n_eff"].to_numpy()[elig]
    mt = est["matches"].to_numpy()[elig]
    j = int(np.argmin(ne))
    marg = float(ne[j])
    b = marg / (marg + k) if k > 0 else 1.0
    extra = max(0.0, k - marg)
    ratio = marg / mt[j] if mt[j] > 0 else float("nan")
    return {"eligible": int(elig.sum()), "n_eff_marginal": marg, "data_weight": float(b),
            "extra_n_eff_required": float(extra),
            "extra_matches_required": float(extra / ratio) if np.isfinite(ratio) and ratio > 0 else None,
            "median_n_eff": float(np.median(ne)), "marginal_matches": int(mt[j]),
            "pool_n_eff_at_least_k": int((ne >= k).sum())}  # fmt: skip


# ---------------------------------------------------------------- match-cluster basis
def cluster_inputs(cd: rb.CellData, mask: np.ndarray) -> dict[str, np.ndarray]:
    """Per-player mean residual, match-cluster noise variance and the validity mask."""
    sub = cd.select_cols(mask)
    dec = rb.decompose_moments(rb.boot_moments(sub, np.ones((sub.N.shape[1], 1))), 1)
    return {"y": dec["mean"][:, 0], "v": dec["match_cluster_noise_i"][:, 0],
            "ok": dec["match_cluster_ok"][:, 0], "sigma_eff": float(dec["match_cluster_sigma_eff"][0])}  # fmt: skip


def mad_tau2(y: np.ndarray, v: np.ndarray) -> float:
    """Robust between-player variance: (1.4826 * MAD of means)^2 minus the mean noise, floor 0."""
    y, v = np.asarray(y, float), np.asarray(v, float)
    if len(y) < 3:
        return float("nan")
    s = 1.4826 * float(np.median(np.abs(y - np.median(y))))
    return float(max(s * s - float(np.mean(v)), 0.0))


def tau2_estimates(
    cd: rb.CellData, w: np.ndarray, mask: np.ndarray, n_draws: int
) -> dict[str, Any]:
    """REML and MAD ``tau2`` on the match-cluster basis with a bootstrap interval of the REML value."""
    inp = cluster_inputs(cd, mask)
    ok = inp["ok"]
    out: dict[str, Any] = {"sigma_eff": _f(inp["sigma_eff"]), "players": int(ok.sum()),
                           "status": NOT_ESTIMABLE}  # fmt: skip
    if ok.sum() < 8 or not np.isfinite(inp["sigma_eff"]):
        return out
    r = rb.reml_tau2(inp["y"][ok], inp["v"][ok])
    out.update(tau2_reml=_f(r["tau2"]), reml_converged=bool(r["converged"]),
               tau2_mad=_f(mad_tau2(inp["y"][ok], inp["v"][ok])), status="ESTIMATED")  # fmt: skip
    sub = cd.select_cols(mask)
    ws = w[mask][:, :n_draws]
    dec = rb.decompose_moments(rb.boot_moments(sub, ws), 1)
    draws = []
    for d in range(ws.shape[1]):
        okd = dec["match_cluster_ok"][:, d]
        if okd.sum() < 8:
            continue
        rd = rb.reml_tau2(dec["mean"][okd, d], dec["match_cluster_noise_i"][okd, d])
        if np.isfinite(rd["tau2"]):
            draws.append(rd["tau2"])
    d_ = np.asarray(draws)
    out.update(boot_draws=int(d_.size),
               tau2_lo=_f(np.percentile(d_, 2.5)) if d_.size >= 20 else None,
               tau2_hi=_f(np.percentile(d_, 97.5)) if d_.size >= 20 else None,
               boot_share_positive=float((d_ > 1e-12).mean()) if d_.size else None)  # fmt: skip
    return out


def cluster_b(
    tau2: float | None, v_eligible: np.ndarray, sigma_eff: float | None
) -> dict[str, Any]:
    """Marginal data weight ``tau2 / (tau2 + v_i)`` over eligible players with a finite ``v_i``."""
    v = np.asarray(v_eligible, float)
    v = v[np.isfinite(v) & (v > 0)]
    if tau2 is None or not np.isfinite(tau2) or v.size == 0 or sigma_eff is None:
        return {"status": NOT_ESTIMABLE, "players_used": int(v.size)}
    vmax = float(v.max())
    b = float(tau2 / (tau2 + vmax)) if tau2 + vmax > 0 else float("nan")
    return {"status": "ESTIMATED", "data_weight": b, "players_used": int(v.size),
            "n_eff_marginal": float(sigma_eff / vmax),
            "k_used": float(sigma_eff / tau2) if tau2 > 0 else None}  # fmt: skip


def parent_of(phase: str, situation: str, kind: str) -> tuple[str, str] | None:
    """Parent context for pooling ``tau2``: phases pooled keeps the situation, and vice versa."""
    if kind == "phases_pooled":
        return ("ALL", situation) if phase != "ALL" else None
    if kind == "situations_pooled":
        return (phase, "ALL") if situation != "ALL" else None
    raise ValueError(kind)


# ---------------------------------------------------------------- summaries
def summarize(opts: pd.DataFrame) -> pd.DataFrame:
    """Per option: rows, rows passing the gate, best and median data weight, who would pass."""
    rows = []
    for oid, g in opts.groupby("option_id", sort=True):
        passing = g[g["passes_gate"].astype(bool)]
        rows.append({
            "option_id": oid, "option_group": g["option_group"].iloc[0], "label": g["label"].iloc[0],
            "scope_kind": g["scope"].astype(str).str.split(":").str[0].iloc[0], "rows": int(len(g)),
            "rows_with_estimate": int(g["data_weight"].notna().sum()),
            "rows_passing_gate": int(len(passing)),
            "rows_passing_on_estimable_subset": int(
                g["passes_on_estimable_subset"].astype("boolean").fillna(False).sum()
            ),
            "rows_marginal_not_estimable": int(
                (g["estimate_status"] == "MARGINAL_INDIVIDUAL_NOT_ESTIMABLE").sum()
            ),
            "best_data_weight": _f(g["data_weight"].max()),
            "median_data_weight": _f(g["data_weight"].median()),
            "requires_methodology_decision": bool(g["requires_methodology_decision"].any()),
            "n_eff_basis": g["n_eff_basis"].iloc[0], "gate_used": GATE,
            "passing_scopes": "; ".join(sorted(passing["scope"].astype(str))) or "none",
        })  # fmt: skip
    return pd.DataFrame(rows)
