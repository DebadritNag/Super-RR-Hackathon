"""Composition optimiser: exactness against brute force, constraints, infeasibility, determinism."""

from __future__ import annotations

import random
from itertools import combinations

import pytest

from app.phase4.selection import (
    GROUPS,
    SCALE,
    Bound,
    Candidate,
    Request,
    SelectionRequestError,
    assign_group,
    select,
)


def brute(cands, req: Request):
    """Reference solver: enumerate every subset of size ``total``."""
    n = req.total
    gb = {}
    for g in GROUPS:
        if g in req.groups:
            gb[g] = req.groups[g].resolve(n)
        else:
            gb[g] = (0, 0) if g == "UNKNOWN" else (0, n)
    rb = {r: b.resolve(n) for r, b in req.roles.items()}
    best = None
    for combo in combinations(cands, n):
        if rb and any(c.role is None for c in combo):
            continue
        if any(not gb[g][0] <= sum(c.group == g for c in combo) <= gb[g][1] for g in GROUPS):
            continue
        if any(not lo <= sum(c.role == r for c in combo) <= hi for r, (lo, hi) in rb.items()):
            continue
        val = sum(int(round(c.score * SCALE)) for c in combo)
        key = (-val, tuple(sorted(c.player_id for c in combo)))
        if best is None or key < best[0]:
            best = (key, combo)
    return best


def pool_4321():
    """Synthetic pool where the unconstrained top 10 ignores the composition."""
    cands, pid = [], 1
    spec = {"IN_CAPPED": 6, "IN_UNCAPPED": 5, "OS_CAPPED": 4, "OS_UNCAPPED": 3}
    for g, k in spec.items():
        for j in range(k):
            cands.append(Candidate(pid, round(3.0 - 0.1 * pid - 0.001 * j, 3), g, None))
            pid += 1
    return cands


def test_four_three_two_one_example_is_exact_and_optimal():
    cands = pool_4321()
    req = Request(
        total=10,
        groups={
            "IN_CAPPED": Bound(exact=4),
            "IN_UNCAPPED": Bound(exact=3),
            "OS_CAPPED": Bound(exact=2),
            "OS_UNCAPPED": Bound(exact=1),
        },
    )
    res = select(cands, req)
    assert res.status == "OK" and len(res.selected) == 10
    counts = {g: sum(c.group == g for c in res.selected) for g in GROUPS}
    assert counts == {
        "IN_CAPPED": 4,
        "IN_UNCAPPED": 3,
        "OS_CAPPED": 2,
        "OS_UNCAPPED": 1,
        "UNKNOWN": 0,
    }
    assert len({c.player_id for c in res.selected}) == 10  # nobody counted twice
    # top-k of each group by score (ids ascend with falling score inside the generated pool)
    assert sorted(c.player_id for c in res.selected) == [1, 2, 3, 4, 7, 8, 9, 12, 13, 16]
    expected = brute(cands, req)
    assert abs(res.total_score - (-expected[0][0]) / SCALE) < 1e-9


def test_infeasible_reports_failing_constraint_and_counts():
    cands = [c for c in pool_4321() if c.group != "OS_UNCAPPED"]
    req = Request(
        total=10,
        groups={
            "IN_CAPPED": Bound(exact=4),
            "IN_UNCAPPED": Bound(exact=3),
            "OS_UNCAPPED": Bound(exact=1),
        },
    )
    res = select(cands, req)
    assert res.status == "INFEASIBLE" and res.selected == []
    ex = [e for e in res.explanations if e["constraint"] == "group OS_UNCAPPED min"][0]
    assert ex["required"] == 1 and ex["available"] == 0
    assert res.available_by_group["OS_UNCAPPED"] == 0


def test_never_pads_when_pool_is_short():
    cands = pool_4321()[:6]
    res = select(cands, Request(total=10))
    assert res.status == "INFEASIBLE" and res.selected == []
    part = select(cands, Request(total=10, allow_fewer=True))
    assert part.status == "PARTIAL" and len(part.selected) == 6
    assert part.explanations[0]["available"] == 6


def test_unknown_group_excluded_unless_requested():
    cands = [Candidate(i, 1.0 - 0.01 * i, "UNKNOWN") for i in range(1, 6)] + [
        Candidate(10 + i, 0.5 - 0.01 * i, "IN_CAPPED") for i in range(1, 6)
    ]
    res = select(cands, Request(total=3))
    assert {c.group for c in res.selected} == {"IN_CAPPED"}
    res = select(cands, Request(total=3, groups={"UNKNOWN": Bound(min=3)}))
    assert {c.group for c in res.selected} == {"UNKNOWN"}


