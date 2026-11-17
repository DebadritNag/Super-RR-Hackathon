"""Run every Phase 3 preparation stage end to end (EXPLORATORY, no scoring, no ranking).

Order: pre-delivery state, spot check, pressure distributions, baseline, pressure eligibility,
pressure format-weight sensitivity, data-quality restrictions + feature dictionary. Then the
framework specification is copied to data/reports/ and all seven deliverables are checked.
One integrity snapshot is taken before and after; official data must be unchanged. Deterministic:
seeds come from the config files. Exit 1 on any failed step, missing deliverable or change.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
SPEC = ROOT / "docs" / "pressure_framework_v1.md"
DELIVERABLES = [
    "pressure_framework_v1.md",
    "pressure_feature_dictionary.json",
    "pressure_distribution_report.md",
    "pressure_threshold_experiment.json",
    "pressure_eligibility_report.md",
    "baseline_methodology_v1.md",
    "phase3_data_quality_application_report.md",
]
EXTRA = ["pressure_format_weight_sensitivity.json", "pressure_format_weight_sensitivity.md",
         "phase3_data_quality_application.json"]  # fmt: skip
SEEDS = {
    "pressure_rules": "config/pressure_rules_v1.json",
    "pressure_eligibility": "config/pressure_eligibility_rules_v1.json",
}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"phase3_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_deliverables(reports: Path) -> dict[str, dict]:
    out = {}
    for name in DELIVERABLES + EXTRA:
        p = reports / name
        rec = {"exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0}
        if p.exists() and name.endswith(".json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            rec["status"] = d.get("status")
            rec["official_ranking"] = d.get("official_ranking")
        rec["ok"] = (
            rec["exists"]
            and rec["bytes"] > 0
            and (
                not name.endswith(".json")
                or (
                    rec["status"] == "EXPLORATORY_NOT_VALIDATED"
                    and rec["official_ranking"] is False
                )
            )
        )
        out[name] = rec
    return out


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--n-boot", type=int, default=None, help="bootstrap resamples override")
    args = ap.parse_args(argv)
    base = [
        "--db",
        str(args.db),
        "--store",
        str(args.store),
        "--reports-dir",
        str(args.reports_dir),
    ]
    boot = ["--n-boot", str(args.n_boot)] if args.n_boot else []
    steps = [
        ("build_pre_delivery_state", base),
        ("spot_check_pre_delivery_state", ["--store", str(args.store)]),
        ("run_pressure_distributions", base),
        ("run_baseline_exploration", base + boot),
        ("run_pressure_eligibility", base + boot),
        ("run_pressure_format_sensitivity", base),
        ("apply_dq_restrictions", base),
    ]
    before = snapshot_from_settings(s, args.db)
    results: dict[str, int] = {}
    for name, step_args in steps:
        print(f"== {name}", flush=True)
        try:
            results[name] = int(_load(name).main(step_args) or 0)
        except SystemExit as exc:
            results[name] = int(exc.code or 0)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SPEC, args.reports_dir / "pressure_framework_v1.md")
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    deliverables = check_deliverables(args.reports_dir)
    ok = (
        not diff
        and all(rc == 0 for rc in results.values())
        and all(d["ok"] for d in deliverables.values())
    )
    report = {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "official_ranking": False,
        "not_for_publication": True,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "official_unchanged": not diff,
        "diff": diff,
        "step_exit_codes": results,
        "deliverables": deliverables,
        "seed_configs": SEEDS,
        "approval_gate": "Stop: full pressure scoring, official rankings and ML training need "
        "explicit user approval.",  # fmt: skip
        "before": before,
        "after": after,
    }
    write_json_deterministic(args.reports_dir / "phase3_preservation.json", report)
    print(
        f"official_unchanged={not diff}; steps={results}; deliverables_ok="
        f"{all(d['ok'] for d in deliverables.values())}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
