"""Player classification from actual records only (nationality and international status).

The two fields are independent: no field is ever inferred from the other. Everything that is not
proven by a record stays ``Unknown`` with a reason. Name matching only generates candidates; a
squad row is applied only when the name is unique AND the player's team in the squad competition
(an id-keyed fact) corroborates the squad row's team group. Uncapped is never derived.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import BACKEND_ROOT

CLASSIFICATION_VERSION = "p4_classification_v1"
CLASSIFICATION_CONFIG = BACKEND_ROOT / "config" / "phase4_classification_v1.json"
OVERRIDES_FILE = BACKEND_ROOT / "config" / "classification_overrides_v1.csv"

NATIONALITIES = ("Indian", "Overseas", "Unknown")
STATUSES = ("Capped", "Uncapped", "Unknown")
V_SOURCE = "VERIFIED_FROM_SOURCE"
V_DERIVED = "DERIVED"
V_T20I = "DERIVED_FROM_OFFICIAL_T20I_APPEARANCES"
V_NONE = "UNVERIFIED"
VERIFICATIONS = (V_SOURCE, V_DERIVED, V_T20I, V_NONE)
OVERRIDE_FIELDS = ("nationality", "international_status")
OVERRIDE_COLUMNS = ("player_id", "field", "value", "source", "verified_by", "verified_date")
_ENUM = {"nationality": ("Indian", "Overseas"), "international_status": ("Capped", "Uncapped")}

R_NO_RECORD = "NO_SOURCE_RECORD"
R_AMBIGUOUS = "SQUAD_NAME_AMBIGUOUS"
R_UNCORROBORATED = "SQUAD_NAME_UNCORROBORATED"
R_VARIANT = "SQUAD_VARIANT_CANDIDATE_NOT_APPLIED"
R_DUPLICATE = "SQUAD_PLAYER_ID_REPEATED"
R_BAD_VALUE = "SQUAD_NATIONALITY_VALUE_UNRECOGNISED"
R_MIXED = "MIXED_T20I_TEAMS"
R_NOT_PROVEN = "NOT_PROVEN_CAPPED_IN_DATA"
R_AFTER = "FIRST_T20I_AFTER_AS_OF_DATE"

SOURCE_SQUAD = "ipl squad.csv:NAME_PLUS_TEAM_MATCH"
SOURCE_NATIONAL_TEAM = "DERIVED_FROM_T20I_NATIONAL_TEAM"


class ClassificationConfigError(ValueError):
    """Raised for an invalid override file or classification configuration."""


def load_config(path: Path | str = CLASSIFICATION_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm_name(value: Any) -> str:
    """Case-insensitive, whitespace-normalised name key (candidate generation only)."""
    return " ".join(str(value).split()).casefold()


# ----------------------------------------------------------------------------- overrides


def load_overrides(path: Path | str, known_player_ids: Iterable[int]) -> pd.DataFrame:
    """Read and validate the manual override file. A header-only file returns an empty frame."""
    known = {int(p) for p in known_player_ids}
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    return validate_overrides(raw, known)


def validate_overrides(raw: pd.DataFrame, known: set[int]) -> pd.DataFrame:
    errors: list[str] = []
    if list(raw.columns) != list(OVERRIDE_COLUMNS):
        raise ClassificationConfigError(
            f"override columns must be exactly {list(OVERRIDE_COLUMNS)}, got {list(raw.columns)}"
        )
    seen: set[tuple[int, str]] = set()
    rows: list[dict[str, Any]] = []
    for i, r in raw.iterrows():
        line = int(i) + 2
        pid = None
        try:
            pid = int(str(r["player_id"]).strip())
        except ValueError:
            errors.append(f"line {line}: player_id '{r['player_id']}' is not an integer")
        if pid is not None and pid not in known:
            errors.append(f"line {line}: unknown player_id {pid}")
        field = str(r["field"]).strip()
        if field not in OVERRIDE_FIELDS:
            errors.append(f"line {line}: field '{field}' must be one of {list(OVERRIDE_FIELDS)}")
        value = str(r["value"]).strip()
        if field in _ENUM and value not in _ENUM[field]:
            errors.append(f"line {line}: value '{value}' invalid for {field} {list(_ENUM[field])}")
        for col in ("source", "verified_by"):
            if not str(r[col]).strip():
                errors.append(f"line {line}: {col} must not be empty")
        try:
            date.fromisoformat(str(r["verified_date"]).strip())
        except ValueError:
            errors.append(
                f"line {line}: verified_date '{r['verified_date']}' is not ISO YYYY-MM-DD"
            )
        if pid is not None and (pid, field) in seen:
            errors.append(f"line {line}: duplicate override for ({pid}, {field})")
        if pid is not None:
            seen.add((pid, field))
        rows.append(
            {
                "player_id": pid,
                "field": field,
                "value": value,
                "source": str(r["source"]).strip(),
                "verified_by": str(r["verified_by"]).strip(),
                "verified_date": str(r["verified_date"]).strip(),
            }
        )
    if errors:
        raise ClassificationConfigError("; ".join(errors))
    out = pd.DataFrame(rows, columns=list(OVERRIDE_COLUMNS))
    if len(out):
        out["player_id"] = out["player_id"].astype("int64")
    return out


# ----------------------------------------------------------------------------- squad evidence


def load_squad(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    need = {"team_no", "team_name", "player", "nationality", "role", "designation"}
    if not need.issubset(df.columns):
        raise ClassificationConfigError(
            f"squad file is missing columns {sorted(need - set(df.columns))}"
        )
    for c in need:
        df[c] = df[c].str.strip()
    df["squad_row"] = range(1, len(df) + 1)
    return df


def _variant_map(players: pd.DataFrame) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for pid, raw in zip(players["player_id"], players.get("name_variants", []), strict=False):
        try:
            names = json.loads(raw) if isinstance(raw, str) else []
        except json.JSONDecodeError:
            names = []
        for n in names:
            out.setdefault(norm_name(n), set()).add(int(pid))
    return out


def resolve_squad(
    squad: pd.DataFrame,
    players: pd.DataFrame,
    mapping: pd.DataFrame,
    teams: pd.DataFrame | None,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """One evidence row per squad row: match type, candidates, team corroboration.

    ``mapping`` holds (player_id, team_id) rows of the squad competition. ``teams`` is optional
    (team_id, team_name) and only used for an informational text cross-check, never for matching.
    """
    exact: dict[str, set[int]] = {}
    for pid, nm in zip(players["player_id"], players["player_name"], strict=False):
        exact.setdefault(norm_name(nm), set()).add(int(pid))
    variants = _variant_map(players)
    team_of: dict[int, set[int]] = {}
    for pid, tid in zip(mapping["player_id"], mapping["team_id"], strict=False):
        team_of.setdefault(int(pid), set()).add(int(tid))
    names = (
        dict(zip(teams["team_id"].astype(int), teams["team_name"], strict=False))
        if teams is not None
        else {}
    )
    rows: list[dict[str, Any]] = []
    for r in squad.itertuples(index=False):
        key = norm_name(r.player)
        ex = sorted(exact.get(key, set()))
        var = sorted(variants.get(key, set()) - set(ex))
        if len(ex) == 1:
            mtype, cands = "EXACT_UNIQUE", ex
        elif len(ex) > 1:
            mtype, cands = "EXACT_AMBIGUOUS", ex
        elif var:
            mtype, cands = "VARIANT_CANDIDATE", var
        else:
            mtype, cands = "NO_MATCH", []
        rows.append(
            {
                "squad_row": r.squad_row,
                "team_no": r.team_no,
                "squad_team_name": r.team_name,
                "squad_player": r.player,
                "squad_nationality": r.nationality,
                "squad_role": r.role,
                "squad_designation": r.designation,
                "match_type": mtype,
                "candidate_ids": ",".join(str(c) for c in cands),
                "player_id": ex[0] if mtype == "EXACT_UNIQUE" else None,
            }
        )
    ev = pd.DataFrame(rows)
    # id-keyed team inference per squad team group (plurality of uniquely resolved players)
    inferred: dict[str, int] = {}
    min_rows = int(cfg["squad_corroboration"]["min_resolved_rows_per_team"])
    min_share = float(cfg["squad_corroboration"]["min_plurality_share"])
    for team_no, g in ev[ev["match_type"] == "EXACT_UNIQUE"].groupby("team_no"):
        ts = [
            next(iter(team_of[int(p)])) for p in g["player_id"] if len(team_of.get(int(p), ())) == 1
        ]
        if len(ts) < min_rows:
            continue
        tid, n = Counter(ts).most_common(1)[0]
        if n / len(g) >= min_share:
            inferred[str(team_no)] = int(tid)
    counts = Counter(inferred.values())
    inferred = {k: v for k, v in inferred.items() if counts[v] == 1}  # bijection only
    ev["inferred_team_id"] = ev["team_no"].map(lambda t: inferred.get(str(t)))

    def corroborated(pid: Any, tno: Any) -> bool:
        tid = inferred.get(str(tno))
        return bool(
            pd.notna(pid) and tid is not None and team_of.get(int(pid), set()) == {int(tid)}
        )

    ev["team_corroborated"] = [
        corroborated(p, t) if m == "EXACT_UNIQUE" else False
        for p, t, m in zip(ev["player_id"], ev["team_no"], ev["match_type"], strict=False)
    ]
    ev["variant_team_corroborated"] = [
        bool(m == "VARIANT_CANDIDATE" and len(c.split(",")) == 1 and corroborated(int(c), t))
        for m, c, t in zip(ev["match_type"], ev["candidate_ids"], ev["team_no"], strict=False)
    ]
    ev["team_text_agrees"] = [
        (
            norm_name(n) == norm_name(names.get(int(i), ""))
            if i is not None and not pd.isna(i)
            else None
        )
        for n, i in zip(ev["squad_team_name"], ev["inferred_team_id"], strict=False)
    ]
    dup = ev[ev["match_type"] == "EXACT_UNIQUE"]["player_id"].value_counts()
    ev["player_id_repeated"] = ev["player_id"].map(
        lambda p: bool(pd.notna(p) and dup.get(p, 0) > 1)
    )
    return ev


# ----------------------------------------------------------------------------- build


def _t20i_summary(t20i: pd.DataFrame, as_of: pd.Timestamp, india: str) -> pd.DataFrame:
    """Per player: appearances on or before as_of, first date, team evidence."""
    if t20i.empty:
        return pd.DataFrame(
            columns=["player_id", "first_t20i_date", "t20i_appearances", "t20i_teams", "n_teams"]
        )
    d = t20i.copy()
    d["match_date"] = pd.to_datetime(d["match_date"])
    first = d.groupby("player_id")["match_date"].min().rename("first_t20i_date")
    pre = d[d["match_date"] <= as_of]
    cnt = pre.groupby("player_id").size().rename("t20i_appearances")
    teams = (
        pre.groupby("player_id")["team_name"]
        .agg(lambda s: "|".join(sorted(set(s))))
        .rename("t20i_teams")
    )
    out = pd.concat([first, cnt, teams], axis=1).reset_index()
    out["t20i_appearances"] = out["t20i_appearances"].fillna(0).astype(int)
    out["t20i_teams"] = out["t20i_teams"].fillna("")
    out["n_teams"] = out["t20i_teams"].map(lambda s: len([t for t in s.split("|") if t]))
    out["plays_for_india_only"] = out["t20i_teams"] == india
    out["plays_never_for_india"] = (out["t20i_teams"] != "") & ~out["t20i_teams"].str.contains(
        f"(?:^|\\|){india}(?:$|\\|)", regex=True
    )
    return out


def apply_overrides(base: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Overrides win, are labelled VERIFIED_FROM_SOURCE and flag a disagreement with a derivation."""
    out = base.copy()
    for col in ("nationality_verified_by", "nationality_verified_date"):
        out[col] = None
    for col in ("status_verified_by", "status_verified_date"):
        out[col] = None
    if overrides is None or overrides.empty:
        return out
    idx = out.set_index("player_id").index
    for o in overrides.itertuples(index=False):
        mask = out["player_id"] == o.player_id
        if not mask.any() or o.player_id not in idx:
            continue
        prefix = "nationality" if o.field == "nationality" else "international_status"
        short = "nationality" if o.field == "nationality" else "status"
        previous = out.loc[mask, prefix].iloc[0]
        prev_ver = out.loc[mask, f"{prefix}_verification"].iloc[0]
        if prev_ver != V_NONE and previous not in ("Unknown", o.value):
            out.loc[mask, "conflict_flag"] = True
        out.loc[mask, prefix] = o.value
        out.loc[mask, f"{prefix}_verification"] = V_SOURCE
        out.loc[mask, f"{prefix}_source"] = f"MANUAL_OVERRIDE:{o.source}"
        out.loc[mask, f"{prefix}_unknown_reason"] = None
        out.loc[mask, f"{short}_verified_by"] = o.verified_by
        out.loc[mask, f"{short}_verified_date"] = o.verified_date
    return out


