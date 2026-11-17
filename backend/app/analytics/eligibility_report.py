"""Markdown rendering of the eligibility experiment. Every number comes from the JSON dicts."""

from __future__ import annotations

from app.analytics.reporting import INTERPRETATION, fmt, md_table

DIRECTION = (
    "Direction of change under pressure samples: a pressure sample is a subset of the "
    "all-situation sample, so every player has fewer balls, matches and innings in it. A fixed "
    "count threshold will therefore admit fewer players, eligible pools will be smaller, "
    "match coverage lower, and bootstrap intervals wider and Top 10 membership less stable than "
    "shown here. The figures below are upper bounds in direction only. No pressure-sample "
    "numbers are extrapolated."
)

FAMILY_TITLES = {
    "balls": "balls (batter balls faced / bowler legal balls)",
    "matches": "distinct matches",
    "innings": "innings batted / bowled in",
    "n_eff_shrink": "effective sample size (shrinkage)",
    "n_eff_kish": "effective number of matches (Kish)",
    "balls+matches": "balls AND matches",
}


def _rule_rows(rules: list[dict], family: str) -> list[list]:
    rows = []
    for r in rules:
        if r["family"] != family:
            continue
        b, ss = r["bootstrap"], r["sample_size_distribution"]["balls"]
        vn, vr = r["vs_next"], r["vs_reference"]
        rows.append(
            [
                r["label"],
                " AND ".join(f"{c['measure']}>={c['min']}" for c in r["clauses"]),
                r["eligible"],
                r["match_coverage"]["matches_covered"],
                r["match_coverage"]["coverage_pct"],
                ss.get("p50"),
                (f"{vn['overlap']}" if vn else "n/a"),
                (vn["spearman"]["rho"] if vn else None),
                f"{vr['overlap']}",
                vr["spearman"]["rho"],
                b.get("interval_width_median"),
                b.get("top_k_mean_membership_freq"),
                b.get("spearman_vs_original_mean"),
                "SUFFICIENT" if r["pool"]["sufficient"] else "INSUFFICIENT",
            ]
        )
    return rows


HEADERS = [
    "Rule",
    "Clauses",
    "Eligible",
    "Matches covered",
    "Coverage %",
    "Median balls",
    "Top10 overlap vs next",
    "Spearman vs next",
    "Top10 overlap vs ref",
    "Spearman vs ref",
    "Median 95% CI width",
    "Top10 mean membership",
    "Boot Spearman",
    "Pool",
]


