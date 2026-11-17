"""Read-side logic of the public descriptive endpoints (Phase 7).

Reads the generated CSVs and the context JSON from ``data/reports`` (no database access, no
recomputation of pressure figures). Nothing here orders players by performance, assigns a score or
declares one player better than another.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase7 import descriptive as ds

PM_CODE = {"batter": 1, "bowler": 2}
SORT_COLUMNS = ("player_name", "player_id", "matches_played", "volume")
LIMITATIONS = (
    "Descriptive counts and rates only; they do not control for opposition, venue, match "
    "situation or role in the batting order.",
    "The interval treats matches as independent draws and ignores how the matches were chosen.",
    "A difference in a rate is not evidence about performance under pressure.",
    "DLS-affected rows are included in the totals and counted per player.",
    "Players with few balls have wide intervals or none; low-sample flags are display flags only.",
)


class NotFound(LookupError):
    pass


class BadRequest(ValueError):
    pass


def clean(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float | np.floating):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if v is pd.NA or v is pd.NaT:
        return None
    return v


def _split(s: Any) -> list[str]:
    s = clean(s)
    return [x for x in str(s).split(";") if x] if s else []


class DescriptiveData:
    def __init__(self, reports: Path | str = ds.REPORTS, config: Path | str = ds.CONFIG_PATH):
        r = Path(reports)
        self.cfg = ds.load_config(config)
        self.batters = pd.read_csv(r / ds.BATTER_CSV, dtype={"overs": str})
        self.bowlers = pd.read_csv(r / ds.BOWLER_CSV, dtype={"overs": str})
        self.per_match = pd.read_csv(r / ds.PER_MATCH_CSV)
        self.context = json.loads((r / ds.CONTEXT_JSON).read_text(encoding="utf-8"))
        h = hashlib.sha256()
        for name in (ds.BATTER_CSV, ds.BOWLER_CSV, ds.PER_MATCH_CSV, ds.CONTEXT_JSON):
            h.update((r / name).read_bytes())
        h.update(Path(config).read_bytes())
        self.version = h.hexdigest()
        self.model_version = self.cfg["version"]

    def side_frame(self, side: str) -> pd.DataFrame:
        return self.batters if side == "batter" else self.bowlers


# ----------------------------------------------------------------------------- profiles
def _splits(row: pd.Series, side: str) -> list[dict[str, Any]]:
    is_bat = side == "batter"
    out_suffix = "dismissals" if is_bat else "wickets"
    rate_suffix = "strike_rate" if is_bat else "economy"
    labels = {
        "pp": "Powerplay overs",
        "mid": "Middle overs",
        "death": "Death overs",
        "inn1": "First innings",
        "chase": "Chase (second innings)",
        "vs_pace": "Against pace bowling",
        "vs_spin": "Against spin bowling",
        "vs_rhb": "Against right-hand batters",
        "vs_lhb": "Against left-hand batters",
    }
    prefixes = [p for p, _ in ds.PHASES] + [p for p, _ in ds.INNINGS_SPLITS]
    prefixes += [p for p, _ in (ds.BAT_OPP if is_bat else ds.BOWL_OPP)]
    res = []
    for p in prefixes:
        balls = clean(row[f"{p}_balls"])
        res.append(
            {
                "key": p,
                "label": labels[p],
                "balls": None if balls is None else int(balls),
                "runs": None if clean(row[f"{p}_runs"]) is None else int(row[f"{p}_runs"]),
                "outs": None
                if clean(row[f"{p}_{out_suffix}"]) is None
                else int(row[f"{p}_{out_suffix}"]),
                "rate": clean(row[f"{p}_{rate_suffix}"]),
                "rate_name": rate_suffix,
                "unavailable_reason": "NO_BALLS_IN_SPLIT" if not balls else None,
            }
        )
    return res


def _int(v: Any) -> int | None:
    v = clean(v)
    return None if v is None else int(v)


def profile_dict(row: pd.Series, side: str) -> dict[str, Any]:
    is_bat = side == "batter"
    main = "strike_rate" if is_bat else "economy"
    d: dict[str, Any] = {
        "player_id": int(row["player_id"]),
        "player_name": clean(row["player_name"]),
        "side": side,
        "format": row["format"],
        "participation_role": clean(row["participation_role"]),
        "squad_role_listed": clean(row["squad_role_listed"]),
        "nationality": clean(row["nationality"]),
        "nationality_verification": clean(row["nationality_verification"]),
        "international_status": clean(row["international_status"]),
        "international_status_verification": clean(row["international_status_verification"]),
        "seasons_covered": _split(row["seasons_covered"]),
        "matches_played": _int(row["matches_played"]),
        "matches_with_participation": int(row["matches_with_participation"]),
        "opportunities_innings": int(row["opportunities_innings"]),
        "fours": int(row["fours"]),
        "sixes": int(row["sixes"]),
        "boundary_runs": _int(row["boundary_runs"]),
        "dot_balls": int(row["dot_balls"]),
        "dot_ball_share": clean(row["dot_ball_share"]),
        "ci_low": clean(row[f"{main}_ci_low"]),
        "ci_high": clean(row[f"{main}_ci_high"]),
        "ci_metric": main,
        "ci_unavailable_reason": clean(row[f"{main}_ci_unavailable_reason"]),
        "ci_method": row[f"{main}_ci_method"],
        "splits": _splits(row, side),
        "context_sample": {
            "balls": int(row["context_sample_balls"]),
            "matches": int(row["context_sample_matches"]),
            "label": row["context_sample_label"],
            "definition": row["context_definition"],
        },
        "quality": {
            "sample_sufficiency": row["sample_sufficiency"],
            "sample_note": clean(row["sample_note"]),
            "dls_rows": int(row["dls_rows"]),
            "anomaly_rows": int(row["anomaly_rows"]),
            "extras_other_rows": int(row["extras_other_rows"]),
            "missing_value_notes": _split(row["missing_value_notes"]),
            "mapping_warnings": _split(row["mapping_warnings"]),
            "caveat_dls": row["caveat_dls"],
        },
        "provenance": {
            "descriptive_version": row["descriptive_version"],
            "window": row["window"],
            "state_version": str(row["state_version"]),
            "official_db_sha256": row["official_db_sha256"],
            "analytical_store_sha256": row["analytical_store_sha256"],
        },
    }
    if is_bat:
        d.update(
            balls_faced=int(row["balls_faced"]),
            runs=_int(row["runs"]),
            dismissals=int(row["dismissals"]),
            strike_rate=clean(row["strike_rate"]),
            average=clean(row["average"]),
            balls_per_dismissal=clean(row["balls_per_dismissal"]),
            boundary_run_share=clean(row["boundary_run_share"]),
            boundary_ball_share=clean(row["boundary_ball_share"]),
        )
    else:
        d.update(
            legal_balls=int(row["legal_balls"]),
            overs=clean(row["overs"]),
            runs_conceded=_int(row["runs_conceded"]),
            wickets=int(row["wickets"]),
            economy=clean(row["economy"]),
            balls_per_wicket=clean(row["balls_per_wicket"]),
            boundary_conceded_share=clean(row["boundary_conceded_share"]),
            wides=_int(row["wides"]),
            no_balls=_int(row["no_balls"]),
            extras_charged_runs=_int(row["extras_charged_runs"]),
            bowling_style_modal=clean(row.get("bowling_style_modal")),
            bowling_style_modal_share=clean(row.get("bowling_style_modal_share")),
            pace_or_spin_modal=clean(row.get("pace_or_spin_modal")),
        )
    return d


def list_profiles(
    data: DescriptiveData,
    side: str,
    fmt: str | None,
    q: str | None,
    nationality: str | None,
    min_balls: int,
    sort_by: str,
    order: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    if sort_by not in SORT_COLUMNS:
        raise BadRequest(f"sort_by must be one of {SORT_COLUMNS}")
    df = data.side_frame(side)
    vol = "balls_faced" if side == "batter" else "legal_balls"
    if fmt:
        df = df[df["format"] == fmt]
    if q:
        df = df[df["player_name"].fillna("").str.contains(q, case=False, regex=False)]
    if nationality:
        df = df[df["nationality"].fillna("").str.upper() == nationality.upper()]
    if min_balls:
        df = df[df[vol] >= min_balls]
    col = vol if sort_by == "volume" else sort_by
    asc = order == "asc"
    df = df.sort_values(
        [col, "player_id", "format"], ascending=[asc, True, True], na_position="last"
    )
    total = len(df)
    page = df.iloc[offset : offset + limit]
    return {
        "page": {"total": int(total), "limit": limit, "offset": offset},
        "items": [profile_dict(r, side) for _, r in page.iterrows()],
        "sort_note": (
            "Sorting is by identity or volume of play only (name, id, matches, balls). It is not "
            "an ordering by performance."
        ),
    }


def player_profile(data: DescriptiveData, player_id: int) -> dict[str, Any]:
    b = data.batters[data.batters["player_id"] == player_id].sort_values("format")
    w = data.bowlers[data.bowlers["player_id"] == player_id].sort_values("format")
    if b.empty and w.empty:
        raise NotFound(f"no descriptive profile for player {player_id}")
    bat = [profile_dict(r, "batter") for _, r in b.iterrows()]
    bowl = [profile_dict(r, "bowler") for _, r in w.iterrows()]
    name = (bat or bowl)[0]["player_name"]
    return {
        "player_id": player_id,
        "player_name": name,
        "batting": bat,
        "bowling": bowl,
        "explanations": [
            s
            for p in bat + bowl
            for s in explain_player(p, data.cfg["display_sample_convention"]["phase_min_balls"])
        ],
        "limitations": list(LIMITATIONS),
    }


# ----------------------------------------------------------------------------- explanations
def _f(v: float | None, nd: int = 1) -> str:
    return "not available" if v is None else f"{v:.{nd}f}"


def explain_player(p: dict[str, Any], phase_min: int = 30) -> list[str]:
    """Plain sentences built only from the profile's own numbers. No superlatives, no ordering."""
    name = p["player_name"] or f"Player {p['player_id']}"
    fmt = p["format"]
    seasons = ", ".join(p["seasons_covered"]) or "no seasons"
    out: list[str] = []
    if p["side"] == "batter":
        n = p["balls_faced"]
        if n == 0:
            return [
                f"{name} ({fmt}): no balls faced in the profile window, so no batting rates exist."
            ]
        out.append(
            f"{name} ({fmt}, seasons {seasons}): {p['runs']} runs from {n} balls faced in "
            f"{p['matches_with_participation']} matches, strike rate {_f(p['strike_rate'])} runs per "
            f"100 balls, {p['dismissals']} dismissals."
        )
        if p["ci_low"] is not None:
            out.append(
                f"The 95% match-bootstrap range of the strike rate is {_f(p['ci_low'])} to "
                f"{_f(p['ci_high'])}."
            )
        else:
            out.append(f"No strike-rate range is given ({p['ci_unavailable_reason']}).")
        if p["average"] is None:
            out.append("The batting average is not defined because there were no dismissals.")
        out.append(
            f"Dot balls were {_f(None if p['dot_ball_share'] is None else 100 * p['dot_ball_share'])}% "
            f"of balls faced; fours {p['fours']}, sixes {p['sixes']}."
        )
        rate_name = "strike rate"
    else:
        n = p["legal_balls"]
        if n == 0:
            return [
                f"{name} ({fmt}): no legal balls bowled in the profile window, so no rates exist."
            ]
        out.append(
            f"{name} ({fmt}, seasons {seasons}): {p['runs_conceded']} runs conceded from {n} legal "
            f"balls ({p['overs']} overs) in {p['matches_with_participation']} matches, economy "
            f"{_f(p['economy'])} runs per over, {p['wickets']} bowler-credited wickets."
        )
        if p["ci_low"] is not None:
            out.append(
                f"The 95% match-bootstrap range of the economy is {_f(p['ci_low'])} to "
                f"{_f(p['ci_high'])}."
            )
        else:
            out.append(f"No economy range is given ({p['ci_unavailable_reason']}).")
        out.append(
            f"Dot balls were {_f(None if p['dot_ball_share'] is None else 100 * p['dot_ball_share'])}% "
            "of legal balls."
        )
        rate_name = "economy"
    for s in p["splits"]:
        if s["key"] in ("pp", "mid", "death") and s["balls"]:
            small = (
                f" (fewer than {phase_min} balls: small sample)" if s["balls"] < phase_min else ""
            )
            out.append(f"{s['label']}: {s['balls']} balls, {rate_name} {_f(s['rate'])}{small}.")
    q = p["quality"]
    if q["sample_sufficiency"] != "OK":
        out.append(f"Small-sample warning: {q['sample_note'] or q['sample_sufficiency']}.")
    out.append(
        f"{p['context_sample']['balls']} of these balls fell in the provisional pressure-context "
        "definition. This is a count only and says nothing about performance in those balls."
    )
    return out


