"""Recommendation text and Markdown report for the pressure eligibility experiment (Stage 5).

Everything is generated from the numbers in the experiment JSON. EXPLORATORY_NOT_VALIDATED.
"""

from __future__ import annotations

from typing import Any

from app.analytics.reporting import fmt, md_table

FORMATS = ("IPL", "T20I")
ROLES = ("batter", "bowler")


def _selected(out: dict) -> dict | None:
    sid = out["selection"]["selected_id"]
    return next((d for d in out["definitions"] if d["definition"]["id"] == sid), None)


def _both(out: dict, def_id: str, role: str):
    d = next(x for x in out["definitions"] if x["definition"]["id"] == def_id)
    return d["combined_both_formats"][role]["eligible_both_formats"]


def _ladder(d: dict, fmt_: str, role: str) -> list[dict]:
    rec = d["experiment"]["recommendation_inputs"][fmt_][role]
    return rec["families"][rec["primary_family"]]["ladder"]


def provisional_recommendation(out: dict) -> dict[str, Any]:
    """PROVISIONAL recommendation, written from the numbers (never from player scores)."""
    sel = _selected(out)
    n_tot = out["selection"]["definitions_examined_in_experiment"]
    n3 = out["stage3_candidates_examined"]
    if sel is None:
        return {
            "status": "NO_DEFINITION_VIABLE",
            "selected_definition": None,
            "thresholds": None,
            "text": [
                f"No definition among the {n_tot} examined has a data-weight rule with a "
                "sufficient pool in all four format-role cells. No pressure-specific threshold "
                "is recommended and no combined list is formed."
            ],
        }
    thr: dict[str, dict] = {}
    text = [
        f"PROVISIONAL, not validated: definition {sel['definition']['id']} (context "
        f"{sel['definition']['ctx']}, quantile {sel['definition']['q']}) is one of {n_tot} "
        f"definitions run through the threshold harness, drawn from {n3} Stage 3 candidate "
        "definitions of families (a) and (b). It was chosen by the pre-declared "
        "population-level rule only (highest quantile with a sufficient pool in all four cells)."
    ]
    for f in FORMATS:
        thr[f] = {}
        for r in ROLES:
            c = sel["summary"][f][r]
            rec = c["recommended"]
            lad = {e["rule_id"]: e for e in _ladder(sel, f, r)}
            alt = c["highest_sufficient_pool_rule"]
            strict = lad.get(alt)
            thr[f][r] = {
                "rule_id": rec["rule_id"],
                "min_balls": rec["min_balls"],
                "eligible_players": rec["eligible_players"],
                "stricter_alternative_rule": alt,
                "stricter_alternative_min_balls": None if strict is None else strict["min_value"],
                "stricter_alternative_eligible": None if strict is None else strict["eligible"],
            }
            unit = "balls faced" if r == "batter" else "legal balls bowled"
            bs = rec["bootstrap"]
            text.append(
                f"{f} {r}: at least {rec['min_balls']} pressure {unit} ({rec['rule_id']}; data "
                f"outweighs the prior from about {c['required_balls_for_data_weight']:.0f}); "
                f"{rec['eligible_players']} eligible, {rec['distinct_matches']} distinct matches "
                f"({rec['match_coverage_pct']:.0f}% of the {sel['context_matches'][f]} "
                f"{sel['definition']['ctx']} matches), bootstrap expected Top 10 overlap "
                f"{bs['expected_top_k_overlap']:.1f}, Spearman versus original "
                f"{bs['spearman_vs_original_mean']:.2f}."
            )
    cb = sel["combined_both_formats"]
    for r in ROLES:
        x = cb[r]
        flag = (
            "fewer than the list size of 10: the combined list is short and is not padded"
            if x["fewer_than_list_size"]
            else "enough for a list of 10"
        )
        text.append(
            f"Eligible in both formats ({r}): {x['eligible_both_formats']}, {flag}. "
            "Single-format lists are reported separately in Stage 6."
        )
    text.append(
        "These thresholds are a floor at which the player's own pressure data outweighs the "
        "empirical-Bayes prior. They are necessary, not sufficient: interval widths and Top 10 "
        "membership frequencies above show that individual pressure residuals remain very "
        "uncertain at this sample size."
    )
    return {
        "status": "PROVISIONAL_NOT_VALIDATED",
        "selected_definition": sel["definition"],
        "thresholds": thr,
        "text": text,
        "caveats": [
            "Selected from population-level quantities only; player scores and rankings were not used.",
            "Ranking stability is reported, not used to choose.",
            "Nominal ladder rungs are placeholders scaled for pressure sample sizes, not validated.",
            "The score is actual minus expected under a FULL_SAMPLE baseline; it is not a pressure score.",
            "Eligibility is held fixed inside the bootstrap; its own sampling variability is not modelled.",
        ],
    }


