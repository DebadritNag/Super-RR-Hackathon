"""Predeclared Phase 8 criteria, their SHA-256 and run-order enforcement.

The criteria file is written once, before any comparison result exists. ``p8_run_log`` (append-only,
see ``store.py``) holds the criteria hash as ``seq = 1`` with step ``plan``. Every analysis step
calls ``begin_step``, which verifies that the file on disk still matches that hash and appends its
own row; a changed file makes every step raise ``CriteriaError``. A needed change goes into a new
versioned file with its own plan row, never an overwrite.

The criteria carry no player identity, rank, score level or Top-10 membership as a *selection
input*. ``forbidden_hits`` checks every list stored under an ``inputs`` key and the wording about
sources; the descriptive rule text may mention ranking mechanics.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from app.phase8 import store
from app.phase8.constants import CRITERIA_FILE, CRITERIA_HASH_FILE, PHASE8_DB


class CriteriaError(RuntimeError):
    """The criteria file is missing, changed, contaminated or was not logged before a step."""


# Tokens that may never appear as a selection input.
FORBIDDEN_INPUT_TOKENS = (
    "player_id",
    "player_name",
    "player identity",
    "rank",
    "top10",
    "top-10",
    "score_level",
    "nationality",
    "capped",
    "test_outcome",
    "cricsheet",
)

CRITERIA: dict[str, Any] = {
    "version": "phase8_selection_criteria_v1",
    "status": "EXPERIMENTAL_NOT_VALIDATED",
    "declared_before_any_result": True,
    "scope": "IPL and T20I, PRE_TEST window (TRAIN + VALIDATION); TEST is never loaded; batters "
    "and bowlers are analysed separately and never compared with each other",
    "splits": {
        "config": "config/phase4_split_v1.json",
        "fold_rule": "match_id % 5, deterministic; no match is in two partitions or folds",
        "fit_population": "TRAIN only; VALIDATION is scored out of sample",
        "test": "never opened; the Phase 4 TEST aggregates are previously accessed and non-pristine",
    },
    "intensity": {
        "candidates": {
            "P0": "binary any-signal-above-TRAIN-q0.75 reference (Phase 6 idea re-implemented)",
            "P1": "leverage: expected absolute win-probability swing of the next ball (chunk 2)",
            "P2": "decision closeness 1 - 2|WP - 0.5| (chunk 2)",
            "P3": "chase difficulty from the required-rate gap, resource ratio (innings 2 only)",
            "P4": "resource scarcity: wickets lost share x innings progress (both innings)",
            "P5": "defending difficulty from the batting side's gap and wickets (innings 2 only)",
            "P6": "first principal component of the standardised passing candidates",
        },
        "scale": "empirical CDF of the raw value fitted on TRAIN, mapped to [0, 1]",
        "validity_tests": {
            "a": "runs per ball lower in decile 10 than decile 1 beyond the bootstrap half-width",
            "b": "wicket probability higher in decile 10 than decile 1",
            "c": "variance of runs per ball higher in decile 10 than decile 1",
            "d": "mean absolute win-probability change larger (mechanical for P1 and P2)",
            "e": "Spearman trend across deciles at least 0.7 for tests a and b",
            "g": "cells with fewer than 2000 deliveries are NOT_ESTIMABLE",
        },
        "pass_rule": "tests a, b, e hold pooled on TRAIN, the same signs hold on VALIDATION and "
        "the candidate passes in at least 2 of 3 phases",
        "primary_choice": "most passed tests among a-e, then widest innings coverage, then id",
        "innings1_rule": "P3 and P5 are innings-2 only; innings 1 uses the best-passing "
        "both-innings candidate (P4, then P6); otherwise innings-1 deliveries are excluded",
        "high_intensity_cut": 0.5,
        "bootstrap_draws": 500,
    },
    "eligibility": {
        "min_matches": 8,
        "min_effective_n": 60,
        "min_balls_faced": 60,
        "min_balls_bowled": 72,
        "min_high_intensity_units": 8,
        "min_matches_2025_window": 4,
        "sensitivity_multipliers": [0.5, 2.0],
        "min_players_out_of_time": 30,
        "min_players_split_half": 30,
    },
    "reliability": {
        "split_half": "match parity (odd/even by date) and time (early/late) on unshrunk "
        "precision-weighted unit means; Spearman-Brown 2r/(1+r); Fisher-z pooling",
        "icc": "one-way random-effects ICC(1) of unit means, units with at least 2 matches",
        "bootstrap": {"method": "match-cluster", "draws": 1000, "seed": 20260512},
        "phase6_data_weight_gate": 0.5,
        "phase6_gate_note": "reported unchanged and never used as a label input",
    },
    "status_thresholds": {
        "PROVISIONAL": {
            "split_half_min": 0.5,
            "split_half_lower_bound_gt": 0.0,
            "out_of_time_lower_bound_gt": 0.0,
        },
        "VALIDATED": {
            "split_half_min": 0.7,
            "split_half_lower_bound_min": 0.5,
            "out_of_time_lower_bound_gt": 0.3,
        },
        "EXPLORATORY": "an ordered list exists but PROVISIONAL is not met",
        "INSUFFICIENT_EVIDENCE": "fewer than ten eligible players or the approach cannot be "
        "computed",
        "floor_rule": "a between-player variance at the floor forces EXPLORATORY with the "
        "unshrunk ordering",
    },
    "evidence_classes": {
        "order": [
            "INSUFFICIENT",
            "INCONSISTENT",
            "STRONG_SUBSTANTIAL",
            "STRONG_LIMITED",
            "UNCLASSIFIED_LOW",
        ],
        "INSUFFICIENT": "below an eligibility floor",
        "INCONSISTENT": "share of positive units below 0.5, or dispersion above the cohort 75th "
        "percentile with a positive mean",
        "STRONG_SUBSTANTIAL": "interval lower bound above 0, matches at least 2x the floor, "
        "positive share at least 0.5",
        "STRONG_LIMITED": "above the cohort 80th percentile with an interval including 0, or "
        "matches between 1x and 2x the floor",
        "UNCLASSIFIED_LOW": "any other eligible player",
    },
    "models": {
        "seed": 20260512,
        "learners": "HistGradientBoosting regressor/classifier, LogisticRegression, Isotonic",
        "grid": {
            "max_depth": [3, 5],
            "learning_rate": [0.05, 0.1],
            "l2_regularization": [0, 1],
            "max_iter": 200,
            "min_samples_leaf": 200,
        },
        "selection": "one pass on VALIDATION: log loss for classifiers, RMSE for regressors",
        "features": "pre-delivery state only; no player identifier, no outcome column",
        "refit": "none on TRAIN + VALIDATION",
    },
    "reml": {
        "tau2_floor": "none imposed; tau2 below 1e-8 sigma2 is flagged FLOOR",
        "floor_ordering": "unshrunk precision-weighted mean; status forced to EXPLORATORY",
        "tie_rule": "absolute difference below 1e-12",
    },
    "approach_selection": {
        "inputs": [
            "split_half_sb_lower_bound",
            "out_of_time_lower_bound",
            "inclusion_probability_concentration",
            "explainability_checklist",
        ],
        "rule": "highest split-half lower bound; within 0.05 choose by out-of-time lower bound, "
        "then inclusion concentration, then explainability, then id order A, B, C",
        "no_positive_lower_bound": "list is EXPLORATORY and the highest point estimate is "
        "submitted with that stated",
    },
    "combination": {
        "inputs": ["cross_format_correlation_lower_bound", "players_with_both_formats"],
        "rule": "combine when the cross-format lower 95% bound is at least 0.3 and at least 30 "
        "players have both formats; otherwise show per-format results and flag the combination "
        "as unsupported; no fixed format weights",
    },
    "ranking": {
        "order": "descending estimate of the chosen approach; unshrunk when the floor binds",
        "bootstrap": {"draws": 1000, "seed": 20260512, "unit": "match"},
        "outputs": ["Top-10 inclusion probability", "95% rank interval", "95% estimate interval"],
    },
    "forbidden_inputs": [
        "player identity",
        "player rank",
        "score level",
        "Top-10 membership",
        "nationality",
        "capped status",
        "TEST outcomes",
        "Cricsheet",
    ],
    "sources": "official IPL and T20I data only; matches 2026.csv and *_stats2026.csv unused",
}


def criteria_bytes(criteria: dict[str, Any] | None = None) -> bytes:
    """Deterministic serialisation (sorted keys, 2-space indent, trailing newline)."""
    c = CRITERIA if criteria is None else criteria
    return (json.dumps(c, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_blob_sha(b: bytes) -> str:
    """``git hash-object`` value of the bytes."""
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324


def _input_lists(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "inputs" and isinstance(v, list):
                out.extend(str(x).lower() for x in v)
            else:
                _input_lists(v, out)
    elif isinstance(node, list):
        for v in node:
            _input_lists(v, out)


def forbidden_hits(criteria: dict[str, Any]) -> list[str]:
    """Forbidden tokens used as a selection input or as a data source in the criteria."""
    c = copy.deepcopy(criteria)
    c.pop("forbidden_inputs", None)
    inputs: list[str] = []
    _input_lists(c, inputs)
    hits = {t for t in FORBIDDEN_INPUT_TOKENS for i in inputs if t in i}
    src = str(c.get("sources", "")).lower()
    if "cricsheet" in src and "unused" not in src:
        hits.add("cricsheet")
    return sorted(hits)


def load_criteria(path: Path | str = CRITERIA_FILE) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise CriteriaError(f"criteria file missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_criteria(
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    store_path: Path | str = PHASE8_DB,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write criteria, hash file and run-log row ``seq = 1`` (step ``plan``).

    Idempotent when the existing files and log row already match the content to write. Refuses to
    overwrite different criteria once a hash file, a criteria file or a run-log row exists.
    """
    crit = CRITERIA if criteria is None else criteria
    hits = forbidden_hits(crit)
    if hits:
        raise CriteriaError(f"criteria contain forbidden inputs: {hits}")
    data = criteria_bytes(crit)
    digest = sha256_bytes(data)
    cp, hp = Path(criteria_path), Path(hash_path)
    log = store.read_run_log(store_path)
    if hp.exists() or len(log) > 0 or cp.exists():
        same_file = cp.exists() and sha256_bytes(cp.read_bytes()) == digest
        rec = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}
        same_log = len(log) > 0 and log.iloc[0]["step"] == "plan"
        same_log = same_log and log.iloc[0]["criteria_sha256"] == digest
        if same_file and rec.get("sha256") == digest and same_log:
            return {**rec, "seq": 1, "already_written": True}
        raise CriteriaError(
            "criteria already declared with different content; refusing to rewrite them"
        )
    cp.parent.mkdir(parents=True, exist_ok=True)
    hp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_bytes(data)
    rec = {
        "criteria_path": "config/" + cp.name,
        "version": crit.get("version"),
        "sha256": digest,
        "git_blob_sha": git_blob_sha(data),
        "note": "written before any comparison result; ordering is enforced by p8_run_log",
    }
    hp.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seq = store.append_run_log(
        "plan", digest, rec["git_blob_sha"], "", "criteria declared", store_path
    )
    return {**rec, "seq": seq, "already_written": False}


