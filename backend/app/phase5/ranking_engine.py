"""Dynamic filter-driven ranking (ranking layer). INTERNAL / EXPERIMENTAL, never validated.

``ContextEngine`` holds the stored analytics (context rows, per-context scores and eligibility
rules). A request is resolved in this order:

1. strict-uncapped check (``STRICT_UNCAPPED_DISABLED``, no rows);
2. context lookup (competition x role x phase x situation) and the context's own eligibility;
3. classification filters (AND) with excluded counts and the explicit include-unknown toggles;
4. experience filters; pool-size rule (below ``min_internal_pool`` there are no rows);
5. seeded match-cluster bootstrap on the filtered pool (intervals, rank interval, Top-10 inclusion
   probability); canonical order (score descending, ``player_id`` ascending).

Nothing is padded or borrowed from a wider context, and no estimator is fitted here: ``k``,
``tau2`` and the shrinkage targets were fitted once per atomic context on TRAIN rows at build time
(``context_eligibility``) and are held fixed, so a filter cannot create reliability. The same
``resolve_pool`` is used by the coverage table and by the ranking, so they cannot disagree.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase5 import context_stats as cs
from app.phase5.context_eligibility import (
    CONTEXT_ELIGIBLE,
    INSUFFICIENT,
    NOT_ESTIMABLE,
)
from app.phase5.filters import (
    CAPPED_FILTERS,
    STATUS_MEMBERS,
    STRICT_UNCAPPED_DISABLED,
    FilterSpec,
    spec_hash,
    validate_combination,
)

CLS_COLUMNS = (
    "player_name",
    "nationality",
    "nationality_verification",
    "international_status",
    "international_status_verification",
)
SORT_COLUMN = {
    "rank": "rank",
    "score": "score",
    "name": "name",
    "matches": "matches",
    "n": "n",
    "n_eff": "n_eff",
}


def reason(code: str, count: int, detail: str) -> dict[str, Any]:
    return {"code": code, "count": int(count), "detail": detail}


@dataclass
class Pool:
    """Outcome of steps 1 to 4 for one spec."""

    spec_hash: str
    ids: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    comps: list[str] = field(default_factory=list)
    context_status: dict[str, str] = field(default_factory=dict)
    reasons: list[dict[str, Any]] = field(default_factory=list)
    stage_counts: dict[str, int] = field(default_factory=dict)
    excluded_counts: dict[str, int] = field(default_factory=dict)
    match_flag: dict[int, str] = field(default_factory=dict)
    disabled: bool = False
    result_status: str = "EMPTY"

    @property
    def size(self) -> int:
        return int(len(self.ids))


class ContextEngine:
    """Reads stored tables only. Build the tables with ``context_eligibility.build_artifacts``."""

    def __init__(
        self,
        stats: pd.DataFrame,
        rules: pd.DataFrame,
        scores: pd.DataFrame,
        cfg: dict[str, Any],
        manifest: dict[str, Any],
        player_stats: pd.DataFrame,
        data_version: str,
    ) -> None:
        cs.check_stats(stats)
        self.cfg = cfg
        self.manifest = manifest
        self.data_version = data_version
        self.stats = stats
        self.gm, self.W = cs.global_match_weights(stats, int(cfg["n_boot"]), int(cfg["seed"]))
        key = ["comp", "role", "phase", "situation"]
        self._rules = {
            tuple(r[k] for k in key): r for r in rules.to_dict(orient="records")
        }  # fmt: skip
        self._scores: dict[tuple[str, str, str, str], pd.DataFrame] = {}
        if len(scores):
            for k, g in scores.groupby(key, sort=False):
                self._scores[tuple(k)] = g.sort_values("player_id").set_index("player_id")
        self._cells: dict[tuple[str, str, str, str], Any] = {}
        self._draws: dict[tuple[str, str, str, str], tuple[np.ndarray, np.ndarray]] = {}
        self._lock = threading.Lock()
        self.career = self._career(player_stats)
        self.model_version = str(cfg["model_version"])
        self.w_ipl = float(cfg["combined_ipl_weight"])
        self.fit_calls = 0  # never incremented on the request path (asserted in tests)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _career(ps: pd.DataFrame) -> pd.DataFrame:
        if ps is None or ps.empty:
            return pd.DataFrame(columns=["IPL", "T20I"])
        t = ps[ps["window"] == "PRE_TEST"] if "window" in ps.columns else ps
        w = t.pivot_table(
            index="player_id", columns="format", values="matches_played", aggfunc="sum"
        )
        return w.reindex(columns=["IPL", "T20I"]).fillna(0)

    @staticmethod
    def _cls_index(cls: pd.DataFrame) -> pd.DataFrame:
        have = [c for c in CLS_COLUMNS if c in cls.columns]
        return cls.set_index("player_id")[have]

    def rule(self, comp: str, role: str, phase: str, situation: str) -> dict[str, Any] | None:
        return self._rules.get((comp, role, phase, situation))

    def context_scores(self, key: tuple[str, str, str, str]) -> pd.DataFrame | None:
        return self._scores.get(key)

    def _context_draws(self, key: tuple[str, str, str, str]) -> tuple[np.ndarray, np.ndarray]:
        """Bootstrap ball counts and shrunk draws of the whole context (fixed ``k``/target)."""
        with self._lock:
            if key in self._draws:
                return self._draws[key]
            comp, role, phase, situation = key
            stream = en.PRIMARY[role][0]
            cell = cs.cell_from_stats(
                cs.select(self.stats, comp, role, phase, situation), comp, role, stream
            )
            sc = self._scores[key]
            est = pd.DataFrame(
                {
                    "n_eff": sc["n_eff"].reindex(cell.players).to_numpy(),
                    "k": sc["k"].reindex(cell.players).to_numpy(),
                    "target": sc["target"].reindex(cell.players).to_numpy(),
                }
            )
            nb, dr = en.draws(cell, est, en.cell_weights(cell, self.gm, self.W))
            self._cells[key] = cell
            self._draws[key] = (nb, dr)
            return nb, dr

    # ------------------------------------------------------------------ pool resolution
    def resolve_pool(self, spec: FilterSpec, cls: pd.DataFrame, strict_enabled: bool) -> Pool:
        pool = Pool(spec_hash=spec_hash(spec))
        blocked = validate_combination(spec, strict_enabled)
        if blocked:
            pool.reasons, pool.disabled = blocked, True
            pool.result_status = STRICT_UNCAPPED_DISABLED
            return pool
        comps = ["IPL", "T20I"] if spec.format == "COMBINED_w70_30" else [spec.format]
        pool.comps = comps
        scores: dict[str, pd.DataFrame] = {}
        bad = False
        for comp in comps:
            rule = self.rule(comp, spec.role, spec.phase, spec.situation)
            status = str(rule["context_status"]) if rule else NOT_ESTIMABLE
            pool.context_status[comp] = status
            if status != CONTEXT_ELIGIBLE:
                bad = True
                pool.reasons.append(reason(status, 0, f"{comp}: context has no usable rule"))
            else:
                scores[comp] = self._scores[(comp, spec.role, spec.phase, spec.situation)]
        if bad:
            if len(comps) == 2:
                pool.reasons.append(
                    reason(
                        "FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS",
                        0,
                        "the combined format needs an estimable context in both formats",
                    )
                )
            pool.stage_counts = {"players_in_context": 0, "eligible_in_context": 0, "final_pool": 0}
            pool.excluded_counts = _zero_excluded()
            return pool
        in_ctx, eligible = self._context_eligible(scores, comps, pool)
        ids = pd.Index(sorted(eligible))
        pool.stage_counts = {"players_in_context": len(in_ctx), "eligible_in_context": len(ids)}
        pool.excluded_counts = _zero_excluded()
        ci = self._cls_index(cls)
        ids = self._apply_classification(spec, ids, ci, pool)
        ids = self._apply_experience(spec, ids, scores, comps, pool)
        pool.ids = np.asarray(ids, dtype=np.int64)
        pool.stage_counts["final_pool"] = pool.size
        n_min = int(self.cfg["min_internal_pool"])
        if pool.size < n_min:
            pool.reasons.append(
                reason("POOL_TOO_SMALL", pool.size, f"{pool.size} players, minimum {n_min}")
            )
            pool.result_status = "EMPTY"
        elif pool.size < int(self.cfg["list_size"]):
            pool.reasons.append(
                reason("FEWER_THAN_LIST_SIZE", pool.size, "fewer than 10 players; never padded")
            )
            pool.result_status = "FEWER_THAN_LIST_SIZE"
        else:
            pool.result_status = "RANKED"
        return pool

    def _context_eligible(
        self, scores: dict[str, pd.DataFrame], comps: list[str], pool: Pool
    ) -> tuple[set[int], set[int]]:
        per = {c: set(scores[c].index) for c in comps}
        elig = {c: set(scores[c].index[scores[c]["eligible"].to_numpy()]) for c in comps}
        in_ctx = set().union(*per.values())
        both = set.intersection(*elig.values())
        lost = in_ctx - both
        if len(comps) == 1:
            if lost:
                pool.reasons.append(
                    reason(
                        INSUFFICIENT,
                        len(lost),
                        "players with context data below the context's own threshold",
                    )
                )
        else:
            one = {p for p in lost if any(p in elig[c] for c in comps)}
            if one:
                pool.reasons.append(
                    reason(
                        "FORMAT_COMBINATION_REQUIRES_BOTH_FORMATS",
                        len(one),
                        "eligible in one format only, not combined",
                    )
                )
            low = lost - one
            if low:
                pool.reasons.append(
                    reason(
                        INSUFFICIENT,
                        len(low),
                        "players with context data below the context's own threshold",
                    )
                )
        return in_ctx, both

    def _apply_classification(
        self, spec: FilterSpec, ids: pd.Index, ci: pd.DataFrame, pool: Pool
    ) -> pd.Index:
        flag = dict.fromkeys((int(i) for i in ids), "NOT_FILTERED")
        if spec.nationality or spec.status:
            flag = dict.fromkeys(flag, "EXACT")
        if spec.nationality:
            nat = ci["nationality"].reindex(ids).fillna("Unknown")
            unk = nat == "Unknown"
            hit = nat == spec.nationality
            if spec.nationality == "Unknown":
                keep = hit
            elif spec.include_unknown_nationality:
                keep = hit | unk
                for p in ids[(unk & ~hit).to_numpy()]:
                    flag[int(p)] = "UNKNOWN_INCLUDED"
            else:
                keep = hit
                n_unk = int((unk & ~hit).sum())
                pool.excluded_counts["unknown_nationality_excluded"] = n_unk
                if n_unk:
                    pool.reasons.append(
                        reason(
                            "CLASSIFICATION_UNKNOWN_EXCLUDED",
                            n_unk,
                            "nationality unknown; excluded because a nationality filter is set",
                        )
                    )
            pool.excluded_counts["nationality_mismatch"] = int((~(keep | unk)).sum())
            ids = ids[keep.to_numpy()]
        pool.stage_counts["after_nationality"] = len(ids)
        if spec.status:
            members = STATUS_MEMBERS[spec.status]
            st = ci["international_status"].reindex(ids).fillna("UNKNOWN")
            unk = st == "UNKNOWN"
            hit = st.isin(members)
            all_st = ci["international_status"]
            if not all_st.isin(members).any():
                pool.reasons.append(
                    reason(
                        "CLASS_EMPTY",
                        0,
                        f"no player in the classification has status {'/'.join(members)}",
                    )
                )
            if spec.status not in CAPPED_FILTERS:
                keep = hit
            elif spec.include_unknown_status:
                keep = hit | unk
                for p in ids[(unk & ~hit).to_numpy()]:
                    flag[int(p)] = "UNKNOWN_INCLUDED"
            else:
                keep = hit
                n_unk = int((unk & ~hit).sum())
                pool.excluded_counts["unknown_status_excluded"] = n_unk
                if n_unk:
                    pool.reasons.append(
                        reason(
                            "CLASSIFICATION_UNKNOWN_EXCLUDED",
                            n_unk,
                            "international status unknown (UNKNOWN_STATUS); excluded because a "
                            "status filter is set",
                        )
                    )
            pool.excluded_counts["status_mismatch"] = int((~(keep | unk)).sum())
            ids = ids[keep.to_numpy()]
        pool.stage_counts["after_status"] = len(ids)
        pool.match_flag = {int(p): flag[int(p)] for p in ids}
        return ids

    def _apply_experience(
        self,
        spec: FilterSpec,
        ids: pd.Index,
        scores: dict[str, pd.DataFrame],
        comps: list[str],
        pool: Pool,
    ) -> pd.Index:
        if spec.min_matches > 0:
            career = self.career.reindex(ids).fillna(0)[comps].sum(axis=1)
            keep = career >= spec.min_matches
            pool.excluded_counts["below_min_matches"] = int((~keep).sum())
            if (~keep).any():
                pool.reasons.append(
                    reason("BELOW_MIN_MATCHES", int((~keep).sum()), "career matches below filter")
                )
            ids = ids[keep.to_numpy()]
        pool.stage_counts["after_min_matches"] = len(ids)
        if spec.min_context_matches > 0:
            cm = sum(scores[c]["matches"].reindex(ids).fillna(0) for c in comps)
            keep = cm >= spec.min_context_matches
            pool.excluded_counts["below_min_context_matches"] = int((~keep).sum())
            if (~keep).any():
                pool.reasons.append(
                    reason(
                        "BELOW_MIN_CONTEXT_MATCHES",
                        int((~keep).sum()),
                        "pressure matches in the context below filter",
                    )
                )
            ids = ids[keep.to_numpy()]
        pool.stage_counts["after_min_context_matches"] = len(ids)
        return ids

    # ------------------------------------------------------------------ ranking
    def rank(self, spec: FilterSpec, cls: pd.DataFrame, strict_enabled: bool) -> dict[str, Any]:
        """Full ranked pool (unsliced). Rows only when the pool meets the internal minimum."""
        pool = self.resolve_pool(spec, cls, strict_enabled)
        out: dict[str, Any] = {
            "result_status": pool.result_status,
            "spec_hash": pool.spec_hash,
            "pool_size": pool.size,
            "reasons": pool.reasons,
            "stage_counts": pool.stage_counts,
            "excluded_counts": pool.excluded_counts,
            "context_status": pool.context_status,
            "context_data_weight": self.context_weight(spec, pool),
            "rows": [],
            "low_data_weight": False,
            "versions": self.versions(),
        }
        if pool.disabled or pool.size < int(self.cfg["min_internal_pool"]):
            return out
        rows, low = self._rows(spec, pool, cls)
        out["rows"] = rows
        out["low_data_weight"] = low
        extra = []
        failed = [c for c, v in out["context_data_weight"].items() if not v["passed"]]
        if failed:
            extra.append(
                reason(
                    "CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED",
                    len(rows),
                    f"marginal shrinkage weight below {el.GATE_B} in {failed}: the working pool is "
                    "not a validated threshold",
                )
            )
        if low:
            extra.append(
                reason(
                    "LOW_DATA_WEIGHT_CONTEXT",
                    len(rows),
                    "median shrinkage weight of the pool is below "
                    f"{self.cfg['low_data_weight_warning']}; scores are mostly the shrinkage target",
                )
            )
        out["reasons"] = [*pool.reasons, *extra]
        return out

    def context_weight(self, spec: FilterSpec, pool: Pool) -> dict[str, dict[str, Any]]:
        """Phase 4 data-weight gate (marginal shrinkage weight >= 0.5) per context of the spec."""
        out = {}
        for comp in pool.comps:
            rule = self.rule(comp, spec.role, spec.phase, spec.situation) or {}
            mdw = rule.get("marginal_data_weight")
            out[comp] = {
                "marginal_data_weight": _fl(mdw) if mdw is not None else None,
                "gate": el.GATE_B,
                "passed": rule.get("data_weight_gate_passed") in (True, np.True_),
            }
        return out

    def versions(self) -> dict[str, Any]:
        m = self.manifest
        return {
            "definition_id": m.get("definition_id", self.cfg["definition_id"]),
            "definition_label": self.cfg["definition_label"],
            "baseline_version": m.get("baseline_version"),
            "shrinkage_config": m.get("shrinkage_config"),
            "model_version": self.model_version,
            "data_version": self.data_version,
            "config_hashes": m.get("config_hashes", {}),
            "interval_level": self.cfg["interval_level"],
            "n_boot": int(self.cfg["n_boot"]),
            "seed": int(self.cfg["seed"]),
        }

    def _rows(self, spec: FilterSpec, pool: Pool, cls: pd.DataFrame) -> tuple[list[dict], bool]:
        ids, comps = pool.ids, pool.comps
        sign = en.PRIMARY[spec.role][1]
        parts, draws, present = {}, {}, {}
        for comp in comps:
            key = (comp, spec.role, spec.phase, spec.situation)
            sc = self._scores[key]
            sub = sc.loc[ids]
            nb, dr = self._context_draws(key)
            pos = pd.Index(self._cells[key].players).get_indexer(ids)
            parts[comp] = sub
            draws[comp] = sign * dr[pos]
            present[comp] = (nb[pos] >= sub["scaled_threshold"].to_numpy()[:, None]) & np.isfinite(
                dr[pos]
            )
        if len(comps) == 1:
            c = comps[0]
            sub, D, pres = parts[c], draws[c], present[c]
            score = sub["score"].to_numpy()
            raw, exp_, res = (
                sub[k].to_numpy() for k in ("mean_raw", "mean_expected", "mean_residual")
            )
            n = sub["n"].to_numpy()
            matches = sub["matches"].to_numpy()
            n_eff = sub["n_eff"].to_numpy()
            weight = sub["shrink_weight"].to_numpy()
        else:
            w = self.w_ipl
            a, b = parts["IPL"], parts["T20I"]
            D = w * draws["IPL"] + (1 - w) * draws["T20I"]
            pres = present["IPL"] & present["T20I"]
            score = w * a["score"].to_numpy() + (1 - w) * b["score"].to_numpy()
            raw = w * a["mean_raw"].to_numpy() + (1 - w) * b["mean_raw"].to_numpy()
            exp_ = w * a["mean_expected"].to_numpy() + (1 - w) * b["mean_expected"].to_numpy()
            res = w * a["mean_residual"].to_numpy() + (1 - w) * b["mean_residual"].to_numpy()
            n = a["n"].to_numpy() + b["n"].to_numpy()
            matches = a["matches"].to_numpy() + b["matches"].to_numpy()
            n_eff = 1.0 / (w**2 / a["n_eff"].to_numpy() + (1 - w) ** 2 / b["n_eff"].to_numpy())
            weight = w * a["shrink_weight"].to_numpy() + (1 - w) * b["shrink_weight"].to_numpy()
        m = len(ids)
        score_draws = np.where(pres & np.isfinite(D), D, np.nan)
        rs = en.rank_summary(score_draws, score, np.ones(m, dtype=bool))
        with np.errstate(all="ignore"):
            lo_q = (1 - float(self.cfg["interval_level"])) / 2 * 100
            lo = np.nanpercentile(np.where(np.isfinite(D), D, np.nan), lo_q, axis=1)
            hi = np.nanpercentile(np.where(np.isfinite(D), D, np.nan), 100 - lo_q, axis=1)
        order = np.lexsort((ids, -score))
        rank = np.empty(m, dtype=int)
        rank[order] = np.arange(1, m + 1)
        ci = self._cls_index(cls).reindex(ids)
        restr = self.manifest.get("restrictions_applied")
        rows = []
        for i in order:
            pid = int(ids[i])
            comp_detail = {
                c: {
                    "n": int(parts[c]["n"].iloc[i]),
                    "matches": int(parts[c]["matches"].iloc[i]),
                    "n_eff": float(parts[c]["n_eff"].iloc[i]),
                    "k": float(parts[c]["k"].iloc[i]),
                    "shrinkage_weight": float(parts[c]["shrink_weight"].iloc[i]),
                    "threshold_balls": _int(parts[c]["threshold_balls"].iloc[i]),
                    "fit_floor_hit": bool(parts[c]["floor_hit"].iloc[i]),
                }
                for c in comps
            }
            rows.append(
                {
                    "rank": int(rank[i]),
                    "player_id": pid,
                    "name": _s(ci["player_name"].iloc[i]) if "player_name" in ci else None,
                    "score": float(score[i]),
                    "raw": float(raw[i]),
                    "expected": float(exp_[i]),
                    "residual": float(res[i]),
                    "shrunk": float(sign * score[i]),
                    "interval_low": _fl(lo[i]),
                    "interval_high": _fl(hi[i]),
                    "rank_lo": _fl(rs["rank_lo"][i]),
                    "rank_median": _fl(rs["rank_med"][i]),
                    "rank_hi": _fl(rs["rank_hi"][i]),
                    "top10_inclusion_prob": _fl(rs["inclusion_prob"][i]),
                    "n": int(n[i]),
                    "matches": int(matches[i]),
                    "n_eff": float(n_eff[i]),
                    "shrinkage_weight": float(weight[i]),
                    "fit_floor_hit": any(v["fit_floor_hit"] for v in comp_detail.values()),
                    "eligibility_status": CONTEXT_ELIGIBLE,
                    "eligibility_label": str(parts[comps[0]]["label"].iloc[i]),
                    "eligibility_thresholds": {c: v["threshold_balls"] for c, v in comp_detail.items()},
                    "components": comp_detail,
                    "restrictions_applied": restr,
                    "nationality": _s(ci["nationality"].iloc[i]) or "Unknown",
                    "nationality_verification": _s(ci["nationality_verification"].iloc[i]),
                    "international_status": _s(ci["international_status"].iloc[i]) or "UNKNOWN",
                    "international_status_verification": _s(
                        ci["international_status_verification"].iloc[i]
                    ),
                    "classification_match": pool.match_flag.get(pid, "NOT_FILTERED"),
                    "career_matches": _career(self.career, pid, comps),
                }
            )  # fmt: skip
        low = bool(np.median(weight) < float(self.cfg["low_data_weight_warning"]))
        return rows, low


def paginate_ranked(full: dict[str, Any], spec: FilterSpec) -> dict[str, Any]:
    """Slice an unsliced ranking for one page. Rank values come from the canonical order."""
    rows = list(full["rows"])
    col = SORT_COLUMN[spec.sort]
    desc = spec.effective_order() == "desc"
    rows.sort(key=lambda r: (_sort_key(r[col] if r[col] is not None else "", desc), r["player_id"]))
    page = rows[spec.offset : spec.offset + spec.limit]
    return {**full, "rows": page, "total": len(rows), "limit": spec.limit, "offset": spec.offset}


def _sort_key(v: Any, desc: bool) -> Any:
    if isinstance(v, str):
        return tuple(-ord(ch) for ch in v) if desc else v
    return -v if desc else v


def _zero_excluded() -> dict[str, int]:
    return {
        "unknown_nationality_excluded": 0,
        "nationality_mismatch": 0,
        "unknown_status_excluded": 0,
        "status_mismatch": 0,
        "below_min_matches": 0,
        "below_min_context_matches": 0,
    }


def _int(v: Any) -> int | None:
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else int(v)


def _fl(v: Any) -> float | None:
    return None if v is None or not np.isfinite(v) else float(v)


def _s(v: Any) -> str | None:
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)


def _career(career: pd.DataFrame, pid: int, comps: list[str]) -> int:
    if pid not in career.index:
        return 0
    return int(sum(career.loc[pid, c] for c in comps))


__all__ = [
    "ContextEngine",
    "Pool",
    "paginate_ranked",
    "reason",
]