# ----------------------------------------------------------------------------- compare
# metric: (label, unit, formula, numerator, denominator, scale)
BAT_METRICS = {
    "strike_rate": (
        "Strike rate",
        "runs per 100 balls",
        "100 * runs / balls faced",
        "runs",
        "balls",
        100.0,
    ),
    "boundary_ball_share": (
        "Boundary-ball share",
        "share of balls faced",
        "(fours + sixes) / balls faced",
        "boundaries",
        "balls",
        1.0,
    ),
    "dot_ball_share": (
        "Dot-ball share",
        "share of balls faced",
        "dot balls / balls faced",
        "dots",
        "balls",
        1.0,
    ),
    "balls_per_dismissal": (
        "Balls per dismissal",
        "balls",
        "balls faced / dismissals (undefined with none)",
        "balls",
        "outs",
        1.0,
    ),
}
BOWL_METRICS = {
    "economy": (
        "Economy",
        "runs per over",
        "6 * runs conceded / legal balls",
        "runs",
        "balls",
        6.0,
    ),
    "boundary_conceded_share": (
        "Boundary-conceded share",
        "share of legal balls",
        "(fours + sixes conceded) / legal balls",
        "boundaries",
        "balls",
        1.0,
    ),
    "dot_ball_share": (
        "Dot-ball share",
        "share of legal balls",
        "dot balls / legal balls",
        "dots",
        "balls",
        1.0,
    ),
    "balls_per_wicket": (
        "Balls per wicket",
        "balls",
        "legal balls / bowler-credited wickets (undefined with none)",
        "balls",
        "outs",
        1.0,
    ),
}


