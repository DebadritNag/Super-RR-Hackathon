"""Experimental ranking, directory and selection-pool views over the stored Phase 4 tables.

Every view is read-only over frames loaded from the analytical store. Scores are the carried
definition's primary stream (batter ``runs``, bowler ``charged``) in the PRE_TEST window. Bowler
scores are negated so that higher is always better. Nothing here is an official ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.phase4.constants import STATUS
from app.phase4.selection import assign_group
from app.phase4.uncapped import ClassificationBasis, effective_classification

DISCLAIMER = (
    "EXPERIMENTAL_NOT_VALIDATED: exploratory pressure estimates for methodology review. "
    "Not an official ranking and not a validated measure."
)
PRIMARY_STREAM = {"batter": "runs", "bowler": "charged"}
FORMATS = ("IPL", "T20I", "COMBINED_w70_30")
SIDES = ("batter", "bowler")
SCORE_UNIT = {
    "batter": "runs per ball above the calibrated baseline (shrunk)",
    "bowler": "runs per ball saved against the calibrated baseline (shrunk, sign flipped)",
}


@dataclass
class Tables:
    classification: pd.DataFrame
    scores: pd.DataFrame
    stats: pd.DataFrame
    ranking_dist: pd.DataFrame
    coverage: pd.DataFrame
    unresolved: pd.DataFrame
    meta: dict = field(default_factory=dict)


def is_eligible(status: pd.Series) -> pd.Series:
    return status.astype(str).str.startswith("ELIGIBLE")


def matches_by_format(stats: pd.DataFrame) -> pd.DataFrame:
    """Wide matches-played table: matches_IPL, matches_T20I, matches_COMBINED_w70_30."""
    w = stats.pivot_table(
        index="player_id", columns="format", values="matches_played", aggfunc="sum"
    )
    w = w.reindex(columns=["IPL", "T20I"]).fillna(0)
    w["COMBINED_w70_30"] = w["IPL"] + w["T20I"]
    return w.rename(columns=lambda c: f"matches_{c}").reset_index()


def _oriented(df: pd.DataFrame, side: str) -> pd.DataFrame:
    out = df.copy()
    if side == "bowler":
        lo, hi = -out["interval_high"], -out["interval_low"]
        out["interval_low"], out["interval_high"] = lo, hi
        out["score"] = -out["shrunk_estimate"]
    else:
        out["score"] = out["shrunk_estimate"]
    return out


def ranking_frame(
    t: Tables,
    side: str,
    fmt: str,
    basis: ClassificationBasis = ClassificationBasis.INCLUDE_DERIVED_CAPPED,
    include_ineligible: bool = False,
) -> pd.DataFrame:
    """Experimental ranking rows for one side and format with classification columns."""
    if side not in SIDES or fmt not in FORMATS:
        raise ValueError(f"side must be one of {SIDES} and format one of {FORMATS}")
    sc = t.scores
    sc = sc[(sc["role"] == side) & (sc["format"] == fmt) & (sc["stream"] == PRIMARY_STREAM[side])]
    sc = _oriented(sc, side)
    sc = sc.assign(eligible=is_eligible(sc["eligibility_status"]))
    elig = sc[sc["eligible"]]
    mu, sd = (
        float(elig["score"].mean()) if len(elig) else 0.0,
        (float(elig["score"].std(ddof=1)) if len(elig) > 1 else 0.0),
    )
    sc["standardised_score"] = (sc["score"] - mu) / sd if sd > 0 else sc["score"] - mu
    order = sc[sc["eligible"]].sort_values(["score", "player_id"], ascending=[False, True])
    ranks = pd.Series(np.arange(1, len(order) + 1), index=order.index)
    sc["rank"] = ranks.reindex(sc.index)
    if not include_ineligible:
        sc = sc[sc["eligible"]]
    cls = effective_classification(t.classification, basis)
    out = sc.merge(cls, on="player_id", how="left")
    out = out.merge(matches_by_format(t.stats), on="player_id", how="left")
    out["matches"] = out[f"matches_{fmt}"].fillna(0).astype(int)
    rd = t.ranking_dist
    if len(rd) and fmt in ("IPL", "T20I"):
        r = rd[(rd["scope"] == fmt) & (rd["role"] == side)][
            ["player_id", "top10_inclusion_prob", "rank_lo", "rank_hi"]
        ]
        out = out.merge(r, on="player_id", how="left")
    else:
        out["top10_inclusion_prob"] = np.nan
        out["rank_lo"] = np.nan
        out["rank_hi"] = np.nan
    out["side"] = side
    out["format"] = fmt
    out["group"] = [
        assign_group(n, s) for n, s in zip(out["eff_nationality"], out["eff_status"], strict=True)
    ]
    out["experimental_status"] = STATUS
    out["official_ranking"] = False
    return out.sort_values(["eligible", "rank", "player_id"], ascending=[False, True, True])


def selection_pool(
    t: Tables,
    fmt: str,
    basis: ClassificationBasis,
    side: str | None = None,
) -> pd.DataFrame:
    """One row per eligible player: the side (batter or bowler) with the higher standardised score."""
    frames = [ranking_frame(t, s, fmt, basis) for s in SIDES if side in (None, s)]
    allr = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if allr.empty:
        return allr
    allr = allr.sort_values(
        ["player_id", "standardised_score", "side"], ascending=[True, False, True]
    )
    return allr.drop_duplicates("player_id", keep="first").reset_index(drop=True)


def directory_frame(
    t: Tables, basis: ClassificationBasis = ClassificationBasis.INCLUDE_DERIVED_CAPPED
) -> pd.DataFrame:
    """All classified players with matches played and experimental eligibility flags."""
    cls = effective_classification(t.classification, basis)
    out = cls.merge(matches_by_format(t.stats), on="player_id", how="left")
    for c in ("matches_IPL", "matches_T20I", "matches_COMBINED_w70_30"):
        out[c] = out[c].fillna(0).astype(int)
    out["matches"] = out["matches_COMBINED_w70_30"]
    sc = t.scores
    sc = sc[sc["stream"].isin(PRIMARY_STREAM.values())]
    sc = sc[is_eligible(sc["eligibility_status"]) & sc["format"].isin(["IPL", "T20I"])]
    flags = (
        sc.groupby("player_id")
        .apply(
            lambda g: ",".join(
                sorted({f"{r}:{f}" for r, f in zip(g["role"], g["format"], strict=True)})
            ),
            include_groups=False,
        )
        .rename("eligible_scopes")
    )
    out = out.merge(flags.reset_index(), on="player_id", how="left")
    out["eligible_scopes"] = out["eligible_scopes"].fillna("")
    pm = sc.groupby("player_id")["distinct_matches"].max().rename("distinct_matches").reset_index()
    out = out.merge(pm, on="player_id", how="left")
    out["group"] = [
        assign_group(n, s) for n, s in zip(out["eff_nationality"], out["eff_status"], strict=True)
    ]
    return out.sort_values("player_id").reset_index(drop=True)
