"""Phase 7: production code under app/ must hold no invented players, rankings or random scores.

Synthetic fixtures are allowed only under tests/ (they are clearly synthetic: "Player 01" etc.).
Seeded numpy generators used for the documented bootstrap/split-half resampling are allow-listed
by pattern (default_rng / SeedSequence); unseeded or scoring-style randomness is banned.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
SQUAD = BACKEND.parent / "ipl squad.csv"

FILES = sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)

BANNED_RANDOM = re.compile(
    r"\brandom\.(random|randint|choice|choices|uniform|shuffle|sample|gauss)\(|"
    r"\bnp\.random\.(rand|randn|randint|random|choice|uniform|normal|shuffle|permutation)\(|"
    r"\bnumpy\.random\.(rand|randn|randint|random|choice|uniform|normal)\(|"
    r"Math\.random|\bfaker\b|\bMOCK_|\bDEMO_|\bfake_|\bdummy_|lorem ipsum",
    re.I,
)
# literal ranking arrays / hand-written rank values
RANKING_LITERAL = re.compile(
    r"""["']rank(_position)?["']\s*:\s*\d+|\brank(ing)?s?\s*=\s*\[\s*["'{(\d]|"""
    r"""\b(top_?10|TOP_?10)\w*\s*=\s*[\[({]""",
)
SCORE_LITERAL = re.compile(r"""["'](pressure_)?score["']\s*:\s*\d+(\.\d+)?\s*[,}]""")


def _squad_names() -> set[str]:
    if not SQUAD.exists():
        pytest.skip("ipl squad.csv not available")
    with open(SQUAD, encoding="utf-8-sig") as fh:
        return {r["player"].strip() for r in csv.DictReader(fh) if " " in r["player"].strip()}


def test_production_files_were_found():
    assert len(FILES) > 50


def test_no_player_name_literals_in_production_code():
    names = _squad_names()
    assert len(names) > 100
    hits = []
    for p in FILES:
        text = p.read_text(encoding="utf-8")
        for n in names:
            if f'"{n}"' in text or f"'{n}'" in text:
                hits.append((p.relative_to(BACKEND).as_posix(), n))
    assert hits == []


def test_no_random_score_generation_or_mock_tokens():
    hits = []
    for p in FILES:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if BANNED_RANDOM.search(line):
                hits.append((p.relative_to(BACKEND).as_posix(), i, line.strip()))
    assert hits == []


def test_no_hardcoded_ranking_arrays_or_score_values():
    hits = []
    for p in FILES:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if RANKING_LITERAL.search(line) or SCORE_LITERAL.search(line):
                hits.append((p.relative_to(BACKEND).as_posix(), i, line.strip()))
    assert hits == []


def test_scanner_detects_planted_violations():
    """The patterns themselves must fire on synthetic examples (guards against a dead scan)."""
    assert BANNED_RANDOM.search("x = np.random.rand(10)")
    assert BANNED_RANDOM.search("s = random.random() * 100")
    assert not BANNED_RANDOM.search("rng = np.random.default_rng(seed)")
    assert RANKING_LITERAL.search('row = {"rank": 1, "name": "X"}')
    assert RANKING_LITERAL.search("top10 = [")
    assert SCORE_LITERAL.search('{"score": 94.8}')
