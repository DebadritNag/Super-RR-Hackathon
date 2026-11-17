"""Stage 5: pressure-specific eligibility threshold experiment (EXPLORATORY, no ranking).

Rebuilds pressure samples (actual minus expected under the Stage 4 baseline) for a pre-declared
grid of pressure definitions, runs the Phase 2.5 threshold harness on them, compares with the
Phase 2.5 all-situation thresholds and writes data/reports/pressure_threshold_experiment.json and
pressure_eligibility_report.md. No official Top 10 is produced. Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics import baseline_engine as be  # noqa: E402
from app.analytics import pressure_distributions as pdist  # noqa: E402
from app.analytics import pressure_eligibility as pe  # noqa: E402
from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.pressure_eligibility_report import (  # noqa: E402
    provisional_recommendation,
    render_report,
)
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402
from scripts.run_pressure_distributions import prepare  # noqa: E402

CONFIG = ROOT / "config" / "pressure_eligibility_rules_v1.json"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    cfg = pe.load_rules(args.config)
    n_boot = args.n_boot or int(cfg["n_boot"])
    before = snapshot_from_settings(s, args.db)
    rules, df, meta = prepare(args.store)
    specs, flags = pf.build_candidates(df, rules)
    params = {
        "min_cell_innings": int(cfg["baseline"]["min_cell_innings"]),
        "tau2_floor": float(cfg["baseline"]["tau2_floor"]),
    }
    bat, bowl = be.batter_frame(df), be.bowler_frame(df)
    bi, wi = bat["_src_index"].to_numpy(), bowl["_src_index"].to_numpy()
    b0 = pe.residual_sets(bat, bowl, None, None, params)
    p25 = pe.phase25_thresholds(
        __import__("json").loads(
            (args.reports_dir / "eligibility_threshold_experiment.json").read_text(encoding="utf-8")
        )
    )
    results, public = [], []
    for d in pe.definitions(cfg):
        fb = pe.definition_flag(flags, cfg, d, "batter")[bi]
        fw = pe.definition_flag(flags, cfg, d, "bowler")[wi]
        mm = pe.context_matches(df, d["ctx"])
        r = pe.run_definition(d, bat, bowl, fb, fw, cfg, mm, params, n_boot, b0)
        r["comparison_with_phase25"] = pe.compare_with_phase25(r, r["_tables"], p25)
        r["context_matches"] = mm
        results.append(r)
        print(f"{d['id']}: done", flush=True)
        public.append({k: v for k, v in r.items() if not k.startswith("_")})
    selection = pe.select_definition(results, cfg)
    effects = pdist.candidate_effects(df, specs, flags)
    out = {
        **pe.STATUS,
        "score_label": "PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE",
        "config_file": args.config.name,
        "config": cfg,
        "n_boot": n_boot,
        "provenance": provenance(None, args.config, seed=int(cfg["seed"])),
        "stage3_candidates_examined": len(effects),
        "stage3_candidate_effects": effects,
        "phase25_all_situation_thresholds": p25,
        "definitions": public,
        "selection": selection,
    }
    out["provisional_recommendation"] = provisional_recommendation(out)
    # keep full rule-level detail only for the provisional definition (file size)
    for d in out["definitions"]:
        if d["definition"]["id"] != selection["selected_id"]:
            for fmt_ in d["experiment"]["formats"].values():
                for cell in fmt_.values():
                    cell.pop("rules", None)
                    cell.pop("candidates", None)
            d["detail_pruned"] = True
        else:
            d["detail_pruned"] = False
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    out["preservation"] = {"official_unchanged": not diff, "diff": diff}
    write_json_deterministic(args.reports_dir / "pressure_threshold_experiment.json", out)
    write_text(args.reports_dir / "pressure_eligibility_report.md", render_report(out))
    print(
        f"definitions={len(public)} selected={selection['selected_id']} "
        f"viable={selection['viable_count']} official_unchanged={not diff}"
    )
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