def _value(num: float, den: float, scale: float) -> float | None:
    return None if den <= 0 else float(num) / float(den) * scale


def compare_players(data: DescriptiveData, side: str, fmt: str, ids: list[int]) -> dict[str, Any]:
    cc = data.cfg["compare"]
    if len(ids) != len(set(ids)):
        raise BadRequest("player_ids must be distinct")
    if not cc["min_players"] <= len(ids) <= cc["max_players"]:
        raise BadRequest(f"compare takes {cc['min_players']} to {cc['max_players']} players")
    b = data.cfg["bootstrap"]
    pm = data.per_match
    pm = pm[(pm["side"] == side) & (pm["format"] == fmt)].copy()
    pm["boundaries"] = pm["fours"] + pm["sixes"]
    prof = data.side_frame(side)
    prof = prof[prof["format"] == fmt].set_index("player_id")
    vol = "balls_faced" if side == "batter" else "legal_balls"
    low = data.cfg["display_sample_convention"][f"low_sample_balls_{side}"]
    groups: dict[int, pd.DataFrame] = {}
    for pid in ids:
        g = pm[pm["player_id"] == pid].sort_values("match_id")
        if g.empty or pid not in prof.index:
            raise NotFound(f"player {pid} has no {side} profile in {fmt}")
        groups[pid] = g
    defs = BAT_METRICS if side == "batter" else BOWL_METRICS
    players = [
        {
            "player_id": pid,
            "player_name": clean(prof.loc[pid, "player_name"]),
            "balls": int(prof.loc[pid, vol]),
            "matches": int(len(groups[pid])),
            "sample_sufficiency": str(prof.loc[pid, "sample_sufficiency"]),
        }
        for pid in ids
    ]
    names = {p["player_id"]: p["player_name"] or f"Player {p['player_id']}" for p in players}
    low_flag = {p["player_id"]: p["balls"] < low for p in players}
    metrics = []
    counts = {"SUPPORTED": 0, "NOT_DISTINGUISHABLE": 0, "LOW_SAMPLE": 0, "UNAVAILABLE": 0}
    for mi, (key, (label, unit, formula, ncol, dcol, scale)) in enumerate(defs.items()):
        dl = {"balls": "balls", "outs": "dismissals" if side == "batter" else "wickets"}[dcol]
        draws: dict[int, np.ndarray | None] = {}
        values = []
        for pid in ids:
            g = groups[pid]
            num, den = g[ncol].to_numpy(dtype=float), g[dcol].to_numpy(dtype=float)
            v = _value(num.sum(), den.sum(), scale)
            reason = None
            lo = hi = None
            arr = None
            if len(g) < b["min_matches"]:
                reason = f"FEWER_THAN_{b['min_matches']}_MATCHES"
            elif v is None:
                reason = "DENOMINATOR_IS_ZERO"
            else:
                arr = ds.bootstrap_values(
                    num,
                    den,
                    (b["seed"], pid, ds.FORMAT_CODE[fmt], PM_CODE[side], mi),
                    b["n_boot"],
                    scale,
                )
                lo, hi, reason = ds.percentile_interval(arr, b["level"], b["max_undefined_share"])
                if reason:
                    arr = None
            draws[pid] = arr
            values.append(
                {
                    "player_id": pid,
                    "value": v,
                    "numerator": float(num.sum()),
                    "denominator": float(den.sum()),
                    "matches": int(len(g)),
                    "ci_low": lo,
                    "ci_high": hi,
                    "unavailable_reason": reason if v is None or reason else None,
                }
            )
        diffs = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, c = ids[i], ids[j]
                va, vc = values[i]["value"], values[j]["value"]
                diffs.append(
                    _pair(
                        key,
                        label,
                        unit,
                        a,
                        c,
                        names,
                        va,
                        vc,
                        draws,
                        low_flag,
                        b,
                        values[i],
                        values[j],
                        dl,
                    )
                )
        for d in diffs:
            counts[d["evidence"]] += 1
        metrics.append(
            {
                "metric": key,
                "label": label,
                "unit": unit,
                "formula": formula,
                "values": values,
                "differences": diffs,
            }
        )
    total = sum(counts.values())
    summary = [
        f"{total} pairwise differences were examined across {len(defs)} measures for "
        f"{len(ids)} players in {fmt}.",
        f"{counts['SUPPORTED']} have an interval that excludes 0, {counts['NOT_DISTINGUISHABLE']} "
        f"include 0, {counts['LOW_SAMPLE']} involve a player below {low} balls and "
        f"{counts['UNAVAILABLE']} could not be estimated.",
        "These are differences in descriptive rates only. They do not order the players and are not "
        "evidence about performance under pressure.",
    ]
    return {
        "side": side,
        "format": fmt,
        "players": players,
        "metrics": metrics,
        "summary": summary,
        "limitations": list(LIMITATIONS),
        "method": (
            f"Difference of two independent match-cluster bootstrap distributions "
            f"({b['n_boot']} draws, seed {b['seed']}, {int(b['level'] * 100)}% percentile). "
            "An interval that excludes 0 is labelled SUPPORTED."
        ),
    }


