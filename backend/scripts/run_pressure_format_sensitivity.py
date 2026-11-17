"""Stage 6: format-weight sensitivity with pressure-specific eligibility (EXPLORATORY).

Reads the provisional thresholds from data/reports/pressure_threshold_experiment.json (run
scripts/run_pressure_eligibility.py first), rebuilds the pressure samples of the provisional
definition and reruns all eight format-weight configurations. Writes
pressure_format_weight_sensitivity.json/.md. No official Top 10; a missing format score is never
filled. Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics import baseline_engine as be  # noqa: E402
from app.analytics import pressure_eligibility as pe  # noqa: E402
from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics import pressure_format_sensitivity as pfs  # noqa: E402
from app.analytics.format_config import load_config  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.pressure_format_report import render_report  # noqa: E402
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402
from scripts.run_pressure_distributions import prepare  # noqa: E402

RULES = ROOT / "config" / "pressure_eligibility_rules_v1.json"


def thresholds_from_experiment(exp: dict) -> tuple[dict, dict, dict]:
    """(primary, robustness, info) min-balls maps {format: {role: value}} from the experiment."""
    sel = next(
        d for d in exp["definitions"] if d["definition"]["id"] == exp["selection"]["selected_id"]
    )
    prim: dict = {}
    strict: dict = {}
    loose: dict = {}
    for f in pe.FORMATS:
        prim[f], strict[f], loose[f] = {}, {}, {}
        for r in pe.ROLES:
            c = sel["summary"][f][r]
            rec = c["recommended"]
            ladder = sel["experiment"]["recommendation_inputs"][f][r]["families"]["balls"]["ladder"]
            mins = [e["min_value"] for e in ladder]
            prim[f][r] = rec["min_balls"]
            lad = {e["rule_id"]: e for e in ladder}
            alt = lad.get(c["highest_sufficient_pool_rule"])
            strict[f][r] = alt["min_value"] if alt else rec["min_balls"]
            below = [m for m in mins if m < rec["min_balls"]]
            loose[f][r] = max(below) if below else rec["min_balls"]
    return prim, {"STRICTER_highest_sufficient_pool": strict, "LOOSER_previous_rung": loose}, sel


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--config", type=Path, default=s.format_weights_config)
    ap.add_argument("--rules", type=Path, default=RULES)
    args = ap.parse_args(argv)
    fcfg = load_config(args.config)
    cfg = pe.load_rules(args.rules)
    before = snapshot_from_settings(s, args.db)
    exp = json.loads(
        (args.reports_dir / "pressure_threshold_experiment.json").read_text(encoding="utf-8")
    )
    if exp["selection"]["selected_id"] is None:
        print("no provisional definition: format sensitivity not run")
        return 1
    prim, rob, sel = thresholds_from_experiment(exp)
    definition = sel["definition"]
    rules, df, _ = prepare(args.store)
    _, flags = pf.build_candidates(df, rules)
    params = {
        "min_cell_innings": int(cfg["baseline"]["min_cell_innings"]),
        "tau2_floor": float(cfg["baseline"]["tau2_floor"]),
    }
    bat, bowl = be.batter_frame(df), be.bowler_frame(df)
    fb = pe.definition_flag(flags, cfg, definition, "batter")[bat["_src_index"].to_numpy()]
    fw = pe.definition_flag(flags, cfg, definition, "bowler")[bowl["_src_index"].to_numpy()]
    res_c = pe.residual_sets(bat, bowl, fb, fw, params)
    bsamp = pe.batter_samples(bat, fb, res_c["runs"])
    wsamp = pe.bowler_samples(bowl, fw, res_c["charged"], res_c["wkt"])
    res = pfs.run(bsamp, wsamp, fcfg, prim, rob, int(cfg["list_size"]), "PRESSURE_SPECIFIC")
    all_sit_path = args.reports_dir / "format_weight_sensitivity.json"
    all_sit = (
        json.loads(all_sit_path.read_text(encoding="utf-8")) if all_sit_path.exists() else None
    )
    res["pressure_definition"] = definition
    res["pressure_thresholds_min_balls"] = prim
    res["threshold_source"] = "pressure_threshold_experiment.json provisional_recommendation"
    res["robustness_thresholds_min_balls"] = rob
    res["population_changes"] = pfs.population_changes(res, all_sit)
    res["degenerate_populations_equal_across_configs"] = pfs.degenerate_note(res)
    res["weights_status"] = "70:30 is a PROVISIONAL default, not a validated optimum"
    res["provenance"] = provenance(None, args.config, seed=None)
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    res["preservation"] = {"official_unchanged": not diff, "diff": diff}
    out = args.reports_dir
    write_json_deterministic(out / "pressure_format_weight_sensitivity.json", res)
    write_text(out / "pressure_format_weight_sensitivity.md", render_report(res))
    print(
        "combined populations: "
        + ", ".join(f"{r}={res['roles'][r]['combined_population']}" for r in pfs.ne.ROLES)
        + f"; official_unchanged={not diff}"
    )
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
