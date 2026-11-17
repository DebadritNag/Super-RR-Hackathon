"""Markdown report for Approach B, generated from the stored ``p8_*`` tables only."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.phase8.constants import MODELS_DIR
from app.phase8.report_a import _fmt, _t, md_table

ROLES = ("batter", "bowler")


def _top(est: pd.DataFrame, role: str, k: int = 10, lo: int = 1) -> pd.DataFrame:
    e = est[(est["role"] == role) & (est["scope"] == "COMBINED")]
    return e[(e["rank"] >= lo) & (e["rank"] <= k)].sort_values("rank")


def write_report(path: Path | str) -> Path:
    met, cal = _t("p8_wp_metrics"), _t("p8_wp_calibration")
    cls, lab = _t("p8_wp_class_metrics"), _t("p8_wp_label_exclusions")
    lev, exc, spl = (
        _t("p8_delivery_leverage"),
        _t("p8_wpa_excluded_events"),
        _t("p8_wpa_split_rules"),
    )
    chk = _t("p8_wp_feature_check")
    tests, td, sel = _t("p8_b_intensity_tests"), _t("p8_b_test_d"), _t("p8_b_intensity_selection")
    est, cmp_, sens = _t("p8_b_estimates"), _t("p8_b_intensity_comparison"), _t("p8_b_sensitivity")
    reml, fmt, status = _t("p8_b_reml"), _t("p8_b_format_study"), _t("p8_b_status")
    boot, inel, reg = _t("p8_b_boot_check"), _t("p8_b_ineligible"), _t("p8_b_wpa_regression")
    meta = json.loads((MODELS_DIR / "p8_wp_v1.json").read_text(encoding="utf-8"))
    primary = str(sel.loc[sel["primary"].astype(bool), "candidate"].iloc[0])
    basis = str(sel.loc[sel["candidate"] == primary, "primary_basis"].iloc[0])
    L: list[str] = []
    L.append("# Phase 8 Approach B results: match leverage and Win Probability Added (WPA)\n")
    L.append(
        "Status: **EXPERIMENTAL_NOT_VALIDATED**. Every player list below is an exploratory ordering "
        "produced by Approach B alone. It is not the submitted ranking and it is not validated: the "
        "Phase 6 findings (between-player variance at the shrinkage floor, split-half reliability far "
        "below 0.5, zero contexts passing the 0.5 data-weight gate) were re-tested and still hold "
        "(section 7). The submitted lists are chosen later by the predeclared rule. Every number is read "
        "from the `p8_wp_*`, `p8_delivery_leverage`, `p8_wpa_*` and `p8_b_*` tables in `phase8.duckdb`. "
        "TEST (2026 onward) was not opened.\n"
    )
    L.append("## 1. Definitions kept apart\n")
    L.append(
        "| Object | Definition | Uses outcome of the ball? |\n|---|---|---|\n"
        "| Pressure intensity | pre-delivery situational difficulty in [0,1] (section 5) | no |\n"
        "| Leverage `L` | expected absolute win-probability swing of the next ball, `sum_k p_k abs(WP_k - WP_before)` over seven outcome classes | no |\n"
        "| WPA | realised `WP_after - WP_before`, credited to players by the rules in section 4 | yes |\n"
        "| WPA above leverage expectation | WPA minus a TRAIN-fitted linear expectation from leverage, phase, innings and A-model expected runs | yes |\n\n"
        "High WPA is never read as pressure. Leverage is reported as a candidate intensity (P1) and "
        "tested like any other candidate; it is mechanically tied to WPA, which is flagged wherever it matters.\n"
    )
    L.append("## 2. Win-probability models\n")
    n_lab = meta["labels"]
    L.append(
        f"Population: IPL and T20I, TRAIN ({meta['train_matches']} matches) and VALIDATION "
        f"({meta['validation_matches']} matches). Labels use decisive regulation results only: "
        f"{n_lab['labelled_matches']} matches are labelled and {n_lab['excluded_matches']} in-scope matches "
        "are excluded and never imputed (no result, abandoned, tied, Super Over or eliminator, DLS or "
        "D/L text, revised target).\n"
    )
    grp = lab.groupby("reason_group").size().rename("matches").reset_index()
    L.append(md_table(grp, ["reason_group", "matches"]) + "\n")
    L.append(
        "Models (`app/phase8/winprob.py`): `W2` (innings 2, target: chasing side wins) and `W1` "
        "(innings 1, target: batting side eventually wins) are HistGradientBoosting classifiers on "
        "pre-delivery state only (features in the artefact metadata). One pass over the declared grid on "
        "VALIDATION chose the parameters by log loss; TRAIN deliveries are scored out of fold "
        "(`match_id % 5`) and VALIDATION deliveries by the model fitted on all of TRAIN. Baselines: "
        "constant prior and a logistic regression on a few state variables. Both opposing-team priors "
        "(win rate over the last five earlier decisive matches) are used instead of the batting side's "
        "alone (declared change; both are pre-match information).\n"
    )
    cols = ["model", "n_validation", "brier", "brier_const", "brier_logit", "brier_gain_vs_const",
            "brier_gain_vs_logit", "log_loss", "log_loss_const", "log_loss_logit", "slope", "intercept"]  # fmt: skip
    L.append("Validation metrics (out of sample, 2025):\n")
    L.append(md_table(met, cols, 4) + "\n")
    L.append(
        "Innings-1 gate (declared before results: calibration slope in [0.8, 1.2] and Brier gain of at least 2% over the constant):\n"
    )
    L.append(
        md_table(met, ["model", "gate_slope_ok", "gate_brier_gain_ok", "gate_passed"], 3) + "\n"
    )
    w1 = met[met["model"] == "W1"].iloc[0]
    L.append(
        f"W1 passes the declared gate on VALIDATION (slope {_fmt(w1['slope'])}, Brier gain "
        f"{_fmt(w1['brier_gain_vs_const'])}). The out-of-fold TRAIN scores are weaker (slope "
        f"{_fmt(w1['train_oof_slope'])}, Brier gain {_fmt(w1['train_oof_brier_gain_vs_const'])}), so the "
        "innings-1 model is less stable than the validation gate alone suggests. The gate was not changed "
        "after seeing results; the estimates are therefore also reported with innings 1 excluded "
        "(`innings2_only` in section 7).\n"
    )
    L.append("Decile calibration on VALIDATION (equal-count bins of predicted probability):\n")
    for m in ("W2", "W1"):
        c = cal[cal["model"] == m]
        L.append(f"`{m}`:\n")
        L.append(md_table(c, ["bin", "n", "mean_pred", "mean_obs"], 3) + "\n")
    L.append(
        "Feature recompute check (the one function that builds features for real rows and for "
        "hypothetical next states reproduces the stored state columns):\n"
    )
    L.append(md_table(chk, ["column", "max_abs_diff"], 12) + "\n")
    L.append(
        f"Artefact: `backend/data/models/p8_wp_v1.joblib` with `p8_wp_v1.json` (algorithm, version, "
        f"training period `{meta['training_period']}`, matches and deliveries, features, targets, "
        f"metrics, exploratory database hash `{meta['data_hash_exploratory_db']}`, seed {meta['seed']}, "
        f"timestamp {meta['timestamp']}, criteria hash {meta['criteria_sha256']}).\n"
    )
    L.append("## 3. Leverage\n")
    c = cls.iloc[0]
    L.append(
        "The next-ball class model (dot, 1, 2, 3, 4, 6, wicket; legal balls) uses situation features only "
        "(no batter or bowler variables) with fixed declared parameters (no tuning). Validation: "
        f"multi-class log loss {_fmt(c['log_loss'], 4)} against {_fmt(c['log_loss_const'], 4)} for the "
        f"class prior (gain {_fmt(c['log_loss_gain'])}); wicket-probability Brier {_fmt(c['wicket_brier'], 5)} "
        f"against {_fmt(c['wicket_brier_const'], 5)}. The class probabilities add little over the prior, so "
        "leverage is driven mainly by the win-probability surface, not by the outcome mix.\n"
    )
    g = lev.groupby(["period", "innings_number"]).agg(
        balls=("leverage", "size"), defined=("leverage", "count"), mean_leverage=("leverage", "mean"),
        median_leverage=("leverage", "median"), p95=("leverage", lambda s: s.quantile(0.95)),
        mean_abs_wpa=("wpa_d", lambda s: s.abs().mean()),
    ).reset_index()  # fmt: skip
    L.append(md_table(g, ["period", "innings_number", "balls", "defined", "mean_leverage",
                          "median_leverage", "p95", "mean_abs_wpa"], 4) + "\n")  # fmt: skip
    v = lev[(lev["period"] == "VALIDATION") & lev["wpa_d"].notna() & lev["leverage"].notna()]
    rho = float(v["leverage"].corr(v["wpa_d"].abs(), method="spearman"))
    L.append(
        f"Check that leverage measures what it claims: on VALIDATION the Spearman correlation between "
        f"pre-delivery leverage and the realised absolute swing of the ball is {_fmt(rho)} "
        f"({len(v)} balls). Leverage is computed before the ball and never uses its outcome.\n"
    )
    L.append("## 4. WPA attribution\n")
    L.append(
        "`WP_after` of a ball is `WP_before` of the next ball of the same innings; the last ball of an "
        "innings 2 uses the match result, the last ball of an innings 1 uses `1 - WP2` of the first ball "
        "of the chase. WP is clipped to [0.005, 0.995] before differencing. Rules (`app/phase8/wpa.py`):\n\n"
        "- runs off the bat and dot balls: striker `+d`, bowler `-d`;\n"
        "- wides and the no-ball penalty: bowler only; a wide gives the striker nothing;\n"
        "- byes and leg-byes: batting side collectively, no striker and no bowler credit (the ball is left out of both players' records, not counted as zero);\n"
        "- bowler-credited wicket (bowled, caught, lbw, stumped, hit wicket): dismissed batter `d_wkt`, bowler `-d_wkt`;\n"
        "- run-outs: dismissed player takes the wicket share, the bowler gets neither credit nor blame (fielding is not modelled);\n"
        "- retired, obstructing the field, extras of type other or penalty, metric-flag anomalies and balls with no defined WP are excluded and counted below.\n\n"
        "When a ball has more than one component (for example a wicket with a dot, a no-ball with runs, "
        "a run-out with a run) the realised delta is split by a counterfactual rule: each component's "
        "delta is the WP change if only that component had happened, and the remainder is shared in "
        "proportion to the absolute component deltas, so the parts always add up to the ball's `d`. This "
        "replaces the plan's expected-share split (declared change). A non-striker dismissed in a run-out "
        "is recorded in the delivery table but does not enter the striker-keyed batter units.\n"
    )
    L.append(md_table(exc, ["excluded_reason", "innings", "period", "balls"], 0) + "\n")
    spl = spl.assign(split_rule=spl["split_rule"].replace("", "NOT_ATTRIBUTED"))
    L.append(md_table(spl, ["split_rule", "innings", "balls", "attributed"], 0) + "\n")
    att = lev["wpa_d"].dropna()
    L.append(
        f"`ZERO_DELTA` marks multi-component balls where WP is flat across all candidate states, so "
        f"the split cannot matter. More generally the gradient-boosting WP surface is piecewise "
        f"constant: {_fmt(float((att.abs() < 1e-12).mean()))} of the {len(att)} attributed balls have "
        "a realised WPA of exactly zero. This coarseness is a limitation of the tree model "
        "(small state changes inside one leaf do not move WP) and adds noise to every WPA total.\n"
    )
    L.append(
        "## 5. Pressure intensity: leverage (P1) and closeness (P2) against the predeclared tests\n"
    )
    L.append(
        "P1 and P2 are built from the out-of-fold win-probability model and scaled by the same TRAIN-only "
        "empirical CDF as the other candidates. Test (d) (mean absolute WP change larger in the top than "
        "in the bottom decile) is now available for every candidate; for P1 and P2 it is mechanical.\n"
    )
    L.append(md_table(sel, ["candidate", "pass", "test_a", "test_b", "test_c", "test_e", "test_d",
                            "n_tests_passed", "primary", "primary_basis"], 3) + "\n")  # fmt: skip
    td_s = td[(td["status"] == "ESTIMATED") & (td["stratum"] == "pooled")]
    L.append(md_table(td_s, ["candidate", "period", "n", "abs_wpa_low_decile", "abs_wpa_high_decile",
                             "diff", "spearman", "test_d", "mechanical"], 4) + "\n")  # fmt: skip
    L.append(
        f"No candidate passes the predeclared pass rule. Leverage (P1) and closeness (P2) do not mark "
        "situations with lower scoring or higher wicket risk, so they fail tests a, b, c and e: a ball "
        "can be high-stakes without being hard for the batting side. The primary intensity stays "
        f"`{primary}` with basis `{basis}` (best available, not passing), as chosen for Approach A. "
        "The test (d) column shows that the primary intensity does not mark balls with larger WP swings "
        "either.\n"
    )
    ts = tests[(tests["status"] == "ESTIMATED") & (tests["stratum"] == "pooled")]
    L.append(md_table(ts, ["candidate", "period", "runs_diff", "wkt_diff", "var_diff", "test_a",
                           "test_b", "test_c", "test_e"], 4) + "\n")  # fmt: skip
    L.append("## 6. Player-level B score\n")
    L.append(
        "Per delivery the credit is the role's WPA (striker or bowler). The B residual is `credit - "
        "fitted`, where `fitted` comes from a linear regression on leverage, leverage squared, phase, "
        "innings and the A-model expected runs, fitted on TRAIN only (out of fold for TRAIN rows). The "
        "unit is the player-match; the REML, eligibility floors, match-cluster bootstrap (1000 full "
        "refits), split-half, ICC and out-of-time procedures are exactly those of Approach A "
        "(`run_cell`). Pressure balls are those with intensity of at least 0.5; the normal baseline is "
        "the mean B residual on balls below 0.5. Positive is better for the player in both roles.\n"
    )
    L.append(md_table(reg[reg["fit"] == "TRAIN_ALL"], ["role", "const", "L", "L2", "middle", "death",
                                                      "innings2", "exp_runs"], 4) + "\n")  # fmt: skip
    L.append("## 7. Reliability, floor and sensitivity\n")
    for r in ROLES:
        rr = reml[
            (reml["role"] == r) & (reml["scope"] == "COMBINED") & (reml["intensity"] == primary)
        ]
        L.append(f"**{r.title()}s** REML (primary intensity `{primary}`, combined formats):\n")
        L.append(md_table(rr, ["tau2", "sigma2", "floor", "label", "mean_B", "share_B_gt_0_5",
                               "n_players", "n_units"], 6) + "\n")  # fmt: skip
    L.append(
        "Between-player variance is at the floor for the primary cell of both roles (tau2 is zero), "
        "so the posterior collapses to the league mean and the listed order is the unshrunk "
        "precision-weighted mean (`UNSHRUNK_FLOOR`). The share of players with data weight B above 0.5, "
        "the Phase 6 gate quantity, is reported unchanged in the `share_B_gt_0_5` column.\n"
    )
    c2 = cmp_[cmp_["split_half_sb"].notna()]
    L.append(md_table(c2, ["role", "intensity", "n_eligible", "split_half_sb", "split_half_sb_low",
                           "split_half_sb_high", "time_sb", "icc1", "oot_spearman", "oot_low",
                           "oot_players", "floor", "volume_spearman", "indicative_status"], 3) + "\n")  # fmt: skip
    L.append(
        "Reliability was computed for the primary intensity and for P1 and P2 (the remaining "
        "candidates were estimated without bootstrap and reliability to bound run time; they appear "
        "in the sensitivity table). Pass thresholds are those declared: split-half Spearman-Brown of "
        "at least 0.5 with a positive lower bound and a positive out-of-time lower bound for PROVISIONAL.\n"
    )
    L.append(
        "Sensitivity of the primary ordering (Spearman and Top-10 overlap with the primary):\n"
    )
    L.append(
        md_table(
            sens, ["role", "comparison", "n_common", "spearman", "top10_overlap", "n_eligible"], 3
        )
        + "\n"
    )
    L.append(
        "IPL and T20I combination study (declared rule: lower 95% bound of the cross-format correlation at least 0.3 and at least 30 players with both):\n"
    )
    L.append(md_table(fmt, ["role", "players_both_formats", "spearman", "spearman_low", "spearman_high",
                            "combination_supported", "combination_basis"], 3) + "\n")  # fmt: skip
    L.append(
        "Bootstrap check (fixed-variance draws against full refits; the full refit is used for every rank statistic):\n"
    )
    L.append(md_table(boot, ["role", "intensity", "draws", "players_compared", "max_abs_gap",
                             "fixed_variance_within_0_05"], 3) + "\n")  # fmt: skip
    L.append("## 8. Exploratory Top 10 by Approach B (not the submitted ranking)\n")
    L.append(
        "Ordered by the unshrunk pressure score of the B residual because the variance is at the floor. "
        "`top10_prob` is the share of 1000 match-cluster bootstrap draws in which the player is in the "
        "Top 10. The status of both lists under Approach B is EXPLORATORY; the lists are shown so the "
        "comparison chunk can contrast them with Approaches A and C, not as a recommendation.\n"
    )
    show = ["rank", "player_name", "estimate", "ci_low", "pressure_delta", "n_matches", "balls",
            "n_units", "top_k_prob", "rank_low", "rank_high", "evidence_class", "matches_ipl", "matches_t20i"]  # fmt: skip
    for r in ROLES:
        t = _top(est, r)
        L.append(f"### {r.title()}s\n")
        L.append(md_table(t, show, 3) + "\n")
        n_hi = int((t["top_k_prob"] >= 0.5).sum())
        n_sub = int((t["evidence_class"] == "STRONG_SUBSTANTIAL").sum())
        L.append(
            f"Of these ten, {n_hi} have a Top-10 inclusion probability of at least 0.5 and {n_sub} "
            f"are classed STRONG_SUBSTANTIAL. The median 95% rank interval spans "
            f"{_fmt(float((t['rank_high'] - t['rank_low']).median()), 0)} places, so the order within "
            "and around the list is not distinguishable from noise. Players near the eligibility floor "
            "can reach the top because the unshrunk mean of a few units is volatile; that is the "
            "reason shrinkage exists, and it cannot help here because the between-player variance "
            "estimate is zero.\n"
        )
        t2 = _top(est, r, 20, 11)
        L.append(f"Ranks 11 to 20 ({r}s):\n")
        L.append(md_table(t2, ["rank", "player_name", "estimate", "n_matches", "balls", "top_k_prob",
                               "evidence_class"], 3) + "\n")  # fmt: skip
        L.append(f"Evidence behind the top ten ({r}s): observed and expected WPA on pressure balls, "
                 "leverage, and leverage-weighted WPA per opportunity over all balls.\n")  # fmt: skip
        L.append(md_table(t, ["rank", "player_name", "obs_wpa", "exp_wpa_given_leverage",
                              "mean_leverage_pressure", "lw_wpa_per_opp", "normal_baseline",
                              "pressure_delta", "pos_share"], 4) + "\n")  # fmt: skip
        n = inel[inel["role"] == r]
        reasons = (
            n["failed_rules"]
            .value_counts()
            .head(6)
            .rename_axis("failed_rules")
            .reset_index(name="players")
        )
        L.append(
            f"Players excluded by the eligibility floors ({r}s): {len(n)}. Most frequent reasons:\n"
        )
        L.append(md_table(reasons, ["failed_rules", "players"], 0) + "\n")
    L.append("## 9. Status of Approach B\n")
    L.append(md_table(status, [c for c in ["role", "intensity", "intensity_basis", "indicative_list_status",
                                           "innings1_wp_gate_passed", "reason"] if c in status.columns], 3) + "\n")  # fmt: skip
    L.append(
        "Both lists are EXPLORATORY. The win-probability models pass the declared calibration and Brier "
        "gates on VALIDATION (innings 2 clearly, innings 1 less stably), so the technical pipeline works. "
        "That does not make the player ordering reliable: the player-level scores do not separate "
        "players beyond noise (the floor binds, split-half and out-of-time lower bounds are not above "
        "zero), exactly the Phase 6 conclusion.\n"
    )
    L.append("## 10. Leakage and integrity checks\n")
    L.append(
        "- `WP_before`, leverage and every feature are functions of one row's pre-delivery columns; tests "
        "show they are unchanged when later rows are truncated or when outcomes and the result label are "
        "mutated (`tests/test_phase8_winprob.py`).\n"
        "- Every fitted component (W1, W2, class model, WPA regression) is fitted on TRAIN only; TRAIN "
        "deliveries are scored by models that exclude their match; matches do not straddle partitions.\n"
        "- The TEST lock state and the protected-file hashes were checked at the start and end of each stage.\n"
        "- No external reference data source, player identity or rank is used as a feature.\n"
    )
    L.append("## 11. Limitations\n")
    L.append(
        "- Leverage uses next-ball classes of legal deliveries only; wides, no-balls and non-striker "
        "run-outs are credited through the attribution rules, not through leverage.\n"
        "- WPA credit mixes player skill with team and match state; the leverage regression removes the "
        "average effect of the state, not the quality of the partner or the opposition.\n"
        "- The innings-1 model is less stable out of fold than on VALIDATION (section 2).\n"
        "- The class model adds little over the class prior, so leverage differences come mainly from the "
        "win-probability surface.\n"
        "- Because the primary intensity is not validated, `pressure` here means the P4 resource-scarcity "
        "proxy, the best available and not a passing definition.\n"
        "- Declared changes: both opposing-team priors in the WP models; counterfactual instead of "
        "expected-share split; fixed class-model parameters; no isotonic recalibration.\n"
    )
    out = Path(path)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
