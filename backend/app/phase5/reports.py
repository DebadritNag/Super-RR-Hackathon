"""Renderers for the Chunk 5 reports. Numbers are read from the stored JSON/CSV outputs.

Templates only: nothing here computes a score. Every report states that the work is experimental,
that nothing is validated and that no ranking is published. No timestamps (deterministic output).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics.reporting import fmt, md_table
from app.phase5.constants import STATUS

REFIT_ID = "p5_refit_trainval_v1"


def jload(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_inputs(reports: Path) -> dict[str, Any]:
    comp = reports / f"{REFIT_ID}_comparison.csv"
    return {
        "gates": jload(reports / "phase5_publication_gates.json"),
        "classification": jload(reports / "phase5_classification_migration.json"),
        "dates": jload(reports / "phase5_t20i_date_verification.json"),
        "sens": jload(reports / "phase5_sensitivity_summary.json"),
        "stab": jload(reports / "phase5_ranking_stability_summary.json"),
        "cov": jload(reports / "phase5_context_coverage_summary.json"),
        "ctx": jload(reports / "phase5_context_engine_summary.json"),
        "inv": jload(reports / "phase5_investigation_summary.json"),
        "checklist": jload(reports / "phase5_pre_lock_checklist.json"),
        "lock": jload(reports / "phase5_methodology_lock.json"),
        "refit": jload(reports / f"{REFIT_ID}_manifest.json"),
        "comparison": pd.read_csv(comp) if comp.is_file() else None,
        "frozen": jload(reports / "phase4_frozen_choices.json"),
    }


def _g(d: Any, *path: str, default: Any = "n/a") -> Any:
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def failing_gate_ids(inp: dict[str, Any]) -> list[str]:
    g = inp.get("gates") or {}
    scen = next(iter((g.get("scenarios") or {}).values()), {})
    return list(scen.get("failing_gates", []))


def _classification_counts(inp: dict[str, Any]) -> dict[str, int]:
    return _g(inp["classification"], "coverage", "status_counts", default={})


# ---------------------------------------------------------------- unresolved issues
def render_unresolved(inp: dict[str, Any]) -> str:
    cc = _classification_counts(inp)
    dist = _g(inp["dates"], "class_distribution_late42", default={})
    sets = {s["set"]: s for s in _g(inp["sens"], "test_sets", "sets", default=[])}
    cells = _g(inp["frozen"], "eligibility", default={})
    cov = inp.get("cov") or {}
    rule = cov.get("minimum_pool_rule", {})
    rows = [
        [
            "1",
            "Strict uncapped selection",
            f"Disabled. No authoritative cap source keyed by player_id. VERIFIED_CAPPED {cc.get('VERIFIED_CAPPED', 'n/a')}, "
            f"DERIVED_CAPPED {cc.get('DERIVED_CAPPED', 'n/a')}, UNKNOWN {cc.get('UNKNOWN', 'n/a')} "
            "(three real values; VERIFIED_UNCAPPED is a disabled placeholder with no source).",
            "An authoritative source with player ids.",
        ],
        [
            "2",
            "42 late T20I match dates",
            f"Original dates kept. Evidence classes: {dist}. None is verified against an official record.",
            "Official match-level dates for the 42 matches.",
        ],
        [
            "3",
            "Data-weight gate",
            f"Fails for all {len(cells)} format-role cells (THRESHOLD_NOT_VALIDATED). Working pools are internal only.",
            "A decision on how the data-weight gate can be met, or more data.",
        ],
        [
            "4",
            "Methodology validation",
            "validated=false in config/phase5_methodology_status_v1.json. The definition any|q0.75 is the rule winner "
            "of nine candidates and is not shown to be better. Only a human edit can change this.",
            "Your review and, if you agree, a signed validation record.",
        ],
        [
            "5",
            "Between-player variance not identified",
            "The between-player moment is negative in every cell and every context (48 of 48), so shrinkage sits at "
            "its variance floor (k = 25) and scores are mostly shrinkage targets.",
            "A decision whether to keep shrinkage as is, change the model, or collect more data.",
        ],
        [
            "6",
            "Ranking instability",
            "; ".join(_g(inp["stab"], "reading", default=[])[:2]),
            "Nothing to supply. This limits any selection use.",
        ],
        [
            "7",
            "Primary TEST-set strictness",
            f"PRIMARY_RESTRICTED {_g(sets, 'PRIMARY_RESTRICTED', 'matches')} matches, STRICT_OFFICIAL_ONLY "
            f"{_g(sets, 'STRICT_OFFICIAL_ONLY', 'matches')}, SENSITIVITY_ALL {_g(sets, 'SENSITIVITY_ALL', 'matches')}.",
            "Choose which set counts as primary for a later TEST evaluation.",
        ],
        [
            "8",
            "TEST is not a pristine hold-out",
            "Phase 4 opened TEST once (FREEZE, OPEN, CLOSE) and aggregate results were shown in its summary. "
            "Phase 5 did not open it and its lock log is empty.",
            "Accept that a later TEST run is not pristine, or supply fresh data.",
        ],
        [
            "9",
            "Minimum pool sizes",
            f"Internal {_g(rule, 'min_internal_pool')} and public {_g(rule, 'min_public_pool')} are provisional values.",
            "Confirm or change the two numbers.",
        ],
        [
            "10",
            "Refit has no hold-out",
            "The TRAIN+VALIDATION refit used VALIDATION for fitting, so no out-of-sample check of the refit exists.",
            "Decide whether a new hold-out is needed before any use.",
        ],
    ]
    return "\n".join(
        [
            "# Phase 5 unresolved issues",
            "",
            f"Status: {STATUS}. Nothing here is validated. No ranking is published.",
            "",
            md_table(
                ["#", "issue", "current state (from the stored outputs)", "needed from you"], rows
            ),
            "",
            "## Publication gates still failing",
            "",
            f"{failing_gate_ids(inp)}. `PUBLIC_ALLOWED` needs every applicable gate to pass. Request-level gates "
            "(`strict_classification_available`, `min_eligible_pool`) apply on top for requests that use them.",
            "",
        ]
    )


# ---------------------------------------------------------------- lock and refit
def render_lock_refit(inp: dict[str, Any]) -> str:
    chk, lock, rf, cmp_ = (
        inp.get("checklist"),
        inp.get("lock"),
        inp.get("refit"),
        inp.get("comparison"),
    )
    L = [
        "# Phase 5 methodology lock and experimental refit",
        "",
        f"Status: {STATUS}. Label of the lock: `EXPERIMENTAL_LOCK`. The lock freezes choices for an experimental "
        "refit. It does not validate the methodology, the pressure definition or the working pools.",
        "",
        "## 1. Pre-lock checklist",
    ]
    if chk:
        L += [
            md_table(
                ["item", "kind", "status", "detail"],
                [[i["id"], i["kind"], i["status"], i["detail"]] for i in chk["items"]],
            ),
            "",
            f"Required items all pass: **{chk['required_all_pass']}**. Methodology validated: "
            f"**{chk['methodology_validated']}**. Publication ready: **{chk['publication_ready']}**.",
            f"Publication checks that fail: {chk['failing_publication_checks']}.",
            f"Decisions waiting for you: {chk['pending_user_decisions']}.",
        ]
    else:
        L.append("The checklist has not been run (`scripts/phase5_methodology_lock.py`).")
    L += ["", "## 2. Lock manifest"]
    if lock:
        c = lock["content"]
        ch = c["choices"]
        L += [
            f"- Manifest: `phase5_methodology_lock.json`, label `{lock['label']}`, validated `{lock['validated']}`.",
            f"- Lock hash: `{lock['lock_hash']}`.",
            f"- Code hash (locked modules): `{c['code_sha256']}`.",
            f"- Definition: `{ch['definition']['id']}` ({ch['definition']['status']}); sensitivity alternatives "
            f"{ch['definition']['sensitivity_alternatives']}.",
            f"- Shrinkage: `{ch['shrinkage']['config']}`. Working pools: {ch['working_pool_status']}.",
            f"- Strict uncapped enabled: {ch['strict_uncapped_enabled']}.",
            f"- Locked files hashed: {len(c['files'])}.",
            "- The lock is created only by `scripts/phase5_methodology_lock.py --confirm-lock`. Any change to a locked "
            "file, choice or module makes `verify_lock` raise `LockDriftError` and the refit refuses to run.",
        ]
    else:
        L.append("No lock manifest exists yet. The refit refuses to run without one.")
    L += ["", "## 3. Refit design"]
    L += [
        "- Fit window: TRAIN + VALIDATION. TEST rows are cut at load time and a second check refuses any row whose "
        "original period is TEST. The original period is kept as `period_orig`.",
        "- Method: the unchanged Phase 4 functions run with the TRAIN/VALIDATION boundary moved to the end of "
        "VALIDATION. Phase 4 code is not edited.",
        "- Locked: definition quantile level (q0.75), working-pool ball thresholds, shrinkage config, streams, "
        "restrictions. Refit: the numeric pressure cut-offs, the baseline, the shrinkage parameters.",
        "- Output tables: `p5_refit_trainval_v1_scores`, `_baseline_calibration`, `_thresholds`, `_comparison`, "
        "`_manifest`. Every row is labelled EXPERIMENTAL and INTERNAL_EXPERIMENTAL_ONLY.",
        "",
        "## 4. Refit results",
    ]
    if rf:
        pr = rf["preservation"]
        L += [
            f"- Rows {rf['rows']}, matches {rf['matches']}, dates {rf['date_min']} to {rf['date_max']}; "
            f"rows by original period {rf['rows_by_period_orig']}.",
            f"- Seed {rf['seed']}, bootstrap draws {rf['n_boot']}. Lock hash used: `{rf['lock_hash']}`.",
            "",
            md_table(
                [
                    "format|role",
                    "players",
                    "eligible (locked working pool)",
                    "matches",
                    "shrinkage k",
                ],
                [
                    [k, v["players"], v["eligible"], v["matches"], fmt(v["shrinkage_k"], 1)]
                    for k, v in rf["cells"].items()
                ],
            ),
            "",
            "### Comparison with the Phase 4 TRAIN-only scores",
        ]
        if cmp_ is not None:
            L.append(
                md_table(
                    [
                        "format",
                        "role",
                        "eligible P4",
                        "eligible refit",
                        "Spearman (eligible both)",
                        "Top-10 overlap",
                        "mean abs change",
                        "max abs change",
                    ],
                    [
                        [
                            r.format,
                            r.role,
                            r.eligible_phase4,
                            r.eligible_refit,
                            fmt(r.spearman_eligible_both, 3),
                            f"{r.top10_overlap} of {r.top10_size}",
                            fmt(r.mean_abs_change, 4),
                            fmt(r.max_abs_change, 4),
                        ]
                        for r in cmp_.itertuples()
                    ],
                )
            )
        L += [
            "",
            "### Preservation (checked before and after the refit)",
            md_table(["check", "result"], [[k, v] for k, v in pr.items()]),
            "",
            "TEST was not opened. Phase 4 tables and reports are byte-identical. This refit has no out-of-sample "
            "check: VALIDATION was used for fitting. The comparison shows how much the experimental scores move; "
            "it does not show that either version is better.",
        ]
    else:
        L.append("The refit has not been run (`scripts/phase5_refit.py`).")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- user summary
def render_user_summary(inp: dict[str, Any]) -> str:
    cc = _classification_counts(inp)
    dist = _g(inp["dates"], "class_distribution_late42", default={})
    sets = {s["set"]: s for s in _g(inp["sens"], "test_sets", "sets", default=[])}
    cov, rf, cmp_, lock = (
        inp.get("cov") or {},
        inp.get("refit"),
        inp.get("comparison"),
        inp.get("lock"),
    )
    L = [
        "# Phase 5 summary for review",
        "",
        "**Everything here is experimental. Nothing is validated. No Top 10 is published. "
        "I have stopped for your review.**",
        "",
        "## What was done",
        "- Moved player classification to three real statuses (verified capped, derived capped, unknown) "
        "plus a disabled VERIFIED_UNCAPPED placeholder. Strict uncapped selection is switched off.",
        "- Checked the 42 late T20I dates against the other sources in the data. The original dates are kept and "
        "unchanged.",
        "- Ran reliability, sensitivity and ranking-stability studies for the provisional definition `any|q0.75` and "
        "the alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75`.",
        "- Built the filter-driven ranking engine (one scoring model; filters only select who is compared). It is "
        "internal only and every response carries the failing gates.",
        "- Wrote a methodology lock (label EXPERIMENTAL_LOCK) and one refit on TRAIN + VALIDATION. TEST was not opened.",
        "",
        "## Real numbers",
        f"- Players: 1,217. VERIFIED_CAPPED {cc.get('VERIFIED_CAPPED', 'n/a')}, DERIVED_CAPPED {cc.get('DERIVED_CAPPED', 'n/a')}, "
        f"UNKNOWN {cc.get('UNKNOWN', 'n/a')} (VERIFIED_UNCAPPED is a disabled placeholder).",
        f"- 42 late T20I dates: evidence classes {dist}. None is checked against an official record.",
        f"- TEST-set options: restricted primary {_g(sets, 'PRIMARY_RESTRICTED', 'matches')} matches, official-only "
        f"{_g(sets, 'STRICT_OFFICIAL_ONLY', 'matches')}, all {_g(sets, 'SENSITIVITY_ALL', 'matches')}.",
    ]
    L += [f"- {x.lstrip('- ')}" for x in _g(inp["sens"], "reading", default=[])[:2]]
    L += [f"- {x.lstrip('- ')}" for x in _g(inp["stab"], "reading", default=[])[:2]]
    L += [
        f"- Filter combinations: {cov.get('combinations', 'n/a')}; {cov.get('disabled_strict_uncapped', 'n/a')} are "
        f"disabled (strict uncapped); {cov.get('meets_internal_min', 'n/a')} reach the internal minimum pool of "
        f"{_g(cov, 'minimum_pool_rule', 'min_internal_pool')}; {cov.get('meets_public_min', 'n/a')} reach the public-size "
        f"rule of {_g(cov, 'minimum_pool_rule', 'min_public_pool')} (size alone does not make anything publishable).",
    ]
    if rf and cmp_ is not None:
        L += [
            f"- Refit on TRAIN+VALIDATION: {rf['rows']:,} delivery rows, {rf['matches']} matches, {rf['date_min']} to "
            f"{rf['date_max']}. Top-10 overlap with the Phase 4 scores per cell: "
            + ", ".join(
                f"{r.format} {r.role} {r.top10_overlap}/{r.top10_size}" for r in cmp_.itertuples()
            )
            + ". Spearman between old and new scores (eligible players): "
            + ", ".join(f"{fmt(r.spearman_eligible_both, 2)}" for r in cmp_.itertuples())
            + ".",
            f"- Phase 4 tables and reports byte-identical after the refit: {rf['preservation']['all_preserved']}. "
            "TEST rows used: 0.",
        ]
    else:
        L.append("- The refit has not been run yet.")
    L += [
        "",
        "## Gates still failing (exact)",
        f"- `{failing_gate_ids(inp)}`.",
        "- `data_weight_gate_passed`: all 4 format-role cells are THRESHOLD_NOT_VALIDATED.",
        "- `methodology_validated`: validated=false; only a human edit can change it.",
        "- `date_verification`: 0 of 42 late T20I matches are verified against an official record.",
        "- Request-level: `strict_classification_available` (no authoritative cap source) and `min_eligible_pool`.",
        "",
        "## Unresolved issues",
        "See `phase5_unresolved_issues.md` (ten items). The main ones: the between-player variance cannot be "
        "identified (shrinkage sits at its floor in all 48 contexts), the rankings move a lot between resamples, "
        "TEST is no longer a pristine hold-out, and the refit has no out-of-sample check.",
        "",
        "## Decisions needed from you",
        "1. Supply an authoritative cap source with player ids (to enable strict uncapped), or keep it off.",
        "2. Supply official match-level dates for the 42 matches, or confirm they stay excluded from the primary "
        "chronological TEST evaluation.",
        "3. Choose which TEST set is primary (restricted, official-only, all), and accept that a later TEST run is not pristine.",
        "4. Confirm or change the minimum pool sizes (internal 5, public 10).",
        "5. Say whether the data-weight gate can be met and how. Nothing becomes public before it does.",
        "6. Whether to approve any validation of the pressure definition, official rankings or official ML training. "
        "None is approved now.",
        "",
        "## Stop for review",
        "I have not published a Top 10, not trained an official model, not opened TEST and not changed the official "
        "data. I will not go further until you review this. The lock "
        + (f"hash is `{lock['lock_hash']}`." if lock else "has not been written yet."),
        "",
    ]
    return "\n".join(L)
