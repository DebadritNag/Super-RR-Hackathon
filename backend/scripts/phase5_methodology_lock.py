"""Phase 5 Chunk 5: pre-lock checklist and (only with --confirm-lock) the methodology lock manifest.

This is the ONLY script that creates ``phase5_methodology_lock.json``. Without ``--confirm-lock`` it
writes the checklist and stops. The lock freezes the choices used by the experimental
TRAIN+VALIDATION refit. It does not validate the methodology: the checklist records the
publication gates that still fail and the decisions that still need the user.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.phase5 import lock_manifest as lm  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402
from app.phase5.store import write_p5_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--lock-path", type=Path, default=None)
    ap.add_argument(
        "--confirm-lock",
        action="store_true",
        help="write the lock manifest (without it only the checklist is written)",
    )
    args = ap.parse_args(argv)
    lock_path = args.lock_path or (args.reports / "phase5_methodology_lock.json")
    pres = Preservation(args.reports)
    check = lm.pre_lock_checklist(args.reports, args.store)
    write_json_deterministic(args.reports / "phase5_pre_lock_checklist.json", check)
    for it in check["items"]:
        print(f"[{it['status']:>21}] {it['kind']:<30} {it['id']}: {it['detail']}")
    print("required items all pass:", check["required_all_pass"])
    print("publication ready:", check["publication_ready"], "(methodology NOT validated)")
    if not args.confirm_lock:
        print("no lock written (pass --confirm-lock to write the EXPERIMENTAL_LOCK manifest)")
        return 0 if pres.verify()["all_preserved"] else 1
    if not check["required_all_pass"]:
        print("refusing to lock: required checklist items fail", file=sys.stderr)
        return 1
    manifest = lm.build_manifest(lm.build_lock_content(store=args.store), check)
    lm.write_lock(lock_path, manifest)
    rows = [{"key": "lock_hash", "value": manifest["lock_hash"]},
            {"key": "label", "value": manifest["label"]},
            {"key": "validated", "value": "False"},
            {"key": "code_sha256", "value": manifest["content"]["code_sha256"]}]  # fmt: skip
    rows += [{"key": f"file:{k}", "value": v} for k, v in manifest["content"]["files"].items()]
    write_p5_table(pd.DataFrame(rows), "p5_methodology_lock", args.store)
    print("lock written:", lock_path, manifest["lock_hash"])
    return 0 if pres.verify()["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