# --------------------------------------------------------------------------------- rendering
def _status_block() -> str:
    return (
        "## 1. Status: exploratory proxy versus validated\n\n"
        "- **Validated numbers in this report: none.** Every figure is an exploratory calculation "
        "on the official DuckDB through the pre-delivery state table.\n"
        "- The measured stream is actual minus expected (AvE) under the Stage 4 baseline, "
        "labelled `PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE`. It exists to measure "
        "sample sufficiency, interval width and ranking stability, not to rank players.\n"
        "- No player is listed, no Top 10 is published, no model is trained, official data is "
        "unchanged. 70:30 stays a provisional default.\n"
        "- Thresholds below are provisional recommendations; approval is required before "
        "full pressure scoring.\n"
    )


def _method(out: dict) -> str:
    c = out["config"]
    g = c["definition_grid"]
    return (
        "## 2. Method\n\n"
        "1. **Pressure sample.** For each pre-declared definition (context x quantile) the "
        "Stage 3 candidate flags of IPL and T20I (each with its own per-format quantile "
        "threshold) select pressure deliveries from the base population: innings 1/2 only, "
        "no OTHER_T20, no DLS-excluded rows, no innings 3/4 (Super Over), no unverified chase "
        "targets. Batters count balls faced (wides and Penalty excluded); bowlers count "
        "deliveries bowled (Penalty excluded), threshold measure = legal balls.\n"
        f"2. **Grid.** Contexts {g['contexts']} x quantiles {g['q']} (view `{g['view']}`; batter "
        f"signal {g['batter_signal']}, bowler signal `{g['bowler_signal']}`). `any` = chase flag "
        "OR innings-1 flag at the same quantile. The grid is a search grid, not a chosen cutoff.\n"
        "3. **Baseline.** Primary: per-candidate baseline (pressure membership as the finest "
        "cell level), leave-player-out, so expectations come from peers in the same pressure "
        "band and phase/wickets/competition cell. Sensitivity: B0 without a pressure term.\n"
        "4. **Harness.** The Phase 2.5 `confidence_engine` is reused unchanged: per-(format, "
        "player, match) sufficient statistics, percentile and nominal ladders (rescaled for "
        "pressure sample sizes, `pressure_eligibility_rules_v1.json`), single-measure and "
        "balls+matches rules, bootstrap by match "
        f"({out['n_boot']} resamples, seed {c['seed']}), pool rule max({c['pool_min_absolute']}, "
        f"{c['pool_min_multiplier']} x {c['list_size']}).\n"
        "5. **Data-weight rule.** The primary rule is the lowest ladder rung at or above the "
        "number of pressure balls at which the player's data outweighs the EB prior "
        f"(weight {c['recommendation']['min_data_weight']}), with a sufficient pool. Batter and "
        "bowler, IPL and T20I are evaluated independently.\n"
        "6. **Selection of the provisional definition.** " + c["selection_rule"]["text"] + "\n"
    )


def _selection_table(out: dict) -> str:
    sel = out["selection"]
    rows = []
    for r in sel["table"]:
        e = r["eligible_by_cell"]
        rows.append(
            [
                r["id"],
                r["pressure_unit_rows_total"],
                r["cells_with_rule"],
                e["IPL|batter"],
                e["IPL|bowler"],
                e["T20I|batter"],
                e["T20I|bowler"],
                _both(out, r["id"], "batter"),
                _both(out, r["id"], "bowler"),
                r["viable"],
                r["id"] == sel["selected_id"],
            ]
        )
    head = [
        "Definition",
        "Pressure unit rows (4 cells)",
        "Cells with a rule",
        "IPL batter elig.",
        "IPL bowler elig.",
        "T20I batter elig.",
        "T20I bowler elig.",
        "Both formats batter",
        "Both formats bowler",
        "Viable",
        "Provisional",
    ]
    return (
        "## 3. Definitions examined and selection\n\n"
        f"Stage 3 candidates recomputed here: {out['stage3_candidates_examined']} "
        "(families a and b; the Stage 3 report lists 384 including 20 family-(c) break rows). "
        f"Definitions run through the full harness: {sel['definitions_examined_in_experiment']}. "
        "Blank (`n/a`) means no rule reaches the data-weight floor with a sufficient pool.\n\n"
        + md_table(head, rows)
        + f"\nViable definitions: {sel['viable_count']}. Selected: `{sel['selected_id']}` "
        "(one of the definitions examined; not validated).\n"
    )


