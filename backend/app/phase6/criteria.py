"""Pre-declared selection criteria, their SHA-256, and run-order enforcement.

The criteria file is written once by ``scripts/phase6_investigation_plan.py`` before any estimator
output exists. ``p6_run_log`` (append-only, see ``store.py``) records the criteria hash as row
``seq = 1`` with step ``plan``. Every later step calls ``begin_step`` which verifies that the file
on disk still matches that hash and that the criteria contain no forbidden wording, then appends
its own row. A rewritten criteria file makes every step fail.

The criteria contain no player identity, rank, score level or Top-10 membership as an input.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from app.phase6 import store
from app.phase6.constants import (
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    INVESTIGATION_CONFIG,
)
from app.services.pressure_service import EXPLORATORY_DB

FORBIDDEN_WORDS = ("player", "rank", "top10", "promot")


class CriteriaError(RuntimeError):
    """The criteria file is missing, changed, contaminated or was not logged before a step."""


CRITERIA: dict[str, Any] = {
    "version": "phase6_selection_criteria_v1",
    "status": "EXPERIMENTAL_NOT_VALIDATED",
    "declared_before_any_result": True,
    "unit": "definition x (format, role) cell; the selection rule uses the primary stream of "
    "each role only (batter runs, bowler charged runs); other streams are descriptive",
    "window": "PRE_TEST (TRAIN + VALIDATION); repeated on TRAIN only as a stability check",
    "metrics": {
        "R": "odd/even split-half Spearman-Brown reliability of definition d in cell c, "
        "primary stream, PRE_TEST, at least 6 pressure balls per half, at least 10 individuals; "
        "match-cluster bootstrap with 1000 draws; lo is the 2.5th percentile of the draws",
        "M1": "Fisher-z pooled R over the four cells (weights n-3, correlation clipped at 0.99); "
        "SE1 is the SD over bootstrap draws of the pooled value",
        "M2": "split-covariance signal share: cov(half1, half2) / var(individual means); "
        "descriptive only",
        "M3": "share of individuals whose match-cluster bootstrap 95% interval of the raw mean "
        "residual excludes the pooled cell mean; descriptive only",
        "M4": "median over individuals of pressure-ball counts, pooled over the four cells",
        "M5": "median over 1000 match-cluster resamples of the Spearman correlation between the "
        "resample ordering and the full-window ordering, per cell, then medianed over cells",
        "M6": "control reliability of a non-pressure ball sample matched on balls per "
        "individual; descriptive only, never a selection input",
    },
    "metrics_in_rule": ["M1", "M4", "M5"],
    "rule": "PASS(d) iff R(d,c) is estimable in all four cells and lo(d,c) > 0 in at least three "
    "cells. TOP(d) iff PASS(d) and M1(d) >= max M1 over passing definitions minus SE1 of the "
    "best. Order inside TOP: M4 descending, then M5 descending, then id ascending. The output "
    "is a pass list and a top group, not a selection.",
    "stability_outcomes": "if the TOP set on TRAIN only differs from the PRE_TEST TOP set the "
    "report states DEFINITION_ORDER_NOT_STABLE and names no top group",
    "confound_control": "M1, M2 and M5 are recomputed on the intersection of individuals "
    "eligible under all nine definitions per cell; the rule uses the intersection version when "
    "it has at least 30 individuals in every cell, otherwise COMPARISON_CONFOUNDED and only the "
    "pass list is reported",
    "multiplicity": "nine candidates examined, no correction applied; any top group is "
    "PROVISIONAL and does not replace any|q0.75",
    "variance_floor": {
        "identification_rule": {
            "identified_positive": "E7 split-covariance bootstrap 95% lower bound > 0 and E1c "
            "match-cluster moment estimate positive in at least 90% of E6 bootstrap draws",
            "not_identified": "E7 interval contains 0 and the E6 share of positive draws is "
            "below 90%",
            "otherwise": "weakly_identified",
        },
        "flags": {
            "positive_draw_share_min": 0.9,
            "power_ratio": 0.01,
            "power_min": 0.8,
            "kish_ratio_to_balls_per_match_lo": 0.75,
            "kish_ratio_to_balls_per_match_hi": 1.25,
            "tercile_variance_ratio_hi": 1.5,
            "tercile_variance_ratio_lo": 0.67,
            "icc_min": 0.05,
            "pearson_dispersion_min": 1.5,
            "min_supported_of_hb_i_to_iv": 2,
            "hb_overall_requires_hb_ii": True,
        },
        "flag_definitions": {
            "H-A_null": "E7 bootstrap 95% interval contains 0 and the E6 share of draws with a "
            "positive match-cluster estimate is below positive_draw_share_min",
            "H-A_power": "detectability simulation share of positive estimates at tau2/sigma2 = "
            "power_ratio is at least power_min",
            "H-B(i)": "mean(sigma2/n_eff_kish) / mean(sigma2/n_i), divided by the mean balls "
            "per match, lies in [kish_ratio_to_balls_per_match_lo, ..._hi]",
            "H-B(ii)": "the sign of the between variance differs between the Kish basis (E1) "
            "and the match-cluster basis (E1c)",
            "H-B(iii)": "residual-variance ratio of the lowest versus highest tercile of "
            "ball counts is above tercile_variance_ratio_hi or below tercile_variance_ratio_lo",
            "H-B(iv)": "ICC of ball residuals within match or within individual-match cluster "
            "above icc_min, or Pearson dispersion of the moment fit above "
            "pearson_dispersion_min",
            "H-B_overall": "at least min_supported_of_hb_i_to_iv of H-B(i) to H-B(iv) "
            "supported, including H-B(ii)",
            "H-C": "E7 or E6 lower bound > 0 and the required-sample projection for R = 0.5 is "
            "finite and larger than the observed median ball count",
        },
        "verdict_table_in_order": [
            ["H-A_null and H-A_power and not H-B_overall", "H-A_SUPPORTED"],
            ["H-A_null and not H-A_power", "UNIDENTIFIED"],
            ["H-B_overall and H-C", "MIXED"],
            ["H-B_overall only", "H-B_SUPPORTED"],
            ["H-C only", "H-C_SUPPORTED"],
            ["any other combination", "UNIDENTIFIED"],
        ],
        "sparse_context": "fewer than 8 TRAIN individuals or fewer than 10 per half is "
        "NOT_ESTIMABLE with a reason",
        "sensitivity_only_estimators": ["E4", "E5"],
    },
    "split_half": {
        "modes": ["odd_even", "early_late", "random"],
        "min_balls_per_half": 6,
        "min_individuals_estimable": 10,
        "random_splits": 200,
        "bootstrap_draws": 1000,
        "spearman_brown": "2r/(1+r), reported unclipped; a negative r gives a negative value",
        "aggregation": "Fisher z with weights n-3, correlation clipped at 0.99",
        "label": "IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION",
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
    "provisional_definition_unchanged": "any|q0.75 stays the provisional definition regardless "
    "of outcome; a change needs a user decision",
}


def criteria_bytes(criteria: dict[str, Any] | None = None) -> bytes:
    """Deterministic serialisation (sorted keys, 2-space indent, trailing newline)."""
    c = CRITERIA if criteria is None else criteria
    return (json.dumps(c, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_blob_sha(b: bytes) -> str:
    """``git hash-object`` value of the bytes (the workspace itself is not a git repository)."""
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324


def forbidden_hits(criteria: dict[str, Any]) -> list[str]:
    """Forbidden words in the criteria text, ignoring the ``forbidden_inputs`` list itself."""
    c = copy.deepcopy(criteria)
    c.pop("forbidden_inputs", None)
    text = json.dumps(c, sort_keys=True).lower().replace("-", "")
    return [w for w in FORBIDDEN_WORDS if w in text]


def load_criteria(path: Path | str = CRITERIA_FILE) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise CriteriaError(f"criteria file missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_criteria(
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    config_path: Path | str = INVESTIGATION_CONFIG,
    store_path: Path | str = EXPLORATORY_DB,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write criteria, hash file and run-log row ``seq = 1`` (step ``plan``).

    Idempotent when the existing files and log row already match the content to write. Refuses
    to overwrite different criteria once a hash file or a run-log row exists.
    """
    crit = CRITERIA if criteria is None else criteria
    hits = forbidden_hits(crit)
    if hits:
        raise CriteriaError(f"criteria contain forbidden wording: {hits}")
    data = criteria_bytes(crit)
    digest = sha256_bytes(data)
    cfg_sha = sha256_bytes(Path(config_path).read_bytes())
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
        "sha256": digest,
        "git_blob_sha": git_blob_sha(data),
        "investigation_config_sha256": cfg_sha,
        "note": "written before any estimator output; ordering is enforced by p6_run_log",
    }
    hp.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seq = store.append_run_log("plan", digest, cfg_sha, rec["git_blob_sha"], store_path)
    return {**rec, "seq": seq, "already_written": False}


