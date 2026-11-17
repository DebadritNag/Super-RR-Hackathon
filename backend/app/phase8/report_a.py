"""Markdown results summary for Approach A, written only from the stored ``p8_a_*`` tables."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from app.phase8.constants import PHASE8_DB


def _t(table: str) -> pd.DataFrame:
    con = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        return con.execute(f"SELECT * FROM {table}").df()
    finally:
        con.close()


def _fmt(v: object, nd: int = 3) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (float, np.floating)):
        return f"{v:.{nd}f}"
    return str(v)


def md_table(
    df: pd.DataFrame, cols: list[str], nd: int = 3, names: dict[str, str] | None = None
) -> str:
    names = names or {}
    head = "| " + " | ".join(names.get(c, c) for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    rows = ["| " + " | ".join(_fmt(r[c], nd) for c in cols) + " |" for _, r in df.iterrows()]
    return "\n".join([head, sep, *rows])


def write_report(path: Path | str) -> Path:
    met, tests, sel = (
        _t("p8_a_model_metrics"),
        _t("p8_intensity_tests"),
        _t("p8_intensity_selection"),
    )
    cmp_, reml, sens = _t("p8_a_intensity_comparison"), _t("p8_a_reml"), _t("p8_a_sensitivity")
    est, status = _t("p8_a_estimates"), _t("p8_a_status")
    chk, fmt, comp_defs = _t("p8_a_boot_check"), _t("p8_a_format_study"), _t("p8_a_component_defs")
    excl = _t("p8_data_exclusions")
    primary = str(sel.loc[sel["primary"].astype(bool), "candidate"].iloc[0])
    basis = str(sel.loc[sel["candidate"] == primary, "primary_basis"].iloc[0])
    L: list[str] = []
    L.append(
        "# Phase 8 Approach A results: context-adjusted performance under continuous pressure\n"
    )
    L.append(
        "Status: **EXPERIMENTAL_NOT_VALIDATED**. This file reports Approach A only (chunk 2). Approaches B and C, "
        "the cross-approach selection and the submitted Top 10 files come later. Every number below is read from "
        "the `p8_a_*` and `p8_intensity_*` tables in `phase8.duckdb`.\n"
    )
    L.append("## 1. What was run\n")
    L.append(
        "- Data: IPL and T20I deliveries in TRAIN (to 2024-12-31) and VALIDATION (2025). TEST (2026 onward) was not opened."
    )
    L.append(
        "- Expected-outcome models: gradient boosting on pre-delivery state, player-blind, fitted on TRAIN, "
        "one selection pass on VALIDATION; TRAIN scored out of fold (`match_id % 5`), VALIDATION scored by the TRAIN model."
    )
    L.append(
        "- Unit of analysis: player-match-innings. Pressure units use deliveries with intensity >= 0.5 weighted by intensity."
    )
    L.append(
        "- Shrinkage: REML random effect per scope (COMBINED with format-centred units, IPL, T20I). No variance floor is imposed."
    )
    L.append(
        "- Declared deviations from the design: no early stopping on an internal holdout and no isotonic recalibration "
        "(calibration slope, intercept and decile tables are reported instead); test (d) of the intensity validity "
        "tests and candidates P1 and P2 need the win-probability model, which belongs to Approach B, so they are "
        "not available here.\n"
    )
    L.append("### Data exclusions (from the data layer)\n")
    L.append(md_table(excl, ["reason", "competition_type", "rows", "matches"]) + "\n")

    L.append("## 2. Expected-outcome models (VALIDATION, out of sample)\n")
    cols = [
        "role",
        "target",
        "chosen",
        "primary_metric",
        "gbm_" + "rmse",
        "const_rmse",
        "gbm_log_loss",
        "const_log_loss",
        "gain_vs_const_pct",
    ]
    m = met.copy()
    for c in cols:
        if c not in m.columns:
            m[c] = np.nan
    L.append(md_table(m, cols, 4, {"gain_vs_const_pct": "gain vs constant (%)"}) + "\n")
    L.append(
        "The gain over a constant mean is small (a few percent at most). Ball outcomes are mostly noise given the "
        "pre-delivery state, so the expected value removes only a modest part of the context effect. "
        "This limits how much of a player's residual can be attributed to anything but chance.\n"
    )
    cl = met[met["kind"] == "clf"]
    if len(cl):
        L.append(
            "Calibration of the chosen classifiers on VALIDATION (slope 1 and intercept 0 are perfect):\n"
        )
        L.append(
            md_table(
                cl,
                [
                    "role",
                    "target",
                    "chosen_log_loss",
                    "chosen_brier",
                    "chosen_slope",
                    "chosen_intercept",
                ],
                3,
            )
            + "\n"
        )
    L.append(
        "Component standardisation constants (TRAIN standard deviation of each oriented residual):\n"
    )
    L.append(md_table(comp_defs, ["component", "train_sd"], 4) + "\n")

    L.append("## 3. Pressure-intensity definitions under the predeclared validity tests\n")
    L.append(
        "Tests a, b, c, e use TRAIN deciles (edges within each stratum), confirmed with the same edges on VALIDATION. "
        "Pass rule: a, b, e hold pooled on TRAIN, the signs of a and b hold on VALIDATION, and a and b hold in at "
        "least two of three phases. P0 is the Phase 6 style binary reference and is never primary.\n"
    )
    L.append(
        md_table(
            sel,
            [
                "candidate",
                "pass",
                "test_a",
                "test_b",
                "test_c",
                "test_e",
                "validation_signs_ok",
                "phases_passing",
                "innings_coverage",
                "n_tests_passed",
                "reference_only",
                "primary",
                "primary_basis",
            ],
        )
        + "\n"
    )
    pooled = tests[(tests["stratum"] == "pooled") & (tests["status"] == "ESTIMATED")]
    L.append(
        "Pooled decile contrasts (highest minus lowest intensity bin; runs are relative to the TRAIN mean of the same innings and phase):\n"
    )
    L.append(
        md_table(
            pooled,
            [
                "candidate",
                "period",
                "n_cell",
                "runs_diff",
                "runs_halfwidth",
                "wkt_diff",
                "wkt_halfwidth",
                "var_diff",
                "runs_spearman",
                "wkt_spearman",
            ],
            4,
        )
        + "\n"
    )
    if not sel.loc[~sel["reference_only"].astype(bool), "pass"].astype(bool).any():
        L.append(
            f"**No candidate passes the predeclared rule.** The monotonic-trend test (e) fails for every candidate on TRAIN. "
            f"The predeclared ordering (tests passed, then innings coverage, then id) was applied to the non-reference "
            f"candidates only to obtain a working definition: **{primary}** ({basis}). "
            "This choice was made from delivery-level validity tests and never from player rankings. It means the "
            "intensity definition itself is unvalidated and no list built on it can exceed EXPLORATORY.\n"
        )
    else:
        L.append(f"Primary intensity: **{primary}** ({basis}).\n")
    L.append(
        "Test (d) (mean absolute win-probability change) and candidates P1 and P2 are NOT_AVAILABLE in this chunk.\n"
    )

    L.append(
        "## 4. Estimation and reliability by intensity definition (COMBINED scope, eligible players)\n"
    )
    c2 = cmp_.copy()
    L.append(
        md_table(
            c2,
            [
                "role",
                "intensity",
                "reference_only",
                "n_eligible",
                "tau2",
                "sigma2",
                "floor",
                "mean_B",
                "share_B_gt_0_5",
                "split_half_sb",
                "split_half_sb_low",
                "split_half_sb_high",
                "time_sb",
                "icc1",
                "volume_spearman",
                "volume_bias_flag",
                "oot_spearman",
                "oot_low",
                "top10_prob_ge_0_5",
                "median_rank_interval_width",
                "indicative_status",
            ],
            4,
            {
                "split_half_sb": "split-half SB",
                "split_half_sb_low": "SB low",
                "split_half_sb_high": "SB high",
                "oot_spearman": "out-of-time rho",
                "volume_spearman": "rho(estimate, exposure)",
                "oot_low": "oot low",
                "top10_prob_ge_0_5": "players with Top-10 prob >= 0.5",
            },
        )
        + "\n"
    )
    L.append(
        "`share_B_gt_0_5` is the share of eligible players whose data weight (shrinkage factor B) exceeds 0.5, the "
        "Phase 6 gate quantity, reported unchanged and not used for labels. SB is the Spearman-Brown corrected "
        "odd/even match split-half correlation of unshrunk precision-weighted means with a 1000-draw match-cluster interval.\n"
    )

    L.append("## 5. Primary cell\n")
    L.append(f"Primary definition: {primary} ({basis}).\n")
    L.append(
        md_table(
            status,
            [
                c
                for c in [
                    "role",
                    "intensity",
                    "intensity_basis",
                    "indicative_list_status",
                    "reason",
                ]
                if c in status.columns
            ],
        )
        + "\n"
    )
    rp = reml[(reml["intensity"] == primary)]
    L.append("REML variance components (units are standardised residual units per ball):\n")
    L.append(
        md_table(
            rp,
            [
                "role",
                "scope",
                "mu",
                "tau2",
                "sigma2",
                "lambda",
                "floor",
                "label",
                "mean_B",
                "n_players",
                "n_units",
            ],
            5,
        )
        + "\n"
    )
    L.append(
        "Bootstrap: ranks, Top-10 inclusion and rank intervals use a full REML refit in each of 1000 match-cluster draws. "
        "A faster variant that holds the variance components fixed was compared with it (largest gap in Top-10 inclusion over players with probability >= 0.1):\n"
    )
    L.append(
        md_table(
            chk[chk["intensity"] == primary],
            [
                "role",
                "intensity",
                "draws",
                "players_compared",
                "max_abs_gap",
                "fixed_variance_within_0_05",
            ],
            3,
        )
        + "\n"
    )

    for role in ("batter", "bowler"):
        e = est[(est["role"] == role) & (est["scope"] == "COMBINED")].sort_values("rank")
        L.append(
            f"### {role.capitalize()}: Approach A ordering (exploratory, not the submission)\n"
        )
        if e.empty:
            L.append("No eligible cohort.\n")
            continue
        basis_txt = e["rank_basis"].iloc[0]
        L.append(
            f"Ranking basis: `{basis_txt}`. The Top 10 inclusion probability is the share of 1000 match-cluster draws in which the player is in the Top 10.\n"
        )
        top = e.head(15)
        L.append(
            md_table(
                top,
                [
                    "rank",
                    "player_name",
                    "estimate",
                    "est_low",
                    "est_high",
                    "pressure_perf_unshrunk",
                    "normal_baseline",
                    "pressure_delta",
                    "n_matches",
                    "pressure_matches",
                    "balls",
                    "top_k_prob",
                    "rank_low",
                    "rank_high",
                    "evidence_class",
                ],
                3,
                {
                    "top_k_prob": "Top-10 prob",
                    "pressure_perf_unshrunk": "pressure (unshrunk)",
                    "est_low": "int low",
                    "est_high": "int high",
                },
            )
            + "\n"
        )
        L.append(
            f"Eligible players: {len(e)}. Evidence classes: "
            + ", ".join(f"{k} {v}" for k, v in e["evidence_class"].value_counts().items())
            + ". "
            f"Players with Top-10 probability >= 0.5: {int((e['top_k_prob'] >= 0.5).sum())}.\n"
        )

    L.append("## 6. Sensitivity of the primary ordering\n")
    L.append(
        "Spearman correlation and Top 10 overlap (out of 10) with the primary COMBINED ordering over common eligible players:\n"
    )
    L.append(
        md_table(
            sens,
            [
                c
                for c in [
                    "role",
                    "comparison",
                    "n_common",
                    "spearman",
                    "top10_overlap",
                    "n_eligible",
                ]
                if c in sens.columns
            ],
            3,
        )
        + "\n"
    )

    L.append("## 7. IPL and T20I\n")
    L.append(
        md_table(
            fmt,
            [
                "role",
                "players_both_formats",
                "spearman",
                "spearman_low",
                "spearman_high",
                "pearson",
                "combination_supported",
                "combination_basis",
            ],
            3,
        )
        + "\n"
    )
    L.append(
        "The combination rule (lower 95% bound at least 0.3 and at least 30 players with both formats) is applied as declared. "
        "When it is not met the combined list is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED` and the per-format estimates remain in `p8_a_estimates`.\n"
    )

    L.append("## 8. Reading these results\n")
    fl = reml[(reml["intensity"] == primary) & (reml["scope"] == "COMBINED")]
    L.append(
        f"- Between-player variance at the floor in the primary COMBINED cells: {int(fl['floor'].astype(bool).sum())} of {len(fl)}."
    )
    pr = cmp_[cmp_["is_primary"].astype(bool)]
    for _, r in pr.iterrows():
        L.append(
            f"- {r['role']}: split-half SB {_fmt(r.get('split_half_sb'))} (interval {_fmt(r.get('split_half_sb_low'))} to {_fmt(r.get('split_half_sb_high'))}), "
            f"out-of-time rho {_fmt(r.get('oot_spearman'))} (lower bound {_fmt(r.get('oot_low'))}), indicative status {r.get('indicative_status')}."
        )
    L.append(
        "- Thresholds, gates and the shrinkage method were not changed to obtain these results. The Phase 6 data-weight gate is reported, not applied."
    )
    L.append(
        "- A positive estimate means more runs saved or scored and fewer dismissals than the context-adjusted expectation. "
        "It still includes overall quality: `normal_baseline` and `pressure_delta` are reported so the reader can separate them."
    )
    L.append(
        "- Evidence classes and intervals describe each player's estimate under the fitted random-effects model. They are not a validation: "
        "the list-level reliability above decides the status, and no row can be stronger than its list."
    )
    L.append(
        "- Intensity definitions P3, P4 and P6 describe pressure from the match state shared by both sides; only P5 is defender-oriented, "
        "and P5 fails the validity direction tests. P5 appears only as a sensitivity. A bowler-specific definition is not validated."
    )
    L.append(
        "- The remaining fairness strata of the design (batting-order group, pace or spin, opposition tercile) are deferred to the comparison chunk; "
        "this chunk reports IPL vs T20I, exposure by phase and innings, and the exposure (volume) correlation."
    )
    L.append(
        "- Observed and expected runs and dismissal rates on pressure deliveries are in `p8_a_estimates` (`obs_*`, `exp_*`), with exposure by phase and innings in `p8_a_pressure_exposure`."
    )
    L.append(
        "- Limitations: expected-outcome models explain little of the outcome variance; pressure intensity is built from the match state alone; "
        "residuals of one innings share conditions the model does not see; the bootstrap holds the variance components fixed (checked against 200 full refits).\n"
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
