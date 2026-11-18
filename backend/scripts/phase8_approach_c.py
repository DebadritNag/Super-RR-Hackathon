"""Approach C (Pressure Response Index) and the IPL/T20I combination study.

Stages (each calls ``begin_step`` first and checks the protected files and the TEST lock):

* ``estimate`` data-derived weights (FIT matches), REML components, PRI, seeded match bootstrap,
               held-out reliability, evidence classes, sensitivity, combination study:
               ``p8_c_*`` tables.
* ``report``   writes ``reports/phase8_approach_c_results.md`` from the stored tables only.

``python scripts/phase8_approach_c.py all`` runs every stage. Inputs are the caches written by the
Approach A and B scripts (expected-outcome residuals and the win-probability timeline).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import duckdb
import joblib
import numpy as np
import pandas as pd

from app.phase4.eligibility import GATE_B
from app.phase8.approach_a import (
    Boot,
    baseline_table,
    eligible_players,
    evidence_class,
    exposure_by_context,
    final_intensity,
    list_status,
    overlap_row,
    player_counts,
    pressure_units,
    scope_counts,
)
from app.phase8.approach_b import design_matrix, wpa_residuals
from app.phase8.approach_c import (
    COMPONENTS,
    bootstrap_pri,
    combination_decision,
    component_units,
    cross_format,
    derive_weights,
    fit_format_model,
    fit_match_split,
    format_means,
    pri_out_of_time,
    pri_point,
    pri_split_half,
    rank_of,
    rel_units,
)
from app.phase8.constants import (
    OFFICIAL_DB,
    REPORTS_DIR,
    active_db,
    cache_dir,
    translate_table,
)
from app.phase8.criteria import begin_step, load_criteria
from app.phase8.data import load_pre_test_deliveries
from app.phase8.intensity import build_intensity, intensity_from_wp
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state
from app.phase8.reliability import icc1, split_half
from app.phase8.reml import RemlError
from app.phase8.splits import assert_pre_test
from app.phase8.stability import point_ranking
from app.phase8.store import write_p8_table

A_CACHE = cache_dir("_p8c2_cache")
B_CACHE = cache_dir("_p8c3_cache")
BOOT_DRAWS = 1000
REL_BOOT = 500
SCOPES = ("COMBINED", "IPL", "T20I")


def _read(table: str) -> pd.DataFrame:
    con = duckdb.connect(str(active_db()), read_only=True)
    try:
        return con.execute(f"SELECT * FROM {translate_table(table)}").df()
    finally:
        con.close()


def _names() -> pd.Series:
    con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
    try:
        d = con.execute("SELECT player_id, player_name FROM players").df()
    finally:
        con.close()
    return d.drop_duplicates("player_id").set_index("player_id")["player_name"]


def _scope_units(cunits: dict[str, pd.DataFrame], scope: str) -> dict[str, pd.DataFrame]:
    if scope == "COMBINED":
        return cunits
    return {c: u[u["competition_type"] == scope] for c, u in cunits.items()}


def _eligible(
    df: pd.DataFrame, role: str, wi: pd.Series, res_a: pd.Series, res_b: pd.Series,
    ua: pd.DataFrame, ub: pd.DataFrame, crit: dict, scope: str, mult: float = 1.0,
) -> tuple[np.ndarray, pd.DataFrame]:  # fmt: skip
    """Players meeting every predeclared floor on both the A and the B units."""
    ca = scope_counts(player_counts(df, role, wi, res_a), ua, scope)
    cb = scope_counts(player_counts(df, role, wi, res_b), ub, scope)
    ok = eligible_players(ca, role, crit, mult) & eligible_players(cb, role, crit, mult).reindex(
        ca.index, fill_value=False
    )
    return np.sort(ok[ok].index.to_numpy()), ca


def _pri_rank(cunits, players, weights, centre) -> pd.Series:
    try:
        return rank_of(pri_point(cunits, players, weights, centre)["pri"])
    except RemlError:
        return pd.Series(dtype=float)


def stage_estimate() -> None:
    check_protected()
    before = lock_state()
    begin_step("approach_c_estimate")
    crit = load_criteria()
    e = crit["eligibility"]
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    w_all, _ = build_intensity(df)
    tl = joblib.load(B_CACHE / "timeline.joblib")
    w_all = w_all.join(intensity_from_wp(df, tl["wp_before"], tl["lev"]))
    c2 = joblib.load(A_CACHE / "residuals.joblib")
    res, yexp = c2["res"], c2["yexp"]
    sel = _read("p8_intensity_selection")
    primary = str(sel.loc[sel["primary"].astype(bool), "candidate"].iloc[0])
    primary_basis = str(sel.loc[sel["candidate"] == primary, "primary_basis"].iloc[0])
    wi, _iinfo = final_intensity(w_all, primary)
    names = _names()
    matches = df.drop_duplicates("match_id")[["match_id", "match_date", "period"]]
    split = fit_match_split(matches)
    fit_ids = set(split[split == "FIT"].index.tolist())
    held_ids = set(split[split == "HELD"].index.tolist())
    per = matches.set_index("match_id")["period"]
    early_ids = {m for m in held_ids if per[m] == "TRAIN"}
    late_ids = {m for m in held_ids if per[m] == "VALIDATION"}
    boot = Boot(df, BOOT_DRAWS)
    wa = _read("p8_a_estimates")
    wb = _read("p8_b_estimates")
    tabs: dict[str, list[pd.DataFrame]] = {k: [] for k in (
        "weights", "corr", "creml", "crel", "est", "sens", "fmt", "hier", "status", "bootchk",
        "comprel", "split",
    )}  # fmt: skip
    for role in ("batter", "bowler"):
        res_a = res[f"a_{role}"]
        x = design_matrix(df, tl["lev"], yexp[f"{role}_runs"]["expected"])
        credit = tl["wpa"]["striker_wpa" if role == "batter" else "bowler_wpa"]
        res_b, _coef = wpa_residuals(df, credit, x)
        ua, ub = pressure_units(df, role, wi, res_a), pressure_units(df, role, wi, res_b)
        base = baseline_table(df, role, wi, res_a)
        cunits = component_units(ua, ub)
        players, counts_a = _eligible(df, role, wi, res_a, res_b, ua, ub, crit, "COMBINED")
        print(role, "eligible (A and B floors):", len(players), flush=True)
        tabs["split"].append(pd.DataFrame([{"role": role, "fit_matches": len(fit_ids),
                                            "held_matches": len(held_ids),
                                            "held_train": len(early_ids), "held_validation": len(late_ids),
                                            "n_players": len(players)}]))  # fmt: skip
        # ---- weights from FIT matches only -------------------------------------------------
        dw = derive_weights(cunits, players, fit_ids)
        weights = dw["weights"]
        tabs["weights"].append(dw["table"].assign(
            role=role, pca_used=dw["combine"]["pca"], max_abs_corr=dw["combine"]["max_abs_corr"],
            defined=dw["defined"]))  # fmt: skip
        cr = dw["corr"].stack().rename("spearman").reset_index()
        cr.columns = ["component_a", "component_b", "spearman"]
        tabs["corr"].append(cr.assign(role=role))
        # ---- point estimates (combined) ----------------------------------------------------
        pt = pri_point(cunits, players, weights, centre=True)
        comps, sds = pt["comps"], pt["sds"]
        for c in COMPONENTS:
            f = comps[c]["fit"]
            tabs["creml"].append(pd.DataFrame([{
                "role": role, "component": c, "scope": "COMBINED", "mu": f["mu"], "tau2": f["tau2"],
                "sigma2": f["sigma2"], "floor": f["floor"], "label": f["label"], "mean_B": f["mean_B"],
                "share_B_gt_0_5": float((f["players"]["B"] > 0.5).mean()), "gate_mean_B_ge_0_5":
                bool(f["mean_B"] >= GATE_B), "n_players": f["n_players"], "n_units": f["n_units"],
                "level_sd": sds[c]}]))  # fmt: skip
            ic = icc1(rel_units(comps[c]["units"]))
            pbar = float(comps[c]["fit"]["players"]["P"].mean())
            tabs["comprel"].append(pd.DataFrame([{
                "role": role, "component": c, "icc1": ic["icc"], "icc_players": ic["n_players"],
                "between_over_noise": (f["tau2"] / (f["sigma2"] / pbar)) if pbar > 0 else np.nan}]))  # fmt: skip
        defined = bool(dw["defined"]) and bool(pt["active"]) and bool(pt["pri"].notna().any())
        status_row = {"role": role, "intensity": primary, "intensity_basis": primary_basis,
                      "pri_defined": defined, "n_eligible": int(len(players)),
                      "pca_used": dw["combine"]["pca"],
        "weights": json.dumps({c: round(v, 4) for c, v in weights.items()}),
        "centre": "cohort mean of each component (0 = typical eligible player)"}  # fmt: skip
        if not defined:
            status_row.update({"indicative_list_status": "NOT_DEFINED",
                               "reason": "every component has no signal on the FIT matches (PRI not produced)"})  # fmt: skip
            tabs["status"].append(pd.DataFrame([status_row]))
            continue
        pri = pt["pri"]
        # ---- bootstrap (full REML refit per draw) -------------------------------------------
        bs = bootstrap_pri(comps, players, boot, weights, sds)
        stab = bs["stability"]
        tabs["bootchk"].append(pd.DataFrame([{
            "role": role, "draws": boot.n_draws, "players": int(len(players)),
            "mean_draws_present": float(stab["draws_present"].mean()),
            "weights_fixed_from": "FIT matches (TRAIN odd parity)",
                    "interval_draws": int(stab["interval_draws"].iloc[0]),
                    "floor_draw_share": json.dumps(bs["floor_draw_share"])}]))  # fmt: skip
        # ---- held-out reliability ------------------------------------------------------------
        par = pri_split_half(cunits, players, held_ids, weights, sds, "parity", 2, REL_BOOT)
        tim = pri_split_half(cunits, players, held_ids, weights, sds, "time", 2, REL_BOOT)
        oot = pri_out_of_time(cunits, players, early_ids, late_ids, weights, sds,
                              max(e["min_matches"] // 2, 2), e["min_matches_2025_window"],
                              e["min_players_out_of_time"])  # fmt: skip
        for metric, blk in (("parity_heldout", par), ("time_heldout", tim)):
            tabs["crel"].append(pd.DataFrame([{"role": role, "metric": metric,
                                               "n_players": blk["n_players"], "r": blk["r"],
                                               "spearman_brown": blk["spearman_brown"],
                                               "sb_low": blk.get("sb_low"), "sb_high": blk.get("sb_high"),
                                               "boot_draws": blk.get("boot_draws")}]))  # fmt: skip
        tabs["crel"].append(pd.DataFrame([{"role": role, "metric": "out_of_time_heldout",
                                           "n_players": oot["n_players"], "r": oot["spearman"],
                                           "spearman_brown": np.nan, "sb_low": oot.get("low"),
                                           "sb_high": oot.get("high"), "boot_draws": 500}]))  # fmt: skip
        all_floor = all(comps[c]["fit"]["floor"] for c in pt["active"])
        st = list_status(crit, par.get("spearman_brown"), par.get("sb_low"), oot.get("low"),
                         all_floor, len(players), par["n_players"], oot["n_players"])  # fmt: skip
        mean_b = {c: comps[c]["fit"]["mean_B"] for c in COMPONENTS}
        status_row.update({"indicative_list_status": st["status"], "reason": st["reason"],
                           "split_half_sb": par["spearman_brown"], "split_half_sb_low": par.get("sb_low"),
                           "time_sb": tim["spearman_brown"], "oot_spearman": oot["spearman"],
                           "oot_low": oot.get("low"), "all_active_components_at_floor": all_floor,
                           "top10_prob_ge_0_5": int((stab["top_k_prob"] >= 0.5).sum()),
                           "median_rank_interval_width": float((stab["rank_high"] - stab["rank_low"]).median()),
                           "mean_B_A": mean_b["A"], "mean_B_B": mean_b["B"], "mean_B_CONS": mean_b["CONS"],
                           "phase6_gate_threshold": GATE_B,
                           "phase6_gate_passed": bool(max(mean_b[c] for c in pt["active"]) >= GATE_B)})  # fmt: skip
        tabs["status"].append(pd.DataFrame([status_row]))
        # ---- scopes: IPL-only and T20I-only PRI (same fixed weights) ---------------------
        scope_pri, scope_pt = {"COMBINED": pri}, {"COMBINED": pt}
        for sc in ("IPL", "T20I"):
            pl_sc, _ = _eligible(df, role, wi, res_a, res_b, ua, ub, crit, sc)
            if len(pl_sc) < 10:
                continue
            try:
                scope_pt[sc] = pri_point(_scope_units(cunits, sc), pl_sc, weights, centre=False)
                scope_pri[sc] = scope_pt[sc]["pri"]
            except RemlError:
                continue
        # ---- combination study ------------------------------------------------------------
        half_min = max(int(e["min_matches"] // 2), 2)
        fm = {c: format_means(cunits[c], half_min) for c in COMPONENTS}
        common = fm["A"].index
        for c in pt["active"]:
            common = common.intersection(fm[c].index)
        rel_f = {}
        for f in ("IPL", "T20I"):
            try:
                blk = split_half(
                    rel_units(cunits["A"][cunits["A"]["competition_type"] == f]),
                    "parity",
                    max(half_min // 2, 2),
                )
                rel_f[f] = blk["spearman_brown"]
            except (ValueError, KeyError):
                rel_f[f] = float("nan")
        pf = pd.DataFrame(index=common)
        pf["ybar_ipl"] = sum(
            weights[c] * fm[c].loc[common, "ybar_ipl"] / sds[c] for c in pt["active"]
        )
        pf["ybar_t20i"] = sum(
            weights[c] * fm[c].loc[common, "ybar_t20i"] / sds[c] for c in pt["active"]
        )
        first = pt["active"][0]
        pf["P_ipl"], pf["P_t20i"] = fm[first].loc[common, "P_ipl"], fm[first].loc[common, "P_t20i"]
        cf = cross_format(pf, rel_f["IPL"], rel_f["T20I"])
        ok, basis = combination_decision(cf["spearman_low"], cf["players_both_formats"],
                                         e["min_players_split_half"])  # fmt: skip
        tabs["fmt"].append(pd.DataFrame([{"role": role, "series": "PRI", **cf,
                                          "rel_ipl": rel_f["IPL"], "rel_t20i": rel_f["T20I"],
                                          "combination_supported": ok, "combination_basis": basis}]))  # fmt: skip
        for c in COMPONENTS:
            comm = fm[c].index
            cc = cross_format(fm[c], None, None)
            tabs["fmt"].append(pd.DataFrame([{"role": role, "series": c, **cc, "rel_ipl": np.nan,
                                              "rel_t20i": np.nan, "combination_supported":
                                              combination_decision(cc["spearman_low"], len(comm),
                                                                   e["min_players_split_half"])[0],
                                              "combination_basis": ""}]))  # fmt: skip
        hier_u: dict[str, pd.Series] = {}
        hier_rows = []
        hplayers = {}
        for c in COMPONENTS:
            raw_units = cunits[c]
            try:
                hf = fit_format_model(raw_units, players)
            except RemlError as exc:
                hier_rows.append({"role": role, "component": c, "status": f"NOT_ESTIMABLE: {exc}"})
                continue
            hplayers[c] = hf["players"]
            hier_u[c] = hf["players"]["u_hat"] if hf["tau_u2"] > 0 else None
            hier_rows.append({"role": role, "component": c, "status": "ESTIMATED",
                              **{k: v for k, v in hf.items() if k != "players"}})  # fmt: skip
        tabs["hier"].append(pd.DataFrame(hier_rows))
        pri_hier = None
        use = [c for c in pt["active"] if hier_u.get(c) is not None]
        if use and len(use) == len(pt["active"]):
            zc = {c: hier_u[c] / hier_u[c].std(ddof=1) for c in use}
            pri_hier = sum(weights[c] * zc[c] for c in use)
        # ---- sensitivity ----------------------------------------------------------------------
        rk = rank_of(pri)
        sens = []

        def add(name: str, other: pd.Series, extra: dict | None = None) -> None:
            if len(other):
                sens.append(
                    {"role": role, "comparison": name, **overlap_row(rk, other), **(extra or {})}
                )

        pub_a = wa[(wa["role"] == role) & (wa["scope"] == "COMBINED")].set_index("player_id")[
            "rank"
        ]
        pub_b = wb[(wb["role"] == role) & (wb["scope"] == "COMBINED")].set_index("player_id")[
            "rank"
        ]
        add("published_approach_A_rank", pub_a)
        add("published_approach_B_rank", pub_b)
        for c in COMPONENTS:
            add(
                f"component_{c}_only",
                _pri_rank(cunits, players, {k: float(k == c) for k in COMPONENTS}, True),
            )
        add(
            "equal_weights_not_data_derived",
            _pri_rank(cunits, players, dict.fromkeys(COMPONENTS, 1 / 3), True),
        )
        for sc, p_sc in scope_pri.items():
            if sc != "COMBINED":
                add(f"scope_{sc}_only", rank_of(p_sc))
        for mult in e["sensitivity_multipliers"]:
            pm, _ = _eligible(df, role, wi, res_a, res_b, ua, ub, crit, "COMBINED", mult)
            if len(pm) >= 10:
                add(f"eligibility_floor_x{mult}", _pri_rank(cunits, pm, weights, True),
                    {"n_eligible": int(len(pm))})  # fmt: skip
        unsh = sum(
            weights[c] * ((comps[c]["unshrunk"] - comps[c]["centre"]) / sds[c])
            for c in pt["active"]
        )
        add("unshrunk_ordering", point_ranking(unsh))
        if pri_hier is not None:
            add("hierarchical_format_common_effect", point_ranking(pri_hier))
        inn2 = {c: u[u["innings"] == 2] for c, u in cunits.items()}
        pl2 = np.sort(np.intersect1d(players, inn2["A"]["player_id"].unique()))
        add("innings2_units_only", _pri_rank(inn2, pl2, weights, True))
        tabs["sens"].append(pd.DataFrame(sens))
        # ---- player table ---------------------------------------------------------------------
        bl = base.groupby("player_id").agg(sr=("sr", "sum"), n_base=("n", "sum"))
        ex = exposure_by_context(df, role, wi, players)
        for sc, p_sc in scope_pri.items():
            p_t = scope_pt[sc]
            lv = p_t["levels"]
            t = pd.DataFrame(
                {"player_id": lv.index.to_numpy(), "pri": p_sc.reindex(lv.index).to_numpy()}
            )
            t["rank"] = rank_of(p_sc.reindex(lv.index)).to_numpy()
            for c in COMPONENTS:
                t[f"level_{c}"] = lv[c].to_numpy()
                t[f"z_{c}"] = ((lv[c] - p_t["comps"][c]["centre"]) / p_t["sds"][c]).to_numpy()
                t[f"shrink_B_{c}"] = p_t["comps"][c]["B"].reindex(lv.index).to_numpy()
            t["sample_reliability"] = t[[f"shrink_B_{c}" for c in pt["active"]]].mean(axis=1)
            t["pressure_unshrunk_A"] = p_t["comps"]["A"]["unshrunk"].reindex(lv.index).to_numpy()
            au = p_t["comps"]["A"]["units"]
            g = au.groupby("player_id")
            t = t.merge(pd.DataFrame({
                "pos_share": g["y"].apply(lambda s: float((s > 0).mean())),
                "disp": g["y"].std(ddof=1).fillna(0.0), "n_units": g.size(),
                "mean_unit_intensity": g["mean_intensity"].mean()}).reset_index(), on="player_id", how="left")  # fmt: skip
            cnt = scope_counts(player_counts(df, role, wi, res_a), ua, sc).reset_index()
            cnt = cnt.rename(columns={cnt.columns[0]: "player_id"})
            t = t.merge(cnt, on="player_id", how="left")
            t = t.merge(bl.reset_index(), on="player_id", how="left")
            t["normal_baseline"] = t["sr"] / t["n_base"]
            t["pressure_delta"] = np.where(
                t["n_base"] > 0, t["pressure_unshrunk_A"] - t["normal_baseline"], np.nan
            )
            t["role"], t["scope"], t["intensity"] = role, sc, primary
            t["player_name"] = t["player_id"].map(names)
            t["rank_basis"] = (
                "PRI_REML_POSTERIOR_COMPONENTS" if not all_floor else "PRI_UNSHRUNK_FLOOR"
            )
            if sc == "COMBINED":
                t = t.merge(stab, on="player_id", how="left")
                t = t.rename(columns={"est_low": "pri_low", "est_high": "pri_high"})
                t["ci_low"] = t["pri_low"]
                t = t.merge(ex, on="player_id", how="left")
                t["evidence_class"] = evidence_class(
                    t.assign(eligible=True, estimate=t["pri"]), e["min_matches"]).to_numpy()  # fmt: skip
                for f, col in (("IPL", "matches_ipl"), ("T20I", "matches_t20i")):
                    t[col] = t["player_id"].map(
                        scope_counts(player_counts(df, role, wi, res_a), ua, f)["n_matches"]
                    )
                pa = cunits["A"][cunits["A"]["player_id"].isin(players)]
                pshare = pa.groupby(["player_id", "competition_type"])["prec"].sum().unstack()
                t["ipl_precision_share"] = t["player_id"].map(
                    (pshare.get("IPL", 0) / (pshare.get("IPL", 0) + pshare.get("T20I", 0))).reindex(
                        pshare.index))  # fmt: skip
                for f in ("IPL", "T20I"):
                    if f in scope_pri:
                        t[f"pri_{f.lower()}"] = t["player_id"].map(scope_pri[f])
                if pri_hier is not None:
                    t["pri_hier_common"] = t["player_id"].map(pri_hier)
                    hp = hplayers["A"]
                    t["format_w_ipl_A"] = t["player_id"].map(hp["w_ipl"])
                    t["format_w_t20i_A"] = t["player_id"].map(hp["w_t20i"])
                t["combination_basis"] = basis
            tabs["est"].append(t)
    est = pd.concat(tabs["est"], ignore_index=True)
    est["status"] = "EXPERIMENTAL_NOT_VALIDATED"
    est["generated_at"] = datetime.now(UTC).isoformat()
    write_p8_table(est, "p8_c_estimates")
    for key, name in (("weights", "p8_c_weights"), ("corr", "p8_c_component_corr"),
                      ("creml", "p8_c_component_reml"), ("crel", "p8_c_reliability"),
                      ("comprel", "p8_c_component_reliability"), ("sens", "p8_c_sensitivity"),
                      ("fmt", "p8_c_format_study"), ("hier", "p8_c_format_hierarchy"),
                      ("status", "p8_c_status"), ("bootchk", "p8_c_boot_check"),
                      ("split", "p8_c_fit_split")):  # fmt: skip
        if tabs[key]:
            write_p8_table(pd.concat(tabs[key], ignore_index=True), name)
    print(
        json.dumps(pd.concat(tabs["status"]).to_dict("records"), indent=1, default=str), flush=True
    )
    assert_lock_state_unchanged(before)
    check_protected()


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("estimate", "all"):
        stage_estimate()
    if stage in ("report", "all"):
        from app.phase8.report_c import write_report

        write_report(REPORTS_DIR / "phase8_approach_c_results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