def verify_criteria(
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    store_path: Path | str = EXPLORATORY_DB,
) -> dict[str, Any]:
    """Raise ``CriteriaError`` unless the declared criteria are intact and were logged first."""
    cp, hp = Path(criteria_path), Path(hash_path)
    if not cp.exists():
        raise CriteriaError(f"criteria file missing: {cp}")
    if not hp.exists():
        raise CriteriaError(f"criteria hash file missing: {hp}")
    log = store.read_run_log(store_path)
    if len(log) == 0 or int(log.iloc[0]["seq"]) != 1 or log.iloc[0]["step"] != "plan":
        raise CriteriaError("p6_run_log has no seq 1 'plan' row: criteria were not declared first")
    data = cp.read_bytes()
    digest = sha256_bytes(data)
    rec = json.loads(hp.read_text(encoding="utf-8"))
    if digest != rec.get("sha256"):
        raise CriteriaError("criteria file changed after the hash file was written")
    if digest != log.iloc[0]["criteria_sha256"]:
        raise CriteriaError("criteria file does not match the hash logged in p6_run_log")
    hits = forbidden_hits(json.loads(data.decode("utf-8")))
    if hits:
        raise CriteriaError(f"criteria contain forbidden wording: {hits}")
    return {"sha256": digest, "git_blob_sha": rec.get("git_blob_sha"), "logged_seq": 1}


def begin_step(
    step: str,
    criteria_path: Path | str = CRITERIA_FILE,
    hash_path: Path | str = CRITERIA_HASH_FILE,
    config_path: Path | str = INVESTIGATION_CONFIG,
    store_path: Path | str = EXPLORATORY_DB,
) -> dict[str, Any]:
    """Verify the criteria, then append this step's run-log row. Returns the criteria info."""
    info = verify_criteria(criteria_path, hash_path, store_path)
    cfg_sha = sha256_bytes(Path(config_path).read_bytes())
    seq = store.append_run_log(step, info["sha256"], cfg_sha, info["git_blob_sha"], store_path)
    return {**info, "seq": seq, "step": step}
