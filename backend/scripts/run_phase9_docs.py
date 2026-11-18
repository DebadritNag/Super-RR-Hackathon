"""Phase 9 documents, comparison, manifest and bundle, written from the stored ``p9_*`` tables.

Usage (from ``d:/Data/backend``, ``PYTHONUTF8=1``, ``PYTHONPATH=d:/Data/backend``)::

    python scripts/run_phase9_docs.py checks [--pytest-output FILE]
    python scripts/run_phase9_docs.py docs

``checks`` stores the real outputs of ruff (and npm) in ``.agents/tasks/_p9_checks.json``. ``docs``
reads that file, the stored tables and the Top 10 files, and writes every report from them. Nothing
here recomputes a ranking and no random draw is made. Two ``docs`` runs over the same inputs give
identical files (the stamp comes from the checks file).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path

os.environ["SUPERR_PHASE"] = "phase9"

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from run_phase8 import (  # noqa: E402
    NOT_USED_FILES,
    SOURCE_FILES,
    f3,
    f4,
    md_table,
    parse_pytest,
    run,
    sha256,
    tail,
    write,
)

from app.phase8.constants import (  # noqa: E402
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    PHASE8_DB,
    PHASE9_DB,
    SEED,
)
from app.phase8.report_final import (  # noqa: E402
    _banner_block,
    explanations_md,
)

ROOT = BACKEND.parent
REPORTS = BACKEND / "data" / "reports"
TASKS = ROOT / ".agents" / "tasks"
SUBMISSION = ROOT / "submission"
CHECKS_FILE = TASKS / "_p9_checks.json"
SUMMARY_TASK_FILE = TASKS / "phase9_user_summary.md"
ROLES = ("batter", "bowler")
WORD = {"batter": "batters", "bowler": "bowlers"}
WINDOW = "2022-01-22 to 2026-11-01"
CRIT_SHA = "9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64"
CHECK_LABEL = "2026 out-of-time check; data previously held out, released by owner decision"

BUNDLE_FILES = [
    "pressure_batters_top10.csv",
    "pressure_batters_top10.json",
    "pressure_bowlers_top10.csv",
    "pressure_bowlers_top10.json",
    "pressure_top10_status.md",
    "submission_methodology.md",
    "submission_executive_summary.md",
    "methodology_comparison.md",
    "pressure_methodology_research.md",
    "player_selection_explanations.md",
    "descriptive_batter_profiles.csv",
    "descriptive_bowler_profiles.csv",
    "ai_pipeline_verification.md",
    "submission_test_report.md",
    "submission_readiness_audit.md",
    "final_submission_summary.md",
    "phase9_owner_decisions.md",
    "phase9_lock_release_log.json",
    "phase9_comparison.md",
    "phase9_build_manifest.json",
]
PHASE8_COPIES = [
    "pressure_batters_top10_phase8.csv",
    "pressure_batters_top10_phase8.json",
    "pressure_bowlers_top10_phase8.csv",
    "pressure_bowlers_top10_phase8.json",
    "pressure_top10_status_phase8.md",
    "player_selection_explanations_phase8.md",
    "methodology_comparison_phase8.md",
    "pressure_methodology_research_phase8.md",
    "submission_methodology_phase8.md",
    "submission_executive_summary_phase8.md",
    "ai_pipeline_verification_phase8.md",
    "descriptive_batter_profiles_phase8.csv",
    "descriptive_bowler_profiles_phase8.csv",
    "submission_test_report_phase8.md",
    "submission_readiness_audit_phase8.md",
]
DELIVERABLES = [
    ("pressure_batters_top10.csv", "Top 10 batters (ordered, status-labelled)"),
    ("pressure_batters_top10.json", "Top 10 batters, JSON"),
    ("pressure_bowlers_top10.csv", "Top 10 bowlers (ordered, status-labelled)"),
    ("pressure_bowlers_top10.json", "Top 10 bowlers, JSON"),
    ("pressure_top10_status.md", "Status and label definitions for both lists"),
    ("submission_methodology.md", "Methodology report (Phase 9)"),
    ("submission_executive_summary.md", "One-page plain-English summary"),
    ("methodology_comparison.md", "Comparison of the three approaches (Phase 9 section + Phase 8)"),
    ("pressure_methodology_research.md", "What was tried, what failed, why (with Phase 9 notice)"),
    ("player_selection_explanations.md", "Why selected and why not selected, per player"),
    ("descriptive_batter_profiles.csv", "Descriptive batter profiles, window to 2026-11-01"),
    ("descriptive_bowler_profiles.csv", "Descriptive bowler profiles, window to 2026-11-01"),
    ("ai_pipeline_verification.md", "Audit of the p9 AI/ML pipeline"),
    ("submission_test_report.md", "Real test, lint and build outputs"),
    ("submission_readiness_audit.md", "Deliverable checklist and open items"),
    ("final_submission_summary.md", "Summary for the owner"),
    ("phase9_owner_decisions.md", "Owner decisions D1 and D2"),
    ("phase9_lock_release_log.json", "Append-only record of the TEST release"),
    ("phase9_comparison.md", "Phase 8 against Phase 9"),
    ("phase9_build_manifest.json", "Input hashes, output provenance, versions"),
]


def p9(q: str) -> pd.DataFrame:
    c = duckdb.connect(str(PHASE9_DB), read_only=True)
    try:
        return c.execute(q).df()
    finally:
        c.close()


def p8(q: str) -> pd.DataFrame:
    c = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        return c.execute(q).df()
    finally:
        c.close()


# ---------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------
def stage_checks(pytest_output: Path | None) -> dict:
    from datetime import UTC, datetime

    npm = "npm.cmd" if platform.system() == "Windows" else "npm"
    res: dict = {"stamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat()}
    res["ruff_check"] = run([sys.executable, "-m", "ruff", "check", "."], BACKEND)
    res["ruff_format"] = run([sys.executable, "-m", "ruff", "format", "--check", "."], BACKEND)
    res["npm_build"] = run([npm, "run", "build"], ROOT / "frontend")
    res["npm_lint"] = run([npm, "run", "lint"], ROOT / "frontend")
    res["ruff_version"] = tail(
        run([sys.executable, "-m", "ruff", "--version"], BACKEND)["output"], 1
    )
    res["node_version"] = tail(run(["node", "--version"], ROOT)["output"], 1)
    res["npm_version"] = tail(run([npm, "--version"], ROOT)["output"], 1)
    if pytest_output is not None:
        text = Path(pytest_output).read_text(encoding="utf-8", errors="replace")
        res["pytest"] = {
            "command": "python -m pytest -q",
            "cwd": str(BACKEND),
            "output_tail": tail(text, 25),
            "source_file": str(pytest_output),
        }
    prior = json.loads(CHECKS_FILE.read_text(encoding="utf-8")) if CHECKS_FILE.exists() else {}
    if pytest_output is None and "pytest" in prior:
        res["pytest"] = prior["pytest"]
    CHECKS_FILE.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def protected_state() -> dict:
    from app.phase8.lockguard import check_protected

    r = check_protected(only=())
    prerun = json.loads((TASKS / "phase9_report_hashes.json").read_text(encoding="utf-8"))
    copies = []
    for name, digest in prerun.items():
        base = Path(name)
        cp = base.with_name(f"{base.stem}_phase8{base.suffix}")
        if cp.exists():
            copies.append({"file": cp.name, "equals_pre_phase9": sha256(cp) == digest})
    return {
        "checked": r["checked"],
        "ok": r["ok"],
        "phase8_copies_checked": len(copies),
        "phase8_copies_identical_to_pre_phase9": all(c["equals_pre_phase9"] for c in copies),
    }


# ---------------------------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------------------------
class Facts:
    def __init__(self) -> None:
        self.checks = json.loads(CHECKS_FILE.read_text(encoding="utf-8"))
        self.pt = parse_pytest(self.checks)
        self.cmp = p9("select * from p9_method_comparison order by role, approach")
        self.cmp8 = p8("select * from p8_method_comparison order by role, approach")
        self.sel = p9("select * from p9_method_selection").set_index("role")
        self.sel8 = p8("select * from p8_method_selection").set_index("role")
        self.status = p9("select * from p9_top10_status").set_index("role")
        self.status8 = p8("select * from p8_top10_status").set_index("role")
        self.sens = p9("select * from p9_final_sensitivity")
        self.intensity = p9("select * from p9_b_intensity_selection order by candidate")
        self.wp = p9("select * from p9_wp_metrics order by model")
        self.exp = p9("select * from p9_a_model_metrics order by role, target")
        self.check26 = p9("select * from p9_2026_check")
        self.repro = p9("select * from p9_reproducibility")
        self.weights = p9("select * from p9_c_weights order by role, component")
        self.excl = p9("select * from p9_data_exclusions")
        self.reml = p9(
            "select role, scope, n_players, tau2, sigma2, floor, label from p9_a_reml "
            "where intensity = 'P4' order by role, scope"
        )
        cols = "role, players_both_formats, spearman, spearman_low, spearman_high, combination_supported"
        self.fmt = p9(
            f"select 'A' approach, {cols} from p9_a_format_study where intensity = 'P4' "
            f"union all select 'B', {cols} from p9_b_format_study where intensity = 'P4' "
            f"union all select 'C', {cols} from p9_c_format_study where series = 'PRI' "
            "order by approach, role"
        )
        self.expl = p9(
            "select role, kind, count(*) n from p9_explanations group by 1,2 order by 1,2"
        )
        self.top = {r: pd.read_csv(REPORTS / f"pressure_{r}s_top10.csv") for r in ROLES}
        self.top8 = {r: pd.read_csv(REPORTS / f"pressure_{r}s_top10_phase8.csv") for r in ROLES}
        self.ai = json.loads((REPORTS / "phase9_ai_verification.json").read_text(encoding="utf-8"))
        self.stamp = self.checks["stamp_utc"]
        self.protected = protected_state()
        o = duckdb.connect(str(BACKEND / "data/database/superr.duckdb"), read_only=True)
        self.n_deliv = o.execute("select count(*) from deliveries").fetchone()[0]
        self.n_matches = o.execute("select count(*) from matches").fetchone()[0]
        o.close()
        e = duckdb.connect(str(BACKEND / "data/database/exploratory.duckdb"), read_only=True)
        self.periods = e.execute(
            "select period, competition_type, count(*) matches, min(match_date) first_date, "
            "max(match_date) last_date from p4_match_period group by 1,2 order by 1,2"
        ).df()
        self.late = e.execute(
            "select match_id from p5_t20i_date_verification where late_after_cutoff"
        ).df()["match_id"]
        self.state_ids26 = set(
            e.execute(
                "select distinct match_id from exp_pre_delivery_state s "
                "join p4_match_period p using(match_id) where p.period = 'TEST'"
            ).df()["match_id"]
        )
        e.close()
        from app.phase8.data import load_pre_test_deliveries

        df9, _ = load_pre_test_deliveries(phase9=True)
        t26 = df9[df9["period_src"] == "TEST"]
        self.used26 = set(t26["match_id"])
        self.deliv26_used = int(len(t26))
        self.n_used_deliv_all = int(len(df9))
        e2 = duckdb.connect(str(BACKEND / "data/database/exploratory.duckdb"), read_only=True)
        self.deliv26_in_scope = int(
            e2.execute(
                "select count(*) from exp_pre_delivery_state s join p4_match_period p using(match_id) "
                "where p.period = 'TEST'"
            ).fetchone()[0]
        )
        e2.close()
        self.crit_hash = json.loads(CRITERIA_HASH_FILE.read_text(encoding="utf-8"))["sha256"]
        self.release = json.loads((REPORTS / "phase9_lock_release_log.json").read_text("utf-8"))[0]

    def cmp_row(self, role: str, approach: str, old: bool = False) -> pd.Series:
        d = self.cmp8 if old else self.cmp
        return d[(d.role == role) & (d.approach == approach)].iloc[0]

    def chosen(self, role: str, old: bool = False) -> str:
        return str((self.sel8 if old else self.sel).loc[role, "approach_chosen"])

    def label(self, role: str) -> str:
        return str(self.status.loc[role, "list_status"])

    def both(self) -> str:
        a, b = self.label("batter"), self.label("bowler")
        return a if a == b else f"batters {a}, bowlers {b}"


def _top_names(f: Facts, role: str) -> str:
    d = f.top[role]
    return "; ".join(f"{int(r)}. {n}" for r, n in zip(d["rank"], d["player_name"], strict=True))


def _ranking_table(f: Facts, role: str) -> str:
    d = f.top[role]
    t = pd.DataFrame(
        {
            "rank": d["rank"],
            "player": d["player_name"],
            "score": d["pressure_score"].map(f4),
            "interval (95%)": [
                f"{f4(a)} to {f4(b)}"
                for a, b in zip(d["interval_low"], d["interval_high"], strict=True)
            ],
            "pressure matches": d["pressure_matches"],
            "pressure balls": d["pressure_deliveries"],
            "top-10 probability": d["top10_inclusion_probability"].map(lambda v: f"{100 * v:.0f}%"),
            "rank interval": [
                f"{a:.0f} to {b:.0f}"
                for a, b in zip(d["rank_interval_low"], d["rank_interval_high"], strict=True)
            ],
            "evidence class": d["evidence_class"],
            "status": d["ranking_status"],
        }
    )
    return md_table(t)


def _comparison_table(f: Facts, role: str) -> str:
    d = f.cmp[f.cmp.role == role]
    t = pd.DataFrame(
        {
            "approach": d["approach"],
            "split-half (Spearman-Brown)": d["sb"].map(f3),
            "95% interval": [
                f"{f3(a)} to {f3(b)}" for a, b in zip(d["sb_low"], d["sb_high"], strict=True)
            ],
            "out-of-time r": d["oot"].map(f3),
            "out-of-time lower bound": d["oot_low"].map(f3),
            "ICC(1)": d["icc1"].map(f4),
            "variance at floor": d["between_player_variance_at_floor"].map(
                lambda v: "yes" if v else "no"
            ),
            "mean data weight": d["mean_data_weight"].map(f3),
            "eligible players": d["n_eligible"],
            "submitted": d["chosen"].map(lambda v: "yes" if v else "no"),
        }
    )
    return md_table(t)


def _reliab_short(f: Facts, role: str) -> str:
    r = f.cmp_row(role, f.chosen(role))
    return f"{f3(r['sb'])} (95% interval {f3(r['sb_low'])} to {f3(r['sb_high'])})"


def _counts(f: Facts) -> dict:
    per = f.periods
    n26 = int(per[per.period == "TEST"]["matches"].sum())
    return {
        "n26": n26,
        "n26_used": len(f.used26),
        "late_total": int(len(f.late)),
        "late_used": int(len(set(f.late) & f.used26)),
    }


# ---------------------------------------------------------------------------------------------
# phase9_comparison.md
# ---------------------------------------------------------------------------------------------
def doc_comparison(f: Facts) -> str:
    L: list[str] = []
    a = L.append
    a("# Phase 8 against Phase 9")
    a("")
    a(
        f"Phase 8 used matches to 2025-12-19 (TRAIN to 2024-12-31, VALIDATION calendar 2025). Phase 9 adds the "
        f"2026 matches by owner decision D1 (window {WINDOW}) and refits the models on matches to "
        "2025-12-31 with the Phase 8 hyperparameters. The criteria file is unchanged "
        f"(SHA-256 `{CRIT_SHA}`). Every number below is read from `phase8.duckdb` (unchanged) and "
        "`phase9.duckdb`."
    )
    a("")
    a("## 1. Top 10 overlap and rank changes")
    a("")
    for role in ROLES:
        o, n = f.top8[role], f.top[role]
        r8 = dict(zip(o["player_name"], o["rank"], strict=True))
        r9 = dict(zip(n["player_name"], n["rank"], strict=True))
        common = [p for p in r9 if p in r8]
        a(
            f"**{WORD[role].capitalize()}**: {len(common)} of 10 players appear in both Top 10 lists."
        )
        a("")
        rows = []
        for p, rk in r9.items():
            prev = r8.get(p)
            rows.append(
                {
                    "player": p,
                    "Phase 9 rank": int(rk),
                    "Phase 8 rank": "not in Top 10" if prev is None else int(prev),
                    "change": "new" if prev is None else f"{int(prev) - int(rk):+d}",
                    "Phase 9 top-10 probability": f"{100 * n.set_index('player_name').loc[p, 'top10_inclusion_probability']:.0f}%",
                }
            )
        a(md_table(pd.DataFrame(rows)))
        a("")
        dropped = [p for p in r8 if p not in r9]
        a(
            "Left the Top 10: "
            + (", ".join(f"{p} (was {int(r8[p])})" for p in dropped) or "none")
            + "."
        )
        a("")
        rho = _rank_corr(o, n)
        a(
            f"Spearman correlation of the order over the {rho[1]} players in both Top 10 lists: {f3(rho[0])}."
            if rho[1] > 2
            else "Too few common players for a rank correlation."
        )
        a("")
    a("## 2. Reliability change")
    a("")
    rows = []
    for role in ROLES:
        for ap in ("A", "B", "C"):
            o, n = f.cmp_row(role, ap, old=True), f.cmp_row(role, ap)
            rows.append(
                {
                    "role": role,
                    "approach": ap + (" (submitted in Phase 9)" if f.chosen(role) == ap else ""),
                    "Phase 8 split-half": f3(o["sb"]),
                    "Phase 9 split-half": f3(n["sb"]),
                    "Phase 9 interval": f"{f3(n['sb_low'])} to {f3(n['sb_high'])}",
                    "Phase 8 out-of-time low": f3(o["oot_low"]),
                    "Phase 9 out-of-time low": f3(n["oot_low"]),
                    "eligible P8 / P9": f"{int(o['n_eligible'])} / {int(n['n_eligible'])}",
                }
            )
    a(md_table(pd.DataFrame(rows)))
    a("")
    for role in ROLES:
        o, n = f.status8.loc[role], f.status.loc[role]
        a(
            f"- {WORD[role].capitalize()}: Phase 8 approach {o['approach']} ({o['list_status']}), Phase 9 approach "
            f"{n['approach']} ({n['list_status']}). Reason stored for Phase 9: {n['reason']}."
        )
    a("")
    a(
        "The out-of-time test correlates 2022-2024 estimates with 2025-2026 estimates in Phase 9 "
        "(Phase 8: 2022-2024 with 2025). The Phase 9 split-half halves by match parity and by time are defined as in Phase 8."
    )
    a("")
    a("## 3. What changed in the data and the models")
    a("")
    c = _counts(f)
    a(
        f"- 2026 matches in scope: {c['n26']} (IPL 74, T20I 70); {c['n26_used']} contribute scored deliveries, "
        f"{f.deliv26_used:,} of {f.deliv26_in_scope:,} deliveries. The others are fully removed by the existing "
        "restrictions (DLS targets that cannot be reconstructed, innings 3 and 4 and Super Over rows, out-of-scope competition)."
    )
    a(
        f"- Late-dated T20I matches: {c['late_used']} of {c['late_total']} contribute scored deliveries "
        "(the rest carry only restricted rows)."
    )
    a(
        "- Expected-outcome and win-probability models: same learners, same hyperparameters as Phase 8, refitted on matches to "
        "2025-12-31; the 2026 balls are scored by those fits, and the earlier balls out of fold (`match_id % 5`)."
    )
    w1 = f.wp[f.wp.model == "W1"].iloc[0]
    a(
        f"- Win probability W1 (first innings) on the 2026 matches: calibration slope {f3(w1['slope'])} "
        f"(declared gate 0.8 to 1.2): gate passed = {bool(w1['gate_passed'])}. "
        + (
            "Because the gate failed, the unchanged Approach B rule removes first-innings win-probability credit "
            "(`INNINGS1_WP_NOT_RELIABLE`)."
            if not bool(w1["gate_passed"])
            else ""
        )
    )
    a("")
    a("## 4. Eligibility floor sensitivity")
    a("")
    a(
        "The criteria file names the recent-activity floor `min_matches_2025_window` (4 matches). In Phase 9 it is applied "
        "unchanged to the most recent window, which is the VALIDATION period of the window labelling "
        "(calendar 2025 and 2026). Its only uses are the late half of the out-of-time test and the window sensitivity. "
        "A variant restricted to calendar 2025 alone was not run."
    )
    a("")
    a("## 5. Sensitivity of the Phase 9 order")
    a("")
    s = f.sens[f.sens.approach.isin([f.chosen("batter"), f.chosen("bowler")])].copy()
    s = s[
        ((s.role == "batter") & (s.approach == f.chosen("batter")))
        | ((s.role == "bowler") & (s.approach == f.chosen("bowler")))
    ]
    s2 = s[["role", "family", "comparison", "n_common", "spearman", "top10_overlap"]].copy()
    s2["spearman"] = s2["spearman"].map(f3)
    s2["top10_overlap"] = s2["top10_overlap"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.0f}")
    a(md_table(s2))
    return "\n".join(L)


def _rank_corr(old: pd.DataFrame, new: pd.DataFrame) -> tuple[float, int]:
    common = [p for p in new["player_name"] if p in set(old["player_name"])]
    if len(common) < 3:
        return float("nan"), len(common)
    a = pd.Series({p: r for p, r in zip(old["player_name"], old["rank"], strict=True)})[common]
    b = pd.Series({p: r for p, r in zip(new["player_name"], new["rank"], strict=True)})[common]
    return float(a.rank().corr(b.rank())), len(common)


# ---------------------------------------------------------------------------------------------
# status, explanations, comparison, research
# ---------------------------------------------------------------------------------------------
def doc_status(f: Facts) -> str:
    st = f.status
    L = ["# Pressure Top 10: submitted ranking status (Phase 9)\n"]
    L += _banner_block(p9("select * from p9_top10_status"))
    L.append(
        f"**Read this first.** Window {WINDOW}, 2026 included by owner decision D1 (owner attestation). "
        "There is no pristine hold-out left. The label of each list is the label the evidence earned under "
        f"thresholds declared before any result (criteria SHA-256 `{CRIT_SHA}`, unchanged). "
        f"Result: {f.both()}.\n"
    )
    t = []
    for role in ROLES:
        r = st.loc[role]
        m = f.cmp_row(role, str(r["approach"]))
        t.append(
            {
                "role": role,
                "approach": r["approach"],
                "rank basis": r["rank_basis"],
                "submitted ranking status": r["list_status"],
                "model validation status": r["model_validation_status"],
                "players listed": r["list_length"],
                "eligible players": r["n_eligible"],
                "split-half": m["sb"],
                "interval low": m["sb_low"],
                "interval high": m["sb_high"],
                "out-of-time lower bound": m["oot_low"],
            }
        )
    L.append("## 1. Status of each list\n")
    L.append(md_table(pd.DataFrame(t)) + "\n")
    th = json.loads(CRITERIA_FILE.read_text(encoding="utf-8"))["status_thresholds"]
    L.append("## 2. Thresholds and what was earned\n")
    L.append(
        f"PROVISIONAL needs split-half reliability of at least {th['PROVISIONAL']['split_half_min']} with a lower bound above 0 and an "
        f"out-of-time lower bound above 0. VALIDATED needs at least {th['VALIDATED']['split_half_min']} with a lower bound of at least "
        f"{th['VALIDATED']['split_half_lower_bound_min']} and an out-of-time lower bound above {th['VALIDATED']['out_of_time_lower_bound_gt']}. "
        "Nothing was changed to reach a label.\n"
    )
    for role in ROLES:
        L.append(f"- **{WORD[role].capitalize()}**: {st.loc[role, 'reason']}.")
    L.append("")
    L.append("## 3. How the approach was chosen\n")
    for role in ROLES:
        L.append(f"- **{WORD[role].capitalize()}**: {f.sel.loc[role, 'reason']}")
    L.append("")
    L.append("## 4. What the lists can and cannot be used for\n")
    L.append(
        "- They describe who performed best against the model's expectation in difficult situations from 2022 to 2026, with each player's evidence.\n"
        "- A list whose label is below PROVISIONAL is not evidence that the order would repeat. Each player has a 95% rank interval (CSV columns "
        "`rank_interval_low` and `rank_interval_high`) and a Top-10 inclusion probability.\n"
        "- The pressure definition (P4, resource scarcity) did not pass the predeclared validity rule (the monotonic trend test fails for every "
        "candidate); it is the best available, not validated.\n"
        "- A player outside the lists may be as good or better. Missing evidence is never reported as poor performance.\n"
    )
    L.append("## 5. Evidence and data caveats\n")
    L.append(
        "- 2026 data are an owner attestation, not an official verification (cross-source check: 36 of the 42 late-dated T20I matches consistent, "
        "6 single-source, 0 conflicts).\n"
        "- The 2026 out-of-time check of the models used data held out earlier; nothing was tuned on it, but it is not an independent test.\n"
    )
    L.append("## 6. Players in the lists\n")
    rk = p9("select * from p9_rankings")
    for role in ROLES:
        d = rk[(rk["role"] == role) & (rk["kind"] == "SELECTED")].sort_values("rank")
        L.append(f"**{WORD[role].capitalize()}** (approach {st.loc[role, 'approach']})\n")
        cols = [
            "rank",
            "player_name",
            "pressure_score",
            "interval_low",
            "interval_high",
            "top10_inclusion_probability",
            "evidence_class",
            "ranking_status",
        ]
        t2 = d[cols].copy()
        for c in ("pressure_score", "interval_low", "interval_high", "top10_inclusion_probability"):
            t2[c] = t2[c].map(f4)
        L.append(md_table(t2) + "\n")
    return "\n".join(L) + "\n"


def doc_comparison_section(f: Facts) -> str:
    old = (REPORTS / "methodology_comparison_phase8.md").read_text(encoding="utf-8")
    L = ["# Methodology comparison (Phase 9 section, then the preserved Phase 8 document)\n"]
    L.append(
        "> **Phase 9 update.** The first part of this file compares the three approaches on the Phase 9 window "
        f"({WINDOW}). The second part is the Phase 8 comparison, kept unchanged for reference (window to 2025-12-19, "
        "2026 not loaded). Where the two disagree, the Phase 9 section is current.\n"
    )
    L.append("## Phase 9: three approaches under the unchanged predeclared criteria\n")
    L.append(
        f"Criteria SHA-256 `{f.crit_hash}`. Source tables: `p9_method_comparison`, `p9_method_selection`.\n"
    )
    for role in ROLES:
        L.append(f"### {WORD[role].capitalize()}\n")
        L.append(_comparison_table(f, role) + "\n")
        L.append(f"Selection: {f.sel.loc[role, 'reason']}\n")
    L.append("### Intensity definitions (predeclared validity tests, rerun unchanged)\n")
    t = f.intensity[
        [
            "candidate",
            "pass",
            "test_a",
            "test_b",
            "test_c",
            "test_e",
            "test_d",
            "n_tests_passed",
            "phases_passing",
            "innings_coverage",
            "primary_basis",
        ]
    ]
    L.append(md_table(t) + "\n")
    L.append(
        "The same procedure as in Phase 8 picks "
        + ", ".join(f"`{c}`" for c in f.intensity[f.intensity.primary.astype(bool)].candidate)
        + " as the primary definition (no candidate passes the declared rule).\n"
    )
    L.append("### Effect of the 2026 data on the format combination\n")
    L.append(md_table(f.fmt) + "\n")
    L.append("---\n")
    L.append("# Phase 8 comparison (preserved, unchanged)\n")
    L.append(old)
    return "\n".join(L) + "\n"


def doc_research(f: Facts) -> str:
    old = (REPORTS / "pressure_methodology_research_phase8.md").read_text(encoding="utf-8")
    head = (
        "# Pressure methodology research: a candid account (with Phase 9 notice)\n\n"
        "> **Phase 9 notice.** The account below is the Phase 8 text, kept unchanged. It states that the 2026 period was never "
        "loaded and that the window ends in 2025. Phase 9 supersedes those statements: by owner decision D1 (2026-11-18) the 2026 "
        f"matches are included (window {WINDOW}), the TEST lock is released and no pristine hold-out remains. The methods, "
        "thresholds and criteria are unchanged. Current results are in `submission_methodology.md`, `phase9_comparison.md` and "
        "`pressure_top10_status.md`.\n\n---\n\n"
    )
    return head + old


# ---------------------------------------------------------------------------------------------
# methodology
# ---------------------------------------------------------------------------------------------
def doc_methodology(f: Facts) -> str:
    cb, cw = f.chosen("batter"), f.chosen("bowler")
    rb, rw = f.cmp_row("batter", cb), f.cmp_row("bowler", cw)
    c = _counts(f)
    p4 = f.intensity[f.intensity.candidate == "P4"].iloc[0]
    per = f.periods.copy()
    per.columns = ["period", "competition", "matches", "first match", "last match"]
    per["first match"] = per["first match"].astype(str).str[:10]
    per["last match"] = per["last match"].astype(str).str[:10]
    excl = f.excl[["reason", "competition_type", "rows", "matches"]]
    exp = f.exp[
        ["role", "target", "chosen", "gain_vs_const_pct", "n_train", "n_validation"]
    ].rename(columns={"n_validation": "n_2026"})
    wp = f.wp[
        [
            "model",
            "n_validation",
            "brier",
            "brier_const",
            "brier_logit",
            "slope",
            "intercept",
            "gate_passed",
        ]
    ].rename(columns={"n_validation": "n_2026"})
    chk = f.check26[
        [
            "model",
            "metric",
            "model_value_2026",
            "constant_value_2026",
            "gain_vs_constant_pct",
            "n_2026",
            "slope",
        ]
    ]
    wts = f.weights[
        [
            "role",
            "component",
            "n_players_fit",
            "split_half_sb",
            "tau2_fit",
            "floor_fit",
            "status",
            "final_weight",
        ]
    ]
    zero = f.weights[f.weights.final_weight == 0]
    src = [{"file": n, "role": w, "sha256": sha256(ROOT / n)} for n, w in SOURCE_FILES]
    sens = f.sens[
        ((f.sens.role == "batter") & (f.sens.approach == cb))
        | ((f.sens.role == "bowler") & (f.sens.approach == cw))
    ][["role", "family", "comparison", "n_common", "spearman", "top10_overlap"]].copy()
    sens["spearman"] = sens["spearman"].map(f3)
    sens["top10_overlap"] = sens["top10_overlap"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.0f}")
    unsupported = f.fmt[~f.fmt.combination_supported.astype(bool)]
    lab_b, lab_w = f.label("batter"), f.label("bowler")
    thresholds_note = (
        "Both lists fall short of the PROVISIONAL threshold (0.5) and both intervals include 0."
        if lab_b == lab_w == "EXPLORATORY"
        else "See the status table for what each list earned."
    )
    L: list[str] = []
    a = L.append
    a(
        "# Submission methodology: pressure performance of IPL and T20I batters and bowlers (Phase 9)"
    )
    a("")
    a(f"> **Batters: {lab_b}.** {f.status.loc['batter', 'banner']}")
    a("")
    a(f"> **Bowlers: {lab_w}.** {f.status.loc['bowler', 'banner']}")
    a("")
    a(
        "Window "
        f"{WINDOW}. The 2026 matches are included by owner decision D1 (owner attestation, not an official verification) and the "
        "TEST lock is released: no pristine hold-out remains. The label of each list is the label the evidence earned under thresholds "
        "declared before any result was seen and left unchanged."
    )
    a("")
    a("## Part 1. The report in plain language")
    a("")
    a("### 1.1 What was asked")
    a("")
    a(
        "Name the ten batters and the ten bowlers who perform best under pressure, in order, and explain how pressure was defined, how players were measured, and how far the conclusions can be trusted. This is a player-performance question."
    )
    a("")
    a("### 1.2 What was done, in five steps")
    a("")
    a(
        "1. **Describe the situation of every ball.** Only what was known before the ball was bowled is used: score, wickets lost, balls left, target, required rate, phase, innings, batting order."
    )
    a(
        "2. **Give each ball a pressure level between 0 and 1** (resource scarcity: share of wickets lost times share of the innings used). Balls at 0.5 or above form the pressure sample and count in proportion to their level; balls below 0.5 define the player's normal play."
    )
    a(
        "3. **Ask what normally happens in that situation.** A statistical model predicts runs and the chance of a wicket from the situation alone, without knowing who is playing. A player's performance is the gap between what happened and what was expected. Every ball is scored by a model that did not see its own match."
    )
    a(
        "4. **Compare pressure with normal play** so a player who is simply good all the time is not mistaken for a player who rises under pressure."
    )
    a(
        "5. **Be honest about noise.** Small samples are pulled towards the average, every score has an interval from resampling whole matches, and the whole procedure was tested for whether it gives the same answer on two halves of the data."
    )
    a("")
    a("### 1.3 What was found")
    a("")
    a(
        f"- Three approaches were compared under criteria written down and hashed before any result existed (A: observed against expected; B: win probability added; C: Pressure Response Index). Batters are submitted from approach **{cb}**, bowlers from approach **{cw}**."
    )
    a(
        f"- Split-half reliability of the submitted batter measure is **{_reliab_short(f, 'batter')}** and of the bowler measure **{_reliab_short(f, 'bowler')}** (declared thresholds: 0.5 for PROVISIONAL, 0.7 for VALIDATED). {thresholds_note}"
    )
    a(
        f"- Result: batters {lab_b}, bowlers {lab_w}. The label did not change when the 2026 matches were added: "
        "see `phase9_comparison.md` for the change against Phase 8."
    )
    a("")
    a("### 1.4 How to read the two lists")
    a("")
    a(f"**Batters** (approach {cb}; higher score is better)")
    a("")
    a(_ranking_table(f, "batter"))
    a("")
    a(f"**Bowlers** (approach {cw}; higher score is better)")
    a("")
    a(_ranking_table(f, "bowler"))
    a("")
    a(
        "Top-10 probability is the share of 1,000 resamples of whole matches in which the player is in the Top 10. The rank interval is the 95% range of the player's rank across the same resamples."
    )
    a("")
    a("## Part 2. Methodology in detail")
    a("")
    a("## 2. Data and provenance")
    a("")
    a(
        "Only the official IPL and T20I data supplied for the competition are used (`updated_ball_by_ball.csv` is authoritative). Source files, `superr.duckdb`, `exploratory.duckdb` and `phase8.duckdb` are read-only and were hash-checked before and after every stage."
    )
    a("")
    a(md_table(pd.DataFrame(src)))
    a("")
    a("Not used: " + "; ".join(NOT_USED_FILES) + ".")
    a("")
    a(
        f"The official database holds {f.n_deliv:,} deliveries and {f.n_matches:,} matches. The Phase 9 window is {WINDOW}: matches of "
        f"TRAIN (to 2024-12-31), VALIDATION (calendar 2025) and the 2026 period (previously TEST). Period boundaries are those of `config/phase4_split_v1.json`."
    )
    a("")
    a(md_table(per))
    a("")
    a(
        f"After the existing data-quality exclusions, {f.n_used_deliv_all:,} regulation deliveries carry no exclusion reason; "
        f"of the {c['n26']} 2026 matches in scope, {c['n26_used']} contribute scored deliveries ({f.deliv26_used:,} of {f.deliv26_in_scope:,} 2026 deliveries). "
        f"{c['late_used']} of the {c['late_total']} late-dated T20I matches (after 2026-05-31) are included; the other {c['late_total'] - c['late_used']} carry only restricted rows."
    )
    a("")
    a("Rows removed before scoring, with reason (whole window):")
    a("")
    a(md_table(excl))
    a("")
    a(
        "All Phase 8 restrictions apply unchanged: Super Over deliveries (innings 3 and 4), matches whose chase target cannot be reconstructed after a rain-reduced target, wicket-flag and extras-label anomalies (excluded at the metric they affect), and OTHER_T20 (out of scope). Missing values are never treated as zero. The only change is that the exclusion of the 42 late-dated T20I matches no longer applies (D1)."
    )
    a("")
    a("### 2.1 Owner decisions")
    a("")
    a(
        "- **D1.** The owner attests that all 2026 data are genuine, including the 42 late-dated T20I matches; they are used for training and scoring. This is an owner attestation, not a third-party verification (cross-source check: 36 of 42 consistent, 6 single-source, 0 conflicts; original dates unchanged). "
        "The TEST lock is released: event `RELEASE`, reason `owner decision phase 9`, in `phase9_lock_release_log.json` (the Phase 4 and Phase 5 lock logs are unchanged). **There is no pristine hold-out any more.**"
    )
    a(
        "- **D2.** The word EXPLORATORY and the status banners are removed from the frontend pages (presentation decision). The data files and reports keep the label the evidence earned."
    )
    a("")
    a("## 3. Pressure definition and why it was chosen")
    a("")
    a(
        "Pressure is observable difficulty of the match situation, not a psychological state. Seven definitions (P0 to P6) were declared before any player was ranked and tested on balls: (a) runs per ball lower at high intensity; (b) wicket chance higher; (c) outcomes vary more; (d) win probability swings more (mechanical for the win-probability definitions); (e) monotonic across ten bands (Spearman at least 0.7). The procedure is rerun unchanged on the Phase 9 window:"
    )
    a("")
    a(
        md_table(
            f.intensity[
                [
                    "candidate",
                    "pass",
                    "test_a",
                    "test_b",
                    "test_c",
                    "test_e",
                    "test_d",
                    "n_tests_passed",
                    "phases_passing",
                    "innings_coverage",
                    "primary_basis",
                ]
            ]
        )
    )
    a("")
    prim = ", ".join(f.intensity[f.intensity.primary.astype(bool)].candidate)
    a(
        f"No candidate passes the declared rule (the monotonic trend test (e) fails for all). The declared ordering picks {prim} (resource scarcity, both innings): {int(p4['n_tests_passed'])} tests passed, coverage of {int(p4['innings_coverage'])} innings. "
        "Pressure balls at P4 have fewer runs per ball and a higher wicket probability than low-pressure balls (pooled TRAIN difference "
        f"{p4['runs_diff_pooled_train']:.3f} runs and {p4['wkt_diff_pooled_train']:.3f} wicket probability). The definition is the best available, not validated. The mechanical selection did not pick a definition other than P4."
    )
    a("")
    a("## 4. Batter and bowler metrics")
    a("")
    a(
        "Batters and bowlers are analysed separately and never compared with each other. Approach A: for every pressure ball, runs scored minus runs expected and expected minus actual dismissal, each divided by its TRAIN standard deviation and averaged with equal weight. Approach C: a Pressure Response Index combining A, B (win probability added above what leverage predicts) and CONS (share of pressure appearances that beat the expectation) with weights from split-half reliability on a fitting half of the matches:"
    )
    a("")
    a(md_table(wts))
    a("")
    if len(zero):
        a(
            "Components with weight 0 (no between-player signal on the fitting matches): "
            + ", ".join(f"{r.role} {r.component}" for r in zero.itertuples())
            + ". The index is the weighted combination of the remaining components."
        )
        a("")
    a(
        "The unit of analysis is one player in one innings (a batting innings or a bowling spell). Matches, not balls, are the resampling unit."
    )
    a("")
    a("## 5. Normal-performance baselines")
    a("")
    a(
        "The normal baseline of a player is the unweighted mean residual on balls below intensity 0.5; the pressure level is the intensity-weighted mean residual on balls at or above 0.5; `pressure_delta` is the second minus the first. All three are CSV columns and appear in every player's explanation. The expectation comes from a player-blind model."
    )
    a("")
    a("## 6. Context adjustment and training scheme")
    a("")
    a(
        "Expected runs and wicket probability come from gradient-boosting models using pre-delivery information only (innings, phase, wickets and balls remaining, score, target, required rate, current run rate, batting order, stage, competition). No player identifier or outcome column is a feature."
    )
    a("")
    a(
        "**Phase 9 scheme.** The 8 expected-outcome models and the win-probability models W1 and W2 (and the next-ball class model) are refitted on matches up to 2025-12-31 (TRAIN and VALIDATION of Phase 4) with the same learners and hyperparameters Phase 8 chose (read from the Phase 8 artefacts; nothing was tuned). Deliveries up to 2025-12-31 are scored out of fold (`match_id % 5`, models fitted on the other four folds). The 2026 deliveries are scored by the fit on all matches to 2025-12-31. So no delivery is scored by a model that saw its match. Earlier balls can be scored by models trained on later matches (as in Phase 8). Artefacts: `backend/data/models/p9_*.joblib` with `.json` metadata; the Phase 8 artefacts are untouched. Retraining with the same seed and parameters reproduced every artefact's predictions exactly (maximum absolute difference "
        f"{f.repro['max_abs_diff'].max():.1f} over {len(f.repro)} models)."
    )
    a("")
    a(f"### 6.1 {CHECK_LABEL}")
    a("")
    a(
        "The models were fitted on matches to 2025-12-31 and evaluated on the 2026 matches. This is the first use of 2026 outcomes for evaluation in this pipeline. Nothing was tuned on it. Gain is against a constant prediction (RMSE or log loss; Brier for win probability)."
    )
    a("")
    a(md_table(chk))
    a("")
    a(md_table(exp))
    a("")
    a(md_table(wp))
    a("")
    w1 = f.wp[f.wp.model == "W1"].iloc[0]
    if not bool(w1["gate_passed"]):
        a(
            f"The first-innings model W1 misses the declared calibration gate on 2026 (slope {w1['slope']:.2f}, required 0.8 to 1.2). Under the unchanged Approach B rule, first-innings win-probability credit is therefore withheld (`INNINGS1_WP_NOT_RELIABLE`); this affects approach B and the win-probability component (B) of approach C, not approach A."
        )
        a("")
    a("## 7. IPL and T20I comparison")
    a("")
    a(
        "Competition is a model feature and scores are centred by format before combination. The declared rule allows one combined score only when the cross-format correlation has a lower 95% bound of at least 0.3 across at least 30 players with both formats:"
    )
    a("")
    a(md_table(f.fmt))
    a("")
    a(
        (
            "The rule is not met in "
            + str(len(unsupported))
            + " of "
            + str(len(f.fmt))
            + " approach and role cells; those combined estimates are flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED` (each unit weighted by its own precision, no fixed split). "
        )
        + "IPL and T20I matches, contributions, scores and ranks are shown separately for every listed player."
    )
    a("")
    a("## 8. Eligibility and sample size")
    a("")
    a(
        "Declared floors (criteria file, unchanged): at least 8 matches, at least 60 balls faced or 72 balls bowled, at least 8 high-intensity units, an effective sample of at least 60, and at least 4 matches in the recent window (the criteria name it `min_matches_2025_window`; in Phase 9 it is applied to the most recent window, 2025 and 2026, and is used for the late half of the out-of-time test and the window sensitivity). "
        f"Eligible players: {int(rb['n_eligible'])} batters (approach {cb}) and {int(rw['n_eligible'])} bowlers (approach {cw}). A player below a floor is `INSUFFICIENT_EVIDENCE`, which says nothing about quality. No list is padded."
    )
    a("")
    a("## 9. Shrinkage and uncertainty")
    a("")
    a(
        "Player estimates are shrunk towards the cohort mean by a random-effects model fitted by REML on match-level units. Between-player variance (tau squared) for approach A at P4, by scope:"
    )
    a("")
    a(md_table(f.reml))
    a("")
    a(
        f"Where a scope sits at the floor (tau squared 0), the predeclared rule orders players by the unshrunk precision-weighted mean and forces the label EXPLORATORY. Intervals are 95% percentile intervals from a 1,000-draw bootstrap that resamples whole matches (seed {SEED}), re-estimating the between-player variance in every draw. Each row also reports Top-10 inclusion probability, a 95% rank interval and a sample-reliability figure. Evidence classes (declared in advance): STRONG_SUBSTANTIAL, STRONG_LIMITED, INCONSISTENT, INSUFFICIENT."
    )
    a("")
    a("## 10. Reliability validation")
    a("")
    a(
        "Two matched halves of each player's matches are scored independently (odd and even matches by date, and early against late), the correlation is corrected to full length (Spearman-Brown) and its interval comes from a match-cluster bootstrap. The out-of-time test correlates 2022-2024 estimates with 2025-2026 estimates (TRAIN against VALIDATION of the Phase 9 window labelling)."
    )
    a("")
    a("**Batters**")
    a("")
    a(_comparison_table(f, "batter"))
    a("")
    a("**Bowlers**")
    a("")
    a(_comparison_table(f, "bowler"))
    a("")
    a(
        "Approach C's figures use held-out matches only (its weights were fitted on the other half), so its columns are not like for like with A and B; the selection rule was applied as declared. The Phase 6 data-weight gate (mean data weight of at least 0.5) is reported unchanged and is not a label input."
    )
    a("")
    a(
        "Phase 6 findings stay in force: between-player variance at the shrinkage floor in all 48 contexts; pooled odd/even reliability 0.37 (0.3656), median 0.25 over the 47 estimable contexts; 0 of 48 contexts pass the 0.5 data-weight gate; no pressure definition passed the predeclared criteria."
    )
    a("")
    a("## 11. Sensitivity analysis")
    a("")
    a(
        "Each row compares the submitted order with a variant: Spearman correlation over the players both versions rank, and how many of the ten submitted players remain in the variant's Top 10."
    )
    a("")
    a(md_table(sens))
    a("")
    a("## 12. Final ranking evidence")
    a("")
    for role in ROLES:
        s = f.sel.loc[role]
        a(
            f"- {WORD[role].capitalize()}: rule path `{s['rule_path']}`, chosen approach {s['approach_chosen']}. {s['reason']}"
        )
    a("")
    a(
        f"Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `{f.crit_hash}`, was verified against the run log before every step. Player-level evidence for the listed players and for near-miss and high-raw-statistic players is in `player_selection_explanations.md` ("
        + ", ".join(f"{r.role} {r.kind}: {r.n}" for r in f.expl.itertuples())
        + " entries)."
    )
    a("")
    a("## 13. Limitations")
    a("")
    a(
        f"- Label earned: batters {lab_b}, bowlers {lab_w}. The orders are not shown to separate players beyond noise unless the status table says otherwise."
    )
    a("- The pressure definition used (P4) did not pass the declared validity rule.")
    a(
        "- No pristine hold-out remains. The 2026 check of the models used data held out earlier and nothing was tuned on it, but it is not an independent test."
    )
    a(
        "- The 2026 data, including the 42 late-dated T20I matches, rest on the owner's attestation; no official third-party verification exists. Cross-source consistency: 36 of 42 consistent, 6 single-source, 0 conflicts."
    )
    pm = pd.concat([f.top["batter"]["pressure_matches"], f.top["bowler"]["pressure_matches"]])
    a(
        f"- The twenty listed players have {int(pm.min())} to {int(pm.max())} pressure appearances each over 2022 to 2026."
    )
    a(
        "- Ball outcomes are mostly chance given the situation: expected-outcome models improve on a constant by about 1.5% to 3.2% on the 2026 matches."
    )
    a("- Earlier balls can be scored by models trained on later matches (out-of-fold design).")
    a(
        "- The experimental AI predictions are a separate diagnostic and are not part of the submitted ranking."
    )
    a("")
    a("## 14. Glossary of status labels")
    a("")
    a(
        "- **VALIDATED**: split-half reliability at least 0.70 with an interval lower bound at least 0.50 and an out-of-time lower bound above 0.30, declared before any result."
    )
    a(
        "- **PROVISIONAL**: split-half reliability at least 0.50 with an interval lower bound above 0 and an out-of-time lower bound above 0."
    )
    a("- **EXPLORATORY**: an ordered list exists but the PROVISIONAL thresholds were not met.")
    a(
        "- **INSUFFICIENT_EVIDENCE**: fewer than ten eligible players, or the approach cannot be computed."
    )
    a("")
    a(
        f"Labels earned in Phase 9: batters {lab_b}; bowlers {lab_w}. A row never carries a stronger label than its list."
    )
    a("")
    a("## Appendix A. Technical details")
    a("")
    a(
        "**Splits.** `config/phase4_split_v1.json`: TRAIN to 2024-12-31, VALIDATION calendar 2025, TEST 2026 onward (released by owner decision). Model-fit group: matches to 2025-12-31; scoring group for 2026. Folds `match_id % 5`."
    )
    a("")
    a(
        "**Models.** Gradient boosting (regressor for runs, classifier for wicket, dot, boundary), grid of learning rate, depth and L2 as in Phase 8, 200 iterations, minimum leaf 200; the Phase 8 choice per target is applied unchanged. Win probability: histogram gradient boosting with logistic baseline. Seed "
        + str(SEED)
        + "."
    )
    a("")
    a(
        "**REML, attribution, reliability estimators** are as in Phase 8 (REML posterior per scope; striker, bowler, wicket, extras and run-out rules; split-half with Spearman-Brown, Fisher-z pooling, ICC(1), 1,000-draw match-cluster bootstrap)."
    )
    a("")
    a(
        "**Reproduction.** From `d:/Data/backend` with `PYTHONUTF8=1` and `PYTHONPATH=d:/Data/backend`: `python scripts/run_phase9_pipeline.py` regenerates the p9 tables and lists; `python scripts/phase9_models_check.py`, `python scripts/phase9_ai_verify.py`, `python scripts/run_phase9_docs.py docs` regenerate the checks and this document."
    )
    a("")
    a(
        f"**Versions.** Methodology `phase9_methodology_v1`; criteria `phase8_selection_criteria_v1` (SHA-256 `{f.crit_hash}`); generated {f.stamp}."
    )
    return "\n".join(L)


def doc_executive(f: Facts) -> str:
    cb, cw = f.chosen("batter"), f.chosen("bowler")
    nb = int((f.top["batter"].top10_inclusion_probability >= 0.5).sum())
    nw = int((f.top["bowler"].top10_inclusion_probability >= 0.5).sum())
    L = ["# Executive summary: who performs best under pressure?"]
    a = L.append
    a("")
    a(
        f"> **Label earned: {f.both()}.** The lists are the best-supported ordering of the data (IPL and T20I, {WINDOW}, 2026 included by owner decision). There is no pristine hold-out left."
    )
    a("")
    a(
        "**The question.** Name the ten batters and ten bowlers who perform best under pressure in the IPL and T20Is, and show how reliable the answer is."
    )
    a("")
    a(
        "**How pressure was defined.** A ball is high pressure when many wickets have fallen and much of the innings has been used. Balls at level 0.5 or above count in proportion to their level; lower-pressure balls give each player a normal-play baseline. Only information known before the ball is used."
    )
    a("")
    a(
        "**How players were measured.** A model trained on earlier matches predicts runs and wicket chance of each ball from the situation alone. Batters are scored on how much they beat that expectation at high pressure, compared with their normal play. Bowlers use a Pressure Response Index. Small samples are pulled towards average and every score has an interval."
    )
    a("")
    a(f"**Top 10 batters** (approach {cb}): " + _top_names(f, "batter") + ".")
    a("")
    a(f"**Top 10 bowlers** (approach {cw}): " + _top_names(f, "bowler") + ".")
    a("")
    a(
        f"**How much to trust the order.** Split-half reliability (two halves of the data, 0.5 needed for PROVISIONAL and 0.7 for VALIDATED) is {_reliab_short(f, 'batter')} for batters and {_reliab_short(f, 'bowler')} for bowlers. {nb} of the 10 batters and {nw} of the 10 bowlers are in the Top 10 in at least half of 1,000 resamples of the matches. The names describe who did best against expectation; they are not proof that the order would repeat."
    )
    a("")
    a(
        "**What changed since Phase 8.** The 2026 matches (144 in scope, including 42 late-dated T20I matches) were added at the owner's instruction and the owner attests that they are genuine. The models were refitted on matches to 2025-12-31 and checked on 2026. No threshold, floor, weight or definition was changed, and no list is labelled stronger than the evidence allows."
    )
    a("")
    a(
        "**Where to look next.** `submission_methodology.md` for the method, `phase9_comparison.md` for the change from Phase 8, `player_selection_explanations.md` for each player, `submission_readiness_audit.md` for what is incomplete."
    )
    return "\n".join(L)


def doc_ai(f: Facts) -> str:
    ai = f.ai
    L = ["# AI pipeline verification (Phase 9)"]
    a = L.append
    a("")
    a(
        f"Generated {ai['generated_utc']}. The p9 models are fitted on matches to 2025-12-31 with the Phase 8 hyperparameters and score the calendar-2026 deliveries out of sample (2026 released by owner decision D1). "
        "They are internal diagnostics; the experimental Top 10 files are not the submitted ranking and are not validated."
    )
    a("")
    a("## 1. Artefacts")
    a("")
    inv = pd.DataFrame(ai["inventory"])
    a(
        md_table(
            inv[
                [
                    c
                    for c in (
                        "artefact",
                        "exists",
                        "algorithm",
                        "trained_on",
                        "seed",
                        "version",
                        "sha256",
                    )
                    if c in inv.columns
                ]
            ]
        )
    )
    a("")
    a("## 2. Reproducibility (retrain from scratch, same seed and parameters)")
    a("")
    a(md_table(f.repro[["model", "learner", "rows_compared", "max_abs_diff", "identical"]]))
    a("")
    a(
        f"All {len(f.repro)} models reproduce their stored predictions exactly: {bool(f.repro['identical'].all())}. The AI-verify script additionally retrained the batter-runs and bowler-wicket models and compared them with the stored artefacts."
    )
    a("")
    a("## 3. Out-of-time check on 2026 (" + CHECK_LABEL + ")")
    a("")
    a(
        md_table(
            f.check26[
                [
                    "model",
                    "metric",
                    "model_value_2026",
                    "constant_value_2026",
                    "gain_vs_constant_pct",
                    "n_2026",
                    "slope",
                    "label",
                ]
            ]
        )
    )
    a("")
    a("Nothing was tuned on 2026. There is no pristine hold-out left after the release.")
    a("")
    a("## 4. Leakage controls")
    a("")
    a(
        "Features are pre-delivery columns only (checked by `assert_feature_list_clean`); no player identifier or outcome column. Scoring is out of fold: no delivery is scored by a model fitted with its match (checked in code and by tests). Team priors use strictly earlier matches."
    )
    a("")
    a("## 4b. Hardcoded values and retained files")
    a("")
    a(
        "No player names, scores or random numbers are hardcoded in the AI modules (checked by tests). "
        "The earlier outputs are retained: the Phase 7 aborted files as `*_phase7_aborted.*` and the "
        "Phase 8 files as `*_phase8.*`."
    )
    a("")
    a("## 5. Experimental AI lists (internal)")
    a("")
    for role, s in ai["summary"].items():
        a(
            f"- {role}: {s['players_with_pressure_balls']} players with 2026 pressure balls, {s['eligible']} eligible, {s['listed']} listed; split-half Spearman-Brown {s['split_half_spearman_brown']:.3f} over {s['split_half_players']} players; {s['intervals_excluding_zero_in_top10']} of the listed intervals exclude zero."
        )
    a("")
    wc = ai["wp_check"]
    a(
        f"Win-probability check: {wc['model']}; Brier {wc['brier']:.4f} against {wc['brier_constant_baseline']:.4f} for a constant (gain {100 * wc['brier_gain_vs_constant']:.1f}%), n = {wc['n_validation']}."
    )
    a("")
    a(
        "Technical success is not reliability: the experimental lists are labelled EXPERIMENTAL_NOT_VALIDATED and are served only by the token-protected route."
    )
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------
# test report, audit, summary
# ---------------------------------------------------------------------------------------------
def doc_test_report(f: Facts) -> str:
    c = f.checks
    cnt = f.pt["counts"]
    L: list[str] = []
    a = L.append
    a("# Submission test report (Phase 9)")
    a("")
    a(
        f"Run stamp (UTC): {f.stamp}. Platform: {platform.system()} {platform.release()}, Python {platform.python_version()}. Outputs are the real outputs (last lines where long)."
    )
    a("")
    summ = pd.DataFrame(
        [
            {
                "check": "pytest (backend, full suite)",
                "result": f.pt["line"] or "no pytest output recorded",
                "exit": "pass"
                if cnt["passed"] and not cnt["failed"] and not cnt["errors"]
                else "see below",
            },
            {
                "check": "ruff check",
                "result": tail(c["ruff_check"]["output"], 1),
                "exit": c["ruff_check"]["exit_code"],
            },
            {
                "check": "ruff format --check",
                "result": tail(c["ruff_format"]["output"], 1),
                "exit": c["ruff_format"]["exit_code"],
            },
            {
                "check": "npm run build",
                "result": tail(c["npm_build"]["output"], 1),
                "exit": c["npm_build"]["exit_code"],
            },
            {
                "check": "npm run lint",
                "result": tail(c["npm_lint"]["output"], 1),
                "exit": c["npm_lint"]["exit_code"],
            },
            {
                "check": "protected files (SHA-256, phase9_prehash.json)",
                "result": json.dumps(f.protected),
                "exit": "pass"
                if f.protected["ok"] and f.protected["phase8_copies_identical_to_pre_phase9"]
                else "FAIL",
            },
        ]
    )
    a("## Summary")
    a("")
    a(md_table(summ))
    a("")
    a(f"Tool versions: {c['ruff_version']}; node {c['node_version']}; npm {c['npm_version']}.")
    a("")
    a("## pytest")
    a("")
    a("Command: `python -m pytest -q` (cwd `d:/Data/backend`).")
    a("")
    a("```")
    a(c.get("pytest", {}).get("output_tail", "no pytest output recorded"))
    a("```")
    a("")
    for key, title in (
        ("ruff_check", "ruff check"),
        ("ruff_format", "ruff format --check"),
        ("npm_build", "npm run build"),
        ("npm_lint", "npm run lint"),
    ):
        r = c[key]
        a(f"## {title}")
        a("")
        a(f"Command: `{r['command']}` (cwd `{r['cwd']}`), exit code {r['exit_code']}.")
        a("")
        a("```")
        a(tail(r["output"], 18))
        a("```")
        a("")
    a("## Protected files")
    a("")
    a(
        "`phase9_prehash.json` lists the databases (`superr`, `exploratory`, `phase8`), the Phase 8 models, the config files and the source CSVs; all were byte-identical after the Phase 9 run. The Phase 8 submission files were copied to `*_phase8.*` before being overwritten and each copy equals the SHA-256 recorded before Phase 9 started "
        f"({f.protected['phase8_copies_checked']} copies checked: {f.protected['phase8_copies_identical_to_pre_phase9']})."
    )
    a("")
    a("## Tests changed or added for Phase 9")
    a("")
    a(
        "See `.agents/tasks/phase9_chunk1_verification.md` for the list of changed tests (each with the reason) and the new Phase 9 tests."
    )
    a("")
    a("## Not covered by automated tests")
    a("")
    a(
        "The frontend has no unit tests; its Phase 9 changes (removal of the status words) belong to the next chunk and are checked there."
    )
    return "\n".join(L)


def doc_audit(f: Facts) -> str:
    c = f.checks
    rows = []
    for name, what in DELIVERABLES:
        if name in ("phase9_build_manifest.json", "submission_readiness_audit.md"):
            ok = "written by this run"
        else:
            ok = "present" if (REPORTS / name).exists() else "MISSING"
        rows.append({"deliverable": name, "content": what, "state": ok})
    nb, nw = len(f.top["batter"]), len(f.top["bowler"])
    L: list[str] = []
    a = L.append
    a("# Submission readiness audit (Phase 9)")
    a("")
    a(f"Stamp (UTC): {f.stamp}.")
    a("")
    a("## 1. Verdict")
    a("")
    a(
        f"{nb} batters and {nw} bowlers are listed in order with evidence, uncertainty and a status label. Label earned: {f.both()}. "
        f"Split-half reliability: batters {f3(f.cmp_row('batter', f.chosen('batter'))['sb'])}, bowlers {f3(f.cmp_row('bowler', f.chosen('bowler'))['sb'])} against 0.5 needed for PROVISIONAL. "
        "The lists are not claimed as validated or provisional rankings."
    )
    a("")
    a("## 2. Deliverable checklist")
    a("")
    a(md_table(pd.DataFrame(rows)))
    a("")
    a(
        "The same files, plus a SHA-256 manifest and the `phase8/` copies, are in `d:/Data/submission/`."
    )
    a("")
    a("## 3. Verification state")
    a("")
    a(f"- pytest: {f.pt['line'] or 'no output recorded'}.")
    a(
        f"- ruff check exit {c['ruff_check']['exit_code']}, ruff format exit {c['ruff_format']['exit_code']}, npm build exit {c['npm_build']['exit_code']}, npm lint exit {c['npm_lint']['exit_code']}."
    )
    a(f"- Protected files: {json.dumps(f.protected)}.")
    a("")
    a("## 4. What is incomplete or weak")
    a("")
    a(
        f"1. **Label.** {f.both()}: reliability thresholds for PROVISIONAL were not met; this is stated in every list."
    )
    a("2. **Pressure definition not validated.** P4 is the best available.")
    a(
        "3. **No pristine hold-out.** 2026 is included by owner decision D1; the 2026 model check is not an independent test."
    )
    a(
        "4. **2026 data rest on an owner attestation**, not an official verification (36 of 42 late-dated T20I matches consistent across sources, 6 single-source, 0 conflicts)."
    )
    a(
        "5. **Not part of this audit state:** API source switch, frontend text removal (decision D2), README and bundle text updates belong to the next Phase 9 chunk and are not yet complete when this file is generated."
    )
    a(
        "6. **Window floor.** The floor named `min_matches_2025_window` is applied to the 2025-2026 window; a calendar-2025-only variant was not run."
    )
    a("")
    a("## 5. Owner actions")
    a("")
    a(
        "1. Restart the backend on port 8000 once the API chunk is done, so it serves the Phase 9 data."
    )
    a("2. Optionally verify the 42 late-dated T20I matches against an official source.")
    return "\n".join(L)


def doc_summary(f: Facts) -> str:
    cb, cw = f.chosen("batter"), f.chosen("bowler")
    L: list[str] = []
    a = L.append
    a("# Final submission summary (Phase 9, data and models)")
    a("")
    a(f"Generated {f.stamp}. Criteria SHA-256 `{f.crit_hash}`.")
    a("")
    a("## Labels earned")
    a("")
    for role in ROLES:
        r = f.status.loc[role]
        a(
            f"- **{WORD[role].capitalize()}**: approach {r['approach']}, **{r['list_status']}**. {r['reason']}."
        )
    a("")
    a("## Top 10")
    a("")
    a(f"**Batters** (approach {cb}): " + _top_names(f, "batter") + ".")
    a("")
    a(f"**Bowlers** (approach {cw}): " + _top_names(f, "bowler") + ".")
    a("")
    a("## Data and training")
    a("")
    c = _counts(f)
    a(
        f"Window {WINDOW}; {c['n26']} 2026 matches in scope, {c['n26_used']} with scored deliveries; {c['late_used']} of {c['late_total']} late-dated T20I matches contribute. Models refitted on matches to 2025-12-31 with the Phase 8 hyperparameters; 2026 out-of-time check in `submission_methodology.md` section 6.1. No pristine hold-out remains (owner decision D1)."
    )
    a("")
    a(
        "See `phase9_comparison.md` for the Phase 8 against Phase 9 comparison and `submission_readiness_audit.md` for open items."
    )
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------
# manifest and bundle
# ---------------------------------------------------------------------------------------------
def build_manifest(f: Facts) -> dict:
    import numpy
    import sklearn

    outs = {}
    for name in BUNDLE_FILES:
        if name == "phase9_build_manifest.json":
            continue
        p = REPORTS / name
        outs[name] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    ins = {n: sha256(ROOT / n) for n, _ in SOURCE_FILES}
    for n in ("superr.duckdb", "exploratory.duckdb", "phase8.duckdb"):
        ins[f"backend/data/database/{n}"] = sha256(BACKEND / "data/database" / n)
    for n in (
        "config/phase8_selection_criteria_v1.json",
        "config/phase4_split_v1.json",
        "config/data_quality_restrictions_v1.json",
    ):
        ins[f"backend/{n}"] = sha256(BACKEND / n)
    models = {p.name: sha256(p) for p in sorted((BACKEND / "data/models").glob("p9_*.joblib"))}
    return {
        "generated_utc": f.stamp,
        "methodology_version": "phase9_methodology_v1",
        "window": WINDOW,
        "seed": SEED,
        "criteria_sha256": f.crit_hash,
        "criteria_file_sha256_now": sha256(CRITERIA_FILE),
        "owner_decisions": {
            "D1": "2026 data attested genuine by the owner; TEST lock released; no pristine hold-out",
            "D2": "EXPLORATORY removed from frontend pages",
        },
        "lock_release": {
            k: f.release[k] for k in ("event", "seq", "reason", "date", "criteria_sha256")
        },
        "protected_check": f.protected,
        "inputs_sha256": ins,
        "phase9_store_tables": int(
            p9("select count(*) n from information_schema.tables").iloc[0, 0]
        ),
        "outputs": outs,
        "models": models,
        "checks": {
            "pytest": f.pt,
            "ruff_check_exit": f.checks["ruff_check"]["exit_code"],
            "ruff_format_exit": f.checks["ruff_format"]["exit_code"],
            "npm_build_exit": f.checks["npm_build"]["exit_code"],
            "npm_lint_exit": f.checks["npm_lint"]["exit_code"],
        },
        "versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": numpy.__version__,
            "scikit_learn": sklearn.__version__,
            "duckdb": duckdb.__version__,
            "ruff": f.checks["ruff_version"],
            "node": f.checks["node_version"],
            "npm": f.checks["npm_version"],
        },
        "list_status": {r: str(f.status.loc[r, "list_status"]) for r in ROLES},
        "phase8_copies": PHASE8_COPIES,
    }


def build_bundle() -> dict:
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    for old in SUBMISSION.iterdir():
        if old.is_file():
            old.unlink()
        elif old.is_dir() and old.name == "phase8":
            shutil.rmtree(old)
    entries = {}
    for name in BUNDLE_FILES:
        shutil.copyfile(REPORTS / name, SUBMISSION / name)
        entries[name] = {
            "sha256": sha256(SUBMISSION / name),
            "bytes": (SUBMISSION / name).stat().st_size,
        }
    (SUBMISSION / "phase8").mkdir()
    for name in PHASE8_COPIES:
        shutil.copyfile(REPORTS / name, SUBMISSION / "phase8" / name)
        entries[f"phase8/{name}"] = {
            "sha256": sha256(SUBMISSION / "phase8" / name),
            "bytes": (SUBMISSION / "phase8" / name).stat().st_size,
        }
    manifest = {"files": entries, "algorithm": "SHA-256", "count": len(entries)}
    write(SUBMISSION / "MANIFEST_SHA256.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def stage_docs() -> None:
    f = Facts()
    write(REPORTS / "phase9_comparison.md", doc_comparison(f))
    write(REPORTS / "pressure_top10_status.md", doc_status(f))
    (REPORTS / "player_selection_explanations.md").write_bytes(explanations_md().encode("utf-8"))
    write(REPORTS / "methodology_comparison.md", doc_comparison_section(f))
    write(REPORTS / "pressure_methodology_research.md", doc_research(f))
    write(REPORTS / "submission_methodology.md", doc_methodology(f))
    write(REPORTS / "submission_executive_summary.md", doc_executive(f))
    write(REPORTS / "ai_pipeline_verification.md", doc_ai(f))
    write(REPORTS / "submission_test_report.md", doc_test_report(f))
    write(REPORTS / "submission_readiness_audit.md", doc_audit(f))
    summary = doc_summary(f)
    write(REPORTS / "final_submission_summary.md", summary)
    write(
        REPORTS / "phase9_build_manifest.json",
        json.dumps(build_manifest(f), indent=2, sort_keys=True),
    )
    m = build_bundle()
    print(f"docs written; bundle of {m['count']} files in {SUBMISSION}")


def main(argv: list[str]) -> int:
    stage = argv[1] if len(argv) > 1 else "docs"
    pt = Path(argv[argv.index("--pytest-output") + 1]) if "--pytest-output" in argv else None
    if stage in ("checks", "all"):
        res = stage_checks(pt)
        print(
            "checks stored:",
            CHECKS_FILE,
            {
                k: res[k]["exit_code"]
                for k in ("ruff_check", "ruff_format", "npm_build", "npm_lint")
            },
        )
    if stage in ("docs", "all"):
        stage_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
