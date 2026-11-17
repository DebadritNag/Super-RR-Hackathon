"""Independent re-implementations used to spot-check the Phase 5 reliability numbers.

These deliberately avoid the matrix code of ``reliability.py``: they work from the raw residual
rows with pandas groupby and plain Python loops over players, so a shared bug is unlikely.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def independent_odd_even(
    rows: pd.DataFrame, comps: str, periods: tuple[str, ...], min_balls_per_half: int
) -> dict[str, Any]:
    """Odd/even split-half reliability from raw pressure rows (columns player_id, match_id, comp,
    period, date, resid). Matches are ordered by (date, match_id) within each player."""
    r = rows[(rows["comp"] == comps) & rows["period"].isin(periods)]
    per = r.groupby(["player_id", "match_id", "date"], as_index=False).agg(
        n=("resid", "size"), s=("resid", "sum")
    )
    m1, m2 = [], []
    for _, g in per.groupby("player_id"):
        g = g.sort_values(["date", "match_id"], kind="mergesort")
        n, s = g["n"].to_numpy(float), g["s"].to_numpy(float)
        odd_n, odd_s = n[0::2].sum(), s[0::2].sum()
        even_n, even_s = n[1::2].sum(), s[1::2].sum()
        if odd_n >= min_balls_per_half and even_n >= min_balls_per_half:
            m1.append(odd_s / odd_n)
            m2.append(even_s / even_n)
    a, b = np.asarray(m1), np.asarray(m2)
    if len(a) < 3:
        return {"players": int(len(a)), "r": None, "sb": None}
    r_ = float(np.corrcoef(a, b)[0, 1])
    return {"players": int(len(a)), "r": r_, "sb": 2 * r_ / (1 + r_)}


def independent_phase4_snr(rows: pd.DataFrame, comp: str, period: str = "TRAIN") -> dict[str, Any]:
    """Phase 4 style SNR (moment between variance over mean sigma2 / n_eff_kish) from raw rows."""
    r = rows[(rows["comp"] == comp) & (rows["period"] == period)].copy()
    r["sq"] = r["resid"] ** 2
    pm = (
        r.groupby(["player_id", "match_id"])
        .agg(n=("resid", "size"), s=("resid", "sum"), q=("sq", "sum"))
        .reset_index()
    )
    pl = pm.groupby("player_id").agg(
        n=("n", "sum"), s=("s", "sum"), q=("q", "sum"), n2=("n", lambda x: float((x**2).sum()))
    )
    pl["mean"] = pl["s"] / pl["n"]
    pl["neff"] = pl["n"] ** 2 / pl["n2"]
    ss = pl["q"] - pl["s"] ** 2 / pl["n"]
    sigma2 = float(ss.sum() / (pl["n"].sum() - len(pl)))
    between = float(pl["mean"].var(ddof=1) - np.mean(sigma2 / pl["neff"]))
    noise = float(np.mean(sigma2 / pl["neff"]))
    return {
        "players": int(len(pl)),
        "sigma2": sigma2,
        "between": between,
        "noise": noise,
        "snr": between / noise,
    }
