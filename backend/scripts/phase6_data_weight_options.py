"""Phase 6: legitimate data-weight improvement options, quantified against the unchanged 0.5 gate.

Writes ``p6_data_weight_options``, ``p6_data_weight_option_summary``, ``p6_data_weight_gate_status``
and ``phase6_data_weight_improvement_options.md/json/csv``. Options that lower the gate or change
the 0.5 requirement are not options and cannot appear (``validate_options_table``). No gate state is
written: ``passes_gate`` is informational and every failing context stays restricted. TEST rows are
never loaded, no lock event is created, Cricsheet is not an input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import (  # noqa: E402
    code_version,
    md_table,
    write_json_deterministic,
    write_text,
)
from app.phase4 import eligibility as el  # noqa: E402
from app.phase4 import engine as en  # noqa: E402
from app.phase4 import shrink as sh  # noqa: E402
from app.phase4.constants import SCOPE  # noqa: E402
from app.phase5 import context_stats as cs  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5 import pressure_signals as ps  # noqa: E402
from app.phase5 import reliability as rb  # noqa: E402
from app.phase5.constants import FROZEN_CHOICES, GATES_CONFIG, REPORTS_DIR  # noqa: E402
from app.phase6 import context_reliability as cr6  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import data_weight_options as dw  # noqa: E402
from app.phase6 import eligibility_reliability as er  # noqa: E402
from app.phase6 import split_half as sp  # noqa: E402
from app.phase6 import variance_floor as vf  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, STATUS  # noqa: E402
from app.phase6.lockguard import assert_lock_state_unchanged, assert_no_test_rows, lock_state  # noqa: E402
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_data_weight_improvement_options"
WATCHED = {"eligibility_rules": pl.ELIG_RULES, "gates": GATES_CONFIG, "frozen": FROZEN_CHOICES}
SHRINK = "shrink_tau4"
CTX = "context"


def _hash(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _scope(comp: str, role: str, phase: str, situation: str) -> str:
    return f"{CTX}:{comp}|{role}|{phase}|{situation}"


def read_tables(store: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str] | None]:
    con = duckdb.connect(str(store), read_only=True)
    try:
        stats = con.execute("SELECT * FROM p5_context_stats").df()
        rules = con.execute("SELECT * FROM p5_context_eligibility_rules").df()
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name='p6_definition_outcome'"
        ).fetchone()[0]
        pass_list = None
        if has:
            o = con.execute("SELECT * FROM p6_definition_outcome WHERE \"window\" = 'FINAL'").df()
            pass_list = json.loads(o["pass_list"].iloc[0]) if len(o) else None
    finally:
        con.close()
    return stats, rules, pass_list


def build_contexts(stats, rules, n_boot: int, seed: int) -> dict[tuple, dict]:
    gm, W = cs.global_match_weights(stats, n_boot, seed)
    out = {}
    for key in vf.context_keys():
        comp, role, phase, situation = key
        rr = rules[(rules["comp"] == comp) & (rules["role"] == role) & (rules["phase"] == phase)
                   & (rules["situation"] == situation)].iloc[0]  # fmt: skip
        sub = cs.select(stats, comp, role, phase, situation)
        cd, cell = vf.cd_from_context(sub)
        if cd is None:
            continue
        assert_no_test_rows(sub)
        rec = cr6.eligibility_recompute(cell, rr, SHRINK)
        out[key] = {"cd": cd, "cell": cell, "rec": rec, "rule": rr,
                    "w": en.cell_weights(cell, gm, W), "mask": sp.window_mask(cd, "PRE_TEST")}  # fmt: skip
    return out


# ---------------------------------------------------------------- options
def o1_definition(study, defns: list[str], pass_list: list[str] | None) -> list[dict]:
    rows = []
    base: dict[tuple, float] = {}
    for defn in ["any|q0.75"] + [d for d in defns if d != "any|q0.75"]:
        prim = study.primary_cells(defn)
        rules = study.frozen_rules(prim)
        for (comp, role), cell in sorted(prim.items()):
            fit = cell.fit()
            k = float(sh.k_for(fit, SHRINK)["k"])
            est = en.point_estimates(cell, fit, SHRINK)
            rule = rules[(comp, role)]
            elig = el.eligible_mask(est, {"threshold_balls": rule["threshold_balls"]}, rule["wr"])
            s = dw.kish_stats(est, elig, k)
            if defn == "any|q0.75":
                base[(comp, role)] = s.get("data_weight")
            on = "not available" if pass_list is None else ("yes" if defn in pass_list else "no")
            rows.append(dw.option_row(
                option_id="O1_" + defn.replace("|", "_"), option_group="definition choice",
                label="ACTUAL_RE_ESTIMATE", scope=f"cell:{comp}|{role}", window="PRE_TEST",
                n_eff_marginal=s.get("n_eff_marginal"), k_used=k, k_source="PHASE4_FLOOR_TAU4",
                data_weight=s.get("data_weight"), data_weight_lo=None, data_weight_hi=None,
                passes_gate=bool(s.get("data_weight") is not None and s["data_weight"] >= dw.GATE),
                extra_n_eff_required=s.get("extra_n_eff_required"),
                extra_matches_required=s.get("extra_matches_required"),
                pool_size_after=s.get("eligible"), baseline_data_weight=base.get((comp, role)),
                notes=f"definition {defn}; frozen threshold {rule['threshold_balls']} balls scaled "
                f"by {rule['wr']:.3f}; on the criteria pass list: {on}; baseline is any|q0.75",
            ))  # fmt: skip
    return rows


def o2_multi_format(study, defn: str) -> list[dict]:
    rows = []
    prim = study.primary_cells(defn)
    rules = study.frozen_rules(prim)
    for role in ("batter", "bowler"):
        a, b = prim.get(("IPL", role)), prim.get(("T20I", role))
        if a is None or b is None:
            continue
        cda, cdb = rb.from_cell(a), rb.from_cell(b)
        a_s, b_s, pooled, _ = rb.pool_cells(cda, cdb, "PRE_TEST")
        scope = f"role:{role}"
        if len(pooled.players) == 0:
            continue
        thr = max(rules[("IPL", role)]["threshold_balls"] * rules[("IPL", role)]["wr"],
                  rules[("T20I", role)]["threshold_balls"] * rules[("T20I", role)]["wr"])  # fmt: skip
        tot = pooled.N.sum(1)
        elig = tot >= thr
        tr = pooled.period == "TRAIN"
        fit = vf.fit_from_cd(pooled.select_cols(tr))
        k = float(sh.k_for(fit, SHRINK)["k"])
        est = pd.DataFrame({"n_eff": er.kish_n_eff(pooled.N), "matches": (pooled.N > 0).sum(1)})
        s = dw.kish_stats(est, elig, k)
        single = er.kish_n_eff(a_s.N)[elig]
        base_b = float((single / (single + k)).min()) if elig.any() and k > 0 else None
        mf = rb.multi_format_pooling(cda, cdb, "PRE_TEST", 6, 10)
        rows.append(dw.option_row(
            option_id="O2_multi_format_pooling", option_group="multi-format pooling",
            label="ACTUAL_RE_ESTIMATE", scope=scope, window="PRE_TEST",
            n_eff_marginal=s.get("n_eff_marginal"), k_used=k, k_source="PHASE4_FLOOR_TAU4",
            data_weight=s.get("data_weight"),
            passes_gate=bool(s.get("data_weight") is not None and s["data_weight"] >= dw.GATE),
            extra_n_eff_required=s.get("extra_n_eff_required"),
            extra_matches_required=s.get("extra_matches_required"),
            pool_size_after=s.get("eligible"), baseline_data_weight=base_b,
            notes=f"players with balls in both formats: {len(pooled.players)}; pooled eligibility "
            f"= pooled balls >= {thr:.2f} (larger of the two scaled frozen thresholds); baseline is "
            f"the same players on first-format data only (IPL); pooled vs single-format odd/even SB "
            f"on the same players: {mf.get('sb_pooled')} vs {mf.get('sb_first_format')}/"
            f"{mf.get('sb_second_format')}",
        ))  # fmt: skip
    return rows


def o3_o6_o4_o7_o8(ctxs: dict, n_draws: int, min_pool: int) -> tuple[list[dict], pd.DataFrame]:
    rows: list[dict] = []
    tau: dict[tuple, dict] = {}
    for key, c in ctxs.items():
        tau[key] = dw.tau2_estimates(c["cd"], c["w"], c["mask"], n_draws)
    tau_rows = []
    for (comp, role, phase, situation), t in tau.items():
        tau_rows.append({"format": comp, "role": role, "phase": phase, "situation": situation,
                         "window": "PRE_TEST", **t})  # fmt: skip
    for key, c in ctxs.items():
        comp, role, phase, situation = key
        rec = c["rec"]
        scope = _scope(*key)
        elig = rec["elig"]
        k = float(rec["kinfo"]["k"])
        base_b = rec.get("marginal_b")
        inp = dw.cluster_inputs(c["cd"], c["mask"])
        v_el = inp["v"][elig]
        n_el, n_single = int(elig.sum()), int((elig & ~np.isfinite(inp["v"])).sum())
        # O6: own-context match-cluster REML tau2
        own = tau[key]
        for oid, grp, src, label in (("O6_match_cluster_own_tau2", "match-cluster tau2", own,
                                      "MATCH_CLUSTER_REML_OWN_CONTEXT"),):  # fmt: skip
            b = dw.cluster_b(src.get("tau2_reml"), v_el, own.get("sigma_eff"))
            blo = dw.cluster_b(src.get("tau2_lo"), v_el, own.get("sigma_eff"))
            bhi = dw.cluster_b(src.get("tau2_hi"), v_el, own.get("sigma_eff"))
            rows.append(
                _cluster_row(
                    oid,
                    grp,
                    label,
                    scope,
                    b,
                    blo,
                    bhi,
                    base_b,
                    own,
                    n_el,
                    n_single,
                    "own context REML",
                )
            )
        # O3: tau2 borrowed from a parent context
        for kind in ("phases_pooled", "situations_pooled"):
            par = dw.parent_of(phase, situation, kind)
            if par is None:
                continue
            pk = (comp, role, par[0], par[1])
            if pk not in tau or tau[pk].get("status") != "ESTIMATED":
                continue
            pt = tau[pk]
            b = dw.cluster_b(pt.get("tau2_reml"), v_el, own.get("sigma_eff"))
            blo = dw.cluster_b(pt.get("tau2_lo"), v_el, own.get("sigma_eff"))
            bhi = dw.cluster_b(pt.get("tau2_hi"), v_el, own.get("sigma_eff"))
            rows.append(
                _cluster_row(
                    f"O3_{kind}",
                    "partial pooling across contexts",
                    "MATCH_CLUSTER_REML_POOLED_CONTEXT",
                    scope,
                    b,
                    blo,
                    bhi,
                    base_b,
                    pt,
                    n_el,
                    n_single,
                    f"tau2 from parent {par[0]}|{par[1]} ({kind.replace('_', ' ')})",
                )
            )
        # O4: window length (TRAIN only versus the full PRE_TEST window)
        cell = c["cell"]
        thr = rec["threshold_balls"]
        tr = cell.match_period == "TRAIN"
        n_tr = cell.N[:, tr].sum(1)
        ne_tr = er.kish_n_eff(cell.N[:, tr])
        el_tr = (n_tr >= thr) & (n_tr > 0) if thr is not None else np.zeros(len(n_tr), dtype=bool)
        b_tr = (
            float(ne_tr[el_tr].min() / (ne_tr[el_tr].min() + k)) if el_tr.any() and k > 0 else None
        )
        rows.append(dw.option_row(
            option_id="O4_window_train_to_pre_test", option_group="longer window",
            label="ACTUAL_RE_ESTIMATE", scope=scope, window="PRE_TEST",
            n_eff_marginal=rec.get("marginal_n_eff"), k_used=k, k_source="PHASE4_FLOOR_TAU4",
            data_weight=base_b, passes_gate=bool(base_b is not None and base_b >= dw.GATE),
            extra_n_eff_required=max(0.0, k - rec["marginal_n_eff"]) if "marginal_n_eff" in rec else None,
            pool_size_after=rec["eligible_players"], baseline_data_weight=b_tr,
            notes=f"baseline is the TRAIN-only window ({int(el_tr.sum())} eligible at the "
            f"unscaled threshold); the current window adds the VALIDATION matches; windows beyond "
            f"the available data are not observable, see O7",
        ))  # fmt: skip
        # O7: required-sample projection
        ks = dw.kish_stats(_est_frame(rec), elig, k)
        typical = (k / float(np.median(rec["est"]["n_eff"].to_numpy()[elig]
                                      / np.maximum(rec["est"]["matches"].to_numpy()[elig], 1)))
                   if elig.any() else None)  # fmt: skip
        rows.append(dw.option_row(
            option_id="O7_required_sample_projection", option_group="required sample",
            label="DESCRIPTIVE_PROJECTION", scope=scope, window="PRE_TEST",
            n_eff_marginal=ks.get("n_eff_marginal"), k_used=k, k_source="PHASE4_FLOOR_TAU4",
            data_weight=base_b, passes_gate=bool(base_b is not None and base_b >= dw.GATE),
            extra_n_eff_required=ks.get("extra_n_eff_required"),
            extra_matches_required=ks.get("extra_matches_required"),
            pool_size_after=rec["eligible_players"], baseline_data_weight=base_b,
            notes=f"B = 0.5 iff n_eff = k; the extra matches are for the marginal individual at his "
            f"own n_eff per match ({ks.get('marginal_matches')} matches now); typical individual "
            f"needs about {None if typical is None else round(typical, 1)} matches in total; "
            f"the context holds "
            f"{int(c['cd'].N.shape[1])} matches; eligible individuals already at n_eff >= k: "
            f"{ks.get('pool_n_eff_at_least_k')}",
        ))  # fmt: skip
        # O8: pool restriction (shows the cost; not applicable)
        ne = rec["est"]["n_eff"].to_numpy()[elig]
        left = int((ne >= k).sum())
        b8 = float(ne[ne >= k].min() / (ne[ne >= k].min() + k)) if left else None
        rows.append(dw.option_row(
            option_id="O8_pool_restriction_cost", option_group="pool restriction",
            label="DESCRIPTIVE_PROJECTION", scope=scope, window="PRE_TEST",
            n_eff_marginal=float(ne[ne >= k].min()) if left else None, k_used=k,
            k_source="PHASE4_FLOOR_TAU4", data_weight=b8,
            passes_gate=bool(left >= min_pool and b8 is not None and b8 >= dw.GATE),
            pool_size_after=left, baseline_data_weight=base_b, applicable=False,
            notes=f"individuals left if the pool is restricted to n_eff >= k (B >= 0.5 holds by "
            f"construction); a pool below the provisional minimum of {min_pool} is not a ranking; "
            "reported only to show the cost, not applicable as an option",
        ))  # fmt: skip
    return rows, pd.DataFrame(tau_rows)


def _est_frame(rec: dict) -> pd.DataFrame:
    return rec["est"][["n_eff", "matches"]]


def _cluster_row(oid, grp, k_source, scope, b, blo, bhi, base_b, tinfo, n_el, n_single, what):
    ok = b.get("status") == "ESTIMATED"
    k_used = b.get("k_used")
    marg = b.get("n_eff_marginal")
    extra = max(0.0, k_used - marg) if ok and k_used is not None and marg is not None else None
    on_subset = bool(ok and b["data_weight"] >= dw.GATE)
    # the gate is about the least-experienced eligible individual: when some eligible
    # individuals have no cluster-noise estimate (one match) the marginal individual is not
    # estimable, so the context cannot be shown to pass
    complete = n_single == 0
    return dw.option_row(
        estimate_status="ESTIMATED" if (ok and complete) else
        ("MARGINAL_INDIVIDUAL_NOT_ESTIMABLE" if ok else "NOT_ESTIMABLE"),
        passes_on_estimable_subset=on_subset,
        option_id=oid, option_group=grp, label="ACTUAL_RE_ESTIMATE", scope=scope,
        window="PRE_TEST", n_eff_marginal=marg, k_used=k_used, k_source=k_source,
        data_weight=b.get("data_weight"), data_weight_lo=blo.get("data_weight"),
        data_weight_hi=bhi.get("data_weight"),
        passes_gate=bool(on_subset and complete),
        extra_n_eff_required=extra, extra_matches_required=None, pool_size_after=n_el,
        requires_methodology_decision=True, n_eff_basis="MATCH_CLUSTER", baseline_data_weight=base_b,
        notes=f"{what}: tau2 REML {tinfo.get('tau2_reml')}, bootstrap [{tinfo.get('tau2_lo')}, "
        f"{tinfo.get('tau2_hi')}] ({tinfo.get('boot_draws')} draws, share positive "
        f"{tinfo.get('boot_share_positive')}), MAD {tinfo.get('tau2_mad')}; eligible players "
        f"used {b.get('players_used')} of {n_el} ({n_single} with one match have no cluster noise); "
        "a different shrinkage methodology: needs a user decision before any use",
    )  # fmt: skip


def o5_bowler_signals(study) -> list[dict]:
    rows = []
    cfg = study.cfg["bowler_signal_candidates"]
    built = ps.build_flags(study.d, cfg)
    base = study.base("bowler", "charged")
    for cid, (flag, pop, _) in built.items():
        press = ps.candidate_pressure_rows(base, flag, pop)
        for comp in SCOPE:
            cell = en.build_cell(press, comp, "bowler", "charged")
            if cell is None:
                continue
            assert_no_test_rows(cell.rows)
            fit = cell.fit()
            k = float(sh.k_for(fit, SHRINK)["k"])
            est = en.point_estimates(cell, fit, SHRINK)
            wr = el.window_ratio(cell, ("TRAIN", "VALIDATION"), "TRAIN")
            thr = study.frozen["eligibility"][f"{comp}|bowler"]["analysis"]["threshold_balls"]
            elig = el.eligible_mask(est, {"threshold_balls": thr}, wr)
            s = dw.kish_stats(est, elig, k)
            rows.append(dw.option_row(
                option_id=f"O5_{cid}", option_group="bowler-specific signal (sensitivity)",
                label="ACTUAL_RE_ESTIMATE", scope=f"cell:{comp}|bowler", window="PRE_TEST",
                n_eff_marginal=s.get("n_eff_marginal"), k_used=k, k_source="PHASE4_FLOOR_TAU4",
                data_weight=s.get("data_weight"),
                passes_gate=bool(s.get("data_weight") is not None and s["data_weight"] >= dw.GATE),
                extra_n_eff_required=s.get("extra_n_eff_required"),
                extra_matches_required=s.get("extra_matches_required"),
                pool_size_after=s.get("eligible"),
                notes="SENSITIVITY_ONLY, never feeds the API or any ranking; the frozen bowler "
                f"threshold ({thr} balls, scaled by {wr:.3f}) is applied to a different pressure "
                f"sample ({int(cell.N.sum())} balls, {len(cell.players)} bowlers)",
            ))  # fmt: skip
    return rows


def gate_status(opts: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    """Per context: stored Phase 5 gate state plus the data weight and pass flag of each option."""
    ctx = opts[opts["scope"].str.startswith(CTX + ":")].copy()
    ctx["key"] = ctx["scope"].str.split(":", n=1).str[1]
    out = rules[["comp", "role", "phase", "situation", "marginal_n_eff_eligible", "k",
                 "marginal_data_weight", "data_weight_gate_passed"]].copy()  # fmt: skip
    out["key"] = out["comp"] + "|" + out["role"] + "|" + out["phase"] + "|" + out["situation"]
    out["gate_used"] = dw.GATE
    out["stored_state"] = np.where(
        out["data_weight_gate_passed"].astype(bool), "PASS", "RESTRICTED"
    )
    for oid, g in ctx.groupby("option_id"):
        m = g.set_index("key")
        out[f"b_{oid}"] = out["key"].map(m["data_weight"])
        out[f"pass_{oid}"] = (
            out["key"].map(m["passes_gate"]).astype("boolean").fillna(False).astype(bool)
        )
    flags = [c for c in out.columns if c.startswith(("pass_O3", "pass_O6"))]
    out["any_methodology_option_passes"] = out[flags].any(axis=1) if flags else False
    return out.drop(columns=["key"])


def render(res: dict) -> str:
    opts, summ, tau = res["options"], res["summary"], res["tau"]
    ctx = opts[opts["scope"].str.startswith(CTX + ":")]
    L = [
        "# Phase 6 data-weight improvement options",
        "",
        f"Status: {STATUS}. INTERNAL, in-sample on TRAIN and VALIDATION. TEST outcomes: not used. "
        f"Cricsheet: not used. **The data-weight gate is `GATE_B` = {dw.GATE} in every row "
        "(`gate_used`); it was not lowered, bypassed, re-defined or tuned, and no option below "
        "changes it.** No gate state is written: `passes_gate` is informational, and every context "
        "that fails stays restricted. "
        f"Code version `{res['code_version'][:16]}`, seed {res['seed']}, {res['n_boot']} match "
        f"resamples, {res['reml_draws']} REML bootstrap draws. Step run-log seq "
        f"{res['criteria']['seq']} (criteria SHA-256 `{res['criteria']['sha256']}` verified).",
        "",
        "## 1. How to read this",
        "- Data weight is `B = n_eff / (n_eff + k)` of the marginal (least-experienced) eligible "
        "individual; the gate needs `B >= 0.5`. On the Phase 4 basis (`KISH_MATCH`) `n_eff` is the "
        "Kish count over per-match ball counts and `k = 25` (the shrinkage floor under "
        "`shrink_tau4`); B = 0.5 iff `n_eff = k`. On the match-cluster basis (`MATCH_CLUSTER`) "
        "`B_i = tau2 / (tau2 + v_i)` with `v_i` the cluster-robust noise variance of the "
        "individual's mean; this equals `n_eff_cluster / (n_eff_cluster + k)` with `k = sigma_eff "
        "/ tau2`. The two bases are never mixed (the validator rejects it).",
        "- `ACTUAL_RE_ESTIMATE`: recomputed from the data under the stated change. "
        "`DESCRIPTIVE_PROJECTION`: arithmetic on the observed numbers, not a re-fit.",
        "- Options marked `requires_methodology_decision` change the shrinkage methodology (a "
        "data-based `tau2` instead of the floor). A pass under them would still leave the context "
        "restricted until the user approves a methodology change. This report changes nothing.",
        "- Everything is in-sample; the match-cluster bootstrap is shifted upward relative to the "
        "point estimate (see the variance report), so interval bounds are rough bands.",
        "",
        "## 2. Excluded by rule (not options, not in the table)",
        *[f"- {x}" for x in dw.EXCLUDED_BY_RULE],
        "",
        "## 3. Summary per option",
        "",
        md_table(
            [
                "option",
                "group",
                "label",
                "scope",
                "rows",
                "with estimate",
                "pass 0.5",
                "pass on estimable subset",
                "marginal not estimable",
                "best B",
                "median B",
                "needs decision",
                "basis",
            ],
            rows_of(
                summ,
                [
                    "option_id",
                    "option_group",
                    "label",
                    "scope_kind",
                    "rows",
                    "rows_with_estimate",
                    "rows_passing_gate",
                    "rows_passing_on_estimable_subset",
                    "rows_marginal_not_estimable",
                    "best_data_weight",
                    "median_data_weight",
                    "requires_methodology_decision",
                    "n_eff_basis",
                ],
            ),
        ),
        "",
        "Scopes that pass the gate under each option (informational):",
        "",
        *[f"- `{r.option_id}`: {r.passing_scopes}" for r in summ.itertuples()],
        "",
        "## 4. Context-level view (48 contexts): data weight of the marginal eligible individual",
        "`stored` is the Phase 5 state (Phase 4 basis, floor `k`). O3 and O6 use the match-cluster "
        "basis. O4's comparison column is the TRAIN-only window. O8 is the number of eligible "
        "individuals left if the pool were restricted to `n_eff >= k`; it is not applicable.",
        "",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "stored B",
                "O3 phases",
                "O3 situations",
                "O6 own",
                "O4 TRAIN-only B",
                "O7 extra matches",
                "O8 pool left",
            ],
            _context_table(ctx),
        ),
        "",
        "## 5. Cell-level options (definition, multi-format pooling, bowler signals)",
        "",
        md_table(
            [
                "option",
                "scope",
                "marginal n_eff",
                "k",
                "B",
                "baseline B",
                "passes",
                "eligible",
                "extra matches",
            ],
            rows_of(
                opts[~opts["scope"].str.startswith(CTX + ":")].sort_values(["option_id", "scope"]),
                [
                    "option_id",
                    "scope",
                    "n_eff_marginal",
                    "k_used",
                    "data_weight",
                    "baseline_data_weight",
                    "passes_gate",
                    "pool_size_after",
                    "extra_matches_required",
                ],
            ),
        ),
        "",
        "## 6. Match-cluster `tau2` per context (REML, with bootstrap and a robust MAD check)",
        "",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "players",
                "sigma_eff",
                "tau2 REML",
                "lo",
                "hi",
                "share positive",
                "tau2 MAD",
            ],
            rows_of(
                tau,
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "players",
                    "sigma_eff",
                    "tau2_reml",
                    "tau2_lo",
                    "tau2_hi",
                    "boot_share_positive",
                    "tau2_mad",
                ],
            ),
        ),
        "",
        "## 7. Reading the numbers",
        res["reading"],
        "",
        "## 8. Limits and open decisions",
        "- No option lowers the gate; none was evaluated. Where no row passes, the finding is that "
        "the gate is not reachable by these legitimate means with the data in hand.",
        "- O3 and O6 need a methodology decision (a data-based `tau2` and the match-cluster "
        "basis instead of the floor). That decision is the user's; this report does not make it.",
        "- O3 borrows `tau2` from a parent context (phases pooled or situations pooled) and "
        "assumes the same between-player variance in the member context. It is an empirical-Bayes "
        "hyperparameter pooling, not a full hierarchical model.",
        "- The extra matches in O7 are per marginal individual, not data to be collected for the "
        "context; they show the size of the gap.",
        "- A match-cluster `tau2` of zero gives `B = 0` and no finite `k`; this is reported, not "
        "repaired.",
        "- In-sample only: TEST was opened once in Phase 4 and is not pristine; nothing here is "
        "validation.",
        "",
    ]
    return "\n".join(L)


def _context_table(ctx: pd.DataFrame) -> list[list]:
    rows = []
    piv = {oid: g.set_index("scope") for oid, g in ctx.groupby("option_id")}
    seen = ctx[ctx["option_id"] == "O7_required_sample_projection"].sort_values("scope")
    for s in seen["scope"]:
        comp, role, phase, situation = s.split(":", 1)[1].split("|")
        get = lambda oid, col: piv[oid].loc[s, col] if oid in piv and s in piv[oid].index else None  # noqa: E731
        rows.append([comp, role, phase, situation, get("O7_required_sample_projection", "data_weight"),
                     get("O3_phases_pooled", "data_weight"), get("O3_situations_pooled", "data_weight"),
                     get("O6_match_cluster_own_tau2", "data_weight"),
                     get("O4_window_train_to_pre_test", "baseline_data_weight"),
                     get("O7_required_sample_projection", "extra_matches_required"),
                     get("O8_pool_restriction_cost", "pool_size_after")])  # fmt: skip
    return [[None if (isinstance(v, float) and np.isnan(v)) else v for v in r] for r in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=None)
    ap.add_argument("--reml-draws", type=int, default=300)
    args = ap.parse_args(argv)
    t0 = time.time()
    rep, store = args.reports, args.store
    guard = Preservation(rep)
    lock_before = lock_state()
    p4_before, p5_before = table_hashes(store, "p4_"), table_hashes(store, "p5_")
    watched_before = {k: _hash(v) for k, v in WATCHED.items()}
    if el.GATE_B != 0.5:
        print("FATAL: GATE_B is not 0.5")
        return 1
    try:
        info = cr.begin_step("data_weight_options", store_path=store)
    except cr.CriteriaError as e:
        print(f"REFUSED: {e}")
        return 1
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    n_boot = int(args.n_boot or cfg["n_boot"])
    seed = int(cfg["seed"])
    stats, rules, pass_list = read_tables(store)
    cs.check_stats(stats)
    study = pl.load_study(store, n_boot=n_boot, seed=seed)
    min_pool = int(study.cfg["stability"]["min_pool_for_stability"])
    ctxs = build_contexts(stats, rules, n_boot, seed)
    rows = o1_definition(study, cfg["definitions"]["candidates"], pass_list)
    rows += o2_multi_format(study, cfg["definitions"]["provisional"])
    r2, tau = o3_o6_o4_o7_o8(ctxs, int(args.reml_draws), min_pool)
    rows += r2
    rows += o5_bowler_signals(study)
    opts = pd.DataFrame(rows)
    dw.validate_options_table(opts)
    summ = dw.summarize(opts)
    gs = gate_status(opts, rules)
    if (gs["gate_used"] != 0.5).any():
        print("FATAL: gate_used differs from 0.5")
        return 1
    if {k: _hash(v) for k, v in WATCHED.items()} != watched_before:
        print("FATAL: a watched configuration file changed")
        return 1
    max_ne = max(float(c["rec"]["est"]["n_eff"].max()) for c in ctxs.values())
    cl = opts[opts["option_id"].str.startswith(("O3_", "O6_")) & opts["data_weight"].notna()]
    best_cluster = float(cl["data_weight"].max()) if len(cl) else float("nan")
    n_cluster_est, n_cluster_zero = int(len(cl)), int((cl["data_weight"] <= 0).sum())
    t_ok = tau[tau["status"] == "ESTIMATED"]
    n_dis = int(((t_ok["tau2_mad"] <= 0) & (t_ok["tau2_reml"] > 0)).sum())
    n_lo0 = int((t_ok["tau2_lo"] <= 1e-12).sum())
    n_subset = int(summ["rows_passing_on_estimable_subset"].sum())
    n_unest = int(summ["rows_marginal_not_estimable"].sum())
    n_pass = {r.option_id: int(r.rows_passing_gate) for r in summ.itertuples()}
    applicable = summ[~summ["option_id"].str.startswith("O8")]
    applicable_pass = int(applicable["rows_passing_gate"].sum())
    stored_pass = int(rules["data_weight_gate_passed"].astype(bool).sum())
    reading = "\n".join(
        [
            f"- Stored Phase 5 state: {stored_pass} of {len(rules)} contexts pass the gate "
            f"(marginal n_eff {rules['marginal_n_eff_eligible'].min():.2f} to "
            f"{rules['marginal_n_eff_eligible'].max():.2f}, k = {rules['k'].min():.0f} to "
            f"{rules['k'].max():.0f}).",
            f"- Rows passing the gate across all options except the pool-restriction cost (O8): "
            f"{applicable_pass} of {int(applicable['rows'].sum())}. By option: "
            + ", ".join(f"{k} {v}" for k, v in sorted(n_pass.items()) if not k.startswith("O8"))
            + ".",
            f"- O8 (restrict to n_eff >= k): pools left per context range "
            f"{int(opts[opts['option_id'] == 'O8_pool_restriction_cost']['pool_size_after'].min())} to "
            f"{int(opts[opts['option_id'] == 'O8_pool_restriction_cost']['pool_size_after'].max())}; "
            f"{n_pass.get('O8_pool_restriction_cost', 0)} contexts keep at least {min_pool} "
            "individuals. It passes only by removing nearly everyone, so it is not an option.",
            "- Under the Phase 4 basis the gate is a statement about the least-experienced eligible "
            "individual having about k = 25 matches' worth of pressure data (n_eff = k). The largest "
            f"Kish count of any individual in the 48 contexts is {max_ne:.1f}.",
            f"- Under the match-cluster basis (O3, O6) the best marginal data weight of any context "
            f"is {best_cluster:.3f} (O3 and O6 rows with an estimate: {n_cluster_est}); "
            f"{n_cluster_zero} of those rows rest on a `tau2` that is zero. {n_subset} O3/O6 "
            f"rows would pass on the individuals that have a cluster-noise estimate, but "
            f"{n_unest} rows have eligible individuals with a single match and no such estimate, "
            "so the marginal individual is not estimable and they are not counted as passing.",
            f"- Robustness of the match-cluster `tau2`: in {n_dis} of {len(t_ok)} contexts the "
            "REML estimate is positive while the MAD-based estimate is 0, and the REML bootstrap "
            f"lower bound is 0 in {n_lo0}. The `tau2` behind O3 and O6 is therefore not "
            "firmly identified (see the variance report), so even a pass would be fragile.",
        ]
    )
    res = {"options": opts, "summary": summ, "gate_status": gs, "tau": tau, "criteria": info,
           "seed": seed, "n_boot": n_boot, "reml_draws": int(args.reml_draws),
           "code_version": code_version(), "reading": reading}  # fmt: skip
    meta = {"fit_on": "WINDOW_IN_SAMPLE", "seed": seed, "n_boot": n_boot,
            "criteria_sha256": info["sha256"]}  # fmt: skip
    cr.verify_criteria(store_path=store)
    for df, nm, tb in ((opts, NAME, "p6_data_weight_options"),
                       (summ, f"{NAME}_summary", "p6_data_weight_option_summary"),
                       (gs, f"{NAME}_gate_status", "p6_data_weight_gate_status"),
                       (tau, f"{NAME}_cluster_tau2", "p6_data_weight_cluster_tau2")):  # fmt: skip
        out = df.copy()
        for k_, v_ in meta.items():
            out[k_] = v_
        save_table(out, nm, rep, store, tb)
    write_text(rep / f"{NAME}.md", render(res))
    guard_files = {"app/phase4/eligibility.py": ROOT / "app" / "phase4" / "eligibility.py",
                   "config/phase5_gates_v1.json": GATES_CONFIG,
                   "config/pressure_eligibility_rules_v1.json": pl.ELIG_RULES,
                   "data/reports/phase4_frozen_choices.json": FROZEN_CHOICES}  # fmt: skip
    write_json_deterministic(
        rep / "phase6_gate_guard.json",
        {"status": STATUS, "gate_value": el.GATE_B, "gate_used_in_options": sorted(
            {float(x) for x in opts["gate_used"]}),
         "files_sha256": {k: _hash(v) for k, v in guard_files.items()}},
    )  # fmt: skip
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "option_rows": len(opts),
                      "applicable_rows_passing": applicable_pass, "by_option": n_pass,
                      "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