def build_classification(
    players: pd.DataFrame,
    squad: pd.DataFrame,
    mapping: pd.DataFrame,
    t20i: pd.DataFrame,
    cfg: dict[str, Any],
    teams: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Return the base classification (no overrides), squad evidence and the unresolved list.

    ``t20i`` has one row per T20I appearance (player_id, team_name, match_date).
    """
    as_of = pd.Timestamp(cfg["as_of_date"])
    india = cfg["national_team_for_indian"]
    ev = resolve_squad(squad, players, mapping, teams, cfg)
    t = _t20i_summary(t20i, as_of, india).set_index("player_id")
    cand_rows: dict[int, list[pd.Series]] = {}
    for _, r in ev.iterrows():
        if r["match_type"] == "EXACT_UNIQUE":
            cand_rows.setdefault(int(r["player_id"]), []).append(r)
        elif r["candidate_ids"]:
            for c in str(r["candidate_ids"]).split(","):
                cand_rows.setdefault(int(c), []).append(r)
    recs: list[dict[str, Any]] = []
    for p in players.itertuples(index=False):
        pid = int(p.player_id)
        rws = cand_rows.get(pid, [])
        exact_rows = [r for r in rws if r["match_type"] == "EXACT_UNIQUE"]
        rec: dict[str, Any] = {
            "player_id": pid,
            "player_name": p.player_name,
            "squad_team_name": None,
            "squad_role": None,
            "squad_designation": None,
            "squad_nationality_raw": None,
            "squad_match_type": "NO_MATCH",
        }
        nat, nver, nsrc, nreason = "Unknown", V_NONE, None, R_NO_RECORD
        conflict = False
        squad_value = None
        if exact_rows:
            r = exact_rows[0]
            rec.update(
                squad_team_name=r["squad_team_name"],
                squad_role=r["squad_role"],
                squad_designation=r["squad_designation"] or None,
                squad_nationality_raw=r["squad_nationality"],
                squad_match_type="EXACT_UNIQUE",
            )
            valid = r["squad_nationality"] in ("Indian", "Overseas")
            if r["player_id_repeated"]:
                nreason = R_DUPLICATE
            elif not valid:
                nreason = R_BAD_VALUE
            elif r["team_corroborated"]:
                nat, nver, nsrc, nreason = r["squad_nationality"], V_DERIVED, SOURCE_SQUAD, None
            else:
                nreason = R_UNCORROBORATED
                squad_value = r["squad_nationality"]
        elif rws:
            kinds = {r["match_type"] for r in rws}
            rec["squad_match_type"] = (
                "EXACT_AMBIGUOUS" if "EXACT_AMBIGUOUS" in kinds else "VARIANT_CANDIDATE"
            )
            nreason = R_AMBIGUOUS if "EXACT_AMBIGUOUS" in kinds else R_VARIANT
        tinfo = t.loc[pid] if pid in t.index else None
        derived_nat = None
        if tinfo is not None and tinfo["t20i_appearances"] > 0:
            if bool(tinfo["plays_for_india_only"]):
                derived_nat = "Indian"
            elif bool(tinfo["plays_never_for_india"]):
                derived_nat = "Overseas"
        if nat == "Unknown":
            if derived_nat is not None:
                nat, nver = derived_nat, V_DERIVED
                nsrc = f"{SOURCE_NATIONAL_TEAM}:{tinfo['t20i_teams']}"
                nreason = None
            elif tinfo is not None and tinfo["t20i_appearances"] > 0 and nreason == R_NO_RECORD:
                nreason = R_MIXED
        if squad_value is not None and derived_nat is not None and squad_value != derived_nat:
            conflict = True
        if nsrc == SOURCE_SQUAD and derived_nat is not None and derived_nat != nat:
            conflict = True
        apps = int(tinfo["t20i_appearances"]) if tinfo is not None else 0
        first = tinfo["first_t20i_date"] if tinfo is not None else pd.NaT
        if apps > 0:
            st, sver, ssrc, sreason = "Capped", V_T20I, V_T20I, None
        else:
            st, sver, ssrc = "Unknown", V_NONE, None
            sreason = R_AFTER if pd.notna(first) and first > as_of else R_NOT_PROVEN
        rec.update(
            nationality=nat,
            nationality_verification=nver,
            nationality_source=nsrc,
            nationality_unknown_reason=nreason,
            international_status=st,
            international_status_verification=sver,
            international_status_source=ssrc,
            international_status_unknown_reason=sreason,
            conflict_flag=conflict,
            first_t20i_date=None if pd.isna(first) else str(pd.Timestamp(first).date()),
            t20i_appearances_to_as_of=apps,
            t20i_teams=tinfo["t20i_teams"] if tinfo is not None else "",
            as_of_date=cfg["as_of_date"],
            classification_version=cfg["version"],
        )
        recs.append(rec)
    base = pd.DataFrame(recs).sort_values("player_id").reset_index(drop=True)
    unresolved = ev[ev["match_type"] != "EXACT_UNIQUE"].copy()
    unresolved["reason"] = unresolved["match_type"].map(
        {
            "EXACT_AMBIGUOUS": "More than one player_id has this exact name; user must supply the id",
            "VARIANT_CANDIDATE": "Only a spelling-variant candidate exists; NOT applied, user must confirm",
            "NO_MATCH": "No player in the data has this name; user must supply the id",
        }
    )
    return {"classification": base, "evidence": ev, "unresolved": unresolved}


# ----------------------------------------------------------------------------- coverage


def coverage(cls: pd.DataFrame, scored_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Counts per nationality x status combination (all nine, including Unknown)."""

    def combos(df: pd.DataFrame) -> list[dict[str, Any]]:
        c = Counter(zip(df["nationality"], df["international_status"], strict=False))
        return [
            {"nationality": n, "international_status": s, "players": int(c.get((n, s), 0))}
            for n in NATIONALITIES
            for s in STATUSES
        ]

    def tally(df: pd.DataFrame, col: str) -> dict[str, int]:
        return {str(k): int(v) for k, v in df[col].value_counts(dropna=False).items()}

    out: dict[str, Any] = {
        "classification_version": CLASSIFICATION_VERSION,
        "players_total": int(len(cls)),
        "combinations_all_players": combos(cls),
        "nationality_verification": tally(cls, "nationality_verification"),
        "status_verification": tally(cls, "international_status_verification"),
        "nationality_unknown_reasons": tally(
            cls[cls["nationality"] == "Unknown"], "nationality_unknown_reason"
        ),
        "status_unknown_reasons": tally(
            cls[cls["international_status"] == "Unknown"], "international_status_unknown_reason"
        ),
        "uncapped_verified_count": int(
            (
                (cls["international_status"] == "Uncapped")
                & (cls["international_status_verification"] == V_SOURCE)
            ).sum()
        ),
        "conflicts": int(cls["conflict_flag"].sum()),
    }
    if scored_ids is not None:
        ids = {int(i) for i in scored_ids}
        sub = cls[cls["player_id"].isin(ids)]
        out["scored_players_total"] = int(len(sub))
        out["combinations_scored_players"] = combos(sub)
    return out
