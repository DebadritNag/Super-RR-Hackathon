"""Final comparison, selection and submitted rankings (Phase 8, chunk 5).

Stages (each calls ``begin_step`` first, so the predeclared criteria hash is verified before any
comparison result is read or written, and checks the protected files and the TEST lock):

* ``compare``  predeclared approach selection per role, window and definition sensitivity,
               ``p8_method_comparison`` / ``p8_method_selection`` / ``p8_final_sensitivity``.
* ``rank``     both Top 10 lists with status labels, candidate pools, explanations:
               ``p8_rankings`` / ``p8_explanations`` / ``p8_top10_status`` and the CSV/JSON files.
* ``report``   methodology comparison, research account, status banner and player explanations,
               written from the stored tables only.

``python scripts/phase8_final_ranking.py all`` runs every stage. The outputs are deterministic:
two runs produce byte-identical CSV and JSON files (``generated_at`` is the source-table stamp).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd

from app.phase8.approach_a import (
    eligible_players,
    final_intensity,
    overlap_row,
    player_counts,
    pressure_units,
    scope_counts,
)
from app.phase8.constants import OFFICIAL_DB, PHASE8_DB, REPORTS_DIR
from app.phase8.criteria import begin_step, load_criteria
from app.phase8.data import load_pre_test_deliveries
from app.phase8.explain import (
    no_estimate_reason,
    reason_below_floor,
    reasons_for_eligible,
    short_explanation,
)
from app.phase8.intensity import build_intensity
from app.phase8.lockguard import (
    assert_lock_state_unchanged,
    check_protected,
    load_prehash,
    lock_state,
)
from app.phase8.ranking import (
    METHODOLOGY_VERSION,
    build_list,
    check_output,
    combined_frame,
    csv_text,
    json_payload,
    to_output,
    write_text,
)
from app.phase8.selection import EXPLAINABILITY, select_approach
from app.phase8.sensitivity import consistency_rank, window_overlap
from app.phase8.splits import assert_pre_test
from app.phase8.status import banner, list_status, load_labels
from app.phase8.store import write_p8_table

A_CACHE = Path("d:/Data/.agents/tasks/_p8c2_cache")
ROLES = ("batter", "bowler")
CANDIDATES = ("P0", "P3", "P5", "P6")
SELECTED_N = 10
RAW_STANDOUT_MIN_BALLS = 60
RAW_STANDOUT_N = 10
INTERVAL_METHOD = {
    "A": "match-cluster bootstrap, 1000 draws, REML posterior, 95% percentile of the estimate",
    "C": "match-cluster bootstrap, 1000 draws, PRI refit per draw with weights fixed, 95% "
    "percentile of the draws without a floor refit",
}


def _read(table: str) -> pd.DataFrame:
    con = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        return con.execute(f"SELECT * FROM {table}").df()
    finally:
        con.close()


def _names() -> pd.Series:
    con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
    try:
        d = con.execute("SELECT player_id, player_name FROM players").df()
    finally:
        con.close()
    return d.drop_duplicates("player_id").set_index("player_id")["player_name"]


def _begin(stage: str) -> tuple[dict, dict]:
    check_protected()
    before = lock_state()
    info = begin_step(f"final_ranking_{stage}")
    return before, info


def _end(before: dict) -> None:
    assert_lock_state_unchanged(before)
    check_protected()


# ---------------------------------------------------------------------------------------------
# metrics per approach and role (approach-level only)
# ---------------------------------------------------------------------------------------------
def approach_metrics(role: str) -> tuple[dict[str, dict], pd.DataFrame]:
    """Selection metrics and the full comparison rows for one role."""
    rows, metrics = [], {}
    for tag, table in (("A", "p8_a_intensity_comparison"), ("B", "p8_b_intensity_comparison")):
        t = _read(table)
        r = t[(t["role"] == role) & (t["is_primary"].astype(bool))].iloc[0]
        metrics[tag] = {
            "sb": r["split_half_sb"], "sb_low": r["split_half_sb_low"], "oot": r["oot_spearman"],
            "oot_low": r["oot_low"], "concentration": r["top10_prob_ge_0_5"],
            "explainability": EXPLAINABILITY[tag], "n_split": r["split_half_players"],
            "n_oot": r["oot_players"],
        }  # fmt: skip
        rows.append(
            {"role": role, "approach": tag, "sb": r["split_half_sb"],
             "sb_low": r["split_half_sb_low"], "sb_high": r["split_half_sb_high"],
             "time_sb": r["time_sb"], "oot": r["oot_spearman"], "oot_low": r["oot_low"],
             "icc1": r["icc1"], "between_player_variance_at_floor": bool(r["floor"]),
             "mean_data_weight": r["mean_B"], "phase6_gate_passed": bool(r["mean_B"] >= 0.5),
             "share_players_weight_gt_0_5": r["share_B_gt_0_5"],
             "top10_prob_ge_0_5": r["top10_prob_ge_0_5"], "n_eligible": r["n_eligible"],
             "indicative_status": r["indicative_status"], "basis": "all PRE_TEST matches",
             "n_split": r["split_half_players"], "n_oot": r["oot_players"],
             "explainability": EXPLAINABILITY[tag]}
        )  # fmt: skip
    rel, stat = _read("p8_c_reliability"), _read("p8_c_status")
    rel, stat = rel[rel["role"] == role], stat[stat["role"] == role].iloc[0]
    par = rel[rel["metric"] == "parity_heldout"].iloc[0]
    tim = rel[rel["metric"] == "time_heldout"].iloc[0]
    oot = rel[rel["metric"] == "out_of_time_heldout"].iloc[0]
    metrics["C"] = {
        "sb": par["spearman_brown"], "sb_low": par["sb_low"], "oot": oot["r"],
        "oot_low": oot["sb_low"], "concentration": stat["top10_prob_ge_0_5"],
        "explainability": EXPLAINABILITY["C"], "n_split": par["n_players"],
        "n_oot": oot["n_players"],
    }  # fmt: skip
    rows.append(
        {"role": role, "approach": "C", "sb": par["spearman_brown"], "sb_low": par["sb_low"],
         "sb_high": par["sb_high"], "time_sb": tim["spearman_brown"], "oot": oot["r"],
         "oot_low": oot["sb_low"], "icc1": np.nan,
         "between_player_variance_at_floor": bool(stat["all_active_components_at_floor"]),
         "mean_data_weight": stat["mean_B_CONS"], "phase6_gate_passed": bool(stat["phase6_gate_passed"]),
         "share_players_weight_gt_0_5": np.nan, "top10_prob_ge_0_5": stat["top10_prob_ge_0_5"],
         "n_eligible": stat["n_eligible"], "indicative_status": stat["indicative_list_status"],
         "basis": "held-out matches only (weights fitted on FIT matches)",
         "n_split": par["n_players"], "n_oot": oot["n_players"],
         "explainability": EXPLAINABILITY["C"]}
    )  # fmt: skip
    return metrics, pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------
# stage compare
# ---------------------------------------------------------------------------------------------
def _family(name: str) -> str:
    if name.startswith("intensity_"):
        return "pressure definition"
    if name.startswith("scope_") or "format" in name:
        return "format (IPL, T20I, combined)"
    if name.startswith("eligibility_floor"):
        return "eligibility floor"
    if name.startswith("component_") or name.startswith("published_approach"):
        return "component or approach"
    if name.startswith("window"):
        return "calendar window"
    return "assumption (ordering, weights, innings)"


def stage_compare() -> dict[str, dict]:
    before, info = _begin("compare")
    crit = load_criteria()
    sel_rows, cmp_frames, decisions = [], [], {}
    for role in ROLES:
        metrics, cmp_df = approach_metrics(role)
        d = select_approach(metrics)
        decisions[role] = {**d, "metrics": metrics}
        cmp_frames.append(cmp_df.assign(chosen=cmp_df["approach"] == d["chosen"]))
        sel_rows.append(
            {"role": role, "approach_chosen": d["chosen"], "rule_path": d["path"],
             "lower_bound_path": d["lower_bound_path"], "point_estimate_path": d["point_estimate_path"],
             "paths_agree": d["paths_agree"], "list_status_cap": d["list_status_cap"] or "",
             "reason": d["reason"], "rule_text": crit["approach_selection"]["rule"],
             "metrics_json": json.dumps(metrics, sort_keys=True, default=float)}
        )  # fmt: skip
    write_p8_table(pd.concat(cmp_frames, ignore_index=True), "p8_method_comparison")
    write_p8_table(pd.DataFrame(sel_rows), "p8_method_selection")
    print(json.dumps({r: {k: v for k, v in d.items() if k != "metrics"} for r, d in decisions.items()},
                     indent=1, default=str), flush=True)  # fmt: skip

    # ----- sensitivity ------------------------------------------------------------------------
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    w, _ = build_intensity(df)
    cache = joblib.load(A_CACHE / "residuals.joblib")
    res = cache["res"]
    wi_p4, _i = final_intensity(w, "P4")
    ests = {"A": _read("p8_a_estimates"), "C": _read("p8_c_estimates")}
    stored = {"A": _read("p8_a_sensitivity"), "C": _read("p8_c_sensitivity")}
    boot = {"A": _read("p8_a_boot_check"), "C": _read("p8_c_boot_check")}
    e = crit["eligibility"]
    floors = {"TRAIN": int(e["min_matches"]), "VALIDATION": int(e["min_matches_2025_window"])}
    rows: list[dict] = []
    for role in ROLES:
        ap = decisions[role]["chosen"]
        if ap not in ests:
            continue
        comb = ests[ap][(ests[ap]["role"] == role) & (ests[ap]["scope"] == "COMBINED")]
        main_rank = comb.set_index("player_id")["rank"].astype(float)
        for _, r in stored[ap][stored[ap]["role"] == role].iterrows():
            rows.append({"role": role, "approach": ap, "family": _family(r["comparison"]),
                         "comparison": r["comparison"], "n_common": r["n_common"],
                         "spearman": r["spearman"], "top10_overlap": r["top10_overlap"],
                         "source": f"stored p8_{ap.lower()}_sensitivity", "note": ""})  # fmt: skip
        bc = boot[ap][boot[ap]["role"] == role]
        if "intensity" in bc.columns:
            bc = bc[bc["intensity"] == "P4"]
        for _, r in bc.iterrows():
            if ap == "A":
                note = (f"fixed-variance versus full-refit Top-10 inclusion: largest gap "
                        f"{r['max_abs_gap']:.3f} over {int(r['players_compared'])} players "
                        f"(within 0.05: {bool(r['fixed_variance_within_0_05'])}); the full refit is used")  # fmt: skip
            else:
                note = (f"{int(r['draws'])} draws, floor-draw share {r['floor_draw_share']}, "
                        f"weights fixed from {r['weights_fixed_from']}")  # fmt: skip
            rows.append({"role": role, "approach": ap, "family": "bootstrap", "comparison":
                         "bootstrap_method_check", "n_common": r.get("players", r.get("players_compared")),
                         "spearman": np.nan, "top10_overlap": np.nan, "source": "stored boot_check",
                         "note": note})  # fmt: skip
        units = pressure_units(df, role, wi_p4, res[f"a_{role}"])
        kind = "mean" if ap == "A" else "pos_share"
        for r in window_overlap(units, main_rank, kind, floors):
            rows.append({"role": role, "approach": ap, "family": "calendar window",
                         "comparison": r["comparison"], "n_common": r.get("n_common"),
                         "spearman": r.get("spearman", np.nan),
                         "top10_overlap": r.get("top10_overlap", np.nan),
                         "source": "recomputed from unit table",
                         "note": r.get("note", "") or
                         f"main Top 10 players estimable in window: {r.get('main_top10_estimable')}; "
                         f"statistic: {'precision-weighted mean residual' if kind == 'mean' else 'share of positive units'}; "
                         f"floors {floors}"})  # fmt: skip
        if ap == "C":
            for cand in CANDIDATES:
                wi = w[f"w_{cand}"]
                u = pressure_units(df, role, wi, res[f"a_{role}"])
                cnt = scope_counts(player_counts(df, role, wi, res[f"a_{role}"]), u, "COMBINED")
                ok = eligible_players(cnt, role, crit)
                pl = np.sort(ok[ok].index.to_numpy())
                other = consistency_rank(u, pl)
                if len(other) < 10:
                    rows.append({"role": role, "approach": ap, "family": "pressure definition",
                                 "comparison": f"intensity_{cand}", "n_common": len(other),
                                 "spearman": np.nan, "top10_overlap": np.nan,
                                 "source": "recomputed", "note": "NOT_ESTIMABLE"})  # fmt: skip
                    continue
                ov = overlap_row(main_rank, other)
                rows.append({"role": role, "approach": ap, "family": "pressure definition",
                             "comparison": f"intensity_{cand}", "n_common": ov["n_common"],
                             "spearman": ov["spearman"], "top10_overlap": ov["top10_overlap"],
                             "source": "recomputed (consistency ordering under that definition)",
                             "note": "eligibility from the A-unit floors"})  # fmt: skip
    sens = pd.DataFrame(rows)
    write_p8_table(sens, "p8_final_sensitivity")
    _end(before)
    return decisions


# ---------------------------------------------------------------------------------------------
# stage rank
# ---------------------------------------------------------------------------------------------
def _raw_standouts(df: pd.DataFrame, role: str) -> pd.DataFrame:
    """Top players on a raw death-overs statistic (no context adjustment), pooled over formats."""
    d = df[df["innings_phase"] == "death"]
    if role == "batter":
        d = d[d["den_counts_as_ball_faced"] == 1]
        g = d.groupby("striker_id").agg(balls=("den_counts_as_ball_faced", "sum"),
                                        runs=("out_batter_runs", "sum"))  # fmt: skip
        g = g[g["balls"] >= RAW_STANDOUT_MIN_BALLS]
        g["raw_stat"] = 100.0 * g["runs"] / g["balls"]
        g = g.sort_values("raw_stat", ascending=False)
        g["raw_label"] = "death-overs strike rate"
    else:
        d = d[d["den_legal_inc"] == 1]
        g = d.groupby("bowler_id").agg(balls=("den_legal_inc", "sum"),
                                       runs=("den_bowler_charged_runs", "sum"))  # fmt: skip
        g = g[g["balls"] >= RAW_STANDOUT_MIN_BALLS]
        g["raw_stat"] = 6.0 * g["runs"] / g["balls"]
        g = g.sort_values("raw_stat", ascending=True)
        g["raw_label"] = "death-overs economy"
    g.index.name = "player_id"
    return g.head(RAW_STANDOUT_N).reset_index()


def stage_rank() -> None:
    before, info = _begin("rank")
    crit = load_criteria()
    labels = load_labels()
    prehash = load_prehash()
    data_hash = ";".join(f"{Path(k).name}:{v}" for k, v in sorted(prehash.items()) if "duckdb" in k)
    selection = _read("p8_method_selection").set_index("role")
    cmp_all = _read("p8_method_comparison")
    ests = {
        "A": _read("p8_a_estimates"),
        "B": _read("p8_b_estimates"),
        "C": _read("p8_c_estimates"),
    }
    ineligible = _read("p8_a_ineligible")
    status_tab = {"A": _read("p8_a_status"), "C": _read("p8_c_status")}
    reml = _read("p8_a_reml")
    names = _names()
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    ranking_rows, expl_rows, status_rows = [], [], []
    for role in ROLES:
        ap = str(selection.loc[role, "approach_chosen"])
        if ap == "B":
            raise RuntimeError("Approach B ranking output is not implemented for submission")
        est = ests[ap]
        comb = combined_frame(est, ap, role)
        if ap == "C":
            a = ests["A"]
            aux = a[(a["role"] == role) & (a["scope"] == "COMBINED")].set_index("player_id")
            for c in ("obs_runs", "exp_runs", "obs_wicket", "exp_wicket", "pressure_perf_unshrunk",
                      "comp_runs", "comp_wicket", "comp_dot", "comp_boundary"):  # fmt: skip
                comb[c] = comb["player_id"].map(aux[c])
        ranks_by = {
            t: ests[t][(ests[t]["role"] == role) & (ests[t]["scope"] == "COMBINED")].set_index(
                "player_id"
            )["rank"]
            for t in ests
        }
        m = cmp_all[(cmp_all["role"] == role) & (cmp_all["approach"] == ap)].iloc[0]
        metrics = {"sb": m["sb"], "sb_low": m["sb_low"], "oot_low": m["oot_low"],
                   "n_split": m["n_split"], "n_oot": m["n_oot"]}  # fmt: skip
        floor_cell = bool(m["between_player_variance_at_floor"])
        n_elig = int(len(comb))
        ls = list_status(crit, metrics, floor_cell, n_elig)
        label = ls["status"]
        if selection.loc[role, "list_status_cap"] == "EXPLORATORY" and label in (
            "PROVISIONAL", "VALIDATED"
        ):  # fmt: skip
            label = "EXPLORATORY"
        st = status_tab[ap]
        st = st[st["role"] == role].iloc[0]
        definition_status = (
            "INTENSITY_DEFINITION_NOT_VALIDATED"
            if st["intensity_basis"] == "BEST_AVAILABLE_NOT_PASSING"
            else "INTENSITY_DEFINITION_PASSED"
        )
        basis = str(comb["rank_basis"].iloc[0])
        fmt_basis = (
            _read("p8_a_format_study" if ap == "A" else "p8_c_format_study")
            .pipe(lambda t: t[t["role"] == role])
            .iloc[0]["combination_basis"]
        )
        ctx = {"role": role, "interval_method": INTERVAL_METHOD[ap], "combination_basis": fmt_basis,
               "min_matches": crit["eligibility"]["min_matches"], "floor_cell": floor_cell,
               "definition_status": definition_status, "data_version_hash": data_hash,
               "criteria_sha256": info["sha256"], "generated_at": str(comb["generated_at"].iloc[0])}  # fmt: skip
        built = build_list(comb, approach=ap, role=role, list_label=label, validation_label=label,
                           rank_basis=basis, ranks_by_approach=ranks_by, context=ctx)  # fmt: skip
        stored_rank = comb.set_index("player_id")["rank"]
        calc = built["top"].set_index("player_id")["rank"]
        if not (stored_rank.loc[calc.index].astype(int) == calc.astype(int)).all():
            raise RuntimeError(f"{role}: recomputed order differs from the stored ranks")
        top = to_output(built["top"], built, short_explanation)
        pool = to_output(built["pool"], built, short_explanation)
        check_output(top, built["label"])
        reason = ls["reason"]
        bnr = banner(built["label"], role, basis, reason)
        header = {
            "role": role, "list_status": built["label"], "model_validation_status": label,
            "approach": ap, "primary_methodology": top["primary_methodology"].iloc[0] if len(top) else "",
            "rank_basis": basis, "banner": bnr, "status_definition": labels["labels"][built["label"]],
            "status_reason": reason, "n_eligible_players": n_elig, "list_length": int(len(top)),
            "shortfall": built["shortfall"], "intensity_definition": "P4 resource scarcity",
            "intensity_basis": st["intensity_basis"], "combination_basis": fmt_basis,
            "methodology_version": METHODOLOGY_VERSION, "criteria_sha256": info["sha256"],
            "data_version_hash": data_hash, "generated_at": ctx["generated_at"],
            "selection_reason": selection.loc[role, "reason"],
            "candidate_pool_note": "Ranks 11 to 20 (or all eligible players when fewer than ten) "
            "are a labelled candidate pool, not part of the submitted list.",
            "candidate_pool": json.loads(pool.to_json(orient="records", double_precision=10)),
        }  # fmt: skip
        stem = "pressure_batters_top10" if role == "batter" else "pressure_bowlers_top10"
        write_text(REPORTS_DIR / f"{stem}.csv", csv_text(top))
        write_text(REPORTS_DIR / f"{stem}.json", json_payload(top, header))
        print(role, ap, built["label"], len(top), flush=True)
        # tables --------------------------------------------------------------------------------
        extras = built["top"].set_index("player_id")
        pextras = built["pool"].set_index("player_id")
        for kind, out_df, ex in (("SELECTED", top, extras), ("CANDIDATE_POOL", pool, pextras)):
            o = out_df.copy()
            o.insert(0, "kind", kind)
            o["detail_json"] = [
                json.dumps(
                    {c: (None if pd.isna(ex.loc[pid].get(c)) else float(ex.loc[pid].get(c)))
                     for c in ("n_death", "n_middle", "n_powerplay", "n_innings1", "n_innings2",
                               "eff_n", "disp", "se", "sum_w", "balls", "hi_units", "n_units")
                     if c in ex.columns},
                    sort_keys=True)
                for pid in o["player_id"]
            ]  # fmt: skip
            ranking_rows.append(o)
        status_rows.append(
            {"role": role, "list_status": built["label"], "model_validation_status": label,
             "approach": ap, "rank_basis": basis, "n_eligible": n_elig, "list_length": int(len(top)),
             "shortfall": built["shortfall"] or "", "banner": bnr, "reason": reason,
             "combination_basis": fmt_basis, "intensity_basis": st["intensity_basis"],
             "between_player_variance_at_floor": floor_cell,
             "reml_tau2_combined": float(reml[(reml["role"] == role) & (reml["scope"] == "COMBINED")]["tau2"].iloc[0])}
        )  # fmt: skip
        # explanations: selected, near, raw standouts -------------------------------------------
        for _, r in top.iterrows():
            expl_rows.append({"role": role, "player_id": r["player_id"], "player_name": r["player_name"],
                              "kind": "SELECTED", "rank": r["rank"], "reason_code": "SELECTED",
                              "detail": r["short_explanation"]})  # fmt: skip
        tenth = float(built["top"]["score"].iloc[-1])
        sel_ids = set(top["player_id"])
        cmin = crit["eligibility"]["min_matches"]
        for _, r in built["pool"].iterrows():
            for code, det in reasons_for_eligible(r, tenth, cmin, False):
                expl_rows.append({"role": role, "player_id": r["player_id"],
                                  "player_name": r["player_name"], "kind": "NEAR_MISS",
                                  "rank": int(r["rank"]), "reason_code": code, "detail": det})  # fmt: skip
        raw = _raw_standouts(df, role)
        by_id = comb.set_index("player_id")
        inel = ineligible[ineligible["role"] == role].set_index("player_id")
        for _, g in raw.iterrows():
            pid = int(g["player_id"])
            nm = names.get(pid, str(pid))
            label_raw = f"{g['raw_label']} {g['raw_stat']:.1f} over {int(g['balls'])} balls"
            expl_rows.append({"role": role, "player_id": pid, "player_name": nm,
                              "kind": "RAW_STANDOUT", "rank": 0, "reason_code": "RAW_STAT",
                              "detail": label_raw})  # fmt: skip
            if pid in sel_ids:
                expl_rows.append({"role": role, "player_id": pid, "player_name": nm,
                                  "kind": "RAW_STANDOUT",
                                  "rank": int(top.set_index("player_id").loc[pid, "rank"]),
                                  "reason_code": "SELECTED",
                                  "detail": "also in the submitted Top 10"})  # fmt: skip
                continue
            if pid in by_id.index:
                row = by_id.loc[pid].copy()
                row["score"] = float(row["score"])
                reasons = reasons_for_eligible(row, tenth, cmin, True)
                rk = int(built["pool"].set_index("player_id")["rank"].get(pid, 0)) or int(
                    comb.set_index("player_id")["rank"].loc[pid]
                )
            elif pid in inel.index:
                reasons, rk = [reason_below_floor(inel.loc[pid], role)], 0
            else:
                reasons, rk = [no_estimate_reason()], 0
            for code, det in reasons:
                expl_rows.append({"role": role, "player_id": pid, "player_name": nm,
                                  "kind": "RAW_STANDOUT", "rank": rk, "reason_code": code,
                                  "detail": det})  # fmt: skip
    write_p8_table(pd.concat(ranking_rows, ignore_index=True), "p8_rankings")
    write_p8_table(pd.DataFrame(expl_rows), "p8_explanations")
    write_p8_table(pd.DataFrame(status_rows), "p8_top10_status")
    _end(before)


# ---------------------------------------------------------------------------------------------
def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("compare", "all"):
        stage_compare()
    if stage in ("rank", "all"):
        stage_rank()
    if stage in ("report", "all"):
        from app.phase8.report_final import write_all

        before, _ = _begin("report")
        write_all(REPORTS_DIR)
        _end(before)
    return 0


if __name__ == "__main__":
    sys.exit(main())
