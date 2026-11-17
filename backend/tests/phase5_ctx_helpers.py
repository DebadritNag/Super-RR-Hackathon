"""Synthetic stored context rows, artifacts and stores for the dynamic ranking tests."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from app.phase5 import context_eligibility as ce
from app.phase5 import context_stats as cs
from app.phase5.constants import CONFIG_DIR
from app.phase5.ranking_engine import ContextEngine
from app.phase5.store import write_p5_table
from app.repositories.phase5_repo import frame_hash, load_context_config
from tests.phase4_api_helpers import N_PLAYERS, base_classification_v2, build_store

LADDERS = json.loads((CONFIG_DIR / "pressure_eligibility_rules_v1.json").read_text("utf-8"))[
    "ladders"
]
SHRINK = "shrink_tau4"
PHASES = cs.PHASES
SITS = cs.SITUATIONS


def make_cfg(n_boot: int = 200) -> dict:
    cfg = load_context_config()
    cfg["n_boot"] = n_boot
    return cfg


def synth_stats(seed: int = 11, n_train: int = 50, n_val: int = 18, tag: int = 0) -> pd.DataFrame:
    """Players 1..24 (batters 1..24, bowlers 7..24) over TRAIN and VALIDATION matches."""
    rng = np.random.default_rng(seed)
    rows = []
    mid = 1000 * (tag + 1)
    effect = {p: 0.35 - 0.03 * p + rng.normal(0, 0.05) for p in range(1, N_PLAYERS + 1)}
    for comp in ("IPL", "T20I"):
        for k in range(n_train + n_val):
            mid += 1
            period = "TRAIN" if k < n_train else "VALIDATION"
            date = f"{2024 if k < n_train else 2025}-{1 + (k % 12):02d}-{1 + (k % 27):02d}"
            for role in ("batter", "bowler"):
                lo = 1 if role == "batter" else 7
                for pid in range(lo, N_PLAYERS + 1):
                    if rng.random() > 0.6:
                        continue
                    sit = "chase" if rng.random() < 0.5 else "first_innings"
                    for ph in PHASES:
                        if rng.random() < 0.35:
                            continue
                        n = int(rng.integers(2, 9))
                        r = rng.normal(effect[pid] * (1 if role == "batter" else -1), 1.0, n)
                        rows.append(
                            {
                                "player_id": pid,
                                "match_id": mid,
                                "comp": comp,
                                "role": role,
                                "stream": "runs" if role == "batter" else "charged",
                                "period": period,
                                "match_date": date,
                                "phase": ph,
                                "situation": sit,
                                "n": float(n),
                                "s": float(r.sum()),
                                "s2": float((r**2).sum()),
                                "e": float(n * 1.3),
                            }
                        )
    out = pd.DataFrame(rows)[cs.STAT_COLUMNS]
    cs.check_stats(out)
    return out


def build_all(stats: pd.DataFrame, cfg: dict | None = None) -> dict[str, pd.DataFrame]:
    return ce.build_artifacts(stats, cfg or make_cfg(), LADDERS, SHRINK)


def player_stats_frame() -> pd.DataFrame:
    rows = []
    for pid in range(1, N_PLAYERS + 1):
        for fmt in ("IPL", "T20I"):
            rows.append({"player_id": pid, "format": fmt, "matches_played": 5 + pid,
                         "window": "PRE_TEST"})  # fmt: skip
    return pd.DataFrame(rows)


def manifest(stats: pd.DataFrame, cls: pd.DataFrame) -> dict:
    return {
        "model_version": "p5_context_v1_train",
        "definition_id": "any|q0.75",
        "baseline_version": "p4_baseline_b0_train_frozen_v1",
        "shrinkage_config": SHRINK,
        "restrictions_applied": "synthetic restrictions",
        "config_hashes": {"context_rules": "synthetic"},
        "classification_hash": frame_hash(cls),
        "stats_hash": frame_hash(stats),
    }


def make_engine(
    stats: pd.DataFrame | None = None,
    art: dict | None = None,
    cfg: dict | None = None,
    version: str = "v1",
) -> tuple[ContextEngine, pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame]:
    stats = synth_stats() if stats is None else stats
    cfg = cfg or make_cfg()
    art = art or build_all(stats, cfg)
    cls = base_classification_v2()
    eng = ContextEngine(
        stats, art["rules"], art["scores"], cfg, manifest(stats, cls), player_stats_frame(), version
    )
    return eng, cls, art, stats


def build_context_store(tmp: Path, stats: pd.DataFrame, art: dict, overrides=None) -> Path:
    """Phase 4 synthetic store plus the stored context tables (and a coverage table)."""
    store = build_store(tmp, overrides)
    con = duckdb.connect(str(store), read_only=True)
    try:
        cls = con.execute("SELECT * FROM p5_player_classification").df()
    finally:
        con.close()
    write_p5_table(stats, "p5_context_stats", store)
    write_p5_table(art["rules"], "p5_context_eligibility_rules", store)
    write_p5_table(art["fit"], "p5_context_fit", store)
    write_p5_table(art["scores"], "p5_context_scores", store)
    write_p5_table(
        pd.DataFrame([{"manifest_json": json.dumps(manifest(stats, cls), sort_keys=True)}]),
        "p5_context_manifest",
        store,
    )
    return store
