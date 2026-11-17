"""Run the Decision 1 IPL/T20I weight sensitivity (proxy run, read-only on official data).

`--register` additionally inserts one model_versions row 'format-weights-v1' after the analysis.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.confidence_engine import load_rules  # noqa: E402
from app.analytics.format_config import (  # noqa: E402
    load_config,
    register_config_in_model_versions,
    settings_consistency,
)
from app.analytics.format_weight_report import render_report  # noqa: E402
from app.analytics.integrity import (  # noqa: E402
    assert_unchanged,
    open_official_readonly,
    snapshot_from_settings,
)
from app.analytics.normalization_engine import run_sensitivity  # noqa: E402
from app.analytics.proxy_samples import extract_samples  # noqa: E402
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--config", type=Path, default=s.format_weights_config)
    ap.add_argument("--register", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    before = snapshot_from_settings(s, args.db)
    db = open_official_readonly(args.db)
    try:
        samples = extract_samples(db)
        rules = load_rules(args.config.parent / "eligibility_rules_v1.json")
        res = run_sensitivity(samples, cfg, int(rules["list_size"]), names=samples.names)
        prov = provenance(db, args.config, seed=None)
    finally:
        db.close()
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    res["warnings"] = settings_consistency(cfg, s)
    res["provenance"] = prov
    res["preservation"] = {"unchanged": not diff, "diff": diff, "snapshot": before}

    registered = None
    if args.register and not diff:
        inserted = register_config_in_model_versions(args.db, cfg)
        post = snapshot_from_settings(s, args.db)
        # the DB file hash legitimately changes after the insert; official tables must not
        post_diff = {k: v for k, v in assert_unchanged(before, post).items() if "db_file" not in k}
        registered = {
            "model_version_name": "format-weights-v1",
            "inserted": inserted,
            "official_tables_unchanged": not post_diff,
        }
        diff = {**diff, **post_diff}
    res["model_version_registration"] = registered

    out = args.reports_dir
    write_json_deterministic(out / "format_weight_sensitivity.json", res)
    write_text(out / "format_weight_sensitivity_report.md", render_report(res))
    print(f"wrote format weight outputs to {out.as_posix()}; preservation unchanged={not diff}")
    if registered:
        print(f"registration: {registered}")
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
