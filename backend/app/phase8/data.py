"""Phase 8 data layer: the single loader of pre-test deliveries, exclusions and feature guard.

Source is ``exp_pre_delivery_state`` (the validated pre-delivery state engine, read-only) joined to
``p4_match_period``. TEST rows are never selected. Exclusions are masks with counts; metric-level
flags (wicket anomaly, unverified extras) mark the target they invalidate and do not drop rows.
Missing is never zero: derived features are NULL when their inputs are unavailable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.phase8.constants import (
    EXPLORATORY_DB,
    LABEL_PREFIXES,
    LATE_DATE_TABLE,
    OFFICIAL_DB,
    PAR_TABLE,
    PERIOD_TABLE,
    PRE_TEST_PERIODS,
    REGULATION_INNINGS,
    RESTRICTED_MATCH_IDS,
    SCOPE,
    STATE_TABLE,
)
from app.phase8.lockguard import assert_no_test_rows

ID_COLS = [
    "match_id", "innings_number", "innings_ball_num", "match_date", "competition_type",
    "venue_id", "batting_team_id", "bowling_team_id", "striker_id", "non_striker_id", "bowler_id",
]  # fmt: skip

# Pre-delivery columns of the state table that may be used as model features.
STATE_FEATURES = [
    "innings_number", "chase_flag", "team_runs_before", "team_wickets_before", "wickets_remaining",
    "legal_balls_bowled_before", "innings_limit_balls", "legal_balls_remaining", "crr",
    "innings_phase", "target", "runs_required", "rrr", "gap", "projected_surplus",
    "resource_ratio", "striker_batting_order", "batter_balls_faced_before", "batter_runs_before",
    "bowler_legal_balls_before", "bowler_runs_charged_before", "competition_type", "stage",
    "knock_out",
]  # fmt: skip
# Derived in this module from earlier information only.
DERIVED_FEATURES = ["par_prior", "projected_total", "bat_team_prior", "bowl_team_prior"]
FEATURE_COLS = STATE_FEATURES + DERIVED_FEATURES

FLAG_COLS = [
    "regulation_pressure_eligible", "format_out_of_scope", "dls_exclude_primary",
    "restricted_innings_flag", "state_wicket_flag_disagreement", "target_basis_unverified",
    "req_nonpositive_flag", "den_wicket_flag_anomaly", "den_extras_label_unverified",
]  # fmt: skip
LABEL_COLS = [
    "out_batter_runs", "out_is_four", "out_is_six", "out_is_wicket", "out_dismissal_type",
    "out_dismissed_player_id", "out_extras_type", "out_extras_primary_runs", "out_is_legal_ball",
    "den_legal_inc", "den_counts_as_ball_faced", "den_bowler_charged_runs",
    "den_bowler_credited_wicket",
]  # fmt: skip
_FORBIDDEN_FEATURE_NAMES = {"striker_id", "non_striker_id", "bowler_id", "player_id", "match_id"}
_FORBIDDEN_FEATURE_FRAGMENTS = ("residual", "player_name", "dismissed")


class FeatureLeakError(ValueError):
    """A feature list contains an outcome column, an identifier or a residual."""


def assert_feature_list_clean(cols: list[str]) -> list[str]:
    """Raise unless every column is pre-delivery information (no label prefix, no player id)."""
    bad = []
    for c in cols:
        low = c.lower()
        if (
            c.startswith(LABEL_PREFIXES)
            or c in _FORBIDDEN_FEATURE_NAMES
            or any(f in low for f in _FORBIDDEN_FEATURE_FRAGMENTS)
            or c not in FEATURE_COLS
        ):
            bad.append(c)
    if bad:
        raise FeatureLeakError(f"not allowed as model features: {bad}")
    return list(cols)


def compute_team_priors(
    matches: pd.DataFrame, recent: int = 5, pseudo: float = 5.0
) -> pd.DataFrame:
    """Pre-match win-rate prior per (match, team) from strictly earlier matches only.

    The prior is ``(wins + 0.5 * pseudo) / (n + pseudo)`` over the team's last ``recent`` earlier
    decisive matches (same-date matches are excluded, as in the Phase 4 par prior). NULL when the
    team has no earlier decisive match. Mutating the result of match ``m`` or any later match leaves
    the prior of ``m`` unchanged.
    """
    need = ["match_id", "match_date", "home_team_id", "away_team_id", "win_team_id"]
    miss = [c for c in need if c not in matches.columns]
    if miss:
        raise ValueError(f"matches frame is missing {miss}")
    m = matches[need].copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    long = pd.concat(
        [
            m.rename(columns={"home_team_id": "team_id"})[
                ["match_id", "match_date", "team_id", "win_team_id"]
            ],
            m.rename(columns={"away_team_id": "team_id"})[
                ["match_id", "match_date", "team_id", "win_team_id"]
            ],
        ],
        ignore_index=True,
    )
    long = long.dropna(subset=["team_id"]).sort_values(["team_id", "match_date", "match_id"])
    long["won"] = (long["win_team_id"] == long["team_id"]).astype(float)
    long["decisive"] = long["win_team_id"].notna()
    rows: list[dict[str, Any]] = []
    for team, g in long.groupby("team_id", sort=True):
        dates = g["match_date"].to_numpy()
        won = g["won"].to_numpy()
        dec = g["decisive"].to_numpy()
        for i, (mid, d) in enumerate(zip(g["match_id"].to_numpy(), dates, strict=True)):
            prior_idx = np.flatnonzero((dates < d) & dec)
            last = prior_idx[-recent:]
            n = len(last)
            rate = (won[last].sum() + 0.5 * pseudo) / (n + pseudo) if n else np.nan
            rows.append({"match_id": int(mid), "team_id": int(team), "prior_win_rate": rate,
                         "prior_n": n})  # fmt: skip
            del i
    return pd.DataFrame(rows, columns=["match_id", "team_id", "prior_win_rate", "prior_n"])


def _exclusion_rows(
    df: pd.DataFrame, masks: list[tuple[str, pd.Series]]
) -> tuple[pd.Series, pd.DataFrame]:
    """First-reason attribution of excluded rows. Returns (keep mask, exclusion table)."""
    keep = pd.Series(True, index=df.index)
    out = []
    for reason, mask in masks:
        hit = mask & keep
        if hit.any():
            g = df[hit].groupby("competition_type")
            for comp, sub in g:
                out.append({"reason": reason, "competition_type": comp, "rows": int(len(sub)),
                            "matches": int(sub["match_id"].nunique())})  # fmt: skip
        keep &= ~mask
    return keep, pd.DataFrame(out, columns=["reason", "competition_type", "rows", "matches"])


def load_pre_test_deliveries(
    exploratory_db: Path | str = EXPLORATORY_DB,
    official_db: Path | str = OFFICIAL_DB,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Primary-scoring deliveries of TRAIN and VALIDATION plus the exclusion table.

    TEST rows are filtered in SQL and re-checked; both databases are opened read-only.
    """
    cols = list(dict.fromkeys(ID_COLS + STATE_FEATURES + FLAG_COLS + LABEL_COLS))
    sel = ", ".join(f"s.{c}" for c in cols)
    periods = ", ".join(f"'{p}'" for p in PRE_TEST_PERIODS)
    con = duckdb.connect(str(exploratory_db), read_only=True)
    try:
        df = con.execute(
            f"SELECT {sel}, p.period, "
            "CASE WHEN par.par_unavailable_insufficient_prior THEN NULL "
            "ELSE par.par_runs_prior END AS par_prior "
            f"FROM {STATE_TABLE} s JOIN {PERIOD_TABLE} p USING (match_id) "
            f"LEFT JOIN {PAR_TABLE} par ON par.match_id = s.match_id "
            "AND par.innings_number = s.innings_number "
            "AND par.innings_ball_num = s.innings_ball_num "
            f"WHERE p.period IN ({periods}) "
            "ORDER BY s.match_id, s.innings_number, s.innings_ball_num"
        ).df()
        late = con.execute(f"SELECT match_id FROM {LATE_DATE_TABLE} WHERE late_after_cutoff").df()[
            "match_id"
        ]
    finally:
        con.close()
    assert_no_test_rows(df)
    df["match_date"] = pd.to_datetime(df["match_date"])

    keep, excl = _exclusion_rows(
        df,
        [
            ("OUT_OF_SCOPE_COMPETITION", ~df["competition_type"].isin(SCOPE)
             | df["format_out_of_scope"].fillna(False).astype(bool)),
            ("RESTRICTED_INNINGS_3_4_SUPER_OVER", ~df["innings_number"].isin(REGULATION_INNINGS)
             | df["restricted_innings_flag"].fillna(False).astype(bool)
             | df["match_id"].isin(RESTRICTED_MATCH_IDS) & ~df["innings_number"].isin(REGULATION_INNINGS)),
            ("LATE_DATED_T20I_MATCH", df["match_id"].isin(set(late))),
            ("DLS_NOT_RECONSTRUCTABLE", df["dls_exclude_primary"].fillna(False).astype(bool)),
            ("NOT_REGULATION_PRESSURE_ELIGIBLE",
             ~df["regulation_pressure_eligible"].fillna(False).astype(bool)),
        ],
    )  # fmt: skip
    out = df[keep].reset_index(drop=True)

    off = duckdb.connect(str(official_db), read_only=True)
    try:
        matches = off.execute(
            "SELECT match_id, match_date, home_team_id, away_team_id, win_team_id FROM matches"
        ).df()
    finally:
        off.close()
    pri = compute_team_priors(matches)
    for side, name in (
        ("batting_team_id", "bat_team_prior"),
        ("bowling_team_id", "bowl_team_prior"),
    ):
        p = pri.rename(columns={"team_id": side, "prior_win_rate": name})[["match_id", side, name]]
        out = out.merge(p, on=["match_id", side], how="left")
    ball_ok = out["legal_balls_bowled_before"] > 0
    out["projected_total"] = np.where(
        ball_ok,
        out["team_runs_before"] + out["crr"] * out["legal_balls_remaining"] / 6.0,
        np.nan,
    )
    out["ok_wicket_target"] = ~out["den_wicket_flag_anomaly"].fillna(False).astype(bool)
    out["ok_run_target"] = ~out["den_extras_label_unverified"].fillna(False).astype(bool)
    metric = pd.DataFrame(
        [
            {"reason": "METRIC_WICKET_FLAG_ANOMALY", "competition_type": "ALL",
             "rows": int((~out["ok_wicket_target"]).sum()),
             "matches": int(out.loc[~out["ok_wicket_target"], "match_id"].nunique())},
            {"reason": "METRIC_EXTRAS_LABEL_UNVERIFIED", "competition_type": "ALL",
             "rows": int((~out["ok_run_target"]).sum()),
             "matches": int(out.loc[~out["ok_run_target"], "match_id"].nunique())},
        ]
    )  # fmt: skip
    excl = pd.concat([excl, metric], ignore_index=True)
    assert_no_test_rows(out)
    return out, excl
