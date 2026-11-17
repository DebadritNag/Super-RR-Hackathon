"""Run the Decision 2 eligibility threshold experiment (proxy run, read-only on official data)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.confidence_engine import load_rules, run_experiment  # noqa: E402
from app.analytics.eligibility_report import render_report  # noqa: E402
from app.analytics.integrity import (  # noqa: E402
    assert_unchanged,
    open_official_readonly,
    snapshot_from_settings,
)
from app.analytics.proxy_samples import extract_samples  # noqa: E402
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--config", type=Path, default=s.config_dir / "eligibility_rules_v1.json")
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)

    before = snapshot_from_settings(s, args.db)
    rules = load_rules(args.config)
    db = open_official_readonly(args.db)
    try:
        samples = extract_samples(db)
        prov = provenance(db, args.config, seed=rules["seed"])
    finally:
        db.close()
    n_boot = args.n_boot if args.n_boot is not None else rules["n_boot"]
    dist, exp = run_experiment(samples, rules, n_boot)
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    preservation = {"unchanged": not diff, "diff": diff, "snapshot": before}
    for d in (dist, exp):
        d["provenance"] = prov
        d["preservation"] = preservation
    out = args.reports_dir
    write_json_deterministic(out / "eligibility_distribution.json", dist)
    write_json_deterministic(out / "eligibility_threshold_experiment.json", exp)
    write_text(out / "eligibility_threshold_report.md", render_report(dist, exp))
    print(f"wrote eligibility outputs to {out.as_posix()}; preservation unchanged={not diff}")
    for fmt, lines in exp["narrative"].items():
        for line in lines:
            print(line)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