def render_report(dist: dict, exp: dict) -> str:
    cfg = exp["rules"]
    L: list[str] = ["# Eligibility Threshold Report (Decision 2)", ""]
    L += ["## 1. Interpretation (read first)", "", INTERPRETATION, "", DIRECTION, ""]
    L += [
        "- proxy_run: true; pressure_status: PENDING_PHASE3; score_label: PROXY_NOT_PRESSURE; "
        "not_for_publication: true.",
        f"- Seed {cfg['seed']}, {exp['n_boot']} bootstrap resamples, rules `{exp['rules_version']}`.",
        "- Batter and bowler eligibility are independent. Combined eligibility means eligible in "
        "both IPL and T20I.",
        "- Spearman and Top 10 overlap versus neighbours use scores re-estimated inside each "
        "eligible pool, because population-level scores would give a trivial Spearman of 1.",
        "- Bootstrap intervals describe shrunk scores. Low-sample players are pulled toward the "
        "prior, so their intervals understate uncertainty about true skill and interval width "
        "does not fall with the threshold. Width is a diagnostic only.",
        "- Primary recommendation rule: the lowest balls rule at or above the sample size where "
        "a player's data outweighs the shrinkage prior (data weight "
        f"{cfg['recommendation']['min_data_weight']}) and the pool is sufficient. The generic "
        "stability checks (Spearman, Top 10 overlap, width plateau) are reported as diagnostics.",
        "",
        "## 2. PROVISIONAL recommendation",
        "",
    ]
    for f, lines in exp["narrative"].items():
        L += [f"- {x}" for x in lines]
    L += [
        "",
        "These are provisional and rest on all-situation proxies. Pool size, noise and match "
        "coverage trade off against each other; the tables in section 4 show how Top 10 "
        "stability and interval width change with the threshold. Where a list would have fewer than "
        f"{cfg['list_size']} eligible players it is reported as such and never padded.",
        "",
        "## 3. Data window and distributions",
        "",
    ]
    L.append(
        md_table(
            ["Format", "Matches with deliveries", "First date", "Last date"],
            [
                [f, w["matches_with_deliveries"], w["first_date"], w["last_date"]]
                for f, w in dist["window"].items()
            ],
        )
    )
    prior_rows = []
    for f, roles in dist["formats"].items():
        for role, d in roles.items():
            for stream, p in d["prior_parameters"].items():
                prior_rows.append(
                    [f, role, stream, p["players"], p["mu0"], p["sigma2"], p["tau2"], p["k"]]
                )
    L += [
        "Shrinkage prior per format, role and stream (k is the prior strength in the stream's "
        "unit; a player's data weight is n/(n+k)):",
        "",
        md_table(["Format", "Role", "Stream", "Players", "mu0", "sigma2", "tau2", "k"], prior_rows),
    ]
    for f, roles in dist["formats"].items():
        for role, d in roles.items():
            L += [f"### {f} {role}: observed players {d['observed_players']:,}", ""]
            rows = []
            for m, v in d["measures"].items():
                s = v["summary"]
                rows.append(
                    [m, s["count"], s["mean"], s["min"], s.get("p10"), s.get("p25"),
                     s.get("p50"), s.get("p75"), s.get("p90"), s["max"]]
                )  # fmt: skip
            L.append(
                md_table(
                    ["Measure", "n", "Mean", "Min", "p10", "p25", "p50", "p75", "p90", "Max"],
                    rows,
                )
            )
            z = d["zero_inflation"]
            L += [
                f"Players with at most 5 balls: {z['balls_le_5']}; single-match players: "
                f"{z['single_match_players']} ({fmt(z['single_match_share'], 3)}).",
                "",
            ]
    L += ["## 4. Candidate thresholds and results", ""]
    for f, roles in exp["formats"].items():
        for role, res in roles.items():
            L += [f"### {f} {role}", ""]
            for m, c in res["candidates"].items():
                pcs = ", ".join(f"{p['label']}={p['value']}" for p in c["percentile"])
                L.append(f"- {m}: percentile candidates {pcs}.")
                for p in c["practical"]:
                    state = "kept" if p["kept"] else f"dropped ({p['drop_reason']})"
                    L.append(f"  - {p['value']} {state}: {p['justification']}.")
            L.append("")
            for fam in (
                "balls",
                "matches",
                "innings",
                "n_eff_shrink",
                "n_eff_kish",
                "balls+matches",
            ):
                rows = _rule_rows(res["rules"], fam)
                if rows:
                    L += [f"#### {f} {role}: {FAMILY_TITLES[fam]}", "", md_table(HEADERS, rows)]
            rec = exp["recommendation_inputs"][f][role]["families"][
                cfg["recommendation"]["primary_family"]
            ]
            L += [
                f"Recommendation inputs ({f} {role}, primary family): lowest stable rule "
                f"{rec['lowest_stable_rule']}, strictest sufficient pool "
                f"{rec['highest_sufficient_pool_rule']}.",
                "",
            ]
    L += ["## 5. Combined eligibility (eligible in IPL and T20I)", ""]
    for role, comb in exp["combined"].items():
        L += [f"### {role}", ""]
        L.append(
            md_table(
                ["Rule", "Eligible in both", "Pool"],
                [
                    [rid, v["eligible_both_formats"], v["pool"]["message"]]
                    for rid, v in comb.items()
                ],
            )
        )
    L += [
        "## 6. Technical appendix (proxy, flagged PROXY_NOT_PRESSURE)",
        "",
        "Top proxy scores at the reference rule with bootstrap 95% intervals. These are not "
        "recommendations and not pressure rankings.",
        "",
    ]
    for f, roles in exp["technical_appendix"].items():
        for role, a in roles.items():
            L += [f"### {f} {role} (reference rule {a['reference_rule']})", ""]
            L.append(
                md_table(
                    ["player_id", "name", "proxy score", "CI low", "CI high", "Top10 freq", "flag"],
                    [
                        [
                            p["player_id"],
                            p["name"],
                            p["proxy_score"],
                            p["ci95_low"],
                            p["ci95_high"],
                            p["top_k_freq"],
                            p["flag"],
                        ]
                        for p in a["players"]
                    ],
                )  # fmt: skip
            )
    return "\n".join(L) + "\n"
