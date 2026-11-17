"""Season-by-season robustness checks, labelled ROBUSTNESS_NOT_VALIDATION.

These are additional consistency checks inside the pre-test window. They are not independent
validation: the same rows feed the baseline, thresholds and every season, the seasons are not
exchangeable hold-outs, and TEST was opened once in Phase 4 so it is not pristine. For each format x
role primary-stream cell of one definition:

* ``within_season``: odd/even split-half reliability inside one calendar season.
* ``adjacent_seasons``: Spearman correlation of individual mean residuals between season s and s+1.
* ``leave_one_season_out``: Spearman correlation between season s and all other seasons, and the
  odd/even reliability of the other seasons pooled (against the full pre-test value).

A unit with too few individuals is ``NOT_ESTIMABLE``. No player id appears in any output.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en
from app.phase5 import pipeline as pl
from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6 import split_half as sp
from app.phase6.lockguard import assert_no_test_rows

LABEL = "ROBUSTNESS_NOT_VALIDATION"
SEASONS = (2022, 2023, 2024, 2025)
MIN_BALLS_PER_SIDE = 12
MIN_PLAYERS = 10


def season_mask(cd: rb.CellData, year: int) -> np.ndarray:
    return sp.window_mask(cd, start=f"{year}-01-01", end=f"{year}-12-31")


def player_means(cd: rb.CellData, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mean residual and ball count per individual over the matches in ``mask``."""
    n = cd.N[:, mask].sum(1)
    s = cd.S[:, mask].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, s / np.where(n > 0, n, 1.0), np.nan), n


def rank_corr(
    cd: rb.CellData, a: np.ndarray, b: np.ndarray, min_balls: int = MIN_BALLS_PER_SIDE
) -> dict[str, Any]:
    """Spearman correlation of mean residuals between two match sets (disjoint)."""
    ma, na = player_means(cd, a)
    mb, nb = player_means(cd, b)
    ok = (na >= min_balls) & (nb >= min_balls)
    n = int(ok.sum())
    if n < MIN_PLAYERS:
        return {
            "status": NOT_ESTIMABLE,
            "players": n,
            "spearman": None,
            "ci_lo": None,
            "ci_hi": None,
        }
    rho = float(pd.Series(ma[ok]).corr(pd.Series(mb[ok]), method="spearman"))
    lo = hi = None
    if np.isfinite(rho) and n > 3 and abs(rho) < 1:
        z, se = np.arctanh(rho), 1.0 / np.sqrt(n - 3)
        lo, hi = float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))
    return {"status": ESTIMATED, "players": n, "spearman": rho, "ci_lo": lo, "ci_hi": hi}


def _split(
    cd: rb.CellData, mask: np.ndarray, seed: int, n_boot: int, min_half: int
) -> dict[str, Any]:
    r, ci = sp.split_half_unit(cd, None, mask, "odd_even", min_half, seed, 1, n_boot, MIN_PLAYERS)
    out = {"status": r["status"], "players": r["players"], "matches": r["matches"],
           "sb": r.get("sb_pearson"), "sb_lo": None, "sb_hi": None}  # fmt: skip
    for c in ci:
        if c["ci_method"] == "player_bootstrap":
            out["sb_lo"], out["sb_hi"] = c["lo"], c["hi"]
    return out


def run(
    study: pl.Study, defn: str, cfg: dict[str, Any], seasons: tuple[int, ...] = SEASONS
) -> pd.DataFrame:
    """Rows for every primary-stream cell and season; every row is ``ROBUSTNESS_NOT_VALIDATION``."""
    sh_cfg = cfg["split_half"]
    n_boot, min_half = int(sh_cfg["bootstrap_draws"]), int(sh_cfg["min_balls_per_half"])
    rows: list[dict[str, Any]] = []
    for (comp, role), cell in study.primary_cells(defn).items():
        assert_no_test_rows(cell.rows)
        cd = rb.from_cell(cell)
        stream = en.PRIMARY[role][0]
        base = {"label": LABEL, "definition": defn, "format": comp, "role": role, "stream": stream}
        all_m = np.ones(cd.N.shape[1], dtype=bool)
        full = _split(
            cd, all_m, sp.unit_seed(study.seed, "season", comp, role, "full"), n_boot, min_half
        )
        masks = {y: season_mask(cd, y) for y in seasons}
        for y in seasons:
            m = masks[y]
            rest = all_m & ~m
            tag = sp.unit_seed(study.seed, "season", comp, role, y)
            w = _split(cd, m, tag, n_boot, min_half)
            rows.append({**base, "check": "within_season", "season": y, "other_season": None,
                         "matches": w["matches"], "players": w["players"], "statistic": "sb_odd_even",
                         "value": w["sb"], "ci_lo": w["sb_lo"], "ci_hi": w["sb_hi"],
                         "reference_value": full["sb"], "status": w["status"]})  # fmt: skip
            loo = rank_corr(cd, m, rest)
            rows.append({**base, "check": "leave_one_season_out_rank", "season": y,
                         "other_season": "all_other", "matches": int(m.sum()),
                         "players": loo["players"], "statistic": "spearman_mean_residual",
                         "value": loo["spearman"], "ci_lo": loo["ci_lo"], "ci_hi": loo["ci_hi"],
                         "reference_value": None, "status": loo["status"]})  # fmt: skip
            r2 = _split(cd, rest, tag + 1, n_boot, min_half)
            rows.append({**base, "check": "leave_one_season_out_reliability", "season": y,
                         "other_season": "all_other", "matches": r2["matches"],
                         "players": r2["players"], "statistic": "sb_odd_even",
                         "value": r2["sb"], "ci_lo": r2["sb_lo"], "ci_hi": r2["sb_hi"],
                         "reference_value": full["sb"], "status": r2["status"]})  # fmt: skip
        for y0, y1 in zip(seasons[:-1], seasons[1:], strict=True):
            ac = rank_corr(cd, masks[y0], masks[y1])
            rows.append({**base, "check": "adjacent_seasons", "season": y0, "other_season": y1,
                         "matches": int(masks[y0].sum() + masks[y1].sum()), "players": ac["players"],
                         "statistic": "spearman_mean_residual", "value": ac["spearman"],
                         "ci_lo": ac["ci_lo"], "ci_hi": ac["ci_hi"], "reference_value": None,
                         "status": ac["status"]})  # fmt: skip
    df = pd.DataFrame(rows)
    assert_no_test_rows(df)
    return df
