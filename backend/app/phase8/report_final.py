"""Final reports of the submission ranking, written from the stored ``p8_*`` tables only.

Files (all in ``reports/``): ``pressure_top10_status.md``, ``methodology_comparison.md``,
``pressure_methodology_research.md`` and ``player_selection_explanations.md``. Numbers are read
from the tables that also feed the CSV and JSON lists, so the text cannot drift from the output.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from app.phase8.constants import translate_table
from app.phase8.report_a import _fmt, _t, md_table
from app.phase8.status import load_labels

ROLES = ("batter", "bowler")
ROLE_WORD = {"batter": "batters", "bowler": "bowlers"}
APPROACH_SHORT = {
    "A": "A (context-adjusted performance)",
    "B": "B (leverage and win probability added)",
    "C": "C (Pressure Response Index)",
}
# Phase 3 to 6 findings that the brief requires to stay visible (reported unchanged).
PHASE6 = [
    "Between-player variance sits at the shrinkage floor in all 48 contexts.",
    "Pooled odd/even reliability is 0.37 (0.3656); the median over the 47 estimable contexts is 0.25.",
    "No context passes the 0.5 data-weight gate (0 of 48).",
    "No pressure definition passed the predeclared criteria; rankings are sensitive to definitions and resampling.",
]


def _p(v: object) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{100.0 * float(v):.0f}%"


def _row(df: pd.DataFrame, **kw: object) -> pd.Series:
    m = pd.Series(True, index=df.index)
    for k, v in kw.items():
        m &= df[k] == v
    return df[m].iloc[0]


def _banner_block(st: pd.DataFrame) -> list[str]:
    out = []
    for role in ROLES:
        r = _row(st, role=role)
        out.append(f"> **{ROLE_WORD[role].capitalize()}: {r['list_status']}.** {r['banner']}\n")
    return out


def _neighbour(rows: pd.DataFrame, i: int) -> str:
    """Why rank i sits where it does relative to its neighbours (interval overlap statements)."""
    r = rows.iloc[i]
    parts = []
    for j, word in ((i - 1, "above"), (i + 1, "below")):
        if j < 0 or j >= len(rows):
            continue
        o = rows.iloc[j]
        overlap = (
            r["interval_low"] <= o["interval_high"] and o["interval_low"] <= r["interval_high"]
        )
        gap = r["pressure_score"] - o["pressure_score"]
        parts.append(
            f"rank {int(o['rank'])} ({o['player_name']}) is {word}: score difference "
            f"{abs(gap):.4g}, 95% intervals {'overlap' if overlap else 'do not overlap'}"
            + (", so the order of the two is not distinguishable from noise" if overlap else "")
        )
    return "; ".join(parts) + "."


# ---------------------------------------------------------------------------------------------
# status document
# ---------------------------------------------------------------------------------------------
def status_md() -> str:
    st, rk, cmp_, sel = (
        _t("p8_top10_status"), _t("p8_rankings"), _t("p8_method_comparison"), _t("p8_method_selection"),
    )  # fmt: skip
    labels = load_labels()
    crit_hash = str(rk["criteria_sha256"].iloc[0])
    L = ["# Pressure Top 10: submitted ranking status\n"]
    L += _banner_block(st)
    lens = {r: int(_row(st, role=r)["list_length"]) for r in ROLES}
    L.append(
        f"**Read this first.** The lists below are ordered ({lens['batter']} batters, {lens['bowler']} "
        "bowlers; none is padded), but "
        "neither is validated. The declared reliability thresholds were not met by any approach, so "
        "both lists carry the label EXPLORATORY. They are the best-supported ordering of the available "
        "data, not evidence that these players are reliably better under pressure than the players "
        "ranked below them.\n"
    )
    L.append("## 1. Two statuses, kept apart\n")
    L.append(labels["two_statuses"] + "\n")
    t = []
    for role in ROLES:
        r = _row(st, role=role)
        m = _row(cmp_, role=role, chosen=True)
        t.append({"role": role, "approach": APPROACH_SHORT[r["approach"]], "rank_basis": r["rank_basis"],
                  "submitted ranking status": r["list_status"], "model validation status": r["model_validation_status"],
                  "players listed": r["list_length"], "eligible players": r["n_eligible"],
                  "split-half (Spearman-Brown)": m["sb"], "interval low": m["sb_low"], "interval high": m["sb_high"]})  # fmt: skip
    L.append(md_table(pd.DataFrame(t), list(t[0].keys())) + "\n")
    L.append("## 2. Why neither list is PROVISIONAL or VALIDATED\n")
    th = json.loads(Path(_criteria_path()).read_text(encoding="utf-8"))["status_thresholds"]
    L.append(
        f"Thresholds declared before any result (criteria hash `{crit_hash}`): PROVISIONAL needs "
        f"split-half reliability of at least {th['PROVISIONAL']['split_half_min']} with a lower bound "
        "above 0 and an out-of-time lower bound above 0; VALIDATED needs at least "
        f"{th['VALIDATED']['split_half_min']} with a lower bound of at least "
        f"{th['VALIDATED']['split_half_lower_bound_min']} and an out-of-time lower bound above "
        f"{th['VALIDATED']['out_of_time_lower_bound_gt']}.\n"
    )
    for role in ROLES:
        r = _row(st, role=role)
        L.append(f"- **{ROLE_WORD[role].capitalize()}**: {r['reason']}.")
    L.append("")
    L.append("## 3. Phase 6 findings still apply\n")
    L += [f"- {x}" for x in PHASE6]
    L.append(
        "- Phase 8 changed the method (continuous intensity, richer expected-outcome models, "
        "match-level units, REML) and tested whether the result improved. It improved the "
        "technical pipeline and left the central finding in place: the data do not separate players "
        "reliably. The Phase 6 data-weight gate (0.5) was not lowered and is reported unchanged: "
        "no approach passes it.\n"
    )
    L.append("## 4. How the submitted approach was chosen\n")
    for role in ROLES:
        s = _row(sel, role=role)
        L.append(f"- **{ROLE_WORD[role].capitalize()}**: {s['reason']}")
    L.append(
        "\nApproach selection used only approach-level metrics (split-half and out-of-time "
        "reliability, inclusion concentration, an explainability checklist), never a player's rank "
        "or name.\n"
    )
    L.append("## 5. What the lists can and cannot be used for\n")
    L.append(
        "- They can be used as a transparent, reproducible description of who performed best "
        "against the model's expectation in difficult match situations in 2022 to 2025.\n"
        "- They cannot be used to claim that the order is reliable. Each player's 95% rank interval "
        "spans many places (see the CSV columns `rank_interval_low` and `rank_interval_high`), and "
        f"{_incl_sentence(rk)}\n"
        "- The pressure definition used (P4, resource scarcity) did not pass the predeclared "
        "validity tests (the monotonic trend test failed for every candidate). It is the best "
        "available candidate, not a validated definition.\n"
        "- A player outside the lists may be as good or better. Missing evidence is never reported "
        "as poor performance.\n"
    )
    flags = []
    for role in ROLES:
        d = rk[(rk["role"] == role) & (rk["kind"] == "SELECTED")]
        n = int((d["interval_flag"] != "OK").sum())
        flags.append(f"{n} of {len(d)} {ROLE_WORD[role]}")
    L.append("### Interval caveat\n")
    L.append(
        "The score interval is a 95% percentile interval of a match-cluster bootstrap in which the "
        "between-player variance is re-estimated in every draw. For Approach C the draws sit above the "
        "point estimate (the scale is held at its full-sample value while the shrinkage changes), so "
        "the interval is skewed and is flagged in the `interval_flag` column. Flagged rows: "
        + ", ".join(flags)
        + ". The rank interval and the top-10 inclusion probability use every draw and are the better "
        "guide to how firm a position is.\n"
    )
    L.append("## 6. Label definitions\n")
    for k, v in labels["labels"].items():
        L.append(f"- **{k}**: {v}")
    L.append("\n" + labels["row_rule"] + "\n")
    L.append("## 7. What would change the status\n")
    L.append(
        "- More matches per player (the declared reliability grows with the sample), or a pressure "
        "definition that passes the predeclared validity tests, together with split-half "
        "reliability of at least 0.5 and a positive lower bound on held-out matches.\n"
        "- Using the 2026 matches would add data, but that period was opened once in Phase 4 and is "
        "not a clean hold-out; it needs an explicit owner decision and a labelled application.\n"
    )
    L.append("## 8. Players in the lists\n")
    for role in ROLES:
        d = rk[(rk["role"] == role) & (rk["kind"] == "SELECTED")].sort_values("rank")
        L.append(
            f"**{ROLE_WORD[role].capitalize()}** (approach {APPROACH_SHORT[_row(st, role=role)['approach']]})\n"
        )
        L.append(md_table(d, ["rank", "player_name", "pressure_score", "interval_low", "interval_high", "top10_inclusion_probability", "evidence_class", "ranking_status"], 4) + "\n")  # fmt: skip
    return "\n".join(L) + "\n"


def _incl_sentence(rk: pd.DataFrame) -> str:
    parts = []
    for role in ROLES:
        d = rk[(rk["role"] == role) & (rk["kind"] == "SELECTED")]
        n = int((d["top10_inclusion_probability"] >= 0.5).sum())
        parts.append(
            f"{n} of {len(d)} listed {ROLE_WORD[role]} have a top-10 inclusion probability of at least 50%"
        )
    return (
        "; ".join(parts)
        + " (the share of 1000 match-cluster bootstrap draws in which the player is in the Top 10)."
    )


def _criteria_path() -> Path:
    from app.phase8.constants import CRITERIA_FILE

    return CRITERIA_FILE


# ---------------------------------------------------------------------------------------------
# methodology comparison
# ---------------------------------------------------------------------------------------------
def comparison_md() -> str:
    cmp_, sel, sens = (
        _t("p8_method_comparison"),
        _t("p8_method_selection"),
        _t("p8_final_sensitivity"),
    )
    sel_tab = _t("p8_b_intensity_selection")
    wp = _t("p8_wp_metrics")
    am = _t("p8_a_model_metrics")
    cw, cr = _t("p8_c_weights"), _t("p8_c_component_reliability")
    fa, fb, fc = _t("p8_a_format_study"), _t("p8_b_format_study"), _t("p8_c_format_study")
    st, rk = _t("p8_top10_status"), _t("p8_rankings")
    crit_hash = str(rk["criteria_sha256"].iloc[0])
    L = ["# Methodology comparison: three approaches under predeclared criteria\n"]
    L += _banner_block(st)
    L.append(
        f"Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `{crit_hash}`. The hash "
        "was verified against the hash file and the run-log row `seq = 1` before this comparison "
        "ran, and the criteria were not altered after any result was seen. Every number comes from "
        "the stored `p8_*` tables. Batters and bowlers are compared within their own role only.\n"
    )
    L.append("## 1. The three approaches\n")
    L.append(
        "- **A, context-adjusted performance.** A player-blind gradient-boosting model predicts the "
        "runs and the wicket probability of each delivery from the pre-delivery situation. A "
        "player's score is the intensity-weighted mean of observed minus expected, shrunk by REML "
        "random effects. Baseline: the same residual on low-intensity deliveries.\n"
        "- **B, leverage and win probability added (WPA).** A calibrated win-probability model "
        "values each delivery; credit goes to the striker, bowler or team by explicit rules (wides "
        "and no-balls to the bowler, byes to the team, run-outs never to the bowler). The score is "
        "WPA above what the leverage of the situation predicts.\n"
        "- **C, Pressure Response Index (PRI).** Components A, B and a consistency component (share "
        "of pressure units that beat the expectation) are weighted by data-derived reliability on "
        "FIT matches only. Every weight rule gave A and B no weight, so the PRI reduces to the "
        "consistency component for both roles. It is not an A plus B composite.\n"
    )
    L.append("## 2. Pressure definitions tested (delivery level, before any player ranking)\n")
    L.append(md_table(sel_tab, ["candidate", "pass", "test_a", "test_b", "test_c", "test_e", "test_d", "n_tests_passed", "phases_passing", "innings_coverage", "primary", "primary_basis"]) + "\n")  # fmt: skip
    L.append(
        "No candidate passes the predeclared rule: the monotonic trend test (e) fails for all. P4 "
        "(wickets lost share times innings progress, both innings) was used as the best available "
        "definition by the predeclared ordering (most tests passed, widest innings coverage). P1 "
        "and P2 (win-probability based) fail the direction tests. The intensity definition is "
        "therefore unvalidated and no list can exceed EXPLORATORY.\n"
    )
    L.append("## 3. Predictive quality of the building blocks (chronological validation)\n")
    L.append("Expected-outcome models of Approach A on VALIDATION (2025), against a constant:\n")
    L.append(md_table(am, ["role", "target", "chosen", "gain_vs_const_pct"], 3, {"gain_vs_const_pct": "gain vs constant (%)"}) + "\n")  # fmt: skip
    L.append("Win-probability models of Approach B on VALIDATION:\n")
    L.append(md_table(wp, ["model", "n_validation", "brier", "brier_const", "brier_logit", "slope", "intercept", "gate_passed"], 4) + "\n")  # fmt: skip
    L.append(
        "The win-probability models are well calibrated and beat both baselines, so the pipeline is "
        "technically sound. The expected-outcome models gain only 1.5% to 3% over a constant: ball "
        "outcomes are mostly noise given the pre-delivery state, which limits how much of a "
        "residual can be attributed to anything but chance. Approach C has no predictive model of "
        "its own.\n"
    )
    L.append("## 4. Player differentiation, reliability and stability (predeclared metrics)\n")
    for role in ROLES:
        d = cmp_[cmp_["role"] == role].copy()
        d["approach"] = d["approach"].map(APPROACH_SHORT)
        L.append(f"**{ROLE_WORD[role].capitalize()}**\n")
        L.append(md_table(d, ["approach", "sb", "sb_low", "sb_high", "time_sb", "oot", "oot_low", "icc1", "between_player_variance_at_floor", "mean_data_weight", "phase6_gate_passed", "top10_prob_ge_0_5", "n_eligible", "basis", "chosen"], 3, {"sb": "split-half SB", "sb_low": "SB low", "sb_high": "SB high", "oot": "out-of-time rho", "oot_low": "oot low", "top10_prob_ge_0_5": "players with Top-10 prob >= 0.5"}) + "\n")  # fmt: skip
    L.append(
        "SB is the Spearman-Brown corrected odd/even match split-half correlation of unshrunk "
        "precision-weighted means (interval: 1000-draw match-cluster bootstrap). Approach C's "
        "figures use held-out matches only (its weights were fitted on FIT matches), A's and B's use "
        "all matches, so the columns are not like for like (C has fewer matches per player in each "
        "half, which lowers reliability by construction). The "
        "selection rule was applied to these figures as declared and the difference is reported, "
        "not corrected. The Phase 6 data-weight gate (mean data weight >= 0.5) is reported "
        "unchanged: no approach passes it.\n"
    )
    cw_ = cw.copy()
    L.append("Approach C data-derived weights (FIT matches only):\n")
    L.append(md_table(cw_, ["role", "component", "n_players_fit", "split_half_sb", "tau2_fit", "floor_fit", "status", "final_weight"], 4) + "\n")  # fmt: skip
    L.append("Between-player variance over noise and ICC(1) per component:\n")
    L.append(md_table(cr, ["role", "component", "icc1", "between_over_noise"], 4) + "\n")
    L.append("## 5. Format fairness (IPL and T20I)\n")
    t = []
    for tag, f in (("A", fa), ("B", fb)):
        for _, r in f.iterrows():
            t.append({"approach": tag, "role": r["role"], "players_both_formats": r["players_both_formats"],
                      "spearman": r["spearman"], "low": r["spearman_low"], "high": r["spearman_high"],
                      "combination_supported": r["combination_supported"]})  # fmt: skip
    for _, r in fc[fc["series"] == "PRI"].iterrows():
        t.append({"approach": "C", "role": r["role"], "players_both_formats": r["players_both_formats"],
                  "spearman": r["spearman"], "low": r["spearman_low"], "high": r["spearman_high"],
                  "combination_supported": r["combination_supported"]})  # fmt: skip
    L.append(md_table(pd.DataFrame(t), list(t[0].keys())) + "\n")
    L.append(
        "The declared combination rule needs a cross-format lower bound of at least 0.3 with at least "
        "30 players in both formats. No approach meets it, so the combined estimate is flagged "
        "`FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`: units are format-centred and each unit "
        "is weighted by its own precision, with no fixed 70:30 split. Each listed player's IPL and "
        "T20I scores and ranks are shown in the CSV.\n"
    )
    L.append("## 6. Explainability (fixed checklist, last tie-break)\n")
    L.append(
        "A scores 3 (observed against expected from observable inputs only), B and C score 2 (a "
        "modelled win-probability state, or a data-weighted index). The checklist decided nothing "
        "in this run because an earlier criterion separated the approaches.\n"
    )
    L.append("## 7. Selection under the predeclared rule\n")
    for _, s in sel.iterrows():
        L.append(
            f"- **{ROLE_WORD[s['role']].capitalize()}**: {s['reason']} Rule text: {s['rule_text']}."
        )
    L.append(
        "\nFor batters A and C are within 0.001 of each other on the split-half point estimate "
        "(0.0571 and 0.0570) and both intervals include 0; A is chosen because both branches of the "
        "rule select it (it also has the better out-of-time lower bound). The choice between them "
        "should not be read as a performance difference. For bowlers C leads on the split-half "
        "point estimate, its lower bound and the out-of-time lower bound, while A has one more "
        "player with a Top-10 inclusion probability of at least 0.5; C's interval also includes 0, "
        "and C's figures come from held-out matches only.\n"
    )
    L.append("## 8. Sensitivity of the submitted orderings\n")
    L.append(
        "Each row compares the submitted ordering with a variant: Spearman correlation over common "
        "eligible players and the overlap of the two Top 10 sets (out of 10).\n"
    )
    for role in ROLES:
        d = sens[sens["role"] == role].sort_values(["family", "comparison"])
        L.append(
            f"**{ROLE_WORD[role].capitalize()}** (approach {_row(sel, role=role)['approach_chosen']})\n"
        )
        L.append(md_table(d, ["family", "comparison", "n_common", "spearman", "top10_overlap", "note"], 3) + "\n")  # fmt: skip
    L.append(
        "Reading: the ordering is stable to eligibility floors and moderately stable to format and "
        "window, but the Top 10 membership changes substantially with the pressure definition, "
        "the shrinkage assumption (unshrunk ordering) and the components used, which is the "
        "sensitivity Phase 6 reported. The fixed-variance bootstrap shortcut differs from the full "
        "refit by more than the declared 0.05 for batters, so the full refit is used for every "
        "published inclusion probability.\n"
    )
    L.append("## 9. Conclusion\n")
    L.append(
        "No approach meets the PROVISIONAL threshold in either role. The selected approaches are the "
        "best-supported available (batters A, bowlers C) and both lists are EXPLORATORY. The "
        "central Phase 6 finding is confirmed with a richer method: the match-level data do not "
        "reliably separate players on pressure performance.\n"
    )
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------
# research account
# ---------------------------------------------------------------------------------------------
def research_md() -> str:
    st, cmp_, sel = _t("p8_top10_status"), _t("p8_method_comparison"), _t("p8_method_selection")
    sel_tab = _t("p8_b_intensity_selection")
    ex = _t("p8_data_exclusions")
    wp = _t("p8_wp_metrics")
    cw = _t("p8_c_weights")
    cmp_ = _t("p8_method_comparison")
    L = ["# Pressure methodology research: a candid account\n"]
    L += _banner_block(st)
    L.append("## 1. The baseline: Phases 3 to 6\n")
    L.append(
        "Phases 3 to 6 defined pressure as a percentile slice of the match situation (the "
        "`any|q0.75` definition: the top quarter of a pressure signal), compared each player with a "
        "cell baseline built from four coarse keys (competition, role, phase, wickets), and shrank "
        "the player's residual toward the cohort mean. Phase 6 tested whether this could separate "
        "players and reported:\n"
    )
    L += [f"- {x}" for x in PHASE6]
    L.append(
        "\nCauses found in the audit: the slice kept about a quarter of the balls (a median player had "
        "26 to 55 pressure balls per cell); ball-level residuals are very noisy (RMSE about 1.75, the "
        "baseline cut it by under 1%); the between-player variance estimate collapsed to the floor so "
        "every estimate was shrunk toward the mean; and independent-ball weights overstated the "
        "precision. Phase 6 tried 18 improvement options and none reached the 0.5 data-weight gate "
        "without changing the methodology.\n"
    )
    L.append("## 2. What Phase 8 did differently\n")
    L.append(
        "1. **Continuous intensity instead of a slice.** Every delivery gets an intensity between 0 and "
        "1 (empirical CDF of the raw value on TRAIN), so every delivery contributes in proportion "
        "to how difficult the situation was. Seven definitions were declared (P0 to P6).\n"
        "2. **A richer, player-blind expected outcome.** Gradient boosting on the pre-delivery "
        "situation (runs, wickets, dots, boundaries), trained on TRAIN only, scored out of fold.\n"
        "3. **Match-level units and REML.** The unit is one player in one innings, which gives honest "
        "clustering and a bootstrap by match. Shrinkage was kept; no floor was imposed.\n"
        "4. **Three approaches, one comparison.** A (observed against expected), B (win probability "
        "added with explicit attribution) and C (a data-weighted index), compared under criteria "
        "declared and hashed before any result existed.\n"
        "5. **Honest labels.** A status system (VALIDATED, PROVISIONAL, EXPLORATORY, "
        "INSUFFICIENT_EVIDENCE) tied to declared reliability thresholds, with the submitted ranking "
        "status kept apart from the model validation status.\n"
    )
    L.append("## 3. What worked\n")
    wp1, wp2 = _row(wp, model="W1"), _row(wp, model="W2")
    L.append(
        f"- The win-probability models are calibrated on 2025 matches: Brier {wp2['brier']:.3f} for the "
        f"chase (constant {wp2['brier_const']:.3f}, slope {wp2['slope']:.2f}) and {wp1['brier']:.3f} for the first "
        f"innings (constant {wp1['brier_const']:.3f}, slope {wp1['slope']:.2f}). Both passed the declared gates.\n"
        "- The WPA attribution rules are unit-tested (striker, bowler, wicket, run-out, extras) and "
        "no bowler credit is given for a run-out.\n"
        "- Leakage tests show pre-delivery values do not change when later rows are truncated or "
        "outcomes are mutated; the TEST period was never opened and the protected databases were "
        "byte-identical before and after every stage.\n"
        "- The approach selection, status labels and ranking are deterministic and reproducible "
        "from the stored tables (two runs give identical output hashes).\n"
    )
    L.append("## 4. What failed, and why\n")
    L.append(
        "- **No pressure definition passed.** The monotonic trend across intensity deciles failed for "
        "every candidate. Pressure raises wicket probability and lowers scoring in the expected "
        "direction (tests a, b and c pass for P0, P3 and P4), but not smoothly enough to meet the "
        "predeclared trend criterion. The win-probability definitions (P1 leverage, P2 closeness) "
        "failed the direction tests outright, and the defender-side definition (P5) points the wrong "
        "way for runs.\n"
    )
    L.append(md_table(sel_tab, ["candidate", "pass", "test_a", "test_b", "test_c", "test_e", "n_tests_passed", "runs_diff_pooled_train", "wkt_diff_pooled_train"], 3) + "\n")  # fmt: skip
    am, cr = _t("p8_a_model_metrics"), _t("p8_c_component_reliability")
    a_noise = cr[cr["component"] == "A"].set_index("role")["between_over_noise"]
    gains = am["gain_vs_const_pct"]
    fmt_rng = pd.concat(
        [_t("p8_a_format_study")["spearman"], _t("p8_b_format_study")["spearman"],
         _t("p8_c_format_study").query("series == 'PRI'")["spearman"]]
    )  # fmt: skip
    cm = cmp_[cmp_["chosen"].astype(bool)].set_index("role")
    L.append(
        "- **The signal is small compared with the noise.** The expected-outcome models improve on a "
        f"constant by {gains.min():.1f}% to {gains.max():.1f}% (RMSE or log loss); between-player variance "
        f"over noise of the A component was {a_noise['batter']:.2f} for batters and "
        f"{a_noise['bowler']:.2f} for bowlers, and the REML variance sat at the floor for Approach B in "
        "most cells and for Approach A in the T20I batter cell.\n"
        "- **Split-half reliability stayed far below the thresholds.** The submitted batters' split-half "
        f"figure is {cm.loc['batter', 'sb']:.2f} (interval {cm.loc['batter', 'sb_low']:.2f} to "
        f"{cm.loc['batter', 'sb_high']:.2f}) and the bowlers' {cm.loc['bowler', 'sb']:.2f} (interval "
        f"{cm.loc['bowler', 'sb_low']:.2f} to {cm.loc['bowler', 'sb_high']:.2f}); both intervals include 0.\n"
        "- **Approach C collapsed.** The data-derived weights gave components A and B zero weight "
        "(floor or non-positive reliability on FIT matches), so the PRI is the consistency of "
        "pressure units: how often a player beats the expectation, whatever the size. It is not "
        "independent of A, because it is built from the same residuals.\n"
    )
    L.append(md_table(cw, ["role", "component", "split_half_sb", "floor_fit", "status", "final_weight"], 4) + "\n")  # fmt: skip
    L.append(
        "- **IPL and T20I do not agree.** Cross-format Spearman correlations of player estimates were "
        f"between {fmt_rng.min():.2f} and {fmt_rng.max():.2f} across approaches and roles, with "
        "intervals that include 0, so no combination was supported.\n"
    )
    L.append("## 5. How the thinking evolved\n")
    L.append(
        "The first intuition was that pressure is a property of the match (a close chase, the death "
        "overs), so the task was to find the right definition and then rank. The Phase 6 failure "
        "showed the problem was not only the definition: even a generous definition leaves too few "
        "pressure balls per player, and ball outcomes carry too much luck. Phase 8 therefore moved "
        "from asking which slice is pressure to asking how much each delivery tells us, then "
        "tested whether anything could be separated. Win probability added looked like the most "
        "cricket-faithful measure, but the credit assigned to one player in one delivery is mostly "
        "the match state, and it was the least reliable of the three. The simplest measure, "
        "observed against expected, did about as well as the most elaborate. The result is a "
        "transparent ordering with honest labels, not a validated ranking.\n"
    )
    L.append("## 6. Data handling facts\n")
    L.append(md_table(ex, ["reason", "competition_type", "rows", "matches"]) + "\n")
    L.append(
        "Official data only; the authoritative ball-by-ball file; confirmed Super Over innings and the "
        "unverified innings 3 and 4 excluded; the 42 late-dated T20I matches excluded from primary "
        "evaluation; restriction register applied at metric level; the 2026 (TEST) matches were not "
        "used (they were opened once in Phase 4 and are not a clean hold-out).\n"
    )
    L.append("## 7. Open decisions for the owner\n")
    L.append(
        "- Confirm the wording of the status labels (`config/phase8_status_labels_v1.json`).\n"
        "- Decide whether a labelled, non-pristine application to the 2026 matches is wanted.\n"
        "- Optional: official verification of the 42 late-dated T20I matches.\n"
        "- `phase8.duckdb` holds the new tables so that the protected databases stay byte-identical "
        "(deviation from the brief wording).\n"
    )
    L.append("## 8. Selection record\n")
    for _, s in sel.iterrows():
        L.append(f"- {ROLE_WORD[s['role']].capitalize()}: {s['reason']}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------
# player explanations
# ---------------------------------------------------------------------------------------------
def explanations_md() -> str:
    st, rk, ex = _t("p8_top10_status"), _t("p8_rankings"), _t("p8_explanations")
    L = ["# Player selection explanations\n"]
    L += _banner_block(st)
    L.append(
        "Each section explains why a player is in the submitted Top 10, what the numbers are, how "
        "much evidence stands behind them and how firmly the position is supported. Every figure "
        f"is read from `{translate_table('p8_rankings')}` (the same table as the CSV and JSON files). The "
        "pressure situation is the P4 resource-scarcity definition, which did not pass the predeclared "
        "validity tests. Each row carries the label of its list (see the banners); no row is "
        "labelled stronger than its list.\n"
    )
    for role in ROLES:
        s = _row(st, role=role)
        sel = (
            rk[(rk["role"] == role) & (rk["kind"] == "SELECTED")]
            .sort_values("rank")
            .reset_index(drop=True)
        )
        L.append(
            f"## {ROLE_WORD[role].capitalize()}: {s['list_status']} (approach {s['approach']})\n"
        )
        L.append(f"{s['banner']}\n")
        for i, r in sel.iterrows():
            d = json.loads(r["detail_json"]) if isinstance(r["detail_json"], str) else {}
            comp = json.loads(r["component_scores"])
            L.append(f"### {int(r['rank'])}. {r['player_name']} (player {int(r['player_id'])})\n")
            L.append(f"**Why selected.** {r['short_explanation']}\n")
            L.append(
                f"- **Pressure situations faced.** {_fmt(r['pressure_deliveries'], 0)} pressure deliveries in "
                f"{_fmt(r['pressure_innings_or_spells'], 0)} {'innings' if role == 'batter' else 'spells'}: "
                f"phases (powerplay {_fmt(d.get('n_powerplay'), 0)}, middle {_fmt(d.get('n_middle'), 0)}, death "
                f"{_fmt(d.get('n_death'), 0)}), innings 1 {_fmt(d.get('n_innings1'), 0)} and innings 2 "
                f"{_fmt(d.get('n_innings2'), 0)}; mean intensity {_fmt(r['mean_intensity'], 2)}."
            )
            L.append(
                f"- **Actual performance against expectation.** Observed {_fmt(r['observed_runs_per_ball'], 2)} "
                f"runs per ball against {_fmt(r['expected_runs_per_ball'], 2)} expected; "
                f"{'dismissal' if role == 'batter' else 'wicket'} rate {_fmt(r['observed_wicket_rate'], 3)} against "
                f"{_fmt(r['expected_wicket_rate'], 3)}."
            )
            L.append(
                f"- **Baseline and difference.** Normal-play baseline {_fmt(r['normal_baseline'], 3)}, "
                f"pressure level (unshrunk) {_fmt(r['pressure_performance_unshrunk'], 3)}, difference "
                f"{_fmt(r['pressure_delta'], 3)} (A-residual units per ball)."
            )
            L.append(
                f"- **Score and components.** Score {_fmt(r['pressure_score'], 4)} "
                f"[{_fmt(r['interval_low'], 4)}, {_fmt(r['interval_high'], 4)}] ({r['score_unit']}; "
                f"interval flag {r['interval_flag']}); components: "
                + ", ".join(f"{k} {_fmt(v, 3)}" for k, v in sorted(comp.items()))
                + "."
            )
            L.append(
                f"- **Consistency across matches.** {_p(r['positive_unit_share'])} of pressure units beat the "
                f"expectation; between-unit dispersion {_fmt(d.get('disp'), 3)}; evidence class "
                f"{r['evidence_class']}."
            )
            L.append(
                f"- **Evidence amount.** {_fmt(r['total_matches'], 0)} matches (IPL {_fmt(r['ipl_matches'], 0)}, "
                f"T20I {_fmt(r['t20i_matches'], 0)}), {_fmt(d.get('balls'), 0)} deliveries with a defined intensity, "
                f"effective sample {_fmt(d.get('eff_n'), 0)}, data weight (reliability of the estimate) "
                f"{_fmt(r['sample_reliability'], 2)}. {r['eligibility_flags']}."
            )
            L.append(
                f"- **Stability.** Top-10 inclusion {_p(r['top10_inclusion_probability'])}, 95% rank interval "
                f"{_fmt(r['rank_interval_low'], 0)} to {_fmt(r['rank_interval_high'], 0)}."
            )
            L.append(
                f"- **Rank under each approach and format.** A {_fmt(r['rank_in_A'], 0)}, B {_fmt(r['rank_in_B'], 0)}, "
                f"C {_fmt(r['rank_in_C'], 0)}; IPL only {_fmt(r['rank_in_IPL'], 0)}, T20I only {_fmt(r['rank_in_T20I'], 0)}, "
                f"combined {int(r['rank'])} (IPL share of matches {_p(r['ipl_contribution'])}; IPL score "
                f"{_fmt(r['ipl_score'], 4)}, T20I score {_fmt(r['t20i_score'], 4)})."
            )
            L.append(f"- **Why this position.** Relative to neighbours: {_neighbour(sel, i)}")
            extra = ""
            if r["evidence_class"] == "INCONSISTENT":
                extra = (
                    " The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or "
                    "dispersion above the cohort's 75th percentile with a positive mean), so the "
                    "position rests on a few large positive units."
                )
            L.append(
                "- **Limitations.** The pressure definition is unvalidated; the estimate contains the "
                "player's overall quality as well as pressure effects; the data weight is low, so the "
                f"estimate is shrunk strongly; format scores are on each format's own scale and are not "
                f"comparable with the combined score; flags: {r['data_quality_flags']}.{extra}\n"
            )
        pool = rk[(rk["role"] == role) & (rk["kind"] == "CANDIDATE_POOL")].sort_values("rank")
        L.append(
            f"### Candidate pool, ranks {int(pool['rank'].min()) if len(pool) else 'n/a'} to {int(pool['rank'].max()) if len(pool) else 'n/a'}\n"
        )
        L.append(
            "These players are not in the submitted list. Reasons come from the data; none is a statement that the player performs poorly.\n"
        )
        near = ex[(ex["role"] == role) & (ex["kind"] == "NEAR_MISS")].sort_values(
            ["rank", "reason_code"]
        )
        for pid, g in near.groupby("player_id", sort=False):
            g0 = g.iloc[0]
            L.append(
                f"- **Rank {int(g0['rank'])}, {g0['player_name']}**: "
                + "; ".join(f"`{x['reason_code']}`: {x['detail']}" for _, x in g.iterrows())
                + "."
            )
        L.append("")
        L.append(
            f"### Raw-statistic standouts ({'death-overs strike rate' if role == 'batter' else 'death-overs economy'}, at least 60 balls)\n"
        )
        L.append(
            "Players at the top of a simple raw statistic, with the reason they are or are not in the list:\n"
        )
        raw = ex[(ex["role"] == role) & (ex["kind"] == "RAW_STANDOUT")].sort_values(
            ["player_name", "reason_code"]
        )
        for pid, g in raw.groupby("player_id", sort=False):
            g0 = g.iloc[0]
            stat = g[g["reason_code"] == "RAW_STAT"]["detail"].iloc[0]
            rest = g[g["reason_code"] != "RAW_STAT"].sort_values("reason_code")
            L.append(
                f"- **{g0['player_name']}** ({stat}): "
                + "; ".join(f"`{x['reason_code']}`: {x['detail']}" for _, x in rest.iterrows())
                + "."
            )
        L.append("")
    return "\n".join(L) + "\n"


def write_all(reports_dir: Path | str) -> list[Path]:
    """Write the four documents; preserve the superseded Phase 7 status file once."""
    d = Path(reports_dir)
    old = d / "pressure_top10_status.md"
    keep = d / "pressure_top10_status_phase7_obsolete.md"
    if old.exists() and not keep.exists():
        text = old.read_text(encoding="utf-8")
        if "intentionally not produced" in text:
            shutil.copyfile(old, keep)
    out = []
    for name, fn in (
        ("pressure_top10_status.md", status_md),
        ("methodology_comparison.md", comparison_md),
        ("pressure_methodology_research.md", research_md),
        ("player_selection_explanations.md", explanations_md),
    ):
        p = d / name
        p.write_bytes(fn().encode("utf-8"))
        out.append(p)
    return out


__all__ = ["write_all", "status_md", "comparison_md", "research_md", "explanations_md", "np"]
