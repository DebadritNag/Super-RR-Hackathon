"""Rajasthan Royals (RR) historical performance versus the rest of the IPL, by season.

Descriptive only. Reads the official database and the exploratory ``exp_pre_delivery_state``
phase labels read-only. Every metric compares RR with all other teams over the same phase
definition, with a seeded bootstrap that resamples matches (cluster unit = match). Nothing here
is a score, a rank, an eligibility decision or a recommendation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 20261114
N_BOOT = 1000
LEVEL = 0.95
MIN_BALLS = 120  # below this many RR balls a row is labelled LOW_SAMPLE
PRIMARY = "2022-2025"
PERIODS = ("2022", "2023", "2024", "2025", PRIMARY, "2026")

# name -> (side, filter, numerator column, denominator column, unit, direction, label)
# direction: +1 higher is better for RR, -1 lower is better, 0 usage only (no gap reading).
METRICS: dict[str, dict] = {}


def _m(name, side, label, num, den, unit, direction, **flt):
    METRICS[name] = dict(
        side=side, label=label, num=num, den=den, unit=unit, direction=direction, flt=flt
    )


# Batting: RR batting rows against league batting rows.
for ph, nm in (("powerplay", "pp"), ("middle", "mid"), ("death", "death")):
    _m(f"bat_{nm}_rpo", "bat", f"Batting {ph}: runs per over", "runs", "legal", "per_over", 1, phase=ph)
    _m(
        f"bat_{nm}_wkt", "bat", f"Batting {ph}: wickets lost per over",
        "wkt", "legal", "per_over", -1, phase=ph,
    )  # fmt: skip
_m("bat_death_bdry", "bat", "Batting death: boundary balls per 100 balls faced",
   "boundary", "faced", "per_100", 1, phase="death")  # fmt: skip
_m("bat_mid_spin_rpo", "bat", "Batting middle vs spin: runs per over",
   "runs", "legal", "per_over", 1, phase="middle", pace_or_spin="Spin")  # fmt: skip
_m("bat_mid_spin_wkt", "bat", "Batting middle vs spin: wickets lost per over",
   "wkt", "legal", "per_over", -1, phase="middle", pace_or_spin="Spin")  # fmt: skip
_m("bat_mid_pace_rpo", "bat", "Batting middle vs pace: runs per over",
   "runs", "legal", "per_over", 1, phase="middle", pace_or_spin="Pace")  # fmt: skip
_m("bat_mid_pace_wkt", "bat", "Batting middle vs pace: wickets lost per over",
   "wkt", "legal", "per_over", -1, phase="middle", pace_or_spin="Pace")  # fmt: skip
_m("bat_pos6to8_rpo", "bat", "Batting positions 6-8, all phases: runs per over",
   "runs", "legal", "per_over", 1, order=(6, 8))  # fmt: skip
_m("bat_pos6to8_wkt", "bat", "Batting positions 6-8, all phases: wickets lost per over",
   "wkt", "legal", "per_over", -1, order=(6, 8))  # fmt: skip
_m("bat_pos6to8_share", "bat", "Share of team legal balls faced by positions 6-8 (usage)",
   "pos6to8_legal", "legal_all", "per_100", 0)  # fmt: skip
# Bowling: RR bowling rows against league bowling rows.
for ph, nm in (("powerplay", "pp"), ("middle", "mid"), ("death", "death")):
    _m(f"bowl_{nm}_econ", "bowl", f"Bowling {ph}: runs conceded per over",
       "bruns", "legal", "per_over", -1, phase=ph)  # fmt: skip
    _m(f"bowl_{nm}_wkt", "bowl", f"Bowling {ph}: bowler-credited wickets per over",
       "bwkt", "legal", "per_over", 1, phase=ph)  # fmt: skip
_m("bowl_pace_pp_econ", "bowl", "Pace bowling powerplay: runs conceded per over",
   "bruns", "legal", "per_over", -1, phase="powerplay", pace_or_spin="Pace")  # fmt: skip
_m("bowl_pace_pp_wkt", "bowl", "Pace bowling powerplay: bowler-credited wickets per over",
   "bwkt", "legal", "per_over", 1, phase="powerplay", pace_or_spin="Pace")  # fmt: skip
_m("bowl_pace_death_econ", "bowl", "Pace bowling death: runs conceded per over",
   "bruns", "legal", "per_over", -1, phase="death", pace_or_spin="Pace")  # fmt: skip
_m("bowl_pace_death_wkt", "bowl", "Pace bowling death: bowler-credited wickets per over",
   "bwkt", "legal", "per_over", 1, phase="death", pace_or_spin="Pace")  # fmt: skip
_m("bowl_spin_mid_econ", "bowl", "Spin bowling middle: runs conceded per over",
   "bruns", "legal", "per_over", -1, phase="middle", pace_or_spin="Spin")  # fmt: skip
_m("bowl_spin_mid_wkt", "bowl", "Spin bowling middle: bowler-credited wickets per over",
   "bwkt", "legal", "per_over", 1, phase="middle", pace_or_spin="Spin")  # fmt: skip
_m("bowl_pace_share", "bowl", "Share of legal balls bowled by pace (usage)",
   "pace_legal", "legal", "per_100", 0)  # fmt: skip
_m("bowl_rank5plus_share", "bowl", "Share of legal balls bowled by the 5th-or-later most used bowler of the innings (usage)",
   "rank5_legal", "legal", "per_100", 0)  # fmt: skip

IPL_SQL = """
select s.match_id, s.innings_number, s.season_label as season, s.batting_team_id,
       s.bowling_team_id, s.innings_phase as phase, s.striker_batting_order as bat_order,
       d.pace_or_spin, d.bowler_id, s.out_runs_row as runs, s.den_legal_inc as legal,
       s.out_is_wicket::int as wkt, s.den_bowler_credited_wicket as bwkt,
       s.den_bowler_charged_runs as bruns, s.den_counts_as_ball_faced as faced,
       (s.out_is_four or s.out_is_six)::int as boundary