def _pair(key, label, unit, a, c, names, va, vc, draws, low_flag, b, ra, rc, dl) -> dict[str, Any]:
    na, nc = names[a], names[c]
    base = {"player_a": a, "player_b": c}
    if va is None or vc is None:
        return {
            **base,
            "difference": None,
            "ci_low": None,
            "ci_high": None,
            "evidence": "UNAVAILABLE",
            "text": f"{label}: not available for {na if va is None else nc} "
            f"({(ra if va is None else rc)['unavailable_reason']}).",
        }
    diff = va - vc
    head = (
        f"{label}: {na} {va:.3f} ({_vol(ra, dl)}) and {nc} {vc:.3f} ({_vol(rc, dl)}); "
        f"{na} minus {nc} = {diff:+.3f} {unit}."
    )
    da, dc = draws.get(a), draws.get(c)
    if da is None or dc is None:
        return {
            **base,
            "difference": diff,
            "ci_low": None,
            "ci_high": None,
            "evidence": "UNAVAILABLE",
            "text": head + " No interval for the difference could be estimated.",
        }
    lo, hi, why = ds.percentile_interval(da - dc, b["level"], b["max_undefined_share"])
    if why:
        return {
            **base,
            "difference": diff,
            "ci_low": None,
            "ci_high": None,
            "evidence": "UNAVAILABLE",
            "text": head + f" No interval for the difference could be estimated ({why}).",
        }
    if low_flag[a] or low_flag[c]:
        ev, tail = "LOW_SAMPLE", "At least one player is below the display sample convention."
    elif lo > 0 or hi < 0:
        ev, tail = (
            "SUPPORTED",
            "The interval excludes 0: the difference in this rate is supported by the sample.",
        )
    else:
        ev, tail = (
            "NOT_DISTINGUISHABLE",
            "The interval includes 0: the sample does not separate the two.",
        )
    return {
        **base,
        "difference": diff,
        "ci_low": lo,
        "ci_high": hi,
        "evidence": ev,
        "text": head + f" 95% interval of the difference {lo:+.3f} to {hi:+.3f}. {tail}",
    }


