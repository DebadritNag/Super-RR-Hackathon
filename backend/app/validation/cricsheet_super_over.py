"""Cricsheet Super Over validation of official innings 3 and 4 (validation-only).

Cricsheet is read from the JSON files / the staging index only. Nothing is written to DuckDB, the
official innings are never relabelled, and the proposed statuses exist only in the output JSON.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics.reporting import PROXY_FIELDS, fmt, md_table
from app.data_pipeline.cricsheet_auditor import _record, iter_match_files, normalise_team

CONFIRMED = "CONFIRMED_SUPER_OVER"
UNCONFIRMED = "UNCONFIRMED"
CONFLICTING = "CONFLICTING"
CLASSES = (CONFIRMED, UNCONFIRMED, CONFLICTING)

MAPPED_UNIQUE = "MAPPED_UNIQUE"
MAPPED_AMBIGUOUS = "MAPPED_AMBIGUOUS"
NOT_FOUND = "NOT_FOUND"

PROPOSED_STATUS = {
    CONFIRMED: "CONFIRMED_SUPER_OVER_BY_CRICSHEET",
    UNCONFIRMED: "UNCONFIRMED_INNINGS_3_4",
    CONFLICTING: "CONFLICT_INNINGS_3_4",
}

# Canonical directory when the same Cricsheet match id sits in several directories.
DIRECTORY_PRIORITY = (
    "ipl_male_json",
    "it20s_male_json",
    "t20s_male_json",
    "bbl_male_json",
    "cpl_male_json",
    "mlc_male_json",
    "india_male_json",
    "2026_male_json",
)

OFFICIAL_SQL = """
SELECT m.match_id, m.match_date, m.competition_type, c.comp_name, m.result_status, m.result,
       m.home_team, m.away_team, i.innings_number, t.team_name, i.delivery_count,
       i.legal_ball_count, i.source_total_runs, i.wicket_rows, i.innings_role_status,
       coalesce(x.dismissed_without_flag, 0) AS dismissed_without_flag
FROM matches m
JOIN competitions c USING (comp_id)
JOIN innings i USING (match_id)
JOIN teams t ON t.team_id = i.batting_team_id
LEFT JOIN (
    SELECT match_id, innings_number,
           sum(CASE WHEN dismissed_player_id IS NOT NULL AND NOT is_wicket THEN 1 ELSE 0 END)
               AS dismissed_without_flag
    FROM deliveries GROUP BY match_id, innings_number
) x ON x.match_id = i.match_id AND x.innings_number = i.innings_number
WHERE m.has_deliveries
ORDER BY m.match_id, i.innings_number
"""


# ------------------------------------------------------------------------------ official side


def load_official_matches(db) -> list[dict[str, Any]]:
    """Official matches with deliveries and their innings aggregates (read-only SQL)."""
    out: dict[int, dict[str, Any]] = {}
    for r in db.query(OFFICIAL_SQL):
        mid = int(r[0])
        m = out.get(mid)
        if m is None:
            m = out[mid] = {
                "match_id": mid,
                "match_date": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "competition_type": r[2],
                "comp_name": r[3],
                "result_status": r[4],
                "result": r[5],
                "home_team": r[6],
                "away_team": r[7],
                "teams_key": "|".join(sorted((normalise_team(r[6]), normalise_team(r[7])))),
                "innings": [],
            }
        m["innings"].append(
            {
                "innings_number": int(r[8]),
                "batting_team": r[9],
                "deliveries": int(r[10]),
                "legal_balls": int(r[11]),
                "total": int(r[12]),
                "wickets": int(r[13]),
                "innings_role_status": r[14],
                "dismissed_without_flag": int(r[15]),
            }
        )
    return list(out.values())


# ---------------------------------------------------------------------------- Cricsheet side


def load_cricsheet_records(
    index_path: Path | None, cricsheet_root: Path, dirs: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Per-file Cricsheet summaries from the staging index, rebuilt from the JSON when absent."""
    if index_path is not None and Path(index_path).exists():
        df = pd.read_parquet(index_path)
        df = df[df["directory"].isin(dirs)]
        return df.to_dict("records")
    records: list[dict[str, Any]] = []
    for name in dirs:
        d = Path(cricsheet_root) / name
        if not d.is_dir():
            continue
        for path in iter_match_files(d):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            records.append(_record(name, path, data))
    return records