from exp_pre_delivery_state s
join o.deliveries d using (match_id, innings_number, innings_ball_num)
where s.competition_type = 'IPL' and s.regulation_flag and not s.dls_exclude_primary
  and s.innings_number in (1, 2) and s.innings_phase is not null
"""


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the derived usage columns. Input columns as returned by ``IPL_SQL``."""
    df = frame.copy()
    df["legal_all"] = df["legal"]
    df["pos6to8_legal"] = np.where(df["bat_order"].between(6, 8), df["legal"], 0)
    df["pace_legal"] = np.where(df["pace_or_spin"] == "Pace", df["legal"], 0)
    key = ["match_id", "innings_number", "bowler_id"]
    balls = df.groupby(key)["legal"].sum().rename("b").reset_index()
    balls["rk"] = balls.groupby(["match_id", "innings_number"])["b"].rank(
        method="first", ascending=False
    )
    df = df.merge(balls[key + ["rk"]], on=key, how="left")
    df["rank5_legal"] = np.where(df["rk"] >= 5, df["legal"], 0)
    return df


def _filter(df: pd.DataFrame, flt: dict) -> pd.DataFrame:
    for k, v in flt.items():
        if k == "order":
            df = df[df["bat_order"].between(v[0], v[1])]
        else:
            df = df[df[k] == v]
    return df


def _scale(unit: str) -> float:
    return 6.0 if unit == "per_over" else 100.0


def _boot(rr: np.ndarray, lg: np.ndarray, scale: float, rng: np.random.Generator):
    """rr, lg: arrays (matches, 2) of (num, den). Returns the difference draws."""
    i = rng.integers(0, len(rr), size=(N_BOOT, len(rr)))
    j = rng.integers(0, len(lg), size=(N_BOOT, len(lg)))
    a = rr[i].sum(axis=1)
    b = lg[j].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = scale * (a[:, 0] / a[:, 1] - b[:, 0] / b[:, 1])
    return d[np.isfinite(d)]


def assess(direction: int, low: bool, lo: float | None, hi: float | None) -> str:
    if direction == 0:
        return "USAGE_DESCRIPTIVE"
    if low or lo is None or hi is None:
        return "LOW_SAMPLE"
    if lo > 0 or hi < 0:
        worse = (hi < 0) if direction > 0 else (lo > 0)
        return "RR_WORSE_SUPPORTED" if worse else "RR_BETTER_SUPPORTED"
    return "NOT_DISTINGUISHABLE"


