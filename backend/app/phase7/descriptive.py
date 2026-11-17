"""Descriptive batter and bowler profile builder (Phase 7, chunk 2).

Everything here is a plain count or ratio over official ball-by-ball rows. The definitions are the
verified Phase 2.5 / Phase 4 ones (``den_*`` columns of ``exp_pre_delivery_state``): a ball faced
excludes wides and the Penalty row, a legal ball excludes wides, no-balls (``Overstep``), ``other``
and the Penalty row, bowler-charged runs and bowler-credited wickets are the stored ``den_*``
values. Rows of innings 3 and 4 (super overs), TEST-period matches and out-of-scope competitions
(OTHER_T20) are never read. DLS-affected rows are NOT excluded (same as ``p4_player_stats``) and
are counted per player so the reader can see them.

There is no composite score and no ordering. Missing values stay empty with a reason.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.core.config import BACKEND_ROOT

CONFIG_PATH = BACKEND_ROOT / "config" / "phase7_descriptive_v1.json"
REPORTS = BACKEND_ROOT / "data" / "reports"
OFFICIAL_DB = BACKEND_ROOT / "data" / "database" / "superr.duckdb"
EXPLORATORY_DB = BACKEND_ROOT / "data" / "database" / "exploratory.duckdb"

BATTER_CSV = "descriptive_batter_profiles.csv"
BOWLER_CSV = "descriptive_bowler_profiles.csv"
PER_MATCH_CSV = "phase7_descriptive_player_match.csv"
MANIFEST_JSON = "phase7_descriptive_manifest.json"
CONTEXT_JSON = "phase7_descriptive_context.json"

PHASES = (("pp", "powerplay"), ("mid", "middle"), ("death", "death"))
INNINGS_SPLITS = (("inn1", 1), ("chase", 2))
BAT_OPP = (("vs_pace", "Pace"), ("vs_spin", "Spin"))
BOWL_OPP = (("vs_rhb", "RHB"), ("vs_lhb", "LHB"))

FRAME_SQL = """
SELECT s.match_id, s.innings_number, s.innings_ball_num, s.competition_type AS format,
       s.season_label, s.match_date, s.striker_id, s.bowler_id, s.innings_phase, s.dls_flag,
       s.den_wicket_flag_anomaly, s.out_extras_type, s.den_extras_label_unverified,
       s.out_batter_runs, s.out_is_four, s.out_is_six, s.out_is_wicket,
       s.out_dismissed_player_id, s.out_runs_row, s.den_legal_inc, s.den_counts_as_ball_faced,
       s.den_bowler_counts_row, s.den_bowler_charged_runs, s.den_bowler_credited_wicket,
       s.state_version
FROM exp_pre_delivery_state s
JOIN p4_match_period p USING (match_id)
WHERE s.competition_type IN ('IPL', 'T20I')
  AND s.innings_number IN (1, 2)
  AND s.format_out_of_scope = FALSE
  AND p.period <> 'TEST'
