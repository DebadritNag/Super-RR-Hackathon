"""Synthetic delivery builders shared by the Phase 3 state and leakage tests."""

from __future__ import annotations

import pandas as pd

from app.analytics.pressure_engine import DELIVERY_COLUMNS


def row(match_id=1, innings=1, ball=1, bat=0, extras=None, prim=0, sec=0, wicket=False,
        dtype=None, dismissed=None, striker=11, non_striker=12, bowler=21, legal=None,
        four=False, six=False):  # fmt: skip
    et = "None" if extras is None else extras
    if legal is None:
        legal = et not in ("wide", "Overstep", "other")
    return {
        "match_id": match_id, "innings_number": innings, "innings_ball_num": ball,
        "overid": (ball - 1) // 6 + 1, "over_ball_num": (ball - 1) % 6 + 1,
        "batting_team_id": 1 if innings == 1 else 2, "bowling_team_id": 2 if innings == 1 else 1,
        "striker_id": striker, "non_striker_id": non_striker, "bowler_id": bowler,
        "batting_order": 1, "is_four": four, "is_six": six, "is_wicket": wicket,
        "dismissal_type": dtype, "dismissed_player_id": dismissed, "batter_runs": bat,
        "extras_type": et, "extras_primary_runs": prim, "extras_secondary_runs": sec,
        "is_legal_ball": legal, "extras_label_unverified": et in ("other", "Penalty"),
    }  # fmt: skip


def deliveries(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in DELIVERY_COLUMNS:
        if c not in df:
            df[c] = None
    return df[DELIVERY_COLUMNS]


def rows_n(n: int, **kw) -> list[dict]:
    """n independent rows (never share one dict between rows)."""
    return [row(**kw) for _ in range(n)]


def number(rows: list[dict], match_id=1, innings=1) -> list[dict]:
    """Assign match, innings and ball numbers in order."""
    for i, r in enumerate(rows, start=1):
        r["match_id"], r["innings_number"], r["innings_ball_num"] = match_id, innings, i
        r["overid"], r["over_ball_num"] = (i - 1) // 6 + 1, (i - 1) % 6 + 1
    return rows


def match(match_id=1, ctype="IPL", first=None, second=None, target=None, knock=False,
          season="2024", date="2024-04-01"):  # fmt: skip
    return {
        "match_id": match_id, "comp_id": 1, "match_date": pd.Timestamp(date), "stage": "League",
        "venue_id": 5, "knock_out": knock, "competition_type": ctype,
        "first_inn_revised_overs": first, "second_inn_revised_overs": second,
        "revised_target": target, "season_source": season,
    }  # fmt: skip


def matches(*ms: dict) -> pd.DataFrame:
    df = pd.DataFrame(list(ms))
    for c in ("first_inn_revised_overs", "second_inn_revised_overs", "revised_target"):
        df[c] = df[c].astype("float64")
    return df


def simple_innings1() -> list[dict]:
    """Seven rows: 4, wide(+1), 6, caught wicket, no-ball bat 2 (+1), legbye 1, dot."""
    return number([
        row(bat=4, four=True),
        row(extras="wide", prim=1),
        row(bat=6, six=True),
        row(wicket=True, dtype="Caught", dismissed=11),
        row(bat=2, extras="Overstep", prim=1),
        row(extras="legbyes", prim=1),
        row(bat=0),
    ])  # fmt: skip


def simple_two_innings() -> tuple[pd.DataFrame, pd.DataFrame]:
    inn1 = simple_innings1()  # total = 4 + 1 + 6 + 0 + 3 + 1 + 0 = 15
    inn2 = number(
        [row(bat=1), row(bat=0), row(bat=4, four=True), row(bat=0), row(bat=2), row(bat=1)],
        innings=2,
    )
    return deliveries(inn1 + inn2), matches(match())
