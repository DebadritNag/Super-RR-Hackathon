"""Approach B (match leverage and Win Probability Added) for batters and bowlers.

Stages (each calls ``begin_step`` first and checks the protected files and the TEST lock):

* ``winprob``  win-probability models W1/W2 and the class model, calibration, artefact, WP timeline,
               leverage, WPA attribution: ``p8_wp_*``, ``p8_delivery_leverage``, ``p8_wpa_*``.
* ``tests``    pressure-intensity validity tests for P1 (leverage) and P2 (closeness) including the
               win-probability test (d): ``p8_b_intensity_tests``.
* ``estimate`` player estimates, reliability, bootstrap and sensitivity: ``p8_b_*``.
* ``report``   writes ``reports/phase8_approach_b_results.md`` from the stored tables only.

``python scripts/phase8_approach_b.py all`` runs every stage.
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

from app.analytics.integrity import sha256_file
from app.phase8.approach_a import (
    HIGH_CUT,
    Boot,
    delta_rank,
    evidence_class,
    exposure_by_context,
    final_intensity,
    list_status,
    overlap_row,
    player_bootstrap_spearman,
    player_counts,
    run_cell,
)
from app.phase8.approach_b import (
    combine_wp_before,
    component_counterfactuals,
    design_matrix,
    leverage_all,
    leverage_weighted,
    wpa_residuals,
)
from app.phase8.constants import OFFICIAL_DB, PHASE8_DB, PREHASH_FILE, REPORTS_DIR, SEED
from app.phase8.criteria import begin_step, load_criteria
from app.phase8.data import load_pre_test_deliveries
from app.phase8.intensity import build_intensity, intensity_from_wp
from app.phase8.intensity_validity import (
    _bin_stats,
    _mask,
    _spearman,
    assign_bins,
    decile_edges,
    run_validity_tests,
    summarise_candidates,
)
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state
from app.phase8.splits import assert_pre_test, check_match_partition
from app.phase8.stability import point_ranking
from app.phase8.store import write_p8_table
from app.phase8.units import ROLE_COL
from app.phase8.winprob import (
    W1_COLS,
    W2_COLS,
    class_target,
    fit_class_oof,
    fit_wp,
    frame_features,
    innings_gate,
    match_labels,
    save_wp_artifact,
    wp_after_series,
    wp_labels,
)
from app.phase8.wpa import attribute

CACHE = Path("d:/Data/.agents/tasks/_p8c3_cache")
A_CACHE = Path("d:/Data/.agents/tasks/_p8c2_cache")
CANDIDATES_B = ("P0", "P1", "P2", "P3", "P4", "P5", "P6")
BOOT_DRAWS = 1000
ID = ["match_id", "innings_number", "innings_ball_num"]


def _begin(stage: str) -> tuple[dict, dict]:
    check_protected()
    before = lock_state()
    info = begin_step(f"approach_b_{stage}")
    return before, info


def _end(before: dict) -> None:
    assert_lock_state_unchanged(before)
    check_protected()


def _matches() -> pd.DataFrame:
    con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
    try:
        return con.execute(
            "SELECT match_id, result, win_team_id, revised_target, result_status FROM matches"
        ).df()
    finally:
        con.close()


def stage_winprob() -> None:
    before, info = _begin("winprob")
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    part = check_match_partition(df)
    matches = _matches()
    labels = match_labels(matches)
    in_scope = set(df["match_id"].unique())
    lab_scope = labels[labels["match_id"].isin(in_scope)]
    excl = labels[~labels["label_ok"] & labels["match_id"].isin(in_scope)].merge(
        matches[["match_id", "result", "result_status"]], on="match_id"
    )
    excl["reason_group"] = excl["reason"].str.split(":").str[0]
    write_p8_table(
        excl.drop(columns=["win_team_id", "label_ok"]).assign(
            period=excl["match_id"].map(
                df.drop_duplicates("match_id").set_index("match_id")["period"]
            )
        ),
        "p8_wp_label_exclusions",
    )
    print("labelled matches in scope:", int(lab_scope["label_ok"].sum()), "of", len(lab_scope))
    print(excl["reason_group"].value_counts().to_string(), flush=True)

    x = frame_features(df)
    y2, pop2 = wp_labels(df, labels, 2)
    y1, pop1 = wp_labels(df, labels, 1)
    score2 = (df["innings_number"] == 2) & x[["runs_required", "rrr"]].notna().all(axis=1)
    score1 = (df["innings_number"] == 1) & x["legal_balls_remaining"].notna()
    f2 = fit_wp("W2", df, x, y2, pop2 & score2, W2_COLS,
                ["resource_ratio", "rrr", "wickets_remaining"], score2)  # fmt: skip
    f1 = fit_wp("W1", df, x, y1, pop1 & score1, W1_COLS,
                ["projected_total", "wickets_remaining", "legal_balls_remaining"], score1)  # fmt: skip
    fits = {"W1": f1, "W2": f2}
    gates = {k: innings_gate(v.metrics) for k, v in fits.items()}
    for k, v in fits.items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.metrics.items()},
              gates[k], flush=True)  # fmt: skip

    yc, popc = class_target(df)
    cls_full, cls_fold, cm = fit_class_oof(df, x, yc, popc)
    print("class model", cm, flush=True)

    wp_before = combine_wp_before(df, f1, f2)
    wp_after = wp_after_series(df, wp_before, labels)
    lev, probs = leverage_all(df, wp_before, f1, f2, cls_full, cls_fold)
    cf = component_counterfactuals(df, f1, f2, cls_full, cls_fold)
    att_in = df[[
        "out_batter_runs", "out_extras_type", "out_is_wicket", "out_dismissal_type",
        "out_dismissed_player_id", "den_bowler_credited_wicket", "striker_id", "non_striker_id",
        "ok_run_target", "ok_wicket_target",
    ]].assign(wp_before=wp_before, wp_after=wp_after).join(cf)  # fmt: skip
    wpa = attribute(att_in)
    if not gates["W1"]["passed"]:
        inn1 = (df["innings_number"] == 1) & (wpa["excluded_reason"] == "")
        wpa.loc[inn1, ["striker_wpa", "bowler_wpa", "team_only_wpa", "dismissed_wpa"]] = np.nan
        wpa.loc[inn1, "excluded_reason"] = "INNINGS1_WP_NOT_RELIABLE"

    # ---- tables -----------------------------------------------------------------------------
    mrows = []
    for k, v in fits.items():
        mrows.append({**v.metrics, **{f"gate_{a}": b for a, b in gates[k].items()},
                      "n_train": v.n_train, "train_matches": v.train_matches})  # fmt: skip
    write_p8_table(pd.DataFrame(mrows), "p8_wp_metrics")
    write_p8_table(
        pd.DataFrame([{"model": k, **g} for k, v in fits.items() for g in v.grid]),
        "p8_wp_model_grid",
    )
    write_p8_table(
        pd.DataFrame([{"model": k, **d} for k, v in fits.items() for d in v.deciles]),
        "p8_wp_calibration",
    )
    write_p8_table(pd.DataFrame([cm]), "p8_wp_class_metrics")
    out = df[ID + ["period", "competition_type"]].copy()
    out["wp_before"], out["wp_after"], out["leverage"] = wp_before, wp_after, lev
    out["wpa_d"] = wpa["d"]
    out["split_rule"], out["excluded_reason"] = wpa["split_rule"], wpa["excluded_reason"]
    write_p8_table(out, "p8_delivery_leverage")
    exc = wpa.assign(innings=df["innings_number"], period=df["period"])
    cnt = (
        exc[exc["excluded_reason"] != ""]
        .groupby(["excluded_reason", "innings", "period"])
        .size()
        .rename("balls")
        .reset_index()
    )
    write_p8_table(cnt, "p8_wpa_excluded_events")
    summ = (
        wpa.assign(innings=df["innings_number"])
        .groupby(["split_rule", "innings"])
        .agg(balls=("d", "size"), attributed=("d", lambda s: int(s.notna().sum())))
        .reset_index()
    )
    write_p8_table(summ, "p8_wpa_split_rules")

    # ---- feature recompute check and artefact ------------------------------------------------
    chk = {}
    for c in ("rrr", "gap", "resource_ratio", "projected_total", "crr"):
        both = df[c].notna() & x[c].notna()
        chk[c] = float(np.nanmax(np.abs(df.loc[both, c] - x.loc[both, c])))
    write_p8_table(pd.DataFrame([{"column": k, "max_abs_diff": v} for k, v in chk.items()]),
                   "p8_wp_feature_check")  # fmt: skip
    print("feature recompute max abs diff", chk, flush=True)
    prehash = json.loads(Path(PREHASH_FILE).read_text(encoding="utf-8-sig"))
    meta = {
        "trained_on": "TRAIN", "seed": SEED, "criteria_sha256": info["sha256"],
        "timestamp": datetime.now(UTC).isoformat(),
        "data_hash_exploratory_db": next((v for k, v in prehash.items() if "exploratory.duckdb" in k), None),
        "train_matches": int(df.loc[df["period"] == "TRAIN", "match_id"].nunique()),
        "validation_matches": int(df.loc[df["period"] == "VALIDATION", "match_id"].nunique()),
        "training_period": "matches up to 2024-12-31 (config/phase4_split_v1.json)",
        "validation_period": "calendar 2025", "test": "never loaded",
        "class_model": cm, "gates": gates, "partition": part,
        "labels": {"excluded_matches": int(len(excl)), "labelled_matches": int(lab_scope["label_ok"].sum())},
    }  # fmt: skip
    path = save_wp_artifact(fits, cls_full, meta)
    print("artefact", path, sha256_file(path), flush=True)

    CACHE.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"wp_before": wp_before, "wp_after": wp_after, "lev": lev, "wpa": wpa, "gates": gates,
         "probs": probs, "cf": cf, "index_cols": df[ID]},
        CACHE / "timeline.joblib",
    )  # fmt: skip
    _end(before)


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


def _timeline() -> dict:
    return joblib.load(CACHE / "timeline.joblib")


def _intensities(df: pd.DataFrame, tl: dict) -> pd.DataFrame:
    w, _ = build_intensity(df)
    return w.join(intensity_from_wp(df, tl["wp_before"], tl["lev"]))


def test_d_rows(df: pd.DataFrame, w: pd.DataFrame, absd: pd.Series) -> pd.DataFrame:
    """Test (d): mean absolute WP change per delivery in the top vs bottom intensity decile.

    Deciles use TRAIN edges per stratum. Candidates built from the WP model (P1, P2) pass this test
    mechanically; the flag ``mechanical`` says so. No bootstrap interval (stated in the report).
    """
    rows = []
    for col in w.columns:
        x = w[col].to_numpy(dtype="float64")
        for st in ("pooled", "innings_1", "innings_2"):
            m = _mask(df, st) & np.isfinite(x) & absd.notna().to_numpy()
            tr = m & (df["period"] == "TRAIN").to_numpy()
            if tr.sum() < 2000:
                rows.append({"candidate": col[2:], "stratum": st, "status": "NOT_ESTIMABLE"})
                continue
            edges = decile_edges(x[tr])
            for per, sel in (
                ("TRAIN", tr),
                ("VALIDATION", m & (df["period"] == "VALIDATION").to_numpy()),
            ):
                b = assign_bins(x[sel], edges)
                k = len(edges) + 1
                s, c = _bin_stats(absd.to_numpy()[sel], b, k)
                with np.errstate(divide="ignore", invalid="ignore"):
                    mean = s / c
                ok = np.isfinite(mean)
                rho = (
                    _spearman(np.arange(k)[ok].astype(float), mean[ok]) if ok.sum() > 2 else np.nan
                )
                rows.append({"candidate": col[2:], "stratum": st, "period": per, "status": "ESTIMATED",
                             "n": int(sel.sum()), "abs_wpa_low_decile": float(mean[0]),
                             "abs_wpa_high_decile": float(mean[-1]),
                             "diff": float(mean[-1] - mean[0]), "spearman": rho,
                             "test_d": bool(mean[-1] > mean[0]),
                             "mechanical": col[2:] in ("P1", "P2")})  # fmt: skip
    return pd.DataFrame(rows)


def stage_tests() -> None:
    before, _ = _begin("tests")
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    tl = _timeline()
    w = _intensities(df, tl)
    new = w[["w_P1", "w_P2"]]
    tests = run_validity_tests(df, new)
    write_p8_table(tests.astype({"test_a": "object", "test_b": "object"}), "p8_b_intensity_tests")
    d_rows = test_d_rows(df, w, tl["wpa"]["d"].abs())
    write_p8_table(d_rows, "p8_b_test_d")
    old = _read("p8_intensity_tests")
    both = pd.concat([old[~old["candidate"].isin(["P1", "P2"])], tests], ignore_index=True)
    summ = summarise_candidates(both)
    dd = d_rows[(d_rows["status"] == "ESTIMATED") & (d_rows["period"] == "TRAIN")
                & (d_rows["stratum"] == "pooled")].set_index("candidate")["test_d"]  # fmt: skip
    summ["test_d"] = summ["candidate"].map(dd)
    write_p8_table(summ, "p8_b_intensity_selection")
    print(summ.to_string(), flush=True)
    _end(before)


def _grp_exposure(df: pd.DataFrame, role: str, w: pd.Series, players: np.ndarray) -> pd.DataFrame:
    return exposure_by_context(df, role, w, players)


def stage_estimate() -> None:
    before, info = _begin("estimate")
    crit = load_criteria()
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    tl = _timeline()
    w = _intensities(df, tl)
    wpa, lev = tl["wpa"], tl["lev"]
    c2 = joblib.load(A_CACHE / "residuals.joblib")
    yexp = c2["yexp"]
    sel = _read("p8_intensity_selection")
    primary = str(sel.loc[sel["primary"].astype(bool), "candidate"].iloc[0])
    primary_basis = str(sel.loc[sel["candidate"] == primary, "primary_basis"].iloc[0])
    names = _names()
    boot = Boot(df, BOOT_DRAWS)
    e = crit["eligibility"]
    credit = {"batter": wpa["striker_wpa"], "bowler": wpa["bowler_wpa"]}
    est_rows, rel_rows, cmp_rows, reml_rows, sens_rows = [], [], [], [], []
    inel_rows, expo_rows, boot_checks, fmt_rows, status_rows, coef_rows = [], [], [], [], [], []
    cells: dict[tuple[str, str], dict] = {}
    boot_cands = (primary, "P1", "P2")
    for role in ("batter", "bowler"):
        exp_runs = yexp[f"{role}_runs"]["expected"]
        x = design_matrix(df, lev, exp_runs)
        resid, coefs = wpa_residuals(df, credit[role], x)
        coef_rows.append(coefs.assign(role=role))
        fitted = credit[role] - resid
        raw = credit[role]
        inn2 = resid.where(df["innings_number"] == 2)
        lw = leverage_weighted(df, ROLE_COL[role], credit[role], lev)
        for cand in CANDIDATES_B:
            wi, iinfo = (
                final_intensity(w, cand)
                if cand == primary
                else (w[f"w_{cand}"], {"innings1_fallback": None})
            )
            deliv = player_counts(df, role, wi, resid)
            use_boot = boot if cand in boot_cands else None
            cell = run_cell(
                df, deliv, role, wi, resid, crit, use_boot, 1.0, use_boot is not None, 1000
            )
            cells[(role, cand)] = cell
            comb = cell["scopes"]["COMBINED"]
            row = {"role": role, "intensity": cand, "is_primary": cand == primary,
                   "reference_only": cand == "P0", "mechanical_with_wpa": cand in ("P1", "P2"),
                   "innings1_fallback": iinfo["innings1_fallback"] or "",
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
                row.update({
                    "volume_spearman": float(fp["basis"].rank().corr(fp["P"].rank())),
                    "split_half_r": par["r"], "split_half_sb": par["spearman_brown"],
                    "split_half_sb_low": par.get("sb_low"), "split_half_sb_high": par.get("sb_high"),
                    "split_half_players": par["n_players"], "time_sb": tim["spearman_brown"],
                    "time_sb_low": tim.get("sb_low"), "time_sb_high": tim.get("sb_high"),
                    "ipl_parity_sb": rb["per_format"]["IPL"].get("spearman_brown"),
                    "t20i_parity_sb": rb["per_format"]["T20I"].get("spearman_brown"),
                    "icc1": ic["icc"], "icc_players": ic["n_players"], "oot_status": oot["status"],
                    "oot_spearman": oot["spearman"], "oot_low": oot.get("low"),
                    "oot_high": oot.get("high"), "oot_players": oot["n_players"],
                    "floor": comb["fit"]["floor"], "tau2": comb["fit"]["tau2"],
                    "sigma2": comb["fit"]["sigma2"], "mean_B": comb["fit"]["mean_B"],
                    "share_B_gt_0_5": float((comb["fit"]["players"]["B"] > 0.5).mean()),
                    "top10_prob_ge_0_5": int((stab["top_k_prob"] >= 0.5).sum()),
                    "median_rank_interval_width": float((stab["rank_high"] - stab["rank_low"]).median()),
                    "indicative_status": st["status"], "status_reason": st["reason"],
                })  # fmt: skip
                for metric, blk in (("parity", par), ("time", tim)):
                    rel_rows.append({"role": role, "intensity": cand, "metric": metric,
                                     **{k: v for k, v in blk.items() if k != "mode"}})  # fmt: skip
            cmp_rows.append(row)

        # primary cell -----------------------------------------------------------------------
        cell = cells[(role, primary)]
        wi, _ = final_intensity(w, primary)
        base = cell["baseline"]
        comb = cell["scopes"]["COMBINED"]
        if "fit" not in comb:
            status_rows.append({"role": role, "status": comb.get("status", "NOT_ESTIMABLE")})
            continue
        players = comb["players"]
        hi = (wi >= HIGH_CUT) & df[ROLE_COL[role]].isin(players) & resid.notna()
        pt = pd.DataFrame({"player_id": df.loc[hi, ROLE_COL[role]].to_numpy(), "w": wi[hi].to_numpy(),
                           "wo": (wi[hi] * credit[role][hi]).to_numpy(),
                           "we": (wi[hi] * fitted[hi]).to_numpy(),
                           "wl": (wi[hi] * lev[hi]).to_numpy()}).groupby("player_id").sum()  # fmt: skip
        pt = pd.DataFrame({"obs_wpa": pt["wo"] / pt["w"], "exp_wpa_given_leverage": pt["we"] / pt["w"],
                           "mean_leverage_pressure": pt["wl"] / pt["w"]})  # fmt: skip
        expo = _grp_exposure(df, role, wi, players)
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
                              "disp": g["y"].std(ddof=1).fillna(0.0), "n_units": g.size(),
                              "mean_unit_intensity": g["mean_intensity"].mean()}).reset_index(),
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
                ps = ps.merge(pt.reset_index(), on="player_id", how="left")
                ps = ps.merge(
                    lw.reset_index().rename(columns={"index": "player_id"}),
                    on="player_id",
                    how="left",
                )
                ps = ps.merge(expo, on="player_id", how="left")
                ps["evidence_class"] = evidence_class(ps.assign(eligible=True, estimate=ps["basis"]),
                                                      e["min_matches"]).to_numpy()  # fmt: skip
                for f in ("IPL", "T20I"):
                    ff = (
                        cell["scopes"][f]["counts"]["n_matches"]
                        if "counts" in cell["scopes"][f]
                        else pd.Series(dtype=float)
                    )
                    ps[f"matches_{f.lower()}"] = ps["player_id"].map(ff)
            est_rows.append(ps)
        cn, elig = comb["counts"], comb["eligible"]
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

        # sensitivity -----------------------------------------------------------------------
        rk = comb["rank"]
        for cand in CANDIDATES_B:
            if cand != primary and "rank" in cells[(role, cand)]["scopes"]["COMBINED"]:
                sens_rows.append({"role": role, "comparison": f"intensity_{cand}",
                                  **overlap_row(rk, cells[(role, cand)]["scopes"]["COMBINED"]["rank"])})  # fmt: skip
        for sc in ("IPL", "T20I"):
            if "rank" in cell["scopes"][sc]:
                sens_rows.append({"role": role, "comparison": f"scope_{sc}_only",
                                  **overlap_row(rk, cell["scopes"][sc]["rank"])})  # fmt: skip
        sens_rows.append({"role": role, "comparison": "rank_by_pressure_delta",
                          **overlap_row(rk, delta_rank(cell, base))})  # fmt: skip
        sens_rows.append({"role": role, "comparison": "unshrunk_ordering",
                          **overlap_row(rk, point_ranking(comb["fit"]["players"]["ybar"]))})  # fmt: skip
        for mult in e["sensitivity_multipliers"]:
            alt = run_cell(
                df, player_counts(df, role, wi, resid), role, wi, resid, crit, None, mult, False
            )
            ent = alt["scopes"]["COMBINED"]
            if "rank" in ent:
                sens_rows.append({"role": role, "comparison": f"eligibility_floor_x{mult}",
                                  **overlap_row(rk, ent["rank"]), "n_eligible": int(len(ent["players"]))})  # fmt: skip
        for name, rr in (("raw_wpa_not_leverage_adjusted", raw), ("innings2_only", inn2)):
            alt = run_cell(
                df, player_counts(df, role, wi, rr), role, wi, rr, crit, None, 1.0, False
            )
            ent = alt["scopes"]["COMBINED"]
            if "rank" in ent:
                sens_rows.append({"role": role, "comparison": name, **overlap_row(rk, ent["rank"]),
                                  "n_eligible": int(len(ent["players"]))})  # fmt: skip
        lwe = lw.reindex(players)["lw_wpa_per_opp"].dropna()
        sens_rows.append({"role": role, "comparison": "leverage_weighted_wpa_per_opportunity_all_balls",
                          **overlap_row(rk, point_ranking(lwe))})  # fmt: skip
        # cross-format study
        u = cell["units"]
        half = {k: max(int(e["min_matches"] // 2), 2) for k in ("IPL", "T20I")}
        pf = {}
        for f in ("IPL", "T20I"):
            uf = u[u["competition_type"] == f]
            gf = uf.groupby("player_id").agg(m=("match_id", "nunique"))
            wm = uf.assign(py=uf["prec"] * uf["y"]).groupby("player_id")[["py", "prec"]].sum()
            gf["ybar"] = wm["py"] / wm["prec"]
            pf[f] = gf[gf["m"] >= half[f]]["ybar"]
        both = pd.concat([pf["IPL"].rename("ipl"), pf["T20I"].rename("t20i")], axis=1, join="inner")
        if len(both) >= 5:
            rho, lo, hi_ = player_bootstrap_spearman(both["ipl"], both["t20i"])
            pear = float(both["ipl"].corr(both["t20i"]))
        else:
            rho = lo = hi_ = pear = float("nan")
        ok = bool(len(both) >= e["min_players_split_half"] and np.isfinite(lo) and lo >= 0.3)
        fmt_rows.append({"role": role, "intensity": primary, "players_both_formats": int(len(both)),
                         "spearman": rho, "spearman_low": lo, "spearman_high": hi_, "pearson": pear,
                         "combination_supported": ok,
                         "combination_basis": "COMMON_EFFECT_FORMAT_CENTRED" if ok else "FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED"})  # fmt: skip
        rb = comb["reliability"]
        stt = list_status(crit, rb["parity"].get("spearman_brown"), rb["parity"].get("sb_low"),
                          rb["oot"].get("low"), comb["fit"]["floor"], len(players),
                          rb["parity"].get("n_players", 0), rb["oot"].get("n_players", 0))  # fmt: skip
        status_rows.append({"role": role, "intensity": primary, "intensity_basis": primary_basis,
                            "indicative_list_status": stt["status"], "reason": stt["reason"],
                            "innings1_wp_gate_passed": bool(tl["gates"]["W1"]["passed"])})  # fmt: skip

    est = pd.concat(est_rows, ignore_index=True)
    est["intensity_basis"] = primary_basis
    est["status"] = "EXPERIMENTAL_NOT_VALIDATED"
    est["generated_at"] = datetime.now(UTC).isoformat()
    write_p8_table(est, "p8_b_estimates")
    write_p8_table(pd.DataFrame(cmp_rows), "p8_b_intensity_comparison")
    write_p8_table(pd.DataFrame(rel_rows), "p8_b_reliability")
    write_p8_table(pd.DataFrame(reml_rows), "p8_b_reml")
    write_p8_table(pd.DataFrame(sens_rows), "p8_b_sensitivity")
    write_p8_table(pd.concat(inel_rows, ignore_index=True), "p8_b_ineligible")
    write_p8_table(pd.concat(expo_rows, ignore_index=True), "p8_b_pressure_exposure")
    write_p8_table(pd.DataFrame(boot_checks), "p8_b_boot_check")
    write_p8_table(pd.DataFrame(fmt_rows), "p8_b_format_study")
    write_p8_table(pd.DataFrame(status_rows), "p8_b_status")
    write_p8_table(pd.concat(coef_rows, ignore_index=True), "p8_b_wpa_regression")
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
    if stage in ("winprob", "all"):
        stage_winprob()
    if stage in ("tests", "all"):
        stage_tests()
    if stage in ("estimate", "all"):
        stage_estimate()
    if stage in ("report", "all"):
        from app.phase8.report_b import write_report

        write_report(REPORTS_DIR / "phase8_approach_b_results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
