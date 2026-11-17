"""Phase 5 Chunk 3 (a): why is signal-to-noise at or below zero? Reliability and variance study.

Reads the pre-test (TRAIN + VALIDATION) state read-only, rebuilds the carried PROVISIONAL
definition ``any|q0.75`` and the three sensitivity alternatives with the unchanged Phase 4 code,
and reports variance decomposition (four noise bases), split-half reliability (odd/even,
early/late, random), ICC, match-cluster bootstrap intervals, reliability against pressure
opportunities, descriptive sample-size projections, a detectability simulation, bowler-specific
signals (SENSITIVITY_ONLY) and IPL + T20I pooling. TEST rows are never loaded, Cricsheet is never
read, nothing is labelled validated. Exit 1 if official data, Phase 4 reports or the lock changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, md_table, write_json_deterministic, write_text  # noqa: E402
from app.phase5 import investigation as inv  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5 import spotchecks as spc  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.outputs import Preservation, failing_gates, rows_of, save_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NOT_OFFICIAL = (
    f"Status: {STATUS}. PROVISIONAL and descriptive. Not an official ranking, no ML model, nothing "
    "here is validated. TEST outcomes: not used. Cricsheet: not used."
)
BASIS_NAME = {
    "phase4_kish": "Phase 4 (sigma2 / n_eff_kish)",
    "ball_independent": "independent balls (sigma2 / n)",
    "match_cluster": "match-cluster robust",
    "split_half_covariance": "split-half covariance",
}


def reproduce_phase4_snr(study: pl.Study, store: Path, var_df: pd.DataFrame) -> dict:
    """Compare the TRAIN Phase 4 SNR (any|q0.75) with the stored Phase 4 definition table."""
    import duckdb

    con = duckdb.connect(str(store), read_only=True)
    try:
        t = con.execute(
            "SELECT definition_id, format, role, snr FROM p4_definition_comparison WHERE definition_id = ?",
            [study.cfg["definitions"]["primary"]],
        ).df()
    finally:
        con.close()
    out, worst = {}, 0.0
    for _, r in t.iterrows():
        m = var_df[(var_df["definition"] == r["definition_id"]) & (var_df["format"] == r["format"])
                   & (var_df["role"] == r["role"]) & var_df["is_primary_stream"]
                   & (var_df["window"] == "TRAIN") & (var_df["min_balls"] == 1)
                   & (var_df["noise_basis"] == "phase4_kish")]  # fmt: skip
        mine = float(m["snr"].iloc[0]) if len(m) else float("nan")
        diff = (
            abs(mine - float(r["snr"]))
            if np.isfinite(mine) and pd.notna(r["snr"])
            else float("nan")
        )
        out[f"{r['format']}|{r['role']}"] = {
            "phase4_snr": float(r["snr"]),
            "phase5_snr": mine,
            "abs_diff": diff,
        }
        worst = max(worst, diff if np.isfinite(diff) else 1.0)
    return {"cells": out, "max_abs_diff": worst, "reproduces": bool(out and worst < 1e-9)}


def primary_view(df: pd.DataFrame, **flt) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    for k, v in flt.items():
        m &= df[k] == v
    return df[m]


# ---------------------------------------------------------------- report
def render(res: dict) -> str:
    var, sh, opp, proj = res["variance"], res["split_half"], res["opportunity"], res["projection"]
    det, pool, bow = res["detect"], res["pooling"], res["bowler"]
    prim = res["primary"]
    L = [
        "# Phase 5 investigation: why signal-to-noise is at or below zero",
        "",
        NOT_OFFICIAL,
        "",
        f"Primary definition `{prim}` is PROVISIONAL: the Phase 4 rule winner among nine candidates, "
        "not shown valid or superior. Alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75` are kept as "
        "sensitivity runs. Data: TRAIN and VALIDATION (pre-test) rows only, baseline B0 fitted on TRAIN, "
        f"match-cluster bootstrap with {res['n_boot']} draws, seed {res['seed']}. "
        f"Code version `{res['code_version'][:16]}`.",
        "",
        "## 0. Preconditions checked before any number below was computed",
        f"- Phase 4 scores reproduced from the unchanged code: max abs difference "
        f"{res['reproduction']['max_abs_diff']:.2e} over {res['reproduction']['players_compared']} players "
        f"(tolerance 1e-9, reproduces = {res['reproduction']['reproduces']}).",
        f"- Phase 4 SNR (TRAIN, `{prim}`) reproduced from the stored definition table: max abs difference "
        f"{res['snr_repro']['max_abs_diff']:.2e} (reproduces = {res['snr_repro']['reproduces']}).",
        "",
        "## 1. Finding in one paragraph",
    ]
    L += res["headline"]
    L += [
        "",
        "## 2. Variance decomposition of the primary definition (TRAIN window, primary streams)",
        "tau2 is the estimated between-player variance of the mean residual, noise is the mean sampling variance "
        "of a player mean, SNR = tau2 / noise, ICC = max(tau2, 0) / (max(tau2, 0) + noise). The Phase 4 basis "
        "reproduces the Phase 4 figure. The other bases change only how the sampling noise of a player mean is "
        "estimated. 'share tau2>0' is the share of match-bootstrap draws with a positive estimate.",
        "",
    ]
    v = var[
        (var["definition"] == prim)
        & var["is_primary_stream"]
        & (var["window"] == "TRAIN")
        & (var["min_balls"] == 1)
    ]
    L.append(md_table(
        ["format", "role", "noise basis", "players", "tau2", "tau2 boot lo", "tau2 boot hi", "noise", "SNR", "ICC", "REML tau2", "share tau2>0", "status"],
        [[r.format, r.role, BASIS_NAME[r.noise_basis], r.players, r.tau2_moment, r.tau2_boot_lo, r.tau2_boot_hi,
          r.mean_noise_variance, r.snr, r.icc_truncated_at_0, r.tau2_reml, r.boot_share_tau2_positive, r.status]
         for r in v.itertuples()]))  # fmt: skip
    L += ["", "### Same, players with at least 12 pressure balls (TRAIN)", ""]
    v = var[
        (var["definition"] == prim)
        & var["is_primary_stream"]
        & (var["window"] == "TRAIN")
        & (var["min_balls"] == 12)
    ]
    L.append(md_table(
        ["format", "role", "noise basis", "players", "tau2", "noise", "SNR", "ICC", "REML tau2", "status"],
        [[r.format, r.role, BASIS_NAME[r.noise_basis], r.players, r.tau2_moment, r.mean_noise_variance, r.snr,
          r.icc_truncated_at_0, r.tau2_reml, r.status] for r in v.itertuples()]))  # fmt: skip
    L += [
        "",
        "### Primary definition, full pre-test window (TRAIN + VALIDATION), at least 12 balls",
        "",
    ]
    v = var[
        (var["definition"] == prim)
        & var["is_primary_stream"]
        & (var["window"] == "PRE_TEST")
        & (var["min_balls"] == 12)
    ]
    L.append(md_table(
        ["format", "role", "noise basis", "players", "tau2", "noise", "SNR", "ICC", "status"],
        [[r.format, r.role, BASIS_NAME[r.noise_basis], r.players, r.tau2_moment, r.mean_noise_variance, r.snr,
          r.icc_truncated_at_0, r.status] for r in v.itertuples()]))  # fmt: skip
    L += [
        "",
        "## 3. Split-half reliability (Spearman-Brown corrected, minimum 6 balls in each half)",
        "Odd/even splits each player's matches by chronological parity. Early/late compares the first and second "
        "half of a player's matches (it mixes noise with real change in form, so it is a lower bound). Random "
        "averages 200 seeded random splits. Intervals are match-cluster bootstrap 2.5% and 97.5% percentiles. "
        "A cell with fewer than 10 qualifying players is `NOT_ESTIMABLE`.",
        "",
    ]
    s = sh[(sh["definition"] == prim) & sh["is_primary_stream"]]
    L.append(md_table(
        ["format", "role", "window", "mode", "players", "r (Pearson)", "SB Pearson", "SB lo", "SB hi", "SB Spearman", "SD across random splits", "status"],
        rows_of(s.sort_values(["role", "format", "window", "mode"]),
                ["format", "role", "window", "mode", "players", "r_pearson", "sb_pearson", "sb_lo", "sb_hi", "sb_spearman", "split_sd_sb_pearson", "status"])))  # fmt: skip
    L += ["", "### All four definitions, odd/even, full pre-test window, primary streams", ""]
    s = sh[sh["is_primary_stream"] & (sh["window"] == "PRE_TEST") & (sh["mode"] == "odd_even")]
    L.append(md_table(
        ["definition", "format", "role", "players", "SB Pearson", "SB lo", "SB hi", "status"],
        rows_of(s.sort_values(["role", "format", "definition"]), ["definition", "format", "role", "players", "sb_pearson", "sb_lo", "sb_hi", "status"])))  # fmt: skip
    L += [
        "",
        "### Alternatives: variance decomposition (PRE_TEST, at least 12 balls, match-cluster and Phase 4 bases)",
        "",
    ]
    v = var[var["is_primary_stream"] & (var["window"] == "PRE_TEST") & (var["min_balls"] == 12)
            & var["noise_basis"].isin(["phase4_kish", "match_cluster", "split_half_covariance"])]  # fmt: skip
    L.append(md_table(
        ["definition", "format", "role", "noise basis", "players", "tau2", "SNR", "ICC", "status"],
        rows_of(v.sort_values(["role", "format", "definition", "noise_basis"]),
                ["definition", "format", "role", "noise_basis", "players", "tau2_moment", "snr", "icc_truncated_at_0", "status"])))  # fmt: skip
    L += [
        "",
        "## 4. Reliability against pressure opportunities (primary streams, full pre-test window)",
        "Players with at least t pressure balls in the window; odd/even Spearman-Brown reliability and the "
        "match-cluster SNR/ICC inside that group. The group changes with t, so rows are not independent.",
        "",
    ]
    o = opp[opp["definition"] == prim]
    L.append(md_table(
        ["format", "role", "min balls", "players", "SB odd/even", "SB lo", "SB hi", "SNR (cluster)", "ICC (cluster)", "SNR (Phase 4)", "status"],
        rows_of(o.sort_values(["role", "format", "min_total_balls"]),
                ["format", "role", "min_total_balls", "players_ge_t", "sb_odd_even", "sb_lo", "sb_hi", "snr_match_cluster", "icc_match_cluster", "snr_phase4_kish", "status"])))  # fmt: skip
    L += [
        "",
        "## 5. Sample size needed for reliability targets (DESCRIPTIVE_PROJECTION, not a threshold)",
        "n* = R / (1 - R) x sigma_eff / tau2, per noise basis, using the full pre-test window and all players "
        "(`min_balls` = 1). For the Phase 4 basis the unit is Kish effective units, for the others it is balls. "
        "`NOT_ESTIMABLE` appears where tau2 is not positive. The last column re-computes n* with tau2 at its "
        "bootstrap 90th percentile (an optimistic bound). None of these numbers is an eligibility threshold.",
        "",
    ]
    p = proj[(proj["definition"] == prim) & (proj["window"] == "PRE_TEST")]
    L.append(md_table(
        ["format", "role", "noise basis", "target R", "unit", "n* (point)", "n* (tau2 at boot p90)", "median player balls", "P90 player balls", "share of players >= n*"],
        rows_of(p.sort_values(["role", "format", "noise_basis", "target_reliability"]),
                ["format", "role", "noise_basis", "target_reliability", "unit", "required_n_point", "required_n_if_tau2_at_bootstrap_p90", "observed_median_player_balls", "observed_p90_player_balls", "share_players_at_or_above_required"])))  # fmt: skip
    L += [
        "",
        "## 6. Could samples like these detect a between-player variance? (parametric simulation)",
        "Players receive a true effect with variance tau2 = ratio x sigma2 plus noise with the observed per-player "
        "noise variance (at least 12 balls, full pre-test window). 'positive' is the share of 400 replications in "
        "which the moment estimator is above zero; 'within 50%' is the share within 50% of the truth. The "
        "simulation assumes the noise model is right, which is the open question.",
        "",
    ]
    d = det[det["noise_basis"] == "match_cluster"]
    L.append(md_table(
        ["format", "role", "tau2 / sigma2", "true ICC", "share positive", "share within 50%", "players"],
        rows_of(d.sort_values(["role", "format", "tau2_over_sigma2"]), ["format", "role", "tau2_over_sigma2", "true_icc", "share_estimate_positive", "share_estimate_within_50pct_of_truth", "players"])))  # fmt: skip
    L += [
        "",
        "## 7. Bowler-specific pressure signals (SENSITIVITY_ONLY)",
        "The primary definition applies batter-state signals to bowlers: its innings-1 rows are states in which the "
        "batting side is BEHIND the prior par, which are easy states for a bowler. Three candidates, declared in "
        "`config/phase5_investigation_v1.json` before any run, flag states in which the bowling side is under pressure. "
        "Thresholds are TRAIN-only per format. They do not replace the primary definition, nothing is selected on "
        "these numbers, and all four signals are reported. Thresholds: "
        f"`{res['bowler_meta']['thresholds_train_only']}`. Not buildable: {res['bowler_meta']['not_buildable'] or 'none'}.",
        "",
    ]
    b = bow[(bow["kind"] == "split_half") & (bow["window"] == "PRE_TEST")]
    L.append(md_table(
        ["signal", "format", "mode", "pressure balls", "players >= 18 balls (TRAIN)", "qualifying players", "SB", "SB lo", "SB hi", "status"],
        rows_of(b.sort_values(["format", "mode", "candidate"]), ["candidate", "format", "mode", "pressure_balls_total", "players_ge_18_balls_TRAIN", "players", "sb_pearson", "sb_lo", "sb_hi", "status"])))  # fmt: skip
    L += ["", "Variance decomposition of the same signals (PRE_TEST, at least 12 balls):", ""]
    b = bow[(bow["kind"] == "variance_decomposition") & (bow["window"] == "PRE_TEST")
            & bow["noise_basis"].isin(["phase4_kish", "match_cluster", "split_half_covariance"])]  # fmt: skip
    L.append(md_table(
        ["signal", "format", "noise basis", "players", "tau2", "SNR", "ICC", "status"],
        rows_of(b.sort_values(["format", "candidate", "noise_basis"]), ["candidate", "format", "noise_basis", "players", "tau2_moment", "snr", "icc_truncated_at_0", "status"])))  # fmt: skip
    L += [
        "",
        "## 8. Pooling IPL and T20I for players who appear in both (descriptive)",
        "Same players, same odd/even rule, each format baseline-adjusted separately, matches pooled chronologically. "
        "Only players qualifying (6 balls per half) in all three analyses are compared. No bootstrap interval is "
        "computed here.",
        "",
    ]
    q = pool[pool["definition"] == prim]
    L.append(md_table(
        ["role", "window", "players in both", "qualifying in all three", "SB IPL only", "SB T20I only", "SB pooled", "ICC cluster IPL", "ICC cluster T20I", "ICC cluster pooled", "status"],
        rows_of(q.sort_values(["role", "window"]), ["role", "window", "players_in_both_formats", "players_qualifying_in_all_three", "sb_first_format", "sb_second_format", "sb_pooled", "icc_cluster_first_format", "icc_cluster_second_format", "icc_cluster_pooled", "status"])))  # fmt: skip
    L += ["", "## 9. What the data can and cannot support"]
    L += res["limits"]
    L += ["", "## 10. Unresolved issues"]
    L += [f"{i}. {t}" for i, t in enumerate(res["unresolved"], 1)]
    L += ["", "## 11. Gates still failing (from `phase5_publication_gates.json`)"]
    g = res["gates"]
    if g.get("available"):
        L.append(f"Publication status of any ranking today: `{g['publication_status']}`.")
        L.append(
            md_table(
                ["gate", "passed", "applicable", "detail"],
                [
                    [x["gate_id"], x["passed"], x["applicable"], x["detail"]]
                    for x in g["gate_results"]
                ],
            )
        )
    else:
        L.append(g["note"])
    L += ["", "## 12. Independent spot checks"]
    for sck in res["spotchecks"]:
        L.append(f"- {sck}")
    L += ["", "## 13. Preservation", f"`{res['preservation']}`"]
    return "\n".join(L) + "\n"


def headline(res: dict) -> list[str]:
    var, sh, prim = res["variance"], res["split_half"], res["primary"]
    base = var[
        (var["definition"] == prim)
        & var["is_primary_stream"]
        & (var["window"] == "TRAIN")
        & (var["min_balls"] == 1)
    ]
    p4 = base[base["noise_basis"] == "phase4_kish"]
    cl = base[base["noise_basis"] == "match_cluster"]
    ball = base[base["noise_basis"] == "ball_independent"]
    spl = sh[
        (sh["definition"] == prim)
        & sh["is_primary_stream"]
        & (sh["window"] == "PRE_TEST")
        & (sh["mode"] == "odd_even")
    ]
    est = spl[spl["status"] == "ESTIMATED"]
    out = (
        [
            f"On the Phase 4 noise basis the between-player variance is not positive in {int((p4['tau2_moment'] <= 0).sum())} of "
            f"{len(p4)} cells (SNR {p4['snr'].min():.2f} to {p4['snr'].max():.2f}), which reproduces the Phase 4 finding. That "
            "estimator divides a per-ball residual variance by a Kish count of equally sized MATCHES, so its noise term is "
            "larger than the sampling variance of a player mean by roughly the number of pressure balls per match. "
            f"With the noise estimated as independent balls the estimate is positive in {int((ball['tau2_moment'] > 0).sum())} of "
            f"{len(ball)} cells and with match-cluster noise in {int((cl['tau2_moment'] > 0).sum())} of {len(cl)}. Those two bases "
            "bracket the truth (independent balls understate noise when balls inside a match are dependent, the cluster "
            "estimator is biased low with few matches per player), so the data cannot pin the size of tau2.",
            "",
            f"A model-free check agrees that some between-player signal exists: odd/even split-half reliability on the full "
            f"pre-test window is estimable in {len(est)} of {len(spl)} cells, with Spearman-Brown values from "
            f"{est['sb_pearson'].min():.2f} to {est['sb_pearson'].max():.2f} (intervals in section 3). These are modest, and the "
            "intervals of several cells reach or cross zero. The statement 'signal-to-noise is at or below zero' is therefore "
            "mainly a property of the Phase 4 noise estimator, not proof that players do not differ under pressure. It is also "
            "not proof that the ranking is reliable. This is an open issue for review: the Phase 4 estimator is NOT changed "
            "here (methodology is not locked).",
        ]
        if len(est)
        else [
            "Split-half reliability could not be estimated for the primary cells with the declared minimums."
        ]
    )
    return out


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    rep = args.reports
    guard = Preservation(rep)
    study = pl.load_study(args.store, n_boot=args.n_boot)
    repro = pl.reproduce_phase4_scores(study, args.store)
    if not repro["reproduces"]:
        print("FATAL: Phase 4 scores do not reproduce", repro)
        return 1
    defns = inv.definitions(study)
    var = inv.run_variance(study, defns)
    snr_repro = reproduce_phase4_snr(study, args.store, var)
    if not snr_repro["reproduces"]:
        print("FATAL: Phase 4 SNR does not reproduce", snr_repro)
        return 1
    sh = inv.run_split_half(study, defns)
    opp = inv.run_opportunity(study, defns)
    proj = inv.run_projection(study, var, defns)
    det = inv.run_detectability(study, defns[0])
    pool = inv.run_pooling(study, defns)
    bow, bow_meta = inv.run_bowler_signals(study)
    for name, df, table in (
        ("phase5_variance_decomposition", var, "p5_variance_decomposition"),
        ("phase5_split_half_reliability", sh, "p5_split_half_reliability"),
        ("phase5_reliability_by_opportunity", opp, "p5_reliability_by_opportunity"),
        ("phase5_required_sample_projection", proj, "p5_required_sample_projection"),
        ("phase5_multiformat_pooling", pool, "p5_multiformat_pooling"),
        ("phase5_bowler_signal_sensitivity", bow, "p5_bowler_signal_sensitivity"),
        ("phase5_detectability_simulation", det, "p5_detectability_simulation"),
    ):
        save_table(df, name, rep, args.store, table)

    # independent spot checks ------------------------------------------------
    prim = defns[0]
    rows = study.pressure_rows(prim, "batter", "runs")
    ind = spc.independent_odd_even(
        rows, "IPL", ("TRAIN", "VALIDATION"), study.cfg["split_half"]["min_balls_per_half"]
    )
    mine = sh[(sh["definition"] == prim) & (sh["format"] == "IPL") & (sh["role"] == "batter") & (sh["stream"] == "runs")
              & (sh["window"] == "PRE_TEST") & (sh["mode"] == "odd_even")].iloc[0]  # fmt: skip
    sc1 = {"stream": "IPL batter runs, any|q0.75, PRE_TEST, odd/even, min 6 balls per half",
           "independent_players": ind["players"], "independent_r": ind["r"], "independent_sb": ind["sb"],
           "module_players": int(mine["players"]), "module_r": float(mine["r_pearson"]), "module_sb": float(mine["sb_pearson"]),
           "abs_diff_r": abs(ind["r"] - float(mine["r_pearson"])), "players_equal": ind["players"] == int(mine["players"])}  # fmt: skip
    ind2 = spc.independent_phase4_snr(
        study.pressure_rows(prim, "bowler", "charged"), "T20I", "TRAIN"
    )
    mine2 = var[(var["definition"] == prim) & (var["format"] == "T20I") & (var["role"] == "bowler") & (var["stream"] == "charged")
                & (var["window"] == "TRAIN") & (var["min_balls"] == 1) & (var["noise_basis"] == "phase4_kish")].iloc[0]  # fmt: skip
    sc2 = {"stream": "T20I bowler charged runs, any|q0.75, TRAIN, Phase 4 basis", "independent_snr": ind2["snr"],
           "module_snr": float(mine2["snr"]), "abs_diff": abs(ind2["snr"] - float(mine2["snr"])),
           "independent_tau2": ind2["between"], "module_tau2": float(mine2["tau2_moment"])}  # fmt: skip
    spot = {"split_half": sc1, "snr": sc2,
            "split_half_agrees": bool(sc1["players_equal"] and sc1["abs_diff_r"] < 1e-9),
            "snr_agrees": bool(sc2["abs_diff"] < 1e-9)}  # fmt: skip
    write_json_deterministic(
        rep / "phase5_investigation_spotcheck.json", {"status": STATUS, **spot}
    )
    if not (spot["split_half_agrees"] and spot["snr_agrees"]):
        print("FATAL: independent spot checks disagree", spot)
        return 1

    pres = guard.verify()
    limits = [
        "- Between-player variance cannot be pinned: its estimate depends on the noise model (section 2) and the "
        "noise model cannot be tested with these data alone. Treat every tau2, SNR and ICC as a bracket, not a value.",
        "- The cluster-robust noise is biased low for players with few matches; the independent-ball noise is biased low "
        "when balls inside a match are dependent; the Phase 4 noise is biased high. REML and the split-half covariance "
        "are cross-checks, not the truth.",
        "- Projections in section 5 inherit that uncertainty and use the pre-test sample only. They say how many pressure "
        "balls a stable estimate would need under each noise model, not how many a validated eligibility rule should require.",
        "- Early/late split-half is a lower bound on reliability because form changes over time.",
        "- Bootstrap percentile intervals are not bias-corrected and can sit off the point value (duplicated matches in a "
        "resample change the half-sample noise); read them as spread, not as a confidence statement.",
        "- Alternative definitions are NOT ranked against each other here and no definition is shown to be better.",
        "- No outcome of the TEST period is used or inferable from this report.",
    ]
    unresolved = [
        "Noise model of the shrinkage estimator: the Phase 4 `n_eff` is a Kish count of equally sized matches but is divided "
        "into a per-ball variance. This drives the negative Phase 4 SNR and the strong shrinkage (floor hits, `shrink_tau4`). "
        "Choosing a different noise model changes every shrunk score and needs a decision before the methodology is locked.",
        "The size of the between-player variance remains unidentified (brackets in section 2). Until it is identified, "
        "ranking reliability claims are not supportable.",
        "Bowler pressure uses batter-state signals. Section 7 shows how three bowler-specific candidates behave; "
        "no candidate is adopted. Adopting one is a methodology decision.",
        "Every eligibility threshold is still the unvalidated TRAIN-median working pool (20 / 16 / 49 / 29 balls).",
        "Sample sizes are small in several cells (see player counts); intervals are wide and some cells are NOT_ESTIMABLE.",
        "Date verification, strict capped/uncapped classification and the methodology-validation gate are unresolved "
        "(section 11). A later TEST evaluation is not a pristine hold-out because Phase 4 aggregate TEST results were shown.",
    ]
    res = {
        "primary": prim,
        "n_boot": study.n_boot,
        "seed": study.seed,
        "code_version": code_version(),
        "reproduction": repro,
        "snr_repro": snr_repro,
        "variance": var,
        "split_half": sh,
        "opportunity": opp,
        "projection": proj,
        "detect": det,
        "pooling": pool,
        "bowler": bow,
        "bowler_meta": bow_meta,
        "limits": limits,
        "unresolved": unresolved,
        "gates": failing_gates(rep),
        "spotchecks": [
            f"Split-half (IPL batter runs, `{prim}`, PRE_TEST, odd/even): independent pandas loop r = {sc1['independent_r']:.6f} "
            f"({sc1['independent_players']} players) vs module r = {sc1['module_r']:.6f} ({sc1['module_players']} players), "
            f"abs diff {sc1['abs_diff_r']:.1e}.",
            f"Phase 4 SNR (T20I bowler, TRAIN) recomputed from raw rows: {sc2['independent_snr']:.6f} vs module {sc2['module_snr']:.6f}.",
        ],
        "preservation": pres,
    }
    res["headline"] = headline(res)
    write_text(rep / "phase5_investigation_report.md", render(res))
    write_json_deterministic(
        rep / "phase5_investigation_summary.json",
        {
            "status": STATUS,
            "official_ranking": False,
            "primary_definition": prim,
            "primary_label": study.cfg["definitions"]["primary_label"],
            "alternatives": defns[1:],
            "n_boot": study.n_boot,
            "seed": study.seed,
            "code_version": code_version(),
            "config_hashes": pl.config_hashes(),
            "phase4_reproduction": {k: v for k, v in repro.items() if k != "per_cell"},
            "phase4_snr_reproduction": snr_repro,
            "spotchecks": spot,
            "bowler_signal_meta": bow_meta,
            "headline": res["headline"],
            "unresolved_issues": unresolved,
            "gates": res["gates"],
            "preservation": pres,
        },
    )
    print(
        "investigation done | preserved:",
        pres["all_preserved"],
        "| spot checks:",
        spot["split_half_agrees"],
        spot["snr_agrees"],
    )
    return 0 if pres["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