def _vol(v: dict[str, Any], dl: str) -> str:
    return f"{int(v['denominator'])} {dl} in {v['matches']} matches"


# ----------------------------------------------------------------------------- radar
RADAR_BAT = (
    ("strike_rate", "Strike rate", "runs per 100 balls", "runs", "balls_faced", 100.0, "base"),
    (
        "boundary_ball_share",
        "Boundary-ball share",
        "share of balls",
        None,
        "balls_faced",
        1.0,
        "base",
    ),
    ("dot_ball_share", "Dot-ball share", "share of balls", "dot_balls", "balls_faced", 1.0, "base"),
    (
        "balls_per_dismissal",
        "Balls per dismissal",
        "balls",
        "balls_faced",
        "dismissals",
        1.0,
        "base",
    ),
    (
        "pp_strike_rate",
        "Strike rate, powerplay",
        "runs per 100 balls",
        "pp_runs",
        "pp_balls",
        100.0,
        "phase",
    ),
    (
        "mid_strike_rate",
        "Strike rate, middle overs",
        "runs per 100 balls",
        "mid_runs",
        "mid_balls",
        100.0,
        "phase",
    ),
    (
        "death_strike_rate",
        "Strike rate, death overs",
        "runs per 100 balls",
        "death_runs",
        "death_balls",
        100.0,
        "phase",
    ),
)
RADAR_BOWL = (
    ("economy", "Economy", "runs per over", "runs_conceded", "legal_balls", 6.0, "base"),
    (
        "boundary_conceded_share",
        "Boundary-conceded share",
        "share of balls",
        None,
        "legal_balls",
        1.0,
        "base",
    ),
    ("dot_ball_share", "Dot-ball share", "share of balls", "dot_balls", "legal_balls", 1.0, "base"),
    ("balls_per_wicket", "Balls per wicket", "balls", "legal_balls", "wickets", 1.0, "base"),
    ("pp_economy", "Economy, powerplay", "runs per over", "pp_runs", "pp_balls", 6.0, "phase"),
    (
        "mid_economy",
        "Economy, middle overs",
        "runs per over",
        "mid_runs",
        "mid_balls",
        6.0,
        "phase",
    ),
    (
        "death_economy",
        "Economy, death overs",
        "runs per over",
        "death_runs",
        "death_balls",
        6.0,
        "phase",
    ),
)


