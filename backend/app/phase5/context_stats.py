"""Stored delivery-level evidence rows for the dynamic ranking engine (analytics layer).

One row per (player, match, competition, role, stream, phase, situation) of the carried
definition's pressure deliveries, holding additive sufficient statistics: ``n`` (balls), ``s`` (sum
of residual), ``s2`` (sum of squared residual) and ``e`` (sum of the baseline expectation). Because
they are additive, any context (phase and/or situation) is a plain sum over rows; no model is
trained per filter combination. Only TRAIN and VALIDATION rows exist here (TEST rows are dropped
before the frame is built). Nothing in this module imports a Cricsheet loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en
from app.phase4 import shrink as sh

STAT_COLUMNS = [
    "player_id",
    "match_id",
    "comp",
    "role",
    "stream",
    "period",
    "match_date",
    "phase",
    "situation",
    "n",
    "s",
    "s2",
    "e",
]
PHASES = ("powerplay", "middle", "death")
SITUATIONS = ("chase", "first_innings")
ALL = "ALL"


class ContextStatsError(RuntimeError):
    """The stored context rows violate an invariant (TEST rows, unknown labels)."""


def situation_labels(innings_number: np.ndarray) -> np.ndarray:
    """``chase`` for innings 2, ``first_innings`` for innings 1; anything else is refused."""
    inn = np.asarray(innings_number)
    bad = ~np.isin(inn, (1, 2))
    if bad.any():
        raise ContextStatsError(f"{int(bad.sum())} pressure rows outside innings 1-2")
    return np.where(inn == 2, "chase", "first_innings")


def build_context_stats(study: Any, defn: str | None = None) -> pd.DataFrame:
    """Aggregate the carried definition's pressure rows to (player, match, phase, situation).

    ``study`` is a ``phase5.pipeline.Study`` (pre-test frame with TRAIN-fitted B0 baseline). The
    primary stream per role is used (batter ``runs``, bowler ``charged``).
    """
    defn = defn or study.frozen["definition"]["id"]
    parts = []
    for role in ("batter", "bowler"):
        stream = en.PRIMARY[role][0]
        rows = study.pressure_rows(defn, role, stream)
        src = rows["src"].to_numpy()
        phase = study.d["innings_phase"].reindex(src).to_numpy()
        if pd.isna(phase).any():
            raise ContextStatsError("pressure rows without an innings phase")
        situ = situation_labels(study.d["innings_number"].reindex(src).to_numpy())
        t = pd.DataFrame(
            {
                "player_id": rows["player_id"].to_numpy(),
                "match_id": rows["match_id"].to_numpy(),
                "comp": rows["comp"].to_numpy(),
                "period": rows["period"].to_numpy(),
                "match_date": pd.to_datetime(rows["date"]).dt.strftime("%Y-%m-%d").to_numpy(),
                "phase": phase,
                "situation": situ,
                "r": rows["resid"].to_numpy(dtype=float),
                "e": rows["expected"].to_numpy(dtype=float),
            }
        )
        t["r2"] = t["r"] ** 2
        t["n"] = 1.0
        g = t.groupby(
            ["player_id", "match_id", "comp", "period", "match_date", "phase", "situation"],
            as_index=False,
            sort=True,
        ).agg(n=("n", "sum"), s=("r", "sum"), s2=("r2", "sum"), e=("e", "sum"))
        g["role"] = role
        g["stream"] = stream
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)[STAT_COLUMNS]
    check_stats(out)
    return out.sort_values(["role", "comp", "player_id", "match_date", "match_id", "phase"],
                           kind="mergesort").reset_index(drop=True)  # fmt: skip


def check_stats(stats: pd.DataFrame) -> None:
    """Refuse TEST rows and unknown labels."""
    missing = [c for c in STAT_COLUMNS if c not in stats.columns]
    if missing:
        raise ContextStatsError(f"context stats columns missing: {missing}")
    if (stats["period"] == "TEST").any() or not stats["period"].isin(["TRAIN", "VALIDATION"]).all():
        raise ContextStatsError("context stats may only hold TRAIN and VALIDATION rows")
    if not stats["phase"].isin(PHASES).all() or not stats["situation"].isin(SITUATIONS).all():
        raise ContextStatsError("unknown phase or situation label in context stats")


def select(stats: pd.DataFrame, comp: str, role: str, phase: str, situation: str) -> pd.DataFrame:
    """Rows of one context. ``ALL`` for phase or situation sums over that label."""
    m = (stats["comp"] == comp) & (stats["role"] == role)
    if phase != ALL:
        m &= stats["phase"] == phase
    if situation != ALL:
        m &= stats["situation"] == situation
    return stats[m]


def player_match_stats(sub: pd.DataFrame) -> pd.DataFrame:
    """Per (player, match) ``n, s, s2`` of a context, the input of ``shrink.player_table``."""
    return sub.groupby(["player_id", "match_id"], as_index=False, sort=True).agg(
        n=("n", "sum"), s=("s", "sum"), s2=("s2", "sum")
    )


@dataclass
class ContextCell(en.Cell):
    """``engine.Cell`` built from stored rows. Phase 4 eligibility and shrinkage code runs on it
    unchanged; the TRAIN player table is rebuilt from match statistics (there are no ball rows)."""

    def train_pt(self) -> pd.DataFrame:
        train_matches = set(self.matches[self.match_period == "TRAIN"].tolist())
        return sh.player_table(self.ms[self.ms["match_id"].isin(train_matches)])


def cell_from_stats(sub: pd.DataFrame, comp: str, role: str, stream: str) -> ContextCell | None:
    """Player x match matrices of a context from stored rows; None when the context is empty."""
    if sub.empty:
        return None
    ms = player_match_stats(sub)
    md = sub.groupby("match_id").agg(date=("match_date", "first"), period=("period", "first"))
    md = md.reset_index().sort_values(["date", "match_id"], kind="mergesort")
    matches = md["match_id"].to_numpy()
    players = np.sort(ms["player_id"].unique())
    pi = pd.Index(players).get_indexer(ms["player_id"])
    mi = pd.Index(matches).get_indexer(ms["match_id"])
    N = np.zeros((len(players), len(matches)))
    S = np.zeros_like(N)
    np.add.at(N, (pi, mi), ms["n"].to_numpy(float))
    np.add.at(S, (pi, mi), ms["s"].to_numpy(float))
    return ContextCell(comp, role, stream, ms, ms, players, matches, md["period"].to_numpy(), N, S)


def expected_sums(sub: pd.DataFrame) -> pd.DataFrame:
    """Per player: sum of baseline expectation ``e`` and ball count ``n`` of a context."""
    return sub.groupby("player_id").agg(e=("e", "sum"), n=("n", "sum"))


def global_match_weights(
    stats: pd.DataFrame, n_boot: int, seed: int
) -> tuple[pd.Index, np.ndarray]:
    """One seeded multinomial match-resample matrix over every match that holds a stored row.

    Derived from the stored rows alone so the build script and the API produce identical draws.
    """
    return en.global_weights(stats["match_id"].to_numpy(), n_boot, seed)
