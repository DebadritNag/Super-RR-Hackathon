"""Phase 6: season-by-season robustness checks (ROBUSTNESS_NOT_VALIDATION, internal).

Writes ``p6_season_robustness`` and ``phase6_robustness_season_checks.md/json/csv``. TEST rows are
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
from app.phase6 import season_robustness as sr  # noqa: E402
from app.phase6.constants import INVESTIGATION_CONFIG, PROVISIONAL_DEFINITION, STATUS  # noqa: E402
from app.phase6.lockguard import (  # noqa: E402
    assert_lock_state_unchanged,
    assert_no_test_rows,
    lock_state,
)
from app.phase6.outputs import Preservation, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_robustness_season_checks"
MANIFEST = REPORTS_DIR / "phase5_test_set_manifest.json"


def _f(x, nd: int = 3):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else f"{x:.{nd}f}"


def test_set_sizes() -> dict:
    """PRIMARY_RESTRICTED and STRICT_OFFICIAL_ONLY sizes, read from the Phase 5 manifest."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sets = m.get("sets", m)
    out = {}
    for k in ("PRIMARY_RESTRICTED", "STRICT_OFFICIAL_ONLY", "SENSITIVITY_ALL"):
        v = sets.get(k)
        out[k] = (
            len(v["match_ids"])
            if isinstance(v, dict) and "match_ids" in v
            else (v.get("matches") if isinstance(v, dict) else (len(v) if v is not None else None))
        )
    return out


def render(df: pd.DataFrame, meta: dict) -> str:
    est = df[df["status"] == "ESTIMATED"]
    L = [
        "# Phase 6 season-by-season robustness checks (ROBUSTNESS_NOT_VALIDATION)",
        "",
        f"Status: {STATUS}. Label: `{sr.LABEL}`. INTERNAL. These checks are robustness analyses, "
        "NOT validation. TEST was opened once in Phase 4 (single opening) and is not pristine. "
        f"`PRIMARY_RESTRICTED` ({meta['tests']['PRIMARY_RESTRICTED']} matches) is kept for internal "
        "diagnostic comparisons only; `STRICT_OFFICIAL_ONLY` "
        f"({meta['tests']['STRICT_OFFICIAL_ONLY']} matches) is a separate set. No independent "
        "out-of-sample validation is claimed. Cricsheet: not used. TEST outcomes: not used. "
        f"Seed {meta['seed']}, {meta['n_boot']} player-bootstrap draws. Code version "
        f"`{meta['code_version'][:16]}`. Criteria SHA-256 `{meta['criteria']['sha256']}`.",
        "",
        "## 1. Scope and reading guide",
        f"- Definition `{meta['definition']}` (provisional), primary streams (batter runs, bowler "
        "charged runs), IPL and T20I separately, seasons 2022 to 2025 (calendar years) inside the "
        "pre-test window.",
        "- `within_season`: odd/even split-half reliability inside one season (Spearman-Brown).",
        "- `adjacent_seasons`: Spearman correlation of individual mean residuals between season s "
        "and s+1, individuals with at least "
        f"{sr.MIN_BALLS_PER_SIDE} pressure balls in both.",
        "- `leave_one_season_out_rank`: the same correlation between season s and all other seasons.",
        "- `leave_one_season_out_reliability`: odd/even reliability of all other seasons pooled, "
        "next to the full pre-test value (`reference_value`).",
        "- Consistency across seasons does not show that the measure captures pressure skill. The "
        "baseline and thresholds were fitted on TRAIN (to 2024-12-31) and the seasons share the "
        "same individuals, so the checks are in-sample and not independent.",
        f"- Units with fewer than {sr.MIN_PLAYERS} individuals are `NOT_ESTIMABLE`.",
        "",
        "## 2. Counts",
        f"- Rows {len(df)}; estimable {len(est)}; not estimable {len(df) - len(est)}.",
        "",
    ]
    for chk, title in (("within_season", "3. Within-season split-half reliability"),
                       ("adjacent_seasons", "4. Adjacent-season rank correlation"),
                       ("leave_one_season_out_rank", "5. Leave-one-season-out rank correlation"),
                       ("leave_one_season_out_reliability",
                        "6. Reliability of the other seasons pooled (leave one season out)")):  # fmt: skip
        d = df[df["check"] == chk].sort_values(["format", "role", "season"])
        L += [f"## {title}", ""]
        L.append(md_table(
            ["format", "role", "season", "other", "matches", "players", "value", "lo", "hi",
             "full-window SB", "status"],
            [[r["format"], r["role"], str(r["season"]), str(r["other_season"] or ""), r["matches"],
              r["players"], _f(r["value"]), _f(r["ci_lo"]), _f(r["ci_hi"]),
              _f(r["reference_value"]), r["status"]] for _, r in d.iterrows()]))  # fmt: skip
        L.append("")
    adj = est[est["check"] == "adjacent_seasons"]
    wi = est[est["check"] == "within_season"]
    L += [
        "## 7. Summary",
        f"- Within-season reliability: {len(wi)} estimable units, median {wi['value'].median():.3f}, "
        f"range {wi['value'].min():.3f} to {wi['value'].max():.3f}; interval lower bound above 0 in "
        f"{int((wi['ci_lo'] > 0).sum())}.",
        f"- Adjacent-season correlation: {len(adj)} estimable units, median "
        f"{adj['value'].median():.3f}, range {adj['value'].min():.3f} to {adj['value'].max():.3f}; "
        f"interval lower bound above 0 in {int((adj['ci_lo'] > 0).sum())}.",
        "- Intervals use a player bootstrap (reliability) or a Fisher-z approximation (rank "
        "correlation) and ignore match clustering, so they are narrower than a match-cluster interval.",
        "- Seasons with few matches give wide intervals; a season that disagrees with the rest is "
        "descriptive and does not by itself indicate a defect.",
        "- Nothing here changes the primary window, the 0.5 data-weight gate, the thresholds or any "
        "restriction.",
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
    prim_before = {k: v for k, v in table_hashes(store, "p6_").items()
                   if k in ("p6_variance_estimators", "p6_split_half", "p6_definition_reliability")}  # fmt: skip
    crit_info = cr.begin_step("season_robustness", store_path=store)
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    if args.n_boot:
        cfg["split_half"]["bootstrap_draws"] = int(args.n_boot)
    study = pl.load_study(store, n_boot=args.n_boot or cfg["n_boot"], seed=cfg["seed"])
    assert_no_test_rows(study.d)
    df = sr.run(study, PROVISIONAL_DEFINITION, cfg)
    meta = {"seed": study.seed, "n_boot": cfg["split_half"]["bootstrap_draws"],
            "criteria": crit_info, "code_version": code_version(),
            "definition": PROVISIONAL_DEFINITION, "tests": test_set_sizes()}  # fmt: skip
    save_table(df, NAME, rep, store, "p6_season_robustness")
    write_text(rep / f"{NAME}.md", render(df, meta))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    now = table_hashes(store, "p6_")
    if {k: v for k, v in now.items() if k in prim_before} != prim_before:
        print("FATAL: a primary p6_ table changed during the season run")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "rows": len(df),
                      "estimable": int((df["status"] == "ESTIMATED").sum()),
                      "preservation": pres["all_preserved"]}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