def test_min_max_exact_bounds():
    cands = pool_4321()
    res = select(
        cands, Request(total=5, groups={"OS_UNCAPPED": Bound(min=2), "IN_CAPPED": Bound(max=1)})
    )
    g = lambda name: sum(c.group == name for c in res.selected)  # noqa: E731
    assert g("OS_UNCAPPED") >= 2 and g("IN_CAPPED") <= 1
    assert res.total_score == pytest.approx(
        brute(
            cands, Request(total=5, groups={"OS_UNCAPPED": Bound(min=2), "IN_CAPPED": Bound(max=1)})
        )[0][0]
        / -SCALE
    )
    with pytest.raises(SelectionRequestError):
        Bound(exact=2, min=1).resolve(5)
    with pytest.raises(SelectionRequestError):
        Bound(min=4, max=2).resolve(5)


def test_deterministic_under_input_order_and_ties():
    cands = [Candidate(i, 1.0, g) for i, g in enumerate(["IN_CAPPED", "OS_CAPPED"] * 6, start=1)]
    a = select(cands, Request(total=4))
    rng = random.Random(7)
    shuffled = cands[:]
    rng.shuffle(shuffled)
    b = select(shuffled, Request(total=4))
    assert [c.player_id for c in a.selected] == [c.player_id for c in b.selected]
    assert sorted(c.player_id for c in a.selected) == [1, 2, 3, 4]  # smallest ids win ties


def test_role_constraints_match_brute_force_and_count_unknown_roles():
    roles = ["Batter", "Bowler", "All Rounder", "Wicket Keeper"]
    rng = random.Random(3)
    cands = [
        Candidate(i, round(rng.uniform(-1, 1), 2), rng.choice(GROUPS[:4]), roles[i % 4])
        for i in range(1, 13)
    ]
    cands.append(Candidate(99, 5.0, "IN_CAPPED", None))  # unknown role: excluded when roles used
    req = Request(
        total=5,
        groups={"IN_CAPPED": Bound(min=1)},
        roles={"Bowler": Bound(min=2), "Wicket Keeper": Bound(exact=1)},
    )
    res = select(cands, req)
    ref = brute(cands, req)
    if ref is None:
        assert res.status == "INFEASIBLE"
    else:
        assert res.status == "OK"
        assert res.total_score == pytest.approx(-ref[0][0] / SCALE)
        assert sorted(c.player_id for c in res.selected) == list(ref[0][1])
    assert res.excluded_unknown_role == 1 and 99 not in {c.player_id for c in res.selected}


def test_random_requests_match_brute_force():
    rng = random.Random(20260512)
    for _ in range(150):
        k = rng.randint(6, 12)
        cands = [
            Candidate(i, round(rng.uniform(-1, 1), 1), rng.choice(GROUPS), None)
            for i in range(1, k + 1)
        ]
        total = rng.randint(1, min(6, k))
        groups = {}
        for g in rng.sample(GROUPS, rng.randint(0, 3)):
            kind = rng.choice(["exact", "min", "max"])
            groups[g] = Bound(**{kind: rng.randint(0, 3)})
        req = Request(total=total, groups=groups)
        ref = brute(cands, req)
        res = select(cands, req)
        if ref is None:
            assert res.status == "INFEASIBLE"
        else:
            assert res.status == "OK"
            assert sorted(c.player_id for c in res.selected) == list(ref[0][1])
            assert res.total_score == pytest.approx(-ref[0][0] / SCALE)


def test_request_validation():
    with pytest.raises(SelectionRequestError):
        select([], Request(total=0))
    with pytest.raises(SelectionRequestError):
        select([Candidate(1, 0.0, "IN_CAPPED")], Request(total=1, groups={"NOPE": Bound(exact=1)}))
    with pytest.raises(SelectionRequestError):
        select([Candidate(1, 0.0, "IN_CAPPED"), Candidate(1, 0.1, "IN_CAPPED")], Request(total=1))
    with pytest.raises(SelectionRequestError):
        select([], Request(total=20, roles={"Batter": Bound(min=1)}))


@pytest.mark.parametrize(
    ("nat", "status", "group"),
    [
        ("Indian", "DERIVED_CAPPED", "IN_CAPPED"),
        ("Indian", "VERIFIED_CAPPED", "IN_CAPPED"),
        ("Indian", "VERIFIED_UNCAPPED", "IN_UNCAPPED"),
        ("Overseas", "DERIVED_CAPPED", "OS_CAPPED"),
        ("Overseas", "VERIFIED_CAPPED", "OS_CAPPED"),
        ("Overseas", "VERIFIED_UNCAPPED", "OS_UNCAPPED"),
        ("Unknown", "DERIVED_CAPPED", "UNKNOWN"),
        ("Indian", "UNKNOWN", "UNKNOWN"),
    ],
)
def test_assign_group(nat, status, group):
    assert assign_group(nat, status) == group


@pytest.mark.parametrize("legacy", ["Capped", "Uncapped"])
def test_assign_group_rejects_legacy_phase4_labels(legacy):
    # Phase 5: legacy labels must be migrated explicitly, never relabelled silently
    with pytest.raises(ValueError, match="legacy status"):
        assign_group("Indian", legacy)
