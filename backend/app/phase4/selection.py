"""Deterministic, exact composition optimiser for custom Top-N selections.

Every player belongs to exactly one of five groups (Indian/Overseas x Capped/Uncapped, plus
UNKNOWN when nationality or status is unknown). Independent exact/min/max constraints on groups,
optional role constraints and the total size are evaluated TOGETHER by a dynamic programme over
count vectors, so nothing is double counted and the result is optimal.

Optimality: all constraints depend only on the counts per (group, role bucket) cell. For fixed
counts, taking the highest-scoring players of each cell maximises the total (exchange argument).
The DP enumerates every feasible count vector, so the best total is global. Ties are broken by the
lexicographically smallest sorted ``player_id`` tuple among all optimal selections. Scores are
rounded to 1e-9 and compared as integers, so there are no floating point ties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any

GROUPS = ("IN_CAPPED", "IN_UNCAPPED", "OS_CAPPED", "OS_UNCAPPED", "UNKNOWN")
SCALE = 10**9
MAX_TOTAL = 50
MAX_TOTAL_WITH_ROLES = 12
MAX_OPTIMAL_PATHS = 5000
OTHER = "OTHER"


class SelectionRequestError(ValueError):
    """Raised for an invalid or too large composition request."""


def assign_group(nationality: str, status: str) -> str:
    """Single group per player; an unknown nationality or UNKNOWN status gives group UNKNOWN.

    ``status`` uses the Phase 5 enum. Legacy Phase 4 labels are rejected instead of being
    relabelled silently; migrate them with ``app.phase5.classification_v2``.
    """
    if status in ("Capped", "Uncapped"):
        raise ValueError(f"legacy status '{status}': migrate with classification_v2 first")
    if nationality not in ("Indian", "Overseas"):
        return "UNKNOWN"
    if status in ("VERIFIED_CAPPED", "DERIVED_CAPPED"):
        suffix = "CAPPED"
    elif status == "VERIFIED_UNCAPPED":
        suffix = "UNCAPPED"
    else:
        return "UNKNOWN"
    return ("IN_" if nationality == "Indian" else "OS_") + suffix


@dataclass(frozen=True)
class Candidate:
    player_id: int
    score: float
    group: str
    role: str | None = None


@dataclass(frozen=True)
class Bound:
    """Independent exact/min/max for one group or role. ``exact`` sets min = max."""

    exact: int | None = None
    min: int | None = None
    max: int | None = None

    def resolve(self, total: int) -> tuple[int, int]:
        if self.exact is not None:
            if self.min is not None or self.max is not None:
                raise SelectionRequestError("exact cannot be combined with min or max")
            lo = hi = int(self.exact)
        else:
            lo = 0 if self.min is None else int(self.min)
            hi = max(total, lo) if self.max is None else int(self.max)
        if lo < 0 or hi < 0:
            raise SelectionRequestError("bounds must be non-negative")
        if lo > hi:
            raise SelectionRequestError(f"min {lo} is greater than max {hi}")
        return lo, hi


@dataclass
class Request:
    total: int = 10
    groups: dict[str, Bound] = field(default_factory=dict)
    roles: dict[str, Bound] = field(default_factory=dict)
    allow_fewer: bool = False


@dataclass
class Result:
    status: str  # OK | PARTIAL | INFEASIBLE
    requested_total: int
    selected: list[Candidate]
    total_score: float | None
    explanations: list[dict[str, Any]]
    available_by_group: dict[str, int]
    available_by_role: dict[str, int]
    excluded_unknown_role: int = 0
    tie_paths_examined: int = 0


def _resolved_groups(req: Request) -> dict[str, tuple[int, int]]:
    for g in req.groups:
        if g not in GROUPS:
            raise SelectionRequestError(f"unknown group '{g}', expected one of {list(GROUPS)}")
    out: dict[str, tuple[int, int]] = {}
    for g in GROUPS:
        if g in req.groups:
            out[g] = req.groups[g].resolve(req.total)
        elif g == "UNKNOWN":
            out[g] = (0, 0)  # Unknown players are never chosen unless the request names the group
        else:
            out[g] = (0, req.total)
    return out


def _vectors(avail: list[int], lo: int, hi: int, cap: int) -> list[tuple[int, ...]]:
    ranges = [range(0, min(a, cap) + 1) for a in avail]
    return [v for v in product(*ranges) if lo <= sum(v) <= hi]


def _solve(
    cells: dict[tuple[str, str | None], list[tuple[int, int, Candidate]]],
    buckets: list[str | None],
    gb: dict[str, tuple[int, int]],
    rb: dict[str, tuple[int, int]],
    n: int,
):
    """Return (best_value, list of optimal paths) or (None, []). Paths: per group count vectors."""
    nb = len(buckets)
    prefix: dict[tuple[str, str | None], list[int]] = {}
    for key, lst in cells.items():
        acc = [0]
        for sc, _pid, _c in lst:
            acc.append(acc[-1] + sc)
        prefix[key] = acc
    vec: dict[str, list[tuple[tuple[int, ...], int]]] = {}
    for g in GROUPS:
        lo, hi = gb[g]
        avail = [len(cells.get((g, b), [])) for b in buckets]
        vs = _vectors(avail, lo, min(hi, n), n)
        vec[g] = [
            (v, sum(prefix[(g, b)][c] for b, c in zip(buckets, v, strict=True) if c)) for v in vs
        ]
    role_hi = [rb.get(b, (0, n))[1] if b is not None else n for b in buckets]
    role_lo = [rb.get(b, (0, n))[0] if b is not None else 0 for b in buckets]
    layers: list[dict[tuple[int, ...], int]] = [{tuple([0] * nb): 0}]
    for g in GROUPS:
        nxt: dict[tuple[int, ...], int] = {}
        for s, val in layers[-1].items():
            ts = sum(s)
            for v, gv in vec[g]:
                if ts + sum(v) > n:
                    continue
                t = tuple(a + b for a, b in zip(s, v, strict=True))
                if any(x > h for x, h in zip(t, role_hi, strict=True)):
                    continue
                cand = val + gv
                if t not in nxt or cand > nxt[t]:
                    nxt[t] = cand
        layers.append(nxt)
    finals = {
        t: v
        for t, v in layers[-1].items()
        if sum(t) == n and all(x >= lo for x, lo in zip(t, role_lo, strict=True))
    }
    if not finals:
        return None, [], vec, prefix
    best = max(finals.values())
    paths: list[list[tuple[int, ...]]] = []

    def back(k: int, t: tuple[int, ...], acc: list[tuple[int, ...]]) -> None:
        if len(paths) >= MAX_OPTIMAL_PATHS:
            return
        if k == 0:
            paths.append(list(reversed(acc)))
            return
        g = GROUPS[k - 1]
        for v, gv in vec[g]:
            if any(c > x for c, x in zip(v, t, strict=True)):
                continue
            s = tuple(x - c for x, c in zip(t, v, strict=True))
            if layers[k - 1].get(s) is not None and layers[k - 1][s] + gv == layers[k][t]:
                back(k - 1, s, [*acc, v])

    for t, v in sorted(finals.items()):
        if v == best:
            back(len(GROUPS), t, [])
    return best, paths, vec, prefix


def _pick(
    cells: dict[tuple[str, str | None], list[tuple[int, int, Candidate]]],
    buckets: list[str | None],
    path: list[tuple[int, ...]],
) -> list[Candidate]:
    chosen: list[Candidate] = []
    for g, v in zip(GROUPS, path, strict=True):
        for b, c in zip(buckets, v, strict=True):
            chosen.extend(x[2] for x in cells.get((g, b), [])[:c])
    return chosen


def _explain(
    gb: dict[str, tuple[int, int]],
    rb: dict[str, tuple[int, int]],
    avail_g: dict[str, int],
    avail_r: dict[str, int],
    n: int,
    role_mode: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in GROUPS:
        lo, hi = gb[g]
        if lo > avail_g[g]:
            out.append(
                {
                    "constraint": f"group {g} min",
                    "required": lo,
                    "available": avail_g[g],
                    "message": f"{g} requires at least {lo} but only {avail_g[g]} eligible "
                    "players are available",
                }
            )
    if sum(lo for lo, _ in gb.values()) > n:
        out.append(
            {
                "constraint": "group minimums vs total",
                "required": sum(lo for lo, _ in gb.values()),
                "available": n,
                "message": "the group minimums add up to more than the requested total",
            }
        )
    cap = sum(min(avail_g[g], gb[g][1]) for g in GROUPS)
    if cap < n:
        out.append(
            {
                "constraint": "total size",
                "required": n,
                "available": cap,
                "message": f"only {cap} players can be chosen under the group maximums and the "
                f"eligible pool, but {n} were requested",
            }
        )
    if role_mode:
        for r, (lo, _hi) in rb.items():
            if lo > avail_r.get(r, 0):
                out.append(
                    {
                        "constraint": f"role {r} min",
                        "required": lo,
                        "available": avail_r.get(r, 0),
                        "message": f"role {r} requires at least {lo} but only "
                        f"{avail_r.get(r, 0)} eligible players are available",
                    }
                )
    return out


def select(candidates: list[Candidate], req: Request) -> Result:
    """Optimal selection, a partial one when ``allow_fewer`` is set, or an infeasibility report."""
    n = int(req.total)
    if n < 1 or n > MAX_TOTAL:
        raise SelectionRequestError(f"total must be between 1 and {MAX_TOTAL}")
    role_mode = bool(req.roles)
    if role_mode and n > MAX_TOTAL_WITH_ROLES:
        raise SelectionRequestError(
            f"role constraints are supported for total up to {MAX_TOTAL_WITH_ROLES}; got {n}"
        )
    gb = _resolved_groups(req)
    rb = {r: b.resolve(n) for r, b in req.roles.items()}
    ids = [c.player_id for c in candidates]
    if len(ids) != len(set(ids)):
        raise SelectionRequestError("candidate pool contains a repeated player_id")
    buckets: list[str | None]
    unknown_role = 0
    pool: list[tuple[Candidate, str | None]] = []
    if role_mode:
        buckets = [*sorted(rb), OTHER]
        for c in candidates:
            if c.role is None:
                unknown_role += 1
                continue
            pool.append((c, c.role if c.role in rb else OTHER))
    else:
        buckets = [None]
        pool = [(c, None) for c in candidates]
    cells: dict[tuple[str, str | None], list[tuple[int, int, Candidate]]] = {}
    for c, b in pool:
        cells.setdefault((c.group, b), []).append((int(round(c.score * SCALE)), c.player_id, c))
    for lst in cells.values():
        lst.sort(key=lambda x: (-x[0], x[1]))
    avail_g = {g: sum(len(cells.get((g, b), [])) for b in buckets) for g in GROUPS}
    avail_r: dict[str, int] = {}
    if role_mode:
        for b in buckets:
            avail_r[str(b)] = sum(len(cells.get((g, b), [])) for g in GROUPS)
    sizes = [n] + (list(range(n - 1, -1, -1)) if req.allow_fewer else [])
    for m in sizes:
        gbm = {g: (lo, min(hi, m)) if lo <= m else (lo, hi) for g, (lo, hi) in gb.items()}
        best, paths, _vec, _pre = _solve(cells, buckets, gbm, rb, m)
        if best is None:
            continue
        options = [_pick(cells, buckets, p) for p in paths]
        chosen = min(options, key=lambda sel: sorted(c.player_id for c in sel))
        chosen.sort(key=lambda c: (-int(round(c.score * SCALE)), c.player_id))
        return Result(
            status="OK" if m == n else "PARTIAL",
            requested_total=n,
            selected=chosen,
            total_score=best / SCALE,
            explanations=[]
            if m == n
            else [
                {
                    "constraint": "total size",
                    "required": n,
                    "available": m,
                    "message": f"only {m} of the requested {n} players can satisfy every "
                    "constraint; the list is not padded",
                }
            ],
            available_by_group=avail_g,
            available_by_role=avail_r,
            excluded_unknown_role=unknown_role,
            tie_paths_examined=len(paths),
        )
    why = _explain(gb, rb, avail_g, avail_r, n, role_mode) or [
        {
            "constraint": "combined constraints",
            "required": n,
            "available": sum(avail_g.values()),
            "message": "no selection satisfies the group, role and total constraints together",
        }
    ]
    return Result(
        status="INFEASIBLE",
        requested_total=n,
        selected=[],
        total_score=None,
        explanations=why,
        available_by_group=avail_g,
        available_by_role=avail_r,
        excluded_unknown_role=unknown_role,
    )
