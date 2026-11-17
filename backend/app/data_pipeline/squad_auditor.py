"""Audit of the IPL squad CSV against the canonical player mapping."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pandas as pd


def norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", (name or "").lower()) if t]


def candidate_ids(name: str, by_exact: dict, by_surname: dict) -> set[str]:
    """Candidate player_ids: exact normalised match, else same surname + same first initial."""
    n = norm_name(name)
    if n in by_exact:
        return set(by_exact[n])
    toks = _tokens(name)
    if len(toks) < 2:
        return set()
    out: set[str] = set()
    for pid, pname in by_surname.get(toks[-1], []):
        ptoks = _tokens(pname)
        if ptoks and ptoks[0][:1] == toks[0][:1]:
            out.add(pid)
    return out


def audit_squad(squad_csv: Path, mapping: pd.DataFrame) -> dict:
    sq = pd.read_csv(squad_csv, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    out: dict = {"rows": int(len(sq)), "columns": list(sq.columns)}
    out["teams"] = int(sq["team_name"].nunique())
    out["players_per_team"] = sq.groupby("team_name").size().astype(int).to_dict()
    for col in ("role", "nationality", "designation"):
        out[f"{col}_counts"] = sq[col].replace("", "(blank)").value_counts().to_dict()
    out["duplicate_player_rows"] = int(sq.duplicated(["team_name", "player"]).sum())
    out["players_in_multiple_teams"] = int((sq.groupby("player")["team_name"].nunique() > 1).sum())
    out["rajasthan_royals_rows"] = sq[sq["team_name"].str.contains("Rajasthan", case=False)][
        ["player", "role", "nationality", "designation"]
    ].to_dict("records")

    by_exact: dict[str, set] = {}
    by_surname: dict[str, list] = {}
    for pid, pname in (
        mapping[["player_id", "player_name"]].drop_duplicates().itertuples(index=False)
    ):
        by_exact.setdefault(norm_name(pname), set()).add(pid)
        toks = _tokens(pname)
        if toks:
            by_surname.setdefault(toks[-1], []).append((pid, pname))
    raw_exact = set(mapping["player_name"])
    out["mapping_distinct_player_ids"] = int(mapping["player_id"].nunique())
    out["exact_case_sensitive_matches"] = int(sq["player"].isin(raw_exact).sum())
    out["exact_normalised_matches"] = int(sq["player"].map(norm_name).isin(by_exact).sum())
    cand_counts: Counter = Counter()
    unmatched: list[str] = []
    ambiguous: list[dict] = []
    for team, player in sq[["team_name", "player"]].itertuples(index=False):
        c = candidate_ids(player, by_exact, by_surname)
        k = "0" if not c else ("1" if len(c) == 1 else ">1")
        cand_counts[k] += 1
        if k == "0":
            unmatched.append(f"{player} ({team})")
        elif k == ">1":
            ambiguous.append({"player": player, "team": team, "candidates": sorted(c)[:6]})
    out["candidate_id_counts"] = dict(cand_counts)
    out["unmatched_players"] = unmatched
    out["ambiguous_players"] = ambiguous[:40]
    out["note"] = (
        "Candidates only: exact normalised name, else same surname + first initial. "
        "No identity is asserted; player_id remains the sole key."
    )
    return out
