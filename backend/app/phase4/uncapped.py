"""Classification filters and the dedicated uncapped rankings (filters over the main scoring).

Phase 5 enum: the international status is VERIFIED_CAPPED, DERIVED_CAPPED or UNKNOWN; the
VERIFIED_UNCAPPED value is a disabled placeholder, not an established status (see ``app.phase5.classification_v2``). ``exclude_uncapped`` removes rows whose effective
status is VERIFIED_UNCAPPED (UNKNOWN rows are kept, because their status cannot be shown to be
uncapped). The uncapped rankings are filtered views of the same experimental ranking frame: they
never recompute scores or thresholds. Strict-uncapped requests are refused one layer up (the
service) while ``strict_uncapped_enabled`` is false; ``is_strict_uncapped_request`` names them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from app.phase4.classification import V_NONE, V_SOURCE

CAPPED_STATUSES = ("VERIFIED_CAPPED", "DERIVED_CAPPED")
VERIFIED_UNCAPPED = "VERIFIED_UNCAPPED"
UNKNOWN_STATUS = "UNKNOWN"


class ClassificationFilter(StrEnum):
    indian_uncapped = "indian_uncapped"
    overseas_uncapped = "overseas_uncapped"
    all_uncapped = "all_uncapped"
    capped_any = "capped_any"
    capped_verified = "capped_verified"
    capped_derived = "capped_derived"
    unknown_international_status = "unknown_international_status"


class UncappedMode(StrEnum):
    include_uncapped = "include_uncapped"
    exclude_uncapped = "exclude_uncapped"


class ClassificationBasis(StrEnum):
    INCLUDE_DERIVED_CAPPED = "INCLUDE_DERIVED_CAPPED"
    VERIFIED_ONLY = "VERIFIED_ONLY"


class UncappedKind(StrEnum):
    indian_batters = "indian_batters"
    indian_bowlers = "indian_bowlers"
    overseas_batters = "overseas_batters"
    overseas_bowlers = "overseas_bowlers"
    overall = "overall"


class FilterError(ValueError):
    """Raised for contradictory filter parameters."""


@dataclass(frozen=True)
class FilterParams:
    classification: ClassificationFilter | None = None
    uncapped_mode: UncappedMode | None = None
    min_matches: int | None = None
    min_pressure_matches: int | None = None


UNCAPPED_FILTERS = (
    ClassificationFilter.indian_uncapped,
    ClassificationFilter.overseas_uncapped,
    ClassificationFilter.all_uncapped,
)


def is_strict_uncapped_request(p: FilterParams) -> bool:
    """True when the request asks for uncapped rows (disabled until strict uncapped is enabled)."""
    return p.classification in UNCAPPED_FILTERS or p.uncapped_mode == UncappedMode.include_uncapped


def effective_classification(cls: pd.DataFrame, basis: ClassificationBasis) -> pd.DataFrame:
    """Add eff_nationality / eff_status. VERIFIED_ONLY treats derived values as UNKNOWN."""
    out = cls.copy()
    if basis == ClassificationBasis.VERIFIED_ONLY:
        nat_ok = out["nationality_verification"] == V_SOURCE
        st_ok = out["international_status_verification"] == V_SOURCE
    else:
        nat_ok = out["nationality_verification"] != V_NONE
        st_ok = out["international_status_verification"] != V_NONE
    out["eff_nationality"] = out["nationality"].where(nat_ok, "Unknown")
    out["eff_status"] = out["international_status"].where(st_ok, UNKNOWN_STATUS)
    out["eff_nationality_verification"] = out["nationality_verification"].where(nat_ok, V_NONE)
    out["eff_status_verification"] = out["international_status_verification"].where(st_ok, V_NONE)
    out["status_is_verified_source"] = out["international_status_verification"] == V_SOURCE
    return out


def verified_uncapped_mask(df: pd.DataFrame) -> pd.Series:
    return (df["eff_status"] == VERIFIED_UNCAPPED) & df["status_is_verified_source"]


def apply_filters(df: pd.DataFrame, p: FilterParams) -> pd.DataFrame:
    if p.classification in UNCAPPED_FILTERS and p.uncapped_mode == UncappedMode.exclude_uncapped:
        raise FilterError("an uncapped classification filter contradicts exclude_uncapped")
    mask = pd.Series(True, index=df.index)
    c = p.classification
    if c == ClassificationFilter.indian_uncapped:
        mask &= verified_uncapped_mask(df) & (df["eff_nationality"] == "Indian")
    elif c == ClassificationFilter.overseas_uncapped:
        mask &= verified_uncapped_mask(df) & (df["eff_nationality"] == "Overseas")
    elif c == ClassificationFilter.all_uncapped:
        mask &= verified_uncapped_mask(df)
    elif c == ClassificationFilter.capped_any:
        mask &= df["eff_status"].isin(CAPPED_STATUSES)
    elif c == ClassificationFilter.capped_verified:
        mask &= df["eff_status"] == "VERIFIED_CAPPED"
    elif c == ClassificationFilter.capped_derived:
        mask &= df["eff_status"] == "DERIVED_CAPPED"
    elif c == ClassificationFilter.unknown_international_status:
        mask &= df["eff_status"] == UNKNOWN_STATUS
    if p.uncapped_mode == UncappedMode.exclude_uncapped:
        mask &= df["eff_status"] != VERIFIED_UNCAPPED
    if p.min_matches is not None:
        mask &= df["matches"].fillna(0) >= p.min_matches
    if p.min_pressure_matches is not None:
        mask &= df["distinct_matches"].fillna(0) >= p.min_pressure_matches
    return df[mask]


_KIND_FILTER = {
    UncappedKind.indian_batters: (ClassificationFilter.indian_uncapped, "batter"),
    UncappedKind.indian_bowlers: (ClassificationFilter.indian_uncapped, "bowler"),
    UncappedKind.overseas_batters: (ClassificationFilter.overseas_uncapped, "batter"),
    UncappedKind.overseas_bowlers: (ClassificationFilter.overseas_uncapped, "bowler"),
    UncappedKind.overall: (ClassificationFilter.all_uncapped, None),
}


def kind_spec(kind: UncappedKind) -> tuple[ClassificationFilter, str | None]:
    return _KIND_FILTER[kind]


def unverified_candidates(df: pd.DataFrame, kind: UncappedKind) -> pd.DataFrame:
    """Separate list: nationality matches, status UNKNOWN_STATUS (not proven capped, NOT uncapped)."""
    flt, _ = _KIND_FILTER[kind]
    unknown = df["eff_status"] == UNKNOWN_STATUS
    if flt == ClassificationFilter.indian_uncapped:
        return df[unknown & (df["eff_nationality"] == "Indian")]
    if flt == ClassificationFilter.overseas_uncapped:
        return df[unknown & (df["eff_nationality"] == "Overseas")]
    return df[unknown]
