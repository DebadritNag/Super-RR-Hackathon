"""Chronological TRAIN / VALIDATION / TEST split, rolling origins and the test-period lock.

Assignment is a pure function of ``match_date``; deliveries follow their match. The test lock is
a convention-level guard (not a security boundary): TEST outcome columns live in a
``LockedFrame`` whose values cannot be read before ``evaluate_on_test`` opens the lock.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase4.config import Phase4ConfigError, load_split_config
from app.phase4.constants import LOCK_LOG, PERIODS


class TestPeriodLockError(RuntimeError):
    """A TEST-period outcome was read before the single final evaluation opened the lock."""

    __test__ = False  # not a pytest class


class SplitIntegrityError(RuntimeError):
    """The chronological split is invalid."""


def _ts(value: str | None) -> pd.Timestamp | None:
    return None if value is None else pd.Timestamp(value).normalize()


@dataclass(frozen=True)
class Split:
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    test_start: pd.Timestamp
    test_core_end: pd.Timestamp | None
    pre_test: tuple[str, ...]
    outcome_prefixes: tuple[str, ...]
    rolling_origins: tuple[dict, ...]

    @classmethod
    def from_config(cls, cfg: dict[str, Any] | None = None) -> Split:
        cfg = cfg or load_split_config()
        if "periods" not in cfg:
            raise Phase4ConfigError("split config is missing 'periods'")
        p = cfg["periods"]
        try:
            split = cls(
                train_end=_ts(p["TRAIN"]["end"]),
                validation_start=_ts(p["VALIDATION"]["start"]),
                validation_end=_ts(p["VALIDATION"]["end"]),
                test_start=_ts(p["TEST"]["start"]),
                test_core_end=_ts(cfg.get("test_core_end")),
                pre_test=tuple(cfg.get("pre_test_window", ["TRAIN", "VALIDATION"])),
                outcome_prefixes=tuple(cfg.get("outcome_column_prefixes", [])),
                rolling_origins=tuple(cfg.get("rolling_origins", [])),
            )
        except (KeyError, TypeError) as exc:
            raise Phase4ConfigError(f"invalid split periods: {exc}") from exc
        split.validate()
        return split

    def validate(self) -> None:
        one = pd.Timedelta(days=1)
        if None in (self.train_end, self.validation_start, self.validation_end, self.test_start):
            raise SplitIntegrityError("TRAIN end, VALIDATION and TEST start must be set")
        if self.validation_start != self.train_end + one:
            raise SplitIntegrityError("VALIDATION must start the day after TRAIN ends")
        if self.test_start != self.validation_end + one:
            raise SplitIntegrityError("TEST must start the day after VALIDATION ends")
        if not self.train_end < self.validation_end:
            raise SplitIntegrityError("periods must be chronologically ordered")

    def assign_period(self, dates: pd.Series | pd.DatetimeIndex) -> pd.Series:
        d = pd.to_datetime(pd.Series(dates)).dt.normalize()
        if d.isna().any():
            raise SplitIntegrityError("match_date is missing for at least one match")
        code = (d > self.train_end).astype(int) + (d > self.validation_end).astype(int)
        return pd.Series(np.array(PERIODS)[code.to_numpy()], index=d.index, name="period")

    def period_of(self, date: str | pd.Timestamp) -> str:
        return str(self.assign_period(pd.Series([pd.Timestamp(date)])).iloc[0])

    def is_outcome_column(self, name: str) -> bool:
        return name.startswith(self.outcome_prefixes) or "residual" in name

    def rolling_folds(self) -> list[dict[str, Any]]:
        """Each fold is fitted on match_date < origin and evaluated on its own year."""
        out = []
        for f in self.rolling_origins:
            out.append(
                {
                    "origin": pd.Timestamp(f["origin"]),
                    "fit_rule": "match_date < origin",
                    "evaluation_start": pd.Timestamp(f["evaluation_start"]),
                    "evaluation_end": pd.Timestamp(f["evaluation_end"]),
                }
            )
        return out

    def fold_masks(self, match_date: pd.Series, fold: dict) -> tuple[pd.Series, pd.Series]:
        d = pd.to_datetime(match_date).dt.normalize()
        fit = d < fold["origin"]
        ev = (d >= fold["evaluation_start"]) & (d <= fold["evaluation_end"])
        return fit, ev


def assign_matches(matches: pd.DataFrame, split: Split) -> pd.DataFrame:
    """One row per match with its period (``match_id``, ``match_date`` required)."""
    out = matches[["match_id", "match_date"]].drop_duplicates("match_id").copy()
    if "competition_type" in matches:
        out["competition_type"] = matches.drop_duplicates("match_id")["competition_type"].to_numpy()
    out["period"] = split.assign_period(out["match_date"]).to_numpy()
    return out.sort_values(["match_date", "match_id"]).reset_index(drop=True)


def attach_period(df: pd.DataFrame, split: Split) -> pd.DataFrame:
    """Attach ``period`` to a delivery-level frame by its match date (deliveries stay together)."""
    out = df.copy()
    out["period"] = split.assign_period(out["match_date"]).to_numpy()
    return out


def check_split_integrity(df: pd.DataFrame, split: Split) -> dict[str, Any]:
    """Return integrity findings for a delivery- or match-level frame that has ``period``."""
    per_match = df.groupby("match_id")["period"].nunique()
    expected = split.assign_period(df["match_date"]).to_numpy()
    bounds = df.groupby("period")["match_date"].agg(["min", "max"])
    ordered = True
    prev_max = None
    for p in PERIODS:
        if p not in bounds.index:
            continue
        if prev_max is not None and not bounds.loc[p, "min"] > prev_max:
            ordered = False
        prev_max = bounds.loc[p, "max"]
    return {
        "matches_in_more_than_one_period": int((per_match > 1).sum()),
        "rows_with_period_not_equal_to_date_rule": int((df["period"].to_numpy() != expected).sum()),
        "periods_strictly_ordered_by_date": ordered,
        "periods_present": sorted(df["period"].unique().tolist()),
    }


# ---------------------------------------------------------------- test-period lock
class TestLock:
    """Append-only lock log plus the open/closed state of the TEST outcomes."""

    __test__ = False

    def __init__(self, log_path: Path | str = LOCK_LOG):
        self.log_path = Path(log_path)
        self.entries: list[dict[str, Any]] = []
        if self.log_path.exists():
            self.entries = json.loads(self.log_path.read_text(encoding="utf-8"))
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def _append(self, event: str, **fields: Any) -> dict[str, Any]:
        entry = {"seq": len(self.entries) + 1, "event": event, **fields}
        self.entries.append(entry)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(
            json.dumps(self.entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return entry

    def denied(self, caller: str, columns: list[str]) -> None:
        self._append("READ_DENIED", caller=caller, columns=sorted(columns))

    def freeze(self, frozen_path: Path | str) -> str:
        """Record the SHA-256 of the frozen-choices file (must come before OPEN)."""
        digest = hashlib.sha256(Path(frozen_path).read_bytes()).hexdigest()
        self._append("FREEZE", sha256=digest)
        return digest

    def opened_before(self) -> bool:
        return any(e["event"] == "OPEN" for e in self.entries)

    def _open_for_evaluation(self, frozen_path: Path | str) -> None:
        path = Path(frozen_path)
        if not path.exists():
            raise TestPeriodLockError("frozen choices file is missing; test stays locked")
        if self.opened_before():
            raise TestPeriodLockError("the test lock has already been opened once")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        freezes = [e for e in self.entries if e["event"] == "FREEZE"]
        if not freezes or freezes[-1]["sha256"] != digest:
            raise TestPeriodLockError(
                "frozen choices file does not match its FREEZE log entry; test stays locked"
            )
        self._append("OPEN", sha256=digest)
        self._open = True

    def _close(self) -> None:
        self._open = False
        self._append("CLOSE")


class LockedFrame:
    """TEST outcome columns. Values are unreadable while the lock is closed."""

    def __init__(self, frame: pd.DataFrame, lock: TestLock):
        self._frame = frame
        self._lock = lock

    @property
    def columns(self) -> list[str]:
        return list(self._frame.columns)

    def __len__(self) -> int:
        return len(self._frame)

    def _check(self, columns: list[str] | None = None) -> None:
        if self._lock.is_open:
            return
        caller = inspect.stack()[2].function
        self._lock.denied(caller, columns if columns is not None else self.columns)
        raise TestPeriodLockError("TEST outcomes are locked until evaluate_on_test opens the lock")

    def __getitem__(self, key: Any) -> Any:
        cols = [key] if isinstance(key, str) else list(key) if isinstance(key, list) else None
        self._check(cols)
        return self._frame[key]

    @property
    def values(self) -> np.ndarray:
        self._check()
        return self._frame.to_numpy()

    def to_numpy(self) -> np.ndarray:
        self._check()
        return self._frame.to_numpy()

    def to_frame(self) -> pd.DataFrame:
        self._check()
        return self._frame.copy()

    def __iter__(self) -> Iterator[Any]:
        self._check()
        return iter(self._frame)

    def sum(self) -> Any:
        self._check()
        return self._frame.sum()


@dataclass
class SplitFrames:
    """Delivery-level frames by period. TEST outcomes are in a LockedFrame."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test_state: pd.DataFrame
    test_outcomes: LockedFrame

    @property
    def pre_test(self) -> pd.DataFrame:
        return pd.concat([self.train, self.validation], ignore_index=True)


def split_frames(df: pd.DataFrame, split: Split, lock: TestLock) -> SplitFrames:
    """Partition a delivery-level frame; TEST outcome columns are moved behind the lock."""
    d = attach_period(df, split)
    out_cols = [c for c in d.columns if split.is_outcome_column(c)]
    test = d[d["period"] == "TEST"]
    return SplitFrames(
        train=d[d["period"] == "TRAIN"].reset_index(drop=True),
        validation=d[d["period"] == "VALIDATION"].reset_index(drop=True),
        test_state=test.drop(columns=out_cols).reset_index(drop=True),
        test_outcomes=LockedFrame(test[out_cols].reset_index(drop=True), lock),
    )


def write_frozen_choices(choices: dict[str, Any], path: Path | str, lock: TestLock) -> str:
    """Write the frozen choices (deterministic JSON) and record the FREEZE entry."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(choices, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock.freeze(p)


def evaluate_on_test(frozen_path: Path | str, lock: TestLock, fn: Callable[[TestLock], Any]) -> Any:
    """The single named final evaluation: opens the lock once, runs ``fn``, closes it."""
    lock._open_for_evaluation(frozen_path)
    try:
        return fn(lock)
    finally:
        lock._close()
