"""Strictly prior first-innings par (primary) and leave-one-match-out par (descriptive only).

Par for an evaluated match uses only source innings of matches with ``match_date`` strictly
before the evaluated match's date, in the same competition type. Same-date matches are excluded
(including the earlier match of a double-header). With fewer than ``min_prior`` prior source
innings the par is NULL and ``par_unavailable_insufficient_prior`` is True. Nothing is
zero-filled and nothing falls back to another format or to a leave-one-match-out value.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics import pressure_features as pf
from app.phase4.constants import DESCRIPTIVE_LOMO_LABEL, PAR_FLAG, SCOPE


class LeakageError(RuntimeError):
    """A feature that uses future matches was requested by the scoring pipeline."""


class LeakageGuard:
    """Rejects any column that is built from future matches."""

    forbidden_fragments = ("_lomo", DESCRIPTIVE_LOMO_LABEL.lower(), "full_sample")

    @classmethod
    def check_columns(cls, columns: list[str] | tuple[str, ...]) -> None:
        bad = [c for c in columns if any(f in c.lower() for f in cls.forbidden_fragments)]
        if bad:
            raise LeakageError(f"columns use future matches and are descriptive only: {bad}")


def strictly_prior_par(
    df: pd.DataFrame,
    min_prior: int = 30,
    scope: tuple[str, ...] = SCOPE,
    source_cutoff: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Per-row strictly prior par for innings-1 rows of in-scope competitions.

    Returns a frame indexed like ``df`` with ``par_runs_prior``, ``par_prior_innings_n``,
    ``par_applicable`` and ``par_unavailable_insufficient_prior``. ``source_cutoff`` limits the
    source innings to match_date <= cutoff (used for the TEST par sensitivity).
    """
    src = pf.source_innings(df)
    if source_cutoff is not None:
        src = src[src["match_date"] <= pd.Timestamp(source_cutoff)].reset_index(drop=True)
    matrix = pf.par_matrix(df, src)
    n = len(df)
    par = np.full(n, np.nan)
    prior_n = np.zeros(n, dtype="int64")
    inn1 = ((df["innings_number"] == 1) & df["competition_type"].isin(scope)).to_numpy()
    for comp in scope:
        sm = (src["competition_type"] == comp).to_numpy()
        fc = matrix[sm]
        dates = src.loc[sm, "match_date"].to_numpy()
        order = np.argsort(dates, kind="stable")
        cum = np.vstack([np.zeros(121), np.cumsum(fc[order], axis=0)])
        sorted_dates = dates[order]
        rmask = inn1 & (df["competition_type"] == comp).to_numpy()
        if not rmask.any():
            continue
        b = np.clip(df.loc[rmask, "legal_balls_bowled_before"].to_numpy().astype(int), 0, 120)
        k = np.searchsorted(sorted_dates, df.loc[rmask, "match_date"].to_numpy(), side="left")
        with np.errstate(invalid="ignore", divide="ignore"):
            value = cum[k, b] / np.where(k > 0, k, 1)
        par[rmask] = np.where(k >= min_prior, value, np.nan)
        prior_n[rmask] = k
    out = pd.DataFrame(index=df.index)
    out["par_runs_prior"] = par
    out["par_prior_innings_n"] = prior_n
    out["par_applicable"] = inn1
    out[PAR_FLAG] = inn1 & np.isnan(par)
    return out


def lomo_par_descriptive(df: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    """Leave-one-match-out par. Uses future matches: retrospective descriptive analysis only."""
    cols, _ = pf.par_columns(df, rules)
    out = pd.DataFrame(index=df.index)
    out[f"par_runs_lomo__{DESCRIPTIVE_LOMO_LABEL}"] = cols["par_runs_lomo"]
    return out


def par_coverage(df: pd.DataFrame, par: pd.DataFrame) -> dict[str, Any]:
    """Counts of innings-1 rows, innings and matches with no prior par, by format and period.

    ``df`` needs ``period``, ``match_id``, ``innings_number``, ``match_date``,
    ``competition_type``; ``par`` is the output of ``strictly_prior_par``.
    """
    app = par["par_applicable"].to_numpy()
    d = df.loc[app, ["match_id", "match_date", "competition_type", "period"]].copy()
    d["unavailable"] = par.loc[app, PAR_FLAG].to_numpy()
    rows: list[dict[str, Any]] = []
    for (comp, period), g in d.groupby(["competition_type", "period"], sort=True):
        bad = g[g["unavailable"]]
        rows.append(
            {
                "competition_type": comp,
                "period": period,
                "innings1_rows": int(len(g)),
                "rows_unavailable": int(len(bad)),
                "innings_unavailable": int(bad["match_id"].nunique()),
                "matches": int(g["match_id"].nunique()),
                "last_unavailable_date": None
                if bad.empty
                else pd.Timestamp(bad["match_date"].max()).date().isoformat(),
            }
        )
    return {
        "min_prior_innings_note": "NULL and flagged, never zero-filled, no cross-format fallback",
        "rows": rows,
        "total_rows_unavailable": int(sum(r["rows_unavailable"] for r in rows)),
        "total_innings_unavailable": int(sum(r["innings_unavailable"] for r in rows)),
    }
