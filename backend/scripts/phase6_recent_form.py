"""Phase 6: separate 2024-onward and 2025-onward recent-form analyses (internal, experimental).

Writes ``p6_recent_form_2024``, ``p6_recent_form_2025``, ``p6_recent_form_reliability`` and
``phase6_recent_form_analyses.md/json/csv``. Each window is its own analysis with its own fit,
eligibility and reliability; nothing is written to or read back into a primary table. TEST rows are
never loaded, no lock event is created, ``superr.duckdb`` is read-only, Cricsheet is not an input.
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
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import recent_form as rf  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, PROVISIONAL_DEFINITION, STATUS  # noqa: E402
from app.phase6.lockguard import (  # noqa: E402
    assert_lock_state_unchanged,
    assert_no_test_rows,
    lock_state,
)
from app.phase6.outputs import Preservation, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_recent_form_analyses"
PRIMARY_TABLES = ("p6_variance_estimators", "p6_split_half", "p6_definition_reliability")


def _primary_hashes(store: Path) -> dict[str, str]:
    allh = table_hashes(store, "p6_")
    return {k: v for k, v in allh.items() if k in PRIMARY_TABLES}


def _f(x, nd: int = 3):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else f"{x:.{nd}f}"


def _c(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else x


def render(res: dict, meta: dict) -> str:
    L = [
        "# Phase 6 recent-form analyses (2024-onward and 2025-onward, separate)",
        "",
        f"Status: {STATUS}. Label: `{rf.LABEL}`. INTERNAL. In-sample (`{rf.FIT_ON}`). TEST outcomes: "
        "not used. TEST was opened once in Phase 4 and is not pristine; nothing here is independent "
        f"validation. Cricsheet: not used. Seed {meta['seed']}, {meta['n_boot']} match-cluster "
        f"bootstrap draws. Code version `{meta['code_version'][:16]}`. Criteria SHA-256 "
        f"`{meta['criteria']['sha256']}`.",
        "",
        "## 1. What these analyses are",
        "- The primary analysis keeps the full verified pre-test window (TRAIN + VALIDATION, "
        "723 matches). These two windows are additional recent-form analyses with their own tables "
        "(`p6_recent_form_2024`, `p6_recent_form_2025`, `p6_recent_form_reliability`). They are "
        "never merged into, or used to replace, a primary table.",
        f"- Definition: `{meta['definition']}` (provisional, unchanged). Shrinkage configuration "
        f"`{meta['shrinkage']}` (frozen). The baseline B0 and the pressure thresholds are the "
        "TRAIN-fitted ones, so a match has the same residual in every window.",
        "- Window-specific parts are refitted on the window's own rows, in-sample: variance "
        "components and `k`, the eligibility scaling, the bootstrap weights and the split-half "
        "reliability. No primary `k`, `tau2` or reliability is borrowed.",
        "- 2024-onward mixes rows that were in the B0 fit window (2024, TRAIN) with rows that were "
        "not (2025, VALIDATION). 2025-onward has no TRAIN rows, so its residuals are out of the B0 "
        "fit window. The column `share_rows_in_b0_fit_window` shows the mix. Comparing the two "
        "windows is confounded by this.",
        "- Eligibility thresholds are the four frozen Phase 4 ball thresholds scaled from the TRAIN "
        "scale to the window as `ceil(t x window_balls / TRAIN_balls)`. They are provisional "
        "(open decision OD-2) and not validated.",
        f"- Data weight is `B = n_eff / (n_eff + k)` for the least-experienced eligible "
        f"individual. The {rf.GATE} gate is only compared against; it is unchanged and every "
        "context that fails it stays restricted. `passes_gate_informational` does not "
        "publish or unlock anything.",
        "- No player-level score or rank is produced or stored here.",
        "",
        "## 2. Window sample counts (from the pre-test frame)",
        "",
    ]
    rows = []
    for key, c in res["counts"].items():
        for _, r in c.iterrows():
            rows.append([key, rf.WINDOWS[key], r["format"], r["matches"], r["delivery_rows"],
                         r["first_date"], r["last_date"]])  # fmt: skip
    L += [
        md_table(
            ["window", "start", "format", "matches", "delivery rows", "first date", "last date"],
            rows,
        ),
        "",
        f"Match ids: 2025-onward {len(res['match_sets']['2025'])} is a subset of 2024-onward "
        f"{len(res['match_sets']['2024'])}, which is a subset of the pre-test window "
        f"{meta['pretest_matches']}: {meta['subset_ok']}. Pre-test matches per format: "
        f"{meta['primary_matches']}.",
        "",
    ]
    for key in ("2024", "2025"):
        s = res["summary"][key]
        L += [f"## {'3' if key == '2024' else '4'}. {key}-onward cells (`{rf.LABEL}`)", ""]
        rows = [[r["format"], r["role"], r["stream"], r["matches"], r["pressure_observations"],
                 r["players_with_pressure_balls"], _f(r.get("share_rows_in_b0_fit_window"), 2),
                 _f(r.get("k"), 2), _c(r.get("floor_hit")), _c(r.get("scaled_threshold_balls")),
                 r.get("eligible_players"), _f(r.get("marginal_n_eff"), 2),
                 _f(r.get("marginal_data_weight")), _c(r.get("passes_gate_informational")),
                 r["status"]] for _, r in s.iterrows()]  # fmt: skip
        L += [
            md_table(
                [
                    "format",
                    "role",
                    "stream",
                    "matches",
                    "pressure obs",
                    "players",
                    "share in B0 fit",
                    "k",
                    "floor hit",
                    "threshold",
                    "eligible",
                    "marginal n_eff",
                    "marginal B",
                    "B >= 0.5",
                    "status",
                ],
                rows,
            ),
            "",
            f"Primary-stream cells estimated: {int(((s['is_primary_stream']) & (s['status'] == 'ESTIMATED')).sum())} of "
            f"{int(s['is_primary_stream'].sum())}; cells passing the 0.5 data-weight gate "
            f"(informational): {int(s['passes_gate_informational'].eq(True).sum())}.",
            "",
        ]
    rel = res["reliability"]
    L += ["## 5. Split-half reliability per window (Spearman-Brown corrected, in-sample)", ""]
    rows = []
    for _, r in rel.sort_values(["window_start", "format", "role", "stream", "mode"]).iterrows():
        rows.append([r["window_start"], r["format"], r["role"], r["stream"], r["mode"], r["players"],
                     _f(r.get("sb_pearson")), _f(r.get("sb_lo_players")), _f(r.get("sb_hi_players")),
                     _f(r.get("sb_lo_matches")), _f(r.get("sb_hi_matches")), r["status"]])  # fmt: skip
    L += [
        md_table(
            [
                "window",
                "format",
                "role",
                "stream",
                "mode",
                "players",
                "SB",
                "lo (players)",
                "hi (players)",
                "lo (matches)",
                "hi (matches)",
                "status",
            ],
            rows,
        ),
        "",
        "An interval that includes 0 gives no evidence of reliability above 0. Early/late splits "
        "also measure drift. Each window has fewer matches than the primary window, so intervals "
        "are wider.",
        "",
        "## 6. Limits",
        "- All fits are in-sample on the window. A shorter window gives fewer pressure balls per "
        "individual, which lowers data weight and reliability; the data cannot show that recent "
        "form is more informative.",
        "- Differences between the primary window and these windows are descriptive. They are "
        "not a validation of either and not a basis for changing the primary window.",
        "- Thresholds are provisional (OD-2). A user decision is needed before any window gets "
        "frozen thresholds of its own.",
        "- Every context that fails the data-weight gate stays restricted in every window.",
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
    prim_before = _primary_hashes(store)
    crit_info = cr.begin_step("recent_form", store_path=store)
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    cfg["split_half"]["bootstrap_draws"] = int(args.n_boot or cfg["split_half"]["bootstrap_draws"])
    study = pl.load_study(store, n_boot=args.n_boot or cfg["n_boot"], seed=cfg["seed"])
    assert_no_test_rows(study.d)
    defn = PROVISIONAL_DEFINITION
    shrinkage = cfg["shrinkage_config"]
    res = rf.run(study, defn, cfg, shrinkage)
    ms = res["match_sets"]
    pre = set(study.d["match_id"].unique())
    subset_ok = bool(ms["2025"] <= ms["2024"] <= pre)
    if not subset_ok:
        print("FATAL: window match sets are not nested")
        return 1
    for key, start in rf.WINDOWS.items():
        dates = study.d[study.d["match_id"].isin(ms[key])]["match_date"]
        if pd.to_datetime(dates).min() < pd.Timestamp(start):
            print("FATAL: a window contains a row before its start date")
            return 1
    meta = {"seed": study.seed, "n_boot": cfg["split_half"]["bootstrap_draws"], "criteria": crit_info,
            "code_version": code_version(), "definition": defn, "shrinkage": shrinkage,
            "pretest_matches": len(pre), "subset_ok": subset_ok,
            "primary_matches": json.dumps(res["primary_matches"], sort_keys=True)}  # fmt: skip
    for key in ("2024", "2025"):
        save_table(res["summary"][key], f"{NAME}_{key}", rep, store, f"p6_recent_form_{key}")
    save_table(res["reliability"], f"{NAME}_reliability", rep, store, "p6_recent_form_reliability")
    both = pd.concat([res["summary"]["2024"], res["summary"]["2025"]], ignore_index=True)
    save_table(both, NAME, rep, store)
    write_text(rep / f"{NAME}.md", render(res, meta))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    if _primary_hashes(store) != prim_before:
        print("FATAL: a primary p6_ table changed during the recent-form run")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1),
                      "rows_2024": len(res["summary"]["2024"]), "rows_2025": len(res["summary"]["2025"]),
                      "reliability_rows": len(res["reliability"]), "subset_ok": subset_ok,
                      "preservation": pres["all_preserved"]}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
