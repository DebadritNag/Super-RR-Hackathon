"""Phase 6: between-player variance estimators and floor-behaviour investigation.

Reads the stored context rows (``p5_context_stats``, TRAIN + VALIDATION) and the pre-test study,
writes ``p6_variance_estimators``, ``p6_floor_diagnostics`` and ``p6_floor_arithmetic`` plus
``phase6_variance_floor_investigation.md/json/csv``. TEST rows are never loaded, no lock event is
created, ``superr.duckdb`` is read-only and Cricsheet is not an input. Exit 1 on any failure of a
precondition (criteria hash, Phase 4 reproduction, preservation).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, fmt, md_table, write_text  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import variance_floor as vf  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, STATUS  # noqa: E402
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_variance_floor_investigation"


def read_context_stats(store: Path) -> pd.DataFrame:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return con.execute("SELECT * FROM p5_context_stats").df()
    finally:
        con.close()


def regression_vs_stored(dg: pd.DataFrame, reports: Path) -> dict:
    """TRAIN-window floor inputs of the 48 contexts against the stored Phase 5 fit."""
    stored = json.loads((reports / "phase5_context_fit.json").read_text(encoding="utf-8"))[
        "records"
    ]
    mine = dg[(dg["unit_kind"] == "context") & (dg["window"] == "TRAIN")]
    worst, n, missing = 0.0, 0, []
    for r in stored:
        m = mine[(mine["format"] == r["comp"]) & (mine["role"] == r["role"])
                 & (mine["phase"] == r["phase"]) & (mine["situation"] == r["situation"])]  # fmt: skip
        if m.empty or pd.isna(m["fit_between"].iloc[0]):
            missing.append(f"{r['comp']}|{r['role']}|{r['phase']}|{r['situation']}")
            continue
        m = m.iloc[0]
        diffs = [abs(m["fit_between"] - r["between"]), abs(m["fit_sigma2"] - r["sigma2"]),
                 abs(m["k_shrink_tau4"] - r["k"]), float(bool(m["floor_hit"]) != bool(r["floor_hit"]))]  # fmt: skip
        worst = max(worst, *diffs)
        n += 1
    return {"stored_records": len(stored), "compared": n, "missing": missing,
            "max_abs_diff": worst, "reproduces": bool(n == len(stored) and worst < 1e-9)}  # fmt: skip


def share(df: pd.DataFrame, col: str) -> str:
    d = df[col].dropna()
    return f"{int(d.sum())}/{len(d)}"


def render(res: dict) -> str:
    dg, est, ar = res["diag"], res["est"], res["arith"]
    ctx = dg[dg["unit_kind"] == "context"]
    cells = dg[dg["unit_kind"] == "stream_cell"]
    pre = ctx[ctx["window"] == "PRE_TEST"]
    trn = ctx[ctx["window"] == "TRAIN"]
    L = [
        "# Phase 6 variance-component and floor investigation",
        "",
        f"Status: {STATUS}. INTERNAL, in-sample diagnostics on TRAIN and VALIDATION. TEST "
        "outcomes: not used. Cricsheet: not used. No gate, threshold or Phase 4/5 artifact was "
        f"changed. Code version `{res['code_version'][:16]}`, seed {res['seed']}, "
        f"{res['n_boot']} match-cluster bootstrap draws. Criteria SHA-256 "
        f"`{res['criteria']['sha256']}` (declared before this run, run-log seq "
        f"{res['criteria']['seq']} for this step).",
        "",
        "## 1. Preconditions",
        f"- Floor inputs recomputed from the stored context rows reproduce `p5_context_fit` "
        f"({res['regress']['compared']}/{res['regress']['stored_records']} contexts, max abs "
        f"difference {res['regress']['max_abs_diff']:.2e}, reproduces = "
        f"{res['regress']['reproduces']}).",
        f"- `k_for` agrees with the hand formula in {int(ar['agrees'].sum())}/{len(ar)} "
        "configuration-branch rows (section 2).",
        "",
        "## 2. Floor arithmetic",
        "`k_for` gives `tau2 = max(max(between, floor_abs) * mult, floor_abs)` and `k = sigma2 / "
        "tau2`. The multiplier acts after the floor. Table from running `k_for` on a floor-hit "
        "fit (between -1, sigma2 3) and on the non-finite branch:",
        "",
        md_table(
            ["config", "branch", "floor", "mult", "k_for", "k_hand", "agrees"],
            rows_of(ar, ["config", "branch", "floor", "mult", "k_for", "k_hand", "agrees"]),
        ),
        "",
        f"For `shrink_tau4` on a floor hit: k = {fmt(float(ar[(ar['config'] == 'shrink_tau4') & (ar['branch'] == 'floor_hit')]['k_for'].iloc[0]), 1)} "
        f"= 1 / (4 x 0.01). In the stored contexts {int((trn['floor_hit'] == True).sum())} of "  # noqa: E712
        f"{len(trn)} TRAIN fits are floor hits and k under `shrink_tau4` takes the values "
        f"{sorted(trn['k_shrink_tau4'].dropna().round(6).unique().tolist())}.",
        "",
        "## 3. Verdicts per context",
        "Verdicts come from the pre-declared flag table; the text is not hand-written.",
        "",
    ]
    for label, d in (("PRE_TEST (primary window)", pre), ("TRAIN", trn)):
        vc = d["verdict"].value_counts().to_dict()
        ic = d["identification"].value_counts().to_dict()
        L += [f"**{label}, 48 contexts.** Verdict counts: {json.dumps(vc, sort_keys=True)}. "
              f"Identification counts: {json.dumps(ic, sort_keys=True)}.", ""]  # fmt: skip
    L += [
        "## 4. Why is the estimate at the floor? Flag counts (PRE_TEST contexts)",
        md_table(
            ["flag", "supported in"],
            [
                [f, share(pre, f)]
                for f in (
                    "flag_H-A_null",
                    "flag_H-A_power",
                    "flag_H-B_i",
                    "flag_H-B_ii",
                    "flag_H-B_iii",
                    "flag_H-B_iv",
                    "flag_H-B_overall",
                    "flag_H-C",
                )
            ],
        ),
        "",
        "- H-A_null: split-covariance interval contains 0 and fewer than 90% of bootstrap draws are positive.",
        "- H-A_power: detectability simulation, share of positive estimates at tau2/sigma2 = 0.01 at least 0.8.",
        "- H-B(i) to (iv): noise-model misspecification tests (Kish arithmetic, sign flip across bases, tercile variance ratio, ICC and dispersion).",
        "- H-C: the lower bound is positive and the required sample exceeds the observed median balls.",
        "",
        "### Between-variance sign by noise basis (PRE_TEST contexts)",
        md_table(
            ["basis", "contexts with raw between variance > 0", "median raw between variance"],
            [
                [b, f"{int((pre[c] > 0).sum())}/{int(pre[c].notna().sum())}", pre[c].median()]
                for b, c in (
                    ("Phase 4 Kish", "between_kish"),
                    ("independent balls", "between_ball_independent"),
                    ("match cluster", "between_match_cluster"),
                )
            ],
        ),
        "",
        "### Split-half covariance (E7, at least 6 balls per half) and E6",
        md_table(
            ["statistic", "value"],
            [
                ["contexts with E7 lower bound > 0", share(pre.assign(x=pre["e7_lo"] > 0), "x")],
                [
                    "contexts with E6 positive-draw share >= 0.9",
                    share(pre.assign(x=pre["e6_share_positive"] >= 0.9), "x"),
                ],
                [
                    "median detectability (share positive) at ratio 0.01",
                    pre["power_at_declared_ratio"].median(),
                ],
                [
                    "median Kish/ball noise ratio over balls per match",
                    pre["kish_ratio_over_balls_per_match"].median(),
                ],
                ["median player-match ICC", pre["icc_player_match"].median()],
                ["median Pearson dispersion", pre["pearson_dispersion"].median()],
            ],
        ),
        "",
        "### How far the verdict labels can be trusted",
        *res["reading"],
        "",
        "## 5. Cells of the study (definition x format x role x stream), PRE_TEST",
        f"{len(cells[cells['window'] == 'PRE_TEST'])} cells. Verdict counts: "
        f"{json.dumps(cells[cells['window'] == 'PRE_TEST']['verdict'].value_counts().to_dict(), sort_keys=True)}.",
        "",
        md_table(
            [
                "definition",
                "format",
                "role",
                "stream",
                "players",
                "verdict",
                "ident.",
                "E7 lo",
                "E7 hi",
                "E6 share>0",
                "between Kish",
                "between cluster",
            ],
            rows_of(
                cells[(cells["window"] == "PRE_TEST") & (cells["definition"] == "any|q0.75")],
                [
                    "definition",
                    "format",
                    "role",
                    "stream",
                    "players",
                    "verdict",
                    "identification",
                    "e7_lo",
                    "e7_hi",
                    "e6_share_positive",
                    "between_kish",
                    "between_match_cluster",
                ],
            ),
        ),
        "",
        "## 6. Estimator comparison (primary streams, any|q0.75, PRE_TEST)",
        md_table(
            ["format", "role", "estimator", "basis", "value", "raw between", "status", "lo", "hi"],
            rows_of(
                est[
                    (est["definition"] == "any|q0.75")
                    & (est["window"] == "PRE_TEST")
                    & (est["unit_kind"] == "stream_cell")
                    & est["is_primary_stream"].eq(True)
                    & (~est["noise_basis"].astype(str).str.contains("min_balls=1$"))
                ],  # fmt: skip
                [
                    "format",
                    "role",
                    "estimator",
                    "noise_basis",
                    "value",
                    "between_raw",
                    "status",
                    "lo",
                    "hi",
                ],
            ),
        ),
        "",
        "## 7. Required sample (balls per player for reliability 0.5, 0.7, 0.8)",
        "Computed only where a lower bound is above 0; otherwise `NOT_ESTIMABLE`.",
        "",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "n* R=0.5",
                "n* R=0.7",
                "n* R=0.8",
                "median balls",
            ],
            rows_of(
                pre[pre["verdict"] != "NOT_ESTIMABLE"].head(48),
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "n_star_r050",
                    "n_star_r070",
                    "n_star_r080",
                    "median_balls",
                ],
            ),
        ),
        "",
        "## 8. Consequence",
    ]
    L += res["consequence"]
    L += [
        "",
        "## 9. Limits",
        "- Every number is in-sample. A consistent finding across estimators is not validation.",
        "- The noise model cannot be tested with these data alone; the three noise bases bracket it.",
        "- E4 and E5 are sensitivity checks. E5 is `MISSPECIFIED_FOR_RUNS` on runs streams.",
        "- Within-innings dependence is not separable: stored context rows are match-level sums.",
        "- The detectability simulation is parametric; its noise comes from the observed match-cluster basis.",
        "",
        "## 10. Per-context table (PRE_TEST)",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "players",
                "between Kish",
                "between cluster",
                "E7",
                "E7 lo",
                "E7 hi",
                "E6 share>0",
                "verdict",
                "ident.",
            ],
            rows_of(
                pre,
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "players",
                    "between_kish",
                    "between_match_cluster",
                    "e7_value",
                    "e7_lo",
                    "e7_hi",
                    "e6_share_positive",
                    "verdict",
                    "identification",
                ],
            ),
        ),
        "",
    ]
    return "\n".join(L)


def reading(pre: pd.DataFrame) -> list[str]:
    """Generated caveats: what the model-free covariance says versus the model-based labels."""
    ok = pre[pre["identification"] != "NOT_ESTIMABLE"]
    n = len(ok)
    e7_pos = int((ok["e7_lo"] > 0).sum())
    e7_zero = int(((ok["e7_lo"] <= 0) & (ok["e7_hi"] >= 0)).sum())
    bias = int((ok["e6_cluster_median"] > ok["between_match_cluster"]).sum())
    ratio = (ok["e7_value"] / ok["between_match_cluster"]).median()
    share_hi = int((ok["e6_share_positive"] >= 0.9).sum())
    return [
        f"- Model-free split covariance (E7), {n} estimable contexts: lower bound above 0 in "
        f"{e7_pos}, interval contains 0 in {e7_zero}. This is the only estimator that does not "
        "depend on a noise model.",
        f"- E6 positive-draw share is at least 0.9 in {share_hi}/{n} contexts. The pre-declared "
        "H-A null needs a share below 0.9, so `H-A_SUPPORTED` could not be reached in this data "
        "even where E7 includes 0.",
        f"- The E6 bootstrap median of the match-cluster estimate exceeds its point estimate in "
        f"{bias}/{n} contexts, so resampled estimates are shifted upwards and the E6 lower bound "
        "above 0 (used for H-C) is a weaker kind of evidence than the E7 lower bound.",
        f"- Median ratio of the E7 estimate to the match-cluster point estimate: {ratio:.2f}. "
        "The cluster basis therefore gives larger between-variance than the model-free split "
        "covariance, in line with a cluster noise estimate that is biased low for players with "
        "few matches.",
        "- Labels `H-C_SUPPORTED` and `MIXED` below rest partly on E6 and the cluster basis. "
        "They say the cluster-basis estimate is positive and larger samples would help; they do "
        "not show that the between-player variance is positive.",
    ]


def consequence(pre: pd.DataFrame) -> list[str]:
    vc = pre["verdict"].value_counts().to_dict()
    n = len(pre)
    ident = pre["identification"].value_counts().to_dict()
    out = [
        f"Verdicts over the {n} contexts: {json.dumps(vc, sort_keys=True)}. "
        f"Identification: {json.dumps(ident, sort_keys=True)}."
    ]
    if vc.get("UNIDENTIFIED", 0) + vc.get("NOT_ESTIMABLE", 0):
        out.append(
            "- Contexts that are `UNIDENTIFIED` or `NOT_ESTIMABLE`: the data cannot identify the "
            "between-player variance. Consequence: wider uncertainty (intervals from E6), shorter "
            "lists, and these contexts stay restricted. The shrinkage estimator is not changed here."
        )
    if vc.get("H-B_SUPPORTED", 0) + vc.get("MIXED", 0):
        out.append(
            "- Contexts with `H-B_SUPPORTED` or `MIXED`: noise-model misspecification is "
            "supported. OPEN DECISION for the user: whether to switch the noise basis in the "
            "methodology. Not applied; a methodology change is outside this phase's stop condition."
        )
    if vc.get("H-A_SUPPORTED", 0):
        out.append("- Contexts with `H-A_SUPPORTED`: a true between-player variance about zero "
                   "is supported and the design had adequate detectability.")  # fmt: skip
    if vc.get("H-C_SUPPORTED", 0):
        out.append("- Contexts with `H-C_SUPPORTED`: a positive lower bound exists but the sample "
                   "is below the required size; more data would be needed.")  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    rep, store = args.reports, args.store
    guard = Preservation(rep)
    lock_before = lock_state()
    p4_before, p5_before = table_hashes(store, "p4_"), table_hashes(store, "p5_")
    crit_info = cr.begin_step("variance_floor", store_path=store)
    crit = cr.load_criteria()
    inv_cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    n_boot = int(args.n_boot or inv_cfg["n_boot"])
    seed = int(inv_cfg["seed"])

    stats = read_context_stats(store)
    study = pl.load_study(store, n_boot=n_boot, seed=seed)
    est_c, dg_c = vf.run_contexts(stats, crit, inv_cfg, n_boot, seed)
    est_s, dg_s = vf.run_stream_cells(study, inv_cfg["definitions"]["candidates"], crit, inv_cfg)
    est = pd.concat([est_c, est_s], ignore_index=True)
    dg = pd.concat([dg_c, dg_s], ignore_index=True)
    arith = vf.floor_arithmetic_table()
    regress = regression_vs_stored(dg, rep)
    if not regress["reproduces"]:
        print("FATAL: stored p5_context_fit not reproduced", regress)
        return 1
    if not bool(arith["agrees"].all()):
        print("FATAL: k_for disagrees with the hand formula")
        return 1

    pre = dg[(dg["unit_kind"] == "context") & (dg["window"] == "PRE_TEST")]
    res = {"diag": dg, "est": est, "arith": arith, "regress": regress, "criteria": crit_info,
           "code_version": code_version(), "seed": seed, "n_boot": n_boot,
           "consequence": consequence(pre), "reading": reading(pre)}  # fmt: skip
    save_table(est, "phase6_variance_estimators", rep, store, "p6_variance_estimators")
    save_table(dg, NAME, rep, store, "p6_floor_diagnostics")
    save_table(arith, "phase6_floor_arithmetic", rep, store, "p6_floor_arithmetic")
    write_text(rep / f"{NAME}.md", render(res))

    # preservation: Phase 4/5 tables, TEST lock, official data
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "contexts": len(pre),
                      "estimator_rows": len(est), "diagnostic_rows": len(dg),
                      "regression": regress, "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