def verify_criteria(
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    store_path: Path | str = PHASE8_DB,
) -> dict[str, Any]:
    """Raise ``CriteriaError`` unless the declared criteria are intact and were logged first."""
    cp, hp = Path(criteria_path), Path(hash_path)
    if not cp.exists():
        raise CriteriaError(f"criteria file missing: {cp}")
    if not hp.exists():
        raise CriteriaError(f"criteria hash file missing: {hp}")
    log = store.read_run_log(store_path)
    if len(log) == 0 or int(log.iloc[0]["seq"]) != 1 or log.iloc[0]["step"] != "plan":
        raise CriteriaError("p8_run_log has no seq 1 'plan' row: criteria were not declared first")
    data = cp.read_bytes()
    digest = sha256_bytes(data)
    rec = json.loads(hp.read_text(encoding="utf-8"))
    if digest != rec.get("sha256"):
        raise CriteriaError("criteria file changed after the hash file was written")
    if digest != log.iloc[0]["criteria_sha256"]:
        raise CriteriaError("criteria file does not match the hash logged in p8_run_log")
    hits = forbidden_hits(json.loads(data.decode("utf-8")))
    if hits:
        raise CriteriaError(f"criteria contain forbidden inputs: {hits}")
    return {"sha256": digest, "git_blob_sha": rec.get("git_blob_sha"), "logged_seq": 1}


def begin_step(
    step: str,
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    store_path: Path | str = PHASE8_DB,
    inputs_hash: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Verify the criteria, then append this step's run-log row. Returns the criteria info."""
    info = verify_criteria(criteria_path, hash_path, store_path)
    seq = store.append_run_log(
        step, info["sha256"], info["git_blob_sha"] or "", inputs_hash, note, store_path
    )
    return {**info, "seq": seq, "step": step}
