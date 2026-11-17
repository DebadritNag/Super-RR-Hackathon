"""Experimental service layer: players, rankings, selection, presets, profiles.

All outputs are experimental (EXPERIMENTAL_NOT_VALIDATED, official_ranking = false). Presets are
parameter templates that run over the stored scores and are never relaxed silently.

Phase 5: every ranking/selection/profile/compare output passes through ``_gate`` (one function,
``app.phase5.gating.apply_gates``). Strict-uncapped requests return a structured
STRICT_UNCAPPED_DISABLED body while ``strict_uncapped_enabled`` is false; nothing is approximated.
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import BACKEND_ROOT
from app.phase4 import selection as sel
from app.phase4 import uncapped as unc
from app.phase4.constants import STATUS
from app.phase4.profiles import build_profile
from app.phase4.views import DISCLAIMER, directory_frame, ranking_frame, selection_pool
from app.phase5 import classification_v2 as c2
from app.phase5.constants import INTERNAL
from app.phase5.gating import (
    GateInput,
    RequestNeeds,
    apply_gates,
    evaluate_gates,
    failing,
    load_gate_inputs,
    publication_status,
)
from app.repositories.phase4_repo import Phase4Repository

PRESETS_FILE = BACKEND_ROOT / "config" / "phase4_selection_presets_v1.json"
DATA_REQUEST = (
    "VERIFIED_UNCAPPED players require an authoritative source keyed by player_id plus validated "
    "override rows (source, verified_by, verified_date) in config/classification_overrides_v1.csv."
)
STRICT_UNCAPPED_REASON = (
    "No authoritative player_id-keyed source of international status is loaded, so strict "
    "uncapped output is disabled. No approximation is produced."
)
STRICT_DISABLED = "STRICT_UNCAPPED_DISABLED"
UNCAPPED_GROUPS = ("IN_UNCAPPED", "OS_UNCAPPED")
RANK_SORTS = {
    "rank": "rank",
    "score": "score",
    "name": "player_name",
    "matches": "matches",
    "pressure_opportunities": "pressure_opportunities",
    "distinct_matches": "distinct_matches",
}
PLAYER_SORTS = {
    "player_id": "player_id",
    "name": "player_name",
    "matches": "matches",
    "distinct_matches": "distinct_matches",
}


class NotFoundError(LookupError):
    pass


def _none(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if v is pd.NA or v is pd.NaT:
        return None
    return v


def _int(v: Any) -> int | None:
    v = _none(v)
    return None if v is None else int(v)


def _flt(v: Any) -> float | None:
    v = _none(v)
    return None if v is None else float(v)


def group_label(group: str) -> str:
    """The UNKNOWN group is always shown as UNKNOWN_STATUS (never as uncapped)."""
    return c2.UNKNOWN_STATUS_LABEL if group == "UNKNOWN" else group


def touches_uncapped(req: dict[str, Any]) -> bool:
    """True when a composition request needs uncapped rows (min>0 or exact>0, or include mode)."""
    if req.get("uncapped_mode") == "include_uncapped":
        return True
    for g in UNCAPPED_GROUPS:
        b = req.get("groups", {}).get(g)
        if b and ((b.get("min") or 0) > 0 or (b.get("exact") or 0) > 0):
            return True
    return False


def result_row(r: pd.Series, view_rank: int | None = None) -> dict[str, Any]:
    return {
        "player_id": int(r["player_id"]),
        "name": str(r["player_name"]),
        "nationality": str(r["eff_nationality"]),
        "nationality_verification": str(r["eff_nationality_verification"]),
        "international_status": str(r["eff_status"]),
        "international_status_verification": str(r["eff_status_verification"]),
        "side": str(r["side"]),
        "format": str(r["format"]),
        "group": str(r["group"]),
        "group_label": group_label(str(r["group"])),
        "squad_role": _none(r["squad_role"]),
        "eligibility": str(r["eligibility_status"]),
        "score": _flt(r["score"]),
        "standardised_score": _flt(r["standardised_score"]),
        "rank": _int(r["rank"]),
        "view_rank": view_rank,
        "pressure_opportunities": _int(r["pressure_opportunities"]),
        "distinct_matches": _int(r["distinct_matches"]),
        "effective_sample_size": _flt(r["effective_sample_size"]),
        "interval_low": _flt(r["interval_low"]),
        "interval_high": _flt(r["interval_high"]),
        "top10_inclusion_prob": _flt(r["top10_inclusion_prob"]),
        "rank_lo": _flt(r["rank_lo"]),
        "rank_hi": _flt(r["rank_hi"]),
        "matches": int(r["matches"]),
        "restrictions_applied": _none(r["applied_restrictions"]),
    }


def paginate(df: pd.DataFrame, limit: int, offset: int) -> tuple[pd.DataFrame, int]:
    return df.iloc[offset : offset + limit], int(len(df))


class Phase4Service:
    def __init__(
        self,
        repo: Phase4Repository,
        presets_path: Path | str = PRESETS_FILE,
        gate_inputs: GateInput | None = None,
    ) -> None:
        self.repo = repo
        self.presets_path = Path(presets_path)
        # A function argument only (never an environment variable or request field), so
        # production cannot inject it. Tests use it for synthetic pass/fail fixtures.
        self._gate_override = gate_inputs
        self._gate_cache: GateInput | None = None

    @property
    def t(self):
        return self.repo.tables

    # ------------------------------------------------------------------ gating
    def gate_input(self) -> GateInput:
        if self._gate_override is not None:
            return self._gate_override
        if self._gate_cache is None:
            self._gate_cache = load_gate_inputs(self.repo.capability()["enabled"])
        return self._gate_cache

    def reset_gates(self) -> None:
        self._gate_cache = None

    def flags(self) -> dict[str, Any]:
        gates = evaluate_gates(self.gate_input(), RequestNeeds())
        return {
            "status": STATUS,
            "official_ranking": False,
            "disclaimer": DISCLAIMER,
            "publication_status": publication_status(gates),
            "gate_results": [g.as_dict() for g in gates],
        }

    def public_flags(self) -> dict[str, Any]:
        """Flags of the public descriptive directory (no publication or gate information)."""
        return {"status": STATUS, "disclaimer": DISCLAIMER, "descriptive_only": True}

    def public_disabled(self, what: str) -> dict[str, Any]:
        return {
            **self.public_flags(),
            "result_status": STRICT_DISABLED,
            "reason": STRICT_UNCAPPED_REASON,
            "source_needed": self.repo.capability()["source_needed"],
            "request_kind": what,
        }

    def precheck(self, needs: RequestNeeds, internal: bool) -> None:
        """Public requests fail before any rows are computed when a static gate fails."""
        if not internal:
            apply_gates({}, self.gate_input(), needs, internal=False)

    def _gate(self, payload: dict[str, Any], needs: RequestNeeds, internal: bool) -> dict[str, Any]:
        return apply_gates(payload, self.gate_input(), needs, internal)

    def disabled(self, what: str, needs: RequestNeeds | None = None) -> dict[str, Any]:
        """Structured STRICT_UNCAPPED_DISABLED body: reason, source needed, no rows."""
        cap = self.repo.capability()
        inp = dataclasses.replace(self.gate_input(), strict_enabled=False)
        gates = evaluate_gates(inp, needs or RequestNeeds(uses_strict_classification=True))
        return {
            "result_status": STRICT_DISABLED,
            "reason": STRICT_UNCAPPED_REASON,
            "source_needed": cap["source_needed"],
            "capability": {
                "enabled": cap["enabled"],
                "reasons": cap["reasons"],
                "verified_coverage": cap["verified_coverage"],
                "min_verified_coverage": cap["min_verified_coverage"],
            },
            "request_kind": what,
            "rows": [],
            "status": STATUS,
            "official_ranking": False,
            "disclaimer": DISCLAIMER,
            "publication_status": INTERNAL,
            "gate_results": [g.as_dict() for g in gates],
            "failing_gates": [g.gate_id for g in failing(gates)],
        }

    def strict_blocked(self) -> bool:
        return not self.repo.capability()["enabled"]

    # ------------------------------------------------------------------ players
    def players(
        self,
        params: unc.FilterParams,
        basis: unc.ClassificationBasis,
        q: str | None,
        sort_by: str,
        descending: bool,
        limit: int,
        offset: int,
        public: bool = False,
    ) -> dict[str, Any]:
        """Player directory. ``public=True`` returns the descriptive allow-listed shape only."""
        if unc.is_strict_uncapped_request(params) and self.strict_blocked():
            return self.public_disabled("players") if public else self.disabled("players")
        df = directory_frame(self.t, basis)
        df = unc.apply_filters(df, params)
        if q:
            df = df[df["player_name"].str.contains(q, case=False, regex=False)]
        df = df.sort_values(
            [PLAYER_SORTS[sort_by], "player_id"],
            ascending=[not descending, True],
            na_position="last",
        )
        page, total = paginate(df, limit, offset)
        build = self._public_player_item if public else self._player_item
        items = [build(r) for _, r in page.iterrows()]
        return {
            **(self.public_flags() if public else self.flags()),
            "basis": basis.value,
            "page": {"items": items, "total": total, "limit": limit, "offset": offset},
        }

    @staticmethod
    def _public_player_item(r: pd.Series) -> dict[str, Any]:
        """Explicit allow-list (not a deny-list): descriptive fields only, nothing score-like."""
        return {
            "player_id": int(r["player_id"]),
            "name": str(r["player_name"]),
            "nationality": str(r["eff_nationality"]),
            "nationality_verification": str(r["eff_nationality_verification"]),
            "international_status": str(r["eff_status"]),
            "international_status_verification": str(r["eff_status_verification"]),
            "group": str(r["group"]),
            "group_label": group_label(str(r["group"])),
            "squad_role": _none(r["squad_role"]),
            "matches": int(r["matches"]),
            "distinct_matches": _int(r["distinct_matches"]),
        }

    @staticmethod
    def _player_item(r: pd.Series) -> dict[str, Any]:
        return {
            "player_id": int(r["player_id"]),
            "name": str(r["player_name"]),
            "nationality": str(r["eff_nationality"]),
            "nationality_verification": str(r["eff_nationality_verification"]),
            "international_status": str(r["eff_status"]),
            "international_status_verification": str(r["eff_status_verification"]),
            "group": str(r["group"]),
            "group_label": group_label(str(r["group"])),
            "squad_role": _none(r["squad_role"]),
            "matches": int(r["matches"]),
            "distinct_matches": _int(r["distinct_matches"]),
            "eligible_scopes": str(r["eligible_scopes"]),
            "conflict_flag": bool(r["conflict_flag"]),
        }

    def player_detail(
        self, pid: int, basis: unc.ClassificationBasis, public: bool = False
    ) -> dict[str, Any]:
        df = directory_frame(self.t, basis)
        row = df[df["player_id"] == pid]
        if row.empty:
            raise NotFoundError(f"player {pid} not found")
        r = row.iloc[0]
        return {
            **(self.public_flags() if public else self.flags()),
            "player": (self._public_player_item if public else self._player_item)(r),
            "nationality_source": _none(r["nationality_source"]),
            "nationality_unknown_reason": _none(r["nationality_unknown_reason"]),
            "international_status_source": _none(r["international_status_source"]),
            "international_status_unknown_reason": _none(r["international_status_unknown_reason"]),
            "derived_evidence": _none(r.get("derived_evidence")),
            "first_t20i_date": _none(r["first_t20i_date"]),
            "t20i_appearances_to_as_of": int(r["t20i_appearances_to_as_of"]),
            "as_of_date": _none(r["as_of_date"]),
            "classification_version": _none(r["classification_version"]),
        }

    def profile(
        self, pid: int, basis: unc.ClassificationBasis, fmt: str | None, internal: bool = True
    ) -> dict[str, Any]:
        needs = RequestNeeds()
        self.precheck(needs, internal)
        p = build_profile(self.t, pid, basis, fmt)
        if p is None:
            raise NotFoundError(f"player {pid} not found")
        return self._gate(p, needs, internal)

    def compare(
        self, ids: list[int], basis: unc.ClassificationBasis, fmt: str, internal: bool = True
    ) -> dict[str, Any]:
        needs = RequestNeeds()
        self.precheck(needs, internal)
        missing = [i for i in ids if i not in set(self.t.classification["player_id"])]
        if missing:
            raise NotFoundError(f"players not found: {missing}")
        items = []
        for i in ids:
            p = build_profile(self.t, i, basis, fmt)
            items.append(self._gate(p, needs, internal))
        return self._gate({**self.flags(), "format": fmt, "items": items}, needs, internal)

    # ------------------------------------------------------------------ rankings
    def _ranking_payload(
        self,
        frame: pd.DataFrame,
        total_pool: int,
        role: str,
        fmt: str,
        basis: unc.ClassificationBasis,
        note: str,
        sort_by: str,
        descending: bool,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        col = RANK_SORTS[sort_by]
        frame = frame.sort_values(
            [col, "player_id"], ascending=[not descending, True], na_position="last"
        )
        frame = (
            frame.assign(view_rank=range(1, len(frame) + 1))
            if sort_by == "rank"
            else frame.assign(view_rank=None)
        )
        page, total = paginate(frame, limit, offset)
        return {
            **self.flags(),
            "role": role,
            "format": fmt,
            "basis": basis.value,
            "definition_id": self.t.meta.get("definition_id"),
            "baseline_version": self.t.meta.get("baseline_version"),
            "shrinkage_config": self.t.meta.get("shrinkage_config"),
            "pool_size": total_pool,
            "note": note,
            "page": {
                "items": [result_row(r, _int(r["view_rank"])) for _, r in page.iterrows()],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        }

    def ranking(
        self,
        side: str,
        fmt: str,
        basis: unc.ClassificationBasis,
        params: unc.FilterParams,
        include_ineligible: bool,
        sort_by: str,
        descending: bool,
        limit: int,
        offset: int,
        internal: bool = True,
    ) -> dict[str, Any]:
        strict = unc.is_strict_uncapped_request(params)
        needs = RequestNeeds(uses_strict_classification=strict)
        self.precheck(needs, internal)
        if strict and self.strict_blocked():
            return self.disabled("ranking", needs)
        full = ranking_frame(self.t, side, fmt, basis, include_ineligible=include_ineligible)
        pool = int(full["eligible"].sum())
        frame = unc.apply_filters(full, params)
        note = (
            f"{pool} eligible players in the experimental pool; fewer than ten is reported as is, "
            "never padded. Eligibility thresholds are working values, not validated."
        )
        payload = self._ranking_payload(
            frame, pool, side, fmt, basis, note, sort_by, descending, limit, offset
        )
        needs = RequestNeeds(strict, int(frame["eligible"].sum()))
        return self._gate(payload, needs, internal)

    def uncapped_ranking(
        self,
        kind: unc.UncappedKind,
        fmt: str,
        basis: unc.ClassificationBasis,
        min_matches: int | None,
        min_pressure_matches: int | None,
        include_unverified_list: bool,
        sort_by: str,
        descending: bool,
        limit: int,
        offset: int,
        internal: bool = True,
    ) -> dict[str, Any]:
        needs = RequestNeeds(uses_strict_classification=True)
        self.precheck(needs, internal)
        if self.strict_blocked():
            return self.disabled(f"uncapped_ranking:{kind.value}", needs)
        flt, side = unc.kind_spec(kind)
        main = (
            ranking_frame(self.t, side, fmt, basis)
            if side
            else selection_pool(self.t, fmt, basis, None)
        )
        params = unc.FilterParams(flt, None, min_matches, min_pressure_matches)
        view = unc.apply_filters(main, params)
        verified = int(unc.verified_uncapped_mask(main).sum())
        note = (
            f"Filtered view of the main experimental ranking ({len(main)} eligible players). "
            f"{len(view)} VERIFIED_UNCAPPED players qualify. UNKNOWN_STATUS players are excluded. "
            + (DATA_REQUEST if verified == 0 else "")
        )
        payload = self._ranking_payload(
            view, len(main), side or "overall", fmt, basis, note, sort_by, descending, limit, offset
        )
        payload["kind"] = kind.value
        payload["verified_uncapped_in_pool"] = verified
        payload["unverified_candidates"] = None
        payload["unverified_note"] = None
        if include_unverified_list:
            cand = unc.unverified_candidates(main, kind).sort_values(["rank", "player_id"])
            payload["unverified_candidates"] = [
                result_row(r) for _, r in cand.head(limit).iterrows()
            ]
            payload["unverified_note"] = (
                "Separate list: nationality matches but the status is UNKNOWN_STATUS "
                f"({c2.UNKNOWN_STATUS_BANNER}). These players are NOT verified uncapped."
            )
        return self._gate(payload, RequestNeeds(True, int(len(view))), internal)

    # ------------------------------------------------------------------ selection
    def _pool(self, req: dict[str, Any]) -> pd.DataFrame:
        basis = unc.ClassificationBasis(req["basis"])
        pool = selection_pool(self.t, req["format"], basis, req.get("side"))
        if pool.empty:
            return pool
        mode = req.get("uncapped_mode")
        params = unc.FilterParams(
            None,
            unc.UncappedMode(mode) if mode else None,
            req.get("min_matches"),
            req.get("min_pressure_matches"),
        )
        return unc.apply_filters(pool, params)

    def compose(
        self,
        req: dict[str, Any],
        preset_id: str | None = None,
        internal: bool = True,
        strict: bool | None = None,
    ) -> dict[str, Any]:
        strict = touches_uncapped(req) if strict is None else strict
        needs = RequestNeeds(uses_strict_classification=strict)
        self.precheck(needs, internal)
        if strict and self.strict_blocked():
            out = self.disabled("preset" if preset_id else "selection", needs)
            out["preset_id"] = preset_id
            return out
        pool = self._pool(req)
        cands = [
            sel.Candidate(
                int(r["player_id"]),
                float(r["standardised_score"]),
                str(r["group"]),
                _none(r["squad_role"]),
            )
            for _, r in pool.iterrows()
        ]
        sreq = sel.Request(
            total=int(req["total"]),
            groups={g: sel.Bound(**b) for g, b in req.get("groups", {}).items()},
            roles={r: sel.Bound(**b) for r, b in req.get("roles", {}).items()},
            allow_fewer=bool(req.get("allow_fewer", False)),
        )
        res = sel.select(cands, sreq)
        by_id = {int(r["player_id"]): r for _, r in pool.iterrows()}
        rows = [result_row(by_id[c.player_id], i + 1) for i, c in enumerate(res.selected)]
        status = res.status
        message = None
        if preset_id is not None:
            if status == "INFEASIBLE" or (status == "PARTIAL" and not rows) or not rows:
                status = "POOL_TOO_SMALL"
                message = (
                    "The verified, eligible pool is too small for this preset; no constraint was "
                    f"relaxed and nobody was added. {DATA_REQUEST}"
                )
            elif status == "PARTIAL":
                message = (
                    f"Only {len(rows)} of {sreq.total} players qualify; the list is not padded."
                )
        elif status == "PARTIAL":
            message = f"Only {len(rows)} of {sreq.total} players satisfy every constraint."
        elif status == "INFEASIBLE":
            message = "The constraints cannot be satisfied together over the eligible pool."
        payload = {
            **self.flags(),
            "selection_status": status,
            "preset_id": preset_id,
            "requested_total": res.requested_total,
            "size": len(rows),
            "total_standardised_score": res.total_score if rows else None,
            "message": message,
            "selected": rows,
            "explanations": res.explanations,
            "available_by_group": res.available_by_group,
            "available_by_role": res.available_by_role,
            "excluded_unknown_role": res.excluded_unknown_role,
            "pool_size": int(len(pool)),
            "request": req,
        }
        return self._gate(payload, RequestNeeds(strict, int(len(pool))), internal)

    def presets(self) -> list[dict[str, Any]]:
        return json.loads(self.presets_path.read_text(encoding="utf-8"))["presets"]

    def preset_catalog(self) -> list[dict[str, Any]]:
        """Preset templates with their availability (all six need strict uncapped today)."""
        blocked = self.strict_blocked()
        out = []
        for p in self.presets():
            needs_strict = bool(p["depends_on_verified_classification"])
            disabled = needs_strict and blocked
            out.append(
                {
                    "preset_id": p["preset_id"],
                    "name": p["name"],
                    "description": p["description"],
                    "request": p["request"],
                    "depends_on_verified_classification": needs_strict,
                    "available": not disabled,
                    "unavailable_reason": STRICT_DISABLED if disabled else None,
                }
            )
        return out

    def run_preset(
        self, preset_id: str, fmt: str, basis: str, min_matches: int | None, internal: bool = True
    ) -> dict[str, Any]:
        found = [p for p in self.presets() if p["preset_id"] == preset_id]
        if not found:
            raise NotFoundError(f"preset '{preset_id}' not found")
        req = dict(found[0]["request"])
        req.update({"format": fmt, "basis": basis})
        if min_matches is not None:
            req["min_matches"] = min_matches
        strict = bool(found[0]["depends_on_verified_classification"])
        return self.compose(req, preset_id, internal, strict=strict)

    # ------------------------------------------------------------------ meta
    def coverage(self) -> dict[str, Any]:
        cov = self.t.coverage
        data: dict[str, Any] = {"rows": cov.to_dict(orient="records")}
        data["summary"] = c2.coverage_v2(self.t.classification)
        return {
            **self.flags(),
            "coverage": data,
            "strict_uncapped": self.repo.capability(),
            "unresolved_players": int(len(self.t.unresolved)),
            "note": DATA_REQUEST,
        }

    def capabilities(self) -> dict[str, Any]:
        cap = self.repo.capability()
        return {
            **self.flags(),
            "strict_uncapped_enabled": cap["enabled"],
            "capability": cap,
            "classification_values": list(c2.STATUS_VALUES),
            "disabled_placeholder_values": list(c2.DISABLED_PLACEHOLDER_VALUES),
            "unknown_status_label": c2.UNKNOWN_STATUS_LABEL,
            "unknown_status_banner": c2.UNKNOWN_STATUS_BANNER,
        }

    def publication_gates(self) -> dict[str, Any]:
        gates = evaluate_gates(self.gate_input(), RequestNeeds())
        return {
            **self.flags(),
            "gates": [g.as_dict() for g in gates],
            "failing_gates": [g.gate_id for g in failing(gates)],
            "note": "min_eligible_pool and strict_classification_available are evaluated per request.",
        }
