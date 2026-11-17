"""Phase boundaries for shortened innings, no future information, DLS exclusions."""

from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.phase_engine import phase_label
from app.phase4 import phases as p4ph
from app.phase4.data import with_primary_mask
from tests.phase4_helpers import innings_rows

# Hand-checked: pp_end = floor(3L/10), death_start = ceil(3L/4)
HAND = {
    30: (9, 23),
    60: (18, 45),
    66: (19, 50),
    72: (21, 54),
    84: (25, 63),
    90: (27, 68),
    96: (28, 72),
    100: (30, 75),
    108: (32, 81),
    114: (34, 86),
    120: (36, 90),
}


@pytest.mark.parametrize("limit", sorted(HAND))
def test_boundaries_hand_checked(limit):
    row = p4ph.boundary_table([limit]).iloc[0]
    pp, death = HAND[limit]
    assert (row["powerplay_end_ball"], row["death_start_ball"]) == (pp, death)
    assert row["powerplay_balls"] + row["middle_balls"] + row["death_balls"] == limit


@pytest.mark.parametrize("limit", sorted(HAND))
def test_labels_switch_exactly_at_the_boundary(limit):
    pp, death = HAND[limit]
    labels = p4ph.phase_for(range(limit), limit)
    assert labels[pp - 1] == "powerplay" and labels[pp] == "middle"
    assert labels[death - 1] == "middle" and labels[death] == "death"
    assert labels.count("powerplay") == pp
    assert labels.count("death") == limit - death


def test_phase_depends_only_on_balls_before_and_limit():
    df = pd.concat(
        [innings_rows(1, "2024-01-01", limit=66), innings_rows(2, "2024-01-02", limit=120)],
        ignore_index=True,
    )
    df["innings_phase"] = phase_label(df["legal_balls_bowled_before"], df["innings_limit_balls"])
    checks = p4ph.check_phase_labels(df)
    assert all(checks[k] for k in checks if k != "rows_checked")
    # corrupting a stored label is detected
    bad = df.copy()
    bad.loc[0, "innings_phase"] = "death"
    assert not p4ph.check_phase_labels(bad)["stored_labels_equal_recomputed_from_B_and_L"]


def test_future_rows_do_not_change_earlier_labels():
    full = innings_rows(1, "2024-01-01", limit=90)
    cut = full.iloc[:50]
    a = phase_label(full["legal_balls_bowled_before"], full["innings_limit_balls"]).iloc[:50]
    b = phase_label(cut["legal_balls_bowled_before"], cut["innings_limit_balls"])
    assert a.tolist() == b.tolist()


def _mixed():
    return pd.concat(
        [
            innings_rows(1, "2024-01-01", limit=120, limit_source="DEFAULT_120"),
            innings_rows(2, "2024-01-02", limit=66, limit_source="REVISED_FIELD"),
            innings_rows(2, "2024-01-02", limit=66, innings=2, limit_source="REVISED_FIELD"),
            innings_rows(
                3, "2024-01-03", limit=90, limit_source="CARRIED_FROM_FIRST_INNINGS_UNVERIFIED"
            ),
        ],
        ignore_index=True,
    )


def test_shortened_report_counts_innings_and_deliveries():
    rep = p4ph.shortened_report(_mixed())
    assert rep["limits_present"] == [66, 90, 120]
    assert rep["shortened_innings"] == 3
    assert rep["shortened_matches"] == 2
    assert rep["shortened_deliveries"] == 66 + 66 + 90
    assert rep["limit_constant_within_every_innings"] is True
    assert rep["shortened_innings_by_limit_source"] == {
        "CARRIED_FROM_FIRST_INNINGS_UNVERIFIED": 1,
        "REVISED_FIELD": 2,
    }
    row66 = next(r for r in rep["by_limit"] if r["limit"] == 66)
    assert (row66["powerplay_end_ball"], row66["death_start_ball"]) == (19, 50)


def test_revision_timing_upper_bound():
    df = innings_rows(1, "2024-01-01", limit=66)
    summary = p4ph.revision_timing_summary(df)
    # under L=120 balls 0..65 are all powerplay (B < 36) or middle; under L=66 they differ
    revised = phase_label(df["legal_balls_bowled_before"], df["innings_limit_balls"])
    original = phase_label(df["legal_balls_bowled_before"], pd.Series(120, index=df.index))
    assert summary["deliveries_whose_label_depends_on_revised_limit"] == int(
        (revised != original).sum()
    )
    assert summary["announcement_time_in_data"] is False


def test_dls_rows_are_masked_not_deleted_and_not_imputed():
    df = _mixed()
    n = len(df)
    masked = with_primary_mask(df)
    assert len(masked) == n  # no delivery row is dropped
    short = masked["innings_limit_balls"] != 120
    assert not masked.loc[short, "in_primary_scoring"].any()
    assert masked.loc[~short, "in_primary_scoring"].all()
    # the original limits are untouched (no imputation of limits or resources)
    assert masked["innings_limit_balls"].tolist() == df["innings_limit_balls"].tolist()
    summary = p4ph.dls_exclusion_summary(df)
    assert summary["dls_excluded_regulation_rows"] == int(short.sum())
    assert summary["dls_resources_imputed"] is False
    assert summary["rows_deleted"] == 0
    assert summary["dls_excluded_chase_rows_otherwise_eligible"] == 66  # the shortened innings 2