def radar_dimension_values(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """Per-row numerator, denominator and value of each supported radar dimension."""
    dims = RADAR_BAT if side == "batter" else RADAR_BOWL
    out = pd.DataFrame({"player_id": df["player_id"].to_numpy()}, index=df.index)
    for key, _label, _unit, num, den, scale, _kind in dims:
        n = df["fours"] + df["sixes"] if num is None else df[num]
        d = df[den]
        out[f"{key}__n"] = n
        out[f"{key}__d"] = d
        out[key] = (n.astype(float) / d.where(d > 0).astype(float)) * scale
    return out


def percentile_of(value: float, cohort: np.ndarray) -> float:
    less = float((cohort < value).sum())
    eq = float((cohort == value).sum())
    return 100.0 * (less + 0.5 * eq) / len(cohort)


def radar(data: DescriptiveData, side: str, fmt: str, ids: list[int]) -> dict[str, Any]:
    if not 1 <= len(ids) <= data.cfg["compare"]["max_players"] or len(ids) != len(set(ids)):
        raise BadRequest("radar takes 1 to 4 distinct player ids")
    conv = data.cfg["display_sample_convention"]
    min_main = conv[f"low_sample_balls_{side}"]
    min_phase = conv["phase_min_balls"]
    min_cohort = data.cfg["radar"]["min_cohort_size"]
    df = data.side_frame(side)
    df = df[df["format"] == fmt].reset_index(drop=True)
    vals = radar_dimension_values(df, side)
    dims = RADAR_BAT if side == "batter" else RADAR_BOWL
    vol = "balls_faced" if side == "batter" else "legal_balls"
    players = []
    for pid in ids:
        idx = df.index[df["player_id"] == pid]
        if len(idx) == 0:
            raise NotFound(f"player {pid} has no {side} profile in {fmt}")
        i = idx[0]
        rows = []
        for key, label, unit, _n, den, _s, kind in dims:
            need = min_main if kind == "base" else min_phase
            gate_col = vol if kind == "base" else den
            d_all = df[gate_col]
            member = (d_all >= need) & vals[key].notna()
            cohort = vals.loc[member, key].to_numpy()
            v = clean(vals.loc[i, key])
            nn = clean(vals.loc[i, f"{key}__n"])
            dd = clean(vals.loc[i, f"{key}__d"])
            reason = None
            pct = None
            if v is None:
                reason = "VALUE_UNDEFINED_NO_DENOMINATOR"
            elif not bool(member.loc[i]):
                reason = f"BELOW_MIN_SAMPLE_{need}_BALLS"
            elif len(cohort) < min_cohort:
                reason = "COHORT_TOO_SMALL"
            else:
                pct = percentile_of(v, cohort)
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "unit": unit,
                    "raw_value": v,
                    "numerator": None if nn is None else float(nn),
                    "denominator": None if dd is None else float(dd),
                    "min_denominator": int(need),
                    "available": pct is not None,
                    "percentile_in_cohort": pct,
                    "cohort_size": int(len(cohort)),
                    "unavailable_reason": reason,
                }
            )
        players.append(
            {"player_id": pid, "player_name": clean(df.loc[i, "player_name"]), "dimensions": rows}
        )
    what = "balls faced" if side == "batter" else "legal balls bowled"
    return {
        "side": side,
        "format": fmt,
        "cohort_name": f"{fmt} {side}s with at least {min_main} {what}, 2022-2025 pre-test window",
        "cohort_definition": (
            f"All {fmt} {side} profiles meeting the minimum for the dimension "
            f"({min_main} {what}; {min_phase} balls for phase dimensions), with a defined value."
        ),
        "percentile_definition": (
            "Share of the cohort with a lower raw value, counting ties as half and including the "
            "player's own value in the cohort. It places a value "
            "within the cohort; it does not say whether a higher or lower value is preferable."
        ),
        "players": players,
        "notes": [
            "Batting and bowling are separate and no dimensions are combined into one figure.",
            "A dimension that cannot be computed is shown as unavailable, never as zero.",
            "Raw values and their denominators are given with every percentile.",
        ],
    }


