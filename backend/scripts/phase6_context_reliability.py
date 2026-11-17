"""Phase 6: reliability and data weight of the 48 atomic contexts (phase / chase / innings).

Reads the stored context rows (``p5_context_stats``, TRAIN + VALIDATION) and the stored Phase 5
eligibility rules. Writes ``p6_context_reliability``, ``p6_context_reliability_groups`` and
``phase6_context_reliability.md/json/csv``. TEST rows are never loaded, no lock event is created,
Cricsheet is not an input, and no gate state is written (the stored Phase 5 state is only compared).
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

from app.analytics.reporting import code_version, md_table, write_text  # noqa: E402
from app.phase5 import context_stats as cs  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import context_reliability as cr6  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import variance_floor as vf  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, STATUS  # noqa: E402
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_context_reliability"


def read_tables(store: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return (
            con.execute("SELECT * FROM p5_context_stats").df(),
            con.execute("SELECT * FROM p5_context_eligibility_rules").df(),
            con.execute("SELECT * FROM p6_split_half").df(),
        )
    finally:
        con.close()


def render(res: dict) -> str:
    df, grp, reg, aa = res["rows"], res["groups"], res["regress"], res["all_all"]
    est = df[df["oe_status"] == "ESTIMATED"]
    L = [
        "# Phase 6 context-specific reliability (phase, chase, innings)",
        "",
        f"Status: {STATUS}. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not "
        "used. Cricsheet: not used. The 0.5 data-weight gate is read from "
        f"`app.phase4.eligibility.GATE_B` (= {cr6.GATE}) and was not changed, lowered or bypassed; "
        "this report never sets a gate state. Contexts that fail the gate stay restricted. Code "
        f"version `{res['code_version'][:16]}`, seed {res['seed']}, {res['n_boot']} bootstrap "
        f"draws, {res['random']} random splits. Step run-log seq {res['criteria']['seq']} "
        f"(criteria SHA-256 `{res['criteria']['sha256']}` verified).",
        "",
        "## 1. Preconditions",
        f"- Recomputed marginal data weight and eligible counts against `p5_context_eligibility_rules`: "
        f"{reg['compared']}/{reg['contexts']} contexts compared, max abs difference in B "
        f"{reg['max_abs_diff_b']:.2e}, gate-state differences {reg['gate_state_differences']}, "
        f"eligible-count differences {reg['eligible_count_differences']}, reproduces = "
        f"{reg['reproduces']}.",
        f"- ALL/ALL context against the primary format x role cell of `any|q0.75` (odd/even, "
        f"PRE_TEST): equal in {int(aa['equal'].sum())}/{len(aa)} cells.",
        "",
        "## 2. Data weight of the marginal eligible player (copied gate state, recomputed number)",
        "`B = n_eff / (n_eff + k)` with `n_eff` the Kish count over per-match ball counts of the "
        "least-experienced eligible player and `k` from the TRAIN fit under `shrink_tau4` (the "
        "floor decides k in every context). B reaches the gate only when `n_eff >= k` (B = 0.5 "
        "iff n_eff = k). The stored eligibility threshold of each context is used unchanged.",
        "",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "matches",
                "eligible",
                "marginal n_eff",
                "k",
                "B",
                "gate",
                "gate passed",
                "n_eff needed",
                "gap",
            ],
            rows_of(
                df,
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "matches",
                    "eligible_players",
                    "marginal_n_eff",
                    "k",
                    "marginal_b",
                    "gate",
                    "stored_gate_passed",
                    "n_eff_required_for_gate",
                    "marginal_gap_n_eff",
                ],
            ),
        ),
        "",
        f"Contexts passing the gate: {int(df['gate_passed_recomputed'].sum())}/{len(df)}. "
        "Every context that fails stays restricted: it is excluded from any public output and "
        "no ranking is published from it.",
        "",
        "## 3. Split-half reliability per context (PRE_TEST)",
        "Odd/even Spearman-Brown reliability with a bootstrap over individuals and a bootstrap "
        "over matches, the median of 200 random splits, and the model-free signal share "
        "(cov of half means over variance of individual means). Individuals are those with at "
        "least 6 balls in each half.",
        "",
        md_table(
            [
                "format",
                "role",
                "phase",
                "situation",
                "indiv.",
                "SB odd/even",
                "lo (indiv.)",
                "hi (indiv.)",
                "lo (matches)",
                "hi (matches)",
                "SB random",
                "signal share",
            ],
            rows_of(
                df,
                [
                    "format",
                    "role",
                    "phase",
                    "situation",
                    "oe_players",
                    "oe_sb",
                    "oe_sb_lo_players",
                    "oe_sb_hi_players",
                    "oe_sb_lo_matches",
                    "oe_sb_hi_matches",
                    "rnd_sb",
                    "signal_share_m2",
                ],
            ),
        ),
        "",
        "## 4. By dimension (the 48 contexts overlap: ALL rows contain the specific ones)",
        "",
        md_table(
            [
                "dimension",
                "value",
                "estimable",
                "of",
                "SB median",
                "min",
                "max",
                "player lo > 0",
                "match lo > 0",
                "median indiv.",
                "median balls",
            ],
            rows_of(
                grp,
                [
                    "dimension",
                    "value",
                    "contexts_estimable",
                    "contexts_total",
                    "oe_sb_median",
                    "oe_sb_min",
                    "oe_sb_max",
                    "contexts_player_lo_above_0",
                    "contexts_match_lo_above_0",
                    "median_individuals",
                    "median_pressure_balls",
                ],
            ),
        ),
        "",
        "## 5. ALL/ALL check against the primary cells",
        "",
        md_table(
            ["format", "role", "context indiv.", "cell indiv.", "context SB", "cell SB", "equal"],
            rows_of(
                aa,
                [
                    "format",
                    "role",
                    "context_players",
                    "cell_players",
                    "context_sb",
                    "cell_sb",
                    "equal",
                ],
            ),
        ),
        "",
        "## 6. Reading the numbers",
        f"- {len(est)} of {len(df)} contexts are estimable for odd/even reliability. The SB "
        f"median is {est['oe_sb'].median():.2f}; the lower bound of the individual-bootstrap "
        f"interval is above 0 in {int((est['oe_sb_lo_players'] > 0).sum())} contexts and that of "
        f"the match-bootstrap interval in {int((est['oe_sb_lo_matches'] > 0).sum())}. The "
        "match-bootstrap interval is not centred on the point estimate (about 37% of matches are "
        "dropped in each draw, which adds noise to the half means), so its lower bound is "
        "conservative.",
        "- Reliability by phase and situation is read from section 4. Because the specific "
        "contexts hold fewer balls, their intervals are wider; a lower SB there is not by itself "
        "evidence that the pressure signal differs by phase.",
        "- The data-weight failure is structural under the Phase 4 basis: B reaches 0.5 only "
        "for an eligible player whose match-equivalent count `n_eff` is at least `k` = 25, "
        "that is 25 matches of equal ball counts, while the least-experienced eligible player "
        f"has `n_eff` between {df['marginal_n_eff'].min():.2f} and "
        f"{df['marginal_n_eff'].max():.2f} across the contexts.",
        "",
        "## 7. Limits",
        "- In-sample on TRAIN and VALIDATION; the thresholds and k come from TRAIN. Nothing here "
        "is validation, and TEST (opened once in Phase 4, not pristine) is not used.",
        "- 48 contexts are examined without multiplicity correction. Stored thresholds are "
        "working values and are not validated.",
        "- Stored rows hold match-level sums, so within-innings dependence cannot be modelled.",
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
    try:
        info = cr.begin_step("context_reliability", store_path=store)
    except cr.CriteriaError as e:
        print(f"REFUSED: {e}")
        return 1
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    crit = cr.load_criteria()
    spec = crit["split_half"]
    n_boot = int(args.n_boot or spec["bootstrap_draws"])
    seed = int(cfg["seed"])
    stats, rules, sh_ = read_tables(store)
    cs.check_stats(stats)
    gm, W = cs.global_match_weights(stats, n_boot, seed)
    rows = []
    for key in vf.context_keys():
        comp, role, phase, situation = key
        rr = rules[(rules["comp"] == comp) & (rules["role"] == role) & (rules["phase"] == phase)
                   & (rules["situation"] == situation)]  # fmt: skip
        if rr.empty:
            print(f"FATAL: no stored rule for {key}")
            return 1
        rows.append(cr6.context_row(stats, key, rr.iloc[0], gm, W, spec, seed, n_boot))
    df = pd.DataFrame(rows)
    meta = {"fit_on": "WINDOW_IN_SAMPLE", "seed": seed, "n_boot": n_boot,
            "criteria_sha256": info["sha256"]}  # fmt: skip
    for k, v in meta.items():
        df[k] = v
    reg = cr6.regression_summary(df)
    if not reg["reproduces"]:
        print("FATAL: stored Phase 5 data weight not reproduced", reg)
        return 1
    aa = cr6.all_all_check(df, sh_, cfg["definitions"]["provisional"])
    if not bool(aa["equal"].all()):
        print("FATAL: ALL/ALL context differs from the primary cell", aa.to_dict("records"))
        return 1
    grp = cr6.group_summary(df)
    cr.verify_criteria(store_path=store)
    save_table(df, NAME, rep, store, "p6_context_reliability")
    save_table(grp, f"{NAME}_groups", rep, store, "p6_context_reliability_groups")
    res = {"rows": df, "groups": grp, "regress": reg, "all_all": aa, "criteria": info,
           "seed": seed, "n_boot": n_boot, "random": spec["random_splits"],
           "code_version": code_version()}  # fmt: skip
    write_text(rep / f"{NAME}.md", render(res))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "contexts": len(df),
                      "estimable": int((df["oe_status"] == "ESTIMATED").sum()),
                      "gate_passed": int(df["gate_passed_recomputed"].sum()),
                      "regression": reg, "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
