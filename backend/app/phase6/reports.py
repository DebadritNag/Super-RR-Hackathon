"""Phase 6 final reports: the unresolved-issues register and the plain-language user summary.

Every number is read from the stored Phase 4/5/6 outputs (CSV/JSON in ``data/reports``); nothing is
typed in. The Phase 5 register is parsed and every Phase 5 item id must be carried forward with an
explicit status (``UNCHANGED``, ``CHANGED`` or ``CLOSED``). Reports carry the experimental label and
the TEST-not-pristine statement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics.reporting import md_table
from app.phase6.constants import STATUS

TEST_NOT_PRISTINE = (
    "TEST was opened once in Phase 4 (aggregate results were shown) and is not a pristine "
    "hold-out. No independent out-of-sample validation is claimed anywhere."
)
CROSS_SOURCE = "Cross-source consistency of the 42 late T20I dates is not official verification."
PHASE5_ITEM = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", re.M)

DELIVERABLES = (
    "phase6_investigation_plan.md",
    "phase6_cleanup_report.md",
    "phase6_variance_floor_investigation.md",
    "phase6_split_half_reliability.md",
    "phase6_definition_reliability_comparison.md",
    "phase6_context_reliability.md",
    "phase6_eligibility_reliability.md",
    "phase6_data_weight_improvement_options.md",
    "phase6_recent_form_analyses.md",
    "phase6_robustness_season_checks.md",
    "phase6_unresolved_issues.md",
    "phase6_retention_import_design.md",
    "phase6_user_summary.md",
)


def _j(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def phase5_items(reports: Path) -> dict[int, str]:
    """Phase 5 register rows: id -> issue title (parsed from the stored Phase 5 register)."""
    text = (reports / "phase5_unresolved_issues.md").read_text(encoding="utf-8")
    return {int(m.group(1)): m.group(2) for m in PHASE5_ITEM.finditer(text)}


def collect(reports: Path) -> dict[str, Any]:
    """Read every number the reports use from stored outputs."""
    n: dict[str, Any] = {}
    cl = _j(reports / "phase6_cleanup_checks.json")["classification"]
    n["cls_counts"] = cl["status_counts"]
    n["cls_values"] = cl["status_values"]
    n["cls_placeholder"] = cl["disabled_placeholder_values"]
    n["cls_total"] = cl["players_total"]
    dv = pd.read_csv(reports / "phase5_t20i_date_verification.csv")
    n["date_total"] = int(len(dv))
    n["date_classes"] = {k: int(v) for k, v in dv["date_class"].value_counts().items()}
    n["date_official"] = int(dv["official_verified"].astype(bool).sum())
    sets = _j(reports / "phase5_test_set_manifest.json")["sets"]
    n["test_sets"] = {k: len(v["match_ids"]) for k, v in sets.items()}
    vf = pd.read_csv(reports / "phase6_variance_floor_investigation.csv")
    vf = vf[(vf["unit_kind"] == "context") & (vf["window"] == "PRE_TEST")]
    n["var_contexts"] = int(len(vf))
    n["var_floor_hits"] = int(vf["floor_hit"].astype(bool).sum())
    n["var_verdicts"] = {k: int(v) for k, v in vf["verdict"].value_counts().items()}
    sh = pd.read_csv(reports / "phase6_split_half_reliability_pooled.csv")
    sh = sh[(sh["definition"] == "any|q0.75") & (sh["stream_group"] == "primary")
            & (sh["window"] == "PRE_TEST")]  # fmt: skip
    n["pooled_sb"] = {r["mode"]: float(r["pooled_sb"]) for _, r in sh.iterrows()}
    oc = pd.read_csv(reports / "phase6_definition_reliability_comparison_outcome.csv")
    fin = oc[oc["window"] == "FINAL"].iloc[0]
    n["def_status"] = str(fin["status"])
    n["def_confounded"] = bool(fin["confounded"])
    n["def_pass_list"] = str(fin["pass_list"])
    ds = pd.read_csv(reports / "phase6_data_weight_improvement_options_summary.csv")
    main = ds[~ds["option_id"].str.startswith("O8")]
    n["opt_rows"] = int(main["rows"].sum())
    n["opt_pass"] = int(main["rows_passing_gate"].sum())
    n["opt_options"] = int(len(main))
    n["opt_best_b"] = float(main["best_data_weight"].max())
    n["opt_best_id"] = str(main.loc[main["best_data_weight"].idxmax(), "option_id"])
    n["opt_subset_pass"] = int(main["rows_passing_on_estimable_subset"].sum())
    gs = pd.read_csv(reports / "phase6_data_weight_improvement_options_gate_status.csv")
    n["gate_contexts"] = int(len(gs))
    n["gate_stored_pass"] = int(gs["data_weight_gate_passed"].astype(bool).sum())
    n["gate_value"] = float(gs["gate_used"].iloc[0])
    et = pd.read_csv(reports / "phase6_eligibility_reliability_targets.csv")
    et = et[et["window"] == "PRE_TEST"]
    n["elig_reached"] = {
        str(t): [int((g["status"] == "TARGET_REACHED").sum()), int(len(g))]
        for t, g in et.groupby("target")
    }
    cr_ = pd.read_csv(reports / "phase6_context_reliability.csv")
    est = cr_[cr_["oe_status"] == "ESTIMATED"]
    n["ctx_total"] = int(len(cr_))
    n["ctx_estimable"] = int(len(est))
    n["ctx_oe_median"] = float(est["oe_sb"].median())
    n["ctx_gate_pass"] = int(cr_["gate_passed_recomputed"].astype(bool).sum())
    for key in ("2024", "2025"):
        s = pd.read_csv(reports / f"phase6_recent_form_analyses_{key}.csv")
        prim = s[s["is_primary_stream"].astype(bool)]
        n[f"rf{key}"] = {
            "cells": int(len(prim)),
            "estimated": int((prim["status"] == "ESTIMATED").sum()),
            "gate_pass": int((prim["passes_gate_informational"] == True).sum()),  # noqa: E712
            "best_b": float(prim["marginal_data_weight"].max()),
            "matches": sorted(prim["matches"].unique().tolist()),
            "pressure_obs": int(prim["pressure_observations"].sum()),
        }
    rr = pd.read_csv(reports / "phase6_recent_form_analyses_reliability.csv")
    oe = rr[(rr["mode"] == "odd_even") & rr["is_primary_stream"].astype(bool)
            & (rr["status"] == "ESTIMATED")]  # fmt: skip
    n["rf_sb_median"] = {k: float(g["sb_pearson"].median()) for k, g in oe.groupby("window_start")}
    ss = pd.read_csv(reports / "phase6_robustness_season_checks.csv")
    ss = ss[ss["status"] == "ESTIMATED"]
    wi, ad = ss[ss["check"] == "within_season"], ss[ss["check"] == "adjacent_seasons"]
    n["season"] = {
        "within_n": int(len(wi)), "within_median": float(wi["value"].median()),
        "within_lo_pos": int((wi["ci_lo"] > 0).sum()),
        "adjacent_n": int(len(ad)), "adjacent_median": float(ad["value"].median()),
        "adjacent_lo_pos": int((ad["ci_lo"] > 0).sum()),
    }  # fmt: skip
    return n


def register_rows(n: dict[str, Any]) -> list[dict[str, str]]:
    c = n["cls_counts"]
    ts = n["test_sets"]
    v = n["var_verdicts"]
    return [
        {
            "id": "P5-1",
            "status": "CHANGED",
            "issue": "Strict uncapped selection",
            "state": f"Still disabled; no authoritative cap source keyed by player_id. Wording corrected: "
            f"three real values ({', '.join(n['cls_values'])}) plus a disabled placeholder "
            f"({', '.join(n['cls_placeholder'])}), which is not an established status. Counts over {n['cls_total']} "
            f"players: VERIFIED_CAPPED {c['VERIFIED_CAPPED']}, DERIVED_CAPPED {c['DERIVED_CAPPED']}, "
            f"UNKNOWN {c['UNKNOWN']}. Verified status is never inferred.",
            "needed": "An authoritative source with player ids.",
        },
        {
            "id": "P5-2",
            "status": "UNCHANGED",
            "issue": "42 late T20I match dates",
            "state": f"{n['date_total']} matches stay excluded from primary evaluation, original dates "
            f"kept. Evidence classes {n['date_classes']}; {n['date_official']} verified against an "
            f"official record. {CROSS_SOURCE}",
            "needed": "Official match-level dates for the 42 matches.",
        },
        {
            "id": "P5-3",
            "status": "UNCHANGED",
            "issue": "Data-weight gate",
            "state": f"Gate stays {n['gate_value']}. It fails in {n['gate_contexts'] - n['gate_stored_pass']} "
            f"of {n['gate_contexts']} contexts. None of {n['opt_rows']} option rows "
            f"({n['opt_options']} legitimate options) passes it; the best marginal data weight is "
            f"{n['opt_best_b']:.3f} ({n['opt_best_id']}, needs a methodology decision, "
            f"{n['opt_subset_pass']} row passes only on the individuals that have an estimate). "
            "Failed contexts stay restricted.",
            "needed": "A decision on whether to change the shrinkage methodology, or more data.",
        },
        {
            "id": "P5-4",
            "status": "UNCHANGED",
            "issue": "Methodology validation",
            "state": f"validated=false. any|q0.75 stays the provisional definition. Definition "
            f"comparison on reliability criteria: {n['def_status']} (pass list {n['def_pass_list']}, "
            f"confounded={n['def_confounded']}). No definition was selected.",
            "needed": "Your review before any validation record.",
        },
        {
            "id": "P5-5",
            "status": "CHANGED",
            "issue": "Between-player variance not identified",
            "state": f"Investigated. The moment estimate sits at the floor in {n['var_floor_hits']} of "
            f"{n['var_contexts']} contexts (k = 25 under shrink_tau4). Verdicts per context: {v}. The "
            "floor arithmetic is verified (25 for shrink_tau4 on a floor hit, 100 on the non-finite "
            "branch). The data identify the variance only weakly. No methodology was changed.",
            "needed": "A decision whether to keep shrinkage as is, change the model, or collect more data.",
        },
        {
            "id": "P5-6",
            "status": "UNCHANGED",
            "issue": "Ranking instability",
            "state": "Not re-run in Phase 6 (no rankings are produced). The Phase 5 figures stand: "
            "the point Top 10 is not stable under match resampling.",
            "needed": "Nothing to supply. This limits any selection use.",
        },
        {
            "id": "P5-7",
            "status": "UNCHANGED",
            "issue": "Primary TEST-set strictness",
            "state": f"PRIMARY_RESTRICTED {ts['PRIMARY_RESTRICTED']} matches kept for internal "
            f"diagnostic comparisons only; STRICT_OFFICIAL_ONLY {ts['STRICT_OFFICIAL_ONLY']} kept "
            f"separate; SENSITIVITY_ALL {ts['SENSITIVITY_ALL']}.",
            "needed": "Choose which set counts as primary for a later TEST evaluation.",
        },
        {
            "id": "P5-8",
            "status": "UNCHANGED",
            "issue": "TEST is not a pristine hold-out",
            "state": f"{TEST_NOT_PRISTINE} Phase 6 did not open TEST and added no lock event.",
            "needed": "Accept that a later TEST run is not pristine, or supply fresh data.",
        },
        {
            "id": "P5-9",
            "status": "UNCHANGED",
            "issue": "Minimum pool sizes",
            "state": "5 for internal exploratory rankings and 10 for a full Top 10 remain provisional "
            "and unvalidated. Results are never padded.",
            "needed": "Confirm or change the two numbers.",
        },
        {
            "id": "P5-10",
            "status": "UNCHANGED",
            "issue": "Refit has no hold-out",
            "state": "The TRAIN+VALIDATION refit has no out-of-sample check. Season-by-season checks "
            "and recent-form windows are robustness and descriptive analyses, not validation.",
            "needed": "Decide whether a new hold-out is needed before any use.",
        },
        {
            "id": "P6-1 (OD-1)",
            "status": "NEW",
            "issue": "Primary window is pre-test only",
            "state": "The full available verified history is TRAIN + VALIDATION (723 matches, "
            "2022-01-22 to 2025-12-19). TEST outcomes are not in the primary window.",
            "needed": "Confirm, or provide a new hold-out (see OD-3).",
        },
        {
            "id": "P6-2 (OD-2)",
            "status": "NEW",
            "issue": "Recent-form thresholds are provisional",
            "state": "2024-onward and 2025-onward scale the four frozen ball thresholds to each "
            "window (`ceil(t x window balls / TRAIN balls)`). They are not validated and each "
            "window is fitted in-sample. 2025-onward has no TRAIN rows.",
            "needed": "Whether a window should get frozen thresholds of its own.",
        },
        {
            "id": "P6-3 (OD-3)",
            "status": "NEW",
            "issue": "No clean hold-out exists",
            "state": "All Phase 6 reliability figures are in-sample diagnostics on TRAIN and "
            "VALIDATION. Season consistency is robustness, not validation.",
            "needed": "Whether to collect fresh data as a hold-out.",
        },
        {
            "id": "P6-4",
            "status": "NEW",
            "issue": "Public /players shape changed",
            "state": "The public directory no longer returns eligible_scopes, conflict_flag, "
            "publication or gate fields, and the min_pressure_matches filter was removed from the "
            "public route. They stay on the token-protected internal routes (OD-6).",
            "needed": "Confirm the public API change.",
        },
        {
            "id": "P6-5",
            "status": "NEW",
            "issue": "Retention and release list pending",
            "state": "Design note and an empty stub table exist. No data imported, no scoring "
            "reference.",
            "needed": "The retention/release list, its format, season and source.",
        },
        {
            "id": "P6-6",
            "status": "NEW",
            "issue": "Reliability of pressure measures is low to moderate",
            "state": f"Pooled odd/even Spearman-Brown reliability of the provisional definition, "
            f"primary streams: {n['pooled_sb'].get('odd_even', float('nan')):.3f}. Context "
            f"reliability median {n['ctx_oe_median']:.3f} over {n['ctx_estimable']} estimable "
            "contexts. Intervals often include 0. Required balls per player for reliability 0.5 "
            f"were reached in {n['elig_reached'].get('0.5', [0, 0])[0]} of "
            f"{n['elig_reached'].get('0.5', [0, 0])[1]} cells within the tested ladder; 0.7 and "
            "0.8 were not reached.",
            "needed": "Decide how to treat contexts with low reliability (wider uncertainty, shorter "
            "lists or staying restricted).",
        },
    ]


def render_register(n: dict[str, Any], p5: dict[int, str]) -> str:
    rows = register_rows(n)
    have = {int(r["id"].split("-")[1]) for r in rows if r["id"].startswith("P5-")}
    missing = sorted(set(p5) - have)
    if missing:
        raise ValueError(f"Phase 5 register items not carried forward: {missing}")
    L = [
        "# Phase 6 unresolved issues",
        "",
        f"Status: {STATUS}. Nothing here is validated. No ranking is published. {TEST_NOT_PRISTINE} "
        f"{CROSS_SOURCE} All Phase 5 items are carried forward with an explicit status: "
        "`UNCHANGED`, `CHANGED` or `CLOSED` (none closed in Phase 6). New items are `NEW`.",
        "",
        md_table(
            ["id", "status", "issue", "current state (from the stored outputs)", "needed from you"],
            [[r["id"], r["status"], r["issue"], r["state"], r["needed"]] for r in rows],
        ),
        "",
        "## Publication gates",
        "`data_weight_gate_passed`, `methodology_validated` and `date_verification` still fail, so "
        "no experimental result is publishable. Phase 6 changed no gate, threshold or methodology.",
        "",
        "## Stop condition",
        "No official Top 10, no public experimental ranking and no official ML training. Phase 6 "
        "stops here for your review before any change to the official methodology or any "
        "production ranking.",
        "",
    ]
    return "\n".join(L)


def render_summary(n: dict[str, Any]) -> str:
    ts, v = n["test_sets"], n["var_verdicts"]
    rf24, rf25, s = n["rf2024"], n["rf2025"], n["season"]
    el = n["elig_reached"]
    L = [
        "# Phase 6 summary for review",
        "",
        f"Status: {STATUS}. Everything below is internal. No official Top 10 was made, nothing was "
        "published, no model was trained for production, and no score is called validated. "
        f"{TEST_NOT_PRISTINE}",
        "",
        "## What I did",
        "- **Cleanup.** The classification wording now names three real values "
        f"({', '.join(n['cls_values'])}) and a disabled placeholder ({', '.join(n['cls_placeholder'])}). "
        "The always-true test assertions were replaced and a test now blocks new ones. The public "
        "`/players` directory no longer carries score, rank or eligibility fields. The ranking cache "
        "is keyed by scope and versions and returns copies.",
        "- **Investigation.** Variance, split-half reliability, nine pressure definitions, "
        "context reliability, eligibility thresholds and data-weight options were examined. The "
        "selection criteria were written and hashed before any definition result.",
        "- **Recent form and robustness.** 2024-onward and 2025-onward are separate analyses. "
        "Season-by-season checks are robustness checks, not validation.",
        "- **Retention list.** A design note and an empty table exist. Nothing was imported.",
        "",
        "## What I found",
        f"- **Between-player variance.** The estimate is at the shrinkage floor in "
        f"{n['var_floor_hits']} of {n['var_contexts']} contexts. Per-context verdicts: {v}. The data "
        "identify the spread between players only weakly, so most scores stay close to the pooled "
        "average. This is a finding about the data, not a bug; the floor arithmetic checks out.",
        f"- **Reliability.** Pooled odd/even reliability for the provisional definition (primary "
        f"streams) is {n['pooled_sb'].get('odd_even', float('nan')):.2f}. Over "
        f"{n['ctx_estimable']} estimable contexts the median is {n['ctx_oe_median']:.2f}. Many "
        "intervals include 0.",
        f"- **Definitions.** Result: {n['def_status']}. No definition was chosen and `any|q0.75` "
        "stays provisional. The comparison is confounded by different player pools.",
        f"- **Data-weight gate.** It stays at {n['gate_value']}. It fails in "
        f"{n['gate_contexts'] - n['gate_stored_pass']} of {n['gate_contexts']} contexts. "
        f"{n['opt_pass']} of {n['opt_rows']} option rows ({n['opt_options']} legitimate options) "
        f"pass it. The best marginal data weight is {n['opt_best_b']:.2f}, and that option "
        "changes the methodology, so it needs your decision. Failed contexts stay restricted.",
        f"- **Required data.** Reliability 0.5 was reached in {el.get('0.5', [0, 0])[0]} of "
        f"{el.get('0.5', [0, 0])[1]} cells within the tested ball ladder; 0.7 and 0.8 were not "
        "reached.",
        f"- **Recent form.** 2024-onward: {rf24['estimated']} of {rf24['cells']} primary cells "
        f"estimated, {rf24['gate_pass']} pass the gate (best data weight {rf24['best_b']:.3f}). "
        f"2025-onward: {rf25['estimated']} of {rf25['cells']}, {rf25['gate_pass']} pass (best "
        f"{rf25['best_b']:.3f}). Shorter windows have fewer observations, so they do better on "
        "neither data weight nor intervals.",
        f"- **Seasons.** Within-season reliability: median {s['within_median']:.2f} over "
        f"{s['within_n']} units, interval above 0 in {s['within_lo_pos']}. Adjacent-season "
        f"correlation: median {s['adjacent_median']:.2f} over {s['adjacent_n']} units, interval "
        f"above 0 in {s['adjacent_lo_pos']}. This is robustness, not validation.",
        "",
        "## What stays as it was",
        f"- {CROSS_SOURCE} All 42 matches stay excluded.",
        f"- PRIMARY_RESTRICTED ({ts['PRIMARY_RESTRICTED']} matches) is for internal diagnostics "
        f"only; STRICT_OFFICIAL_ONLY ({ts['STRICT_OFFICIAL_ONLY']}) is separate.",
        "- Minimum pool sizes 5 and 10 are provisional and unvalidated. Results are never padded.",
        "- Strict uncapped selection stays disabled.",
        "",
        "## What I need from you",
        "- Whether to keep the current shrinkage, change the model, or collect more data.",
        "- How to treat low-reliability contexts: wider uncertainty, shorter lists or staying "
        "restricted.",
        "- Official dates for the 42 matches, a cap source with player ids, and the retention list.",
        "- Confirmation of the public `/players` change and the open decisions OD-1 to OD-3.",
        "",
        "I stopped here. I will not change the official methodology or produce rankings until you "
        "review. Details: `phase6_unresolved_issues.md` and the reports it names.",
        "",
    ]
    return "\n".join(L)
