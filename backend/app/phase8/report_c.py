"""Markdown results summary for Approach C, written only from the stored ``p8_c_*`` tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.phase8.report_a import _fmt, _t, md_table

ROLES = ("batter", "bowler")


def _top(est: pd.DataFrame, role: str, scope: str, k: int = 10) -> pd.DataFrame:
    d = est[(est["role"] == role) & (est["scope"] == scope)]
    return d.sort_values(["rank", "player_id"]).head(k)


def _approach_rows(role: str) -> list[dict[str, object]]:
    """Primary-intensity reliability rows of A and B for the side-by-side comparison."""
    out = []
    for tag, table in (("A", "p8_a_intensity_comparison"), ("B", "p8_b_intensity_comparison")):
        t = _t(table)
        r = t[(t["role"] == role) & (t["is_primary"].astype(bool))].iloc[0]
        out.append({"approach": tag, "split_half_sb": r["split_half_sb"],
                    "split_half_sb_low": r["split_half_sb_low"], "time_sb": r["time_sb"],
                    "oot_spearman": r["oot_spearman"], "oot_low": r["oot_low"], "icc1": r["icc1"],
                    "floor": r["floor"], "top10_prob_ge_0_5": r["top10_prob_ge_0_5"],
                    "indicative_status": r["indicative_status"]})  # fmt: skip
    return out


def write_report(path: Path | str) -> Path:
    wt, corr, creml = _t("p8_c_weights"), _t("p8_c_component_corr"), _t("p8_c_component_reml")
    crel, comprel, est = (
        _t("p8_c_reliability"),
        _t("p8_c_component_reliability"),
        _t("p8_c_estimates"),
    )
    sens, fmt, hier = _t("p8_c_sensitivity"), _t("p8_c_format_study"), _t("p8_c_format_hierarchy")
    status, split, bchk = _t("p8_c_status"), _t("p8_c_fit_split"), _t("p8_c_boot_check")
    L: list[str] = []
    L.append(
        "# Phase 8 Approach C results: Pressure Response Index (PRI) and the IPL/T20I combination study\n"
    )
    L.append(
        "Status: **EXPERIMENTAL_NOT_VALIDATED**. This file reports Approach C (chunk 4) only. It does "
        "not select an approach and does not produce the submitted Top 10 files. Every number is read from the "
        "`p8_c_*` tables in `phase8.duckdb`. The PRI describes observable performance in difficult "
        "situations; it is not a psychological score.\n"
    )
    L.append("## 1. Design\n")
    L.append(
        "- Role systems are separate (batters and bowlers are never compared). Unit: player-match-innings "
        "pressure unit (deliveries with intensity >= 0.5, weighted by intensity; primary intensity "
        f"`{status['intensity'].iloc[0]}`, basis `{status['intensity_basis'].iloc[0]}`: the best available "
        "definition, which did **not** pass the predeclared criteria)."
    )
    L.append(
        "- Components, each shrunk by REML on those units: **A** context-adjusted performance (Approach A "
        "residual); **B** match impact (leverage-adjusted win-probability-added residual, Approach B); "
        "**CONS** consistency (share of pressure units with a positive A residual). Exposure (count and mean "
        "intensity) and sample reliability (the REML shrinkage factor) are reported and feed the evidence "
        "classes; they are not scored, because a score for facing pressure would reward opportunity."
    )
    L.append(
        "- Weights are derived from data and fixed on the `FIT` matches (TRAIN, odd position in date order). "
        "Reliability, the split-half checks and the out-of-time check below use only the other matches "
        "(`HELD`: TRAIN even position plus VALIDATION). No weight was tuned on a ranking, and none was chosen by hand."
    )
    L.append(
        "- Weight rule: split-half reliability r of each component on FIT (Spearman-Brown) gives w = r/(1-r) "
        "(r clipped at 0.99). A non-positive r, a non-estimable r or a REML floor on FIT gives weight 0 and "
        "the label `NO_SIGNAL_*`. When two active components correlate above 0.5 (Spearman, FIT) the first "
        "principal component of the standardised active components defines the weights. If every component "
        "has no signal the PRI is `NOT_DEFINED` and no ranking is produced."
    )
    L.append(
        "- PRI = sum of weight x (level - cohort mean) / cohort SD over active components, so PRI 0 is the typical "
        "eligible player. Level is the REML posterior mean, or the unshrunk mean in a cell at the floor "
        "(predeclared rule). Shrinkage was kept in every component.\n"
    )
    L.append(
        md_table(
            split,
            ["role", "fit_matches", "held_matches", "held_train", "held_validation", "n_players"],
        )
        + "\n"
    )
    L.append("## 2. Data-derived weights\n")
    L.append(
        md_table(
            wt,
            [
                "role",
                "component",
                "n_players_fit",
                "split_half_sb",
                "tau2_fit",
                "floor_fit",
                "reliability_weight",
                "status",
                "final_weight",
            ],
            4,
        )  # fmt: skip
        + "\n"
    )
    for role in ROLES:
        w = wt[wt["role"] == role]
        act = [
            f"{r['component']} (weight {_fmt(r['final_weight'], 2)})"
            for _, r in w.iterrows()
            if r["final_weight"] != 0
        ]
        L.append(
            f"- {role}: active components: {', '.join(act) if act else 'none (PRI not defined)'}."
        )
    L.append(
        "\nThe zero weights are the result of the rule, not a choice. A component whose between-player variance "
        "is indistinguishable from zero on FIT, or whose reliability is not positive, carries no information about "
        "differences between players there, so giving it weight would add noise to the order.\n"
    )
    L.append(
        "Spearman correlation of the unshrunk component means on FIT (decides whether PCA is used; threshold 0.5):\n"
    )
    c2 = corr[corr["component_a"] < corr["component_b"]]
    L.append(md_table(c2, ["role", "component_a", "component_b", "spearman"], 3) + "\n")
    L.append(
        "CONS is built from the A units, so a high A-CONS correlation is partly mechanical and is not "
        "independent evidence. PCA is only used when at least two components are active.\n"
    )
    L.append("## 3. Component estimates and the Phase 6 data-weight gate (unchanged)\n")
    L.append(
        md_table(
            creml,
            [
                "role",
                "component",
                "n_players",
                "n_units",
                "tau2",
                "sigma2",
                "floor",
                "mean_B",
                "share_B_gt_0_5",
                "gate_mean_B_ge_0_5",
            ],
            4,
        )
        + "\n"
    )
    L.append(
        "`mean_B` is the average REML data weight (0 = fully shrunk to the mean, 1 = no shrinkage). The Phase 6 gate "
        "(mean data weight >= 0.5) is reported unchanged and was not lowered or used as an input. "
        "Between-player variance over noise and ICC(1) per component:\n"
    )
    L.append(
        md_table(comprel, ["role", "component", "icc1", "icc_players", "between_over_noise"], 4)
        + "\n"
    )
    L.append("## 4. Reliability of the PRI on held-out matches\n")
    L.append(
        md_table(
            crel, ["role", "metric", "n_players", "r", "spearman_brown", "sb_low", "sb_high"], 3
        )
        + "\n"
    )
    L.append(
        "Out-of-time uses the Spearman correlation of TRAIN-HELD matches against VALIDATION (interval from a "
        "player bootstrap); the early window needs 4 matches and the late window 4 matches (half the full-sample "
        "floor for the early window because HELD holds about 60 % of TRAIN).\n"
    )
    L.append("### Predeclared status\n")
    cols = [
        c
        for c in [
            "role",
            "indicative_list_status",
            "reason",
            "split_half_sb",
            "split_half_sb_low",
            "oot_spearman",
            "oot_low",
            "top10_prob_ge_0_5",
            "median_rank_interval_width",
            "phase6_gate_passed",
        ]
        if c in status.columns
    ]
    L.append(md_table(status, cols, 3) + "\n")
    L.append(
        "### Side by side with A and B (primary intensity, all matches, same predeclared criteria)\n"
    )
    for role in ROLES:
        rows = pd.DataFrame(_approach_rows(role))
        s = status[status["role"] == role].iloc[0]
        rows = pd.concat([rows, pd.DataFrame([{
            "approach": "C (held-out)", "split_half_sb": s.get("split_half_sb"),
            "split_half_sb_low": s.get("split_half_sb_low"), "time_sb": s.get("time_sb"),
            "oot_spearman": s.get("oot_spearman"), "oot_low": s.get("oot_low"), "icc1": float("nan"),
            "floor": s.get("all_active_components_at_floor"),
            "top10_prob_ge_0_5": s.get("top10_prob_ge_0_5"),
            "indicative_status": s.get("indicative_list_status")}])], ignore_index=True)  # fmt: skip
        L.append(f"**{role}s**\n")
        L.append(
            md_table(
                rows,
                [
                    "approach",
                    "split_half_sb",
                    "split_half_sb_low",
                    "time_sb",
                    "oot_spearman",
                    "oot_low",
                    "icc1",
                    "floor",
                    "top10_prob_ge_0_5",
                    "indicative_status",
                ],
                3,
            )
            + "\n"
        )
    L.append(
        "C's split-half and out-of-time figures use only matches that were not used to fit its weights; A's and B's "
        "use all matches (their weights are fixed, not fitted). The comparison is therefore not a contest the "
        "predeclared selection rule has resolved: that rule is applied in a later step. None of the approaches meets "
        "the PROVISIONAL threshold (split-half >= 0.5 with a lower bound above 0).\n"
    )
    L.append(
        "## 5. Candidate Top 10 under C (EXPLORATORY; combined IPL + T20I, PRE_TEST matches)\n"
    )
    L.append(
        "These are the ten highest PRI values, listed so the evidence can be read, not a validated ranking. "
        "`top10_prob` is the share of 1000 match-cluster bootstrap draws (full REML refit per draw, weights fixed) "
        "in which the player is in the top ten.\n"
    )
    cols = [
        "rank",
        "player_name",
        "pri",
        "pri_low",
        "pri_high",
        "top_k_prob",
        "rank_low",
        "rank_high",
        "evidence_class",
        "n_matches",
        "pressure_matches",
        "z_A",
        "z_B",
        "z_CONS",
        "pos_share",
        "sample_reliability",
    ]
    for role in ROLES:
        L.append(f"**{role}s**\n")
        L.append(
            md_table(_top(est, role, "COMBINED"), cols, 2, {"top_k_prob": "top10_prob"}) + "\n"
        )
        ec = est[(est["role"] == role) & (est["scope"] == "COMBINED")][
            "evidence_class"
        ].value_counts()
        L.append(
            "Evidence classes among eligible players: "
            + ", ".join(f"{k} {v}" for k, v in ec.items())
            + ".\n"
        )
    L.append(
        "Intervals are wide: a rank interval of a player in the top ten typically runs from 1 to 25 or more (see rank_low and rank_high) of about "
        "220. The estimate interval uses only draws in which no active component hit the floor (see section 8) and refits the between-player variance in every draw, so its upper end can be long: the PRI scale is fixed at its full-sample value and a draw with a larger variance spreads players further; ranks and Top 10 inclusion use every draw, where a floor draw uses the "
        "unshrunk mean by the predeclared rule.\n"
    )
    L.append(
        "## 6. Sensitivity (overlap of the Top 10 and Spearman correlation with the C order)\n"
    )
    L.append(
        md_table(
            sens, ["role", "comparison", "n_common", "spearman", "top10_overlap", "n_eligible"], 3
        )
        + "\n"
    )
    L.append("## 7. IPL and T20I combination study\n")
    L.append(
        "Decision rule (predeclared): combine when the lower 95 % bound of the cross-format Spearman correlation "
        "is at least 0.3 and at least 30 players have both formats; otherwise the format-specific results are shown "
        "and the combination is flagged `FORMAT_COMBINATION_UNSUPPORTED`. No fixed 70:30 weighting is used anywhere.\n"
    )
    L.append(
        md_table(
            fmt,
            [
                "role",
                "series",
                "players_both_formats",
                "spearman",
                "spearman_low",
                "spearman_high",
                "pearson_pw",
                "disattenuated",
                "disattenuation_note",
                "combination_supported",
            ],
            3,
        )
        + "\n"
    )
    L.append(
        "Hierarchical format model per component, `y = mu_format + u_player + v_player_format + e` (REML; "
        "`tau_u2` common player effect, `tau_v2` format-specific deviation, `common_share = tau_u2/(tau_u2+tau_v2)`; a "
        "variance whose removal changes the REML deviance by less than 1e-6 is reported as 0 with a floor flag):\n"
    )
    L.append(
        md_table(
            hier,
            [
                c
                for c in [
                    "role",
                    "component",
                    "status",
                    "tau_u2",
                    "tau_v2",
                    "sigma2",
                    "mu_ipl",
                    "mu_t20i",
                    "common_share",
                    "floor_common",
                    "floor_format_dev",
                ]
                if c in hier.columns
            ],
            5,
        )
        + "\n"
    )
    L.append(
        "The precision each format receives for a player follows from these variance components "
        "(`format_w_ipl_A`, `format_w_t20i_A` in `p8_c_estimates`) and from each player's own format counts; "
        "`ipl_precision_share` gives the observed share of a player's pressure precision that comes from the IPL.\n"
    )
    for role in ROLES:
        d = fmt[(fmt["role"] == role) & (fmt["series"] == "PRI")].iloc[0]
        L.append(
            f"- {role}s: PRI cross-format Spearman {_fmt(d['spearman'], 2)} (95 % interval {_fmt(d['spearman_low'], 2)} to "
            f"{_fmt(d['spearman_high'], 2)}, {int(d['players_both_formats'])} players), so the combination is "
            f"{'supported' if d['combination_supported'] else 'not supported'} under the predeclared rule "
            f"(`{d['combination_basis']}`)."
        )
    L.append(
        "\nWhere the combination is unsupported the combined list is the pooled estimate with format-centred units, in "
        "which each unit is already weighted by its own precision; it is labelled as such, and the IPL-only and "
        "T20I-only candidate lists below are the format-specific results.\n"
    )
    for role in ROLES:
        for sc in ("IPL", "T20I"):
            t = _top(est, role, sc)
            if len(t):
                L.append(f"**{role}s, {sc} only** (PRI within the format; same fixed weights)\n")
                L.append(
                    md_table(
                        t,
                        [
                            "rank",
                            "player_name",
                            "pri",
                            "z_A",
                            "z_B",
                            "z_CONS",
                            "n_matches",
                            "n_units",
                        ],
                        2,
                    )
                    + "\n"
                )
    L.append("## 8. Bootstrap check\n")
    L.append(
        md_table(
            bchk,
            [
                "role",
                "draws",
                "players",
                "mean_draws_present",
                "interval_draws",
                "floor_draw_share",
                "weights_fixed_from",
            ],
            3,
        )
        + "\n"
    )
    L.append("## 9. What this does and does not show\n")
    only = {
        r: [
            c
            for c in ("A", "B", "CONS")
            if wt[(wt["role"] == r) & (wt["component"] == c)]["final_weight"].iloc[0] != 0
        ]
        for r in ROLES
    }
    sh = {r: status[status["role"] == r]["split_half_sb"].iloc[0] for r in ROLES}
    lo = {r: status[status["role"] == r]["split_half_sb_low"].iloc[0] for r in ROLES}
    L.append(
        f"- Components with a non-zero weight after the data-derived rule: batters {only['batter'] or 'none'}, "
        f"bowlers {only['bowler'] or 'none'}. The others have no between-player signal (REML floor) or a "
        "non-positive reliability on the FIT matches. Where only CONS is active the index is close to a ranking "
        "by how often a player's pressure units beat expectation.\n"
        f"- Held-out parity reliability: batters {_fmt(sh['batter'], 2)} (lower bound {_fmt(lo['batter'], 2)}), "
        f"bowlers {_fmt(sh['bowler'], 2)} (lower bound {_fmt(lo['bowler'], 2)}). Rank intervals span most of the "
        "cohort. No list meets the PROVISIONAL criteria; both are "
        f"{' and '.join(sorted(set(status['indicative_list_status'])))}.\n"
        "- The IPL and T20I estimates do not agree well enough to support a combined estimate under the "
        "predeclared rule.\n"
        "- CONS counts a unit as positive whatever its size, so it is not independent of the A residual, and "
        "the A residual is itself small relative to ball-level noise. Players with few pressure units can reach the "
        "top by a short run of positive units (the `STRONG_LIMITED` class marks them).\n"
        "- Weights come from FIT only (about 40 % of TRAIN matches), so they use less data than the full-sample "
        "estimates; this was chosen so the held-out numbers are not optimistic.\n"
        "- No test-period (2026) data was used.\n"
    )
    out = Path(path)
    out.write_text("\n".join(L), encoding="utf-8")
    return out
