"""Phase 5 Chunk 4: build the stored analytics of the dynamic ranking engine. EXPERIMENTAL.

Computed once (no model per filter combination): ``p5_context_stats`` (delivery-level evidence rows
of the PROVISIONAL definition, TRAIN and VALIDATION only), ``p5_context_fit`` (TRAIN-only
between-player variance and shrinkage strength per atomic context), ``p5_context_eligibility_rules``
(each context's own data-derived working threshold, NOT validated), ``p5_context_scores`` (raw,
expected, residual, shrunk, sample sizes per player and context), ``p5_context_manifest``,
``p5_filter_catalog`` and ``p5_context_coverage`` (actual qualifying counts per filter combination).
TEST outcomes and Cricsheet are never read. Exit 1 if the overall context does not reproduce the
Phase 4 scores or if official data, Phase 4 reports or the TEST lock changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, write_json_deterministic  # noqa: E402
from app.phase4.config import file_sha256  # noqa: E402
from app.phase5 import context_eligibility as ce  # noqa: E402
from app.phase5 import context_stats as cs  # noqa: E402
from app.phase5 import coverage as cov  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.filters import catalog  # noqa: E402
from app.phase5.outputs import Preservation, save_table  # noqa: E402
from app.phase5.ranking_engine import ContextEngine  # noqa: E402
from app.phase5.store import write_p5_table  # noqa: E402
from app.repositories.phase5_repo import CONTEXT_RULES_CONFIG, frame_hash, load_context_config  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def reproduce_overall(artifacts: dict[str, pd.DataFrame], store: Path, defn: str, cfg_name: str):
    """The (ALL, ALL) context must equal the stored Phase 4 scores of the carried definition."""
    con = duckdb.connect(str(store), read_only=True)
    try:
        ref = con.execute(
            "SELECT player_id, role, format, shrunk_estimate, pressure_opportunities "
            "FROM p4_pressure_scores_frozen_rules WHERE definition_id = ? AND shrinkage_config = ? "
            "AND \"window\" = 'PRE_TEST' AND stream IN ('runs', 'charged') AND format IN ('IPL','T20I')",
            [defn, cfg_name],
        ).df()
    finally:
        con.close()
    sc = artifacts["scores"]
    sc = sc[(sc["phase"] == "ALL") & (sc["situation"] == "ALL")]
    worst, n_cmp, n_equal = 0.0, 0, 0
    per_cell = {}
    for (comp, role), g in sc.groupby(["comp", "role"]):
        r = ref[(ref["format"] == comp) & (ref["role"] == role)].set_index("player_id")
        mine = g.set_index("player_id")
        common = mine.index.intersection(r.index)
        d = float(np.max(np.abs(mine.loc[common, "shrunk"] - r.loc[common, "shrunk_estimate"])))
        eq = int(
            (
                mine.loc[common, "n"].to_numpy()
                == r.loc[common, "pressure_opportunities"].to_numpy()
            ).sum()
        )
        per_cell[f"{comp}|{role}"] = {"compared": int(len(common)), "in_store": int(len(r)),
                                      "here": int(len(mine)), "max_abs_diff": d,
                                      "opportunity_counts_equal": eq}  # fmt: skip
        worst, n_cmp, n_equal = max(worst, d), n_cmp + len(common), n_equal + eq
    return {"max_abs_diff": worst, "players_compared": n_cmp, "opportunity_counts_equal": n_equal,
            "reproduces": bool(worst <= 1e-9 and n_cmp == n_equal and n_cmp > 0),
            "per_cell": per_cell}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    pres = Preservation(args.reports)
    cfg = load_context_config()
    study = pl.load_study(args.store)
    rep = pl.reproduce_phase4_scores(study, args.store)
    if not rep["reproduces"]:
        print("FATAL: Phase 4 scores do not reproduce", rep["max_abs_diff"])
        return 1
    frozen = study.frozen
    defn, shrink_config = frozen["definition"]["id"], frozen["shrinkage"]["config"]
    if defn != cfg["definition_id"]:
        print("FATAL: frozen definition differs from the context rules config")
        return 1
    stats = cs.build_context_stats(study, defn)
    ladders = json.loads(pl.ELIG_RULES.read_text(encoding="utf-8"))["ladders"]
    art = ce.build_artifacts(stats, cfg, ladders, shrink_config)
    repro = reproduce_overall(art, args.store, defn, shrink_config)
    if not repro["reproduces"]:
        print("FATAL: the overall context does not reproduce the Phase 4 scores", repro)
        return 1
    con = duckdb.connect(str(args.store), read_only=True)
    try:
        restr = con.execute(
            "SELECT applied_restrictions FROM p4_pressure_scores_frozen_rules "
            "WHERE is_carried_definition LIMIT 1"
        ).fetchone()[0]
        cls = con.execute("SELECT * FROM p5_player_classification").df()
    finally:
        con.close()
    cfg_hashes = pl.config_hashes({"context_rules": CONTEXT_RULES_CONFIG})
    manifest = {
        "model_version": cfg["model_version"],
        "status": STATUS,
        "definition_id": defn,
        "definition_label": cfg["definition_label"],
        "baseline_version": study.bs.version,
        "shrinkage_config": shrink_config,
        "restrictions_applied": restr,
        "config_hashes": cfg_hashes,
        "classification_hash": frame_hash(cls),
        "stats_hash": frame_hash(stats),
        "code_version": code_version(),
        "periods_in_fit": ["TRAIN"],
        "periods_scored": ["TRAIN", "VALIDATION"],
        "test_outcomes_used": False,
        "n_boot": cfg["n_boot"],
        "seed": cfg["seed"],
    }
    write_p5_table(stats, "p5_context_stats", args.store)
    save_table(art["rules"], "phase5_context_eligibility_rules", args.reports, args.store,
               "p5_context_eligibility_rules")  # fmt: skip
    save_table(art["fit"], "phase5_context_fit", args.reports, args.store, "p5_context_fit")
    write_p5_table(art["scores"], "p5_context_scores", args.store)
    write_p5_table(
        pd.DataFrame([{"manifest_json": json.dumps(manifest, sort_keys=True)}]),
        "p5_context_manifest",
        args.store,
    )
    # coverage from the engine's own pool resolution over the stored tables
    from app.repositories.phase5_repo import Phase5Repository

    repo = Phase5Repository(args.store)
    eng: ContextEngine = repo.engine()
    con = duckdb.connect(str(args.store), read_only=True)
    try:
        strict = bool(
            con.execute("SELECT enabled FROM p5_strict_uncapped_capability").fetchone()[0]
        )
    finally:
        con.close()
    coverage = cov.build_coverage(eng, cls, strict)
    save_table(coverage, "phase5_context_coverage", args.reports, args.store, "p5_context_coverage")
    cat = catalog(cfg, strict)
    cat_rows = [{"filter": f, **it} for f, items in cat.items() for it in items]
    write_p5_table(pd.DataFrame(cat_rows), "p5_filter_catalog", args.store)
    ok = pres.verify()
    ctx = art["rules"]
    summary = {
        "status": STATUS,
        "model_version": cfg["model_version"],
        "definition": f"{defn} ({cfg['definition_label']})",
        "contexts": int(len(ctx)),
        "context_status_counts": ctx["context_status"].value_counts().to_dict(),
        "stats_rows": int(len(stats)),
        "score_rows": int(len(art["scores"])),
        "fit_floor_hit_contexts": int(art["fit"].get("floor_hit", pd.Series(dtype=bool)).fillna(False).sum()),
        "coverage_combinations": int(len(coverage)),
        "coverage_meets_internal_min": int(coverage["meets_internal_min"].sum()),
        "coverage_meets_public_min": int(coverage["meets_public_min"].sum()),
        "coverage_disabled": int((~coverage["enabled"]).sum()),
        "strict_uncapped_enabled": strict,
        "reproduction_overall_vs_phase4": repro,
        "phase4_reproduction": {"max_abs_diff": rep["max_abs_diff"], "players_compared": rep["players_compared"]},
        "config_hashes": cfg_hashes,
        "preservation": ok,
        "context_rules_sha256": file_sha256(CONTEXT_RULES_CONFIG),
    }  # fmt: skip
    write_json_deterministic(args.reports / "phase5_context_engine_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("contexts", "context_status_counts", "stats_rows",
          "score_rows", "coverage_combinations", "coverage_meets_internal_min",
          "coverage_meets_public_min", "coverage_disabled")}, indent=1))  # fmt: skip
    print("overall reproduces Phase 4:", repro["reproduces"], "max diff", repro["max_abs_diff"])
    print("preserved:", ok["all_preserved"])
    return 0 if ok["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
