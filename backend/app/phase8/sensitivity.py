"""Sensitivity checks for the submitted rankings: time windows and pressure definitions.

The stored Approach A, B and C tables already hold the floor, format, component and ordering
variants. This module adds the checks that need the unit tables: the same statistic recomputed
inside one calendar window (TRAIN 2022-2024, VALIDATION 2025) and the consistency ranking under
every pressure definition. All inputs are unit tables; nothing here reads a rank or a name.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase8.approach_c import consistency_units
from app.phase8.reml import RemlError, fit_reml
from app.phase8.stability import point_ranking

WINDOWS = {"TRAIN": "window_2022_2024", "VALIDATION": "window_2025"}


def window_statistic(units: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Per player: matches and the window statistic.

    ``kind='mean'`` is the precision-weighted mean of the unit residual; ``kind='pos_share'`` is
    the share of units with a positive residual (the consistency statistic of Approach C).
    """
    if kind not in ("mean", "pos_share"):
        raise ValueError("kind must be 'mean' or 'pos_share'")
    g = units.groupby("player_id")
    out = pd.DataFrame({"n_matches": g["match_id"].nunique()})
    if kind == "mean":
        num = (units["prec"] * units["y"]).groupby(units["player_id"]).sum()
        den = units.groupby("player_id")["prec"].sum()
        out["stat"] = num / den
    else:
        out["stat"] = (units["y"] > 0).groupby(units["player_id"]).mean()
    return out


def window_overlap(
    units: pd.DataFrame,
    main_rank: pd.Series,
    kind: str,
    floors: dict[str, int],
    k: int = 10,
) -> list[dict[str, Any]]:
    """Agreement of the submitted order with the same statistic inside each calendar window.

    ``main_rank`` is the submitted rank per player. The window set is the eligible submitted
    players with at least ``floors[period]`` matches in that window (the declared floor in
    2022-2024 and the declared half floor in 2025).
    """
    rows = []
    main_top = set(main_rank[main_rank <= k].index)
    for period, name in WINDOWS.items():
        u = units[(units["period"] == period) & units["player_id"].isin(main_rank.index)]
        if u.empty:
            rows.append({"comparison": name, "n_common": 0, "note": "NOT_ESTIMABLE_NO_UNITS"})
            continue
        ws = window_statistic(u, kind)
        ws = ws[ws["n_matches"] >= floors[period]]
        if len(ws) < 10:
            rows.append(
                {"comparison": name, "n_common": int(len(ws)), "note": "NOT_ESTIMABLE_FEW_PLAYERS"}
            )
            continue
        wr = point_ranking(ws["stat"])
        common = wr.index.intersection(main_rank.index)
        rho = float(wr[common].rank().corr(main_rank[common].rank()))
        win_top = set(wr[wr <= k].index)
        rows.append(
            {
                "comparison": name,
                "n_common": int(len(common)),
                "spearman": rho,
                "top10_overlap": int(len(main_top & win_top)),
                "main_top10_estimable": int(len(main_top & set(ws.index))),
                "note": "",
            }
        )
    return rows


def consistency_rank(units: pd.DataFrame, players: np.ndarray) -> pd.Series:
    """Rank by the REML level of the consistency units (the ordering Approach C reduces to)."""
    from app.phase8.approach_a import centre_by_format

    cu = consistency_units(units[units["player_id"].isin(players)])
    cu, _ = centre_by_format(cu)
    try:
        fit = fit_reml(cu)
    except RemlError:
        return pd.Series(dtype=float)
    ps = fit["players"]
    basis = ps["ybar"] if fit["floor"] else ps["theta"]
    return point_ranking(basis)
