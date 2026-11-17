"""Phase 4 Chunk 3, Stages D and E: definition comparison, eligibility, shrinkage, format weights,
baseline alternatives and ranking stability. EXPERIMENTAL_NOT_VALIDATED, no official ranking.

Order of choices (fixed before any downstream experiment): (1) pressure definition by the rule in
``config/phase4_definition_rule_v1.json``; (2) shrinkage strength on VALIDATION; (3) per-cell
eligibility thresholds. They are written to ``phase4_frozen_choices.json`` (with a FREEZE entry in
the lock log) before sensitivity runs. Only TRAIN and VALIDATION rows are loaded. TEST outcomes
are never read and ``evaluate_on_test`` is not called here. Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import (  # noqa: E402
    md_table,
    round_floats,
    write_json_deterministic,
    write_text,  # noqa: E402
)
from app.core.config import get_settings  # noqa: E402
from app.phase4 import definitions as df_  # noqa: E402
from app.phase4 import eligibility as el  # noqa: E402
from app.phase4 import engine as en  # noqa: E402
from app.phase4 import scoring as sc  # noqa: E402
from app.phase4 import sensitivity as sn  # noqa: E402
from app.phase4 import shrink as sh  # noqa: E402
from app.phase4.baseline import DEFAULT_PARAMS, fit_baseline_set  # noqa: E402
from app.phase4.config import file_sha256  # noqa: E402
from app.phase4.constants import FROZEN_CHOICES, REPORTS_DIR, SPLIT_CONFIG, STATUS  # noqa: E402
from app.phase4.split import TestLock, write_frozen_choices  # noqa: E402
from app.phase4.store import write_p4_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402
from scripts.phase4_baseline import load_pre_test  # noqa: E402

FORMAT_WEIGHTS = ROOT / "config" / "format_weights_v1.json"
ELIG_RULES = ROOT / "config" / "pressure_eligibility_rules_v1.json"
NOT_OFFICIAL = f"Status: {STATUS}. Not an official ranking. No final ML model."


def save(df: pd.DataFrame, name: str, reports: Path, store: Path, table: str | None = None) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    df.to_csv(reports / f"{name}.csv", index=False)
    write_json_deterministic(
        reports / f"{name}.json",
        {
            "status": STATUS,
            "official_ranking": False,
            "records": json.loads(df.to_json(orient="records")),
        },
    )
    if table:
        write_p4_table(df, table, store)


def cols(df: pd.DataFrame, names: list[str]) -> list[str]:
    return [c for c in names if c in df.columns]


def rows_of(df: pd.DataFrame, names: list[str]) -> list[list]:
    c = cols(df, names)
    return df[c].astype(object).where(df[c].notna(), None).values.tolist()


# ---------------------------------------------------------------- renderers
def render_definitions(defs: dict, chosen: str, chosen_label: str) -> str:
    rule, res, t = defs["rule"], defs["candidates"], defs["table"]
    c = pd.DataFrame(res["candidates"])
    L = [
        "# Phase 4 pressure definition comparison",
        "",
        NOT_OFFICIAL,
        "",
        "All nine full-eligibility candidates (`{chase, inn1, any} x q in {0.75, 0.90, 0.95}`) are "
        "compared. The full table is retained. The winner is PROVISIONAL, one of nine examined, "
        "with no multiplicity correction. `chase|q0.9` was accepted only as the leading provisional "
        "candidate; its earlier selection rested on eligible population size, which is not used here.",
        "",
        f"Rule file: `config/phase4_definition_rule_v1.json` (SHA-256 `{defs['rule_sha256']}`), "
        "fixed before any metric was computed. Data: TRAIN and VALIDATION only. TEST outcomes: not "
        f"used. Bootstrap: {defs['n_boot']} match-cluster resamples, seed {defs['seed']}. "
        "Thresholds are TRAIN-only quantiles of the pre-delivery signal "
        "(`rrr` for chase; negative deviation from the STRICTLY PRIOR par for innings 1).",
        "",
        "## Selection rule (as written before the run)",
    ]
    L += [f"- {x}" for x in rule["gates_and_choice"]]
    L += [f"- Bootstrap note: {rule['bootstrap_note']}", "", "## Result"]
    if res.get("winner"):
        L.append(
            f"Rule winner: **`{res['winner']}`** ({res['label']}). Top group "
            f"(within max(0.02, bootstrap SE of best Sc) = {res['tie_margin_used']:.3f} of the best): "
            f"{res['top_group']}. Best Sc candidate: `{res['best_Sc_candidate']}`. "
            f"Leading candidate `{res['leading_provisional']}` status under the rule: "
            f"{res['leading_status']}; in top group: {res['leading_in_top_group']}."
        )
    else:
        L.append(
            "No candidate passed Gate 1 and was rankable, so the rule names NO winner. "
            f"`{res['leading_provisional']}` stays the labelled leading provisional default and is "
            "not validated."
        )
    if "sample_size_confound_spearman" in res:
        L.append(
            f"Sample-size check: across the {res['sample_size_confound_n']} rankable candidates the "
            "Spearman correlation between Sc and total TRAIN pressure balls is "
            f"{res['sample_size_confound_spearman']:.2f}. Reliability rises mechanically with the "
            "number of balls per player, so Sc is partly a sample-size effect and the rule gives "
            "weak evidence about which definition measures pressure better. Members of the top "
            "group are not distinguishable, and the winner among them is fixed by the "
            "pre-declared lexicographic tie-break, not by merit."
        )
    L += [
        "",
        f"Definition carried into the downstream experiments: `{chosen}` ({chosen_label}).",
        "",
        "## Candidate table (population is shown, never used to select)",
        md_table(
            [
                "definition",
                "status",
                "Sc (corr scale)",
                "Sc boot SE",
                "selection share",
                "min P",
                "total P",
                "TRAIN pressure balls",
            ],
            rows_of(
                c,
                [
                    "definition_id",
                    "status",
                    "Sc",
                    "Sc_boot_se",
                    "selection_share",
                    "min_P",
                    "total_P",
                    "total_pressure_balls_TRAIN",
                ],
            ),
        ),
        "Selection share: share of match-bootstrap resamples in which the candidate has the highest "
        "Sc among Gate-1-passing rankable candidates. A low share means it is not distinguishable "
        "from the others.",
        "",
        "## Cell-level metrics (format x role)",
        md_table(
            [
                "definition",
                "format",
                "role",
                "P (>=18 balls TRAIN)",
                "R split-half (SB)",
                "n R",
                "S TRAIN->VAL",
                "n S",
                "SNR",
                "D (VAL)",
                "D lo",
                "D hi",
                "D expected direction",
                "expected top-10 overlap",
                "pool",
                "par unavailable share (inn1 TRAIN)",
            ],
            rows_of(
                t,
                [
                    "definition_id",
                    "format",
                    "role",
                    "P_players_ge_min_balls",
                    "R_split_half",
                    "n_R",
                    "S_train_validation",
                    "n_S",
                    "snr",
                    "D",
                    "D_lo",
                    "D_hi",
                    "D_in_expected_direction",
                    "expected_top10_overlap",
                    "top10_pool",
                    "par_unavailable_share_inn1_TRAIN",
                ],
            ),
        ),
        "",
        "## Pressure samples and performance relative to baseline",
        md_table(
            [
                "definition",
                "format",
                "role",
                "balls TRAIN",
                "matches TRAIN",
                "players TRAIN",
                "balls VAL",
                "matches VAL",
                "mean residual diff (pressure - other), VAL",
                "lo",
                "hi",
                "secondary stream",
                "secondary diff",
                "lo",
                "hi",
            ],
            rows_of(
                t,
                [
                    "definition_id",
                    "format",
                    "role",
                    "pressure_balls_TRAIN",
                    "distinct_matches_TRAIN",
                    "players_TRAIN",
                    "pressure_balls_VALIDATION",
                    "distinct_matches_VALIDATION",
                    "mean_diff",
                    "diff_lo",
                    "diff_hi",
                    "secondary_stream",
                    "secondary_mean_diff",
                    "secondary_diff_lo",
                    "secondary_diff_hi",
                ],
            ),
        ),
        "",
        "## Reading the table",
        "- D is report-only. |D| grows with the quantile by construction, so D is compared only "
        "within the same quantile. Expected sign: batter residual below baseline and bowler "
        "residual (runs conceded) above baseline under pressure.",
        "- R and S measure whether the sample separates players; population does not.",
        "- Format differences: compare the IPL and T20I rows of the same definition and role.",
        "- Threshold sensitivity: the three quantiles of each context are adjacent rows in the "
        "candidate table.",
        "",
        "## Limitations",
        "- Bowler pressure uses the same pre-delivery state signals as batters; the bowler-specific "
        "signal B of the design notes is not implemented, so bowler definitions are not bowler-specific.",
        "- Thresholds are fixed at their TRAIN values in the bootstrap (not refitted per resample).",
        "- Many cells have few players; R and S with fewer than 15 players make a candidate "
        "NOT_RANKABLE rather than being guessed.",
        "- Phase 3 population-based selection is context only and is not used.",
    ]
    return "\n".join(L) + "\n"


def render_eligibility(ev: dict, decisions: dict, rules: dict, chosen: str, cfg: str) -> str:
    L = [
        "# Phase 4 pressure eligibility validation",
        "",
        NOT_OFFICIAL,
        "",
        f"Definition `{chosen}`, shrinkage `{cfg}`. Thresholds are re-derived per cell from the "
        "observed TRAIN distribution of per-player pressure balls and judged on TRAIN and "
        "VALIDATION only. The Phase 3 T20I placeholders (batter 24, bowler 36 balls) are SUPERSEDED "
        "placeholders and are not validated.",
        "",
        "Rule (fixed before the run): (1) marginal-player data weight B(t) = n_t / (n_t + k) >= "
        f"{el.GATE_B}; (2) smallest passing candidate unless TRAIN-to-VALIDATION reproducibility "
        "is significantly negative; (3) otherwise THRESHOLD_NOT_VALIDATED (a low-data-weight "
        "fallback is named only if reproducibility is estimable with its interval above 0 and the marginal data weight is at least 0.1); "
        "(4) no threshold is lowered to reach ten players, and fewer than ten is reported as is.",
        "A threshold t is on the TRAIN scale: a PRE_TEST player qualifies with PRE_TEST balls >= t x W "
        "(W = PRE_TEST pressure balls / TRAIN pressure balls of the cell).",
        "",
        "## Decisions",
    ]
    dec_rows = []
    for (comp, role), d in decisions.items():
        r = rules[(comp, role)]
        dec_rows.append([comp, role, d["status"], d["threshold_balls"], d["fallback_threshold_balls"],
                         d["label"], d["working_pool_threshold_balls"], r["threshold_balls"],
                         r["label"], d["window_ratio_W"],
                         json.dumps(d["alt_gate_smallest_threshold"])])  # fmt: skip
    L.append(
        md_table(
            [
                "format",
                "role",
                "status",
                "selected t",
                "fallback t",
                "label",
                "working-pool t (TRAIN median)",
                "analysis t",
                "analysis label",
                "W",
                "smallest t at other data-weight gates",
            ],
            dec_rows,
        )
    )
    L += [
        "`analysis t` is the threshold used by the format-weight and ranking experiments. When it "
        "comes from the working pool it is NOT a validated eligibility rule; it exists so that the "
        "downstream experiments have players to rank, and every output carries its label.",
        "",
        "## Candidate thresholds by cell",
    ]
    for (comp, role), e in ev.items():
        c = pd.DataFrame(e["candidates"])
        L += [
            "",
            f"### {comp} {role}s (k = {e['k']:.2f}, W = {e['window_ratio']:.2f}, "
            f"VAL/TRAIN ball ratio = {e['validation_ratio']:.2f})",
            md_table(
                [
                    "t",
                    "source",
                    "players",
                    "balls",
                    "matches",
                    "median n_eff",
                    "marginal B",
                    "median B",
                    "median interval width",
                    "pool 2.5%",
                    "pool 97.5%",
                    "boot Jaccard top10",
                    "exp. top10 overlap",
                    "repro n",
                    "repro rho",
                    "lo",
                    "hi",
                    "Phase 3 placeholder value",
                ],
                rows_of(
                    c,
                    [
                        "threshold_balls",
                        "source",
                        "eligible_players",
                        "pressure_opportunities",
                        "distinct_matches",
                        "effective_sample_size_median",
                        "marginal_data_weight",
                        "median_data_weight",
                        "median_interval_width",
                        "pool_size_p2_5",
                        "pool_size_p97_5",
                        "boot_mean_jaccard_top10",
                        "expected_top10_overlap",
                        "reproducibility_players",
                        "reproducibility_spearman",
                        "reproducibility_lo",
                        "reproducibility_hi",
                        "is_phase3_placeholder_value",
                    ],
                ),
            ),
        ]
    L += [
        "",
        "## Limitations",
        "- Marginal-player data weight depends on k, which is estimated from few players and "
        "frequently sits at its floor; a floor hit means the data show little between-player spread, "
        "not that the spread is zero.",
        "- Reproducibility is estimable only with at least 15 players in both periods; otherwise it "
        "does not block a candidate and is reported as not estimable.",
        "- The candidate with the best reproducibility among many noisy values is a maximum with no "
        "multiplicity correction.",
    ]
    return "\n".join(L) + "\n"


def render_shrinkage(sens: pd.DataFrame, choice: dict, cfg: str, chosen: str) -> str:
    L = [
        "# Phase 4 shrinkage sensitivity",
        "",
        NOT_OFFICIAL,
        "",
        f"Definition `{chosen}`. Chosen configuration (TRAIN estimates against VALIDATION outcomes, "
        f"written before any scoring): **`{cfg}`**. Rule: {choice.get('rule')}. TEST outcomes: not used.",
        "",
        "## Estimator and assumptions",
        sh.__doc__.strip(),
        "",
        "Zero shrinkage (`shrink_none`) and target 0 (`shrink_target0`) are retained as sensitivity "
        "configurations and cannot be chosen as primary.",
        "",
        "## Pooled VALIDATION loss",
        md_table(
            ["config", "loss", "diff vs shrink_eb", "bootstrap SE", "choosable"],
            [
                [k, v["loss"], v["diff_vs_eb"], v["bootstrap_se"], v["choosable"]]
                for k, v in choice["losses"].items()
            ],
        ),  # fmt: skip
        "",
        "## Per cell and configuration (pool = frozen analysis eligibility; other factors fixed)",
        md_table(
            [
                "format",
                "role",
                "config",
                "k",
                "floor hit",
                "pool",
                "median B (pool)",
                "mean |shift| from raw",
                "Spearman vs eb",
                "top-10 overlap vs eb",
                "trivial full pool",
                "median interval width",
                "exp. top-10 overlap (boot)",
                "VAL loss",
                "diff vs eb",
                "SE",
            ],
            rows_of(
                sens,
                [
                    "format",
                    "role",
                    "shrinkage_config",
                    "k",
                    "floor_hit",
                    "pool_size",
                    "median_data_weight_pool",
                    "mean_abs_shift_from_raw_pool",
                    "spearman_vs_shrink_eb",
                    "top10_overlap_vs_shrink_eb",
                    "top10_trivial_full_pool",
                    "median_interval_width_pool",
                    "expected_top10_overlap_bootstrap",
                    "validation_loss_cell",
                    "validation_loss_diff_vs_eb",
                    "validation_loss_bootstrap_se",
                ],
            ),
        ),
        "",
        "## Limitations",
        "- Intervals hold k and the pooled target fixed; tau2 estimation error is not propagated.",
        "- The pooled target uses TRAIN rows only; the PRE_TEST-window target (`shrink_mu_window`) "
        "sensitivity was not run.",
        "- A tau2 at the floor means stronger shrinkage than a larger tau2 would give; compare "
        "`shrink_floor0.001` and `shrink_tau4`.",
    ]
    return "\n".join(L) + "\n"


def render_weights(fw: dict, cfg_json: dict, chosen: str) -> str:
    c = fw["configs"]
    L = [
        "# Phase 4 format weight sensitivity",
        "",
        NOT_OFFICIAL,
        "",
        "70:30 (IPL:T20I) remains the PROVISIONAL default (`PROVISIONAL_NOT_VALIDATED`). It is not "
        "described as optimised or validated, and no weighting is selected here. The same frozen "
        f"eligibility rules apply to all eight configurations. Definition `{chosen}` and the frozen "
        "shrinkage are held fixed; definition sensitivity is reported separately in "
        "`phase4_definition_comparison.md` and is not crossed with weights.",
        "",
        "Combined pool: players eligible in BOTH formats. A player in one format only is never "
        "zero-filled into a combination; single-format scores are reported separately below.",
        "",
        "## Eight configurations (reference = w70_30)",
        md_table(
            [
                "role",
                "config",
                "IPL w",
                "T20I w",
                "pool",
                "top-10 overlap vs 70:30",
                "top-10 size",
                "trivial full pool",
                "Spearman vs 70:30",
                "mean |rank change|",
                "max |rank change|",
                "boot exp. overlap",
                "boot mean Spearman",
                "IPL label",
                "T20I label",
            ],
            rows_of(
                c,
                [
                    "role",
                    "config_id",
                    "ipl_weight",
                    "t20i_weight",
                    "pool_size",
                    "top10_overlap_vs_default",
                    "top10_size",
                    "top10_trivial_full_pool",
                    "spearman_vs_default",
                    "mean_abs_rank_change_vs_default",
                    "max_abs_rank_change_vs_default",
                    "bootstrap_expected_top10_overlap",
                    "bootstrap_mean_spearman",
                    "ipl_eligibility_label",
                    "t20i_eligibility_label",
                ],
            ),
        ),
        "Top-10 overlap is only meaningful when the pool exceeds ten players; a pool of ten or "
        "fewer is marked trivial.",
        "",
        "## Single-format ranking stability (separate eligibility pools)",
        md_table(
            [
                "role",
                "scope",
                "label",
                "threshold",
                "pool",
                "exp. top-10 overlap",
                "mean Spearman",
                "trivial full pool",
            ],
            rows_of(
                fw["single_format"],
                [
                    "role",
                    "scope",
                    "eligibility_label",
                    "threshold_balls",
                    "pool_size",
                    "expected_top10_overlap",
                    "mean_spearman",
                    "trivial_full_pool",
                ],
            ),
        ),
        "",
        "## Pairwise Spearman between configurations (point estimates, combined pool)",
    ]
    for role, g in fw["pairwise"].groupby("role"):
        p = g.pivot(index="config_a", columns="config_b", values="spearman")
        ids = [x["id"] for x in cfg_json["configurations"]]
        p = p.reindex(index=ids, columns=ids)
        L += ["", f"### {role}", md_table(["config"] + ids, [[i] + p.loc[i].tolist() for i in ids])]
    L += [
        "",
        "## Limitations",
        "- With a small combined pool every ranking statistic is dominated by few players.",
        "- Per-format ranking scores use the primary stream only (runs for batters, runs conceded "
        "for bowlers); wickets and dismissals are in the Stage C records but not in this score.",
        "- Weights act on shrunk per-format estimates; no weighting is validated.",
    ]
    return "\n".join(L) + "\n"


def render_stability(rs: dict, chosen: str, cfg: str) -> str:
    s, p = rs["summary"], rs["players"]
    L = [
        "# Phase 4 ranking stability",
        "",
        NOT_OFFICIAL + " These are experimental ranking DISTRIBUTIONS, not published rankings.",
        "",
        f"Definition `{chosen}`, shrinkage `{cfg}`, 1,000 match-cluster bootstrap resamples (fixed "
        "seed). Pools are never padded to ten; a pool of ten or fewer is trivially its own Top 10. "
        "Eligibility labels show whether each pool rests on a selected threshold, a low-data-weight "
        "fallback or the unvalidated working pool.",
        "",
        "## Baseline configuration, by format and role",
        md_table(
            [
                "scope",
                "role",
                "label",
                "threshold",
                "pool",
                "trivial full pool",
                "exp. top-10 overlap",
                "mean Jaccard",
                "mean Spearman",
                "Spearman 2.5%",
                "97.5%",
                "pool size 2.5%",
                "97.5%",
            ],
            rows_of(
                s,
                [
                    "scope",
                    "role",
                    "eligibility_label",
                    "threshold_balls",
                    "pool_size",
                    "trivial_full_pool",
                    "expected_top10_overlap",
                    "mean_jaccard",
                    "mean_spearman",
                    "spearman_p2_5",
                    "spearman_p97_5",
                    "pool_size_p2_5",
                    "pool_size_p97_5",
                ],
            ),
        ),
        "",
        "## Player-level uncertainty (point rank, rank interval, Top-10 inclusion probability)",
    ]
    for (scope, role), g in p.groupby(["scope", "role"]):
        L += ["", f"### {scope} {role}s ({len(g)} eligible players)",
              md_table(["player_id", "point rank", "score", "rank 2.5%", "median", "97.5%",
                        "Top-10 inclusion", "balls", "matches", "n_eff"],
                       rows_of(g.head(25), ["player_id", "point_rank", "point_score", "rank_lo",
                                            "rank_median", "rank_hi", "top10_inclusion_prob",
                                            "pressure_opportunities", "distinct_matches",
                                            "effective_sample_size"]))]  # fmt: skip
    L += ["", "(First 25 players per pool; the full table is in `phase4_ranking_distributions.csv`.)",
          "", "## Changes under different eligibility thresholds",
          md_table(["scope", "role", "t", "source", "analysis t", "pool", "top-10 overlap with analysis pool",
                    "trivial", "exp. top-10 overlap (boot)", "boot Jaccard", "boot Spearman",
                    "reproducibility rho"],
                   rows_of(rs["threshold_variants"], ["scope", "role", "threshold_balls", "source",
                                                      "is_analysis_threshold", "pool_size",
                                                      "top10_overlap_with_analysis_pool",
                                                      "trivial_full_pool",
                                                      "expected_top10_overlap_bootstrap",
                                                      "bootstrap_mean_jaccard_top10",
                                                      "bootstrap_mean_spearman",
                                                      "reproducibility_spearman"])),
          "", "## Changes under different shrinkage strengths (pool fixed to the analysis pool)",
          md_table(["format", "role", "config", "pool", "top-10 overlap vs eb", "Spearman vs eb",
                    "exp. top-10 overlap (boot)", "boot Spearman", "trivial"],
                   rows_of(rs["shrinkage_variants"], ["format", "role", "shrinkage_config",
                                                      "pool_size", "top10_overlap_vs_shrink_eb",
                                                      "spearman_vs_shrink_eb",
                                                      "expected_top10_overlap_bootstrap",
                                                      "mean_bootstrap_spearman",
                                                      "top10_trivial_full_pool"])),
          "", "## Limitations",
          "- Intervals ignore uncertainty in k, the pooled target and the baseline.",
          "- Small pools make Top-10 statistics trivial or very noisy; check the trivial flag.",
          "- Rank intervals describe sampling variability of matches, not model error."]  # fmt: skip
    return "\n".join(L) + "\n"


def render_alternatives(alt: pd.DataFrame) -> str:
    L = [
        "# Phase 4 baseline alternatives (Stage D)",
        "",
        NOT_OFFICIAL,
        "",
        "Alternatives are fitted on TRAIN only and judged by VALIDATION fit and by agreement of "
        "the resulting pressure scores with B0. `B_coarse_L1` drops the wickets-remaining level, "
        "`B_coarse_L2` also drops phase, `B_no_format_offset` removes the additive format "
        "calibration offset. A season/time offset is not part of B0 and was not tested.",
        "",
        md_table(
            [
                "baseline",
                "format",
                "role",
                "VAL rows",
                "VAL mean residual",
                "VAL RMSE",
                "VAL MAE",
                "pool B0",
                "pool variant",
                "common",
                "Spearman vs B0",
                "top-10 overlap",
                "top-10 size",
                "trivial",
            ],
            rows_of(
                alt,
                [
                    "baseline",
                    "format",
                    "role",
                    "validation_rows",
                    "validation_mean_residual",
                    "validation_rmse",
                    "validation_mae",
                    "pool_size_B0",
                    "pool_size_variant",
                    "common_players",
                    "spearman_vs_B0",
                    "top10_overlap_vs_B0",
                    "top10_size",
                    "top10_trivial_full_pool",
                ],
            ),
        ),
    ]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=None)
    ap.add_argument("--skip-all-definition-scores", action="store_true")
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    rep = args.reports
    rule = df_.load_rule()
    B = int(args.n_boot or rule["n_boot"])
    seed = int(rule["seed"])
    d, _ = load_pre_test(args.store)
    lock = TestLock(rep / "phase4_lock_log.json")
    d = sc.add_signals(d, lock)
    bs = fit_baseline_set(d)

    # (1) definition ---------------------------------------------------------
    defs = df_.evaluate_definitions(d, bs, lock, rule, B)
    res = defs["candidates"]
    chosen = res.get("winner") or rule["candidates"]["leading_provisional"]
    chosen_label = (
        "PROVISIONAL rule winner" if res.get("winner")
        else "LEADING_PROVISIONAL_DEFAULT_NOT_SELECTED_BY_RULE"
    )  # fmt: skip
    table = defs["table"].copy()
    table["threshold"] = table["threshold"].astype(str)
    save(table, "phase4_definition_comparison", rep, args.store, "p4_definition_comparison")
    cdf = pd.DataFrame(res["candidates"])
    cdf.to_csv(rep / "phase4_definition_candidates.csv", index=False)
    write_p4_table(cdf, "p4_definition_candidates", args.store)
    write_json_deterministic(
        rep / "phase4_definition_selection.json",
        {"status": STATUS, "rule_sha256": defs["rule_sha256"], "selection": res,
         "carried_definition": chosen, "carried_label": chosen_label},
    )  # fmt: skip
    write_text(
        rep / "phase4_definition_comparison.md", render_definitions(defs, chosen, chosen_label)
    )

    # (2) shrinkage ----------------------------------------------------------
    _, q = sc.parse_definition(chosen)
    thr = sc.fit_thresholds(d[d["period"] == "TRAIN"], q)
    sel = sn.selection_cells(d, bs, chosen, thr, lock)
    choice = sh.choose_shrinkage(sel, B, seed)
    sh.record_choice(choice, rep / "phase4_shrinkage_choice_final.json")
    cfg = choice["chosen"]
    val_cells = {}
    for c in sel:
        role, stream, comp = c["cell"].split(":")
        if stream == en.PRIMARY[role][0]:
            val_cells[(comp, role)] = c

    # (3) eligibility --------------------------------------------------------
    cells = sn.build_cells(d, bs, chosen, thr, lock)
    fits = {k: c.fit() for k, c in cells.items()}
    gm, W = en.global_weights(d["match_id"].to_numpy(), B, seed)
    ladders = json.loads(ELIG_RULES.read_text(encoding="utf-8"))["ladders"]
    ev, decisions, cand_rows = {}, {}, []
    for key, cell in cells.items():
        comp, role = key
        e = el.evaluate_cell(
            cell, fits[key], cfg, gm, W, ladders[role]["balls"], en.PRIMARY[role][1]
        )
        ev[key], decisions[key] = e, e["decision"]
        cand_rows += [{"format": comp, "role": role, **r} for r in e["candidates"]]
    rules = sn.analysis_rules(cells, decisions)
    cand_df = pd.DataFrame(cand_rows)
    save(cand_df, "phase4_eligibility_candidates", rep, args.store, "p4_eligibility_candidates")
    frozen_rows = [
        {"format": c, "role": r, **{k: v for k, v in dec.items() if k != "alt_gate_smallest_threshold"},
         "alt_gate_smallest_threshold": json.dumps(dec["alt_gate_smallest_threshold"]),
         "analysis_threshold_balls": rules[(c, r)]["threshold_balls"],
         "analysis_label": rules[(c, r)]["label"], "analysis_window_ratio_W": rules[(c, r)]["wr"]}
        for (c, r), dec in decisions.items()
    ]  # fmt: skip
    frozen_df = pd.DataFrame(frozen_rows)
    save(frozen_df, "phase4_eligibility_frozen", rep, args.store, "p4_eligibility_frozen")
    write_text(rep / "phase4_eligibility_validation.md",
               render_eligibility(ev, decisions, rules, chosen, cfg))  # fmt: skip

    # freeze -----------------------------------------------------------------
    frozen = round_floats(
        {
            "status": STATUS,
            "official_ranking": False,
            "order_of_choices": ["definition", "shrinkage", "eligibility"],
            "definition": {
                "id": chosen,
                "label": chosen_label,
                "rule_sha256": defs["rule_sha256"],
                "winner": res.get("winner"),
                "train_only_thresholds": thr,
            },  # fmt: skip
            "shrinkage": {
                "config": cfg,
                "rule": choice.get("rule"),
                "selection_data": choice.get("selection_data"),
            },  # fmt: skip
            "eligibility": {
                f"{c}|{r}": {"decision": dec, "analysis": rules[(c, r)]}
                for (c, r), dec in decisions.items()
            },  # fmt: skip
            "baseline": {"version": bs.version, "params": bs.params},
            "split_config_sha256": file_sha256(SPLIT_CONFIG),
            "seed": seed,
            "n_boot": B,
            "test_evaluation": "NOT_RUN_IN_CHUNK3_LOCK_REMAINS_CLOSED",
        }
    )
    sha = write_frozen_choices(frozen, args.reports / FROZEN_CHOICES.name, lock)
    print("frozen choices sha256:", sha)

    # sensitivity ------------------------------------------------------------
    sens = sn.shrinkage_sensitivity(cells, fits, rules, gm, W, val_cells, B, seed)
    save(sens, "phase4_shrinkage_sensitivity", rep, args.store, "p4_shrinkage_sensitivity")
    write_text(rep / "phase4_shrinkage_sensitivity.md", render_shrinkage(sens, choice, cfg, chosen))

    wcfg = json.loads(FORMAT_WEIGHTS.read_text(encoding="utf-8"))
    fw = sn.format_weight_analysis(cells, fits, rules, gm, W, cfg, wcfg)
    save(fw["configs"], "phase4_format_weight_results", rep, args.store, "p4_format_weight_results")
    save(
        fw["pairwise"],
        "phase4_format_weight_pairwise",
        rep,
        args.store,
        "p4_format_weight_pairwise",
    )
    save(fw["players"], "phase4_format_weight_players", rep, args.store, "p4_format_weight_players")
    write_text(rep / "phase4_format_weight_sensitivity.md", render_weights(fw, wcfg, chosen))

    thr_rows = {
        k: [r for r in e["candidates"] if "marginal_data_weight" in r] for k, e in ev.items()
    }
    rs = sn.ranking_stability(cells, fits, rules, gm, W, cfg, thr_rows, sens)
    save(rs["players"], "phase4_ranking_distributions", rep, args.store, "p4_ranking_distributions")
    save(rs["summary"], "phase4_ranking_summary", rep, args.store, "p4_ranking_summary")
    save(rs["threshold_variants"], "phase4_ranking_threshold_variants", rep, args.store,
         "p4_ranking_threshold_variants")  # fmt: skip
    write_text(rep / "phase4_ranking_stability.md", render_stability(rs, chosen, cfg))

    alt = sn.baseline_alternatives(d, chosen, thr, cfg, rules, cells, lock, DEFAULT_PARAMS)
    save(alt, "phase4_baseline_alternatives", rep, args.store, "p4_baseline_alternatives")
    write_text(rep / "phase4_baseline_alternatives.md", render_alternatives(alt))

    # Stage C records under the frozen rules ---------------------------------
    elig_rules = {
        k: {"threshold_balls": r["threshold_balls"], "label": r["label"], "wr": r["wr"],
            "basis": f"PHASE4_TRAIN_DERIVED_THRESHOLD({decisions[k]['status']})"}
        for k, r in rules.items()
    }  # fmt: skip
    defs_to_score = [chosen] if args.skip_all_definition_scores else df_.definition_ids(rule)
    frames = []
    for dd in dict.fromkeys(defs_to_score):
        _, qd = sc.parse_definition(dd)
        thr_d = sc.fit_thresholds(d[d["period"] == "TRAIN"], qd)
        cfgs = list(dict.fromkeys([cfg, "shrink_none"])) if dd == chosen else [cfg]
        frames.append(sc.score_all(d, bs, dd, thr_d, cfgs, lock, n_boot=B, elig_rules=elig_rules))
    scores = pd.concat(frames, ignore_index=True)
    scores["is_carried_definition"] = scores["definition_id"] == chosen
    scores["is_leading_provisional"] = (
        scores["definition_id"] == rule["candidates"]["leading_provisional"]
    )
    sc.write_scores(scores, rep / "phase4_pressure_scores_frozen_rules.csv",
                    rep / "phase4_pressure_scores_frozen_rules.json")  # fmt: skip
    write_p4_table(scores, "p4_pressure_scores_frozen_rules", args.store)
    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("chosen definition:", chosen, chosen_label, "| shrinkage:", cfg)
    print("eligible pools:", {f"{c}|{r}": int(rs['summary'].query('scope==@c and role==@r')['pool_size'].iloc[0])
                              for (c, r) in cells})  # fmt: skip
    print("score records:", len(scores), "| official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
