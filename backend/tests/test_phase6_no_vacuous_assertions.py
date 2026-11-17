"""No test may contain an assertion that can never fail (Phase 6 cleanup, decision 6b)."""

from __future__ import annotations

from pathlib import Path

from app.phase6.cleanup_scans import scan_vacuous_assertions, vacuous_in_source

TESTS = Path(__file__).resolve().parent
THIS = Path(__file__).name

OLD_LINES = (
    'assert r["interval_low"] <= r["score"] <= r["interval_high"] or True\n'
    'assert len(table) == len(specs) == len(set(table["spec_hash"]) | set()) or True\n'
    "assert s.team_wickets_before.tolist() == [0, 1][:1] + [0, 1][:0] or True\n"
)


def test_no_test_file_contains_an_always_true_assertion():
    hits = scan_vacuous_assertions(TESTS, exclude=(THIS,))
    assert hits == [], f"vacuous assertions: {hits}"


def test_scanner_flags_the_three_original_vacuous_lines():
    hits = vacuous_in_source(OLD_LINES, "old.py")
    assert [h[1] for h in hits] == [1, 2, 3]
    assert all("truthy constant" in h[2] for h in hits)


def test_scanner_flags_assert_true_and_constants_but_not_real_assertions():
    src = "assert True\nassert 1\nassert x or y\nassert a <= b or c > d\nassert x == 1\n"
    assert [h[1] for h in vacuous_in_source(src)] == [1, 2]


def test_scanner_catches_a_multiline_assert_with_a_true_operand():
    src = "assert (\n    a == b\n    or True\n)\n"
    assert vacuous_in_source(src)  # the AST sees the BoolOp(Or) with a True operand
