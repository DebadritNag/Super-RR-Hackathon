"""Restricted TEST-set definitions (Phase 5). Definition only: TEST is never evaluated here.

Three sets are frozen in a manifest with hashes for one future evaluation under a new lock log:
  PRIMARY_RESTRICTED   OFFICIAL_VERIFIED, plus matches on or before ``core_end`` whose date class is
                       DATE_CONSISTENT_ACROSS_SOURCES
  STRICT_OFFICIAL_ONLY only matches in the user-supplied official verification record
  SENSITIVITY_ALL      every TEST match Phase 4 evaluated

Membership is computed over the matches present in the Phase 4 state (matches with deliveries).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

import pandas as pd

from app.phase5.date_verification import CONSISTENT

PRIMARY = "PRIMARY_RESTRICTED"
STRICT = "STRICT_OFFICIAL_ONLY"
ALL = "SENSITIVITY_ALL"
SET_NAMES = (PRIMARY, STRICT, ALL)
RULES = {
    PRIMARY: "OFFICIAL_VERIFIED, or date <= core_end and class DATE_CONSISTENT_ACROSS_SOURCES",
    STRICT: "match in the user-supplied official verification record with an unchanged date",
    ALL: "all TEST matches, as Phase 4 evaluated them",
}


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_membership(check: pd.DataFrame, core_end: str, state_ids: set[int]) -> pd.DataFrame:
    """Long table (match_id, set_name, member) over matches in the Phase 4 state."""
    end = date.fromisoformat(core_end)
    rows = []
    for r in check.itertuples():
        if int(r.match_id) not in state_ids:
            continue
        official = r.official_status == "OFFICIAL_VERIFIED"
        early_ok = date.fromisoformat(r.original_match_date) <= end and r.date_class == CONSISTENT
        member = {PRIMARY: official or early_ok, STRICT: official, ALL: True}
        rows.extend(
            {"match_id": int(r.match_id), "set_name": s, "member": bool(member[s])}
            for s in SET_NAMES
        )
    return pd.DataFrame(rows, columns=["match_id", "set_name", "member"])


def _counts(ids: set[int], state: pd.DataFrame, comp_type: dict[int, str]) -> dict[str, Any]:
    sub = state[state["match_id"].isin(ids)]
    players = set(sub["striker_id"].dropna().astype(int)) | set(
        sub["bowler_id"].dropna().astype(int)
    )
    by_comp: dict[str, dict[str, int]] = {}
    for ct in sorted({comp_type[i] for i in ids}):
        cs = {i for i in ids if comp_type[i] == ct}
        s = sub[sub["match_id"].isin(cs)]
        p = set(s["striker_id"].dropna().astype(int)) | set(s["bowler_id"].dropna().astype(int))
        by_comp[ct] = {"matches": len(cs), "deliveries": int(len(s)), "players": len(p)}
    return {
        "matches": len(ids),
        "deliveries": int(len(sub)),
        "players": len(players),
        "by_competition_type": by_comp,
    }


def set_counts(
    membership: pd.DataFrame, state: pd.DataFrame, comp_type: dict[int, str]
) -> dict[str, dict[str, Any]]:
    out = {}
    for s in SET_NAMES:
        ids = set(membership[(membership["set_name"] == s) & membership["member"]]["match_id"])
        out[s] = _counts({int(i) for i in ids}, state, comp_type)
    return out


def excluded_effect(
    membership: pd.DataFrame,
    state: pd.DataFrame,
    comp_type: dict[int, str],
    set_name: str = PRIMARY,
) -> dict[str, Any]:
    """Matches, deliveries and players removed from ``set_name`` relative to SENSITIVITY_ALL."""
    mem = membership[membership["set_name"] == set_name]
    inc = {int(i) for i in mem[mem["member"]]["match_id"]}
    exc = {int(i) for i in mem[~mem["member"]]["match_id"]}
    ex = _counts(exc, state, comp_type) if exc else {"matches": 0, "deliveries": 0, "players": 0}
    s_ex = state[state["match_id"].isin(exc)]
    s_in = state[state["match_id"].isin(inc)]
    p_ex = set(s_ex["striker_id"].dropna().astype(int)) | set(
        s_ex["bowler_id"].dropna().astype(int)
    )
    p_in = set(s_in["striker_id"].dropna().astype(int)) | set(
        s_in["bowler_id"].dropna().astype(int)
    )
    return {
        "excluded_matches": ex["matches"],
        "excluded_deliveries": ex["deliveries"],
        "players_in_excluded_matches": len(p_ex),
        "players_only_in_excluded_matches": len(p_ex - p_in),
    }


def build_manifest(
    membership: pd.DataFrame,
    check: pd.DataFrame,
    state: pd.DataFrame,
    comp_type: dict[int, str],
    core_end: str,
    inputs: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Manifest with per-set id lists, hashes and counts. ``self_sha256`` covers everything else."""
    dates = {int(r.match_id): r.original_match_date for r in check.itertuples()}
    sets: dict[str, Any] = {}
    counts = set_counts(membership, state, comp_type)
    for s in SET_NAMES:
        ids = sorted(
            int(i)
            for i in membership[(membership["set_name"] == s) & membership["member"]]["match_id"]
        )
        sets[s] = {
            "rule": RULES[s],
            "match_ids": ids,
            "ids_and_original_dates_sha256": sha256_json([[i, dates[i]] for i in ids]),
            "counts": counts[s],
        }
    manifest: dict[str, Any] = {
        "manifest_version": "phase5_test_set_manifest_v1",
        "status": "EXPERIMENTAL_NOT_VALIDATED",
        "test_evaluated_in_phase5": False,
        "core_end": core_end,
        "sets": sets,
        "excluded_from_primary": excluded_effect(membership, state, comp_type, PRIMARY),
        "excluded_from_strict": excluded_effect(membership, state, comp_type, STRICT),
        "inputs": inputs,
    }
    if extra:
        manifest.update(extra)
    manifest["self_sha256"] = sha256_json(manifest)
    return manifest


def verify_manifest(manifest: dict[str, Any]) -> bool:
    body = {k: v for k, v in manifest.items() if k != "self_sha256"}
    return sha256_json(body) == manifest.get("self_sha256")
