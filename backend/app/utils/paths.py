"""Path helpers."""

from __future__ import annotations

from pathlib import Path


def posix(path: Path | str) -> str:
    return Path(path).as_posix()


def sql_quote(value: str) -> str:
    """Quote a string literal for SQL by doubling single quotes."""
    return "'" + str(value).replace("'", "''") + "'"