def _priority(directory: str) -> int:
    return DIRECTORY_PRIORITY.index(directory) if directory in DIRECTORY_PRIORITY else 99


def dedupe_by_match_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """One entry per Cricsheet match id; copies in other directories are compared, not merged."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        groups[str(rec["match_id"])].append(rec)
    out: dict[str, dict[str, Any]] = {}
    for mid, recs in groups.items():
        recs = sorted(recs, key=lambda r: (_priority(r["directory"]), r["directory"]))
        canon = recs[0]
        sig = {(r.get("date"), r.get("teams_key"), r.get("innings_json")) for r in recs}
        out[mid] = {
            "match_id": mid,
            "record": canon,
            "directories": [r["directory"] for r in recs],
            "copies_agree": len(sig) == 1,
            "innings": json.loads(canon["innings_json"]) if canon.get("innings_json") else [],
        }
    return out


def _all_dates(entry: dict[str, Any], cricsheet_root: Path | None) -> list[str]:
    rec = entry["record"]
    dates = [rec["date"]] if rec.get("date") else []
    if int(rec.get("n_dates") or 1) > 1 and cricsheet_root is not None:
        path = Path(cricsheet_root) / rec["directory"] / f"{rec['match_id']}.json"
        try:
            dates = list(json.loads(path.read_text(encoding="utf-8"))["info"].get("dates") or [])
        except (OSError, ValueError, KeyError):
            pass
    return dates


def build_lookup(
    deduped: dict[str, dict[str, Any]], cricsheet_root: Path | None = None
) -> dict[tuple[str, str], list[str]]:
    """(date, normalised team pair) -> sorted distinct Cricsheet match ids."""
    lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for mid, entry in deduped.items():
        for d in _all_dates(entry, cricsheet_root):
            lookup[(str(d), entry["record"]["teams_key"])].add(mid)
    return {k: sorted(v) for k, v in lookup.items()}


# ------------------------------------------------------------------------------ mapping logic


def competition_check(official: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    ctype = official["competition_type"]
    if ctype == "T20I":
        ok = str(rec.get("team_type")) == "international"
        return {"rule": "T20I requires Cricsheet team_type international", "passed": ok}
    if ctype == "IPL":
        ok = "indian premier league" in str(rec.get("event_name") or "").lower()
        return {"rule": "IPL requires Cricsheet event name Indian Premier League", "passed": ok}
    return {"rule": "no competition rule for OTHER_T20", "passed": True}


def regulation_sanity(official: dict[str, Any], cs_innings: list[dict]) -> dict[str, Any]:
    """Official innings 1/2 against the non-super-over Cricsheet innings (team, balls, runs)."""
    off = [i for i in official["innings"] if i["innings_number"] in (1, 2)]
    reg = [i for i in cs_innings if not i.get("super_over")]
    failures: list[str] = []
    notes: list[str] = []
    if len(off) != len(reg):
        failures.append(f"REGULATION_INNINGS_COUNT official={len(off)} cricsheet={len(reg)}")
    for pos, (o, c) in enumerate(zip(off, reg), start=1):
        if normalise_team(o["batting_team"]) != normalise_team(c.get("team")):
            failures.append(f"REG{pos}_BATTING_TEAM")
        if o["deliveries"] != c.get("deliveries"):
            failures.append(f"REG{pos}_DELIVERY_COUNT")
        if o["total"] != c.get("total"):
            failures.append(f"REG{pos}_TOTAL_RUNS")
        if o["wickets"] != c.get("wickets"):
            failures.append(f"REG{pos}_WICKETS")
            gap = (c.get("wickets") or 0) - o["wickets"]
            if gap > 0 and gap == o.get("dismissed_without_flag", 0):
                notes.append(
                    f"REG{pos}_WICKETS gap of {gap} equals the official rows with a dismissed "
                    "player but is_wicket false (open_dismissed_player_without_wicket_flag); "
                    "the failure is kept, not waived"
                )
    return {"passed": not failures, "failures": failures, "notes": notes}


def map_official_match(
    official: dict[str, Any],
    lookup: dict[tuple[str, str], list[str]],
    deduped: dict[str, dict[str, Any]],
    official_key_counts: Counter,
) -> dict[str, Any]:
    key = (official["match_date"], official["teams_key"])
    ids = lookup.get(key, [])
    official_dupes = official_key_counts.get(key, 0)
    if not ids:
        return {"status": NOT_FOUND, "cricsheet_match_id": None, "candidates": []}
    if len(ids) > 1 or official_dupes > 1:
        return {"status": MAPPED_AMBIGUOUS, "cricsheet_match_id": None, "candidates": ids}
    entry = deduped[ids[0]]
    sanity = regulation_sanity(official, entry["innings"])
    comp = competition_check(official, entry["record"])
    return {
        "status": MAPPED_UNIQUE,
        "cricsheet_match_id": ids[0],
        "candidates": ids,
        "directories": entry["directories"],
        "copies_agree": entry["copies_agree"],
        "sanity": {
            **sanity,
            "competition_check": comp,
            "passed": sanity["passed"] and comp["passed"],
        },
    }


def classify_super_over(
    official_so: list[dict[str, Any]],
    mapping: dict[str, Any],
    cs_innings: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Pure classification of official innings 3/4 (`official_so`) against Cricsheet innings."""

    def result(cls: str, reasons: list[str], positions=None, extra=None) -> dict[str, Any]:
        return {
            "classification": cls,
            "reason_codes": reasons,
            "positions": positions or [],
            "proposed_innings_role_status": PROPOSED_STATUS[cls],
            **(extra or {}),
        }

    status = mapping.get("status")
    if status != MAPPED_UNIQUE:
        return result(UNCONFIRMED, [f"MAPPING_{status}"])
    if not cs_innings or not any((i.get("deliveries") or 0) > 0 for i in cs_innings):
        return result(UNCONFIRMED, ["CRICSHEET_NO_BALL_DATA"])
    cs_so = [i for i in cs_innings if i.get("super_over")]
    if not mapping.get("sanity", {}).get("passed", False):
        # Context only: the verdict stays UNCONFIRMED because the match mapping is not trusted.
        sup, sup_reasons = compare_positions(official_so, cs_so) if cs_so else ([], [])
        return result(
            UNCONFIRMED,
            ["MAPPING_SANITY_FAILED"],
            extra={
                "supplementary_positions_not_used_for_verdict": sup,
                "super_over_fields_agree_ignoring_sanity": bool(cs_so) and not sup_reasons,
            },
        )
    if not cs_so:
        return result(CONFLICTING, ["NO_SUPER_OVER_IN_CRICSHEET"])
    positions, reasons = compare_positions(official_so, cs_so)
    return result(CONFLICTING if reasons else CONFIRMED, reasons, positions)


