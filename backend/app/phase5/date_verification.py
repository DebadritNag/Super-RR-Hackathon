"""T20I / TEST-period match-date verification (Phase 5). EXPERIMENTAL_NOT_VALIDATED.

Builds a per-match evidence table from data already in the project. No date is ever changed and no
match is official-verified unless the user supplies a complete official record. This is the only
Phase 5 module allowed to read Cricsheet; Cricsheet is secondary, validation-only evidence and is
never an input to any score, baseline, threshold or ranking.

Evidence checks:
  (a) first and last ``delivery_ist_time`` date part (the column carries a ``UTC`` suffix),
  (b) series ordering, spacing and double-booking (internal only),
  (c) competition season/year token (internal only, weak),
  (d) ``matches 2026.csv`` cross-check (IPL only, read-only),
  (e) Cricsheet date for the same team pair, identity confirmed by non-date facts,
  (f) internal conflicts.
Only (a), (d) and (e) count as agreeing sources. Internal checks can create a conflict but never
raise a single-source row to consistent.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.data_pipeline.cricsheet_auditor import normalise_team

CONSISTENT = "DATE_CONSISTENT_ACROSS_SOURCES"
SINGLE = "DATE_SINGLE_SOURCE"
CONFLICT = "DATE_CONFLICT"
UNVERIFIED = "DATE_UNVERIFIED"
CLASSES = (CONSISTENT, SINGLE, CONFLICT, UNVERIFIED)

OFFICIAL_COLUMNS = (
    "match_id",
    "verified_date",
    "source",
    "verified_by",
    "verified_date_of_verification",
)
NOT_OFFICIAL_STATEMENT = (
    "No match is official-verified: no user-supplied official record is loaded. Classes below are "
    "evidence consistency only, not verification against an authoritative record."
)


class DateVerificationError(ValueError):
    """Invalid official verification input or evidence input."""


def _d(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _status(diff: int | None, tol: int) -> str:
    if diff is None:
        return "NO_DATA"
    return "AGREE" if abs(diff) <= tol else "CONFLICT"


# ---------------------------------------------------------------- (a) timestamps
def timestamp_evidence(row: pd.Series | dict | None, match_date: date, cfg: dict) -> dict[str, Any]:
    """``row``: n_rows, n_nonmidnight, min_ts, max_ts (strings like ``2026-07-01 16:33:43 UTC``)."""
    tcfg = cfg["timestamp"]
    out: dict[str, Any] = {
        "ts_first_date": None,
        "ts_last_date": None,
        "ts_diff_first_days": None,
        "ts_diff_last_days": None,
        "timestamp_informative": False,
        "ts_status": "NO_DATA",
    }
    if row is None:
        return out
    n_rows = int(row["n_rows"])
    n_non = int(row["n_nonmidnight"])
    if n_rows == 0:
        return out
    if n_non == 0 or n_non / n_rows < float(tcfg["min_nonmidnight_share"]):
        out["ts_status"] = "NOT_INFORMATIVE"
        return out
    first, last = _d(str(row["min_ts"])[:10]), _d(str(row["max_ts"])[:10])
    d_first, d_last = (first - match_date).days, (last - match_date).days
    out.update(
        ts_first_date=first.isoformat(),
        ts_last_date=last.isoformat(),
        ts_diff_first_days=d_first,
        ts_diff_last_days=d_last,
        timestamp_informative=True,
    )
    tol = int(tcfg["tolerance_days"])
    out["ts_status"] = "AGREE" if max(abs(d_first), abs(d_last)) <= tol else "CONFLICT"
    return out


# ---------------------------------------------------------------- (b) ordering / double booking
def ordering_checks(matches: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Internal checks per match_id over the whole ``matches`` frame (never changes dates)."""
    max_gap = int(cfg["ordering"]["max_gap_days_between_series_matches"])
    m = matches[
        ["match_id", "comp_id", "match_number", "match_date", "home_team_id", "away_team_id"]
    ]
    m = m.copy()
    m["_d"] = m["match_date"].map(_d)
    notes: dict[int, list[str]] = {int(i): [] for i in m["match_id"]}
    for _, grp in m.dropna(subset=["match_number", "_d"]).groupby("comp_id"):
        g = grp.sort_values(["match_number", "match_id"])
        ids, nums, dts = g["match_id"].tolist(), g["match_number"].tolist(), g["_d"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if nums[i] < nums[j] and dts[i] > dts[j]:
                    notes[int(ids[i])].append(f"order:later_than_match_{ids[j]}")
                    notes[int(ids[j])].append(f"order:earlier_than_match_{ids[i]}")
        for i in range(len(ids) - 1):
            if abs((dts[i + 1] - dts[i]).days) > max_gap:
                notes[int(ids[i])].append(f"gap>{max_gap}d_to_match_{ids[i + 1]}")
                notes[int(ids[i + 1])].append(f"gap>{max_gap}d_to_match_{ids[i]}")
    # a team cannot play two matches on one date
    long = pd.concat(
        [
            m[["match_id", "_d", "home_team_id"]].rename(columns={"home_team_id": "team"}),
            m[["match_id", "_d", "away_team_id"]].rename(columns={"away_team_id": "team"}),
        ]
    ).dropna()
    dup = long[long.duplicated(["_d", "team"], keep=False)]
    for (_, team), grp in dup.groupby(["_d", "team"]):
        ids = sorted(int(i) for i in grp["match_id"])
        for i in ids:
            notes[i].append(f"double_booked_team_{int(team)}:" + "/".join(str(x) for x in ids))
    rows = []
    for i, n in notes.items():
        order_notes = sorted(set(x for x in n if not x.startswith("double_booked")))
        dbl = sorted(set(x for x in n if x.startswith("double_booked")))
        rows.append(
            {
                "match_id": i,
                "ordering_consistent": not order_notes,
                "ordering_detail": ";".join(order_notes),
                "double_booking": ";".join(dbl),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- (c) season token
def season_token_status(comp_name: str | None, season: str | None, match_date: date) -> str:
    text = f"{season or ''} {comp_name or ''}"
    years = {int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", text)}
    for a, b in re.findall(r"((?:19|20)\d{2})/(\d{2})(?!\d)", text):
        years.add(int(a[:2] + b))
    if not years:
        return "NOT_APPLICABLE"
    return "CONSISTENT" if match_date.year in years else "INCONSISTENT"


# ---------------------------------------------------------------- (d) matches 2026.csv
def load_matches_2026(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["_date"] = pd.to_datetime(df["date"], format="%B %d, %Y", errors="coerce").dt.date
    return df


def _abbrev(name: str, cfg: dict) -> str:
    initials = "".join(w[0] for w in re.split(r"\s+", name.strip()) if w).upper()
    return initials


def matches_2026_evidence(
    match: pd.Series, first_total: int | None, m26: pd.DataFrame | None, cfg: dict
) -> dict[str, Any]:
    out = {"m26_status": "NOT_APPLICABLE", "m26_date": None, "m26_diff_days": None}
    if m26 is None or match["competition_type"] not in cfg["matches_2026_csv"]["applies_to"]:
        return out
    aliases = cfg["matches_2026_csv"]["team_abbreviations"]
    inv = {normalise_team(v): k for k, v in aliases.items()}

    def abbr(name: str) -> str:
        return inv.get(normalise_team(name)) or _abbrev(name, cfg)

    pair = {abbr(match["home_team"]), abbr(match["away_team"])}
    md = _d(match["match_date"])
    cand = m26[
        pd.Series(
            [{str(a), str(b)} == pair for a, b in zip(m26["team1"], m26["team2"], strict=True)],
            index=m26.index,
            dtype=bool,
        )
    ]
    if first_total is not None:
        cand = cand[cand["first_ings_score"] == first_total]
    win = int(cfg["cricsheet"]["confirmed_identity_window_days"])
    cand = cand[
        pd.Series(
            [d is not None and abs((d - md).days) <= win for d in cand["_date"]],
            index=cand.index,
            dtype=bool,
        )
    ]
    if len(cand) == 0:
        out["m26_status"] = "NO_ROW"
        return out
    d = cand.iloc[0]["_date"]
    diff = (d - md).days
    out.update(
        m26_date=d.isoformat(),
        m26_diff_days=diff,
        m26_status=_status(diff, int(cfg["matches_2026_csv"]["tolerance_days"])),
    )
    return out


# ---------------------------------------------------------------- (e) Cricsheet (validation only)
def load_cricsheet_index(path: Path | str, min_date: str) -> pd.DataFrame:
    """Staged Cricsheet index, men's T20 only (VALIDATION ONLY). Not deduplicated here: the same id\n    can sit in several directories, so duplicates are dropped after the directory filter."""
    cs = pd.read_parquet(path)
    cs = cs[(cs["match_type"] == "T20") & (cs["gender"] == "male") & (cs["date"] >= min_date)]
    return cs.reset_index(drop=True)


def _first_innings(raw: str | None) -> tuple[str, int] | None:
    try:
        for inn in json.loads(raw or "[]"):
            if not inn.get("super_over", False):
                return normalise_team(inn.get("team")), int(inn.get("total"))
    except (ValueError, TypeError):
        return None
    return None


def cricsheet_evidence(
    match: pd.Series,
    first_team: str | None,
    first_total: int | None,
    cs: pd.DataFrame | None,
    cfg: dict,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cs_status": "NOT_CHECKED",
        "cs_match_id": None,
        "cs_dir": None,
        "cs_date": None,
        "cs_diff_days": None,
        "cs_candidates": 0,
    }
    if cs is None:
        return out
    ccfg = cfg["cricsheet"]
    dirs = ccfg["directories"].get(match["competition_type"])
    if not dirs:
        out["cs_status"] = "NOT_APPLICABLE"
        return out
    md = _d(match["match_date"])
    key = "|".join(sorted([normalise_team(match["home_team"]), normalise_team(match["away_team"])]))
    pool = cs[(cs["teams_key"] == key) & cs["directory"].isin(dirs)]
    pool = pool.sort_values(["match_id", "directory"]).drop_duplicates("match_id", keep="first")
    pool = pool.assign(_cd=pool["date"].map(_d))
    wide = int(ccfg["confirmed_identity_window_days"])
    near = int(ccfg["candidate_window_days"])
    pool = pool[
        pd.Series(
            [c is not None and abs((c - md).days) <= wide for c in pool["_cd"]],
            index=pool.index,
            dtype=bool,
        )
    ]
    out["cs_candidates"] = int(sum(abs((c - md).days) <= near for c in pool["_cd"]))
    confirmed = []
    for _, r in pool.iterrows():
        fi = _first_innings(r["innings_json"])
        if (
            fi
            and first_team is not None
            and first_total is not None
            and fi == (first_team, first_total)
        ):
            confirmed.append(r)
    if not confirmed:
        out["cs_status"] = "IDENTITY_UNCONFIRMED" if out["cs_candidates"] else "NO_CANDIDATE"
        return out
    best = sorted(confirmed, key=lambda r: (abs((r["_cd"] - md).days), str(r["match_id"])))[0]
    diff = (best["_cd"] - md).days
    out.update(
        cs_match_id=str(best["match_id"]),
        cs_dir=best["directory"],
        cs_date=best["_cd"].isoformat(),
        cs_diff_days=diff,
        cs_status=_status(diff, int(ccfg["tolerance_days"])),
    )
    return out


# ---------------------------------------------------------------- classification
def classify(evidence: dict[str, Any]) -> dict[str, Any]:
    """Class from independent source statuses plus internal conflicts."""
    sources = {
        "timestamp": evidence.get("ts_status"),
        "cricsheet": evidence.get("cs_status"),
        "matches_2026_csv": evidence.get("m26_status"),
    }
    agree = sorted(k for k, v in sources.items() if v == "AGREE")
    conflicts = sorted(k for k, v in sources.items() if v == "CONFLICT")
    internal = []
    if evidence.get("ordering_consistent") is False:
        internal.append("ordering:" + str(evidence.get("ordering_detail", "")))
    if evidence.get("double_booking"):
        internal.append(str(evidence["double_booking"]))
    if evidence.get("season_token_status") == "INCONSISTENT":
        internal.append("season_token_inconsistent")
    if conflicts or internal:
        cls = CONFLICT
    elif len(agree) >= 2:
        cls = CONSISTENT
    elif len(agree) == 1:
        cls = SINGLE
    else:
        cls = UNVERIFIED
    return {
        "date_class": cls,
        "n_agreeing_sources": len(agree),
        "agreeing_sources": ",".join(agree),
        "n_conflicting_sources": len(conflicts),
        "conflicting_sources": ",".join(conflicts),
        "internal_conflicts": " | ".join(internal),
        "official_verified": False,
    }


# ---------------------------------------------------------------- official verification input
def load_official_verification(
    csv_path: Path | str | None, known_ids: set[int], original_dates: dict[int, date]
) -> dict[str, Any]:
    """Read the user-supplied official record.

    Only rows with every field filled are OFFICIAL. Rows with some fields empty are reported as
    ``incomplete`` and never count. A complete row with a bad ISO date or an unknown match id
    raises. A verified date that differs from the original is returned in ``differs`` (the
    original is never changed and the match is not treated as officially verified).
    """
    empty = pd.DataFrame(columns=list(OFFICIAL_COLUMNS))
    res: dict[str, Any] = {"official": empty, "differs": empty, "incomplete": [], "path": None}
    if csv_path is None or not Path(csv_path).exists():
        return res
    res["path"] = str(csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    if list(df.columns) != list(OFFICIAL_COLUMNS):
        raise DateVerificationError(
            f"official verification columns must be {list(OFFICIAL_COLUMNS)}, got {list(df.columns)}"
        )
    keep, differ = [], []
    seen: set[int] = set()
    for i, r in df.iterrows():
        vals = {c: str(r[c]).strip() for c in OFFICIAL_COLUMNS}
        if not any(vals.values()):
            continue
        if not all(vals.values()):
            res["incomplete"].append({"row": int(i) + 2, "match_id": vals["match_id"]})
            continue
        try:
            mid = int(vals["match_id"])
            vd = date.fromisoformat(vals["verified_date"])
            date.fromisoformat(vals["verified_date_of_verification"])
        except ValueError as exc:
            raise DateVerificationError(
                f"row {int(i) + 2}: invalid id or ISO date ({exc})"
            ) from exc
        if mid not in known_ids:
            raise DateVerificationError(f"row {int(i) + 2}: unknown T20I match_id {mid}")
        if mid in seen:
            raise DateVerificationError(f"row {int(i) + 2}: duplicate match_id {mid}")
        seen.add(mid)
        rec = {**vals, "match_id": mid, "verified_date": vd.isoformat()}
        (keep if vd == original_dates[mid] else differ).append(rec)
    res["official"] = pd.DataFrame(keep, columns=list(OFFICIAL_COLUMNS))
    res["differs"] = pd.DataFrame(differ, columns=list(OFFICIAL_COLUMNS))
    return res


# ---------------------------------------------------------------- orchestration
def build_date_check(
    matches: pd.DataFrame,
    targets: pd.DataFrame,
    competitions: pd.DataFrame,
    ts_summary: pd.DataFrame,
    first_innings: pd.DataFrame,
    cricsheet: pd.DataFrame | None,
    matches_2026: pd.DataFrame | None,
    official: dict[str, Any],
    cfg: dict,
) -> pd.DataFrame:
    """One row per target match with all evidence columns, a class and the official status.

    ``matches`` is the full match table (context for ordering). It is only read.
    """
    order = ordering_checks(matches, cfg).set_index("match_id")
    comps = competitions.set_index("comp_id")
    ts = ts_summary.set_index("match_id")
    fi = first_innings.set_index("match_id")
    off = {int(r.match_id): r for r in official["official"].itertuples()}
    diff = {int(r.match_id): r for r in official["differs"].itertuples()}
    cutoff = date.fromisoformat(cfg["late_cutoff"])
    rows = []
    for _, m in targets.sort_values("match_id").iterrows():
        mid = int(m["match_id"])
        md = _d(m["match_date"])
        c = comps.loc[m["comp_id"]] if m["comp_id"] in comps.index else None
        names = {int(m["home_team_id"]): m["home_team"], int(m["away_team_id"]): m["away_team"]}
        f_team = f_total = None
        if mid in fi.index:
            f_total = int(fi.loc[mid, "total_runs"])
            f_team = normalise_team(names.get(int(fi.loc[mid, "batting_team_id"])))
        ev: dict[str, Any] = {
            "match_id": mid,
            "comp_id": int(m["comp_id"]),
            "comp_name": None if c is None else c["comp_name"],
            "competition_type": m["competition_type"],
            "match_number": None if pd.isna(m["match_number"]) else int(m["match_number"]),
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "original_match_date": md.isoformat(),
            "late_after_cutoff": md > cutoff,
            "has_deliveries": bool(m["has_deliveries"]),
        }
        ev.update(timestamp_evidence(ts.loc[mid] if mid in ts.index else None, md, cfg))
        o = order.loc[mid] if mid in order.index else None
        ev["ordering_consistent"] = True if o is None else bool(o["ordering_consistent"])
        ev["ordering_detail"] = "" if o is None else o["ordering_detail"]
        ev["double_booking"] = "" if o is None else o["double_booking"]
        ev["season_token_status"] = (
            "NOT_APPLICABLE"
            if c is None
            else season_token_status(c["comp_name"], str(c["season"]), md)
        )
        ev.update(matches_2026_evidence(m, f_total, matches_2026, cfg))
        ev.update(cricsheet_evidence(m, f_team, f_total, cricsheet, cfg))
        ev.update(classify(ev))
        if mid in off:
            ev["official_status"], ev["official_verified"] = "OFFICIAL_VERIFIED", True
            ev["official_date"] = off[mid].verified_date
        elif mid in diff:
            ev["official_status"], ev["official_date"] = (
                "OFFICIAL_DATE_DIFFERS",
                diff[mid].verified_date,
            )
        else:
            ev["official_status"], ev["official_date"] = "NOT_SUPPLIED", None
        rows.append(ev)
    return pd.DataFrame(rows)
