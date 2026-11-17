"""Phase 6: eligibility thresholds under the reliability lens (descriptive, thresholds untouched).

Writes ``p6_eligibility_reliability``, ``p6_eligibility_targets``, ``p6_eligibility_projection``,
``p6_eligibility_n_eff`` and ``phase6_eligibility_reliability.md/json/csv``. The eligibility rules,
the gate configuration and the frozen choices are hashed before and after and must not change.
TEST rows are never loaded, no lock event is created, Cricsheet is not an input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, md_table, write_text  # noqa: E402
from app.phase4 import engine as en  # noqa: E402
from app.phase4 import shrink as sh  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5 import reliability as rb  # noqa: E402
from app.phase5.constants import FROZEN_CHOICES, GATES_CONFIG, REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import eligibility_reliability as er  # noqa: E402
from app.phase6 import split_half as sp  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, STATUS  # noqa: E402
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_eligibility_reliability"
WATCHED = {"eligibility_rules": pl.ELIG_RULES, "gates": GATES_CONFIG, "frozen": FROZEN_CHOICES}
WINDOWS = ("PRE_TEST", "TRAIN")


def _hash(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_candidates(store: Path) -> pd.DataFrame:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return con.execute("SELECT * FROM p4_eligibility_candidates").df()
    finally:
        con.close()


def render(res: dict) -> str:
    lad, tg, pj, ne, cand, xc = (
        res[k] for k in ("ladder", "targets", "proj", "n_eff", "cand", "xcheck")
    )
    pre = lad[(lad["window"] == "PRE_TEST") & (lad["source"] == "ladder")]
    L = [
        "# Phase 6 eligibility thresholds under the reliability lens",
        "",
        f"Status: {STATUS}. INTERNAL, descriptive, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. "
        "TEST outcomes: not used. Cricsheet: not used. **No threshold was changed and the 0.5 "
        f"data-weight gate (read from `GATE_B` = {er.GATE}) was not lowered, bypassed or "
        "re-defined.** The frozen thresholds stay as they are; this report only shows what "
        f"reliability and data weight look like at other thresholds. Code version "
        f"`{res['code_version'][:16]}`, seed {res['seed']}, {res['n_boot']} bootstrap draws. "
        f"Definition `{res['definition']}`, primary streams. Step run-log seq "
        f"{res['criteria']['seq']} (criteria SHA-256 `{res['criteria']['sha256']}` verified).",
        "",
        "## 1. Preconditions",
        f"- SHA-256 of the eligibility rules, the gate configuration and the frozen choices is "
        f"unchanged: {res['hash_check']}.",
        f"- Ladder reliability reproduces `reliability_by_opportunity` of Phase 5 "
        f"(PRE_TEST odd/even, {xc['compared']} steps compared, max abs difference "
        f"{xc['max_abs_diff']:.2e}).",
        f"- `k` from the TRAIN fit under `shrink_tau4`: "
        f"{json.dumps(res['k_by_cell'], sort_keys=True)} (floor hit in every cell).",
        "",
        "## 2. Reliability by minimum pressure balls (PRE_TEST, Phase 5 ladders)",
        "Each row is the pool of individuals with at least `t` pressure balls in the window. "
        "`B marg.` is the data weight of the least-experienced individual in the pool (Kish "
        "`n_eff` over match ball counts, `k` as above); `B med.` is the median individual's. "
        "Pools shrink as `t` rises, so the figures describe different individuals at each row "
        "(a selection effect, not a pure effect of sample size).",
        "",
    ]
    for (f, r), g in pre.groupby(["format", "role"]):
        L += [f"### {f} {r}", "",
              md_table(["t balls", "pool", "estimable", "SB", "lo (indiv.)", "hi (indiv.)",
                        "lo (matches)", "hi (matches)", "marg. n_eff", "median n_eff", "B marg.",
                        "B med."],
                       rows_of(g.sort_values("min_total_balls"),
                               ["min_total_balls", "players_ge_t", "players_estimable", "sb",
                                "sb_lo_players", "sb_hi_players", "sb_lo_matches",
                                "sb_hi_matches", "marginal_n_eff", "median_n_eff", "b_marginal",
                                "b_median"])), ""]  # fmt: skip
    L += [
        "## 3. Smallest ladder step at which reliability reaches the target",
        "Point estimate, and the step at which the interval lower bound reaches the target "
        "(individual bootstrap, match bootstrap). 'none' means the target is not reached within "
        "the ladder. A lower bound is the conservative reading; the match-bootstrap interval is "
        "not centred on the point estimate.",
        "",
        md_table(
            [
                "format",
                "role",
                "window",
                "target",
                "status",
                "point",
                "lo (indiv.)",
                "lo (matches)",
            ],
            rows_of(
                tg,
                [
                    "format",
                    "role",
                    "window",
                    "target",
                    "status",
                    "min_balls_point",
                    "min_balls_lo_players",
                    "min_balls_lo_matches",
                ],
            ),
        ),
        "",
        "## 4. Frozen thresholds and Phase 4 candidates under the same lens (PRE_TEST)",
        "The frozen thresholds are scaled by the window ratio exactly as in Phase 4 and 5. "
        "Candidate rows come from `p4_eligibility_candidates`; each is evaluated at its stored "
        "scaled threshold.",
        "",
        md_table(
            [
                "format",
                "role",
                "source",
                "threshold (TRAIN scale)",
                "scaled t",
                "pool",
                "estimable",
                "SB",
                "lo (indiv.)",
                "lo (matches)",
                "marg. n_eff",
                "B marg.",
            ],
            rows_of(
                cand.sort_values(["format", "role", "min_total_balls"]),
                [
                    "format",
                    "role",
                    "source",
                    "threshold_balls",
                    "min_total_balls",
                    "players_ge_t",
                    "players_estimable",
                    "sb",
                    "sb_lo_players",
                    "sb_lo_matches",
                    "marginal_n_eff",
                    "b_marginal",
                ],
            ),
        ),
        "",
        "## 5. Required balls per individual for reliability targets (descriptive projection)",
        "`n* = R / (1 - R) * sigma_eff / tau2`. E7 is the model-free split-half covariance; E1b "
        "assumes independent balls. The range comes from the bootstrap bounds of `tau2`; when "
        "the lower bound is not above 0 there is no upper bound on the requirement.",
        "",
        md_table(
            [
                "format",
                "role",
                "source",
                "target",
                "tau2",
                "tau2 lo",
                "tau2 hi",
                "n* balls",
                "n* lo",
                "n* hi",
                "status",
            ],
            rows_of(
                pj,
                [
                    "format",
                    "role",
                    "source",
                    "target",
                    "tau2",
                    "tau2_lo",
                    "tau2_hi",
                    "required_balls",
                    "required_balls_lo",
                    "required_balls_hi",
                    "status",
                ],
            ),
        ),
        "",
        res["proj_note"],
        "",
        "## 6. Balls at which the Phase 4 data weight reaches 0.5 (measured)",
        "Under the Phase 4 basis B = 0.5 iff the Kish count `n_eff` equals `k`. `n_eff` cannot "
        "exceed the number of matches played, so an individual needs at least `k` matches. "
        "Counts below are measured in the cell, not assumed.",
        "",
        md_table(
            [
                "format",
                "role",
                "window",
                "k",
                "individuals",
                "n_eff >= k",
                "min balls among them",
                "median balls among them",
                "max n_eff",
            ],
            rows_of(
                ne,
                [
                    "format",
                    "role",
                    "window",
                    "k",
                    "players_total",
                    "players_n_eff_at_least_k",
                    "min_balls_among_them",
                    "median_balls_among_them",
                    "max_n_eff",
                ],
            ),
        ),
        "",
        "## 7. Reading the numbers",
        res["reading"],
        "",
        "## 8. Limits",
        "- In-sample on TRAIN and VALIDATION; the baseline and the frozen thresholds were fitted "
        "there. Nothing here validates a threshold. Thresholds stay `THRESHOLD_NOT_VALIDATED`.",
        "- Raising `t` selects heavier-usage individuals, which changes who is in the pool as "
        "well as how much data each has.",
        "- The projections inherit the identification problem of the variance estimates "
        "(`phase6_variance_floor_investigation.md`): where `tau2` is not distinguishable from "
        "0 the requirement has no upper bound.",
        "- The ladder stops at 120 (batters) and 144 (bowlers) balls; a target not reached "
        "inside it may still be reached beyond it.",
        "",
    ]
    return "\n".join(L)


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
    watched_before = {k: _hash(v) for k, v in WATCHED.items()}
    try:
        info = cr.begin_step("eligibility_reliability", store_path=store)
    except cr.CriteriaError as e:
        print(f"REFUSED: {e}")
        return 1
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    crit = cr.load_criteria()
    spec = crit["split_half"]
    n_boot = int(args.n_boot or spec["bootstrap_draws"])
    defn = cfg["definitions"]["provisional"]
    study = pl.load_study(store, n_boot=n_boot, seed=cfg["seed"])
    ladders = study.cfg["opportunity_ladders"]
    targets = [float(x) for x in cfg["reliability_targets"]]
    prim = study.primary_cells(defn)
    rules = study.frozen_rules(prim)
    cand = read_candidates(store)
    ladder_rows, proj_rows, ne_rows, cand_rows = [], [], [], []
    k_by_cell: dict[str, float] = {}
    xc_diffs: list[float] = []
    for (comp, role), cell in sorted(prim.items()):
        cd = rb.from_cell(cell)
        w = en.cell_weights(cell, study.gm, study.W)
        fit = cell.fit()
        k = float(sh.k_for(fit, cfg["shrinkage_config"])["k"])
        k_by_cell[f"{comp}|{role}"] = k
        meta = {"format": comp, "role": role, "stream": en.PRIMARY[role][0], "definition": defn}
        rule = rules[(comp, role)]
        for window in WINDOWS:
            mask = sp.window_mask(cd, window)
            wr = float(rule["wr"]) if window == "PRE_TEST" else 1.0
            steps = [(float(t), "ladder", None) for t in ladders[role]
                     if t >= 2 * spec["min_balls_per_half"]]  # fmt: skip
            steps.append((float(rule["threshold_balls"]) * wr, "frozen_scaled",
                          float(rule["threshold_balls"])))  # fmt: skip
            if window == "PRE_TEST":
                c = cand[(cand["format"] == comp) & (cand["role"] == role)]
                steps += [(float(x.scaled_threshold_pre_test), "phase4_candidate",
                           float(x.threshold_balls)) for x in c.itertuples()]  # fmt: skip
            for t, source, orig in steps:
                seed = sp.unit_seed(study.seed, "elig", comp, role, window, source, round(t, 6))
                row = er.pool_unit(cd, w, mask, t, k, spec, seed, n_boot)
                row.update(**meta, window=window, source=source, threshold_balls=orig)
                if source == "phase4_candidate":
                    cr_ = c[c["threshold_balls"] == orig].iloc[0]
                    row["source"] = f"phase4_candidate:{cr_['source']}"
                    cand_rows.append(row)
                elif source == "frozen_scaled":
                    row["source"] = "frozen_scaled"
                    if window == "PRE_TEST":
                        cand_rows.append({**row, "source": "frozen"})
                ladder_rows.append(row)
        pre_mask = sp.window_mask(cd, "PRE_TEST")
        for window in WINDOWS:
            m = sp.window_mask(cd, window)
            ne_rows.append({**meta, "window": window, "k": k, **er.balls_at_n_eff(cd, m, k)})
        proj_rows += er.projection_rows(cd, w, pre_mask, targets, meta)
        # cross-check against the Phase 5 helper (PRE_TEST odd/even point values)
        old = rb.reliability_by_opportunity(cd, "PRE_TEST", ladders[role],
                                            spec["min_balls_per_half"], w, spec["min_individuals_estimable"])  # fmt: skip
        mine = [r for r in ladder_rows if r["format"] == comp and r["role"] == role
                and r["window"] == "PRE_TEST" and r["source"] == "ladder"]  # fmt: skip
        for o in old:
            m_ = next(
                (r for r in mine if r["min_total_balls"] == float(o["min_total_balls"])), None
            )
            if m_ and o.get("sb_odd_even") is not None and m_.get("sb") is not None:
                xc_diffs.append(abs(o["sb_odd_even"] - m_["sb"]))
    lad = pd.DataFrame(ladder_rows)
    tg = er.target_table(lad, targets)
    pj, ne = pd.DataFrame(proj_rows), pd.DataFrame(ne_rows)
    cd_df = pd.DataFrame(cand_rows)
    xcheck = {
        "compared": len(xc_diffs),
        "max_abs_diff": float(max(xc_diffs)) if xc_diffs else float("nan"),
    }
    if not xc_diffs or xcheck["max_abs_diff"] > 1e-9:
        print("FATAL: ladder reliability does not reproduce the Phase 5 helper", xcheck)
        return 1
    watched_after = {k: _hash(v) for k, v in WATCHED.items()}
    if watched_after != watched_before:
        print("FATAL: a watched configuration file changed")
        return 1
    reach = tg[(tg["window"] == "PRE_TEST") & (tg["status"] == er.REACHED)]
    n_t = lambda x: int((reach["target"] == x).sum())  # noqa: E731
    pre = lad[
        (lad["window"] == "PRE_TEST") & (lad["source"] == "ladder") & (lad["status"] == "ESTIMATED")
    ]
    ne_pre = ne[ne["window"] == "PRE_TEST"]
    reading = "\n".join(
        [
            f"- Within the ladders the point estimate of the odd/even reliability reaches 0.5 in "
            f"{n_t(0.5)} of {len(prim)} cells, 0.7 in {n_t(0.7)} and 0.8 in {n_t(0.8)} (PRE_TEST).",
            f"- Across the {len(pre)} estimable ladder pools the SB runs from {pre['sb'].min():.2f} to "
            f"{pre['sb'].max():.2f}; the individual-bootstrap lower bound is above 0 in "
            f"{int((pre['sb_lo_players'] > 0).sum())} and the match-bootstrap lower bound in "
            f"{int((pre['sb_lo_matches'] > 0).sum())} of them.",
            f"- Individuals whose Kish count reaches k (data weight 0.5): "
            f"{int(ne_pre['players_n_eff_at_least_k'].sum())} of {int(ne_pre['players_total'].sum())} "
            "across the four cells. A threshold on balls alone does not lift the marginal individual "
            "to B = 0.5; that needs at least k distinct matches.",
            "- At the frozen thresholds (scaled), odd/even SB: "
            + ", ".join(
                f"{r.format} {r.role} {r.sb:.2f}"
                for r in cd_df[cd_df["source"] == "frozen"]
                .sort_values(["format", "role"])
                .itertuples()
            )
            + ".",
            "- Interval lower bound at or above the target within the ladder (PRE_TEST, cells "
            "of "
            f"{len(prim)}): individual bootstrap "
            + ", ".join(
                f"R {t}: {int(tg[(tg['window'] == 'PRE_TEST') & (tg['target'] == t)]['min_balls_lo_players'].notna().sum())}"
                for t in targets
            )
            + "; match bootstrap "
            + ", ".join(
                f"R {t}: {int(tg[(tg['window'] == 'PRE_TEST') & (tg['target'] == t)]['min_balls_lo_matches'].notna().sum())}"
                for t in targets
            )
            + ". 'n/a' in section 3 means the target is not reached.",
            "- This is descriptive; no threshold is changed here.",
        ]
    )
    both = pj[pj["required_balls_lo"].notna() & pj["required_balls_hi"].notna()]
    outside = int(
        (
            (both["required_balls"] < both["required_balls_lo"])
            | (both["required_balls"] > both["required_balls_hi"])
        ).sum()
    )
    proj_note = (
        "The bootstrap interval of `tau2` is not centred on the point estimate (the resampled "
        f"estimate is shifted upward, as noted for E6 in the variance report). In {outside} of "
        f"{len(both)} projection rows that have both bounds, the point requirement lies outside "
        "its own interval; read the range as a rough sensitivity band, not a confidence interval."
    )
    res = {"proj_note": proj_note, "ladder": lad, "targets": tg, "proj": pj, "n_eff": ne, "cand": cd_df, "xcheck": xcheck,
           "criteria": info, "seed": study.seed, "n_boot": n_boot, "definition": defn,
           "k_by_cell": k_by_cell, "code_version": code_version(), "reading": reading,
           "hash_check": "equal before and after (" + ", ".join(sorted(WATCHED)) + ")"}  # fmt: skip
    meta = {"fit_on": "WINDOW_IN_SAMPLE", "seed": study.seed, "n_boot": n_boot,
            "criteria_sha256": info["sha256"]}  # fmt: skip
    cr.verify_criteria(store_path=store)
    for df, nm, tb in ((lad, NAME, "p6_eligibility_reliability"),
                       (tg, f"{NAME}_targets", "p6_eligibility_targets"),
                       (pj, f"{NAME}_projection", "p6_eligibility_projection"),
                       (ne, f"{NAME}_n_eff", "p6_eligibility_n_eff")):  # fmt: skip
        out = df.copy()
        for k_, v_ in meta.items():
            out[k_] = v_
        save_table(out, nm, rep, store, tb)
    write_text(rep / f"{NAME}.md", render(res))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "ladder_rows": len(lad),
                      "targets": len(tg), "projection_rows": len(pj), "xcheck": xcheck,
                      "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
