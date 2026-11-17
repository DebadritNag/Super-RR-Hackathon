"""Markdown report for the pressure format-weight sensitivity (Stage 6). EXPLORATORY."""

from __future__ import annotations

from app.analytics.reporting import fmt, md_table

ROLES = ("batter", "bowler")


def _matrix(m: dict, key: str, ids: list[str]) -> str:
    rows = [[ids[i]] + m[key][i] for i in range(len(ids))]
    return md_table(["config"] + ids, rows)


def render_report(res: dict) -> str:
    L: list[str] = [
        "# Pressure format-weight sensitivity (Phase 3, Stage 6, EXPLORATORY)\n",
        "Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication "
        "`True`. Source numbers: `pressure_format_weight_sensitivity.json`.\n",
        "## 1. Status: exploratory proxy versus validated\n",
        "- **Validated numbers in this report: none.** Format scores are the shrunk "
        "actual-minus-expected proxy on pressure deliveries "
        "(`PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE`), not validated pressure scores.\n"
        f"- {res['weights_status']}. The eight configurations measure how much results move "
        "when the weighting changes.\n"
        "- No official Top 10 is published. Rankings in the JSON are technical (player ids, "
        "trimmed, no names). Nothing is imputed: a missing format score stays missing.\n",
    ]
    d = res["pressure_definition"]
    L.append("## 2. Inputs\n")
    L.append(
        f"Provisional pressure definition `{d['id']}` and thresholds from the Stage 5 "
        f"experiment ({res['threshold_source']}). Format-weight config version "
        f"`{res['config']['version']}`, config hash `{res['config_hash_all_results']}`; every "
        "ranked row in the JSON carries `config_id` and `config_hash`.\n"
    )
    rows = [
        [
            f,
            r,
            res["pressure_thresholds_min_balls"][f][r],
            res["robustness_thresholds_min_balls"]["STRICTER_highest_sufficient_pool"][f][r],
            res["robustness_thresholds_min_balls"]["LOOSER_previous_rung"][f][r],
        ]
        for f in ("IPL", "T20I")
        for r in ROLES
    ]
    L.append(
        md_table(
            ["Format", "Role", "Primary min balls", "Stricter (robustness)", "Looser (robustness)"],
            rows,
        )
    )
    L.append(
        md_table(
            ["Config", "IPL weight", "T20I weight", "Default"],
            [
                [
                    c["id"],
                    c["ipl_weight"],
                    c["t20i_weight"],
                    c["id"] == res["config"]["default_config_id"],
                ]
                for c in res["config"]["configurations"]
            ],
        )
    )
    L.append("## 3. Eligible populations and population changes\n")
    for role in ROLES:
        pc = res["population_changes"][role]
        r = res["roles"][role]
        sc = r["status_counts"]["combined_status"]
        L.append(f"### {role}\n")
        rows = [
            ["pressure primary", pc["pressure_primary"]["IPL_eligible"],
             pc["pressure_primary"]["T20I_eligible"], pc["pressure_primary"]["combined"]],
        ]  # fmt: skip
        for lab, x in pc["pressure_robustness"].items():
            rows.append([lab, x["IPL_eligible"], x["T20I_eligible"], x["combined"]])
        if "phase25_all_situation" in pc:
            a = pc["phase25_all_situation"]
            rows.append(
                [
                    f"Phase 2.5 all-situation ({a['level']})",
                    a["IPL_eligible"],
                    a["T20I_eligible"],
                    a["combined"],
                ]
            )
        L.append(
            md_table(
                ["Eligibility", "IPL eligible", "T20I eligible", "Both formats (combined)"], rows
            )
        )
        L.append(
            f"Players by combined status at the primary threshold: both formats "
            f"{sc['BOTH_FORMATS_VALID']}, IPL only {sc['SINGLE_FORMAT_IPL_ONLY']}, T20I only "
            f"{sc['SINGLE_FORMAT_T20I_ONLY']}, neither {sc['NO_VALID_FORMAT']}.\n"
        )
        if r["combined_population"] < 10:
            L.append(
                f"**Fewer than ten players ({r['combined_population']}) are eligible in both "
                "formats; the combined list is short and is not padded.**\n"
            )
    L.append("## 4. IPL-only and T20I-only results\n")
    L.append(
        "Format-specific lists are independent of the weights. Only counts are shown; trimmed "
        "technical ids are in the JSON (`format_rankings`).\n"
    )
    rows = []
    for role in ROLES:
        fr = res["roles"][role]["format_rankings"]
        rows.append([role, fr["IPL"]["n_ranked"], fr["T20I"]["n_ranked"]])
    L.append(
        md_table(["Role", "IPL-only eligible and ranked", "T20I-only eligible and ranked"], rows)
    )
    L.append("## 5. Combined results by weight configuration\n")
    for role in ROLES:
        r = res["roles"][role]
        L.append(f"### {role} (combined population {r['combined_population']})\n")
        rows = []
        for cid, e in r["configs"].items():
            mv = e["movement_vs_default"]
            rows.append(
                [
                    cid,
                    e["ipl_weight"],
                    e["t20i_weight"],
                    e["n_ranked"],
                    e["overlap_with_default"],
                    e["spearman_with_default"],
                    mv["mean_abs_change"],
                    mv["max_abs_change"],
                    len(mv["entering_top_k"]),
                    len(mv["leaving_top_k"]),
                ]
            )
        L.append(
            md_table(
                [
                    "Config",
                    "IPL w",
                    "T20I w",
                    "Ranked",
                    "Top 10 overlap vs 70:30",
                    "Spearman vs 70:30",
                    "Mean abs rank change",
                    "Max abs rank change",
                    "Entering Top 10",
                    "Leaving Top 10",
                ],
                rows,
            )
        )
        L.append(
            "Eligible population is identical across the eight configurations "
            f"({fmt(res['degenerate_populations_equal_across_configs'][role])}), including 100:0 "
            "and 0:100, which rank the same combined population by one format's z-score.\n"
        )
        pw = r["pairwise"]
        ids = pw["config_ids"]
        L.append("Pairwise Top 10 overlap:\n")
        L.append(_matrix(pw, "top_k_overlap", ids))
        L.append("Pairwise Spearman rank correlation:\n")
        L.append(_matrix(pw, "spearman", ids))
    L.append("## 6. Single-format adjusted estimates (separate section)\n")
    L.append(
        "ADJUSTED_ESTIMATE renormalises the weights over the formats in which a player is "
        "eligible. It is not a combined score, is never part of the default ranking, and is not "
        "comparable between single-format and two-format players.\n"
    )
    rows = []
    for role in ROLES:
        a = res["roles"][role]["adjusted_estimate"]
        sc = res["roles"][role]["status_counts"]["combined_status"]
        rows.append(
            [
                role,
                a["n_ranked"],
                sc["SINGLE_FORMAT_IPL_ONLY"],
                sc["SINGLE_FORMAT_T20I_ONLY"],
                sc["BOTH_FORMATS_VALID"],
            ]
        )
    L.append(
        md_table(
            ["Role", "Players with an adjusted estimate", "IPL only", "T20I only", "Both formats"],
            rows,
        )
    )
    L.append("## 7. Missing-format audit\n")
    rows = [
        [
            role,
            res["audit"][role]["players_not_in_both_formats"],
            res["audit"][role]["combined_scores_present_for_them"],
            res["audit"][role]["z_present_for_not_eligible_format"],
        ]
        for role in ROLES
    ]
    L.append(
        md_table(
            [
                "Role",
                "Players not eligible in both formats",
                "Combined scores present for them (must be 0)",
                "Z-scores present for a non-eligible format (must be 0)",
            ],
            rows,
        )
    )
    L.append(
        "\nRobustness: the same eight configurations were rerun at the stricter and looser "
        "thresholds listed in section 2; see `robustness` in the JSON.\n"
    )
    L.append(
        f"\nOfficial data preservation: unchanged = {fmt(res['preservation']['official_unchanged'])}.\n"
        "\nReproduce: `python scripts/run_pressure_eligibility.py` then "
        "`python scripts/run_pressure_format_sensitivity.py`.\n"
    )
    return "\n".join(L)
