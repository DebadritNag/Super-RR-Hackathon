"""Phase 5 Chunk 3 (b): sensitivity of the PROVISIONAL primary run. EXPERIMENTAL_NOT_VALIDATED.

One-factor-at-a-time grids around ``any|q0.75`` / ``shrink_tau4`` / baseline B0 / frozen working-pool
ball thresholds: pressure definition (nine candidates, so the quantile thresholds are included),
eligibility ball thresholds, shrinkage strength (also crossed with the four named definitions),
baseline alternatives, and the eight format weights (primary definition only, same final
eligibility rules, independent of the definition axis). The date-restricted TEST sets are compared
as set composition and counts only. TEST outcomes and Cricsheet are never read. Exit 1 if official
data, Phase 4 reports or the TEST lock changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import (  # noqa: E402
    code_version,
    md_table,
    write_json_deterministic,
    write_text,
)
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5 import sensitivity as sn  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.outputs import Preservation, failing_gates, rows_of, save_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NOT_OFFICIAL = (
    f"Status: {STATUS}. PROVISIONAL and descriptive. Not an official ranking, no ML model, nothing "
    "here is validated. TEST outcomes: not used. Cricsheet: not used."
)


def render(res: dict) -> str:
    prim, cfg = res["primary"], res["shrinkage"]
    dg, sg, tg, bg = res["definition"], res["shrinkage_grid"], res["threshold"], res["baseline"]
    fw, ts = res["format_weights"], res["test_sets"]
    L = [
        "# Phase 5 sensitivity report",
        "",
        NOT_OFFICIAL,
        "",
        f"Reference run: definition `{prim}` (PROVISIONAL rule winner), shrinkage `{cfg}`, baseline B0, "
        "frozen working-pool ball thresholds (IPL batter 20, T20I batter 16, IPL bowler 49, T20I bowler 29; "
        "NOT validated, every cell is `THRESHOLD_NOT_VALIDATED`). Data: TRAIN + VALIDATION only. "
        f"Code version `{res['code_version'][:16]}`. Overlap and Spearman measure how far a choice moves the "
        "ordering. They do not say which choice is right.",
        "",
        "## 0. Preconditions",
        f"- Phase 4 scores reproduced: max abs difference {res['reproduction']['max_abs_diff']:.2e} over "
        f"{res['reproduction']['players_compared']} players (reproduces = {res['reproduction']['reproduces']}).",
        "- When a pool has 10 or fewer players the Top 10 is the whole pool and overlap is trivially high "
        "(`trivial` column). Pools are never padded.",
        "",
        "## 1. Definition alternatives (all nine candidates; quantile thresholds 0.75 / 0.9 / 0.95 included)",
        "Same frozen ball thresholds for every definition, so pool size changes with the definition because the "
        "pressure sample changes. Compared on players eligible under both.",
        "",
    ]
    d = dg[dg["format"] != "COMBINED_w70_30"]
    L.append(
        md_table(
            [
                "definition",
                "named alt",
                "format",
                "role",
                "pool ref",
                "pool alt",
                "common",
                "top-10 overlap",
                "trivial",
                "Spearman",
                "Kendall",
            ],
            rows_of(
                d.sort_values(["role", "format", "definition"]),
                [
                    "definition",
                    "is_named_alternative",
                    "format",
                    "role",
                    "pool_ref",
                    "pool_alt",
                    "common_players",
                    "top_k_overlap",
                    "top_k_trivial_full_pool",
                    "spearman",
                    "kendall_tau",
                ],
            ),
        )
    )
    L += ["", "Format-combined pools (players eligible in both formats, 70:30):", ""]
    d = dg[dg["format"] == "COMBINED_w70_30"]
    L.append(
        md_table(
            [
                "definition",
                "role",
                "pool ref",
                "pool alt",
                "common",
                "top-10 overlap",
                "trivial",
                "Spearman",
            ],
            rows_of(
                d.sort_values(["role", "definition"]),
                [
                    "definition",
                    "role",
                    "pool_ref",
                    "pool_alt",
                    "common_players",
                    "top_k_overlap",
                    "top_k_trivial_full_pool",
                    "spearman",
                ],
            ),
        )
    )
    L += [
        "",
        "## 2. Eligibility ball thresholds (primary definition, candidates from each cell's TRAIN distribution and ladder)",
        "`marginal data weight` is n_eff / (n_eff + k) of the least-qualified player in the pool. The Phase 4 gate "
        "needed 0.5 and no candidate reached it in any cell.",
        "",
    ]
    L.append(
        md_table(
            [
                "format",
                "role",
                "threshold",
                "source",
                "frozen pool",
                "pool",
                "common",
                "top-10 overlap",
                "trivial",
                "Spearman",
                "marginal data weight",
            ],
            rows_of(
                tg.sort_values(["role", "format", "threshold_balls"]),
                [
                    "format",
                    "role",
                    "threshold_balls",
                    "source",
                    "is_frozen_working_pool",
                    "pool_alt",
                    "common_players",
                    "top_k_overlap",
                    "top_k_trivial_full_pool",
                    "spearman",
                    "marginal_data_weight",
                ],
            ),
        )
    )
    L += [
        "",
        "## 3. Shrinkage strength (seven configurations) crossed with the four named definitions",
        f"Two references: the primary run (`{prim}`, `{cfg}`) and the same definition under its own frozen shrinkage. "
        "k is the shrinkage strength of the configuration (larger = more shrinkage). `shrink_none` and "
        "`shrink_target0` are sensitivity-only and cannot be chosen as primary.",
        "",
    ]
    s = sg[
        (sg["reference"] == "same_definition_frozen_shrinkage")
        & (sg["format"] != "COMBINED_w70_30")
    ]
    L.append(
        md_table(
            [
                "definition",
                "shrinkage",
                "format",
                "role",
                "k",
                "median data weight",
                "pool",
                "top-10 overlap vs same-definition frozen",
                "trivial",
                "Spearman",
            ],
            rows_of(
                s.sort_values(["role", "format", "definition", "shrinkage_config"]),
                [
                    "definition",
                    "shrinkage_config",
                    "format",
                    "role",
                    "k",
                    "median_data_weight_pool",
                    "pool_alt",
                    "top_k_overlap",
                    "top_k_trivial_full_pool",
                    "spearman",
                ],
            ),
        )
    )
    L += ["", "Against the primary run (all 28 combinations, single-format pools):", ""]
    s = sg[(sg["reference"] == "primary_run") & (sg["format"] != "COMBINED_w70_30")]
    L.append(
        md_table(
            ["definition", "shrinkage", "format", "role", "common", "top-10 overlap", "Spearman"],
            rows_of(
                s.sort_values(["role", "format", "definition", "shrinkage_config"]),
                [
                    "definition",
                    "shrinkage_config",
                    "format",
                    "role",
                    "common_players",
                    "top_k_overlap",
                    "spearman",
                ],
            ),
        )
    )
    L += [
        "",
        "## 4. Baseline alternatives (fitted on TRAIN only; primary definition)",
        "B0 is the frozen baseline. Alternatives use coarser first cell levels or drop the format offset. "
        "VALIDATION RMSE/MAE show fit; overlap and Spearman show ranking movement against B0.",
        "",
    ]
    L.append(
        md_table(
            [
                "baseline",
                "format",
                "role",
                "VAL rows",
                "VAL RMSE",
                "VAL MAE",
                "pool B0",
                "pool variant",
                "common",
                "top-10 overlap",
                "Spearman",
            ],
            rows_of(
                bg,
                [
                    "baseline",
                    "format",
                    "role",
                    "validation_rows",
                    "validation_rmse",
                    "validation_mae",
                    "pool_size_B0",
                    "pool_size_variant",
                    "common_players",
                    "top10_overlap_vs_B0",
                    "spearman_vs_B0",
                ],
            ),
        )
    )
    L += [
        "",
        "## 5. Format weights (eight configurations; primary definition; same final eligibility rules)",
        "Only players eligible in BOTH formats under the same frozen rules are combined. This axis is independent "
        "of the definition axis. The 70:30 default is PROVISIONAL.",
        "",
    ]
    L.append(
        md_table(
            [
                "role",
                "config",
                "IPL w",
                "T20I w",
                "pool",
                "top-10 overlap vs w70_30",
                "trivial",
                "Spearman vs w70_30",
                "mean abs rank change",
                "bootstrap expected overlap",
            ],
            rows_of(
                fw["configs"],
                [
                    "role",
                    "config_id",
                    "ipl_weight",
                    "t20i_weight",
                    "pool_size",
                    "top10_overlap_vs_default",
                    "top10_trivial_full_pool",
                    "spearman_vs_default",
                    "mean_abs_rank_change_vs_default",
                    "bootstrap_expected_top10_overlap",
                ],
            ),
        )
    )
    L += [
        "",
        "## 6. Date-restricted TEST sets (set composition only)",
        "Sets from `phase5_test_set_manifest.json`. TEST stays closed: no outcome, score or metric of any TEST match "
        "is computed here, so this section says how much data each rule removes, not how results would change. "
        "Phase 4's aggregate TEST evaluation covered all 144 matches including the 42 late T20I matches with "
        "unverified dates and is sensitivity-only; a later evaluation is not a pristine hold-out.",
        "",
        f"Manifest status: `{ts.get('status')}`.",
        "",
    ]
    if ts.get("sets"):
        L.append(
            md_table(
                ["set", "rule", "matches", "IPL matches", "T20I matches", "deliveries", "players"],
                [
                    [
                        s_["set"],
                        s_["rule"],
                        s_["matches"],
                        s_.get("matches_IPL"),
                        s_.get("matches_T20I"),
                        s_["deliveries"],
                        s_["players"],
                    ]
                    for s_ in ts["sets"]
                ],
            )
        )
        L.append(f"\nExcluded from PRIMARY_RESTRICTED: `{ts.get('excluded_from_primary')}`.")
    L += ["", "## 7. Reading the grids"]
    L += res["reading"]
    L += ["", "## 8. Unresolved issues"]
    L += [f"{i}. {t}" for i, t in enumerate(res["unresolved"], 1)]
    L += ["", "## 9. Gates still failing (from `phase5_publication_gates.json`)"]
    g = res["gates"]
    if g.get("available"):
        L.append(f"Publication status of any ranking today: `{g['publication_status']}`.")
        L.append(
            md_table(
                ["gate", "passed", "applicable", "detail"],
                [
                    [x["gate_id"], x["passed"], x["applicable"], x["detail"]]
                    for x in g["gate_results"]
                ],
            )
        )
    else:
        L.append(g["note"])
    L += ["", "## 10. Preservation", f"`{res['preservation']}`"]
    return "\n".join(L) + "\n"


def reading(dg: pd.DataFrame, sg: pd.DataFrame, bg: pd.DataFrame, fw: pd.DataFrame) -> list[str]:
    single = dg[
        (dg["format"] != "COMBINED_w70_30") & ~dg["is_primary"] & dg["top_k_overlap_share"].notna()
    ]
    nontrivial = single[~single["top_k_trivial_full_pool"].astype(bool)]
    lines = []
    if len(nontrivial):
        lines.append(
            f"- Definition axis: over {len(nontrivial)} non-trivial single-format comparisons the Top-10 overlap with the "
            f"primary ranges from {int(nontrivial['top_k_overlap'].min())} to {int(nontrivial['top_k_overlap'].max())} of 10 "
            f"(median {nontrivial['top_k_overlap'].median():.1f}), Spearman from {nontrivial['spearman'].min():.2f} to "
            f"{nontrivial['spearman'].max():.2f}. The ordering depends on the pressure definition."
        )
    same = sg[
        (sg["reference"] == "same_definition_frozen_shrinkage")
        & (sg["format"] != "COMBINED_w70_30")
        & ~sg["is_frozen_choice"]
    ]
    ns = same[~same["top_k_trivial_full_pool"].astype(bool) & same["top_k_overlap"].notna()]
    if len(ns):
        lines.append(
            f"- Shrinkage axis: against the same definition's frozen shrinkage the Top-10 overlap ranges from "
            f"{int(ns['top_k_overlap'].min())} to {int(ns['top_k_overlap'].max())} (median {ns['top_k_overlap'].median():.1f}); "
            f"Spearman {ns['spearman'].min():.2f} to {ns['spearman'].max():.2f}."
        )
    b = bg[bg["baseline"] != "B0"]
    if "top10_overlap_vs_B0" in b and b["top10_overlap_vs_B0"].notna().any():
        lines.append(
            f"- Baseline axis: Top-10 overlap with B0 {int(b['top10_overlap_vs_B0'].min())} to {int(b['top10_overlap_vs_B0'].max())}; "
            f"Spearman {b['spearman_vs_B0'].min():.2f} to {b['spearman_vs_B0'].max():.2f}."
        )
    f = fw[fw["top10_overlap_vs_default"].notna() & ~fw["is_default_provisional"]]
    if len(f):
        lines.append(
            f"- Format-weight axis: Top-10 overlap with w70_30 {int(f['top10_overlap_vs_default'].min())} to "
            f"{int(f['top10_overlap_vs_default'].max())}; Spearman {f['spearman_vs_default'].min():.2f} to "
            f"{f['spearman_vs_default'].max():.2f}. Pools are small (see `pool`), so many rows are trivial or near trivial."
        )
    lines.append("- None of these results selects a setting. Every setting stays PROVISIONAL.")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    rep = args.reports
    guard = Preservation(rep)
    study = pl.load_study(args.store, n_boot=args.n_boot)
    repro = pl.reproduce_phase4_scores(study, args.store)
    if not repro["reproduces"]:
        print("FATAL: Phase 4 scores do not reproduce", repro)
        return 1
    dg = sn.definition_grid(study)
    sg = sn.shrinkage_grid(study)
    tg = sn.threshold_grid(study)
    bg = sn.baseline_grid(study)
    fw = sn.format_weight_grid(study)
    ts = sn.test_set_comparison(rep / "phase5_test_set_manifest.json")
    save_table(dg, "phase5_sensitivity_definitions", rep, args.store, "p5_sensitivity_results")
    save_table(sg, "phase5_sensitivity_shrinkage", rep, args.store, "p5_sensitivity_shrinkage")
    save_table(tg, "phase5_sensitivity_thresholds", rep, args.store, "p5_sensitivity_thresholds")
    save_table(bg, "phase5_sensitivity_baselines", rep, args.store, "p5_sensitivity_baselines")
    save_table(
        fw["configs"],
        "phase5_sensitivity_format_weights",
        rep,
        args.store,
        "p5_sensitivity_format_weights",
    )
    save_table(
        fw["pairwise"],
        "phase5_sensitivity_format_weight_pairwise",
        rep,
        args.store,
        "p5_sensitivity_pairwise",
    )
    pres = guard.verify()
    unresolved = [
        "No setting is validated. Definition, shrinkage, baseline, thresholds and format weights all stay PROVISIONAL.",
        "Eligibility thresholds are the unvalidated TRAIN-median working pools; the marginal data weight gate (0.5) "
        "was not met by any candidate in any cell, so pool sizes here are a function of an unvalidated choice.",
        "Pools are small. Several overlap figures are trivial (Top 10 equals the whole pool) and carry no information.",
        "TEST sensitivity cannot be measured while TEST is closed; only set composition is reported.",
        "The Phase 4 noise estimator (see the investigation report) drives the strong shrinkage; a different noise "
        "model would change the shrinkage axis and is a methodology decision for review.",
        "Date verification, strict classification and the methodology-validation gate remain failing (section 9).",
    ]
    res = {
        "primary": study.cfg["definitions"]["primary"], "shrinkage": study.frozen["shrinkage"]["config"],
        "code_version": code_version(), "reproduction": repro, "definition": dg, "shrinkage_grid": sg,
        "threshold": tg, "baseline": bg, "format_weights": fw, "test_sets": ts,
        "reading": reading(dg, sg, bg, fw["configs"]), "unresolved": unresolved, "gates": failing_gates(rep),
        "preservation": pres,
    }  # fmt: skip
    write_text(rep / "phase5_sensitivity_report.md", render(res))
    write_json_deterministic(
        rep / "phase5_sensitivity_summary.json",
        {"status": STATUS, "official_ranking": False, "primary_definition": res["primary"], "shrinkage": res["shrinkage"],
         "n_boot": study.n_boot, "seed": study.seed, "code_version": res["code_version"],
         "config_hashes": pl.config_hashes(), "phase4_reproduction": {k: v for k, v in repro.items() if k != "per_cell"},
         "test_sets": ts, "reading": res["reading"], "unresolved_issues": unresolved, "gates": res["gates"],
         "preservation": pres, "rows": {"definitions": len(dg), "shrinkage": len(sg), "thresholds": len(tg),
                                        "baselines": len(bg), "format_weights": len(fw["configs"])}},
    )  # fmt: skip
    print("sensitivity done | preserved:", pres["all_preserved"])
    return 0 if pres["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