def compare(df: pd.DataFrame, rr_id: int) -> pd.DataFrame:
    """One row per metric and period: RR value, league value (RR excluded), difference, CI."""
    rng = np.random.default_rng(SEED)
    rows = []
    for name, m in METRICS.items():
        team_col = "batting_team_id" if m["side"] == "bat" else "bowling_team_id"
        sub = _filter(df, m["flt"])
        grp = (
            sub.assign(is_rr=sub[team_col] == rr_id)
            .groupby(["season", "match_id", "is_rr"])[[m["num"], m["den"]]]
            .sum()
            .reset_index()
        )
        # RR matches with no qualifying rows still count as matches with 0/0.
        for period in PERIODS:
            seasons = period.split("-") if "-" in period else [period]
            if "-" in period:
                seasons = [str(y) for y in range(int(seasons[0]), int(seasons[1]) + 1)]
            g = grp[grp["season"].isin(seasons)]
            rr_m = df[(df["season"].isin(seasons)) & ((df["batting_team_id"] == rr_id) | (df["bowling_team_id"] == rr_id))]["match_id"].unique()
            rr_g = g[g["is_rr"]].set_index("match_id")[[m["num"], m["den"]]]
            lg_g = g[~g["is_rr"]]
            # League = rows of non-RR teams; matches where RR played contribute the opponent.
            lg_g = lg_g.groupby("match_id")[[m["num"], m["den"]]].sum()
            rr_arr = rr_g.reindex(rr_m, fill_value=0).to_numpy(dtype=float)
            lg_arr = lg_g.to_numpy(dtype=float)
            sc = _scale(m["unit"])
            rn, rd = rr_arr.sum(axis=0)
            ln, ld = lg_arr.sum(axis=0)
            rr_v = sc * rn / rd if rd else None
            lg_v = sc * ln / ld if ld else None
            lo = hi = diff = None
            if rd and ld and len(rr_arr) > 1:
                draws = _boot(rr_arr, lg_arr, sc, rng)
                diff = rr_v - lg_v
                lo, hi = (float(x) for x in np.quantile(draws, [(1 - LEVEL) / 2, (1 + LEVEL) / 2]))
            low = rd < MIN_BALLS
            rows.append(
                dict(
                    metric=name, label=m["label"], side=m["side"], unit=m["unit"],
                    period=period, rr_matches=int(len(rr_m)), league_matches=int(len(lg_g)),
                    rr_numerator=float(rn), rr_balls=float(rd), rr_value=rr_v,
                    league_numerator=float(ln), league_balls=float(ld), league_value=lg_v,
                    difference=diff, ci_low=lo, ci_high=hi, direction=m["direction"],
                    assessment=assess(m["direction"], low, lo, hi),
                )
            )  # fmt: skip
    return pd.DataFrame(rows)


def bowler_depth(df: pd.DataFrame, rr_id: int, min_balls: int = MIN_BALLS) -> pd.DataFrame:
    """Per season: bowlers with at least ``min_balls`` legal balls, split by pace and spin,
    for RR and for the mean of the other nine teams (descriptive counts, no uncertainty)."""
    b = (
        df.groupby(["season", "bowling_team_id", "bowler_id", "pace_or_spin"])["legal"]
        .sum()
        .reset_index()
    )
    b = b[b["legal"] >= min_balls]
    cnt = (
        b.groupby(["season", "bowling_team_id", "pace_or_spin"]).size().rename("n").reset_index()
    )
    out = []
    for s in sorted(df["season"].unique()):
        teams = sorted(df[df["season"] == s]["bowling_team_id"].unique())
        for kind in ("Pace", "Spin"):
            c = cnt[(cnt["season"] == s) & (cnt["pace_or_spin"] == kind)].set_index(
                "bowling_team_id"
            )["n"]
            full = c.reindex(teams, fill_value=0)
            others = full.drop(rr_id, errors="ignore")
            out.append(
                dict(
                    season=s, kind=kind, rr_bowlers=int(full.get(rr_id, 0)),
                    league_mean=float(others.mean()), league_min=int(others.min()),
                    league_max=int(others.max()), min_balls=min_balls,
                )
            )  # fmt: skip
    return pd.DataFrame(out)
