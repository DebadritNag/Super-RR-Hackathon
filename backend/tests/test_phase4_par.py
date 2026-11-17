"""Strictly prior par: prior-only, same-day tie-break, insufficient prior, leakage guard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics import pressure_features as pf
from app.phase4 import par as p4par
from app.phase4.constants import PAR_FLAG
from app.phase4.split import Split, attach_period
from tests.phase4_helpers import brute_force_prior, many_matches

SPECS = [
    (1, "2024-01-01", "IPL", 1.0),
    (2, "2024-01-02", "IPL", 2.0),
    (3, "2024-01-02", "IPL", 4.0),  # same date as match 2 (double-header)
    (4, "2024-01-03", "IPL", 8.0),
    (5, "2024-01-03", "T20I", 100.0),  # other format must never leak into IPL par
    (6, "2024-01-04", "IPL", 16.0),
]


def par_at(df, par, match_id, ball=60):
    sel = (df["match_id"] == match_id) & (df["legal_balls_bowled_before"] == ball)
    return par.loc[sel, "par_runs_prior"].iloc[0]


def test_prior_only_and_same_day_excluded():
    df = many_matches(SPECS)
    par = p4par.strictly_prior_par(df, min_prior=1)
    # match 1 is first: nothing before it
    assert np.isnan(par_at(df, par, 1))
    # match 2 and 3 share a date: both see only match 1 (rpb 1 -> 60 runs after 60 balls)
    assert par_at(df, par, 2) == 60.0
    assert par_at(df, par, 3) == 60.0
    # match 4 sees matches 1, 2, 3 (same-day pair is earlier than match 4): mean rpb 7/3
    assert par_at(df, par, 4) == pytest.approx(60 * (1 + 2 + 4) / 3)
    # match 6 sees 1, 2, 3, 4 in IPL only (the T20I match is another format)
    assert par_at(df, par, 6) == pytest.approx(60 * (1 + 2 + 4 + 8) / 4)
    sel = df["match_id"] == 4
    assert (par.loc[sel, "par_prior_innings_n"] == 3).all()


def test_changing_later_or_same_day_matches_does_not_change_par():
    df = many_matches(SPECS)
    base = p4par.strictly_prior_par(df, min_prior=1)
    later = df.copy()
    later.loc[later["match_id"].isin([6]), ["team_runs_before", "out_runs_row"]] *= 5
    same_day = df.copy()
    same_day.loc[same_day["match_id"] == 3, ["team_runs_before", "out_runs_row"]] *= 7
    p_later = p4par.strictly_prior_par(later, min_prior=1)
    p_same = p4par.strictly_prior_par(same_day, min_prior=1)
    for mid in (1, 2, 3, 4):
        m = (df["match_id"] == mid).to_numpy()
        np.testing.assert_array_equal(
            base.loc[m, "par_runs_prior"].to_numpy(), p_later.loc[m, "par_runs_prior"].to_numpy()
        )
    for mid in (1, 2, 3):  # match 3 changed on the same day: matches 2 and 3 unaffected
        m = (df["match_id"] == mid).to_numpy()
        np.testing.assert_array_equal(
            base.loc[m, "par_runs_prior"].to_numpy(), p_same.loc[m, "par_runs_prior"].to_numpy()
        )


def test_changing_an_earlier_match_changes_later_par():
    df = many_matches(SPECS)
    base = p4par.strictly_prior_par(df, min_prior=1)
    mut = df.copy()
    mut.loc[mut["match_id"] == 1, "team_runs_before"] *= 3
    mut.loc[mut["match_id"] == 1, "out_runs_row"] *= 3
    changed = p4par.strictly_prior_par(mut, min_prior=1)
    assert par_at(mut, changed, 4) != par_at(df, base, 4)


def test_insufficient_prior_is_null_flagged_and_never_zero():
    df = many_matches(SPECS)
    par = p4par.strictly_prior_par(df, min_prior=3)
    # IPL matches 1,2,3 have 0,1,1 prior innings -> unavailable; match 4 has 3 -> available
    for mid in (1, 2, 3):
        m = df["match_id"] == mid
        assert par.loc[m, "par_runs_prior"].isna().all()
        assert par.loc[m, PAR_FLAG].all()
    assert par.loc[df["match_id"] == 4, "par_runs_prior"].notna().all()
    assert not par.loc[df["match_id"] == 4, PAR_FLAG].any()
    assert par.loc[par[PAR_FLAG], "par_runs_prior"].isna().all()  # never zero-filled
    # the T20I match has no prior T20I innings at all
    assert par.loc[df["match_id"] == 5, PAR_FLAG].all()


def test_non_innings1_rows_are_not_applicable():
    df = pd.concat(
        [many_matches(SPECS[:2]), many_matches(SPECS[:2]).assign(innings_number=2)],
        ignore_index=True,
    )
    par = p4par.strictly_prior_par(df, min_prior=1)
    second = df["innings_number"] == 2
    assert not par.loc[second, "par_applicable"].any()
    assert par.loc[second, "par_runs_prior"].isna().all()
    assert not par.loc[second, PAR_FLAG].any()


def test_matches_brute_force_reference():
    df = many_matches(
        [
            (1, "2024-01-01", "IPL", 1.0),
            (2, "2024-01-02", "IPL", 1.5),
            (3, "2024-01-03", "IPL", 2.0),
            (4, "2024-01-03", "IPL", 0.5),
            (5, "2024-01-05", "IPL", 3.0),
            (6, "2024-01-06", "T20I", 1.0),
            (7, "2024-01-07", "T20I", 2.0),
            (8, "2024-01-08", "IPL", 2.5),
        ]
    )
    for min_prior in (1, 2, 3):
        fast = p4par.strictly_prior_par(df, min_prior=min_prior)["par_runs_prior"].to_numpy()
        slow = brute_force_prior(df, min_prior)
        np.testing.assert_allclose(fast, slow, equal_nan=True)


def test_equivalent_to_existing_par_runs_prior():
    rules = pf.load_rules()
    min_prior = int(pf.param(rules, "min_prior_innings"))
    specs = [(i, f"2024-02-{(i % 28) + 1:02d}", "IPL", 1.0 + (i % 5)) for i in range(1, 38)]
    specs.sort(key=lambda s: s[1])
    specs += [(100 + i, f"2024-03-{i + 1:02d}", "T20I", 2.0 + i) for i in range(3)]
    df = many_matches(specs)
    new = p4par.strictly_prior_par(df, min_prior=min_prior)["par_runs_prior"]
    old, _ = pf.par_columns(df, rules)
    np.testing.assert_allclose(new.to_numpy(), old["par_runs_prior"].to_numpy(), equal_nan=True)


def test_source_cutoff_freezes_the_source_set():
    df = many_matches(SPECS)
    frozen = p4par.strictly_prior_par(df, min_prior=1, source_cutoff="2024-01-01")
    assert par_at(df, frozen, 6) == 60.0  # only match 1 is allowed as a source
    assert par_at(df, frozen, 4) == 60.0


def test_lomo_is_labelled_descriptive_and_guard_rejects_it():
    rules = pf.load_rules()
    specs = [(i, f"2024-03-{i:02d}", "IPL", 1.0 + i % 3) for i in range(1, 8)]
    specs.append((99, "2024-03-09", "T20I", 2.0))
    df = many_matches(specs)
    lomo = p4par.lomo_par_descriptive(df, rules)
    (col,) = lomo.columns
    assert "DESCRIPTIVE_ONLY_USES_FUTURE_MATCHES" in col
    with pytest.raises(p4par.LeakageError):
        p4par.LeakageGuard.check_columns(["par_runs_prior", col])
    with pytest.raises(p4par.LeakageError):
        p4par.LeakageGuard.check_columns(["par_runs_lomo"])
    p4par.LeakageGuard.check_columns(["par_runs_prior", "par_deviation_prior"])  # fine


def test_coverage_counts_by_format_and_period():
    split = Split.from_config()
    specs = [
        (1, "2024-12-30", "IPL", 1.0),
        (2, "2025-02-01", "IPL", 2.0),
        (3, "2026-02-01", "IPL", 3.0),
    ]
    df = attach_period(many_matches(specs), split)
    par = p4par.strictly_prior_par(df, min_prior=2)
    cov = p4par.par_coverage(df, par)
    by = {(r["competition_type"], r["period"]): r for r in cov["rows"]}
    assert by[("IPL", "TRAIN")]["rows_unavailable"] == 120
    assert by[("IPL", "VALIDATION")]["innings_unavailable"] == 1  # one prior innings < 2
    assert by[("IPL", "TEST")]["rows_unavailable"] == 0  # two prior innings
    assert cov["total_innings_unavailable"] == 2
    assert by[("IPL", "TRAIN")]["last_unavailable_date"] == "2024-12-30"
