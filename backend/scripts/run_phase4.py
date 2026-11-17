"""Run every Phase 4 stage end to end (EXPERIMENTAL_NOT_VALIDATED, no official ranking).

Order: split and strictly prior par, baseline calibration, first scoring pass, definition
comparison with shrinkage and eligibility choices (frozen choices file plus FREEZE log entry),
the single TEST evaluation of the frozen configuration, classification, reports and spot checks.
One integrity snapshot is taken before and after; official data must be unchanged. Seeds come from
the config files. A full run resets the run-scoped lock log so the log shows exactly one FREEZE
before one OPEN. Exit 1 on any failed step, missing deliverable, failed spot check or change.

``--compare-hashes FILE`` compares the hashes of the deterministic outputs with an earlier run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import reports as rp  # noqa: E402
from app.phase4.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
STEPS = [
    "phase4_split",
    "phase4_baseline",
    "phase4_scoring",
    "phase4_sensitivity",
    "phase4_test_eval",
    "phase4_classification",
    "phase4_reports",
]
DELIVERABLES = [
    "phase4_temporal_validation_plan.md",
    "phase4_baseline_calibration_report.md",
    "phase4_pressure_scoring_report.md",
    "phase4_definition_comparison.md",
    "phase4_eligibility_validation.md",
    "phase4_shrinkage_sensitivity.md",
    "phase4_format_weight_sensitivity.md",
    "phase4_ranking_stability.md",
    "phase4_data_quality_report.md",
    "phase4_user_summary.md",
]
MACHINE_READABLE = [
    "phase4_split_manifest.json",
    "phase4_calibration.json",
    "phase4_definition_comparison.csv",
    "phase4_eligibility_candidates.csv",
    "phase4_pressure_scores_frozen_rules.csv",
    "phase4_shrinkage_sensitivity.csv",
    "phase4_format_weight_results.csv",
    "phase4_ranking_distributions.csv",
    "phase4_frozen_choices.json",
    "phase4_test_evaluation.json",
    "phase4_spot_checks.json",
]
HASH_EXCLUDE = {
    "phase4_lock_log.json",
    "phase4_preservation.json",
    "phase4_output_hashes.json",
}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"p4run_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_deliverables(reports: Path) -> dict[str, dict]:
    out = {}
    for name in DELIVERABLES + MACHINE_READABLE:
        p = reports / name
        rec = {"exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0}
        if p.exists() and name.endswith(".json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "status" in d:
                rec["status"] = d["status"]
                rec["official_ranking"] = d.get("official_ranking")
        rec["ok"] = (
            rec["exists"]
            and rec["bytes"] > 0
            and rec.get("status", STATUS) == STATUS
            and rec.get("official_ranking") in (None, False)
        )
        out[name] = rec
    return out


def output_hashes(reports: Path) -> dict[str, str]:
    """SHA-256 of every deterministic Phase 4 output file (csv, json, md)."""
    out = {}
    for p in sorted(reports.glob("phase4_*")):
        if p.suffix in (".csv", ".json", ".md") and p.name not in HASH_EXCLUDE:
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--steps", default=",".join(STEPS), help="comma-separated subset of steps")
    ap.add_argument("--keep-lock-log", action="store_true", help="do not reset the lock log")
    ap.add_argument("--compare-hashes", type=Path, default=None)
    args = ap.parse_args(argv)
    steps = [x for x in args.steps.split(",") if x]
    unknown = [x for x in steps if x not in STEPS]
    if unknown:
        raise SystemExit(f"unknown steps: {unknown}")
    rep = args.reports
    rep.mkdir(parents=True, exist_ok=True)
    before = snapshot_from_settings(s)
    full = steps == STEPS
    reset = full and not args.keep_lock_log
    if reset:
        (rep / "phase4_lock_log.json").write_text("[]\n", encoding="utf-8")
    common = ["--store", str(args.store), "--reports", str(rep)]
    results: dict[str, int] = {}
    for name in steps:
        print(f"== {name}", flush=True)
        try:
            results[name] = int(_load(name).main(common) or 0)
        except SystemExit as exc:
            results[name] = int(exc.code or 0)
    after = snapshot_from_settings(s)
    diff = assert_unchanged(before, after)
    deliverables = check_deliverables(rep)
    log = json.loads((rep / "phase4_lock_log.json").read_text(encoding="utf-8"))
    lock = rp.lock_facts(log)
    hashes = output_hashes(rep)
    hash_diff: dict[str, list] = {}
    if args.compare_hashes and args.compare_hashes.exists():
        prev = json.loads(args.compare_hashes.read_text(encoding="utf-8"))["hashes"]
        hash_diff = {k: [prev.get(k), hashes.get(k)] for k in sorted(set(prev) | set(hashes))
                     if prev.get(k) != hashes.get(k)}  # fmt: skip
    ok = (
        not diff
        and all(rc == 0 for rc in results.values())
        and (not full or all(v["ok"] for v in deliverables.values()))
        and (not full or (lock["opened_exactly_once"] and lock["freeze_recorded_before_open"]))
        and not hash_diff
    )
    write_json_deterministic(
        rep / "phase4_preservation.json",
        {
            "status": STATUS,
            "official_ranking": False,
            "official_data_unchanged": not diff,
            "differences": diff,
            "steps": results,
            "lock_log_reset_for_this_run": reset,
            "lock": lock,
            "deliverables": deliverables,
            "determinism_comparison_differences": hash_diff,
        },
    )
    write_json_deterministic(rep / "phase4_output_hashes.json", {"hashes": hashes})
    print("steps:", results)
    print("official data unchanged:", not diff, "| lock:", lock)
    print("deliverables ok:", all(v["ok"] for v in deliverables.values()))
    if args.compare_hashes:
        print("hash differences versus earlier run:", hash_diff or "none")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
