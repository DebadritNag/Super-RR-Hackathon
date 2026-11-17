"""Experimental refit on TRAIN + VALIDATION (artifact set ``p5_refit_trainval_v1``).

Everything produced here is ``EXPERIMENTAL_NOT_VALIDATED`` and ``INTERNAL_EXPERIMENTAL_ONLY``. The
refit refuses to run unless the methodology lock manifest exists and every locked hash still
matches. TEST rows are never used: the state frame is cut to TRAIN and VALIDATION dates at load time
and a second check refuses any row whose original period is TEST. The unchanged Phase 4 functions
are reused by moving the TRAIN/VALIDATION boundary to the end of VALIDATION (``refit_split``), so
no Phase 4 code is edited. The original ``period`` of each row is kept in ``period_orig``.
Phase 4 tables and reports are only read; their hashes are compared before and after.
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import eligibility as el
from app.phase4 import engine as en
from app.phase4 import scoring as sc
from app.phase4.baseline import STREAMS, fit_baseline_set, prepare_frame, role_frame
from app.phase4.data import load_state_with_period
from app.phase4.lockguard import drop_test_rows
from app.phase4.split import Split, TestLock
from app.phase5 import lock_manifest as lm
from app.phase5.constants import INTERNAL, PROVISIONAL_DEFINITION, REPORTS_DIR, STATUS
from app.phase5.lockguard import PHASE5_LOCK_LOG, assert_phase5_lock_not_opened, file_sha256
from app.phase5.pipeline import Study, load_config, load_frozen
from app.phase5.store import table_hashes, write_p5_table
from app.services.pressure_service import EXPLORATORY_DB

REFIT_ID = "p5_refit_trainval_v1"
MODEL_LABEL = "EXPERIMENTAL_REFIT_TRAIN_VALIDATION"
TABLES = {
    "scores": f"{REFIT_ID}_scores",
    "calibration": f"{REFIT_ID}_baseline_calibration",
    "thresholds": f"{REFIT_ID}_thresholds",
    "comparison": f"{REFIT_ID}_comparison",
    "manifest": f"{REFIT_ID}_manifest",
}


class RefitTestRowsError(RuntimeError):
    """A TEST-period row reached the refit frame."""


# ---------------------------------------------------------------- frame construction
def refit_split(split: Split) -> Split:
    """Split whose TRAIN window ends where VALIDATION ends (VALIDATION becomes empty)."""
    return dataclasses.replace(
        split,
        train_end=split.validation_end,
        validation_start=split.validation_end + pd.Timedelta(days=1),
    )


def assert_no_test(df: pd.DataFrame, column: str = "period_orig") -> None:
    if column not in df.columns:
        raise RefitTestRowsError(f"frame has no '{column}' column; cannot prove TEST is absent")
    if bool((df[column] == "TEST").any()):
        raise RefitTestRowsError("TEST rows reached the refit frame")


def load_pretest_raw(store: Path | str, split: Split) -> pd.DataFrame:
    """TRAIN and VALIDATION rows only, with the original period kept as ``period_orig``."""
    raw = drop_test_rows(load_state_with_period(split, store))
    raw["period_orig"] = raw["period"]
    assert_no_test(raw)
    return raw


def build_refit_frame(raw: pd.DataFrame, split: Split) -> pd.DataFrame:
    """Relabel VALIDATION rows as TRAIN through the moved split boundary (period_orig kept)."""
    assert_no_test(raw)
    d, _ = prepare_frame(raw, refit_split(split))
    assert_no_test(d)
    if set(d["period"].unique()) != {"TRAIN"}:
        raise RefitTestRowsError(
            f"unexpected periods after relabelling: {sorted(d['period'].unique())}"
        )
    return d


# ---------------------------------------------------------------- hashing helpers
def frame_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def frames_hashes(frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    return {k: frame_hash(v) for k, v in sorted(frames.items()) if k != "manifest"}


# ---------------------------------------------------------------- scoring
def score_cells(
    study: Study, defn: str, cfg_name: str, gm: pd.Index, W: np.ndarray
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Primary-stream scores of the four format-role cells under the locked definition."""
    cells = study.primary_cells(defn)
    rules = study.frozen["eligibility"]
    parts, meta = [], {}
    for (comp, role), cell in sorted(cells.items()):
        rule = rules[f"{comp}|{role}"]["analysis"]
        sign = en.PRIMARY[role][1]
        fit = cell.fit()
        est = en.point_estimates(cell, fit, cfg_name)
        pool = el.eligible_mask(est, rule, rule["wr"])
        w = en.cell_weights(cell, gm, W)
        nb, dr = en.draws(cell, est, w)
        thr_b = (rule["threshold_balls"] or 0) * rule["wr"]
        present = pool[:, None] & (nb >= thr_b) & np.isfinite(dr)
        sd = np.where(present, sign * dr, np.nan)
        point = np.where(pool, sign * est["shrunk"].to_numpy(), 0.0)
        rs = en.rank_summary(sd, point, pool)
        t = pd.DataFrame(
            {
                "refit_id": REFIT_ID,
                "status": STATUS,
                "model_label": MODEL_LABEL,
                "publication_status": INTERNAL,
                "official_ranking": False,
                "definition_id": defn,
                "shrinkage_config": cfg_name,
                "fit_window": "TRAIN+VALIDATION",
                "format": comp,
                "role": role,
                "stream": en.PRIMARY[role][0],
                "player_id": cell.players,
                "score": sign * est["shrunk"].to_numpy(),
                "shrunk_estimate": est["shrunk"].to_numpy(),
                "pressure_opportunities": est["n"].to_numpy(),
                "distinct_matches": est["matches"].to_numpy(),
                "effective_sample_size": est["n_eff"].to_numpy(),
                "shrinkage_k": float(est["k"].iloc[0]) if len(est) else float("nan"),
                "working_pool_threshold_balls": rule["threshold_balls"],
                "working_pool_window_ratio": rule["wr"],
                "eligible_working_pool": pool,
                "eligibility_label": np.where(pool, rule["label"], "NOT_ELIGIBLE"),
                "rank": np.where(pool, rs["point_rank"], np.nan),
                "top10_inclusion_prob": np.where(pool, rs["inclusion_prob"], np.nan),
                "rank_lo": np.where(pool, rs["rank_lo"], np.nan),
                "rank_hi": np.where(pool, rs["rank_hi"], np.nan),
            }
        )
        parts.append(t.sort_values(["rank", "player_id"], kind="mergesort", na_position="last"))
        meta[f"{comp}|{role}"] = {
            "players": int(len(cell.players)),
            "eligible": int(pool.sum()),
            "matches": int(len(cell.matches)),
            "shrinkage_k": float(est["k"].iloc[0]) if len(est) else None,
            "floor_hit": bool(fit.get("floor_hit", False)) if isinstance(fit, dict) else None,
        }
    return pd.concat(parts, ignore_index=True), meta


