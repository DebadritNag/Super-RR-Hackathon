"""Phase 5 analytical pipeline: pre-test frame, baseline, pressure cells, frozen rules.

Reuses the unchanged Phase 4 functions. Only TRAIN and VALIDATION rows are loaded (TEST rows are
dropped before any frame exists) and the TEST lock is never opened here. Nothing in this module
imports a Cricsheet loader.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4.baseline import STREAMS, BaselineSet, fit_baseline_set, prepare_frame
from app.phase4.config import file_sha256
from app.phase4.constants import SCOPE
from app.phase4.data import load_state_with_period
from app.phase4.lockguard import drop_test_rows
from app.phase4.split import Split, TestLock
from app.phase5.constants import CONFIG_DIR, FROZEN_CHOICES, PROVISIONAL_DEFINITION, SEED
from app.phase5.lockguard import PHASE5_LOCK_LOG
from app.services.pressure_service import EXPLORATORY_DB

INVESTIGATION_CONFIG = CONFIG_DIR / "phase5_investigation_v1.json"
FORMAT_WEIGHTS = CONFIG_DIR / "format_weights_v1.json"
ELIG_RULES = CONFIG_DIR / "pressure_eligibility_rules_v1.json"
CellKey = tuple[str, str]
StreamKey = tuple[str, str, str]


def load_config(path: Path | str = INVESTIGATION_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_frozen(path: Path | str = FROZEN_CHOICES) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class Study:
    """Pre-test state, TRAIN-fitted baseline B0, frozen choices and shared bootstrap weights."""

    d: pd.DataFrame
    bs: BaselineSet
    lock: TestLock
    frozen: dict[str, Any]
    cfg: dict[str, Any]
    gm: pd.Index
    W: np.ndarray
    n_boot: int
    seed: int
    _thr: dict[float, dict[str, float]] = field(default_factory=dict)
    _base: dict[tuple[str, str], pd.DataFrame] = field(default_factory=dict)
    _cells: dict[str, dict[StreamKey, en.Cell]] = field(default_factory=dict)

    # -------------------------------------------------------------- thresholds and rows
    def thresholds(self, defn: str) -> dict[str, float]:
        _, q = sc.parse_definition(defn)
        if q not in self._thr:
            self._thr[q] = sc.fit_thresholds(self.d[self.d["period"] == "TRAIN"], q)
        return self._thr[q]

    def base(self, role: str, stream: str) -> pd.DataFrame:
        if (role, stream) not in self._base:
            self._base[(role, stream)] = en.base_rows(self.d, self.bs, role, stream, self.lock)
        return self._base[(role, stream)]

    def tagged(self, defn: str, role: str, stream: str) -> pd.DataFrame:
        return en.tag_rows(self.base(role, stream), self.d, defn, self.thresholds(defn))

    def pressure_rows(self, defn: str, role: str, stream: str) -> pd.DataFrame:
        t = self.tagged(defn, role, stream)
        return t[t["press"]]

    # -------------------------------------------------------------- cells
    def all_cells(self, defn: str) -> dict[StreamKey, en.Cell]:
        """(format, role, stream) -> Cell for the four streams and two formats."""
        if defn not in self._cells:
            out: dict[StreamKey, en.Cell] = {}
            for role, stream, _ in STREAMS:
                press = self.pressure_rows(defn, role, stream)
                for comp in SCOPE:
                    c = en.build_cell(press, comp, role, stream)
                    if c is not None:
                        out[(comp, role, stream)] = c
            self._cells[defn] = out
        return self._cells[defn]

    def primary_cells(self, defn: str) -> dict[CellKey, en.Cell]:
        return {
            (comp, role): c
            for (comp, role, stream), c in self.all_cells(defn).items()
            if stream == en.PRIMARY[role][0]
        }

    # -------------------------------------------------------------- frozen eligibility
    def frozen_rules(self, cells: dict[CellKey, en.Cell]) -> dict[CellKey, dict[str, Any]]:
        """Frozen working-pool ball thresholds (Phase 4) with each cell's own window ratio.

        The thresholds are NOT validated (every cell is ``THRESHOLD_NOT_VALIDATED``). The same
        four numbers are applied to every definition, so pool sizes differ by definition.
        """
        out = {}
        for (comp, role), cell in cells.items():
            rule = self.frozen["eligibility"][f"{comp}|{role}"]["analysis"]
            out[(comp, role)] = {
                "threshold_balls": rule["threshold_balls"],
                "label": rule["label"],
                "wr": el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN"),
            }
        return out

    def format_weights(self) -> dict[str, Any]:
        return json.loads(FORMAT_WEIGHTS.read_text(encoding="utf-8"))


def load_study(
    store: Path | str = EXPLORATORY_DB,
    n_boot: int | None = None,
    seed: int | None = None,
    frozen_path: Path | str = FROZEN_CHOICES,
    config_path: Path | str = INVESTIGATION_CONFIG,
) -> Study:
    """Load pre-test rows, add signals, fit B0 on TRAIN. Refuses any frame holding TEST rows."""
    cfg = load_config(config_path)
    frozen = load_frozen(frozen_path)
    split = Split.from_config()
    raw = drop_test_rows(load_state_with_period(split, store))
    d, _ = prepare_frame(raw, split)
    lock = TestLock(PHASE5_LOCK_LOG)
    d = sc.add_signals(d, lock)
    if (d["period"] == "TEST").any():
        raise RuntimeError("TEST rows reached the Phase 5 pipeline")
    bs = fit_baseline_set(d)
    nb = int(n_boot or cfg["n_boot"])
    sd = int(seed or cfg["seed"] or SEED)
    gm, W = en.global_weights(d["match_id"].to_numpy(), nb, sd)
    return Study(d, bs, lock, frozen, cfg, gm, W, nb, sd)


def config_hashes(extra: dict[str, Path] | None = None) -> dict[str, str]:
    paths = {"investigation_config": INVESTIGATION_CONFIG, "frozen_choices": FROZEN_CHOICES,
             "format_weights": FORMAT_WEIGHTS, "eligibility_rules": ELIG_RULES,
             **(extra or {})}  # fmt: skip
    return {k: file_sha256(v) for k, v in paths.items()}


def reproduce_phase4_scores(
    study: Study, store: Path | str = EXPLORATORY_DB, tol: float = 1e-9
) -> dict[str, Any]:
    """Recompute the carried definition's shrunk estimates and compare to the stored Phase 4 scores.

    Uses the TRAIN-fitted shrinkage of the frozen choice. Any difference above ``tol`` is fatal for
    the callers: no investigation may run on numbers that do not reproduce Phase 4.
    """
    import duckdb

    defn = study.frozen["definition"]["id"]
    cfg_name = study.frozen["shrinkage"]["config"]
    if defn != PROVISIONAL_DEFINITION:
        raise RuntimeError(f"frozen definition {defn} differs from {PROVISIONAL_DEFINITION}")
    con = duckdb.connect(str(store), read_only=True)
    try:
        stored = con.execute(
            "SELECT player_id, role, stream, format, shrunk_estimate, pressure_opportunities "
            "FROM p4_pressure_scores_frozen_rules WHERE definition_id = ? AND shrinkage_config = ?",
            [defn, cfg_name],
        ).df()
    finally:
        con.close()
    worst, n_cmp = 0.0, 0
    per_cell = {}
    for (comp, role), cell in study.primary_cells(defn).items():
        est = en.point_estimates(cell, cell.fit(), cfg_name)
        ref = stored[(stored["format"] == comp) & (stored["role"] == role)
                     & (stored["stream"] == en.PRIMARY[role][0])].set_index("player_id")  # fmt: skip
        mine = pd.Series(est["shrunk"].to_numpy(), index=cell.players)
        common = mine.index.intersection(ref.index)
        diff = (
            float(
                np.max(
                    np.abs(mine[common].to_numpy() - ref.loc[common, "shrunk_estimate"].to_numpy())
                )
            )
            if len(common)
            else float("nan")
        )
        n_ok = int(
            (
                est["n"].to_numpy()
                == ref["pressure_opportunities"].reindex(cell.players).to_numpy()
            ).sum()
        )
        per_cell[f"{comp}|{role}"] = {"players_compared": int(len(common)), "players_in_store": int(len(ref)),
                                      "players_here": int(len(mine)), "max_abs_diff": diff,
                                      "opportunity_counts_equal": n_ok}  # fmt: skip
        worst = max(worst, diff if np.isfinite(diff) else 1.0)
        n_cmp += len(common)
    return {"definition": defn, "shrinkage": cfg_name, "tolerance": tol, "max_abs_diff": worst,
            "players_compared": n_cmp, "reproduces": bool(worst <= tol and n_cmp > 0),
            "per_cell": per_cell}  # fmt: skip