def compare_positions(
    official_so: list[dict[str, Any]], cs_so: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Field-by-field comparison of official innings 3/4 with Cricsheet Super Over innings."""
    positions: list[dict[str, Any]] = []
    reasons: list[str] = []
    if len(cs_so) != len(official_so):
        reasons.append(
            f"SUPER_OVER_COUNT_MISMATCH official={len(official_so)} cricsheet={len(cs_so)}"
        )
    for pos, (o, c) in enumerate(zip(official_so, cs_so), start=1):
        checks = {
            "batting_team": normalise_team(o["batting_team"]) == normalise_team(c.get("team")),
            "deliveries": o["deliveries"] == c.get("deliveries"),
            "legal_balls": o["legal_balls"] == c.get("legal_balls"),
            "total_runs": o["total"] == c.get("total"),
            "wickets": o["wickets"] == c.get("wickets"),
        }
        positions.append(
            {
                "position": pos,
                "official_innings_number": o["innings_number"],
                "official": {
                    k: o[k]
                    for k in ("batting_team", "deliveries", "legal_balls", "total", "wickets")
                },
                "cricsheet": {
                    k: c.get(k) for k in ("team", "deliveries", "legal_balls", "total", "wickets")
                },
                "checks": checks,
            }
        )
        reasons.extend(f"POS{pos}_{k.upper()}_MISMATCH" for k, ok in checks.items() if not ok)
    return positions, reasons


# ----------------------------------------------------------------------------- raw JSON facts


def read_raw_meta(cricsheet_root: Path, directory: str, match_id: str) -> dict[str, Any]:
    """Outcome, event and venue facts from the raw Cricsheet file (validation context only)."""
    path = Path(cricsheet_root) / directory / f"{match_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"available": False}
    info = data.get("info", {})
    outcome = info.get("outcome", {}) or {}
    so_innings = [i for i in data.get("innings", []) if i.get("super_over")]
    return {
        "available": True,
        "file": f"{directory}/{match_id}.json",
        "event": info.get("event"),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "dates": info.get("dates"),
        "outcome": outcome,
        "outcome_has_eliminator": "eliminator" in outcome,
        "outcome_has_bowl_out": "bowl_out" in outcome,
        "super_over_innings_flags": [
            {k: v for k, v in i.items() if k != "overs"} for i in so_innings
        ],
        "super_over_overs": [
            [
                {"over": ov.get("over"), "deliveries": len(ov.get("deliveries", []))}
                for ov in i.get("overs", [])
            ]
            for i in so_innings
        ],
    }


# ----------------------------------------------------------------------------------- driver


def official_innings_view(official: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(i) for i in official["innings"]]


def validate_super_overs(
    official: list[dict[str, Any]],
    records: list[dict[str, Any]],
    cricsheet_root: Path,
) -> dict[str, Any]:
    """Classify every official match with innings 3/4 and run the converse check."""
    deduped = dedupe_by_match_id(records)
    lookup = build_lookup(deduped, cricsheet_root)
    key_counts: Counter = Counter((m["match_date"], m["teams_key"]) for m in official)

    matches: list[dict[str, Any]] = []
    converse: list[dict[str, Any]] = []
    mapping_stats: Counter = Counter()
    for m in sorted(official, key=lambda x: x["match_id"]):
        so = [i for i in m["innings"] if i["innings_number"] >= 3]
        mapping = map_official_match(m, lookup, deduped, key_counts)
        mapping_stats[mapping["status"]] += 1
        cs_entry = deduped.get(mapping.get("cricsheet_match_id") or "")
        cs_innings = cs_entry["innings"] if cs_entry else None
        if so:
            verdict = classify_super_over(so, mapping, cs_innings)
            raw = (
                read_raw_meta(cricsheet_root, cs_entry["record"]["directory"], cs_entry["match_id"])
                if cs_entry
                else None
            )
            matches.append(
                {
                    "match_id": m["match_id"],
                    "match_date": m["match_date"],
                    "competition_type": m["competition_type"],
                    "comp_name": m["comp_name"],
                    "teams": [m["home_team"], m["away_team"]],
                    "official_result_status": m["result_status"],
                    "official_result": m["result"],
                    "official_result_text_mentions_super_over": "super over"
                    in str(m["result"] or "").lower(),
                    "official_innings": official_innings_view(m),
                    "mapping": mapping,
                    "cricsheet_innings": cs_innings,
                    "cricsheet_raw": raw,
                    **verdict,
                }
            )
        elif (
            mapping["status"] == MAPPED_UNIQUE
            and cs_innings
            and any(i.get("super_over") for i in cs_innings)
        ):
            converse.append(
                {
                    "match_id": m["match_id"],
                    "match_date": m["match_date"],
                    "cricsheet_match_id": mapping["cricsheet_match_id"],
                    "mapping_sanity_passed": mapping["sanity"]["passed"],
                    "cricsheet_super_over_innings": [i for i in cs_innings if i.get("super_over")],
                    "note": "Cricsheet has a Super Over but the official data has no innings 3/4",
                }
            )

    counts = Counter(x["classification"] for x in matches)
    so_entries = [e for e in deduped.values() if any(i.get("super_over") for i in e["innings"])]
    return {
        **PROXY_FIELDS,
        "validation_only": True,
        "cricsheet_loaded_into_database": False,
        "official_data_modified": False,
        "official_matches_with_innings_3_4": len(matches),
        "classification_counts": {c: counts.get(c, 0) for c in CLASSES},
        "matches": matches,
        "converse_check": {
            "description": "Official matches that map reliably, where Cricsheet shows a Super Over "
            "and the official data has no innings 3/4",
            "official_matches_checked": len(official),
            "mapping_status_counts": dict(sorted(mapping_stats.items())),
            "official_missing_super_over": converse,
            "count": len(converse),
        },
        "cricsheet_context": {
            "index_rows": len(records),
            "distinct_match_ids": len(deduped),
            "ids_in_multiple_directories": sum(
                1 for e in deduped.values() if len(e["directories"]) > 1
            ),
            "ids_with_disagreeing_copies": sorted(
                e["match_id"] for e in deduped.values() if not e["copies_agree"]
            ),
            "matches_with_super_over_innings": len(so_entries),
            "directory_priority": list(DIRECTORY_PRIORITY),
        },
    }


# ---------------------------------------------------------------------------------- the report


REPRESENTATION = (
    "Cricsheet marks a Super Over as extra entries in the top-level `innings` list, appended "
    'after the regulation innings, each carrying `"super_over": true`, a `team`, and `overs` '
    "numbered from 0. A tied match also carries `info.outcome.eliminator` (the winning team) "
    "next to `result: tie`; a bowl-out would appear as `info.outcome.bowl_out`."
)

UNVERIFIABLE = [
    "Official matches not found in Cricsheet cannot be checked and stay UNCONFIRMED.",
    "Cricsheet match/venue naming is not compared: the official venue table only has venue_id "
    "and venue_country, so venues are not used for mapping.",
    "Official `innings_role_status` stays UNVERIFIED for every innings 3/4; the proposed values "
    "exist only in this report and are not written anywhere.",
]

PHASE3_RULE = (
    "Phase 3 excludes innings 3 and 4 from regulation-pressure metrics by a per-metric "
    "restriction (open_innings_3_4_role_unverified), whatever the Cricsheet verdict. Cricsheet "
    "evidence is context for a later human decision on relabelling, not an automatic relabel."
)


def finalize(result: dict[str, Any]) -> dict[str, Any]:
    result["representation_in_cricsheet"] = REPRESENTATION
    result["unverifiable"] = UNVERIFIABLE
    result["phase3_rule"] = PHASE3_RULE
    return result


def render_report(res: dict[str, Any]) -> str:
    L: list[str] = ["# Cricsheet Super Over validation (innings 3 and 4)", ""]
    L += [
        "## 1. Interpretation and status",
        "",
        "- Validation only. Cricsheet JSON was read from disk; nothing was loaded into DuckDB, "
        "no official record was changed and no innings was relabelled.",
        f"- proxy_run: {fmt(res['proxy_run'])}; pressure_status: {res['pressure_status']}; "
        f"not_for_publication: {fmt(res['not_for_publication'])}.",
        f"- Official matches with innings 3/4: {res['official_matches_with_innings_3_4']}. "
        + ", ".join(f"{k}: {v}" for k, v in res["classification_counts"].items())
        + ".",
        "",
        "How Cricsheet represents a Super Over: " + res["representation_in_cricsheet"],
        "",
        "## 2. Classification per official match",
        "",
    ]
    rows = []
    for m in res["matches"]:
        rows.append(
            [
                str(m["match_id"]),
                m["match_date"],
                m["competition_type"],
                " v ".join(m["teams"]),
                m["mapping"]["status"],
                m["mapping"].get("cricsheet_match_id") or "none",
                m["classification"],
                "; ".join(m["reason_codes"]) or "none",
                m["proposed_innings_role_status"],
            ]
        )
    L.append(
        md_table(
            [
                "match",
                "date",
                "type",
                "teams",
                "mapping",
                "cricsheet id",
                "class",
                "reasons",
                "proposed status (not written)",
            ],
            rows,
        )
    )
    L += ["## 3. Evidence per match", ""]
    for m in res["matches"]:
        L += [f"### Match {m['match_id']} ({m['comp_name']}, {m['match_date']})", ""]
        L.append(
            f"Official result status: {m['official_result_status']}; result text: {m['official_result']}."
        )
        san = m["mapping"].get("sanity")
        if san:
            L.append(
                f"Regulation-innings sanity: {'passed' if san['passed'] else 'FAILED'} "
                f"({', '.join(san['failures']) or 'no failures'}); competition check: "
                f"{'passed' if san['competition_check']['passed'] else 'FAILED'}."
            )
        for note in (san or {}).get("notes", []):
            L.append(f"Note: {note}.")
        if "super_over_fields_agree_ignoring_sanity" in m:
            L.append(
                "Context only, not used for the verdict: Super Over fields agree with Cricsheet "
                f"if the mapping were trusted: {fmt(m['super_over_fields_agree_ignoring_sanity'])}."
            )
        raw = m.get("cricsheet_raw")
        if raw and raw.get("available"):
            L.append(
                f"Cricsheet file {raw['file']}; outcome {json.dumps(raw['outcome'])}; "
                f"event {json.dumps(raw['event'])}."
            )
        L.append("")
        L.append(
            md_table(
                [
                    "innings",
                    "batting team",
                    "deliveries",
                    "legal",
                    "runs",
                    "wickets",
                    "official role status",
                ],
                [
                    [
                        i["innings_number"],
                        i["batting_team"],
                        i["deliveries"],
                        i["legal_balls"],
                        i["total"],
                        i["wickets"],
                        i["innings_role_status"],
                    ]
                    for i in m["official_innings"]
                    if i["innings_number"] >= 3
                ],
            )
        )
        if m["cricsheet_innings"]:
            L.append(
                md_table(
                    [
                        "cricsheet innings",
                        "team",
                        "super_over",
                        "deliveries",
                        "legal",
                        "runs",
                        "wickets",
                    ],
                    [
                        [
                            n,
                            c["team"],
                            c["super_over"],
                            c["deliveries"],
                            c["legal_balls"],
                            c["total"],
                            c["wickets"],
                        ]
                        for n, c in enumerate(m["cricsheet_innings"], start=1)
                    ],
                )
            )
        else:
            L += ["No Cricsheet counterpart was found, so no side-by-side evidence exists.", ""]
    cv = res["converse_check"]
    L += [
        "## 4. Converse check",
        "",
        f"{cv['description']}: {cv['count']} of {cv['official_matches_checked']} official matches "
        f"with deliveries. Mapping status counts: {json.dumps(cv['mapping_status_counts'])}.",
        "",
    ]
    if cv["official_missing_super_over"]:
        L.append(
            md_table(
                ["match", "date", "cricsheet id", "sanity passed"],
                [
                    [
                        str(c["match_id"]),
                        c["match_date"],
                        c["cricsheet_match_id"],
                        c["mapping_sanity_passed"],
                    ]
                    for c in cv["official_missing_super_over"]
                ],
            )
        )
    ctx = res["cricsheet_context"]
    L += [
        "## 5. Cricsheet context and limits",
        "",
        f"Index rows {ctx['index_rows']}; distinct Cricsheet ids {ctx['distinct_match_ids']}; ids present "
        f"in several directories {ctx['ids_in_multiple_directories']}; ids whose copies disagree "
        f"{len(ctx['ids_with_disagreeing_copies'])}; matches with a Super Over innings "
        f"{ctx['matches_with_super_over_innings']}.",
        "",
    ]
    L += [f"- {u}" for u in res["unverifiable"]]
    L += ["", "## 6. Phase 3 treatment", "", res["phase3_rule"], ""]
    pres = res.get("preservation")
    if pres:
        L += [
            "## 7. Preservation",
            "",
            f"Official CSV hashes, official table hashes and Cricsheet manifests unchanged: "
            f"{fmt(pres['unchanged'])}.",
            "",
        ]
    return "\n".join(L)
