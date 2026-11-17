"""Pure cricket arithmetic for the pre-delivery state (EXPLORATORY, no I/O).

Extras semantics are the verified Phase 2 / 2.5 ones: `extras_type` is the literal string 'None'
when there is no extra, `wide`, `Overstep` and `other` are not legal balls, `Penalty` adds no legal
ball (RULE_EXTRAS_PENALTY), byes and legbyes are legal. Unknown categories are never mapped to
zero: they stay visible through `extras_category_known`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

KNOWN_EXTRAS = ("None", "wide", "Overstep", "other", "byes", "legbyes", "Penalty")


def normalise_extras_type(s: pd.Series) -> pd.Series:
    """NULL becomes the string 'None' only for the type label, never for the run values."""
    return s.where(s.notna(), "None").astype(str)


def extras_category_known(extras_type: pd.Series) -> pd.Series:
    return extras_type.isin(KNOWN_EXTRAS)


def legal_increment(is_legal_ball: pd.Series, extras_type: pd.Series) -> pd.Series:
    """1 if the DB flags the ball legal and it is not the Penalty row, else 0 (denominator flag)."""
    return (is_legal_ball.fillna(False).astype(bool) & (extras_type != "Penalty")).astype("int64")


def counts_as_ball_faced(
    striker_id: pd.Series, extras_type: pd.Series, innings_number: pd.Series
) -> pd.Series:
    """Phase 2.5 BATTER_SQL definition: striker present, not wide/Penalty, innings 1 and 2."""
    return (
        striker_id.notna() & ~extras_type.isin(("wide", "Penalty")) & innings_number.isin((1, 2))
    ).astype("int64")


def exclusive_cumsum(values: pd.Series, groups: list[pd.Series] | pd.Series) -> pd.Series:
    """Sum of strictly earlier rows within each group (row order is the series order)."""
    return values.groupby(groups, sort=False).cumsum() - values


def safe_rate_per_over(runs: pd.Series, balls: pd.Series) -> pd.Series:
    """runs / balls * 6; NULL (NaN), never 0, when balls == 0."""
    out = runs.astype("float64") / balls.where(balls > 0).astype("float64") * 6.0
    return out


def required_run_rate(runs_required: pd.Series, balls_remaining: pd.Series) -> pd.Series:
    """RRR; NULL when no balls remain, no target, or nothing is required (Req <= 0)."""
    ok = (
        balls_remaining.notna()
        & (balls_remaining > 0)
        & runs_required.notna()
        & (runs_required > 0)
    )
    rrr = runs_required.astype("float64") / balls_remaining.where(ok).astype("float64") * 6.0
    return rrr.where(ok)


def resource_ratio(balls_remaining: pd.Series, wickets_remaining: pd.Series, limit: pd.Series):
    """Brem * Wrem / (L * 10): a simple proxy, NOT a DLS resource percentage."""
    return balls_remaining.astype("float64") * wickets_remaining / (limit.astype("float64") * 10.0)


def projected_surplus(crr: pd.Series, rrr: pd.Series, balls_remaining: pd.Series) -> pd.Series:
    """(CRR - RRR) * Brem / 6 for chases; NULL when either rate is NULL."""
    return (crr - rrr) * balls_remaining.astype("float64") / 6.0


def over_index(legal_balls_before: pd.Series) -> pd.Series:
    """1-based legal over index."""
    return legal_balls_before // 6 + 1


def ball_in_over(legal_balls_before: pd.Series) -> pd.Series:
    """1 to 6, by LEGAL balls."""
    return legal_balls_before % 6 + 1


def is_multiple_of(values: pd.Series, k: int) -> bool:
    v = values.dropna()
    return bool(len(v) == 0 or np.all(np.mod(v.to_numpy(), k) == 0))