def _populations(out: dict) -> str:
    rows = []
    for d in out["definitions"]:
        for f in FORMATS:
            for r in ROLES:
                c = d["summary"][f][r]
                rows.append(
                    [
                        d["definition"]["id"],
                        f,
                        r,
                        c["observed_players"],
                        c["pressure_unit_rows"],
                        c["pressure_matches"],
                        c["required_balls_for_data_weight"],
                        c["data_weight_rule"],
                        c["highest_sufficient_pool_rule"],
                    ]
                )
    return (
        "## 4. Pressure sample sizes by definition\n\n"
        "Observed players = players with at least one pressure delivery.\n\n"
        + md_table(
            [
                "Definition",
                "Format",
                "Role",
                "Observed players",
                "Pressure deliveries",
                "Distinct matches",
                "Balls for data weight",
                "Data-weight rule",
                "Strictest sufficient-pool rule",
            ],
            rows,
        )
    )


def _ladders(out: dict) -> str:
    sel = _selected(out)
    if sel is None:
        return "## 5. Candidate thresholds\n\nNo definition selected.\n"
    parts = [
        f"## 5. Candidate thresholds for the provisional definition `{sel['definition']['id']}`\n",
        "Balls family (batter balls faced, bowler legal balls). Percentile rungs `P` come from "
        "the observed pressure distribution; `PR` rungs are nominal and kept only between the "
        "observed p10 and p90. Eligible counts, match coverage, bootstrap Top 10 overlap and "
        "median 95% interval width (score units) per rung; `Spearman/Overlap vs next` compares "
        "neighbouring rungs.\n",
    ]
    for f in FORMATS:
        for r in ROLES:
            c = sel["summary"][f][r]
            rows = [
                [
                    e["rule_id"],
                    e["min_value"],
                    e["eligible"],
                    e["pool_sufficient"],
                    e["coverage_pct"],
                    e["expected_top_k_overlap"],
                    e["width_median"],
                    e["spearman_vs_next"],
                    e["overlap_vs_next"],
                    e["rule_id"] == c["data_weight_rule"],
                ]
                for e in _ladder(sel, f, r)
            ]
            parts.append(f"### {f} {r}\n")
            parts.append(
                md_table(
                    [
                        "Rule",
                        "Min",
                        "Eligible",
                        "Pool ok",
                        "Match coverage %",
                        "Exp. Top 10 overlap",
                        "Median CI width",
                        "Spearman vs next",
                        "Overlap vs next",
                        "Data-weight rule",
                    ],
                    rows,
                )
            )
    return "\n".join(parts)


def _recommended(out: dict) -> str:
    sel = _selected(out)
    if sel is None:
        return "## 6. Eligible populations at the recommended rules\n\nNone.\n"
    rows, unc_rows = [], []
    for f in FORMATS:
        for r in ROLES:
            c = sel["summary"][f][r]
            rec = c["recommended"]
            bs = rec["bootstrap"]
            rows.append(
                [
                    f,
                    r,
                    rec["rule_id"],
                    rec["min_balls"],
                    rec["eligible_players"],
                    rec["pressure_unit_rows"],
                    rec["distinct_matches"],
                    rec["n_eff_shrink"]["p50"],
                    rec["n_eff_shrink_total"],
                    rec["n_eff_kish"]["p50"],
                    rec["pool"]["message"],
                ]
            )
            u = sel["uncertainty"][f][r]
            unc_rows.append(
                [
                    f,
                    r,
                    bs["expected_top_k_overlap"],
                    bs["top_k_mean_membership_freq"],
                    bs["spearman_vs_original_mean"],
                    bs["spearman_vs_original_p5"],
                    u["ci_width_median"],
                    u["ci_width_p90"],
                    u["interval_excludes_zero_share"],
                ]
            )
    return (
        "## 6. Eligible populations at the recommended rules\n\n"
        + md_table(
            [
                "Format",
                "Role",
                "Rule",
                "Min balls",
                "Eligible players",
                "Pressure deliveries",
                "Distinct matches",
                "Median n_eff (shrink)",
                "Total n_eff (shrink)",
                "Median n_eff (Kish, innings-level)",
                "Pool verdict",
            ],
            rows,
        )
        + "\n### Ranking stability and uncertainty (bootstrap by match)\n\n"
        "The Top 10 columns describe how often the original Top 10 stays in the Top 10 under "
        "resampling; no player is named. Interval widths are in score units (batter: 100 x "
        "runs per ball, actual minus expected; bowler: z-composite). `Excludes zero` is the share "
        "of eligible batters whose 95% interval excludes 0.\n\n"
        + md_table(
            [
                "Format",
                "Role",
                "Expected Top 10 overlap",
                "Mean Top 10 membership freq.",
                "Spearman vs original (mean)",
                "Spearman vs original (p5)",
                "Median 95% CI width",
                "p90 CI width",
                "Excludes zero (batter)",
            ],
            unc_rows,
        )
    )


