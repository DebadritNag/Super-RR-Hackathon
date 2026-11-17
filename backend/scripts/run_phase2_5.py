"""Run all Phase 2.5 analyses in order with one combined preservation check.

Order: eligibility experiment, format-weight sensitivity, Cricsheet Super Over validation,
data-quality impact. Exit code 1 when any step fails or any official data changed.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import PROXY_FIELDS, write_json_deterministic  # noqa: E402
from app.core.config import get_settings  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"phase25_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--n-boot", type=int, default=None, help="bootstrap resamples (eligibility)")
    args = ap.parse_args(argv)

    common = ["--db", str(args.db), "--reports-dir", str(args.reports_dir)]
    steps = [
        (
            "run_eligibility_experiment",
            common + (["--n-boot", str(args.n_boot)] if args.n_boot else []),
        ),
        ("run_format_weight_sensitivity", common),
        ("validate_super_overs", common),
        ("assess_data_quality_impact", common),
    ]
    before = snapshot_from_settings(s, args.db)
    results: dict[str, int] = {}
    for name, step_args in steps:
        print(f"== {name}")
        try:
            results[name] = int(_load(name).main(step_args))
        except SystemExit as exc:  # argparse errors
            results[name] = int(exc.code or 1)
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    ok = not diff and all(rc == 0 for rc in results.values())
    report = {
        **PROXY_FIELDS,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unchanged": not diff,
        "diff": diff,
        "step_exit_codes": results,
        "all_steps_succeeded": all(rc == 0 for rc in results.values()),
        "cricsheet_loaded_into_database": False,
        "before": before,
        "after": after,
    }
    write_json_deterministic(args.reports_dir / "phase25_preservation.json", report)
    print(f"preservation unchanged={not diff}; steps={results}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