"""


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------- inputs
def load_frame(store: Path | str = EXPLORATORY_DB, official: Path | str = OFFICIAL_DB):
    """In-scope delivery rows (TEST periods and innings 3-4 filtered in SQL) plus bowler type
    and batter hand from the official deliveries, joined on the delivery key."""
    e = duckdb.connect(str(store), read_only=True)
    try:
        df = e.execute(FRAME_SQL).df()
    finally:
        e.close()
    o = duckdb.connect(str(official), read_only=True)
    try:
        dl = o.execute(
            "SELECT match_id, innings_number, innings_ball_num, pace_or_spin, batting_type, "
            "bowling_type FROM deliveries WHERE innings_number IN (1, 2)"
        ).df()
    finally:
        o.close()
    key = ["match_id", "innings_number", "innings_ball_num"]
    if dl.duplicated(key).any():
        raise ValueError("delivery key is not unique in the official deliveries")
    n = len(df)
    df = df.merge(dl, on=key, how="left", validate="one_to_one")
    if len(df) != n:
        raise ValueError("delivery join changed the row count")
    return df


def load_reference(store: Path | str = EXPLORATORY_DB, official: Path | str = OFFICIAL_DB):
    """Player names and mapping flags, classification, matches played, context-sample counts."""
    o = duckdb.connect(str(official), read_only=True)
    try:
        players = o.execute(
            "SELECT player_id, player_name, in_mapping, in_playing_eleven, in_deliveries, "
            "shares_name_with_other_id FROM players"
        ).df()
        played = o.execute(
            "SELECT DISTINCT s.player_id, s.match_id, m.competition_type AS format "
            "FROM match_squads s JOIN matches m USING (match_id) "
            "WHERE s.is_played AND m.competition_type IN ('IPL', 'T20I')"
        ).df()
    finally:
        o.close()
    e = duckdb.connect(str(store), read_only=True)
    try:
        cls = e.execute(
            "SELECT player_id, squad_role, nationality, nationality_verification, "
            "international_status, international_status_verification, conflict_flag "
            "FROM p5_player_classification"
        ).df()
        periods = e.execute("SELECT match_id, period FROM p4_match_period").df()
        ctx = e.execute(
            "SELECT player_id, comp AS format, role, sum(n) AS context_sample_balls, "
            "count(DISTINCT match_id) AS context_sample_matches "
            "FROM p5_context_stats WHERE period <> 'TEST' GROUP BY 1, 2, 3"
        ).df()
    finally:
        e.close()
    played = played.merge(periods, on="match_id")
    played = played[played["period"] != "TEST"]
    mp = played.groupby(["player_id", "format"]).size().rename("matches_played").reset_index()
    return {"players": players, "classification": cls, "matches_played": mp, "context": ctx}


# ----------------------------------------------------------------------------- row level
def prepare_batting(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["striker_id"].notna()].copy()
    runs = d["out_batter_runs"]
    boundary = d["out_is_four"].fillna(False).astype(bool) | d["out_is_six"].fillna(False).astype(
        bool
    )
    out = pd.DataFrame(
        {
            "player_id": d["striker_id"].astype("int64"),
            "format": d["format"],
            "match_id": d["match_id"],
            "innings_number": d["innings_number"],
            "season_label": d["season_label"],
            "innings_phase": d["innings_phase"],
            "opponent": d["pace_or_spin"],
            "balls": d["den_counts_as_ball_faced"].fillna(0).astype("int64"),
            "runs": runs,
            "outs": (
                d["out_is_wicket"].fillna(False).astype(bool)
                & (d["out_dismissed_player_id"] == d["striker_id"]).fillna(False).astype(bool)
            ).astype("int64"),
            "fours": d["out_is_four"].fillna(False).astype(bool).astype("int64"),
            "sixes": d["out_is_six"].fillna(False).astype(bool).astype("int64"),
            "boundary_runs": runs.where(boundary, 0),
            "dots": (
                ((d["den_counts_as_ball_faced"] == 1) & (runs == 0)).fillna(False).astype("int64")
            ),
            "dls_rows": d["dls_flag"].fillna(False).astype(bool).astype("int64"),
            "anomaly_rows": d["den_wicket_flag_anomaly"].fillna(False).astype(bool).astype("int64"),
            "extras_other_rows": (d["out_extras_type"] == "other").fillna(False).astype("int64"),
        }
    )
    return out


def prepare_bowling(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["bowler_id"].notna()].copy()
    counted = (d["den_bowler_counts_row"].fillna(0) == 1).astype(bool)
    boundary = d["out_is_four"].fillna(False).astype(bool) | d["out_is_six"].fillna(False).astype(
        bool
    )
    bat_runs = d["out_batter_runs"]
    out = pd.DataFrame(
        {
            "player_id": d["bowler_id"].astype("int64"),
            "format": d["format"],
            "match_id": d["match_id"],
            "innings_number": d["innings_number"],
            "season_label": d["season_label"],
            "innings_phase": d["innings_phase"],
            "opponent": d["batting_type"],
            "bowling_type": d["bowling_type"],
            "pace_or_spin": d["pace_or_spin"],
            "balls": d["den_legal_inc"].fillna(0).astype("int64"),
            "runs": d["den_bowler_charged_runs"],
            "outs": d["den_bowler_credited_wicket"].fillna(0).astype("int64"),
            "fours": (counted & d["out_is_four"].fillna(False).astype(bool)).astype("int64"),
            "sixes": (counted & d["out_is_six"].fillna(False).astype(bool)).astype("int64"),
            "boundary_runs": bat_runs.where(counted & boundary, 0),
            "dots": ((d["den_legal_inc"] == 1) & (d["out_runs_row"] == 0))
            .fillna(False)
            .astype("int64"),
            "wides": (d["out_extras_type"] == "wide").fillna(False).astype("int64"),
            "no_balls": (d["out_extras_type"] == "Overstep").fillna(False).astype("int64"),
            "extras_charged_runs": (d["den_bowler_charged_runs"] - bat_runs).where(counted, 0),
            "dls_rows": d["dls_flag"].fillna(False).astype(bool).astype("int64"),
            "anomaly_rows": d["den_wicket_flag_anomaly"].fillna(False).astype(bool).astype("int64"),
            "extras_other_rows": (d["out_extras_type"] == "other").fillna(False).astype("int64"),
        }
    )
    return out


SUM_COLS = ("balls", "runs", "outs", "fours", "sixes", "boundary_runs", "dots")


def _sum(d: pd.DataFrame, keys: list[str], cols: tuple[str, ...]) -> pd.DataFrame:
    return d.groupby(keys, sort=True)[list(cols)].sum(min_count=1).reset_index()


def per_match_table(rows: pd.DataFrame, side: str) -> pd.DataFrame:
    """One row per (side, player, format, match): the inputs of the match-cluster bootstrap."""
    g = _sum(rows, ["player_id", "format", "match_id"], SUM_COLS)
    g.insert(0, "side", side)
    return g


# ----------------------------------------------------------------------------- statistics
def ratio(num: pd.Series, den: pd.Series, scale: float = 1.0) -> pd.Series:
    """num / den * scale; empty (NaN) when the denominator is 0 or missing, never 0."""
    d = den.where(den > 0)
    return (num.astype("float64") / d.astype("float64")) * scale


def bootstrap_values(
    num: np.ndarray,
    den: np.ndarray,
    seed_parts: tuple[int, ...],
    n_boot: int,
    scale: float = 1.0,
) -> np.ndarray:
    """Match-cluster bootstrap draws of ``sum(num) / sum(den) * scale`` (NaN where den is 0).

    Per-match numerators and denominators are resampled with replacement (multinomial counts)."""
    m = len(num)
    rng = np.random.default_rng(np.random.SeedSequence([int(x) for x in seed_parts]))
    counts = rng.multinomial(m, np.full(m, 1.0 / m), size=n_boot).astype("float64")
    nb = counts @ np.asarray(num, dtype="float64")
    db = counts @ np.asarray(den, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(db > 0, nb / np.where(db > 0, db, 1.0) * scale, np.nan)


def percentile_interval(
    vals: np.ndarray, level: float, max_undefined_share: float
) -> tuple[float | None, float | None, str | None]:
    ok = ~np.isnan(vals)
    if (~ok).mean() > max_undefined_share:
        return None, None, "UNDEFINED_IN_MANY_RESAMPLES"
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(vals[ok], [a, 1.0 - a])
    return float(lo), float(hi), None


def bootstrap_ratio(
    num: np.ndarray,
    den: np.ndarray,
    seed_parts: tuple[int, ...],
    n_boot: int,
    level: float,
    scale: float = 1.0,
    max_undefined_share: float = 0.05,
) -> tuple[float | None, float | None, str | None]:
    """Percentile interval of the bootstrap draws; ``reason`` is set when none is reported."""
    if len(num) < 2:
        return None, None, "FEWER_THAN_2_MATCHES"
    vals = bootstrap_values(num, den, seed_parts, n_boot, scale)
    return percentile_interval(vals, level, max_undefined_share)


FORMAT_CODE = {"IPL": 1, "T20I": 2}


def _ci_columns(
    pm: pd.DataFrame, num_col: str, den_col: str, scale: float, cfg: dict[str, Any], side_code: int
) -> pd.DataFrame:
    b = cfg["bootstrap"]
    out = []
    for (pid, fmt), g in pm.groupby(["player_id", "format"], sort=True):
        if len(g) < b["min_matches"]:
            out.append((pid, fmt, None, None, f"FEWER_THAN_{b['min_matches']}_MATCHES"))
            continue
        lo, hi, why = bootstrap_ratio(
            g[num_col].to_numpy(),
            g[den_col].to_numpy(),
            (b["seed"], int(pid), FORMAT_CODE[fmt], side_code, 0),
            b["n_boot"],
            b["level"],
            scale,
            b["max_undefined_share"],
        )
        out.append((pid, fmt, lo, hi, why))
    res = pd.DataFrame(out, columns=["player_id", "format", "ci_low", "ci_high", "ci_reason"])
    res[["ci_low", "ci_high"]] = res[["ci_low", "ci_high"]].astype("float64")
    return res


def _split_block(rows: pd.DataFrame, mask: pd.Series, prefix: str, side: str) -> pd.DataFrame:
    t = _sum(rows[mask], ["player_id", "format"], ("balls", "runs", "outs"))
    t = t.rename(
        columns={
            "balls": f"{prefix}_balls",
            "runs": f"{prefix}_runs",
            "outs": f"{prefix}_dismissals" if side == "batter" else f"{prefix}_wickets",
        }
    )
    rate = f"{prefix}_strike_rate" if side == "batter" else f"{prefix}_economy"
    t[rate] = ratio(t[f"{prefix}_runs"], t[f"{prefix}_balls"], 100.0 if side == "batter" else 6.0)
    return t


def _joined_seasons(rows: pd.DataFrame) -> pd.DataFrame:
    s = (
        rows.dropna(subset=["season_label"])
        .groupby(["player_id", "format"])["season_label"]
        .apply(lambda x: ";".join(sorted(set(map(str, x)))))
        .rename("seasons_covered")
        .reset_index()
    )
    return s


def build_side(
    rows: pd.DataFrame,
    side: str,
    ref: dict[str, pd.DataFrame],
    cfg: dict[str, Any],
    provenance: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Profile table and per-match table for one side ('batter' or 'bowler')."""
    keys = ["player_id", "format"]
    tot = _sum(rows, keys, SUM_COLS)
    inn = rows.assign(_i=rows["match_id"] * 10 + rows["innings_number"])
    counts = (
        inn.groupby(keys)
        .agg(
            matches_with_participation=("match_id", "nunique"),
            opportunities_innings=("_i", "nunique"),
        )
        .reset_index()
    )
    tot = tot.merge(counts, on=keys, how="left")
    flags = (
        rows.groupby(keys)[["dls_rows", "anomaly_rows", "extras_other_rows"]].sum().reset_index()
    )
    tot = tot.merge(flags, on=keys, how="left")
    tot = tot.merge(_joined_seasons(rows), on=keys, how="left")
    is_bat = side == "batter"
    sc = 100.0 if is_bat else 6.0
    main_rate = "strike_rate" if is_bat else "economy"
    tot[main_rate] = ratio(tot["runs"], tot["balls"], sc)
    outs_name = "dismissals" if is_bat else "wickets"
    tot = tot.rename(columns={"outs": outs_name})
    tot["balls_per_" + ("dismissal" if is_bat else "wicket")] = ratio(tot["balls"], tot[outs_name])
    if is_bat:
        tot["average"] = ratio(tot["runs"], tot[outs_name])
        tot["boundary_run_share"] = ratio(tot["boundary_runs"], tot["runs"])
        tot["boundary_ball_share"] = ratio(tot["fours"] + tot["sixes"], tot["balls"])
    else:
        tot["boundary_conceded_share"] = ratio(tot["fours"] + tot["sixes"], tot["balls"])
        tot["overs"] = (
            (tot["balls"] // 6).astype("Int64").astype(str) + "." + (tot["balls"] % 6).astype(str)
        )
    tot["dot_ball_share"] = ratio(tot["dots"], tot["balls"])
    if not is_bat:
        ex = _sum(rows, keys, ("wides", "no_balls", "extras_charged_runs"))
        tot = tot.merge(ex, on=keys, how="left")
    # splits
    ph = rows["innings_phase"]
    for pref, label in PHASES:
        tot = tot.merge(_split_block(rows, ph == label, pref, side), on=keys, how="left")
    for pref, n in INNINGS_SPLITS:
        tot = tot.merge(
            _split_block(rows, rows["innings_number"] == n, pref, side), on=keys, how="left"
        )
    opp = BAT_OPP if is_bat else BOWL_OPP
    for pref, label in opp:
        tot = tot.merge(
            _split_block(rows, rows["opponent"] == label, pref, side), on=keys, how="left"
        )
    # a split with no balls is "not observed", not zero runs / zero outs
    for pref in [p for p, _ in PHASES] + [p for p, _ in INNINGS_SPLITS] + [p for p, _ in opp]:
        b = pref + "_balls"
        tot[b] = tot[b].fillna(0).astype("int64")
        for c in tot.columns:
            if c.startswith(pref + "_") and c != b:
                tot.loc[tot[b] == 0, c] = np.nan
    # uncertainty
    pm = per_match_table(rows, side)
    ci = _ci_columns(pm, "runs", "balls", sc, cfg, 1 if is_bat else 2)
    ci = ci.rename(
        columns={
            "ci_low": f"{main_rate}_ci_low",
            "ci_high": f"{main_rate}_ci_high",
            "ci_reason": f"{main_rate}_ci_unavailable_reason",
        }
    )
    tot = tot.merge(ci, on=keys, how="left")
    tot[f"{main_rate}_ci_method"] = (
        f"match-cluster bootstrap, {cfg['bootstrap']['n_boot']} draws, seed {cfg['bootstrap']['seed']}, "
        f"{int(cfg['bootstrap']['level'] * 100)}% percentile"
    )
    # identity, classification, mapping
    tot = tot.merge(ref["players"][["player_id", "player_name"]], on="player_id", how="left")
    tot = tot.merge(ref["matches_played"], on=keys, how="left")
    c = ref["classification"].drop(columns=["conflict_flag"])
    tot = tot.merge(c, on="player_id", how="left")
    tot = tot.rename(columns={"squad_role": "squad_role_listed"})
    ctxs = ref["context"]
    ctxs = ctxs[ctxs["role"] == side].drop(columns=["role"])
    tot = tot.merge(ctxs, on=keys, how="left")
    tot["context_sample_balls"] = tot["context_sample_balls"].fillna(0).astype("int64")
    tot["context_sample_matches"] = tot["context_sample_matches"].fillna(0).astype("int64")
    tot["context_sample_label"] = cfg["context_sample"]["label"]
    tot["context_definition"] = (
        f"{cfg['context_sample']['definition_id']} {cfg['context_sample']['definition_label']}"
    )
    # sample flags and warnings
    low = cfg["display_sample_convention"][f"low_sample_balls_{side}"]
    tot["sample_sufficiency"] = np.where(
        tot["balls"] == 0, "NO_BALLS", np.where(tot["balls"] < low, "LOW_SAMPLE", "OK")
    )
    tot["sample_note"] = np.where(
        tot["balls"] < low,
        f"fewer than {low} {'balls faced' if is_bat else 'legal balls bowled'}; display flag only",
        None,
    )
    tot["missing_value_notes"] = _missing_notes(tot, side)
    tot["mapping_warnings"] = _mapping_warnings(tot, ref)
    tot["caveat_dls"] = "DLS-affected rows are not excluded from these totals; see dls_rows"
    tot["descriptive_version"] = cfg["version"]
    tot["window"] = cfg["window"]
    for k, v in provenance.items():
        tot[k] = v
    return tot, pm


def _missing_notes(t: pd.DataFrame, side: str) -> pd.Series:
    out = []
    is_bat = side == "batter"
    out_col = "dismissals" if is_bat else "wickets"
    for r in t.itertuples(index=False):
        notes = []
        if r.balls == 0:
            notes.append("rates:NO_BALLS_OBSERVED")
        if r.balls > 0 and getattr(r, out_col) == 0:
            notes.append(("average" if is_bat else "balls_per_wicket") + ":NO_" + out_col.upper())
            if is_bat:
                notes.append("balls_per_dismissal:NO_DISMISSALS")
        for pref, _ in PHASES + INNINGS_SPLITS + (BAT_OPP if is_bat else BOWL_OPP):
            if getattr(r, pref + "_balls") == 0:
                notes.append(f"{pref}:NO_BALLS_IN_SPLIT")
        out.append(";".join(notes) if notes else None)
    return pd.Series(out, index=t.index, dtype="object")


def _mapping_warnings(t: pd.DataFrame, ref: dict[str, pd.DataFrame]) -> pd.Series:
    p = ref["players"].set_index("player_id")
    conflict = ref["classification"].set_index("player_id")["conflict_flag"]
    out = []
    for r in t.itertuples(index=False):
        w = []
        pid = r.player_id
        if pid not in p.index:
            w.append("PLAYER_ID_NOT_IN_PLAYERS_TABLE")
        else:
            row = p.loc[pid]
            if bool(row["shares_name_with_other_id"]):
                w.append("NAME_SHARED_WITH_OTHER_PLAYER_ID")
            if not bool(row["in_mapping"]):
                w.append("NOT_IN_COMPETITION_MAPPING")
            if not bool(row["in_playing_eleven"]):
                w.append("NOT_IN_PLAYING_ELEVEN_FILE")
        if pd.isna(r.nationality):
            w.append("NO_CLASSIFICATION_ROW")
        else:
            if str(r.nationality).upper() == "UNKNOWN":
                w.append("NATIONALITY_UNKNOWN")
            if str(r.international_status).upper() == "UNKNOWN":
                w.append("INTERNATIONAL_STATUS_UNKNOWN")
            if bool(conflict.get(pid, False)):
                w.append("CLASSIFICATION_CONFLICT_SEE_INTERNAL")
        if pd.isna(r.matches_played):
            w.append("NO_PLAYED_FLAG_IN_SQUAD_DATA")
        out.append(";".join(w) if w else None)
    return pd.Series(out, index=t.index, dtype="object")


def participation_roles(bat: pd.DataFrame, bowl: pd.DataFrame) -> pd.Series:
    b = bat.groupby("player_id")["balls"].sum()
    w = bowl.groupby("player_id")["balls"].sum()
    ids = sorted(set(b.index) | set(w.index))
    out = {}
    for i in ids:
        hb, hw = b.get(i, 0) > 0, w.get(i, 0) > 0
        out[i] = (
            "BATS_AND_BOWLS"
            if hb and hw
            else "BATS_ONLY"
            if hb
            else "BOWLS_ONLY"
            if hw
            else "NO_BALLS_FACED_OR_BOWLED"
        )
    return pd.Series(out, name="participation_role")


IDENT = [
    "player_id",
    "player_name",
    "format",
    "participation_role",
    "squad_role_listed",
    "nationality",
    "nationality_verification",
    "international_status",
    "international_status_verification",
    "seasons_covered",
    "matches_played",
    "matches_with_participation",
    "opportunities_innings",
]


def _order(df: pd.DataFrame, first: list[str]) -> pd.DataFrame:
    rest = [c for c in df.columns if c not in first]
    return df[first + rest]


def build_profiles(
    frame: pd.DataFrame,
    ref: dict[str, pd.DataFrame],
    cfg: dict[str, Any],
    provenance: dict[str, str],
) -> dict[str, pd.DataFrame]:
    bat_rows = prepare_batting(frame)
    bowl_rows = prepare_bowling(frame)
    roles = participation_roles(bat_rows, bowl_rows)
    batters, pm_bat = build_side(bat_rows, "batter", ref, cfg, provenance)
    bowlers, pm_bowl = build_side(bowl_rows, "bowler", ref, cfg, provenance)
    # modal bowling style from actual deliveries
    style = (
        bowl_rows.dropna(subset=["bowling_type"])
        .groupby(["player_id", "format", "bowling_type"])["balls"]
        .size()
        .reset_index(name="n")
    )
    if len(style):
        style = style.sort_values(
            ["player_id", "format", "n", "bowling_type"], ascending=[True, True, False, True]
        )
        tot_n = style.groupby(["player_id", "format"])["n"].transform("sum")
        top = style.groupby(["player_id", "format"]).head(1).copy()
        top["bowling_style_modal_share"] = top["n"] / tot_n.loc[top.index]
        top = top.rename(columns={"bowling_type": "bowling_style_modal"}).drop(columns="n")
        bowlers = bowlers.merge(top, on=["player_id", "format"], how="left")
        ps = (
            bowl_rows.dropna(subset=["pace_or_spin"])
            .groupby(["player_id", "format"])["pace_or_spin"]
            .agg(lambda x: x.value_counts().sort_index().index[0] if len(x) else None)
            .rename("pace_or_spin_modal")
            .reset_index()
        )
        bowlers = bowlers.merge(ps, on=["player_id", "format"], how="left")
    for df in (batters, bowlers):
        df["participation_role"] = df["player_id"].map(roles)
    batters = batters.rename(columns={"balls": "balls_faced"})
    bowlers = bowlers.rename(
        columns={"balls": "legal_balls", "runs": "runs_conceded", "dots": "dot_balls"}
    )
    batters = batters.rename(columns={"dots": "dot_balls"})
    batters = _order(batters, IDENT)
    bowlers = _order(bowlers, IDENT)
    batters = batters.sort_values(["player_id", "format"]).reset_index(drop=True)
    bowlers = bowlers.sort_values(["player_id", "format"]).reset_index(drop=True)
    pm = pd.concat([pm_bat, pm_bowl], ignore_index=True)
    dates = frame.groupby("match_id")["match_date"].first().dt.strftime("%Y-%m-%d")
    pm.insert(4, "match_date", pm["match_id"].map(dates))
    pm = pm.sort_values(["side", "player_id", "format", "match_id"]).reset_index(drop=True)
    return {"batters": batters, "bowlers": bowlers, "per_match": pm}


_RATIO_NAME = re.compile(r"(rate|share|average|economy|_ci_low|_ci_high|per_|overs)")


def write_csv(df: pd.DataFrame, path: Path) -> str:
    """Sorted, rounded, UTF-8 CSV with empty cells for missing values. Returns the sha256."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            s = out[c]
            nn = s.dropna()
            if not _RATIO_NAME.search(c) and (nn == nn.round()).all():
                out[c] = s.astype("Int64")
            else:
                out[c] = s.round(6)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return sha256_file(path)
