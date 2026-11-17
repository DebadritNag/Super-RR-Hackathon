"""Innings phase labels from legal balls (integer arithmetic only, EXPLORATORY).

Powerplay if B < pp_end, death if B >= death_start, middle otherwise, with
pp_end = (3 * L) // 10 and death_start = ceil(3 * L / 4). For L = 120 these are 36 and 90.
For L < 120 the boundaries fall inside an over, so phase is ball-based, never over-based.
The fractions come from `config/pressure_rules_v1.json` (parameter `phase_fractions`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_FRACTIONS = {"powerplay_num": 3, "powerplay_den": 10, "death_num": 3, "death_den": 4}


def phase_bounds(limit, fractions: dict | None = None):
    """Return (pp_end, death_start) for an int or integer array of limits (in balls)."""
    f = fractions or DEFAULT_FRACTIONS
    arr = np.asarray(limit, dtype="int64")
    pp_end = (f["powerplay_num"] * arr) // f["powerplay_den"]
    death_start = -((-f["death_num"] * arr) // f["death_den"])
    if arr.ndim == 0:
        return int(pp_end), int(death_start)
    return pp_end, death_start


def phase_label(legal_balls_before: pd.Series, limit: pd.Series, fractions: dict | None = None):
    """Phase label per row; NULL where the limit is NULL."""
    ok = limit.notna()
    lim = limit.where(ok, 120).astype("int64")
    pp_end, death_start = phase_bounds(lim.to_numpy(), fractions)
    b = legal_balls_before.to_numpy()
    out = np.where(b < pp_end, "powerplay", np.where(b >= death_start, "death", "middle"))
    return pd.Series(out, index=legal_balls_before.index).where(ok)


def phase_rule(limit: pd.Series) -> pd.Series:
    rule = np.where(limit == 120, "FULL_120", "PROPORTIONAL_DLS")
    return pd.Series(rule, index=limit.index).where(limit.notna())