def compare_with_phase4(
    scores: pd.DataFrame, store: Path | str, defn: str, cfg_name: str
) -> pd.DataFrame:
    """Per cell: how the refit differs from the stored TRAIN-only Phase 4 scores."""
    import duckdb

    con = duckdb.connect(str(store), read_only=True)
    try:
        old = con.execute(
            "SELECT player_id, role, stream, format, shrunk_estimate, eligibility_status "
            "FROM p4_pressure_scores_frozen_rules WHERE definition_id = ? AND shrinkage_config = ? "
            "AND \"window\" = 'PRE_TEST'",
            [defn, cfg_name],
        ).df()
    finally:
        con.close()
    rows = []
    for (comp, role), new in scores.groupby(["format", "role"], sort=True):
        sign = en.PRIMARY[role][1]
        o = old[
            (old["format"] == comp) & (old["role"] == role) & (old["stream"] == en.PRIMARY[role][0])
        ]
        o = o.set_index("player_id")
        n = new.set_index("player_id")
        common = n.index.intersection(o.index)
        o_c, n_c = o.loc[common, "shrunk_estimate"], n.loc[common, "shrunk_estimate"]
        o_elig = o["eligibility_status"].str.startswith("ELIGIBLE")
        n_elig = n["eligible_working_pool"].astype(bool)
        both = common[o_elig.reindex(common).to_numpy() & n_elig.reindex(common).to_numpy()]
        top_o = set(
            (sign * o.loc[o_elig, "shrunk_estimate"])
            .sort_values(ascending=False, kind="mergesort")
            .head(10)
            .index
        )
        top_n = set(
            (sign * n.loc[n_elig, "shrunk_estimate"])
            .sort_values(ascending=False, kind="mergesort")
            .head(10)
            .index
        )
        diff = (n_c - o_c).abs()

        def rho(a: pd.Series, b: pd.Series) -> float | None:
            return float(a.rank().corr(b.rank())) if len(a) >= 3 else None

        rows.append(
            {
                "format": comp,
                "role": role,
                "players_phase4": int(len(o)),
                "players_refit": int(len(n)),
                "players_common": int(len(common)),
                "eligible_phase4": int(o_elig.sum()),
                "eligible_refit": int(n_elig.sum()),
                "eligible_both": int(len(both)),
                "spearman_common": rho(o_c, n_c),
                "spearman_eligible_both": rho(
                    o.loc[both, "shrunk_estimate"], n.loc[both, "shrunk_estimate"]
                ),
                "top10_overlap": int(len(top_o & top_n)),
                "top10_size": int(min(10, len(top_o), len(top_n))),
                "mean_abs_change": float(diff.mean()) if len(diff) else None,
                "max_abs_change": float(diff.max()) if len(diff) else None,
                "note": "Phase 4 = TRAIN-fitted, PRE_TEST window; refit = TRAIN+VALIDATION-fitted. Not a validation.",
            }
        )
    return pd.DataFrame(rows)


