"""Player profile data: descriptive stats, experimental pressure result, radar data, strengths.

All numbers come from stored tables. Radar axes are DATA only: each axis has a formula, a
direction and a reference population, and the normalised value is a percentile (0 to 100) within
that population. Where the sample or the reference population is too small the result carries an
explicit ``INSUFFICIENT_DATA`` label with the reason. Strength sentences are templates over the
actual values, never free text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.phase4.constants import STATUS
from app.phase4.uncapped import (
    ClassificationBasis,
    effective_classification,
    verified_uncapped_mask,
)
from app.phase4.views import DISCLAIMER, SCORE_UNIT, Tables, ranking_frame

INSUFFICIENT = "INSUFFICIENT_DATA"
OK = "OK"
MIN_BALLS = {"batter": 60, "bowler": 60}  # balls faced / legal balls bowled for a radar axis
MIN_UNCAPPED_REFERENCE = 5  # verified-uncapped players needed for an uncapped percentile
STRENGTH_PERCENTILE = 75.0
MIN_STRENGTH_REFERENCE = 10


@dataclass(frozen=True)
class Axis:
    key: str
    label: str
    formula: str
    higher_is_better: bool
    unit: str


AXES: dict[str, tuple[Axis, ...]] = {
    "batter": (
        Axis(
            "pressure_score",
            "Pressure residual",
            "shrunk pressure residual (runs per ball above baseline)",
            True,
            "runs/ball",
        ),
        Axis(
            "strike_rate", "Strike rate", "100 * bat_runs / bat_balls", True, "runs per 100 balls"
        ),
        Axis(
            "boundary_rate",
            "Boundary rate",
            "(bat_fours + bat_sixes) / bat_balls",
            True,
            "share of balls",
        ),
        Axis(
            "balls_per_dismissal",
            "Balls per dismissal",
            "bat_balls / bat_dismissals (undefined with 0 dismissals)",
            True,
            "balls",
        ),
    ),
    "bowler": (
        Axis(
            "pressure_score",
            "Pressure residual",
            "-(shrunk pressure residual) (runs per ball saved)",
            True,
            "runs/ball",
        ),
        Axis("economy", "Economy", "6 * bowl_runs / bowl_balls", False, "runs per over"),
        Axis(
            "balls_per_wicket",
            "Balls per wicket",
            "bowl_balls / bowl_wickets (undefined with 0 wickets)",
            False,
            "balls",
        ),
        Axis(
            "dot_ball_rate",
            "Dot-ball rate",
            "bowl_dots / bowl_balls (legal balls)",
            True,
            "share of balls",
        ),
    ),
}


def axis_value(row: pd.Series, side: str, key: str) -> float | None:
    """Descriptive axis value from one stats row, or None when undefined."""
    if side == "batter":
        b = float(row["bat_balls"])
        if b <= 0:
            return None
        if key == "strike_rate":
            return 100.0 * float(row["bat_runs"]) / b
        if key == "boundary_rate":
            return (float(row["bat_fours"]) + float(row["bat_sixes"])) / b
        if key == "balls_per_dismissal":
            return b / float(row["bat_dismissals"]) if row["bat_dismissals"] > 0 else None
    else:
        b = float(row["bowl_balls"])
        if b <= 0:
            return None
        if key == "economy":
            return 6.0 * float(row["bowl_runs"]) / b
        if key == "balls_per_wicket":
            return b / float(row["bowl_wickets"]) if row["bowl_wickets"] > 0 else None
        if key == "dot_ball_rate":
            return float(row["bowl_dots"]) / b
    return None


def sample_balls(row: pd.Series, side: str) -> int:
    return int(row["bat_balls"] if side == "batter" else row["bowl_balls"])


def percentile_rank(value: float, ref: np.ndarray, higher_is_better: bool) -> float:
    """Share of the reference population this value beats (ties count half), 0 to 100."""
    if len(ref) == 0:
        raise ValueError("empty reference population")
    worse = (ref < value).sum() if higher_is_better else (ref > value).sum()
    equal = (ref == value).sum()
    return float(100.0 * (worse + 0.5 * equal) / len(ref))


def reference_values(
    stats: pd.DataFrame, side: str, fmt: str, key: str, ids: set[int] | None = None
) -> pd.Series:
    """Axis values of every player with a sufficient sample in (side, format)."""
    if fmt == "COMBINED_w70_30":
        d = stats.groupby("player_id", as_index=False).sum(numeric_only=True)
    else:
        d = stats[stats["format"] == fmt]
    col = "bat_balls" if side == "batter" else "bowl_balls"
    d = d[d[col] >= MIN_BALLS[side]]
    if ids is not None:
        d = d[d["player_id"].isin(ids)]
    vals = {int(r["player_id"]): axis_value(r, side, key) for _, r in d.iterrows()}
    return pd.Series({k: v for k, v in vals.items() if v is not None}, dtype=float)


def pressure_reference(t: Tables, side: str, fmt: str, basis: ClassificationBasis) -> pd.DataFrame:
    return ranking_frame(t, side, fmt, basis)


def _stats_row(stats: pd.DataFrame, pid: int, fmt: str) -> pd.Series | None:
    if fmt == "COMBINED_w70_30":
        d = stats[stats["player_id"] == pid]
        return None if d.empty else d.sum(numeric_only=True)
    d = stats[(stats["player_id"] == pid) & (stats["format"] == fmt)]
    return None if d.empty else d.iloc[0]


def _axis_entry(
    ax: Axis,
    value: float | None,
    ref_all: pd.Series,
    ref_unc: pd.Series,
    sample: int,
    side: str,
    insufficient_reason: str | None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "axis": ax.key,
        "label": ax.label,
        "formula": ax.formula,
        "unit": ax.unit,
        "higher_is_better": ax.higher_is_better,
        "value": value,
        "reference_overall_n": int(len(ref_all)),
        "reference_uncapped_n": int(len(ref_unc)),
        "percentile_overall": None,
        "percentile_uncapped": None,
        "label_overall": OK,
        "label_uncapped": OK,
        "reason_overall": None,
        "reason_uncapped": None,
    }
    if insufficient_reason is not None or value is None:
        reason = insufficient_reason or "axis is undefined for this player (zero denominator)"
        entry.update(label_overall=INSUFFICIENT, label_uncapped=INSUFFICIENT)
        entry.update(reason_overall=reason, reason_uncapped=reason)
        return entry
    if len(ref_all) < 2:
        entry.update(
            label_overall=INSUFFICIENT, reason_overall="overall reference population is too small"
        )
    else:
        entry["percentile_overall"] = percentile_rank(
            value, ref_all.to_numpy(), ax.higher_is_better
        )
    if len(ref_unc) < MIN_UNCAPPED_REFERENCE:
        entry.update(
            label_uncapped=INSUFFICIENT,
            reason_uncapped=f"only {len(ref_unc)} verified-uncapped players with a sufficient "
            f"sample; at least {MIN_UNCAPPED_REFERENCE} are needed",
        )
    else:
        entry["percentile_uncapped"] = percentile_rank(
            value, ref_unc.to_numpy(), ax.higher_is_better
        )
    return entry


def build_side_profile(
    t: Tables, pid: int, side: str, fmt: str, basis: ClassificationBasis
) -> dict[str, Any]:
    cls = effective_classification(t.classification, basis)
    unc_ids = {int(p) for p in cls.loc[verified_uncapped_mask(cls), "player_id"]}
    srow = _stats_row(t.stats, pid, fmt)
    sample = sample_balls(srow, side) if srow is not None else 0
    unit = "balls faced" if side == "batter" else "legal balls bowled"
    axes: list[dict[str, Any]] = []
    rf = pressure_reference(t, side, fmt, basis)
    me = rf[rf["player_id"] == pid]
    elig_pool = rf[rf["eligible"]]
    pressure: dict[str, Any]
    if me.empty or not bool(me["eligible"].iloc[0]):
        status = None if me.empty else str(me["eligibility_status"].iloc[0])
        pressure = {
            "label": INSUFFICIENT,
            "reason": "not eligible for experimental pressure scoring in this format"
            + (f" ({status})" if status else " (no pressure record)"),
        }
    else:
        r = me.iloc[0]
        pressure = {
            "label": OK,
            "reason": None,
            "score": float(r["score"]),
            "score_unit": SCORE_UNIT[side],
            "interval_low": float(r["interval_low"]),
            "interval_high": float(r["interval_high"]),
            "rank": int(r["rank"]),
            "pool_size": int(len(elig_pool)),
            "pressure_opportunities": int(r["pressure_opportunities"]),
            "distinct_matches": int(r["distinct_matches"]),
            "effective_sample_size": float(r["effective_sample_size"]),
            "eligibility_status": str(r["eligibility_status"]),
        }
    for ax in AXES[side]:
        if ax.key == "pressure_score":
            ref_all = elig_pool.set_index("player_id")["score"].astype(float)
            ref_unc = ref_all[ref_all.index.isin(unc_ids)]
            val = pressure.get("score") if pressure["label"] == OK else None
            reason = pressure["reason"] if pressure["label"] != OK else None
            axes.append(_axis_entry(ax, val, ref_all, ref_unc, sample, side, reason))
            continue
        ref_all = reference_values(t.stats, side, fmt, ax.key)
        ref_unc = ref_all[ref_all.index.isin(unc_ids)]
        reason = None
        val = None
        if srow is not None:
            val = axis_value(srow, side, ax.key)
        if srow is None or sample < MIN_BALLS[side]:
            reason = f"{sample} {unit}; at least {MIN_BALLS[side]} are required"
        axes.append(
            _axis_entry(ax, val if reason is None else None, ref_all, ref_unc, sample, side, reason)
        )
    strengths = [
        {
            "axis": a["axis"],
            "percentile_overall": a["percentile_overall"],
            "evidence": f"{a['label']} {a['value']:.3f} {a['unit']} is at the "
            f"{a['percentile_overall']:.0f}th percentile of {a['reference_overall_n']} "
            f"{fmt} {side}s with at least {MIN_BALLS[side]} {unit} (value from the stored tables)",
        }
        for a in axes
        if a["percentile_overall"] is not None
        and a["percentile_overall"] >= STRENGTH_PERCENTILE
        and a["reference_overall_n"] >= MIN_STRENGTH_REFERENCE
    ]
    raw = {}
    if srow is not None:
        cols = (
            ("bat_balls", "bat_runs", "bat_dismissals", "bat_fours", "bat_sixes")
            if side == "batter"
            else ("bowl_balls", "bowl_runs", "bowl_wickets", "bowl_dots")
        )
        raw = {c: int(srow[c]) for c in cols}
        raw["matches_played"] = int(srow["matches_played"])
    return {
        "side": side,
        "format": fmt,
        "sample_size": {"unit": unit, "value": sample, "minimum_for_axes": MIN_BALLS[side]},
        "descriptive": raw,
        "pressure": pressure,
        "radar": {
            "axes": axes,
            "normalisation": "percentile (0 to 100) within the reference population; the player "
            "is included in his own reference",
            "reference_overall": f"all {fmt} players with at least {MIN_BALLS[side]} {unit} "
            "(pressure axis: all eligible experimental players)",
            "reference_uncapped": f"verified-uncapped subset of the overall reference; needs at "
            f"least {MIN_UNCAPPED_REFERENCE} players",
        },
        "strengths": strengths,
        "ranking_status": {
            "rank": pressure.get("rank"),
            "pool_size": pressure.get("pool_size"),
            "status": STATUS,
            "official_ranking": False,
        },
    }


def build_profile(
    t: Tables,
    pid: int,
    basis: ClassificationBasis = ClassificationBasis.INCLUDE_DERIVED_CAPPED,
    fmt: str | None = None,
) -> dict[str, Any] | None:
    """Full profile, or None for an unknown player_id. One block per (side, format) with data."""
    cls = effective_classification(t.classification, basis)
    row = cls[cls["player_id"] == pid]
    if row.empty:
        return None
    c = row.iloc[0]
    formats = [fmt] if fmt else ["IPL", "T20I", "COMBINED_w70_30"]
    blocks = []
    for f in formats:
        srow = _stats_row(t.stats, pid, f)
        for side in ("batter", "bowler"):
            has_stats = srow is not None and sample_balls(srow, side) > 0
            has_score = (
                not ranking_frame(t, side, f, basis, include_ineligible=True)
                .query("player_id == @pid")
                .empty
            )
            if has_stats or has_score:
                blocks.append(build_side_profile(t, pid, side, f, basis))
    return {
        "player": {
            "player_id": int(pid),
            "name": str(c["player_name"]),
            "nationality": str(c["eff_nationality"]),
            "nationality_verification": str(c["eff_nationality_verification"]),
            "international_status": str(c["eff_status"]),
            "international_status_verification": str(c["eff_status_verification"]),
            "squad_role": None if pd.isna(c["squad_role"]) else str(c["squad_role"]),
            "conflict_flag": bool(c["conflict_flag"]),
        },
        "blocks": blocks,
        "insufficient_data": None
        if blocks
        else {
            "label": INSUFFICIENT,
            "reason": "no IPL or T20I deliveries or pressure records in the data window",
        },
        "status": STATUS,
        "official_ranking": False,
        "disclaimer": DISCLAIMER,
    }
