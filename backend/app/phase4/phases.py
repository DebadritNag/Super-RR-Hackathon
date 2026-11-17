"""Innings-phase boundary documentation, shortened-innings reporting and no-future-info checks.

Phase is ball-based: powerplay if B < floor(3L/10), death if B >= ceil(3L/4), middle otherwise,
where B is the number of legal balls bowled before the delivery and L is the innings limit in
balls. This module wraps ``app.analytics.phase_engine`` and never changes it.

Revision timing: the data records the revised limit of an innings but not when the revision was
announced. A label for a ball that was bowled before the announcement may therefore use a limit
that was only known later. Every innings whose limit is not 120 is already excluded from primary
scoring (``dls_exclude_primary``), so no primary score depends on this. Resources are never
imputed.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.phase_engine import phase_bounds, phase_label
from app.analytics.pressure_features import SCOPE as _SCOPE

REGULATION_INNINGS = (1, 2)
DEFAULT_LIMIT = 120


def boundary_table(limits: Iterable[int]) -> pd.DataFrame:
    """Exact boundaries per innings limit (balls). Phase sizes always sum to L."""
    rows = []
    for limit in sorted({int(x) for x in limits}):
        pp_end, death_start = phase_bounds(limit)
        rows.append(
            {
                "innings_limit": limit,
                "powerplay_end_ball": pp_end,
                "death_start_ball": death_start,
                "powerplay_balls": pp_end,
                "middle_balls": death_start - pp_end,
                "death_balls": limit - death_start,
            }
        )
    return pd.DataFrame(rows)


def phase_for(legal_balls_before: Iterable[int], limit: int) -> list[str]:
    """Phase labels for balls bowled before the delivery, for one innings limit."""
    b = pd.Series(list(legal_balls_before), dtype="int64")
    return phase_label(b, pd.Series([limit] * len(b), index=b.index)).tolist()


def regulation(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["innings_number"].isin(REGULATION_INNINGS)]


def innings_limits(df: pd.DataFrame) -> pd.DataFrame:
    """One row per regulation innings with its limit and delivery count."""
    reg = regulation(df)
    g = reg.groupby(["match_id", "innings_number"], sort=True)
    out = g.agg(
        limit=("innings_limit_balls", "first"),
        n_limits=("innings_limit_balls", "nunique"),
        deliveries=("innings_limit_balls", "size"),
        competition_type=("competition_type", "first"),
    ).reset_index()
    if "period" in reg:
        out["period"] = g["period"].first().to_numpy()
    if "limit_source" in reg:
        out["limit_source"] = g["limit_source"].first().to_numpy()
    if "dls_exclude_primary" in reg:
        out["dls_excluded"] = g["dls_exclude_primary"].all().to_numpy()
    return out


def shortened_report(df: pd.DataFrame) -> dict[str, Any]:
    """Affected innings and deliveries for every limit that is not 120 (innings 1 and 2)."""
    inn = innings_limits(df)
    short = inn[inn["limit"] != DEFAULT_LIMIT]
    by_limit = (
        inn.groupby("limit")
        .agg(innings=("match_id", "size"), deliveries=("deliveries", "sum"))
        .reset_index()
        .sort_values("limit")
    )
    bounds = boundary_table(by_limit["limit"].astype(int))
    table = by_limit.merge(bounds, left_on="limit", right_on="innings_limit").drop(
        columns="innings_limit"
    )
    report: dict[str, Any] = {
        "limits_present": [int(x) for x in by_limit["limit"]],
        "limit_constant_within_every_innings": bool((inn["n_limits"] == 1).all()),
        "by_limit": table.to_dict(orient="records"),
        "regulation_innings_total": int(len(inn)),
        "shortened_innings": int(len(short)),
        "shortened_matches": int(short["match_id"].nunique()),
        "shortened_deliveries": int(short["deliveries"].sum()),
        "shortened_innings_by_innings_number": {
            str(k): int(v) for k, v in short.groupby("innings_number").size().items()
        },
    }
    if "limit_source" in inn:
        report["shortened_innings_by_limit_source"] = {
            str(k): int(v) for k, v in short.groupby("limit_source").size().items()
        }
    if "period" in inn:
        report["shortened_innings_by_period"] = {
            f"{c}|{p}": int(v)
            for (c, p), v in short.groupby(["competition_type", "period"]).size().items()
        }
    if "dls_excluded" in inn:
        report["shortened_innings_all_rows_dls_excluded"] = int(short["dls_excluded"].sum())
    return report


def check_phase_labels(df: pd.DataFrame) -> dict[str, Any]:
    """Verify that stored labels are a function of (B, L) only and use no later information.

    1. Recomputed labels equal the stored labels.
    2. Labels are unchanged when the last 30 percent of each innings is removed (a later ball
       cannot influence an earlier label).
    3. Labels are unchanged when the order of other innings changes (no cross-innings use).
    """
    reg = regulation(df)
    reg = reg[reg["innings_limit_balls"].notna()]
    recomputed = phase_label(reg["legal_balls_bowled_before"], reg["innings_limit_balls"])
    stored_equal = bool((recomputed.to_numpy() == reg["innings_phase"].to_numpy()).all())
    pos = reg.groupby(["match_id", "innings_number"]).cumcount()
    size = reg.groupby(["match_id", "innings_number"])["match_id"].transform("size")
    prefix = reg[pos < np.floor(size * 0.7)]
    prefix_labels = phase_label(prefix["legal_balls_bowled_before"], prefix["innings_limit_balls"])
    prefix_equal = bool((prefix_labels.to_numpy() == recomputed.loc[prefix.index].to_numpy()).all())
    shuffled = reg.sample(frac=1.0, random_state=0)
    shuffled_labels = phase_label(
        shuffled["legal_balls_bowled_before"], shuffled["innings_limit_balls"]
    )
    order_equal = bool((shuffled_labels.sort_index().to_numpy() == recomputed.to_numpy()).all())
    return {
        "rows_checked": int(len(reg)),
        "stored_labels_equal_recomputed_from_B_and_L": stored_equal,
        "labels_unchanged_when_last_30pct_of_each_innings_removed": prefix_equal,
        "labels_independent_of_row_order_and_other_innings": order_equal,
    }


def revision_timing_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Deliveries whose label could differ if the original limit of 120 had applied when bowled.

    This is an upper bound on timing-sensitive labels: the data has no announcement time.
    """
    reg = regulation(df)
    reg = reg[reg["innings_limit_balls"].notna() & (reg["innings_limit_balls"] != DEFAULT_LIMIT)]
    if reg.empty:
        return {"shortened_deliveries": 0, "deliveries_whose_label_depends_on_revised_limit": 0}
    b = reg["legal_balls_bowled_before"]
    revised = phase_label(b, reg["innings_limit_balls"])
    original = phase_label(b, pd.Series(DEFAULT_LIMIT, index=reg.index))
    return {
        "shortened_deliveries": int(len(reg)),
        "deliveries_whose_label_depends_on_revised_limit": int((revised != original).sum()),
        "announcement_time_in_data": False,
        "handling": "all such innings are excluded from primary scoring (dls_exclude_primary)",
    }


def dls_exclusion_summary(df: pd.DataFrame) -> dict[str, Any]:
    """DLS exclusions are row masks. Counts of excluded rows and primary-chase-sample overlap."""
    reg = regulation(df)
    scope = reg["competition_type"].isin(_SCOPE)
    excluded = reg["dls_exclude_primary"].fillna(False).astype(bool)
    chase_candidate = (
        reg["chase_flag"].fillna(False).astype(bool)
        & reg["regulation_pressure_eligible"].fillna(False).astype(bool)
        & ~reg["format_out_of_scope"].fillna(False).astype(bool)
        & scope
    )
    return {
        "total_rows": int(len(df)),
        "regulation_rows": int(len(reg)),
        "dls_excluded_regulation_rows": int(excluded.sum()),
        "dls_excluded_regulation_innings": int(
            reg[excluded].groupby(["match_id", "innings_number"]).ngroups
        ),
        "dls_excluded_rows_in_scope": int((excluded & scope).sum()),
        "dls_excluded_chase_rows_otherwise_eligible": int((excluded & chase_candidate).sum()),
        "dls_resources_imputed": False,
        "rows_deleted": 0,
    }