def _phase25(out: dict) -> str:
    sel = _selected(out)
    if sel is None:
        return "## 7. Comparison with Phase 2.5\n\nNone.\n"
    rows = []
    for f in FORMATS:
        for r in ROLES:
            x = sel["comparison_with_phase25"][f][r]
            rows.append(
                [
                    f,
                    r,
                    x["phase25_rule"],
                    x["phase25_min_balls"],
                    x["phase25_eligible_all_situation"],
                    x["phase25_required_balls_for_data_weight"],
                    x["players_with_pressure_sample"],
                    x["players_passing_phase25_threshold_on_pressure_samples"],
                    x["pressure_required_balls_for_data_weight"],
                    x["pressure_specific_min_balls"],
                    x["pressure_specific_eligible"],
                ]
            )
    bsen = sel.get("baseline_sensitivity_b0", {})
    brows = [
        [f, r, bsen[f][r].get("eligible"), bsen[f][r].get("spearman_b0_vs_candidate")]
        for f in FORMATS
        for r in ROLES
        if f in bsen
    ]
    return (
        "## 7. Comparison with the Phase 2.5 all-situation thresholds\n\n"
        "The Phase 2.5 thresholds were not reused: they are checked here against the pressure "
        "samples. A pressure sample is a small slice of a player's deliveries, so the "
        "all-situation floor leaves almost no player eligible.\n\n"
        + md_table(
            [
                "Format",
                "Role",
                "Phase 2.5 rule",
                "Phase 2.5 min balls",
                "Phase 2.5 eligible (all situations)",
                "Phase 2.5 balls for data weight",
                "Players with a pressure sample",
                "Pass Phase 2.5 min on pressure samples",
                "Pressure balls for data weight",
                "Pressure-specific min balls",
                "Pressure-specific eligible",
            ],
            rows,
        )
        + "\n### Baseline sensitivity (B0 versus per-candidate baseline)\n\n"
        "Spearman correlation of eligible-player scores computed from B0 residuals and from the "
        "per-candidate baseline residuals.\n\n"
        + md_table(["Format", "Role", "Eligible", "Spearman B0 vs candidate"], brows)
    )


def _recommendation(out: dict) -> str:
    rec = out["provisional_recommendation"]
    lines = ["## 8. Provisional recommendation (written after reading the results)\n"]
    lines += [f"- {t}" for t in rec["text"]]
    if rec.get("caveats"):
        lines.append("\nCaveats:\n")
        lines += [f"- {t}" for t in rec["caveats"]]
    thr = rec.get("thresholds") or {}
    sel = _selected(out)
    short = [
        f"{f} {r}" for f in FORMATS for r in ROLES if thr and thr[f][r]["eligible_players"] < 10
    ]
    short += [
        f"both formats {r}"
        for r in ROLES
        if sel and sel["combined_both_formats"][r]["fewer_than_list_size"]
    ]
    if short:
        tail = f"Fewer than ten players qualify in: {', '.join(short)}; no list is padded there."
    else:
        tail = "Every cell has at least ten eligible players."
    tail += (
        " The expected Top 10 overlap above shows that even a full list of ten would not be stable."
    )
    lines.append(
        "\nNo list of ten is forced: wherever fewer than ten players satisfy a rule the cell is "
        f"reported as insufficient and none is padded. {tail}\n"
    )
    return "\n".join(lines)


def render_report(out: dict) -> str:
    head = (
        "# Pressure-specific eligibility report (Phase 3, Stage 5, EXPLORATORY)\n\n"
        "Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication "
        "`True`. Source numbers: `pressure_threshold_experiment.json` (same directory).\n"
    )
    tail = (
        "\n## 9. Reproduce\n\n"
        "```\npython scripts/run_pressure_eligibility.py\n```\n"
        f"Config `{out['config_file']}`, seed {out['config']['seed']}, {out['n_boot']} bootstrap "
        "resamples. Official data preservation: "
        f"unchanged = {fmt(out['preservation']['official_unchanged'])}.\n"
    )
    return "\n".join(
        [
            head,
            _status_block(),
            _method(out),
            _selection_table(out),
            _populations(out),
            _ladders(out),
            _recommended(out),
            _phase25(out),
            _recommendation(out),
            tail,
        ]
    )
