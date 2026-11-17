"""Phase 5 orchestrator: runs every Phase 5 script in a fixed order and checks preservation.

Order: classification, date verification, gates, investigation, sensitivity, ranking stability,
context engine, context coverage, dynamic demo, gates (again, to add the dynamic section), context
spot check, reports, pre-lock checklist, [lock], [refit], reports.

The methodology lock is NOT created implicitly. Pass ``--create-lock`` to run
``phase5_methodology_lock.py --confirm-lock``; without it the checklist is written, and the refit
runs only if a valid lock manifest already exists (otherwise it is reported as SKIPPED_NO_LOCK).
It never runs or imports Phase 4's runner and never writes the Phase 4 lock log. TEST is not opened.

``--compare-hashes`` compares the SHA-256 of every ``phase5_*`` output with the previous run's
``phase5_output_hashes.json`` and exits 1 on any difference (a second run must show none).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.lockguard import PHASE5_LOCK_LOG, assert_phase5_lock_not_opened  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402
from app.phase5.store import table_hashes, write_p5_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

SCRIPTS = ROOT / "scripts"
HASHES_FILE = "phase5_output_hashes.json"
RUN_FILE = "phase5_orchestrator_run.json"
VOLATILE = {HASHES_FILE, RUN_FILE}

# (step name, script, extra args)
STEPS: list[tuple[str, str, list[str]]] = [
    ("phase5_classification", "phase5_classification.py", []),
    ("phase5_date_verification", "phase5_date_verification.py", []),
    ("phase5_gates", "phase5_gates.py", []),
    ("phase5_investigation", "phase5_investigation.py", []),
    ("phase5_sensitivity", "phase5_sensitivity.py", []),
    ("phase5_ranking_stability", "phase5_ranking_stability.py", []),
    ("phase5_context_engine", "phase5_context_engine.py", []),
    ("phase5_context_coverage", "phase5_context_coverage.py", []),
    ("phase5_dynamic_demo", "phase5_dynamic_demo.py", []),
    ("phase5_gates_dynamic_section", "phase5_gates.py", []),
    ("phase5_context_spotcheck", "phase5_context_spotcheck.py", []),
    ("phase5_reports_pre", "phase5_reports.py", []),
    ("phase5_pre_lock_checklist", "phase5_methodology_lock.py", []),
]
LOCK_STEP = ("phase5_methodology_lock", "phase5_methodology_lock.py", ["--confirm-lock"])
REFIT_STEP = ("phase5_refit", "phase5_refit.py", [])
REPORT_STEP = ("phase5_reports_final", "phase5_reports.py", [])

DELIVERABLES = [
    "phase5_investigation_report.md",
    "phase5_t20i_date_verification.md",
    "phase5_classification_migration.md",
    "phase5_sensitivity_report.md",
    "phase5_ranking_stability.md",
    "phase5_publication_gates.md",
    "phase5_dynamic_ranking_architecture.md",
    "phase5_unresolved_issues.md",
    "phase5_methodology_lock_and_refit.md",
    "phase5_user_summary.md",
    "phase5_pre_lock_checklist.json",
]


def output_hashes(reports: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(reports.glob("phase5_*"))
        if p.is_file() and p.name not in VOLATILE
    }


def run_step(name: str, script: str, extra: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *extra],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    print(
        f"[{'ok' if proc.returncode == 0 else 'FAIL'}] {name} (exit {proc.returncode}) {tail[0][:120]}"
    )
    if proc.returncode != 0:
        print((proc.stderr or "")[-1500:], file=sys.stderr)
    return {"step": name, "script": script, "args": extra, "exit_code": proc.returncode}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument(
        "--create-lock",
        action="store_true",
        help="explicitly create the EXPERIMENTAL_LOCK manifest (never done implicitly)",
    )
    ap.add_argument("--compare-hashes", action="store_true", help="compare with the previous run")
    args = ap.parse_args(argv)
    reports = args.reports
    pres = Preservation(reports)
    p4_tables_before = table_hashes(args.store, "p4_")
    previous = (
        json.loads((reports / HASHES_FILE).read_text("utf-8"))["hashes"]
        if (reports / HASHES_FILE).is_file()
        else None
    )
    steps = list(STEPS)
    if args.create_lock:
        steps.append(LOCK_STEP)
    lock_exists = (reports / "phase5_methodology_lock.json").is_file()
    results = []
    ok = True
    for name, script, extra in steps:
        r = run_step(name, script, extra)
        results.append(r)
        if r["exit_code"] != 0:
            ok = False
            break
        if name == LOCK_STEP[0]:
            lock_exists = (reports / "phase5_methodology_lock.json").is_file()
    if ok:
        if lock_exists:
            r = run_step(*REFIT_STEP)
            ok = r["exit_code"] == 0
        else:
            r = {"step": REFIT_STEP[0], "exit_code": None, "result": "SKIPPED_NO_LOCK"}
            print(
                "[skip] phase5_refit: no lock manifest (use --create-lock to create it explicitly)"
            )
        results.append(r)
    if ok:
        r = run_step(*REPORT_STEP)
        results.append(r)
        ok = r["exit_code"] == 0
    missing = [
        d for d in DELIVERABLES if not (reports / d).is_file() or (reports / d).stat().st_size == 0
    ]
    full = pres.verify()
    p4_tables_after = table_hashes(args.store, "p4_")
    p5_events = assert_phase5_lock_not_opened(PHASE5_LOCK_LOG)
    hashes = output_hashes(reports)
    diffs = (
        sorted(k for k in set(hashes) | set(previous) if hashes.get(k) != previous.get(k))
        if previous is not None
        else None
    )
    preservation = {
        **full,
        "phase4_tables_hashed": len(p4_tables_before),
        "phase4_tables_byte_identical": p4_tables_before == p4_tables_after,
        "phase5_lock_log_events": p5_events,
        "runs_phase4_runner": False,
        "writes_phase4_lock_log": False,
    }
    summary = {
        "status": STATUS,
        "create_lock_flag": bool(args.create_lock),
        "lock_manifest_present": lock_exists,
        "steps": results,
        "missing_deliverables": missing,
        "preservation": preservation,
    }
    write_json_deterministic(reports / RUN_FILE, summary)
    write_json_deterministic(
        reports / HASHES_FILE, {"status": STATUS, "files": len(hashes), "hashes": hashes}
    )
    write_p5_table(
        pd.DataFrame([{"file": k, "sha256": v} for k, v in hashes.items()]),
        "p5_output_hashes",
        args.store,
    )
    ok = (
        ok
        and not missing
        and preservation["all_preserved"]
        and preservation["phase4_tables_byte_identical"]
    )
    if args.compare_hashes:
        if diffs is None:
            print("compare-hashes: no previous run to compare with")
        else:
            print(f"compare-hashes: {len(diffs)} differing files {diffs[:10]}")
            ok = ok and not diffs
    print("missing deliverables:", missing, "| preservation:", preservation["all_preserved"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
