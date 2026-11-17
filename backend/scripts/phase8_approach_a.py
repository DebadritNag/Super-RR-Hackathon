"""Approach A (context-adjusted performance) for batters and bowlers, with the intensity comparison.

Stages (run in order; each calls ``begin_step`` first and checks the protected files and TEST lock):

* ``models``   expected-outcome models, OOF residuals, artefacts, ``p8_a_model_*`` tables.
* ``tests``    predeclared intensity validity tests, ``p8_intensity_tests`` / ``p8_intensity_selection``.
* ``estimate`` pressure units, REML, reliability, bootstrap, sensitivity, ``p8_a_*`` tables.
* ``report``   writes ``reports/phase8_approach_a_results.md`` from the stored tables only.

``python scripts/phase8_approach_a.py all`` runs every stage.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd

from app.phase8.approach_a import (
    Boot,
    component_means,
    component_residuals,
    delta_rank,
    evidence_class,
    exposure_by_context,
    final_intensity,
    list_status,
    observed_expected,
    overlap_row,
    player_bootstrap_spearman,
    player_counts,
    run_cell,
)
from app.phase8.constants import OFFICIAL_DB, PHASE8_DB, REPORTS_DIR, SEED
from app.phase8.criteria import begin_step, load_criteria
from app.phase8.data import load_pre_test_deliveries
from app.phase8.expected import SPECS, category_codes, prepare_features, save_artifact, score_target
from app.phase8.intensity import build_intensity
from app.phase8.intensity_validity import run_validity_tests, summarise_candidates
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state
from app.phase8.splits import assert_pre_test, check_match_partition
from app.phase8.stability import point_ranking
from app.phase8.store import write_p8_table

CACHE = Path("d:/Data/.agents/tasks/_p8c2_cache")
CANDIDATES = ("P0", "P3", "P4", "P5", "P6")
BOOT_DRAWS = 1000


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
    info = begin_step(f"approach_a_{stage}")
    return before, info


def _end(before: dict) -> None:
    assert_lock_state_unchanged(before)
    check_protected()


def stage_models() -> None:
    before, info = _begin("models")
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    part = check_match_partition(df)
    codes = category_codes(df)
    x = prepare_features(df, codes)
    results, metric_rows, grid_rows, decile_rows = {}, [], [], []
    for spec in SPECS:
        r = score_target(df, x, spec)
        results[(spec.role, spec.name)] = r
        m = dict(r["metrics"])
        for g in m.pop("grid"):
            grid_rows.append({"role": spec.role, "target": spec.name, **g})
        for d in m.pop("deciles", []):
            decile_rows.append({"role": spec.role, "target": spec.name, **d})
        metric_rows.append(m)
        meta = {
            "version": "p8_expected_v1", "trained_on": "TRAIN", "seed": SEED,
            "train_matches": int(df.loc[df["period"] == "TRAIN", "match_id"].nunique()),
            "criteria_sha256": info["sha256"], "timestamp": datetime.now(UTC).isoformat(),
        }  # fmt: skip
        save_artifact(r, spec, codes, meta)
        print(spec.role, spec.name, r["chosen"], f"gain {m['gain_vs_const_pct']:.2f}%", flush=True)
    write_p8_table(pd.DataFrame(metric_rows), "p8_a_model_metrics")
    write_p8_table(pd.DataFrame(grid_rows), "p8_a_model_grid")
    write_p8_table(pd.DataFrame(decile_rows), "p8_a_model_deciles")
    res, sds = component_residuals(df, results)
    write_p8_table(
        pd.DataFrame([{"component": k, "train_sd": v} for k, v in sds.items()]),
        "p8_a_component_defs",
    )
    CACHE.mkdir(parents=True, exist_ok=True)
    keep = {f"{k[0]}_{k[1]}": {"y": v["y"], "expected": v["expected"]} for k, v in results.items()}
    joblib.dump(
        {"res": res, "yexp": keep, "sds": sds, "partition": part}, CACHE / "residuals.joblib"
    )
    _end(before)


def _load_cache() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    c = joblib.load(CACHE / "residuals.joblib")
    return c["res"], c["yexp"], c["sds"], c["partition"]


def stage_tests() -> None:
    before, _ = _begin("tests")
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    w, _info = build_intensity(df)
    tests = run_validity_tests(df, w)
    summary = summarise_candidates(tests)
    write_p8_table(tests.astype({"test_a": "object", "test_b": "object"}), "p8_intensity_tests")
    write_p8_table(summary, "p8_intensity_selection")
    print(summary.drop(columns=["test_d"]).to_string(), flush=True)
    _end(before)


def _intensity_for(w: pd.DataFrame, cand: str, primary: str) -> tuple[pd.Series, dict]:
    if cand == primary:
        return final_intensity(w, cand)
    return w[f"w_{cand}"], {"primary": cand, "innings1_fallback": None}


def stage_estimate() -> None:
    before, info = _begin("estimate")
    crit = load_criteria()
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    w, _ = build_intensity(df)
    res, yexp, sds, _part = _load_cache()
    sel = _read("p8_intensity_selection")
    primary = str(sel.loc[sel["primary"].astype(bool), "candidate"].iloc[0])
    primary_basis = str(sel.loc[sel["candidate"] == primary, "primary_basis"].iloc[0])
    names = _names()
    boot = Boot(df, BOOT_DRAWS)
    e = crit["eligibility"]
    est_rows, rel_rows, cmp_rows, reml_rows, sens_rows, inel_rows, expo_rows = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    boot_checks, fmt_rows, status_rows = [], [], []
    cells: dict[tuple[str, str], dict] = {}
    for role in ("batter", "bowler"):
        resid = res[f"a_{role}"]
        for cand in CANDIDATES:
            wi, iinfo = _intensity_for(w, cand, primary)
            deliv = player_counts(df, role, wi, resid)
            cell = run_cell(df, deliv, role, wi, resid, crit, boot, 1.0, True, 1000)
            cells[(role, cand)] = cell
            comb = cell["scopes"]["COMBINED"]
            row = {"role": role, "intensity": cand, "is_primary": cand == primary,
                   "reference_only": cand == "P0", "innings1_fallback": iinfo["innings1_fallback"] or "",
                   "n_eligible": int(len(comb["players"]))}  # fmt: skip
            for sc, ent in cell["scopes"].items():
                if "fit" in ent:
                    f = ent["fit"]
                    reml_rows.append({"role": role, "intensity": cand, "scope": sc, "mu": f["mu"],
                                      "tau2": f["tau2"], "sigma2": f["sigma2"], "lambda": f["lambda"],
                                      "floor": f["floor"], "label": f["label"], "mean_B": f["mean_B"],
                                      "share_B_gt_0_5": float((f["players"]["B"] > 0.5).mean()),
                                      "n_players": f["n_players"], "n_units": f["n_units"]})  # fmt: skip
            if "reliability" in comb:
                rb = comb["reliability"]
                par, tim, ic, oot = rb["parity"], rb["time"], rb["icc"], rb["oot"]
                st = list_status(crit, par.get("spearman_brown"), par.get("sb_low"), oot.get("low"),
                                 comb["fit"]["floor"], len(comb["players"]), par.get("n_players", 0),
                                 oot.get("n_players", 0))  # fmt: skip
                stab = comb["boot"]["stability"]
                boot_checks.append({"role": role, "intensity": cand, **comb["boot"]["check"]})
                fp = comb["fit"]["players"]
                vol = float(fp["basis"].rank().corr(fp["P"].rank()))
                row.update({
                    "volume_spearman": vol, "volume_bias_flag": bool(vol > 0.3),
                    "boot_method": "FULL_REFIT",
                    "split_half_r": par["r"], "split_half_sb": par["spearman_brown"],
                    "split_half_sb_low": par.get("sb_low"), "split_half_sb_high": par.get("sb_high"),
                    "split_half_players": par["n_players"], "time_sb": tim["spearman_brown"],
                    "time_sb_low": tim.get("sb_low"), "time_sb_high": tim.get("sb_high"),
                    "ipl_parity_sb": rb["per_format"]["IPL"].get("spearman_brown"),
                    "t20i_parity_sb": rb["per_format"]["T20I"].get("spearman_brown"),
                    "icc1": ic["icc"], "icc_players": ic["n_players"],
                    "oot_status": oot["status"], "oot_spearman": oot["spearman"], "oot_low": oot.get("low"),
                    "oot_high": oot.get("high"), "oot_players": oot["n_players"],
                    "floor": comb["fit"]["floor"], "tau2": comb["fit"]["tau2"], "sigma2": comb["fit"]["sigma2"],
                    "mean_B": comb["fit"]["mean_B"],
                    "share_B_gt_0_5": float((comb["fit"]["players"]["B"] > 0.5).mean()),
                    "top10_prob_ge_0_5": int((stab["top_k_prob"] >= 0.5).sum()),
                    "median_rank_interval_width": float((stab["rank_high"] - stab["rank_low"]).median()),
                    "indicative_status": st["status"], "status_reason": st["reason"],
                })  # fmt: skip
                rel_rows.append(
                    {
                        "role": role,
                        "intensity": cand,
                        "metric": "parity",
                        **{k: v for k, v in par.items() if k != "mode"},
                    }
                )
                rel_rows.append(
                    {
                        "role": role,
                        "intensity": cand,
                        "metric": "time",
                        **{k: v for k, v in tim.items() if k != "mode"},
                    }
                )
            cmp_rows.append(row)

        # primary cell: estimates, evidence, sensitivity -------------------------------------
        cell = cells[(role, primary)]
        wi, iinfo = _intensity_for(w, primary, primary)
        base = cell["baseline"]
        comb = cell["scopes"]["COMBINED"]
        if "fit" not in comb:
            status_rows.append({"role": role, "status": comb.get("status", "NOT_ESTIMABLE")})
            continue
        players = comb["players"]
        comp = component_means(df, role, wi, res, players)
        oe = observed_expected(
            df, role, wi, {(k.split("_")[0], k.split("_")[1]): v for k, v in yexp.items()}, players
        )
        expo = exposure_by_context(df, role, wi, players)
        expo_rows.append(expo.assign(role=role, intensity=primary))
        bl = base.groupby("player_id").agg(sr=("sr", "sum"), n_base=("n", "sum"))
        for sc in ("COMBINED", "IPL", "T20I"):
            ent = cell["scopes"][sc]
            if "fit" not in ent:
                continue
            ps = ent["fit"]["players"].copy()
            eu = ent["units"]
            ps.index.name = "player_id"
            ps = ps.reset_index()
            raw_mean = float(np.average(eu["y"], weights=eu["prec"]))
            shift = raw_mean if sc == "COMBINED" else 0.0
            g = eu.groupby("player_id")
            ps = ps.merge(
                pd.DataFrame({"pos_share": g["y"].apply(lambda s: float((s > 0).mean())),
                              "disp": g["y"].std(ddof=1).fillna(0.0),
                              "n_units": g.size(), "mean_unit_intensity": g["mean_intensity"].mean()}).reset_index(),
                on="player_id")  # fmt: skip
            c = ent["counts"].reset_index().rename(columns={"index": "player_id"})
            ps = ps.merge(c, on="player_id", how="left", suffixes=("", "_c"))
            ps["estimate"] = ps["basis"] + shift
            ps["rank"] = ps["player_id"].map(ent["rank"])
            ps["rank_basis"] = "REML_POSTERIOR" if ent["use_posterior"] else "UNSHRUNK_FLOOR"
            ps["role"], ps["intensity"], ps["scope"] = role, primary, sc
            ps["player_name"] = ps["player_id"].map(names)
            ps["pressure_perf_unshrunk"] = ps["ybar"] + shift
            ps = ps.merge(bl.reset_index(), on="player_id", how="left")
            ps["normal_baseline"] = ps["sr"] / ps["n_base"]
            ps["pressure_delta"] = np.where(
                ps["n_base"] > 0, ps["pressure_perf_unshrunk"] - ps["normal_baseline"], np.nan
            )
            if sc == "COMBINED":
                stab = comb["boot"]["stability"]
                ps = ps.merge(stab, on="player_id", how="left")
                for k in ("est_low", "est_high", "pressure_low", "pressure_high"):
                    ps[k] = ps[k] + shift
                ps["ci_low"] = ps["est_low"] - shift
                ps = ps.merge(comp, on="player_id", how="left").merge(
                    oe, on="player_id", how="left"
                )
                ps = ps.merge(expo, on="player_id", how="left")
                ps["evidence_class"] = evidence_class(
                    ps.assign(eligible=True, estimate=ps["basis"]), e["min_matches"]
                ).to_numpy()
                for f in ("IPL", "T20I"):
                    ff = (
                        cell["scopes"][f]["counts"]["n_matches"]
                        if "counts" in cell["scopes"][f]
                        else pd.Series(dtype=float)
                    )
                    ps[f"matches_{f.lower()}"] = ps["player_id"].map(ff)
            est_rows.append(ps)
        # ineligible players with counts, for exclusion reasons (primary, combined)
        cn = comb["counts"]
        elig = comb["eligible"]
        bad = cn[~elig].copy()
        bad["failed_rules"] = np.where(bad["n_matches"] < e["min_matches"], "matches;", "")
        bad["failed_rules"] += np.where(bad["eff_n"] < e["min_effective_n"], "effective_n;", "")
        bad["failed_rules"] += np.where(
            bad["balls"] < e["min_balls_faced" if role == "batter" else "min_balls_bowled"],
            "balls;",
            "",
        )
        bad["failed_rules"] += np.where(
            bad["hi_units"] < e["min_high_intensity_units"], "high_intensity_units;", ""
        )
        bad = bad.reset_index().rename(columns={"index": "player_id"})
        bad["player_name"] = bad["player_id"].map(names)
        inel_rows.append(bad.assign(role=role, intensity=primary))

        # sensitivity -------------------------------------------------------------------------
        rk = comb["rank"]
        for cand in CANDIDATES:
            if cand == primary:
                continue
            other = cells[(role, cand)]["scopes"]["COMBINED"]
            if "rank" in other:
                sens_rows.append(
                    {
                        "role": role,
                        "comparison": f"intensity_{cand}",
                        **overlap_row(rk, other["rank"]),
                    }
                )
        for sc in ("IPL", "T20I"):
            ent = cell["scopes"][sc]
            if "rank" in ent:
                sens_rows.append(
                    {"role": role, "comparison": f"scope_{sc}_only", **overlap_row(rk, ent["rank"])}
                )
        sens_rows.append(
            {
                "role": role,
                "comparison": "rank_by_pressure_delta",
                **overlap_row(rk, delta_rank(cell, base)),
            }
        )
        unsh = comb["fit"]["players"]["ybar"]
        sens_rows.append(
            {
                "role": role,
                "comparison": "unshrunk_ordering",
                **overlap_row(rk, point_ranking(unsh)),
            }
        )
        for mult in e["sensitivity_multipliers"]:
            alt = run_cell(
                df, player_counts(df, role, wi, resid), role, wi, resid, crit, None, mult, False
            )
            ent = alt["scopes"]["COMBINED"]
            if "rank" in ent:
                sens_rows.append({"role": role, "comparison": f"eligibility_floor_x{mult}", **overlap_row(rk, ent["rank"]),
                                  "n_eligible": int(len(ent["players"]))})  # fmt: skip
        for comp_name in ("runs", "wicket"):
            alt = run_cell(df, player_counts(df, role, wi, res[f"r_{role}_{comp_name}"]), role, wi,
                           res[f"r_{role}_{comp_name}"], crit, None, 1.0, False)  # fmt: skip
            ent = alt["scopes"]["COMBINED"]
            if "rank" in ent:
                sens_rows.append(
                    {
                        "role": role,
                        "comparison": f"component_{comp_name}_only",
                        **overlap_row(rk, ent["rank"]),
                    }
                )
        # cross-format study
        u = cell["units"]
        half = {k: max(int(e["min_matches"] // 2), 2) for k in ("IPL", "T20I")}
        pf = {}
        for f in ("IPL", "T20I"):
            uf = u[(u["competition_type"] == f)]
            gf = uf.groupby("player_id").agg(m=("match_id", "nunique"), yb=("y", lambda s: 0.0))
            wm = uf.assign(py=uf["prec"] * uf["y"]).groupby("player_id")[["py", "prec"]].sum()
            gf["ybar"] = wm["py"] / wm["prec"]
            pf[f] = gf[gf["m"] >= half[f]]["ybar"]
        both = pd.concat([pf["IPL"].rename("ipl"), pf["T20I"].rename("t20i")], axis=1, join="inner")
        if len(both) >= 5:
            rho, lo, hi = player_bootstrap_spearman(both["ipl"], both["t20i"])
            pear = float(both["ipl"].corr(both["t20i"]))
        else:
            rho = lo = hi = pear = float("nan")
        # criteria.combination: lower 95% bound >= 0.3 and at least 30 players with both formats
        ok = bool(len(both) >= e["min_players_split_half"] and np.isfinite(lo) and lo >= 0.3)
        fmt_rows.append({"role": role, "intensity": primary, "players_both_formats": int(len(both)),
                         "spearman": rho, "spearman_low": lo, "spearman_high": hi, "pearson": pear,
                         "combination_supported": ok,
                         "combination_basis": "COMMON_EFFECT_FORMAT_CENTRED" if ok else "FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED"})  # fmt: skip
        rb = comb["reliability"]
        stt = list_status(crit, rb["parity"].get("spearman_brown"), rb["parity"].get("sb_low"), rb["oot"].get("low"),
                          comb["fit"]["floor"], len(players), rb["parity"].get("n_players", 0), rb["oot"].get("n_players", 0))  # fmt: skip
        status_rows.append({"role": role, "intensity": primary, "intensity_basis": primary_basis,
                            "indicative_list_status": stt["status"], "reason": stt["reason"]})  # fmt: skip

    est = pd.concat(est_rows, ignore_index=True)
    est["intensity_basis"] = primary_basis
    est["status"] = "EXPERIMENTAL_NOT_VALIDATED"
    est["generated_at"] = datetime.now(UTC).isoformat()
    write_p8_table(est, "p8_a_estimates")
    write_p8_table(pd.DataFrame(cmp_rows), "p8_a_intensity_comparison")
    write_p8_table(pd.DataFrame(rel_rows), "p8_a_reliability")
    write_p8_table(pd.DataFrame(reml_rows), "p8_a_reml")
    write_p8_table(pd.DataFrame(sens_rows), "p8_a_sensitivity")
    write_p8_table(pd.concat(inel_rows, ignore_index=True), "p8_a_ineligible")
    write_p8_table(pd.concat(expo_rows, ignore_index=True), "p8_a_pressure_exposure")
    write_p8_table(pd.DataFrame(boot_checks), "p8_a_boot_check")
    write_p8_table(pd.DataFrame(fmt_rows), "p8_a_format_study")
    write_p8_table(pd.DataFrame(status_rows), "p8_a_status")
    print(
        json.dumps(
            {"primary": primary, "basis": primary_basis, "status": status_rows},
            indent=1,
            default=str,
        ),
        flush=True,
    )
    _end(before)


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("models", "all"):
        stage_models()
    if stage in ("tests", "all"):
        stage_tests()
    if stage in ("estimate", "all"):
        stage_estimate()
    if stage in ("report", "all"):
        from app.phase8.report_a import write_report

        write_report(REPORTS_DIR / "phase8_approach_a_results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
