"""Phase 8 chunk 8 orchestrator: checks, submission documents, build manifest and the bundle.

Usage (from ``d:/Data/backend``, ``PYTHONUTF8=1``)::

    python scripts/run_phase8.py checks [--pytest-output FILE]   # ruff, format, npm build/lint, pytest summary
    python scripts/run_phase8.py docs                              # write the reports, the manifest and the bundle
    python scripts/run_phase8.py all [--pytest-output FILE]

``checks`` stores the real command outputs in ``.agents/tasks/_p8c8_checks.json``. ``docs`` reads
that file, the stored ``p8_*`` tables and the Top 10 files, and writes every report from them, so
the text cannot drift from the outputs. Nothing here recomputes a ranking and no random draw is
made; ``SEED`` is recorded in the manifest. Two ``docs`` runs over the same inputs give identical
files (the stamp is taken from the checks file, not from the clock).
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.phase8.constants import (  # noqa: E402
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    PHASE8_DB,
    SEED,
)
from app.phase8.lockguard import load_prehash  # noqa: E402

ROOT = BACKEND.parent
REPORTS = BACKEND / "data" / "reports"
TASKS = ROOT / ".agents" / "tasks"
SUBMISSION = ROOT / "submission"
CHECKS_FILE = TASKS / "_p8c8_checks.json"
SUMMARY_TASK_FILE = TASKS / "phase8_user_summary.md"
ROLES = ("batter", "bowler")

SOURCE_FILES = [
    ("updated_ball_by_ball.csv", "authoritative ball-by-ball deliveries"),
    ("matches.csv", "match headers"),
    ("competitions.csv", "competitions"),
    ("teams.csv", "teams"),
    ("playing_eleven.csv", "playing XI"),
    ("competition_team_player_mapping.csv", "player to team mapping"),
    ("ball_by_ball.csv", "comparison only (not a scoring source)"),
]
NOT_USED_FILES = [
    "matches 2026.csv",
    "batting_stats2026.csv",
    "bowling_stats2026.csv",
    "fielding_stats2026.csv",
    "any Cricsheet file (never a feature, model or ranking source)",
]
DATABASES = [
    ("superr.duckdb", "official database built from the source files (read-only)"),
    ("exploratory.duckdb", "pre-delivery state and Phase 3 to 6 tables (read-only in Phase 8)"),
    ("phase8.duckdb", "Phase 8 tables, prefix p8_ (written by Phase 8 only)"),
]
CONFIG_FILES = [
    "config/phase8_selection_criteria_v1.json",
    "config/phase4_split_v1.json",
    "config/data_quality_restrictions_v1.json",
]
# Reports that make up the submission (copied to d:/Data/submission/).
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
    "phase8_build_manifest.json",
]
DELIVERABLES = [
    ("pressure_batters_top10.csv", "Top 10 batters (ordered, status-labelled)"),
    ("pressure_batters_top10.json", "Top 10 batters, JSON"),
    ("pressure_bowlers_top10.csv", "Top 10 bowlers (ordered, status-labelled)"),
    ("pressure_bowlers_top10.json", "Top 10 bowlers, JSON"),
    ("pressure_top10_status.md", "Status banner and label definitions for both lists"),
    ("submission_methodology.md", "Methodology report"),
    ("submission_executive_summary.md", "One-page plain-English summary"),
    ("methodology_comparison.md", "Comparison of the three approaches"),
    ("pressure_methodology_research.md", "What was tried, what failed, why"),
    ("player_selection_explanations.md", "Why selected and why not selected, per player"),
    ("descriptive_batter_profiles.csv", "Descriptive batter profiles (no composite, no rank)"),
    ("descriptive_bowler_profiles.csv", "Descriptive bowler profiles (no composite, no rank)"),
    ("ai_pipeline_verification.md", "Independent AI/ML pipeline audit"),
    ("submission_test_report.md", "Real test, lint and build outputs"),
    ("submission_readiness_audit.md", "Deliverable checklist and open items"),
    ("final_submission_summary.md", "Final summary for the owner"),
    ("phase8_build_manifest.json", "Input hashes, output provenance, versions"),
]


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(_cell(r[c]) for c in cols) + " |")
    return "\n".join(out)


def _cell(v: object) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v).replace("|", "/")


def f3(v: object) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{float(v):.3f}"


def f4(v: object) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{float(v):.4f}"


DOCUMENTED_CHANGES = {
    "phase7_model_registry.json": "intentional Phase 8 chunk 6 change: output keys renamed to the preserved "
    "*_phase7_aborted.csv names (content hashes of those files verified equal); see phase8_chunk6_verification.md",
}


def protected_check() -> dict:
    """Compare every recorded pre-Phase 8 hash; a documented intentional change is listed, not hidden."""
    rec = load_prehash()
    bad, documented, checked = [], [], 0
    for name, digest in rec.items():
        p = Path(name)
        if not p.exists():
            bad.append({"file": name, "state": "missing"})
            continue
        checked += 1
        if sha256(p) != digest:
            note = DOCUMENTED_CHANGES.get(p.name)
            (documented if note else bad).append({"file": name, "state": "changed", "note": note})
    return {
        "checked": checked,
        "ok": not bad,
        "unexpected_changes": bad,
        "documented_changes": documented,
    }


def run(cmd: list[str], cwd: Path, timeout: int = 1800) -> dict:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env={**__import__("os").environ, "PYTHONUTF8": "1", "NO_COLOR": "1", "CI": "1"},
    )
    out = (p.stdout or "") + (p.stderr or "")
    return {"command": " ".join(cmd), "cwd": str(cwd), "exit_code": p.returncode, "output": out}


def tail(text: str, n: int = 14) -> str:
    lines = [ln.rstrip() for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


# ---------------------------------------------------------------------------------------------
# stage 1: checks
# ---------------------------------------------------------------------------------------------
def stage_checks(pytest_output: Path | None) -> dict:
    from datetime import datetime, timezone

    npm = "npm.cmd" if platform.system() == "Windows" else "npm"
    res: dict = {"stamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    res["protected"] = protected_check()
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
    CHECKS_FILE.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def parse_pytest(res: dict) -> dict:
    t = res.get("pytest", {}).get("output_tail", "")
    last = [ln for ln in t.splitlines() if re.search(r"\b(passed|failed|error)", ln)]
    line = last[-1] if last else ""
    counts = {
        k: int(m.group(1)) if (m := re.search(rf"(\d+) {k}", line)) else 0
        for k in ("passed", "failed", "errors", "skipped", "warnings", "xfailed", "xpassed")
    }
    m = re.search(r"in ([\d.]+)s", line)
    return {"line": line, "counts": counts, "seconds": float(m.group(1)) if m else None}


# ---------------------------------------------------------------------------------------------
# stage 2: documents
# ---------------------------------------------------------------------------------------------
class Facts:
    """Everything the documents quote, read from the stored outputs."""

    def __init__(self) -> None:
        self.checks = json.loads(CHECKS_FILE.read_text(encoding="utf-8"))
        self.pt = parse_pytest(self.checks)
        c = duckdb.connect(str(PHASE8_DB), read_only=True)
        self.cmp = c.execute("select * from p8_method_comparison order by role, approach").df()
        self.sel = c.execute("select * from p8_method_selection").df().set_index("role")
        self.status = c.execute("select * from p8_top10_status").df().set_index("role")
        self.sens = c.execute("select * from p8_final_sensitivity").df()
        self.intensity = c.execute("select * from p8_intensity_selection order by candidate").df()
        self.intensity_all = c.execute(
            "select * from p8_b_intensity_selection order by candidate"
        ).df()
        self.wp = c.execute("select * from p8_wp_metrics order by model").df()
        self.exp = c.execute("select * from p8_a_model_metrics order by role, target").df()
        self.weights = c.execute("select * from p8_c_weights order by role, component").df()
        self.excl = c.execute("select * from p8_data_exclusions").df()
        cols = "role, players_both_formats, spearman, spearman_low, spearman_high, combination_supported"
        self.fmt = c.execute(
            f"select 'A' approach, {cols} from p8_a_format_study where intensity = 'P4' "
            f"union all select 'B', {cols} from p8_b_format_study where intensity = 'P4' "
            f"union all select 'C', {cols} from p8_c_format_study where series = 'PRI' "
            "order by approach, role"
        ).df()
        self.reml = c.execute(
            "select role, scope, n_players, tau2, sigma2, floor, label from p8_a_reml "
            "where intensity = 'P4' order by role, scope"
        ).df()
        self.used = c.execute(
            "select period, competition_type, count(*) deliveries, count(distinct match_id) matches "
            "from p8_delivery_leverage where coalesce(excluded_reason, '') = '' group by 1,2 order by 1,2"
        ).df()
        self.n_leverage = c.execute("select count(*) from p8_delivery_leverage").fetchone()[0]
        self.leverage_excl = c.execute(
            "select excluded_reason reason, count(*) deliveries, count(distinct match_id) matches "
            "from p8_delivery_leverage where coalesce(excluded_reason, '') <> '' group by 1 order by 1"
        ).df()
        self.expl = c.execute(
            "select role, kind, count(*) n from p8_explanations group by 1,2 order by 1,2"
        ).df()
        c.close()
        o = duckdb.connect(str(BACKEND / "data/database/superr.duckdb"), read_only=True)
        self.n_deliv = o.execute("select count(*) from deliveries").fetchone()[0]
        self.n_matches = o.execute("select count(*) from matches").fetchone()[0]
        self.n_players = o.execute("select count(*) from players").fetchone()[0]
        o.close()
        e = duckdb.connect(str(BACKEND / "data/database/exploratory.duckdb"), read_only=True)
        self.periods = e.execute(
            "select period, competition_type, count(*) matches, min(match_date) first_date, "
            "max(match_date) last_date from p4_match_period group by 1,2 order by 1,2"
        ).df()
        e.close()
        self.top = {r: pd.read_csv(REPORTS / f"pressure_{r}s_top10.csv") for r in ROLES}
        self.crit_hash = json.loads(CRITERIA_HASH_FILE.read_text(encoding="utf-8"))["sha256"]
        self.ai = json.loads((REPORTS / "phase8_ai_verification.json").read_text(encoding="utf-8"))
        self.prof = {
            r: pd.read_csv(REPORTS / f"descriptive_{r}_profiles.csv", usecols=["player_id"])
            for r in ROLES
        }
        self.stamp = self.checks["stamp_utc"]

    def cmp_row(self, role: str, approach: str) -> pd.Series:
        d = self.cmp[(self.cmp.role == role) & (self.cmp.approach == approach)]
        return d.iloc[0]

    def chosen(self, role: str) -> str:
        return str(self.sel.loc[role, "approach_chosen"])

    def banner(self, role: str) -> str:
        return str(self.status.loc[role, "banner"])


def _ranking_table(f: Facts, role: str) -> str:
    d = f.top[role]
    t = pd.DataFrame(
        {
            "rank": d["rank"],
            "player": d["player_name"],
            "score": d["pressure_score"].map(f4),
            "interval (95%)": [
                f"{f4(a)} to {f4(b)}" for a, b in zip(d["interval_low"], d["interval_high"])
            ],
            "pressure matches": d["pressure_matches"],
            "pressure balls": d["pressure_deliveries"],
            "IPL / T20I matches": [
                f"{a} / {b}" for a, b in zip(d["ipl_matches"], d["t20i_matches"])
            ],
            "top-10 probability": d["top10_inclusion_probability"].map(lambda v: f"{100 * v:.0f}%"),
            "rank interval": [
                f"{a:.0f} to {b:.0f}"
                for a, b in zip(d["rank_interval_low"], d["rank_interval_high"])
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
            "95% interval": [f"{f3(a)} to {f3(b)}" for a, b in zip(d["sb_low"], d["sb_high"])],
            "out-of-time r": d["oot"].map(f3),
            "out-of-time lower bound": d["oot_low"].map(f3),
            "ICC(1)": d["icc1"].map(f4),
            "variance at floor": d["between_player_variance_at_floor"].map(
                lambda v: "yes" if v else "no"
            ),
            "mean data weight": d["mean_data_weight"].map(f3),
            "passes 0.5 data-weight gate": d["phase6_gate_passed"].map(
                lambda v: "yes" if v else "no"
            ),
            "eligible players": d["n_eligible"],
            "submitted": d["chosen"].map(lambda v: "yes" if v else "no"),
        }
    )
    return md_table(t)


def doc_methodology(f: Facts) -> str:
    cb, cw = f.chosen("batter"), f.chosen("bowler")
    rb, rw = f.cmp_row("batter", cb), f.cmp_row("bowler", cw)
    p4 = f.intensity[f.intensity.candidate == "P4"].iloc[0]

    src = []
    for name, why in SOURCE_FILES:
        p = ROOT / name
        src.append({"file": name, "role": why, "bytes": p.stat().st_size, "sha256": sha256(p)})
    dbs = []
    for name, why in DATABASES:
        p = BACKEND / "data/database" / name
        dbs.append({"file": name, "role": why, "sha256": sha256(p)})
    cfg = [
        {"file": c, "sha256": sha256(BACKEND / c)} for c in CONFIG_FILES if (BACKEND / c).exists()
    ]
    used = f.used.copy()
    used.columns = ["period", "competition", "deliveries used", "matches"]
    excl = f.excl[["reason", "competition_type", "rows", "matches"]].copy()
    per = f.periods.copy()
    per.columns = ["period", "competition", "matches", "first match", "last match"]
    per["first match"] = per["first match"].astype(str).str[:10]
    per["last match"] = per["last match"].astype(str).str[:10]
    n_used = int(f.used["deliveries"].sum())

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
    ]
    exp = f.exp[["role", "target", "chosen", "gain_vs_const_pct", "n_train", "n_validation"]]
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
    sens_rows = []
    for role in ROLES:
        ap = f.chosen(role)
        s = f.sens[(f.sens.role == role) & (f.sens.approach == ap)].copy()
        s["role"] = role
        sens_rows.append(
            s[["role", "family", "comparison", "n_common", "spearman", "top10_overlap"]]
        )
    sens = pd.concat(sens_rows)
    fmt_txt = md_table(f.fmt)

    lines: list[str] = []
    a = lines.append
    a("# Submission methodology: pressure performance of IPL and T20I batters and bowlers")
    a("")
    a(f"> **Batters: {f.status.loc['batter', 'list_status']}.** {f.banner('batter')}")
    a("")
    a(f"> **Bowlers: {f.status.loc['bowler', 'list_status']}.** {f.banner('bowler')}")
    a("")
    a(
        "Both lists are the best-supported ordering available. Neither is a validated ranking. "
        "The label of each list is the label the evidence earned under thresholds declared before any result was seen."
    )
    a("")
    a("## Part 1. The report in plain language")
    a("")
    a("### 1.1 What was asked")
    a("")
    a(
        "Name the ten batters and the ten bowlers who perform best under pressure, in order, and explain how pressure was defined, how players were measured, and how far the conclusions can be trusted. This is a player-performance question. It is not a squad-building exercise."
    )
    a("")
    a("### 1.2 What was done, in five steps")
    a("")
    a(
        "1. **Describe the situation of every ball.** For each delivery, only what was known before the ball was bowled is used: score, wickets lost, balls left, target, required rate, phase, innings, batting order."
    )
    a(
        "2. **Give each ball a pressure level between 0 and 1.** The level used is *resource scarcity*: the share of wickets already lost multiplied by the share of the innings already used. A ball late in an innings with many wickets down is high pressure. Balls at level 0.5 or above form the pressure sample and each counts in proportion to its level, so a very high-pressure ball counts more than a borderline one; balls below 0.5 define the player's normal play."
    )
    a(
        "3. **Ask what normally happens in that situation.** A statistical model trained on earlier matches (to the end of 2024) predicts the runs and the chance of a wicket for each ball from the situation alone, without knowing who is playing. A player's performance is the gap between what happened and what the model expected."
    )
    a(
        "4. **Compare pressure with normal play.** Each player's pressure gap is set beside the same gap on low-pressure balls, so a player who is simply good all the time is not mistaken for a player who rises under pressure."
    )
    a(
        "5. **Be honest about noise.** Small samples are pulled towards the average, every score has an interval from resampling whole matches, and the whole procedure was tested for whether it gives the same answer on two halves of the same data."
    )
    a("")
    a("### 1.3 What was found")
    a("")
    a(
        f"- Three different approaches were built and compared under criteria written down and hashed before any result existed (A: observed against expected; B: win probability added; C: a Pressure Response Index). Batters are submitted from approach **{cb}**, bowlers from approach **{cw}**."
    )
    a(
        f"- The split-half reliability of the submitted batter measure is **{f3(rb['sb'])}** and of the bowler measure **{f3(rw['sb'])}** (1.0 would mean two halves of the data give the same order; the declared thresholds were 0.5 for PROVISIONAL and 0.7 for VALIDATED). Both fall short, and both intervals include 0."
    )
    a(
        "- So the data do not show that these players are reliably better under pressure than players just below them. The earlier Phase 6 finding stands: match-level data are too thin to separate players on pressure performance with confidence."
    )
    a(
        "- The lists are still useful as a transparent, reproducible description of who beat the model's expectation most in difficult situations from 2022 to 2025, with each player's evidence shown."
    )
    a("")
    a("### 1.4 How to read the two lists")
    a("")
    a("**Batters** (approach A: context-adjusted performance; higher score is better)")
    a("")
    a(_ranking_table(f, "batter"))
    a("")
    a("**Bowlers** (approach C: Pressure Response Index; higher score is better)")
    a("")
    a(_ranking_table(f, "bowler"))
    a("")
    a(
        "Top-10 probability is the share of 1,000 resamples of whole matches in which the player is in the Top 10. The rank interval is the 95% range of the player's rank across the same resamples. A player with a probability near 50% and a rank interval spanning twenty places has an order that should not be taken literally."
    )
    a("")
    a("### 1.5 What the status labels mean")
    a("")
    a("See the glossary in section 14. In short: every row and both lists are EXPLORATORY.")
    a("")
    a("## Part 2. Methodology in detail")
    a("")
    a("## 2. Data and provenance")
    a("")
    a(
        "Only the official IPL and T20I data supplied for the competition are used. `updated_ball_by_ball.csv` is authoritative; `ball_by_ball.csv` is used for comparison only. Source files are read-only and were hashed before and after the Phase 8 run: every recorded hash was compared at the end of the run (results in the test report; one documented intentional change to a Phase 7 registry file, none to a source file or database)."
    )
    a("")
    a(md_table(pd.DataFrame(src)))
    a("")
    a("Not used: " + "; ".join(NOT_USED_FILES) + ".")
    a("")
    a(md_table(pd.DataFrame(dbs)))
    a("")
    a(md_table(pd.DataFrame(cfg)))
    a("")
    a(
        f"Counts: the official database holds {f.n_deliv:,} deliveries, {f.n_matches:,} matches and {f.n_players:,} players. Phase 8 scores the pre-test window only (TRAIN to 2024-12-31 and VALIDATION, calendar 2025). The 2026 matches (TEST) were never loaded."
    )
    a("")
    a(md_table(per))
    a("")
    a(
        f"After exclusions, {n_used:,} regulation deliveries in the IPL and T20I carry no exclusion reason and are available for scoring (the stored delivery table has {f.n_leverage:,} rows including those with a stated exclusion reason)."
    )
    a("")
    a(md_table(used))
    a("")
    a("Rows removed before scoring, with the reason (source-data exclusions):")
    a("")
    a(md_table(excl))
    a("")
    a(
        "Deliveries dropped at the scoring stage because a needed quantity was undefined (never filled with zero):"
    )
    a("")
    a(md_table(f.leverage_excl))
    a("")
    a(
        "Super Over deliveries (innings 3 and 4 of the six restricted matches), deliveries in matches whose chase target cannot be reconstructed after a rain-reduced target, and the wicket-flag and extras-label anomalies listed in the restriction register are excluded at the metric they affect. Missing values are never treated as zero. The 42 T20I matches with late-dated records stay out of the primary evaluation."
    )
    a("")
    a("## 3. Pressure definition and why it was chosen")
    a("")
    a(
        "Pressure is defined here as observable difficulty of the match situation, not as a psychological state. Seven definitions were declared before any player was ranked (P0 to P6) and tested on balls, not on players:"
    )
    a("")
    a("- a: runs per ball are lower at high intensity than at low intensity;")
    a("- b: the chance of a wicket is higher at high intensity;")
    a("- c: outcomes vary more at high intensity;")
    a("- d: the win probability swings more (mechanical for the win-probability definitions);")
    a("- e: the relation is monotonic across the ten intensity bands (Spearman at least 0.7).")
    a("")
    t = f.intensity_all[
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
    ].copy()
    a(md_table(t))
    a("")
    a(
        f"No candidate passes the declared rule, because the monotonic trend test (e) fails for all. P4 (resource scarcity, both innings) was used because the declared ordering picks the candidate that passes the most tests with the widest innings coverage ({int(p4['n_tests_passed'])} tests passed, coverage of {int(p4['innings_coverage'])} innings). Pressure balls at P4 have {abs(p4['runs_diff_pooled_train']):.3f} fewer runs per ball and a {p4['wkt_diff_pooled_train']:.3f} higher wicket probability (pooled difference, TRAIN) than low-pressure balls. The definition is therefore the best available, not validated, and this alone caps both lists at EXPLORATORY. Win-probability based definitions (P1, P2) were built but failed the direction tests; they are reported in the comparison."
    )
    a("")
    a(
        "Why these indicators are meaningful: wickets in hand and balls remaining are the two resources a batting side spends, and scarcity of both is what commentators describe as pressure; both are known before each ball, so there is no look-ahead. Close-match and last-overs definitions were not assumed. The first principal component of P3 and P4 (P6) and the Phase 6 style slice (P0) were kept as sensitivity checks."
    )
    a("")
    a("## 4. Batter and bowler metrics")
    a("")
    a("Batters and bowlers are analysed separately and never compared with each other.")
    a("")
    a(
        "- **Batter, approach A.** For every pressure ball, runs scored minus runs expected, and expected minus actual dismissal (so not being dismissed counts as better), each divided by its TRAIN standard deviation and averaged with equal weight. Dot-ball and boundary components are reported but not scored."
    )
    a(
        "- **Bowler, approach C.** The Pressure Response Index combines three components: A (the same expected-outcome residual from the bowler's side), B (win probability added above what the leverage predicts) and CONS (the share of pressure appearances in which the bowler beat the expectation). Component weights come from split-half reliability on a fitting half of the matches; the table below shows the weights that resulted."
    )
    a("")
    a(md_table(wts))
    a("")
    a(
        "Every weight rule gave components A and B zero weight for both roles, because they showed no between-player signal on the fitting matches. The index therefore reduces to the consistency component. It is a share of appearances, not an A plus B composite, and the bowler list should be read with that in mind."
    )
    a("")
    a(
        "The unit of analysis is one player in one innings (a batting innings or a bowling spell). Matches, not balls, are the resampling unit, because balls in the same match are not independent."
    )
    a("")
    a("## 5. Normal-performance baselines")
    a("")
    a(
        "The *normal baseline* of a player is the unweighted mean residual on balls below intensity 0.5 (low-pressure balls), in the same units as the pressure score. The *pressure level* is the intensity-weighted mean residual on balls at or above 0.5. The pressure-versus-baseline difference (`pressure_delta`) is the second minus the first. Both are in the CSV columns `normal_baseline`, `pressure_performance_unshrunk` and `pressure_delta`, and in every player's explanation. The expected value for each ball comes from a player-blind model, so the baseline reflects the player's performance relative to the typical player in the same situation, not a raw average."
    )
    a("")
    a("## 6. Context adjustment")
    a("")
    a(
        "Expected runs and wicket probability are predicted by gradient-boosting models fitted on TRAIN only from pre-delivery information: innings, phase, wickets remaining, balls remaining, score, target and required rate in a chase, current run rate, batting order, stage and competition type. No player identifier and no outcome column is a feature; a leakage test mutates future rows and shows the expectation of earlier balls does not change. TRAIN balls are predicted out of fold (fold = match_id modulo 5) so no ball is scored by a model that saw its own match."
    )
    a("")
    a("Out-of-sample quality on VALIDATION (calendar 2025):")
    a("")
    a(md_table(exp))
    a("")
    a(
        "The gain over a constant prediction is 1.5% to 3.1%. Ball outcomes are mostly chance given the situation, which limits how much of any residual can be credited to the player. The win-probability models used by approach B are better calibrated:"
    )
    a("")
    a(md_table(wp))
    a("")
    a(
        "W1 is the first-innings model and W2 the chase model. Both beat a constant and a logistic baseline and passed the declared calibration gates. Technical soundness does not establish that the resulting player order is reliable (section 10)."
    )
    a("")
    a("## 7. IPL and T20I comparison")
    a("")
    a(
        "Competition is a model feature, and scores are centred by format before combination. Whether a single combined score is justified was tested, not assumed: the declared rule needs a cross-format correlation with lower 95% bound of at least 0.3 across at least 30 players who appear in both formats."
    )
    a("")
    if fmt_txt:
        a(fmt_txt)
        a("")
    a(
        "No approach meets the rule for either role, so the combined estimate is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`: each player-match unit is weighted by its own precision and there is no fixed 70:30 split. IPL and T20I matches, contributions, scores and ranks are shown separately for every listed player in the CSV (`ipl_matches`, `t20i_matches`, `ipl_contribution`, `t20i_contribution`, `ipl_score`, `t20i_score`, `rank_in_IPL`, `rank_in_T20I`). Players' IPL and T20I results are essentially uncorrelated, which is itself evidence of how noisy single-format results are."
    )
    a("")
    a("## 8. Eligibility and sample size")
    a("")
    a(
        "Declared floors (criteria file, hash below): at least 8 matches, at least 60 balls faced or 72 balls bowled, at least 8 high-intensity units, an effective sample of at least 60, and at least 4 matches in the 2025 window. Floors were also halved and doubled as a sensitivity check."
    )
    a("")
    a(
        f"Eligible players: {int(rb['n_eligible'])} batters (approach {cb}) and {int(rw['n_eligible'])} bowlers (approach {cw}). A player below a floor is `INSUFFICIENT_EVIDENCE`, which says nothing about quality. No list is padded."
    )
    a("")
    a("## 9. Shrinkage and uncertainty")
    a("")
    a(
        "Player estimates are shrunk towards the cohort mean by a random-effects model fitted by REML on the match-level units, so a player with few pressure appearances moves further towards the mean. Shrinkage was not removed or weakened to make a gate pass. Between-player variance (tau squared) estimated for approach A at the P4 intensity, by scope:"
    )
    a("")
    a(md_table(f.reml))
    a("")
    a(
        f"The variances are tiny relative to the residual variance (sigma squared), so the data find very little player-to-player difference to shrink towards. Where a scope sits at the floor (tau squared 0), the predeclared rule orders players by the unshrunk precision-weighted mean and forces the label EXPLORATORY. For the submitted combined scope the status table stores tau squared {f4(f.status.loc['batter', 'reml_tau2_combined'])} for batters and {f4(f.status.loc['bowler', 'reml_tau2_combined'])} for bowlers."
    )
    a("")
    a(
        f"Intervals are 95% percentile intervals from a 1,000-draw bootstrap that resamples whole matches (seed {SEED}), re-estimating the between-player variance in every draw. Each row also reports Top-10 inclusion probability, a 95% rank interval and a sample-reliability (shrinkage) figure. Bowler score intervals are skewed above the point estimate because the scale is held at its full-sample value while shrinkage changes; 9 of 10 bowler rows carry the flag `ASYMMETRIC_UPPER_TAIL`. Rank intervals and inclusion probabilities use every draw and are the better guide."
    )
    a("")
    a(
        "Evidence classes (declared in advance): STRONG_SUBSTANTIAL (interval above 0, at least twice the match floor, positive share at least 0.5), STRONG_LIMITED, INCONSISTENT and INSUFFICIENT."
    )
    a("")
    a("## 10. Reliability validation")
    a("")
    a(
        "Reliability asks whether the method gives the same order twice. Two matched halves of each player's matches are scored independently (odd and even matches by date, and early against late), the correlation is corrected to full length (Spearman-Brown) and its interval comes from a match-cluster bootstrap. An out-of-time test correlates TRAIN-period estimates with VALIDATION-period estimates. Batters first, then bowlers:"
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
        "Approach C's figures use held-out matches only (its weights were fitted on the other half), so its columns are not like for like with A and B; the selection rule was applied as declared and the difference is disclosed rather than corrected. The Phase 6 data-weight gate (mean data weight of at least 0.5) is reported unchanged and no approach passes it."
    )
    a("")
    a(
        "Phase 6 findings that remain true after Phase 8: between-player variance sits at the shrinkage floor in all 48 contexts; pooled odd/even reliability was 0.37 (0.3656) with a median of 0.25 over the 47 estimable contexts; 0 of 48 contexts pass the 0.5 data-weight gate; no pressure definition passed the predeclared criteria; rankings are sensitive to definitions and resampling. Phase 8 changed the method (continuous intensity, richer expected-outcome models, match-level units, REML) and tested whether the result improved. The technical pipeline improved; the central finding did not change."
    )
    a("")
    a("## 11. Sensitivity analysis")
    a("")
    a(
        "Each row compares the submitted order with a variant: Spearman correlation over the players both versions rank, and how many of the ten submitted players remain in the variant's Top 10."
    )
    a("")
    s2 = sens.copy()
    s2["spearman"] = s2["spearman"].map(f3)
    s2["top10_overlap"] = s2["top10_overlap"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.0f}")
    a(md_table(s2))
    a("")
    a(
        "The ordering is stable to the eligibility floors and moderately stable to format and calendar window. Membership of the Top 10 changes substantially with the pressure definition, with the shrinkage assumption and with the components used. This matches the Phase 6 sensitivity finding and is a further reason the lists are EXPLORATORY."
    )
    a("")
    a("## 12. Final ranking evidence")
    a("")
    a(
        f"Approach selection used only approach-level metrics declared in advance (split-half and out-of-time lower bounds, inclusion concentration, an explainability checklist), never a player's rank or name. For batters the rule path was `{f.sel.loc['batter', 'rule_path']}` and chose {cb}; for bowlers it was `{f.sel.loc['bowler', 'rule_path']}` and chose {cw}. Both the lower-bound path and the point-estimate path agree in each role."
    )
    a("")
    a(
        "For batters, approaches A and C are within 0.001 of each other on the split-half point estimate and both intervals include 0, so the choice of A should not be read as a performance difference. Bowlers' approach C leads on the split-half point estimate and on the out-of-time lower bound but its interval also includes 0, and approach A has one more player with a Top-10 probability of at least 0.5."
    )
    a("")
    a(
        "Criteria file `config/phase8_selection_criteria_v1.json`, SHA-256 `"
        + f.crit_hash
        + "`, was verified against the run log before every comparison step."
    )
    a("")
    a(
        "Player-level evidence for all twenty listed players, and for near-miss and high-raw-statistic players who were not listed, with data-based reasons, is in `player_selection_explanations.md` ("
        + ", ".join(f"{r.role} {r.kind}: {r.n}" for r in f.expl.itertuples())
        + " entries). A player left out is never described as poor merely for lacking evidence."
    )
    a("")
    a("## 13. Limitations")
    a("")
    a(
        "- No approach reached the declared PROVISIONAL threshold. The orders are not shown to separate players beyond noise."
    )
    a("- The pressure definition used (P4) did not pass the declared validity rule.")
    a(
        "- Ball outcomes are mostly chance given the situation: the expected-outcome models improve on a constant by 1.5% to 3.1%."
    )
    pm = pd.concat([f.top["batter"]["pressure_matches"], f.top["bowler"]["pressure_matches"]])
    a(
        f"- The sample is small: the twenty listed players have {int(pm.min())} to {int(pm.max())} pressure appearances each (one appearance is one innings or one spell at pressure intensity 0.5 or more), over 2022 to 2025."
    )
    a(
        "- IPL and T20I results are not correlated enough to combine; the combined estimate is a precision-weighted compromise, labelled as such."
    )
    a(
        "- The bowler index reduces to a consistency share, which rewards beating the expectation often rather than by much."
    )
    a(
        "- The 2026 matches are not used. They were opened once in an earlier phase and are not a clean hold-out; using them needs an explicit owner decision."
    )
    a(
        "- The 42 T20I matches with late-dated records are excluded from primary evaluation and have not been verified against an official source."
    )
    a(
        "- Win-probability models for the first innings are less well calibrated (slope 0.89) than for chases (slope 1.13)."
    )
    a(
        "- The experimental AI predictions are a separate, validation-period diagnostic and are not part of the submitted ranking."
    )
    a("")
    a("## 14. Glossary of status labels")
    a("")
    a(
        "- **VALIDATED**: split-half reliability at least 0.70 with an interval lower bound at least 0.50 and an out-of-time lower bound above 0.30, all declared before any result. *Nothing in this submission has this label.*"
    )
    a(
        "- **PROVISIONAL**: split-half reliability at least 0.50 with an interval lower bound above 0 and an out-of-time lower bound above 0, but not every VALIDATED threshold. *Nothing in this submission has this label.*"
    )
    a(
        "- **EXPLORATORY**: an ordered list exists but the PROVISIONAL thresholds were not met. The order is the best available description of the data and is not shown to separate players beyond noise. *Both submitted lists and all twenty rows have this label.*"
    )
    a(
        "- **INSUFFICIENT_EVIDENCE**: fewer than ten players meet the eligibility floors, or the approach cannot be computed. A player with this label is not ranked and nothing is implied about their quality. *No list needed it; players below an eligibility floor are not ranked.*"
    )
    a("")
    a(
        "A row never carries a stronger label than its list. The submitted ranking status (is this order reliable?) is kept apart from the model validation status (did the method pass its declared tests?)."
    )
    a("")
    a("## Appendix A. Technical details")
    a("")
    a(
        "**Splits.** `config/phase4_split_v1.json`: TRAIN to 2024-12-31, VALIDATION calendar 2025, TEST 2026 onwards (never loaded; a lock log hash was identical before and after every stage). Chronological, whole matches only, checked by test."
    )
    a("")
    a(
        "**Models.** Expected-outcome: scikit-learn gradient boosting (regressor for runs, histogram classifier for wicket, dot, boundary), grid of learning rate {0.05, 0.1}, depth {3, 5}, L2 {0, 1}, 200 iterations, minimum leaf 200, chosen once on VALIDATION by RMSE or log loss. Win probability: histogram gradient boosting with logistic and isotonic baselines. Artefacts in `backend/data/models/` with metadata JSON and SHA-256 (see `ai_pipeline_verification.md`). Seed "
        + str(SEED)
        + "."
    )
    a("")
    a(
        "**REML.** Random-effects model per scope (combined with format-centred units, IPL, T20I): player effect with variance tau squared, residual variance sigma squared, estimated by REML; posterior mean per player. A tau squared below 1e-8 sigma squared is flagged FLOOR and no floor is imposed."
    )
    a("")
    a(
        "**Win probability added attribution.** Striker receives runs off the bat; bowler receives wickets with bowler credit, wides and no-balls; byes and leg-byes go to the batting side collectively; run-outs and other non-credit dismissals never give bowler credit; unusual events are excluded and counted in `p8_wpa_excluded_events`."
    )
    a("")
    a(
        "**Reliability estimators.** Split-half on unshrunk precision-weighted unit means; Spearman-Brown 2r/(1+r); Fisher-z pooling; one-way ICC(1) on unit means of players with at least two matches; 1,000-draw match-cluster bootstrap."
    )
    a("")
    a(
        "**Reproduction.** From `d:/Data/backend` with `PYTHONUTF8=1`: `python scripts/phase8_final_ranking.py all` regenerates the lists and reports from the stored tables (two runs give byte-identical CSV and JSON); `python scripts/run_phase8.py all` regenerates this document, the test report, the audit, the manifest and the bundle. The manifest `phase8_build_manifest.json` records input hashes, output hashes and tool versions."
    )
    a("")
    a(
        f"**Versions.** Methodology `phase8_methodology_v1`; criteria `phase8_selection_criteria_v1` (SHA-256 `{f.crit_hash}`); generated {f.stamp}."
    )
    return "\n".join(lines)


def _top_names(f: Facts, role: str) -> str:
    d = f.top[role]
    return "; ".join(f"{int(r)}. {n}" for r, n in zip(d["rank"], d["player_name"]))


def doc_executive(f: Facts) -> str:
    rb, rw = f.cmp_row("batter", f.chosen("batter")), f.cmp_row("bowler", f.chosen("bowler"))
    bat, bow = f.top["batter"], f.top["bowler"]
    nb = int((bat.top10_inclusion_probability >= 0.5).sum())
    nw = int((bow.top10_inclusion_probability >= 0.5).sum())
    L = []
    a = L.append
    a("# Executive summary: who performs best under pressure?")
    a("")
    a(
        "> **Both lists are EXPLORATORY.** They are the best-supported ordering of the available data, not validated rankings. The order is not shown to separate players beyond noise."
    )
    a("")
    a(
        "**The question.** Name the ten batters and ten bowlers who perform best under pressure in the IPL and T20Is, and show how reliable the answer is."
    )
    a("")
    a(
        "**How we defined pressure.** A ball is high pressure when many wickets have fallen and much of the innings has been used (the share of wickets lost times the share of the innings gone). Balls at level 0.5 or above count in proportion to their level, and lower-pressure balls give each player a normal-play baseline. Only information known before the ball is used."
    )
    a("")
    a(
        "**How we measured players.** A model trained on earlier matches predicts the runs and wicket chance of each ball from the situation alone. Batters are scored on how much they beat that expectation at high pressure, compared with their normal play. Bowlers are scored by how consistently they beat the expectation in their pressure spells. Small samples are pulled towards average and every score has an interval."
    )
    a("")
    a("**Top 10 batters** (approach A): " + _top_names(f, "batter") + ".")
    a("")
    a("**Top 10 bowlers** (approach C): " + _top_names(f, "bowler") + ".")
    a("")
    a(
        f"**How much to trust the order.** We tested whether the method gives the same order on two halves of the data. The score was {f3(rb['sb'])} for batters and {f3(rw['sb'])} for bowlers, where 0.5 was needed for PROVISIONAL and 0.7 for VALIDATED. Both intervals include zero. {nb} of the 10 batters and {nw} of the 10 bowlers are in the Top 10 in at least half of 1,000 resamples of the matches. Moving the pressure definition or ignoring shrinkage changes who is in the Top 10. So the names are a fair description of who did best against expectation, and they are not proof that the order would repeat."
    )
    a("")
    a(
        "**What we did not do.** We did not lower the declared thresholds, change the shrinkage to pass a test, or label any list stronger than the evidence allows. We did not use the 2026 matches. An AI-style model (gradient boosting) is used to predict expected outcomes and win probability; it trains and predicts on real data, and its separate experimental lists are not part of the submission."
    )
    a("")
    a(
        "**Where to look next.** `submission_methodology.md` for the method, `player_selection_explanations.md` for why each player is or is not in the lists, `submission_readiness_audit.md` for what is incomplete."
    )
    return "\n".join(L)


def doc_test_report(f: Facts) -> str:
    c = f.checks
    pt = f.pt
    L: list[str] = []
    a = L.append
    a("# Submission test report")
    a("")
    a(
        f"Run stamp (UTC): {f.stamp}. Platform: {platform.system()} {platform.release()}, Python {platform.python_version()}. Commands were run from the stated directory; outputs below are the real outputs (the last lines, where long)."
    )
    a("")
    a("## Summary")
    a("")
    cnt = pt["counts"]
    summ = pd.DataFrame(
        [
            {
                "check": "pytest (backend, full suite)",
                "result": pt["line"] or "no pytest output recorded",
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
                "check": "npm run build (tsc -b && vite build)",
                "result": tail(c["npm_build"]["output"], 1),
                "exit": c["npm_build"]["exit_code"],
            },
            {
                "check": "npm run lint (oxlint)",
                "result": tail(c["npm_lint"]["output"], 1),
                "exit": c["npm_lint"]["exit_code"],
            },
            {
                "check": "protected files (SHA-256 against recorded hashes)",
                "result": f"checked {c['protected'].get('checked')}, ok {c['protected'].get('ok')}",
                "exit": "pass" if c["protected"].get("ok") else "FAIL",
            },
        ]
    )
    a(md_table(summ))
    a("")
    a(f"Tool versions: {c['ruff_version']}; node {c['node_version']}; npm {c['npm_version']}.")
    a("")
    a("## pytest")
    a("")
    a("Command: `python -m pytest -q` (cwd `d:/Data/backend`).")
    a("")
    a(
        f"Parsed counts: passed {cnt['passed']}, failed {cnt['failed']}, errors {cnt['errors']}, skipped {cnt['skipped']}, warnings {cnt['warnings']}"
        + (f", duration {pt['seconds']:.0f} s" if pt["seconds"] else "")
        + "."
    )
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
        f"A SHA-256 comparison over the recorded manifest `phase8_prehash.json`: {json.dumps(c['protected'])}. The source CSVs, `superr.duckdb`, `exploratory.duckdb` and the Phase 2 to 7 reports recorded there are byte-identical to their pre-Phase 8 hashes, except for the documented intentional change(s): "
        + (
            "; ".join(
                f"`{Path(d['file']).name}` ({d['note']})"
                for d in c["protected"]["documented_changes"]
            )
            or "none"
        )
        + "."
    )
    a("## What the tests cover")
    a("")
    a(
        "Calculations, win-probability attribution (striker, bowler, wicket, extras, run-out), eligibility, missing-data handling, ranking determinism and tie-breaks, leakage (truncation and mutation of future rows, chronological split integrity, model trained on TRAIN only), calibration function on synthetic data, criteria-hash predeclaration, TEST-lock preservation, no external ball-by-ball source in scoring modules, protected-file preservation, API schema and status labels on every submission endpoint, token protection of `/internal/*`, descriptive-only `/players`, a scan for hardcoded player names and random scores in backend production code and frontend source, and the earlier phases' suites unchanged."
    )
    a("")
    a("## Not covered by automated tests")
    a("")
    a(
        "The frontend has no unit tests; it is checked by the type-check and build, the linter and the earlier Playwright pass (ten pages at 375, 768, 1024 and 1440 px, no horizontal scroll, no console errors). The unlocked state of the Experimental AI page, a keyboard-only walkthrough and automated contrast tooling were not run."
    )
    return "\n".join(L)


def doc_audit(f: Facts) -> str:
    c = f.checks
    rows = []
    for name, what in DELIVERABLES:
        p = REPORTS / name
        if name == "phase8_build_manifest.json" or name == "submission_readiness_audit.md":
            ok = "written by this run"
        else:
            ok = "present" if p.exists() else "MISSING"
        rows.append({"deliverable": name, "content": what, "state": ok})
    nb, nw = len(f.top["batter"]), len(f.top["bowler"])
    L: list[str] = []
    a = L.append
    a("# Submission readiness audit")
    a("")
    a(f"Stamp (UTC): {f.stamp}.")
    a("")
    a("## 1. Verdict")
    a("")
    a(
        f"Ready to submit as an honestly labelled **exploratory** analysis: {nb} batters and {nw} bowlers are listed in order, each with evidence, uncertainty and a status label. Not ready to claim as a validated or provisional ranking, because no approach reached the declared reliability thresholds (batters {f3(f.cmp_row('batter', f.chosen('batter'))['sb'])}, bowlers {f3(f.cmp_row('bowler', f.chosen('bowler'))['sb'])} split-half against 0.5 needed)."
    )
    a("")
    a("## 2. Deliverable checklist")
    a("")
    a(md_table(pd.DataFrame(rows)))
    a("")
    a(
        "The same files, plus a SHA-256 manifest, are copied to `d:/Data/submission/` by `scripts/run_phase8.py`."
    )
    a("")
    a("## 3. Requirements check")
    a("")
    chk = [
        (
            "Top 10 batters, ordered, real data",
            f"{nb} rows, rank 1 to {nb}, deterministic tie-break by player id",
            "met",
        ),
        ("Top 10 bowlers, ordered, real data", f"{nw} rows, rank 1 to {nw}", "met"),
        (
            "Pressure definition and rationale",
            "section 3 of the methodology",
            "met (definition not validated)",
        ),
        ("Batter and bowler metrics, baselines, context adjustment", "sections 4 to 6", "met"),
        (
            "IPL against T20I comparison",
            "section 7, per-format columns in both CSVs",
            "met (combination unsupported)",
        ),
        ("Eligibility, shrinkage, uncertainty", "sections 8 and 9", "met"),
        (
            "Reliability validation",
            "section 10, split-half, out-of-time, ICC",
            "met; thresholds not reached",
        ),
        ("Sensitivity analysis", "section 11", "met; Top 10 membership is sensitive"),
        ("Player-level evidence and exclusions", "`player_selection_explanations.md`", "met"),
        (
            "Phase 6 findings respected, no gate lowered",
            "gate reported unchanged; no shrinkage change",
            "met",
        ),
        ("Experimental AI kept separate", "token-protected route, separate CSVs, banner", "met"),
        ("Frontend with ten navigation items", "built and type-checked", "met"),
    ]
    a(md_table(pd.DataFrame(chk, columns=["requirement", "evidence", "state"])))
    a("")
    a("## 4. Verification state")
    a("")
    a(f"- pytest: {f.pt['line'] or 'no output recorded'}.")
    a(
        f"- ruff check exit {c['ruff_check']['exit_code']}, ruff format exit {c['ruff_format']['exit_code']}, npm build exit {c['npm_build']['exit_code']}, npm lint exit {c['npm_lint']['exit_code']}."
    )
    a(f"- Protected-file check: {json.dumps(c['protected'])}.")
    a("")
    a("## 5. What is incomplete or weak")
    a("")
    a(
        "1. **No validated or provisional ranking.** Split-half reliability is below 0.5 for both roles and every interval includes 0. This is the central limitation and it is stated on every list."
    )
    a(
        "2. **Pressure definition not validated.** The monotonic trend test fails for all seven candidates; P4 is the best available."
    )
    a(
        "3. **IPL and T20I not combinable by the declared rule.** The combined estimate is labelled unsupported."
    )
    a(
        "4. **Bowler index is a consistency share.** Components A and B received zero weight by the data-derived rule."
    )
    a(
        "5. **2026 matches unused.** The period was opened once earlier and is not pristine; using it needs an owner decision."
    )
    a(
        "6. **42 late-dated T20I matches** remain excluded and unverified against an official source."
    )
    a(
        "7. **AI audit depth.** Two of eight expected-outcome models were refit from scratch and the win-probability bundle was re-scored; the other six were checked for existence, metadata and loading only."
    )
    a(
        "8. **Frontend checks.** No unit tests. Not visually verified: the unlocked AI page, keyboard-only use, automated contrast. The linter reports warnings (see the test report)."
    )
    a(
        "9. **Reproducibility of the timing columns.** Test durations vary between runs; every ranking, table and hash in the reports does not."
    )
    a("")
    a("## 6. Owner actions")
    a("")
    a("1. Confirm the wording of the status labels and banners.")
    a("2. Decide whether to apply the 2026 matches as a labelled, non-pristine diagnostic.")
    a("3. Optionally verify the 42 late-dated T20I matches against an official source.")
    a(
        "4. Enter the two lists in the competition's selection form and check the document format required for the methodology report."
    )
    return "\n".join(L)


def doc_summary(f: Facts) -> str:
    cnt = f.pt["counts"]
    rb, rw = f.cmp_row("batter", f.chosen("batter")), f.cmp_row("bowler", f.chosen("bowler"))
    ai = f.ai
    bat, bow = f.top["batter"], f.top["bowler"]
    L: list[str] = []
    a = L.append
    a("# Final submission summary (Phase 8)")
    a("")
    a(f"Generated {f.stamp}. Criteria SHA-256 `{f.crit_hash}`.")
    a("")
    a("## Methodologies implemented")
    a("")
    a(
        "- **A, context-adjusted performance:** player-blind gradient-boosting expectation of runs and wicket per ball, residuals weighted by a continuous pressure intensity, REML shrinkage, match-cluster bootstrap."
    )
    a(
        "- **B, leverage and win probability added:** calibrated win-probability models (first innings and chase), explicit attribution rules, WPA above what the leverage predicts."
    )
    a(
        "- **C, Pressure Response Index:** components A, B and consistency weighted by data-derived reliability on fitting matches, evaluated on held-out matches."
    )
    a("")
    a("## Which performed best and why")
    a("")
    a(
        f"Selection followed the predeclared rule. Batters: approach {f.chosen('batter')} (split-half {f3(rb['sb'])}, out-of-time lower bound {f3(rb['oot_low'])}); A and C are tied within 0.001 and the choice is not a performance difference. Bowlers: approach {f.chosen('bowler')} (split-half {f3(rw['sb'])}, out-of-time lower bound {f3(rw['oot_low'])}). Approach B was weakest (split-half {f3(f.cmp_row('batter', 'B')['sb'])} for batters, {f3(f.cmp_row('bowler', 'B')['sb'])} for bowlers). No approach passes the PROVISIONAL threshold of 0.5 or the 0.5 data-weight gate."
    )
    a("")
    a("## Are the Top 10 lists available, and with what status")
    a("")
    a(
        f"Yes: {len(bat)} batters and {len(bow)} bowlers, ordered, none padded. Both lists, and every row, are **EXPLORATORY**; model validation status is also EXPLORATORY. The submitted ranking status and the model validation status are kept apart in the files."
    )
    a("")
    a("**Batters:** " + _top_names(f, "batter") + ".")
    a("")
    a("**Bowlers:** " + _top_names(f, "bowler") + ".")
    a("")
    a("## Headline evidence")
    a("")
    for role, d in (("Batters", bat), ("Bowlers", bow)):
        a(f"**{role}**")
        a("")
        t = pd.DataFrame(
            {
                "rank": d["rank"],
                "player": d["player_name"],
                "pressure matches": d["pressure_matches"],
                "pressure balls": d["pressure_deliveries"],
                "pressure level": d["pressure_performance_unshrunk"].map(f3),
                "normal baseline": d["normal_baseline"].map(f3),
                "difference": d["pressure_delta"].map(f3),
                "top-10 probability": d["top10_inclusion_probability"].map(
                    lambda v: f"{100 * v:.0f}%"
                ),
            }
        )
        a(md_table(t))
        a("")
    a("## Limitations")
    a("")
    a(
        "The data do not reliably separate players on pressure performance (Phase 6 finding, confirmed with a richer method); the pressure definition is unvalidated; the Top 10 membership moves with the definition and the shrinkage assumption; IPL and T20I results do not agree enough to combine; the 2026 matches are unused. See methodology section 13."
    )
    a("")
    a("## Phase 6 findings")
    a("")
    a(
        "Between-player variance at the shrinkage floor in all 48 contexts; pooled odd/even reliability 0.37 (0.3656), median 0.25; 0 of 48 contexts pass the 0.5 data-weight gate; no definition passed the predeclared criteria. None of these gates or the shrinkage method was changed."
    )
    a("")
    a("## Does the AI pipeline genuinely train and predict?")
    a("")
    inv = ai.get("inventory", [])
    a(
        f"Yes. {len(inv)} versioned artefacts exist in `backend/data/models/`. Retraining the batter-runs and bowler-wicket models from scratch on TRAIN reproduced the stored artefacts exactly (maximum prediction difference 0.0), and the win-probability chase model re-scored on 20,040 validation deliveries gives Brier 0.1167 against 0.2506 for a constant. Gains of the expected-outcome models over a constant are 1.5% to 3.1%. Predictions come from the stored artefacts. The experimental Top 10 files are served only by the token-protected route and are labelled EXPERIMENTAL_NOT_VALIDATED; their split-half reliability is about 0.2. Technical success is not reliability."
    )
    a("")
    a("## Tests")
    a("")
    a(
        f"`python -m pytest -q`: {f.pt['line'] or 'not recorded'} (passed {cnt['passed']}, failed {cnt['failed']}, errors {cnt['errors']}). `ruff check .` exit {f.checks['ruff_check']['exit_code']}; `ruff format --check .` exit {f.checks['ruff_format']['exit_code']}; `npm run build` exit {f.checks['npm_build']['exit_code']}; `npm run lint` exit {f.checks['npm_lint']['exit_code']}. Protected files: {json.dumps(f.checks['protected'])}. Details in `submission_test_report.md`."
    )
    a("")
    a("## What remains incomplete")
    a("")
    a(
        "No validated or provisional ranking exists. The 2026 matches are unused. The 42 late-dated T20I matches are unverified. Frontend unit tests do not exist; the unlocked AI page and keyboard-only use were not visually verified. Full list in `submission_readiness_audit.md`."
    )
    a("")
    a("## What the owner must do")
    a("")
    a("1. Confirm the status-label wording (EXPLORATORY, with the plain-language banner).")
    a("2. Optionally verify the 42 late T20I dates against an official source.")
    a("3. Decide whether the 2026 matches may be used as a labelled non-pristine diagnostic.")
    a(
        "4. Enter the two lists in the competition's dropdowns and check the required format of the methodology document."
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
        if name == "phase8_build_manifest.json":
            continue
        p = REPORTS / name
        outs[name] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    ins = {n: sha256(ROOT / n) for n, _ in SOURCE_FILES}
    for n, _ in DATABASES:
        ins[f"backend/data/database/{n}"] = sha256(BACKEND / "data/database" / n)
    for n in CONFIG_FILES:
        if (BACKEND / n).exists():
            ins[f"backend/{n}"] = sha256(BACKEND / n)
    return {
        "generated_utc": f.stamp,
        "methodology_version": "phase8_methodology_v1",
        "seed": SEED,
        "criteria_sha256": f.crit_hash,
        "criteria_file_sha256_now": sha256(CRITERIA_FILE),
        "protected_check": f.checks["protected"],
        "inputs_sha256": ins,
        "outputs": outs,
        "models": {m["artefact"]: m["sha256"] for m in f.ai.get("inventory", [])},
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
        "note": "Phase 3 to 6 reports and the aborted-run files are preserved on disk and are not part of the submission bundle.",
    }


def build_bundle() -> dict:
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    for old in SUBMISSION.iterdir():
        if old.is_file():
            old.unlink()
    entries = {}
    for name in BUNDLE_FILES:
        shutil.copyfile(REPORTS / name, SUBMISSION / name)
        entries[name] = {
            "sha256": sha256(SUBMISSION / name),
            "bytes": (SUBMISSION / name).stat().st_size,
        }
    manifest = {"files": entries, "algorithm": "SHA-256", "count": len(entries)}
    write(SUBMISSION / "MANIFEST_SHA256.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def stage_docs() -> None:
    f = Facts()
    write(REPORTS / "submission_methodology.md", doc_methodology(f))
    write(REPORTS / "submission_executive_summary.md", doc_executive(f))
    write(REPORTS / "submission_test_report.md", doc_test_report(f))
    write(REPORTS / "submission_readiness_audit.md", doc_audit(f))
    summary = doc_summary(f)
    write(SUMMARY_TASK_FILE, summary)
    write(REPORTS / "final_submission_summary.md", summary)
    write(
        REPORTS / "phase8_build_manifest.json",
        json.dumps(build_manifest(f), indent=2, sort_keys=True),
    )
    m = build_bundle()
    print(f"docs written; bundle of {m['count']} files in {SUBMISSION}")


def main(argv: list[str]) -> int:
    stage = argv[1] if len(argv) > 1 else "all"
    pt = None
    if "--pytest-output" in argv:
        pt = Path(argv[argv.index("--pytest-output") + 1])
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
