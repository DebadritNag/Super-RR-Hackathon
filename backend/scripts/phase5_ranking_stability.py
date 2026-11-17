"""Phase 5 Chunk 3 (c): ranking stability by seeded match-cluster bootstrap. EXPERIMENTAL_NOT_VALIDATED.

Per (format x role) cell for the PROVISIONAL primary and the three alternative definitions, the
format-combined pool, and the phase x situation contexts of the primary: Top-10 inclusion
probabilities, rank intervals, expected Top-10 overlap, bootstrap Spearman, Spearman across
contexts and across definitions. A pool below the minimum reports POOL_TOO_SMALL and nothing is
padded. TEST outcomes and Cricsheet are never read. Exit 1 if official data, Phase 4 reports or
the TEST lock changed. No Top 10 here is a published or official list.
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
from app.phase5 import stability as stb  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.outputs import Preservation, failing_gates, rows_of, save_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NOT_OFFICIAL = (
    f"Status: {STATUS}. PROVISIONAL and descriptive. Not an official ranking and not a published Top 10; "
    "nothing here is validated. TEST outcomes: not used. Cricsheet: not used."
)


def cross_definition(study: pl.Study, defns: list[str]) -> pd.DataFrame:
    """Spearman and Top-10 overlap of each alternative definition against the primary, per cell."""
    cfg = study.frozen["shrinkage"]["config"]
    runs = {}
    for d in defns:
        cells = study.primary_cells(d)
        runs[d] = sn.run_scores(cells, study.frozen_rules(cells), cfg)
    rows = []
    for a in defns:
        for b in defns:
            if a >= b:
                continue
            for key in runs[a]:
                if key in runs[b]:
                    c = sn.compare(runs[a][key]["scores"], runs[b][key]["scores"])
                    rows.append(
                        {
                            "definition_a": a,
                            "definition_b": b,
                            "format": key[0],
                            "role": key[1],
                            **c,
                        }
                    )
    return pd.DataFrame(rows)


def render(res: dict) -> str:
    ds, cs, at, cross, xd = (
        res["def_summary"],
        res["combined"],
        res["atomic"],
        res["atomic_cross"],
        res["cross_def"],
    )
    prim = res["primary"]
    L = [
        "# Phase 5 ranking stability",
        "",
        NOT_OFFICIAL,
        "",
        f"Primary definition `{prim}` is PROVISIONAL. Bootstrap: {res['n_boot']} match-cluster resamples, seed "
        f"{res['seed']}, baseline, TRAIN-fitted thresholds and shrinkage parameters held fixed. Shrinkage "
        f"`{res['shrinkage']}`. Pools use the frozen unvalidated working-pool ball thresholds. Code version "
        f"`{res['code_version'][:16]}`. Reading guide: 'inclusion' is the share of resamples in which a player is in "
        "the Top 10 of the pool; 'rank interval' is the 2.5% to 97.5% range of the player's rank. Phase 4's own "
        "report `phase4_ranking_stability.md` is untouched.",
        "",
        "## 0. Preconditions",
        f"- Phase 4 scores reproduced: max abs difference {res['reproduction']['max_abs_diff']:.2e} over "
        f"{res['reproduction']['players_compared']} players (reproduces = {res['reproduction']['reproduces']}).",
        "",
        "## 1. Format x role cells, all four definitions",
        "'expected overlap (point)' is the mean number of the point-estimate Top 10 that are in the Top 10 of a "
        "resample. 'expected overlap (two resamples)' is the mean overlap between two independent resamples' Top 10. "
        "Both are out of `top-10 size`; rows marked trivial have a pool of 10 or fewer, where the Top 10 is the whole pool.",
        "",
    ]
    L.append(
        md_table(
            [
                "definition",
                "format",
                "role",
                "status",
                "pool",
                "top-10 size",
                "trivial",
                "overlap (point)",
                "overlap (two resamples)",
                "mean Spearman",
                "point Top 10 with inclusion >= 0.5",
                "players with inclusion 0.2 to 0.8",
                "median rank-interval width (point Top 10)",
            ],
            rows_of(
                ds.sort_values(["role", "format", "definition"]),
                [
                    "definition",
                    "format",
                    "role",
                    "status",
                    "pool_size",
                    "top10_size",
                    "trivial_full_pool",
                    "expected_overlap_with_point_top10",
                    "expected_overlap_two_independent_bootstrap_top10",
                    "mean_spearman_vs_point",
                    "point_top10_with_inclusion_ge_0_5",
                    "players_with_inclusion_between_0_2_and_0_8",
                    "median_rank_interval_width_point_top10",
                ],
            ),
        )
    )
    L += [
        "",
        "### Point-estimate Top 10 of the primary definition with inclusion probabilities (internal diagnostic, not a ranking)",
        "",
    ]
    pl_ = res["players"]
    pp = pl_[(pl_["definition"] == prim) & (pl_["point_rank"] <= 10)]
    L.append(
        md_table(
            [
                "format",
                "role",
                "player_id",
                "point rank",
                "Top-10 inclusion",
                "rank lo",
                "rank median",
                "rank hi",
                "pressure balls",
                "matches",
                "n_eff",
            ],
            rows_of(
                pp.sort_values(["role", "format", "point_rank"]),
                [
                    "format",
                    "role",
                    "player_id",
                    "point_rank",
                    "top10_inclusion_prob",
                    "rank_lo",
                    "rank_median",
                    "rank_hi",
                    "pressure_opportunities",
                    "distinct_matches",
                    "effective_sample_size",
                ],
            ),
        )
    )
    L += ["", "## 2. Format-combined pools (players eligible in both formats, 70:30)", ""]
    L.append(
        md_table(
            [
                "format",
                "role",
                "status",
                "pool",
                "trivial",
                "overlap (point)",
                "mean Jaccard",
                "mean Spearman",
            ],
            rows_of(
                cs,
                [
                    "format",
                    "role",
                    "status",
                    "pool_size",
                    "trivial_full_pool",
                    "expected_overlap_with_point_top10",
                    "mean_jaccard",
                    "mean_spearman_vs_point",
                ],
            ),
        )
    )
    L += [
        "",
        "## 3. Phase x situation contexts of the primary definition",
        "Each context re-aggregates the same stored residuals (no new model), refits the between-player variance on "
        "that context's TRAIN rows and uses that context's OWN working-pool threshold (P50 of its TRAIN ball counts; "
        "not validated, never borrowed from the overall cell). Contexts with fewer than 8 TRAIN players are "
        "`CONTEXT_NOT_ESTIMABLE`, with a pool below 5 `POOL_TOO_SMALL`. Filters cannot create reliability: a context "
        "that is thin stays thin.",
        "",
    ]
    L.append(
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "status",
                "TRAIN players",
                "pressure balls",
                "pool",
                "threshold balls",
                "floor hit",
                "overlap (point)",
                "mean Spearman",
            ],
            rows_of(
                at.sort_values(["role", "format", "phase", "situation"]),
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "status",
                    "train_players",
                    "pressure_balls_pre_test",
                    "pool_size",
                    "threshold_balls",
                    "fit_floor_hit",
                    "expected_overlap_with_point_top10",
                    "mean_spearman_vs_point",
                ],
            ),
        )
    )
    L += [
        "",
        "### Spearman across contexts (same players, same format and role; at least 8 common players)",
        "",
    ]
    ce = cross[cross["status"] == "ESTIMATED"]
    L.append(
        md_table(
            [
                "format",
                "role",
                "context A",
                "context B",
                "common",
                "Spearman",
                "top-10 overlap share",
            ],
            rows_of(
                ce.sort_values(["role", "format", "context_a", "context_b"]),
                [
                    "format",
                    "role",
                    "context_a",
                    "context_b",
                    "common_players",
                    "spearman",
                    "top10_overlap_share",
                ],
            ),
        )
    )
    L.append(
        f"\nPairs not estimable (fewer than 8 common players): {int((cross['status'] != 'ESTIMATED').sum())}."
    )
    L += ["", "## 4. Across definitions (point rankings, same cell)", ""]
    xd2 = xd[xd["definition_a"] == prim]
    L.append(
        md_table(
            [
                "definition A",
                "definition B",
                "format",
                "role",
                "common",
                "top-10 overlap",
                "trivial",
                "Spearman",
            ],
            rows_of(
                xd2.sort_values(["role", "format", "definition_b"]),
                [
                    "definition_a",
                    "definition_b",
                    "format",
                    "role",
                    "common_players",
                    "top_k_overlap",
                    "top_k_trivial_full_pool",
                    "spearman",
                ],
            ),
        )
    )
    L += ["", "## 5. Reading"]
    L += res["reading"]
    L += ["", "## 6. Unresolved issues"]
    L += [f"{i}. {t}" for i, t in enumerate(res["unresolved"], 1)]
    L += ["", "## 7. Gates still failing (from `phase5_publication_gates.json`)"]
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
    L += ["", "## 8. Preservation", f"`{res['preservation']}`"]
    return "\n".join(L) + "\n"


def reading(ds: pd.DataFrame, at: pd.DataFrame, prim: str) -> list[str]:
    p = ds[
        (ds["definition"] == prim)
        & (ds["status"] == "ESTIMATED")
        & ~ds["trivial_full_pool"].astype(bool)
    ]
    out = []
    if len(p):
        out.append(
            f"- Primary definition, non-trivial cells ({len(p)}): the point Top 10 keeps on average "
            f"{p['expected_overlap_with_point_top10'].min():.1f} to {p['expected_overlap_with_point_top10'].max():.1f} of its 10 "
            f"members in a resampled Top 10; two independent resamples agree on {p['expected_overlap_two_independent_bootstrap_top10'].min():.1f} "
            f"to {p['expected_overlap_two_independent_bootstrap_top10'].max():.1f} of 10. Fewer than 10 means the membership of the Top 10 "
            "depends on which matches happen to be in the sample."
        )
        lt = int(p["point_top10_with_inclusion_lt_0_5"].sum())
        out.append(
            f"- {lt} of the {int(p['top10_size'].sum())} point-Top-10 slots in these cells have a Top-10 inclusion "
            "probability below 0.5."
        )
    st = at["status"].value_counts().to_dict() if len(at) else {}
    out.append(
        f"- Phase x situation contexts by status: {st}. Thin contexts are reported as such, never padded."
    )
    out.append(
        "- Because the between-player variance is not identified (investigation report), this instability should be "
        "read as a lower bound on the problem: filters change which players are compared, they do not add information "
        "about each player."
    )
    out.append("- No ranking is validated and none may be published while the gates below fail.")
    return out


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
    defns = [study.cfg["definitions"]["primary"], *study.cfg["definitions"]["alternatives"]]
    ds, players = stb.definition_stability(study, defns)
    fw = sn.format_weight_grid(study)
    cs = stb.combined_stability(study, fw)
    ac = stb.atomic_contexts(study)
    xd = cross_definition(study, defns)
    save_table(ds, "phase5_ranking_stability_cells", rep, args.store, "p5_ranking_stability")
    save_table(players, "phase5_ranking_distributions", rep, args.store, "p5_ranking_distributions")
    save_table(
        cs, "phase5_ranking_stability_combined", rep, args.store, "p5_ranking_stability_combined"
    )
    save_table(
        ac["summary"],
        "phase5_ranking_stability_contexts",
        rep,
        args.store,
        "p5_ranking_stability_contexts",
    )
    save_table(
        ac["cross"],
        "phase5_ranking_context_spearman",
        rep,
        args.store,
        "p5_ranking_context_spearman",
    )
    save_table(
        xd, "phase5_ranking_cross_definition", rep, args.store, "p5_ranking_cross_definition"
    )
    pres = guard.verify()
    unresolved = [
        "Rankings are unstable where pools are non-trivial (section 1); the ordering is not reliable enough for "
        "any selection use, and no ranking is validated.",
        "Context pools use per-context working thresholds that are not validated; many contexts are thin or not estimable.",
        "Between-player variance is unidentified (see the investigation report), so the shrinkage that stabilises these "
        "rankings is itself provisional.",
        "Bootstrap holds baseline, thresholds and shrinkage parameters fixed, so it understates total uncertainty.",
        "Date verification, strict classification and the methodology-validation gate remain failing (section 7).",
    ]
    res = {
        "primary": defns[0], "shrinkage": study.frozen["shrinkage"]["config"], "n_boot": study.n_boot,
        "seed": study.seed, "code_version": code_version(), "reproduction": repro, "def_summary": ds,
        "players": players, "combined": cs, "atomic": ac["summary"], "atomic_cross": ac["cross"], "cross_def": xd,
        "reading": reading(ds, ac["summary"], defns[0]), "unresolved": unresolved, "gates": failing_gates(rep),
        "preservation": pres,
    }  # fmt: skip
    write_text(rep / "phase5_ranking_stability.md", render(res))
    write_json_deterministic(
        rep / "phase5_ranking_stability_summary.json",
        {"status": STATUS, "official_ranking": False, "primary_definition": defns[0], "n_boot": study.n_boot,
         "seed": study.seed, "code_version": res["code_version"], "config_hashes": pl.config_hashes(),
         "phase4_reproduction": {k: v for k, v in repro.items() if k != "per_cell"},
         "reading": res["reading"], "unresolved_issues": unresolved, "gates": res["gates"], "preservation": pres,
         "context_status_counts": ac["summary"]["status"].value_counts().to_dict()},
    )  # fmt: skip
    print("stability done | preserved:", pres["all_preserved"])
    return 0 if pres["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
