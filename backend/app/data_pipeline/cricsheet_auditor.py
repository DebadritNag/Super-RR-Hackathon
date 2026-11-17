"""Audit of Cricsheet JSON directories (read-only)."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from app.core.logging import get_logger

log = get_logger(__name__)


def iter_match_files(directory: Path):
    """Yield <id>.json files, sorted by numeric id. Non-json files are ignored."""
    files = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".json"]
    yield from sorted(files, key=lambda p: (len(p.stem), p.stem))


# Spelling variants of the same team name that differ between sources (matching aid only).
TEAM_ALIASES = {"bangalore": "bengaluru", "unitedstatesofamerica": "unitedstates"}


def normalise_team(name: str | None) -> str:
    key = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    for old, new in TEAM_ALIASES.items():
        key = key.replace(old, new)
    return key


def summarise_innings(inn: dict) -> dict:
    total = batter = extras = wides = noballs = byes = legbyes = penalty = legal = wkts = 0
    n_deliveries = 0
    for ov in inn.get("overs", []):
        for d in ov.get("deliveries", []):
            n_deliveries += 1
            r = d.get("runs", {})
            total += r.get("total", 0)
            batter += r.get("batter", 0)
            extras += r.get("extras", 0)
            ex = d.get("extras", {})
            wides += ex.get("wides", 0)
            noballs += ex.get("noballs", 0)
            byes += ex.get("byes", 0)
            legbyes += ex.get("legbyes", 0)
            penalty += ex.get("penalty", 0)
            if "wides" not in ex and "noballs" not in ex:
                legal += 1
            wkts += len(d.get("wickets", []))
    return {
        "team": inn.get("team"),
        "super_over": bool(inn.get("super_over", False)),
        "deliveries": n_deliveries,
        "legal_balls": legal,
        "total": total,
        "batter": batter,
        "extras": extras,
        "wides": wides,
        "noballs": noballs,
        "byes": byes,
        "legbyes": legbyes,
        "penalty": penalty,
        "wickets": wkts,
        "has_target": "target" in inn,
        "has_powerplays": "powerplays" in inn,
    }


def _record(directory: str, path: Path, data: dict) -> dict:
    info = data.get("info", {})
    meta = data.get("meta", {})
    teams = info.get("teams") or []
    dates = info.get("dates") or []
    outcome = info.get("outcome", {}) or {}
    event = info.get("event", {}) or {}
    innings = [summarise_innings(i) for i in data.get("innings", [])]
    return {
        "match_id": path.stem,
        "directory": directory,
        "date": dates[0] if dates else None,
        "n_dates": len(dates),
        "team_a": sorted(teams)[0] if teams else None,
        "team_b": sorted(teams)[1] if len(teams) > 1 else None,
        "teams_key": "|".join(sorted(normalise_team(t) for t in teams)),
        "event_name": event.get("name"),
        "match_number": event.get("match_number"),
        "stage": event.get("stage"),
        "match_type": info.get("match_type"),
        "gender": info.get("gender"),
        "team_type": info.get("team_type"),
        "season": str(info.get("season")) if info.get("season") is not None else None,
        "venue": info.get("venue"),
        "city": info.get("city"),
        "data_version": meta.get("data_version"),
        "outcome_keys": ",".join(sorted(outcome.keys())),
        "winner": outcome.get("winner"),
        "result": outcome.get("result"),
        "dls_method": outcome.get("method"),
        "innings_json": json.dumps(innings),
        "n_innings": len(innings),
    }


def audit_cricsheet_dir(directory: Path, expected: int | None) -> tuple[dict, list[dict]]:
    """Single pass. Returns (audit dict, per-match records)."""
    cnt: dict[str, Counter] = {
        k: Counter()
        for k in (
            "data_version",
            "revision",
            "top_keys",
            "info_keys",
            "outcome_keys",
            "outcome_by_keys",
            "event_name",
            "gender",
            "team_type",
            "match_type",
            "innings_keys",
            "delivery_keys",
            "extras_keys",
            "n_innings",
        )
    }
    flags: Counter = Counter()
    records: list[dict] = []
    errors: list[dict] = []
    dmin = dmax = None
    n_json = 0
    all_files = list(directory.iterdir())
    for path in iter_match_files(directory):
        n_json += 1
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            log.warning("cannot read %s: %s", path, exc)
            errors.append({"file": path.name, "error": str(exc)})
            continue
        records.append(_record(directory.name, path, data))
        cnt["top_keys"].update(data.keys())
        meta = data.get("meta", {})
        cnt["data_version"][str(meta.get("data_version"))] += 1
        cnt["revision"][str(meta.get("revision"))] += 1
        info = data.get("info", {})
        cnt["info_keys"].update(info.keys())
        outcome = info.get("outcome", {}) or {}
        cnt["outcome_keys"].update(outcome.keys())
        cnt["outcome_by_keys"][",".join(sorted(outcome.keys())) or "(none)"] += 1
        cnt["event_name"][str((info.get("event") or {}).get("name"))] += 1
        cnt["gender"][str(info.get("gender"))] += 1
        cnt["team_type"][str(info.get("team_type"))] += 1
        cnt["match_type"][str(info.get("match_type"))] += 1
        innings = data.get("innings", [])
        cnt["n_innings"][str(len(innings))] += 1
        for inn in innings:
            cnt["innings_keys"].update(inn.keys())
            if inn.get("super_over"):
                flags["innings_super_over"] += 1
            for ov in inn.get("overs", []):
                for d in ov.get("deliveries", []):
                    cnt["delivery_keys"].update(d.keys())
                    cnt["extras_keys"].update((d.get("extras") or {}).keys())
        if "registry" in info:
            flags["has_registry"] += 1
        if "missing" in data:
            flags["has_missing"] += 1
        if outcome.get("method"):
            flags["dls_method"] += 1
        dates = info.get("dates") or []
        for dt in dates:
            dmin = dt if dmin is None or dt < dmin else dmin
            dmax = dt if dmax is None or dt > dmax else dmax
    return (
        {
            "directory": directory.name,
            "total_files_in_dir": len(all_files),
            "json_files": n_json,
            "non_json_files": [p.name for p in all_files if p.suffix.lower() != ".json"],
            "expected_by_spec": expected,
            "delta_json_vs_spec": None if expected is None else n_json - expected,
            "parsed_ok": len(records),
            "read_errors": errors,
            "date_min": dmin,
            "date_max": dmax,
            "flags": dict(flags),
            "counters": {
                k: dict(v.most_common(40 if k == "event_name" else 100)) for k, v in cnt.items()
            },
            "n_distinct_event_names": len(cnt["event_name"]),
        },
        records,
    )


def build_index(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame.from_records(records)


def cross_directory_overlap(index: pd.DataFrame) -> dict:
    """Overlap across directories by match id (file name) and by date + teams."""
    out: dict = {"total_index_rows": int(len(index))}
    out["rows_per_directory"] = index.groupby("directory").size().astype(int).to_dict()
    out["distinct_match_ids"] = int(index["match_id"].nunique())
    dup = index.groupby("match_id")["directory"].apply(lambda s: sorted(set(s)))
    dup_multi = dup[dup.map(len) > 1]
    out["match_ids_in_multiple_directories"] = int(len(dup_multi))
    pair_counts: Counter = Counter("+".join(v) for v in dup_multi)
    out["id_overlap_by_directory_combo"] = dict(pair_counts.most_common())
    out["id_overlap_samples"] = {k: v for k, v in list(dup_multi.items())[:10]}
    out["duplicate_ids_within_same_directory"] = int(
        index.duplicated(["directory", "match_id"]).sum()
    )
    k = index.assign(key=index["date"].astype(str) + "#" + index["teams_key"])
    g = k.groupby("key")
    multi = g["match_id"].nunique()
    out["date_teams_keys"] = int(len(multi))
    out["date_teams_keys_with_multiple_distinct_match_ids"] = int((multi > 1).sum())
    out["date_teams_samples"] = [
        {"key": key, "match_ids": sorted(k[k["key"] == key]["match_id"].unique())}
        for key in list(multi[multi > 1].index[:10])
    ]
    # Directory-pair overlap by date+teams (distinct ids)
    dirs_per_key = g["directory"].apply(lambda s: tuple(sorted(set(s))))
    combo = Counter("+".join(v) for v in dirs_per_key if len(v) > 1)
    out["date_teams_overlap_by_directory_combo"] = dict(combo.most_common())
    return out


def ipl_overlap_with_csv(index: pd.DataFrame, matches: pd.DataFrame, comps: pd.DataFrame) -> dict:
    """Cricsheet ipl_male_json vs official IPL matches by date and normalised team names.

    matches needs match_id, comp_id, match_date, home_team, away_team; comps needs comp_id,
    comp_name. Report only; no mapping table is produced here.
    """
    ipl_comp = comps[
        comps["comp_name"].str.contains(r"^IPL\b|Indian Premier League", case=False, regex=True)
    ]
    csv_ipl = matches[matches["comp_id"].isin(ipl_comp["comp_id"])].copy()
    csv_ipl["teams_key"] = [
        "|".join(sorted([normalise_team(a), normalise_team(b)]))
        for a, b in zip(csv_ipl["home_team"], csv_ipl["away_team"])
    ]
    csv_ipl["key"] = csv_ipl["match_date"].astype(str) + "#" + csv_ipl["teams_key"]
    cs = index[index["directory"] == "ipl_male_json"].copy()
    cs["key"] = cs["date"].astype(str) + "#" + cs["teams_key"]
    csv_counts = csv_ipl.groupby("key").size()
    cs_counts = cs.groupby("key").size()
    both = set(csv_counts.index) & set(cs_counts.index)
    ambiguous = {k for k in both if csv_counts[k] > 1 or cs_counts[k] > 1}
    csv_only = csv_ipl[~csv_ipl["key"].isin(cs_counts.index)]
    cs_only = cs[~cs["key"].isin(csv_counts.index)]
    return {
        "ipl_competitions_in_csv": ipl_comp[["comp_id", "comp_name"]].to_dict("records"),
        "csv_ipl_matches": int(len(csv_ipl)),
        "cricsheet_ipl_matches": int(len(cs)),
        "matched_keys": int(len(both)),
        "ambiguous_keys": int(len(ambiguous)),
        "csv_ipl_unmatched": int(len(csv_only)),
        "cricsheet_ipl_unmatched": int(len(cs_only)),
        "csv_ipl_unmatched_samples": csv_only[["match_id", "match_date", "home_team", "away_team"]]
        .head(15)
        .to_dict("records"),
        "cricsheet_ipl_unmatched_samples": cs_only[
            ["match_id", "date", "team_a", "team_b", "event_name"]
        ]
        .head(15)
        .to_dict("records"),
        "cricsheet_ipl_date_range": [cs["date"].min(), cs["date"].max()],
        "csv_ipl_date_range": [csv_ipl["match_date"].min(), csv_ipl["match_date"].max()],
        "note": "Matching is by exact date and normalised team names only; "
        "no mapping tables are created in Phase 1.",
    }
