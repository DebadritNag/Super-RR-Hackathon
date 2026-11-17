"""Build the Rajasthan Royals historical-performance tables (JSON) and the report tables.

Read-only on ``superr.duckdb`` and ``exploratory.duckdb``; writes only
``data/reports/rr_analysis_tables.json``. TEST-lock note: deliveries of the 2026 IPL season are
read for a clearly labelled descriptive table only; nothing is tuned on them.
Run from ``backend``: ``python scripts/rr_analysis.py [--candidate-min-balls N]``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from app.phase7 import rr_analysis as rr  # noqa: E402

DB = ROOT / "data" / "database"
REPORTS = ROOT / "data" / "reports"
SQUAD = ROOT.parent / "ipl squad.csv"
OUT = REPORTS / "rr_analysis_tables.json"
REPORT = REPORTS / "rr_historical_performance_and_recruitment_gaps.md"
TEAM_NAME = "Rajasthan Royals"

CANDIDATE_RULES = {
    "A_batters_vs_spin_middle": dict(
        side="batter", need=("vs_spin_balls", "mid_balls"),
        cols=("vs_spin_balls", "vs_spin_strike_rate", "vs_spin_dismissals", "mid_balls", "mid_strike_rate"),
        extra=None, title="Batters with a large middle-over and versus-spin sample",
    ),
    "B_pace_death_bowlers": dict(
        side="bowler", need=("death_balls",),
        cols=("death_balls", "death_economy", "death_wickets"),
        extra="Pace", title="Pace bowlers with a large death-over sample",
    ),
    "C_pace_powerplay_bowlers": dict(
        side="bowler", need=("pp_balls",),
        cols=("pp_balls", "pp_economy", "pp_wickets"),
        extra="Pace", title="Pace bowlers with a large powerplay sample",
    ),
    "D_spin_middle_bowlers": dict(
        side="bowler", need=("mid_balls",),
        cols=("mid_balls", "mid_economy", "mid_wickets"),
        extra="Spin", title="Spin bowlers with a large middle-over sample",
    ),
}  # fmt: skip


def clean(v):
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    if v is pd.NA or v is None:
        return None
    return v


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def retention(con) -> dict:
    t = con.execute(
        "select count(*) from information_schema.tables where table_name='p7_retention_rows'"
    ).fetchone()[0]
    if not t:
        return dict(list_received=False, retained_ids=[], status={}, rows=0)
    n = con.execute("select count(*) from p7_retention_rows").fetchone()[0]
    if n == 0:
        return dict(list_received=False, retained_ids=[], status={}, rows=0)
    df = con.execute(
        "select player_id, status from p7_retention_rows where player_id is not null"
    ).fetchdf()
    return dict(
        list_received=True,
        retained_ids=sorted(int(x) for x in df[df.status == "RETAINED"].player_id),
        status={int(r.player_id): r.status for r in df.itertuples()},
        rows=int(n),
    )


def candidates(ret: dict, min_balls: int) -> dict:
    squad = pd.read_csv(SQUAD, encoding="utf-8")
    snap = {str(r.player).strip().casefold(): r.team_name for r in squad.itertuples()}
    out = {}
    for key, rule in CANDIDATE_RULES.items():
        f = "descriptive_batter_profiles.csv" if rule["side"] == "batter" else "descriptive_bowler_profiles.csv"
        p = pd.read_csv(REPORTS / f)
        p = p[p["format"] == "IPL"]
        if rule["extra"]:
            p = p[p["pace_or_spin_modal"] == rule["extra"]]
        for c in rule["need"]:
            p = p[p[c] >= min_balls]
        p = p[~p["player_id"].isin(ret["retained_ids"])]
        p = p.sort_values("player_name")  # alphabetical: not a ranking
        keep = ["player_id", "player_name", *rule["cols"], "matches_played", "sample_sufficiency"]
        t = p[keep].copy()
        t["squad_snapshot_team"] = [snap.get(str(n).strip().casefold(), "not matched") for n in p["player_name"]]
        t["availability"] = [ret["status"].get(int(i), "UNKNOWN") for i in p["player_id"]]
        out[key] = dict(
            title=rule["title"], min_balls=min_balls, n=int(len(t)), rows=records(t),
            ordering="alphabetical by player name; not a ranking",
        )  # fmt: skip
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-min-balls", type=int, default=250)
    args = ap.parse_args()
    con = duckdb.connect(str(DB / "exploratory.duckdb"), read_only=True)
    con.execute(f"attach '{(DB / 'superr.duckdb').as_posix()}' as o (read_only)")
    rr_id = int(con.execute("select team_id from o.teams where team_name = ?", [TEAM_NAME]).fetchone()[0])

    results = con.execute(
        f"""select c.season::varchar season, count(*) n, sum((m.win_team_id={rr_id})::int) wins,
        sum((m.result_status <> 'COMPLETED')::int) not_completed, sum(m.has_deliveries::int) with_deliveries
        from o.matches m join o.competitions c using(comp_id)
        where m.competition_type='IPL' and (m.home_team_id={rr_id} or m.away_team_id={rr_id})
        group by 1 order by 1"""
    ).fetchdf()
    ko = con.execute(
        f"""select c.season::varchar season, m.stage, m.match_number, cast(m.match_date as date)::varchar match_date,
        m.home_team, m.away_team, m.result from o.matches m join o.competitions c using(comp_id)
        where m.competition_type='IPL' and m.knock_out and (m.home_team_id={rr_id} or m.away_team_id={rr_id})
        order by m.match_date"""
    ).fetchdf()
    ipl_ko_all = con.execute(
        """select c.season::varchar season, m.stage, count(*) n from o.matches m join o.competitions c using(comp_id)
        where m.competition_type='IPL' and m.knock_out group by 1,2 order by 1,2"""
    ).fetchdf()

    quality = dict(
        ipl_deliveries=int(con.execute("select count(*) from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL'").fetchone()[0]),
        pace_or_spin_null=int(con.execute("select count(*) from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' and (d.pace_or_spin is null or d.bowling_type is null)").fetchone()[0]),
        pace_or_spin_values=con.execute("select pace_or_spin v, count(*) n from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' group by 1 order by 1").fetchdf().to_dict("records"),
        bowling_types_by_class=con.execute("select pace_or_spin, count(distinct bowling_type) n_types from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' group by 1").fetchdf().to_dict("records"),
        type_class_conflicts=int(con.execute("select count(*) from (select bowling_type from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' group by 1 having count(distinct pace_or_spin)>1)").fetchone()[0]),
        bowlers_with_more_than_one_type=int(con.execute("select count(*) from (select bowler_id from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' group by 1 having count(distinct bowling_type)>1)").fetchone()[0]),
        bowl_speed_zero_or_negative=int(con.execute("select count(*) from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' and bowl_speed<=0").fetchone()[0]),
        bowl_speed_above_200=int(con.execute("select count(*) from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' and bowl_speed>200").fetchone()[0]),
        mean_speed_pace_spin=con.execute("select pace_or_spin, round(avg(bowl_speed),1) mean_kmh from o.deliveries d join o.matches m using(match_id) where m.competition_type='IPL' and bowl_speed between 40 and 170 group by 1").fetchdf().to_dict("records"),
    )  # fmt: skip

    frame = rr.prepare(con.execute(rr.IPL_SQL).fetchdf())
    frame["season"] = frame["season"].astype(str)
    scope = dict(
        rows=int(len(frame)),
        matches=int(frame["match_id"].nunique()),
        matches_by_season=frame.groupby("season")["match_id"].nunique().to_dict(),
    )
    in_frame = set(frame["match_id"].unique())
    excl = con.execute(
        """select m.match_id, c.season::varchar season, cast(m.match_date as date)::varchar match_date,
        m.home_team, m.away_team, m.result from o.matches m join o.competitions c using(comp_id)
        where m.competition_type='IPL' and m.has_deliveries order by m.match_date"""
    ).fetchdf()
    excl = excl[~excl["match_id"].isin(in_frame)]
    cmp = rr.compare(frame, rr_id)
    depth = rr.bowler_depth(frame, rr_id)
    ret = retention(con)
    cand = candidates(ret, args.candidate_min_balls)

    doc = dict(
        version="rr_analysis_v1",
        descriptive_only=True,
        team=dict(team_id=rr_id, team_name=TEAM_NAME),
        seed=rr.SEED, n_boot=rr.N_BOOT, ci_level=rr.LEVEL, min_rr_balls=rr.MIN_BALLS,
        primary_window=rr.PRIMARY,
        scope=scope,
        scope_rule="IPL, regulation innings 1-2, DLS-affected rows excluded, rows with a phase label",
        provenance=dict(
            official_db_sha256=sha(DB / "superr.duckdb"),
            analytical_store_sha256=sha(DB / "exploratory.duckdb"),
            squad_snapshot_sha256=sha(SQUAD),
        ),
        excluded_matches_with_deliveries=records(excl),
        season_results=records(results),
        knockout_matches=records(ko),
        ipl_knockout_counts=records(ipl_ko_all),
        data_quality=quality,
        comparisons=records(cmp),
        bowler_depth=records(depth),
        retention=dict(list_received=ret["list_received"], rows=ret["rows"], retained_excluded=len(ret["retained_ids"])),
        candidate_fit_tables=cand,
        candidate_statement="Descriptive candidate-fit tables, not recommendations. Availability is UNKNOWN unless an authoritative retention row says otherwise.",
    )  # fmt: skip
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, "metrics", cmp["metric"].nunique(), 