def calibration_table(study: Study) -> pd.DataFrame:
    """In-sample baseline calibration of the refit baseline, split by original period."""
    rows = []
    for role, stream, _ in STREAMS:
        fr = role_frame(role, study.d)
        ex = study.bs.expected(role, stream, fr)["expected"].to_numpy()
        t = pd.DataFrame(
            {
                "po": fr["period_orig"].to_numpy(),
                "comp": fr["competition_type"].to_numpy(),
                "a": fr[stream].to_numpy(dtype=float),
                "e": ex,
            }
        )
        for (po, comp), g in t.groupby(["po", "comp"], sort=True):
            rows.append(
                {
                    "role": role,
                    "stream": stream,
                    "period_orig": po,
                    "format": comp,
                    "rows": int(len(g)),
                    "actual_sum": float(g["a"].sum()),
                    "expected_sum": float(g["e"].sum()),
                    "ratio_actual_over_expected": float(g["a"].sum() / g["e"].sum())
                    if g["e"].sum()
                    else None,
                    "basis": "IN_SAMPLE_TRAIN_PLUS_VALIDATION",
                }
            )
    return pd.DataFrame(rows)


def thresholds_table(study: Study, defn: str) -> pd.DataFrame:
    new = study.thresholds(defn)
    old = study.frozen["definition"]["train_only_thresholds"]
    rows = [
        {
            "threshold": k,
            "quantile_definition": defn,
            "refit_train_validation": float(new[k]),
            "phase4_train_only": float(old[k]),
            "difference": float(new[k] - old[k]),
        }
        for k in sorted(new)
    ]
    for k, v in sorted(study.frozen["eligibility"].items()):
        a = v["analysis"]
        rows.append(
            {
                "threshold": f"working_pool_balls|{k}",
                "quantile_definition": "LOCKED_FROM_PHASE4",
                "refit_train_validation": float(a["threshold_balls"]),
                "phase4_train_only": float(a["threshold_balls"]),
                "difference": 0.0,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- orchestration
@dataclass
class RefitResult:
    frames: dict[str, pd.DataFrame]
    summary: dict[str, Any]


def _p4_report_hashes(reports: Path) -> dict[str, str]:
    return {p.name: file_sha256(p) for p in sorted(reports.glob("phase4_*")) if p.is_file()}


def run_refit(
    store: Path | str = EXPLORATORY_DB,
    reports: Path | str = REPORTS_DIR,
    lock_path: Path | str = lm.LOCK_PATH,
    n_boot: int | None = None,
    seed: int | None = None,
    write: bool = True,
    verify_files: dict[str, Path] | None = None,
    verify_code: list[Path] | None = None,
) -> RefitResult:
    """Refuses without a valid lock. Fits on TRAIN+VALIDATION, scores, compares, optionally writes."""
    reports, store = Path(reports), Path(store)
    manifest = lm.verify_lock(lock_path, files=verify_files, code=verify_code, store=store)
    choices = manifest["content"]["choices"]
    defn = choices["definition"]["id"]
    if defn != PROVISIONAL_DEFINITION:
        raise lm.LockDriftError(f"locked definition {defn} is not {PROVISIONAL_DEFINITION}")
    cfg_name = choices["shrinkage"]["config"]
    nb = int(n_boot or choices["refit"]["n_boot"])
    sd = int(seed or choices["refit"]["seed"])
    p4_tables_before = table_hashes(store, "p4_")
    p4_reports_before = _p4_report_hashes(reports)
    lock4_before = file_sha256(reports / "phase4_lock_log.json")
    events5_before = assert_phase5_lock_not_opened(PHASE5_LOCK_LOG)

    split = Split.from_config()
    raw = load_pretest_raw(store, split)
    d = build_refit_frame(raw, split)
    lock = TestLock(PHASE5_LOCK_LOG)
    d = sc.add_signals(d, lock)
    assert_no_test(d)
    bs = fit_baseline_set(d)
    gm, W = en.global_weights(d["match_id"].to_numpy(), nb, sd)
    study = Study(d, bs, lock, load_frozen(), load_config(), gm, W, nb, sd)

    scores, meta = score_cells(study, defn, cfg_name, gm, W)
    comparison = compare_with_phase4(scores, store, defn, cfg_name)
    frames = {
        "scores": scores,
        "calibration": calibration_table(study),
        "thresholds": thresholds_table(study, defn),
        "comparison": comparison,
    }
    p4_tables_after = table_hashes(store, "p4_")
    p4_reports_after = _p4_report_hashes(reports)
    lock4_after = file_sha256(reports / "phase4_lock_log.json")
    events5_after = assert_phase5_lock_not_opened(PHASE5_LOCK_LOG)
    pres = {
        "phase4_tables_hashed": len(p4_tables_before),
        "phase4_tables_byte_identical": p4_tables_before == p4_tables_after,
        "phase4_report_files_hashed": len(p4_reports_before),
        "phase4_report_files_byte_identical": p4_reports_before == p4_reports_after,
        "phase4_lock_log_sha256_before": lock4_before,
        "phase4_lock_log_sha256_after": lock4_after,
        "phase5_lock_log_events_before": events5_before,
        "phase5_lock_log_events_after": events5_after,
        "test_opened": False,
        "rows_with_period_orig_test": int((d["period_orig"] == "TEST").sum()),
        "periods_in_refit_frame": sorted(d["period"].unique().tolist()),
        "period_orig_in_refit_frame": sorted(d["period_orig"].unique().tolist()),
    }
    pres["all_preserved"] = bool(
        pres["phase4_tables_byte_identical"]
        and pres["phase4_report_files_byte_identical"]
        and lock4_before == lock4_after
        and events5_before == events5_after
        and pres["rows_with_period_orig_test"] == 0
    )
    hashes = frames_hashes(frames)
    summary = {
        "refit_id": REFIT_ID,
        "status": STATUS,
        "model_label": MODEL_LABEL,
        "publication_status": INTERNAL,
        "official_ranking": False,
        "validated": False,
        "lock_hash": manifest["lock_hash"],
        "lock_label": manifest["label"],
        "definition": defn,
        "definition_status": choices["definition"]["status"],
        "shrinkage_config": cfg_name,
        "fit_window": "TRAIN+VALIDATION",
        "seed": sd,
        "n_boot": nb,
        "rows": int(len(d)),
        "matches": int(d["match_id"].nunique()),
        "date_min": str(d["match_date"].min().date()),
        "date_max": str(d["match_date"].max().date()),
        "rows_by_period_orig": {
            k: int(v) for k, v in d["period_orig"].value_counts().sort_index().items()
        },
        "cells": meta,
        "output_hashes": hashes,
        "preservation": pres,
        "note": (
            "Experimental refit. VALIDATION was used for fitting, so no out-of-sample check of this "
            "refit exists. Nothing here is validated or publishable."
        ),
    }
    out_manifest = pd.DataFrame([{"key": k, "value": str(v)} for k, v in _flat(summary).items()])
    frames["manifest"] = out_manifest
    if write:
        write_outputs(RefitResult(frames, summary), store, reports)
    return RefitResult(frames, summary)


def _flat(obj: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in obj.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flat(v, key + "."))
        else:
            out[key] = v
    return out


def write_outputs(result: RefitResult, store: Path | str, reports: Path | str) -> None:
    """Write the p5_refit_trainval_v1_* tables and the manifest/comparison reports (p5 only)."""
    from app.analytics.reporting import write_json_deterministic

    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    for key, table in TABLES.items():
        write_p5_table(result.frames[key], table, store)
    result.frames["scores"].to_csv(reports / f"{REFIT_ID}_scores.csv", index=False)
    result.frames["comparison"].to_csv(reports / f"{REFIT_ID}_comparison.csv", index=False)
    write_json_deterministic(reports / f"{REFIT_ID}_manifest.json", result.summary)
