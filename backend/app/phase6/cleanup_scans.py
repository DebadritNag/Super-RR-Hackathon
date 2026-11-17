"""Static scans used by the Phase 6 cleanup tests and ``scripts/phase6_cleanup_checks.py``.

Three scans, all read-only:

* ``scan_vacuous_assertions``: asserts that can never fail (``assert x or True``, ``assert True``,
  ``assert <truthy constant>``), found with ``ast`` plus a plain-text ``or True`` guard.
* ``walk_model_fields``: every field name reachable from a Pydantic response model (nested models,
  unions, generics, list/dict element types).
* ``scan_wording``: text that describes the classification as having four statuses.
"""

from __future__ import annotations

import ast
import re
import types
import typing
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# ----------------------------------------------------------------------------- vacuous asserts
_TEXT_PATTERN = re.compile(r"\bor\s+True\b")


def _truthy_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and bool(node.value)


def vacuous_in_source(source: str, name: str = "<source>") -> list[tuple[str, int, str]]:
    """Return (file, line, reason) for each always-true assert in ``source``."""
    found: list[tuple[str, int, str]] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if _truthy_constant(test):
            found.append((name, node.lineno, "assert of a truthy constant"))
        elif isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
            if any(_truthy_constant(v) for v in test.values):
                found.append((name, node.lineno, "assert ... or <truthy constant>"))
    seen = {line for _, line, _ in found}
    for i, line in enumerate(source.splitlines(), start=1):
        code = line.split("#", 1)[0]
        if _TEXT_PATTERN.search(code) and i not in seen and code.lstrip().startswith("assert"):
            found.append((name, i, "text 'or True' in an assert line"))
    return sorted(found, key=lambda t: t[1])


def scan_vacuous_assertions(
    tests_dir: Path, exclude: tuple[str, ...] = ()
) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for path in sorted(Path(tests_dir).rglob("*.py")):
        if path.name in exclude:
            continue
        rel = path.as_posix()
        out.extend(vacuous_in_source(path.read_text(encoding="utf-8"), rel))
    return out


# ----------------------------------------------------------------------------- schema walk
def _model_args(tp: Any) -> list[Any]:
    origin = typing.get_origin(tp)
    if origin is None:
        return [tp]
    args = typing.get_args(tp)
    if origin is typing.Annotated:
        return _model_args(args[0])
    if origin in (typing.Union, types.UnionType, list, tuple, set, frozenset, dict):
        out: list[Any] = []
        for a in args:
            out.extend(_model_args(a))
        return out
    # Generic pydantic model such as Page[PublicPlayerRow]
    return [tp]


def walk_model_fields(model: Any, _seen: set[Any] | None = None) -> set[str]:
    """All field names reachable from ``model`` (a model class, generic alias or union)."""
    seen = _seen if _seen is not None else set()
    names: set[str] = set()
    for tp in _model_args(model):
        if not (isinstance(tp, type) and issubclass(tp, BaseModel)):
            continue
        if tp in seen:
            continue
        seen.add(tp)
        for fname, finfo in tp.model_fields.items():
            names.add(fname)
            names |= walk_model_fields(finfo.annotation, seen)
    return names


def walk_json_keys(obj: Any) -> set[str]:
    """All dictionary keys in a parsed JSON value, recursively."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= walk_json_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= walk_json_keys(v)
    return keys


# Names that would expose a score, rank, eligibility or publication state.
FORBIDDEN_PUBLIC_FIELD = re.compile(
    r"score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict",
    re.IGNORECASE,
)


def forbidden_public_names(names: set[str]) -> list[str]:
    return sorted(n for n in names if FORBIDDEN_PUBLIC_FIELD.search(n))


# ----------------------------------------------------------------------------- wording
_NEGATED = re.compile(r"\bnot\s+(an?\s+)?(established\s+)?fourth\s+status\b", re.IGNORECASE)
_FOUR = re.compile(
    r"(?<!phase\s)\b(four|4)\s+(\*\*)?(separate|real|distinct)?(\*\*)?\s*(classification\s+|international\s+|capped\s+)?"
    r"(statuses|status values|status)\b"
    r"|\b(four|4)\s+(\*\*)?separate(\*\*)?\s+values\b"
    r"|\bfourth\s+status\b|\b3\s*x\s*4\s+(combinations|statuses)\b",
    re.IGNORECASE,
)


def scan_wording(text: str) -> list[str]:
    """Return the offending snippets that call the classification four-valued."""
    return [m.group(0) for m in _FOUR.finditer(_NEGATED.sub("", text))]
