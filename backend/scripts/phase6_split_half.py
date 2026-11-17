"""Phase 6: split-half reliability per definition, format, role, stream, window and split mode.

Writes ``p6_split_half``, ``p6_split_half_ci``, ``p6_split_half_pooled`` and
``phase6_split_half_reliability.md/json/csv`` (plus ``_ci`` and ``_pooled`` files). TEST rows are
never loaded, no lock event is created, ``superr.duckdb`` is read-only, Cricsheet is not an input.
In-sample diagnostics on TRAIN and VALIDATION only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, md_table, write_text  # noqa: E402
from app.phase4 import engine as en  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5 import reliability as rb  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import split_half as sp  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, STATUS  # noqa: E402
from app.phase6.lockguard import (  # noqa: E402
    assert_lock_state_unchanged,
    assert_no_test_rows,
    lock_state,
)
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_split_half_reliability"
WINDOWS = ("PRE_TEST", "TRAIN")


def run(study: pl.Study, defns: list[str], cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    sh = cfg["split_half"]
    rows, cis = [], []
    for defn in defns:
        for (comp, role, stream), cell in study.all_cells(defn).items():
            assert_no_test_rows(cell.rows)
            cd = rb.from_cell(cell)
            w = en.cell_weights(cell, study.gm, study.W)
            meta = {"definition": defn, "format": comp, "role": role, "stream": stream,
                    "is_primary_stream": stream == en.PRIMARY[role][0]}  # fmt: skip
            for window in WINDOWS:
                mask = sp.window_mask(cd, window)
                for mode in sh["modes"]:
                    seed = sp.unit_seed(study.seed, defn, comp, role, stream, window, mode)
                    row, ci = sp.split_half_unit(cd, w, mask, mode, sh["min_balls_per_half"], seed,
                                                 sh["random_splits"], sh["bootstrap_draws"],
                                                 sh["min_players_estimable"])  # fmt: skip
                    rows.append({**meta, "window": window, **row})
                    cis += [{**meta, "window": window, "mode": mode, "statistic": "sb_pearson", **c}
                            for c in ci]  # fmt: skip
    return pd.DataFrame(rows), pd.DataFrame(cis)


def regression_vs_phase5(df: pd.DataFrame, reports: Path) -> dict:
    """Odd/even and early/late rows against the stored Phase 5 split-half table."""
    p5 = pd.read_csv(reports / "phase5_split_half_reliability.csv")
    p5 = p5[p5["mode"].isin(["odd_even", "early_late"]) & (p5["status"] == "ESTIMATED")]
    key = ["definition", "format", "role", "stream", "window", "mode"]
    m = p5.merge(df, on=key, suffixes=("_p5", "_p6"))
    diff_r = (m["r_pearson_p5"] - m["r_pearson_p6"]).abs()
    diff_sb = (m["sb_pearson_p5"] - m["sb_pearson_p6"]).abs()
    same_n = (m["players_p5"] == m["players_p6"]).all()
    return {"phase5_rows": len(p5), "matched": len(m), "max_abs_diff_r": float(diff_r.max()),
            "max_abs_diff_sb": float(diff_sb.max()), "players_equal": bool(same_n),
            "reproduces": bool(len(m) == len(p5) and diff_r.max() < 1e-9 and same_n)}  # fmt: skip


def render(res: dict) -> str:
    df, ci, pooled = res["rows"], res["ci"], res["pooled"]
    est = df[df["status"] == "ESTIMATED"]
    prim = est[est["is_primary_stream"]]
    pre = prim[prim["window"] == "PRE_TEST"]
    L = [
        "# Phase 6 split-half reliability",
        "",
        f"Status: {STATUS}. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not "
        "used. Cricsheet: not used. Seed "
        f"{res['seed']}, {res['n_boot']} bootstrap draws, {res['random']} random splits, at "
        f"least {res['min_balls']} pressure balls per half, at least {res['min_players']} players. "
        f"Code version `{res['code_version'][:16]}`. Criteria SHA-256 `{res['criteria']['sha256']}` "
        f"(declared before this run, run-log seq {res['criteria']['seq']} for this step).",
        "",
        "## 1. How to read this",
        "- Reliability is the Spearman-Brown corrected correlation `2r / (1 + r)` between the "
        "mean residual of two halves of each player's matches. It is reported unclipped: a "
        "negative value means the halves disagree.",
        "- Odd/even uses alternate matches. Early/late splits in time and so also measures drift "
        "(the halves are not parallel). Random splits repeat random match partitions; the "
        "value is the median over repeats and the SD across splits is shown.",
        "- Intervals: bootstrap over players, match-cluster bootstrap (all modes), and "
        "bootstrap of the per-repeat median (random, split noise only; the table also holds player and match intervals on the repeat closest to the median). An interval that includes 0 gives no "
        "evidence of reliability above 0.",
        "- In-sample diagnostics. The baseline and pressure thresholds were fitted on TRAIN, so "
        "these figures are not out-of-sample validation.",
        "",
        "## 2. Preconditions",
        f"- Odd/even and early/late rows reproduce the stored Phase 5 table: "
        f"{res['regress']['matched']}/{res['regress']['phase5_rows']} rows matched, max abs "
        f"difference in r {res['regress']['max_abs_diff_r']:.2e}, players equal = "
        f"{res['regress']['players_equal']}, reproduces = {res['regress']['reproduces']}.",
        "",
        "## 3. Counts",
        f"- Rows: {len(df)}; estimable: {len(est)}; units not estimable (fewer than "
        f"{res['min_players']} players with enough balls per half): {len(df) - len(est)}.",
    ]
    for mode in ("odd_even", "early_late", "random"):
        d = pre[pre["mode"] == mode]
        c = ci[(ci["mode"] == mode) & (ci["window"] == "PRE_TEST") & ci["is_primary_stream"]
               & (ci["ci_method"] == ("player_bootstrap_median_split" if mode == "random" else "player_bootstrap"))]  # fmt: skip
        excl = int((c["lo"] > 0).sum())
        L.append(
            f"- PRE_TEST, primary streams, {mode}: {len(d)} estimable units over "
            f"{d['definition'].nunique()} definitions; Spearman-Brown median {d['sb_pearson'].median():.3f} "
            f"(min {d['sb_pearson'].min():.3f}, max {d['sb_pearson'].max():.3f}); "
            f"interval lower bound above 0 in {excl}/{len(c)} units."
        )
    L += [
        "",
        "## 4. Provisional definition `any|q0.75`, all streams",
        "",
    ]
    d = df[(df["definition"] == "any|q0.75") & (df["window"] == "PRE_TEST")]
    cim = ci[(ci["definition"] == "any|q0.75") & (ci["window"] == "PRE_TEST")]
    wide = []
    for _, r in d.iterrows():
        sel = cim[(cim["format"] == r["format"]) & (cim["role"] == r["role"])
                  & (cim["stream"] == r["stream"]) & (cim["mode"] == r["mode"])]  # fmt: skip
        s = {x["ci_method"]: (x["lo"], x["hi"]) for _, x in sel.iterrows()}
        first = s.get("player_bootstrap") or s.get("player_bootstrap_median_split") or (None, None)
        mt = s.get("match_bootstrap") or s.get("match_bootstrap_median_split") or (None, None)
        wide.append([r["format"], r["role"], r["stream"], r["mode"], r["players"],
                     r["r_pearson"], r["sb_pearson"], first[0], first[1], mt[0], mt[1]])  # fmt: skip
    L += [
        md_table(
            [
                "format",
                "role",
                "stream",
                "mode",
                "players",
                "r",
                "SB",
                "SB lo (players)",
                "SB hi",
                "SB lo (matches)",
                "SB hi (matches)",
            ],
            wide,
        ),
        "",
        "## 5. Pooled over format x role cells (Fisher z, weights n-3, clip 0.99)",
        "Primary streams, all nine definitions, PRE_TEST.",
        "",
        md_table(
            ["definition", "mode", "cells", "players", "pooled r", "pooled SB"],
            rows_of(
                pooled[(pooled["stream_group"] == "primary") & (pooled["window"] == "PRE_TEST")],
                ["definition", "mode", "cells", "players_total", "pooled_r", "pooled_sb"],
            ),
        ),
        "",
        "## 6. TRAIN window versus PRE_TEST (primary streams, provisional definition)",
        md_table(
            ["format", "role", "mode", "window", "players", "SB"],
            rows_of(
                prim[(prim["definition"] == "any|q0.75")].sort_values(
                    ["format", "role", "mode", "window"]
                ),
                ["format", "role", "mode", "window", "players", "sb_pearson"],
            ),
        ),
        "",
        "## 7. Limits",
        "- Spearman-Brown assumes parallel halves; early/late violates stationarity.",
        "- The nine definitions are examined side by side without multiplicity correction. "
        "Higher reliability of one definition is not evidence that it measures pressure skill.",
        "- Players with at least 6 balls in each half are a selected, more active subset.",
        "- Bootstrap over players and over matches answer different questions; both are shown. "
        "Each match-bootstrap draw drops about 37% of the matches, which adds noise to the "
        "half means, so the match-bootstrap interval is not centred on the point estimate: "
        f"{res['above']}. It is a conservative check for reliability above 0.",
        "- Consistency between odd/even, early/late and random splits is a robustness check, not "
        "independent validation.",
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
    crit_info = cr.begin_step("split_half", store_path=store)
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    if args.n_boot:
        cfg["split_half"]["bootstrap_draws"] = int(args.n_boot)
    study = pl.load_study(store, n_boot=args.n_boot or cfg["n_boot"], seed=cfg["seed"])
    df, ci = run(study, cfg["definitions"]["candidates"], cfg)
    regress = regression_vs_phase5(df, rep)
    if not regress["reproduces"]:
        print("FATAL: Phase 5 split-half table not reproduced", regress)
        return 1
    pooled = sp.pool_rows(df, cfg["split_half"]["corr_clip"])
    sh = cfg["split_half"]
    key = ["definition", "format", "role", "stream", "window", "mode"]
    mb = ci[ci["ci_method"] == "match_bootstrap"].merge(df[[*key, "sb_pearson"]], on=key)
    mid_below = int((0.5 * (mb["lo"] + mb["hi"]) < mb["sb_pearson"]).sum())
    above = (
        f"the interval midpoint is below the point estimate in {mid_below}/{len(mb)} odd/even and "
        f"early/late units and the point estimate is above the interval upper bound in "
        f"{int((mb['sb_pearson'] > mb['hi']).sum())}/{len(mb)}"
    )
    res = {"rows": df, "ci": ci,
           "pooled": pooled, "regress": regress, "criteria": crit_info, "seed": study.seed,
           "n_boot": sh["bootstrap_draws"], "random": sh["random_splits"],
           "min_balls": sh["min_balls_per_half"], "min_players": sh["min_players_estimable"],
           "code_version": code_version(), "above": above}  # fmt: skip
    save_table(df, NAME, rep, store, "p6_split_half")
    save_table(ci, f"{NAME}_ci", rep, store, "p6_split_half_ci")
    save_table(pooled, f"{NAME}_pooled", rep, store, "p6_split_half_pooled")
    write_text(rep / f"{NAME}.md", render(res))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "rows": len(df), "ci_rows": len(ci),
                      "pooled_rows": len(pooled), "regression": regress,
                      "estimable": int((df["status"] == "ESTIMATED").sum()),
                      "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
