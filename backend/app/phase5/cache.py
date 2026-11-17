"""Deterministic in-memory cache of full (unsliced) context rankings.

Key = SHA-256 of the JSON-encoded list (filter-spec hash, data version, model version, gate-config
version, visibility scope, methodology-lock version, gate-state hash). Any change of one component
changes the key. ``scope`` is ``internal`` or ``public``: the two never share an entry. The gate
state hash is the SHA-256 of the sorted ids of the gates failing at request time. Publication
gates themselves are still recomputed on read and are not cached; the cache holds the pre-gate
ranking, so the gate component only guarantees that an entry made under one gate state is never
reused under another. ``invalidate_if_version_changed`` drops every entry when the data, model or
lock version differs from the one the cache was filled under.

Isolation: ``put`` stores a deep copy and every ``get``/``get_or_compute`` returns a deep copy
(on a miss too), so no caller ever holds a reference to cache memory and a mutated response
cannot change a later response.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

GATE_CONFIG_VERSION = "p5_gates_v1"
SCOPES = ("internal", "public")


def gate_state_hash(failing_gate_ids: list[str] | tuple[str, ...]) -> str:
    """SHA-256 of the sorted ids of the gates that currently fail."""
    body = json.dumps(sorted(str(g) for g in failing_gate_ids), separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def cache_key(
    spec_hash: str,
    data_version: str,
    model_version: str,
    gate_version: str,
    scope: str,
    lock_version: str,
    gate_state: str,
) -> str:
    """Key of one cached ranking. Every component is required (no defaults on purpose)."""
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, got {scope!r}")
    parts = [spec_hash, data_version, model_version, gate_version, scope, lock_version, gate_state]
    body = json.dumps(parts, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class RankingCache:
    def __init__(self, max_entries: int = 256) -> None:
        self.max_entries = max(1, int(max_entries))
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._versions: tuple[str, str, str] | None = None
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0

    def invalidate_if_version_changed(
        self, data_version: str, model_version: str, lock_version: str
    ) -> bool:
        with self._lock:
            current = (data_version, model_version, lock_version)
            changed = self._versions is not None and self._versions != current
            if changed:
                self._data.clear()
                self.invalidations += 1
            self._versions = current
            return changed

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self.hits += 1
                return copy.deepcopy(self._data[key])
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = copy.deepcopy(value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)
                self.evictions += 1

    def get_or_compute(
        self,
        spec_hash: str,
        data_version: str,
        model_version: str,
        compute: Callable[[], Any],
        *,
        scope: str,
        lock_version: str,
        gate_state: str,
        gate_version: str = GATE_CONFIG_VERSION,
    ) -> tuple[Any, bool]:
        """Returns (private copy of the value, cache_hit)."""
        self.invalidate_if_version_changed(data_version, model_version, lock_version)
        key = cache_key(
            spec_hash, data_version, model_version, gate_version, scope, lock_version, gate_state
        )
        hit = self.get(key)
        if hit is not None:
            return hit, True
        value = compute()
        self.put(key, value)
        return value, False

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._data),
                "max_entries": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "invalidations": self.invalidations,
                "evictions": self.evictions,
            }