# ----------------------------------------------------------------------------- overview
def overview(data: DescriptiveData) -> dict[str, Any]:
    ov = data.context["overview"]
    off, st, sc = ov["official"], ov["analytical_store"], ov["descriptive_scope"]
    return {
        "matches_total": off["matches_total"],
        "delivery_rows_total": off["delivery_rows_total"],
        "matches_by_competition": off["matches_by_competition"],
        "descriptive_window": sc["window"],
        "scope_by_format": [{"format": k, **v} for k, v in sorted(sc["formats"].items())],
        "players_with_any_profile": sc["players_with_any_profile"],
        "match_periods": st["match_periods"],
        "rows_in_innings_3_4_excluded": st["rows_in_innings_3_4_excluded"],
        "rows_out_of_scope_competition": st["rows_out_of_scope_competition"],
        "late_t20i_dates_unverified": st["late_t20i_dates_unverified"],
        "lineage": off["lineage"],
        "pending_official_inputs": ov["pending_official_inputs"],
        "reliability_checks": ov["reliability_checks"],
        "lists_available": ov["lists_available"],
        "why_no_ordered_lists": ov["why_no_ordered_lists"],
        "descriptive_hashes": ov["descriptive_hashes"],
    }


def methodology(data: DescriptiveData) -> dict[str, Any]:
    m = data.context["methodology"]
    return {
        "sections": m["sections"],
        "reliability_facts": m["reliability_facts"],
        "primary_definition_id": m["primary_definition"]["id"],
        "primary_definition_label": m["primary_definition"]["label"],
        "profile_columns_note": (
            "Column definitions are in player_profile_explanations.md in the reports folder."
        ),
    }
