"""Win Probability Added (WPA) attribution (design D12, with one declared change to the split rule).

Delivery WPA ``d = WP_after - WP_before`` is in the batting side's frame. A ball is decomposed into
components and each component is credited as follows (positive credit means good for the player):

* bat component (no extra, or a no-ball): striker ``+d_bat``, bowler ``-d_bat``;
* wide or no-ball penalty: bowler ``-d_ext``; no striker credit (a wide is not a ball faced);
* byes and leg-byes: batting side collectively (``team_only``), no striker and no bowler credit;
* wicket component: the dismissed player gets ``+d_wkt`` (negative for a dismissal); the bowler gets
  ``-d_wkt`` only when the dismissal is bowler-credited (bowled, caught, lbw, stumped, hit wicket).
  Run-outs and other non-credit dismissals give the bowler neither credit nor blame;
* retired, obstructing, timed out, handled ball, extras type other or penalty, metric-flag anomalies
  and balls without a defined ``WP_before`` or ``WP_after`` are excluded and counted, never zeroed.

When a ball has more than one component the realised delta is split by the counterfactual rule:
``delta_c = WP(state with component c only) - WP_before`` and
``d_c = delta_c + (d - sum delta) * |delta_c| / sum |delta|``, so the parts always add up to ``d``.
This replaces the plan's "expected-share" split: the counterfactual deltas use only the ball's own
realised components and the pre-delivery state, so they need no outcome beyond the ball.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BAT, EXT, TEAM, WKT = 0, 1, 2, 3
UNUSUAL_DISMISSALS = ("retire", "obstruct", "obstract", "timed out", "handled", "hit the ball")
EXT_EXCLUDED = ("other", "penalty")
CF_COLS = ("cf_bat", "cf_ext", "cf_team", "cf_wkt")


def _lower(s: pd.Series) -> pd.Series:
    """Lower-cased text; the literal label ``None`` (no extra) becomes missing."""
    t = s.astype("string").str.strip().str.lower()
    return t.mask(t.isin(["none", ""]))


def component_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Boolean component presence per ball (bat, ext, team, wkt)."""
    ex = _lower(df["out_extras_type"])
    wk = df["out_is_wicket"].fillna(False).astype(bool).to_numpy()
    bat = (ex.isna() | (ex == "overstep")).to_numpy()
    ext = ex.isin(["wide", "overstep"]).to_numpy()
    team = ex.isin(["byes", "legbyes"]).to_numpy()
    return pd.DataFrame({"bat": bat, "ext": ext, "team": team, "wkt": wk}, index=df.index)


def exclusion_codes(df: pd.DataFrame) -> pd.Series:
    """Reason a ball is excluded from WPA (empty string when it is attributed)."""
    ex = _lower(df["out_extras_type"])
    dis = _lower(df["out_dismissal_type"]).fillna("")
    wk = df["out_is_wicket"].fillna(False).astype(bool)
    reason = pd.Series("", index=df.index, dtype="object")
    wp_missing = df["wp_before"].isna() | df["wp_after"].isna()
    reason[wp_missing] = "WP_UNAVAILABLE"
    anomaly = ~df["ok_run_target"].astype(bool) | ~df["ok_wicket_target"].astype(bool)
    reason[anomaly] = "METRIC_FLAG_ANOMALY"
    reason[ex.isin(EXT_EXCLUDED).fillna(False).to_numpy()] = "EXTRAS_OTHER_OR_PENALTY"
    unusual = wk & dis.str.contains("|".join(UNUSUAL_DISMISSALS), regex=True)
    reason[unusual.to_numpy()] = "UNUSUAL_EVENT"
    return reason


