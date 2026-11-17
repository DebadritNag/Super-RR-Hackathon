"""Phase 6 orchestrator: runs every Phase 6 script in a fixed order and checks preservation.

Order: cleanup checks, investigation plan (criteria declared first), variance floor, split-half,
definition reliability, context reliability, eligibility reliability, data-weight options, recent
form, season robustness, retention stub (empty table and design note), reports.
It never creates a TEST lock, never opens TEST, never runs the Phase 4 or Phase 5 runner and never
imports retention data. Every script is seeded (seed 20260512), so a second run reproduces the
outputs. ``--compare-hashes`` compares the SHA-256 of every ``phase6_*`` output with the previous
run's ``phase6_output_hashes.json`` and exits 1 on any difference (the run-log sequence number
printed in report headers is masked: ``p6_run_log`` is append-only and grows with every run).
Preservation: official data, source CSVs, every ``phase4_*``/``phase5_*`` report file and the other
files hashed before Phase 6 (``phase6_prerun_hashes.json``) must be byte-identical, ``p4_*`` and
``p5_*`` tables must be unchanged, the Phase 4 lock log must be unchanged and the Phase 5 lock log
must hold 0 events. Exit code 1 on any change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6.constants import STATUS  # noqa: E402
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase6.outputs import Preservation  # noqa: E402
from app.phase6.reports import DELIVERABLES  # noqa: E402
from app.phase6.store import table_hashes, write_p6_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

SCRIPTS = ROOT / "scripts"
HASHES_FILE = "phase6_output_hashes.json"
RUN_FILE = "phase6_orchestrator_run.json"
VOLATILE = {HASHES_FILE, RUN_FILE, "phase6_cleanup_timings.json"}  # timings are machine dependent
PRERUN = Path("d:/Data/.agents/tasks/phase6_prerun_hashes.json")
SEQ = re.compile(rb"(run-log seq )\d+")
# (step name, script, extra args)
STEPS: list[tuple[str, str, list[str]]] = [
    ("phase6_cleanup_checks", "phase6_cleanup_checks.py", []),
    ("phase6_investigation_plan", "phase6_investigation_plan.py", []),
    ("phase6_variance_floor", "phase6_variance_floor.py", []),
    ("phase6_split_half", "phase6_split_half.py", []),
    ("phase6_definition_reliability", "phase6_definition_compare.py", []),
    ("phase6_context_reliability", "phase6_context_reliability.py", []),
    ("phase6_eligibility_reliability", "phase6_eligibility_reliability.py", []),
    ("phase6_data_weight_options", "phase6_data_weight_options.py", []),
    ("phase6_recent_form", "phase6_recent_form.py", []),
    ("phase6_season_robustness", "phase6_season_robustness.py", []),
    ("phase6_retention_stub", "phase6_retention_stub.py", []),
    ("phase6_reports", "phase6_reports.py", []),
]


def _hash(p: Path) -> str:
    b = p.read_bytes()
    if p.suffix == ".md":
        b = SEQ.sub(rb"\1N", b)
    return hashlib.sha256(b).hexdigest()


def output_hashes(reports: Path) -> dict[str, str]:
    return {
        p.name: _hash(p)
        for p in sorted(reports.glob("phase6_*"))
        if p.is_file() and p.name not in VOLATILE
    }


def prerun_check() -> dict:
    """Files hashed before Phase 6 (exploratory.duckdb excluded: it holds the p6_ tables)."""
    files = json.loads(PRERUN.read_text(encoding="utf-8-sig"))["files"]
    changed, missing = [], []
    for path, rec in files.items():
        p = Path(path)
        if p.name == "exploratory.duckdb":
            continue
        if not p.is_file():
            missing.append(path)
        elif hashlib.sha256(p.read_bytes()).hexdigest() != rec["sha256"]:
            changed.append(path)
    return {"files_checked": len(files) - 1, "changed": changed, "missing": missing,
            "byte_identical": not changed and not missing}  # fmt: skip


def retention_stub_rows(store: Path) -> int | None:
    con = duckdb.connect(str(store), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name = 'p6_retention_status_stub'"
        ).fetchone()[0]
        return (
            int(con.execute("SELECT count(*) FROM p6_retention_status_stub").fetchone()[0])
            if has
            else None
        )
    finally:
        con.close()


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
    ap.add_argument("--compare-hashes", action="store_true", help="compare with the previous run")
    args = ap.parse_args(argv)
    reports = args.reports
    pres = Preservation(reports)
    lock_before = lock_state()
    p4_before, p5_before = table_hashes(args.store, "p4_"), table_hashes(args.store, "p5_")
    previous = (
        json.loads((reports / HASHES_FILE).read_text("utf-8"))["hashes"]
        if (reports / HASHES_FILE).is_file()
        else None
    )
    results, ok = [], True
    for name, script, extra in STEPS:
        r = run_step(name, script, extra)
        results.append(r)
        if r["exit_code"] != 0:
            ok = False
            break
    missing = [d for d in DELIVERABLES
               if not (reports / d).is_file() or (reports / d).stat().st_size == 0]  # fmt: skip
    full = pres.verify()
    lock_ok = True
    try:
        lock_after = assert_lock_state_unchanged(lock_before)
    except Exception as exc:  # noqa: BLE001
        lock_ok, lock_after = False, {"error": str(exc)}
    prerun = prerun_check()
    stub_rows = retention_stub_rows(args.store)
    hashes = output_hashes(reports)
    diffs = (
        sorted(k for k in set(hashes) | set(previous) if hashes.get(k) != previous.get(k))
        if previous is not None
        else None
    )
    preservation = {
        **full,
        "p4_tables_byte_identical": table_hashes(args.store, "p4_") == p4_before,
        "p5_tables_byte_identical": table_hashes(args.store, "p5_") == p5_before,
        "p4_p5_tables_hashed": len(p4_before) + len(p5_before),
        "prerun_files": prerun,
        "lock_state_unchanged": lock_ok,
        "phase5_lock_log_events": lock_after.get("phase5_events"),
        "retention_stub_rows": stub_rows,
        "creates_lock": False,
        "opens_test": False,
        "imports_retention_data": False,
    }
    summary = {"status": STATUS, "steps": results, "missing_deliverables": missing,
               "preservation": preservation}  # fmt: skip
    write_json_deterministic(reports / RUN_FILE, summary)
    write_json_deterministic(reports / HASHES_FILE, {"status": STATUS, "files": len(hashes),
                                                     "hashes": hashes})  # fmt: skip
    write_p6_table(pd.DataFrame([{"file": k, "sha256": v} for k, v in hashes.items()]),
                   "p6_output_hashes", args.store)  # fmt: skip
    ok = (
        ok
        and not missing
        and preservation["all_preserved"]
        and preservation["p4_tables_byte_identical"]
        and preservation["p5_tables_byte_identical"]
        and prerun["byte_identical"]
        and lock_ok
        and stub_rows == 0
    )
    if args.compare_hashes:
        if diffs is None:
            print("compare-hashes: no previous run to compare with")
        else:
            print(f"compare-hashes: {len(diffs)} differing files {diffs[:10]}")
            ok = ok and not diffs
    print("missing deliverables:", missing, "| preservation:", preservation["all_preserved"],
          "| prerun byte-identical:", prerun["byte_identical"])  # fmt: skip
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
