"""Markdown rendering of the Stage 3 pressure distribution report (EXPLORATORY)."""

from __future__ import annotations

from typing import Any

from app.analytics.reporting import md_table

STATUS_BLOCK = """## 1. Status: what is exploratory and what is validated

- **Validated numbers in this report: none.** Every figure is an exploratory proxy calculation
  from the official DuckDB through the pre-delivery state table (`pre_delivery_state_v1`).
- Pressure is a state-based proxy (score, wickets, balls, par). It is not a validated measure of
  difficulty. No pressure category, cutoff or score is chosen here, and no player is ranked.
- Quantile thresholds are `FULL_SAMPLE` (computed over every regulation delivery in the data
  window). Par and expected-remaining-runs values are leave-one-match-out (LOMO). Both are
  descriptive and must not be used for predictive claims. A strictly-prior innings-1 par variant is
  reported separately (section 9).
- The quantile grid is a search grid, not a selection. Each candidate below is evaluated for the
  population it would select; the choice is left for the Stage 5 experiment and for approval.
- Innings 3 and 4 (six matches), OTHER_T20 matches, DLS-unreliable rows, chases whose target rests
  on an unverified innings 1 and rows with `Req <= 0` are outside every population shown.
- Official records were not changed. Cricsheet is not used.
"""

LIMITS = """## 12. Limitations (exploratory)

1. Pressure signals ignore opposition quality, pitch, weather, boundary size and real DLS resources.
2. Quantiles and par tables use the whole data window including later matches (FULL_SAMPLE/LOMO).
   Only the innings-1 par has a strictly-prior variant; strictly-prior `exp_remaining` and
   `req_to_exp` variants are not built in this chunk.
3. Deliveries inside an innings are autocorrelated. Effective sample sizes use innings (population)
   and matches (players) as clusters through the Kish formula.
4. Membership changes under the alternative wicket count `W_alt` are not recomputed per candidate in
   this chunk. The rows affected by the 12 flag disagreements are counted in section 2.
5. Family (b) conjunctions are evaluated for batters only. Bowling convention A is defined through
   the relative view only (it is the mirror of batting relative pressure).
6. Players are identified by `player_id`. No name join is used (RULE_DUPLICATE_NAMES).
"""

COLS = ["n", "mean", "p5", "p25", "p50", "p75", "p90", "p95", "p99", "max"]


def _label(k: str) -> str:
    return k.replace("|", " / ")


def _pct_table(dist: dict, keys: list[str], cols: list[str]) -> str:
    rows = []
    for k in keys:
        d = dist.get(k)
        if not d or "p50" not in d:
            continue
        rows.append([_label(k)] + [d.get(c) for c in cols])
    return md_table(["context / signal"] + cols, rows)


def _wide(effects: list[dict], ctx: str, role: str, family: str) -> str:
    comps = ["IPL", "T20I"]
    keyed: dict[tuple, dict] = {}
    for e in effects:
        if e["ctx"] == ctx and e["role"] == role and e["family"] == family:
            q = e["q"] if family != "c" else "knee"
            keyed.setdefault((e["signal"], e["view"], q), {})[e["comp"]] = e
    if not keyed:
        return "_No candidates._\n"
    heads = ["signal", "view", "q"]
    for c in comps:
        heads += [f"{c} thr", f"{c} rows", f"{c} matches", f"{c} innings", f"{c} n_eff(inn)",
                  f"{c} >=f2", f"{c} >=f2&m3"]  # fmt: skip
    rows = []
    for (sig, view, q), by in sorted(
        keyed.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][2]))
    ):
        r = [_label(sig).replace("&", " AND "), view, q]
        for c in comps:
            e = by.get(c)
            if e is None:
                r += [None] * 7
                continue
            thr = e["threshold"]
            thr = round(thr, 3) if isinstance(thr, float) else str(thr).replace("&", " AND ")
            r += [thr, e["pressure_unit_rows"], e["matches"], e["innings"],
                  round(e["n_eff_innings_kish"], 1), e["players_ge_floor2"],
                  e["players_ge_floor2_m3"]]  # fmt: skip
        rows.append(r)
    return md_table(heads, rows)