def attribute(df: pd.DataFrame) -> pd.DataFrame:
    """Attribute every ball. Needs ``wp_before``, ``wp_after``, the ``out_*``/``den_*`` columns,
    ``striker_id``, ``non_striker_id`` and, for multi-component balls, ``cf_bat/ext/team/wkt``.

    Returns one row per input row: ``d``, ``excluded_reason``, ``split_rule``, ``striker_wpa``,
    ``bowler_wpa``, ``dismissed_player_id``, ``dismissed_wpa``, ``team_only_wpa``,
    ``unassigned_wpa``. Credits are NaN (never zero) where a ball gives the role no credit.
    """
    n = len(df)
    flags = component_flags(df)
    present = flags[["bat", "ext", "team", "wkt"]].to_numpy()
    wpb = df["wp_before"].to_numpy(dtype="float64")
    d = df["wp_after"].to_numpy(dtype="float64") - wpb
    reason = exclusion_codes(df).to_numpy(dtype=object)
    ok = reason == ""
    k = present.sum(axis=1)
    alloc = np.zeros((n, 4))
    rule = np.full(n, "", dtype=object)
    single = ok & (k == 1)
    alloc[single] = d[single, None] * present[single]
    rule[single] = "SINGLE"
    multi = ok & (k > 1)
    if multi.any():
        cf = np.column_stack(
            [df[c].to_numpy(dtype="float64") if c in df else np.full(n, np.nan) for c in CF_COLS]
        )
        delta = np.where(present, cf - wpb[:, None], np.nan)
        have = ~np.isnan(np.where(present, delta, 0.0)).any(axis=1)
        cfm = multi & have
        dz = np.where(present, delta, 0.0)
        s = dz.sum(axis=1)
        a = np.abs(dz).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            share = np.where(a[:, None] > 0, np.abs(dz) / a[:, None], np.nan)
        part = dz + (d - s)[:, None] * share
        use = cfm & (a > 0)
        alloc[use] = np.where(present[use], part[use], 0.0)
        rule[use] = "COUNTERFACTUAL"
        eq = multi & ~use
        alloc[eq] = d[eq, None] * present[eq] / k[eq, None]
        # no counterfactual information: either every component delta is exactly zero (WP is flat
        # across the states, so the split cannot matter when d is zero) or a counterfactual is
        # missing; the first case is labelled separately so the second stays visible
        rule[eq] = np.where(np.abs(d[eq]) < 1e-12, "ZERO_DELTA", "EQUAL_FALLBACK")
    credited = (df["den_bowler_credited_wicket"].fillna(0).to_numpy() == 1) & present[:, WKT]
    striker = alloc[:, BAT].copy()
    bowler = -(alloc[:, BAT] + alloc[:, EXT] + np.where(credited, alloc[:, WKT], 0.0))
    team = alloc[:, TEAM].copy()
    dismissed = df["out_dismissed_player_id"].to_numpy(dtype="float64")
    wk_alloc = alloc[:, WKT]
    unassigned = np.where(present[:, WKT] & np.isnan(dismissed), wk_alloc, np.nan)
    on_strike = dismissed == df["striker_id"].to_numpy(dtype="float64")
    striker = striker + np.where(on_strike & present[:, WKT], wk_alloc, 0.0)
    # roles that receive no credit on a ball are NaN, not zero
    striker = np.where(ok & (present[:, BAT] | (on_strike & present[:, WKT])), striker, np.nan)
    bowler = np.where(ok & (present[:, BAT] | present[:, EXT] | credited), bowler, np.nan)
    team = np.where(ok & present[:, TEAM], team, np.nan)
    dis_w = np.where(ok & present[:, WKT] & ~np.isnan(dismissed), wk_alloc, np.nan)
    return pd.DataFrame(
        {
            "d": np.where(ok, d, np.nan), "excluded_reason": reason, "split_rule": rule,
            "striker_wpa": striker, "bowler_wpa": bowler, "team_only_wpa": team,
            "dismissed_player_id": np.where(np.isnan(dis_w), np.nan, dismissed),
            "dismissed_wpa": dis_w,
            "dismissed_non_striker": np.where(
                ~np.isnan(dis_w) & ~on_strike & present[:, WKT], True, False
            ),
            "unassigned_wpa": np.where(ok, unassigned, np.nan),
        },
        index=df.index,
    )  # fmt: skip