def render_report(res: dict[str, Any]) -> str:
    L: list[str] = []
    L.append("# Pressure feature distribution report (Phase 3 Stage 3, EXPLORATORY)\n")
    L.append(f"Status `{res['status']}`, official_ranking `{res['official_ranking']}`, "
             f"not_for_publication `{res['not_for_publication']}`. Generated from "
             f"`{res['provenance']['state_table']}` ({res['provenance']['state_rows']:,} rows).\n")  # fmt: skip
    L.append(STATUS_BLOCK)

    pop = res["populations"]
    L.append("## 2. Populations (actual DuckDB figures)\n")
    L.append(
        md_table(
            ["population", "rows", "matches", "innings"],
            [[k, v["rows"], v["matches"], v["innings"]] for k, v in pop["sets"].items()],
        )
    )
    L.append(md_table(["comp", "context", "rows", "matches", "innings"],
                      [[r["comp"], r["ctx"], r["rows"], r["matches"], r["innings"]]
                       for r in pop["by_comp_ctx"]]))  # fmt: skip
    L.append("Rows with a wicket-flag disagreement in the state (`state_wicket_flag_disagreement`) "
             f"inside the base population: {pop['wicket_disagreement_rows']:,}. They keep the primary "
             "`is_wicket` count; the alternative count is a sensitivity.\n")  # fmt: skip
    L.append("Exclusions from the primary populations (rows):\n")
    L.append(md_table(["reason", "rows"], [[k, v] for k, v in pop["exclusions"].items()]))
    L.append("Distinct matches and innings by season (union of the two primary populations):\n")
    L.append(md_table(["comp", "season", "rows", "innings", "matches"],
                      [[r["comp"], r["season"], r["rows"], r["innings"], r["matches"]]
                       for r in res["season_counts"]]))  # fmt: skip

    wb = res["wickets_bins"]
    L.append("## 3. Wickets-remaining bins and par/expectation tables\n")
    L.append(f"Deterministic global partition (min_cell_innings = {wb['min_cell_innings']}). Rule: "
             "merge the bin with the smallest m with the adjacent bin giving the larger combined m, "
             "ties toward Wrem 1. FULL_SAMPLE, descriptive.\n")  # fmt: skip
    L.append(md_table(["bin (Wrem)", "m (min distinct innings over the 12 cells)"],
                      [[f"{max(b)}-{min(b)}" if len(b) > 1 else str(b[0]), m]
                       for b, m in zip(wb["bins"], wb["m_per_bin"])]))  # fmt: skip
    L.append(md_table(["step", "deficient bin", "m", "merged into", "combined m"],
                      [[i + 1, str(s["deficient_bin"]), s["m"], str(s["merged"]), s["combined_m"]]
                       for i, s in enumerate(wb["merge_log"])]))  # fmt: skip
    L.append(f"`wickets_bins_failed`: {wb['wickets_bins_failed']}. The low-wicket singleton bins "
             "are empty in the powerplay cells (no innings reaches Wrem 1-4 in the powerplay), so the "
             "minimum over cells forces a coarse two-bin partition. This is reported, not tuned.\n")  # fmt: skip
    pm = res["par_meta"]
    L.append(f"Source innings for par (complete 120-ball innings 1): IPL {pm['source_innings']['IPL']}, "
             f"T20I {pm['source_innings']['T20I']} (total {res['source_innings_n']}).\n")  # fmt: skip
    L.append("`exp_cell_level_used` over all state rows (LOMO, chain E0 -> E1 -> E2 -> NONE; NONE "
             "covers OTHER_T20, innings 3/4 and rows with no balls remaining):\n")  # fmt: skip
    L.append(md_table(["level", "rows"], [[k, v] for k, v in res["exp_levels"].items()]))
    L.append(f"`shrinkage_floor_hit` at E0 rows: {res['shrinkage_floor_hit_rows']:,}; E1 parents with "
             f"the tau2 floor binding: {res['floor_hit_parents']} of {res['parents']}.\n")  # fmt: skip
    L.append("Innings-1 rows without a strictly-prior par (`par_unavailable_prior`): "
             f"{pm['par_unavailable_prior_rows']:,} (reported, never filled).\n")  # fmt: skip

    d = res["distributions"]
    L.append("## 4. Required run rate (chase) distributions\n")
    L.append("Chase population only: innings 2, valid target, `Req > 0`, not DLS-excluded. RRR is "
             "shown uncapped; the capped variant uses the observed p99 and is always shown beside "
             "it.\n")  # fmt: skip
    L.append(_pct_table(d, [f"chase|{c}|rrr" for c in ("IPL", "T20I")]
                        + [f"chase|{c}|rrr|phase={p}" for c in ("IPL", "T20I")
                           for p in ("powerplay", "middle", "death")], COLS))  # fmt: skip
    L.append(md_table(
        ["comp", "p99 cap", "uncapped mean", "capped mean", "uncapped p90", "capped p90",
         "rows above cap", "rows Brem<6", "p90 RRR (Brem>=6)"],
        [[c, v["p99_cap"], v["uncapped"]["mean"], v["capped"]["mean"], v["uncapped"]["p90"],
          v["capped"]["p90"], v["rows_above_cap"], v["rows_brem_lt_6"], v["rrr_brem_ge_6_p90"]]
         for c, v in res["rrr_cap"].items()],
    ))  # fmt: skip
    L.append("RRR histogram (chase, both formats):\n")
    L.append(md_table(["RRR from", "to", "rows", "share"],
                      [[h["lo"], "inf" if h["hi"] >= 1e8 else h["hi"], h["n"], h["share"]]
                       for h in res["rrr_hist"]]))  # fmt: skip

    L.append("## 5. Balls remaining, wickets remaining and innings phase\n")
    L.append(_pct_table(d, [f"{c}|{f}|{s}" for c in ("chase", "inn1") for f in ("IPL", "T20I")
                            for s in ("legal_balls_remaining", "wickets_remaining")], COLS))  # fmt: skip
    L.append(md_table(["context", "comp", "phase", "rows", "innings", "mean Wrem", "mean Brem"],
                      [[r["ctx"], r["comp"], r["phase"], r["rows"], r["innings"],
                        r["wickets_remaining_mean"], r["balls_remaining_mean"]]
                       for r in res["phase_table"]]))  # fmt: skip
    L.append("Wickets remaining histogram (rows, primary populations):\n")
    L.append(
        md_table(
            ["Wrem", "chase rows", "innings-1 rows"],
            [[w, v["chase"], v["inn1"]] for w, v in res["wrem_hist"].items()],
        )
    )
    L.append("Runs required versus balls remaining (chase, every third over-bin):\n")
    L.append(md_table(["comp", "Brem from", "Brem to", "rows", "Req p25", "Req p50", "Req p75",
                       "RRR p50", "RRR p90"],
                      [[r["comp"], r["balls_remaining_lo"], r["balls_remaining_hi"], r["rows"],
                        r["req_p25"], r["req_p50"], r["req_p75"], r["rrr_p50"], r["rrr_p90"]]
                       for r in res["req_by_balls"]]))  # fmt: skip
    L.append("Cell sizes behind the relative view (distinct innings per comp x phase x wickets "
             "bin):\n")  # fmt: skip
    L.append(md_table(["ctx", "comp", "phase", "wbin", "rows", "innings", "matches"],
                      [[r["ctx"], r["comp"], r["phase"], r["wbin"], r["rows"], r["innings"],
                        r["matches"]] for r in res["cell_counts"]]))  # fmt: skip

    L.append("## 6. Score relative to target or par\n")
    L.append("Chase: `req_to_exp = Req / exp_remaining` (innings-1 LOMO expectation at the same "
             "balls bin and wickets bin; near 1 means a balanced chase), `gap = RRR - CRR`, "
             "`projected_surplus`. Innings 1: `par_deviation` (LOMO), `projected_total_gap`. "
             "Signals prefixed `neg_` carry the sign used for pressure (higher = more pressure).\n")  # fmt: skip
    L.append(_pct_table(d, [f"chase|{c}|{s}" for c in ("IPL", "T20I")
                            for s in ("req_to_exp", "gap", "projected_surplus", "runs_required",
                                      "neg_resource_ratio")]
                        + [f"inn1|{c}|{s}" for c in ("IPL", "T20I")
                           for s in ("neg_par_dev", "neg_proj_gap", "neg_resource_ratio")],
                        COLS))  # fmt: skip
    L.append("Zero or boundary inflation (share of rows at the signal minimum; config threshold "
             f"{res['zero_inflation_share']}):\n")  # fmt: skip
    L.append(md_table(["context / signal", "share at min", "min", "above threshold"],
                      [[_label(k), v["share_at_min"], v["min"],
                        v["share_at_min"] > res["zero_inflation_share"]]
                       for k, v in d.items() if "share_at_min" in v and "phase=" not in k
                       and not k.endswith("wickets_remaining")
                       and not k.endswith("legal_balls_remaining")]))  # fmt: skip

    L.append("## 7. Candidate thresholds from the observed distributions\n")
    L.append("Family (a) absolute thresholds at the quantile grid. Quantiles are per competition type "
             "within the context (chase or innings 1). This is the search grid, not a selection.\n")  # fmt: skip
    L.append(md_table(["ctx", "comp", "signal"] + [f"q={q}" for q in res["grid"]],
                      [[r["ctx"], r["comp"], r["signal"]] + [r["thr"].get(str(q)) for q in res["grid"]]
                       for r in res["threshold_grid"]]))  # fmt: skip
    L.append("Family (c) data-derived breaks (knee of the cumulative curve; reproducible only when the "
             f"quantile positions agree within {res['break_tol']}):\n")  # fmt: skip
    L.append(md_table(
        ["ctx", "signal", "IPL knee value", "IPL q-position", "T20I knee value", "T20I q-position",
         "IPL zero-inflated", "T20I zero-inflated", "reproduced IPL/T20I", "reproduced LOMO/prior",
         "usable"],
        [[b["ctx"], b["signal"], b["per_comp"]["IPL"].get("value"),
          b["per_comp"]["IPL"].get("quantile_position"), b["per_comp"]["T20I"].get("value"),
          b["per_comp"]["T20I"].get("quantile_position"), b["per_comp"]["IPL"].get("zero_inflated"),
          b["per_comp"]["T20I"].get("zero_inflated"), b["reproduced_across_ipl_t20i"],
          b["reproduced_lomo_vs_prior"], b["usable_candidate"]] for b in res["breaks"]],
    ))  # fmt: skip

    L.append("## 8. Effect of each candidate on the eligible player population\n")
    L.append(f"{res['n_candidates']} candidate definitions were examined (family a: "
             f"{res['n_family']['a']}, family b: {res['n_family']['b']}, family c reproducible "
             f"breaks: {res['n_family']['c']}). Columns: threshold, pressure rows (batter: balls "
             "faced; bowler: deliveries including wides and no-balls), distinct matches, distinct "
             "innings, Kish effective size over innings, players with at least floor 2 and with "
             "floor 2 plus 3 matches. Floors come from the Phase 2.5 ladders (batter balls 30/60, "
             "bowler legal balls 24/48, matches 3/5), not invented. They are provisional reference "
             "points until Stage 5 recalculates pressure-specific thresholds. The full table "
             "(floor 1, 5 matches, per-player n_eff) is in `pressure_distribution_report.json`.\n")  # fmt: skip
    for ctx in ("chase", "inn1"):
        for role in ("batter", "bowler"):
            for fam in ("a", "b", "c"):
                tbl = _wide(res["effects"], ctx, role, fam)
                if tbl.startswith("_No"):
                    continue
                L.append(f"### 8.{ctx}.{role}.family-{fam}\n")
                L.append(tbl)
    L.append("### Opportunity counts per player for representative candidates\n")
    L.append("Mechanical illustration at q = 0.75 and 0.90 of the primary signals, not a candidate "
             "selection. Players are counted by `player_id`.\n")  # fmt: skip
    L.append(md_table(
        ["candidate", "role", "players", "measure p10", "p25", "p50", "p75", "p90", "max",
         "n_eff_kish p50", "n_eff_kish p90", "matches p50"],
        [[_label(r["id"]), r["role"], r["players"], r["p10"], r["p25"], r["p50"], r["p75"],
          r["p90"], r["max"], r["neff_p50"], r["neff_p90"], r["matches_p50"]]
         for r in res["opportunity_dist"]],
    ))  # fmt: skip

    L.append("## 9. Strictly-prior versus LOMO innings-1 par\n")
    L.append(f"Strictly prior needs at least {res['min_prior_innings']} earlier source innings. "
             "Early-window rows have no value and are never filled.\n")  # fmt: skip
    L.append(md_table(
        ["comp", "q", "LOMO thr", "LOMO rows", "LOMO matches", "LOMO innings", "prior thr",
         "prior rows", "prior matches", "prior innings", "prior population rows",
         "LOMO population rows"],
        [[r["comp"], r["q"], r["lomo_threshold"], r["lomo_rows"], r["lomo_matches"],
          r["lomo_innings"], r["prior_threshold"], r["prior_rows"], r["prior_matches"],
          r["prior_innings"], r["prior_population_rows"], r["lomo_population_rows"]]
         for r in res["prior_vs_lomo"]],
    ))  # fmt: skip

    L.append("## 10. Independent cross-check\n")
    sc = res["spot_check"]
    L.append(f"Candidate `{_label(sc['candidate'])}` recomputed with a separate DuckDB SQL "
             "implementation (population filter, quantile_cont, counts) and compared with the "
             "pandas engine:\n")  # fmt: skip
    L.append(
        md_table(
            ["quantity", "engine", "independent SQL", "match"],
            [[k, v["engine"], v["sql"], v["match"]] for k, v in sc["checks"].items()],
        )
    )
    L.append("## 11. Interpretation\n")
    L.append("- The chase RRR distribution is right-skewed; its upper tail consists of rows with few "
             "balls left, so RRR is reported with `Brem` and uncapped/capped. A death-over chase is "
             "not high pressure by label alone; the relative view compares it with other death-over "
             "chases.\n"
             "- Candidate populations shrink quickly as q grows. The section 8 tables show where the "
             "batter and bowler pools fall below ten players at each floor.\n"
             "- Nothing here selects a definition. Stage 5 reads these populations, bootstraps by "
             "match and states which definitions are defensible.\n")  # fmt: skip
    L.append(LIMITS)
    return "\n".join(L)
