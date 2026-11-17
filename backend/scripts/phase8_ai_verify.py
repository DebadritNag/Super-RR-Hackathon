"""Phase 8 chunk 6: audit the saved models, regenerate the experimental AI Top 10 files.

Reads deliveries up to the end of VALIDATION only (TEST rows are never loaded) and opens both
databases read-only. Writes into the reports folder:
``experimental_ai_top10_batters.csv``, ``experimental_ai_top10_bowlers.csv``,
``phase8_ai_verification.json`` and ``ai_pipeline_verification.md``.
The previous Phase 7 files are kept as ``*_phase7_aborted``.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.phase8 import ai_verify as av  # noqa: E402
from app.phase8.constants import OFFICIAL_DB, PHASE8_DB, REPORTS_DIR  # noqa: E402
from app.phase8.data import load_pre_test_deliveries  # noqa: E402
from app.phase8.intensity import build_intensity  # noqa: E402
from app.phase8.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase8.splits import assert_pre_test, check_match_partition  # noqa: E402
from app.phase8.winprob import (  # noqa: E402
    W2_COLS,
    frame_features,
    match_labels,
    wp_labels,
)


def _names() -> pd.Series:
    con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
    try:
        d = con.execute("SELECT player_id, player_name FROM players").df()
        m = con.execute(
            "SELECT match_id, result, win_team_id, revised_target, result_status FROM matches"
        ).df()
    finally:
        con.close()
    return d.drop_duplicates("player_id").set_index("player_id")["player_name"], m


def _wp_check(df: pd.DataFrame, matches: pd.DataFrame) -> dict:
    import joblib

    from app.phase8.constants import MODELS_DIR

    a = joblib.load(MODELS_DIR / "p8_wp_v1.joblib")
    labels = match_labels(matches)
    x = frame_features(df)
    y2, pop2 = wp_labels(df, labels, 2)
    ok = pop2 & x[["runs_required", "rrr"]].notna().all(axis=1)
    va = ok & (df["period"] == "VALIDATION")
    tr = ok & (df["period"] == "TRAIN")
    p = np.clip(a["w2"](x[va]), 0.005, 0.995)
    y = y2[va].to_numpy()
    brier = float(np.mean((p - y) ** 2))
    base = float(np.mean((y2[tr].mean() - y) ** 2))
    return {
        "model": "W2 (chasing side wins), stored artefact applied to VALIDATION deliveries",
        "n_validation": int(va.sum()),
        "brier": brier,
        "brier_constant_baseline": base,
        "brier_gain_vs_constant": 1 - brier / base,
        "prediction_range": [float(p.min()), float(p.max())],
        "features": a["w2_cols"] if "w2_cols" in a else list(W2_COLS),
    }


def main() -> int:
    before = lock_state()
    names, matches = _names()
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    part = check_match_partition(df)
    w_all, _ = build_intensity(df)
    w = w_all["w_P4"]

    inventory = av.artefact_inventory()
    retrain = [av.retrain_check(df, r, n) for r, n in (("batter", "runs"), ("bowler", "wicket"))]
    wp = _wp_check(df, matches)

    # sensitivity of the output to the artefact: replace the predictor by a constant
    outs: dict[str, pd.DataFrame] = {}
    run_ts = datetime.now(UTC).isoformat(timespec="seconds")
    summary: dict[str, dict] = {}
    for role in ("batter", "bowler"):
        scores = av.experimental_scores(df, w, role, names)
        top = av.top10(scores)
        top["model_version"] = "p8_expected_v1 (gradient boosting, TRAIN-only fit)"
        top["training_data"] = "TRAIN to 2024-12-31; scored on VALIDATION (calendar 2025) only"
        top["pressure_definition"] = "P4 intensity >= 0.5 (not validated)"
        top["prediction_timestamp_utc"] = run_ts
        top["uncertainty"] = (
            "95% interval from match-cluster standard error; ranking stability not estimated"
        )
        outs[role] = top
        summary[role] = {
            "players_with_pressure_balls": int(len(scores)),
            "eligible": int(scores["eligible"].sum()),
            "listed": int(len(top)),
            "intervals_excluding_zero_in_top10": int(top["interval_excludes_zero"].sum()),
            "median_interval_half_width_top10": float(
                ((top["ci_high"] - top["ci_low"]) / 2).median()
            ),
        }
        # split-half by match parity among eligible players: does the order repeat?
        e = scores[scores["eligible"]]["player_id"]
        col = "striker_id" if role == "batter" else "bowler_id"
        spec_sign = 1.0 if role == "batter" else -1.0
        exp, _ = av.expected_from_artefact(df, role, "runs")
        from app.phase8.expected import spec_for, target_frame

        y, _pop = target_frame(df, spec_for(role, "runs"))
        use = (df["period"] == "VALIDATION") & (w >= av.HIGH_CUT) & y.notna() & df[col].isin(e)
        r = spec_sign * (y - exp)
        d = pd.DataFrame(
            {"p": df.loc[use, col], "r": r[use], "par": df.loc[use, "match_id"].astype(int) % 2}
        )
        g = d.groupby(["p", "par"])["r"].mean().unstack()
        g = g.dropna()
        rr = float(g[0].corr(g[1])) if len(g) > 5 else float("nan")
        sb = float(2 * rr / (1 + rr)) if rr == rr else float("nan")
        summary[role]["split_half_players"] = int(len(g))
        summary[role]["split_half_r"] = rr
        summary[role]["split_half_spearman_brown"] = sb

    # old files preserved before overwrite
    for role in ("batters", "bowlers"):
        src = REPORTS_DIR / f"experimental_ai_top10_{role}.csv"
        dst = REPORTS_DIR / f"experimental_ai_top10_{role}_phase7_aborted.csv"
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
    cols = [
        "model_output_order", "player_id", "player_name", "role", "mean_runs_residual", "ci_low",
        "ci_high", "se_match_cluster", "interval_excludes_zero", "mean_wicket_residual",
        "actual_runs_per_ball", "expected_runs_per_ball", "pressure_balls", "pressure_matches",
        "ipl_balls", "t20i_balls", "mean_intensity", "model_output_definition", "uncertainty",
        "eligibility_rule", "model_version", "training_data", "pressure_definition",
        "model_artefact_runs_sha256", "model_artefact_wicket_sha256", "prediction_timestamp_utc",
        "status_label", "banner",
    ]  # fmt: skip
    for role, name in (("batter", "batters"), ("bowler", "bowlers")):
        outs[role][cols].to_csv(
            REPORTS_DIR / f"experimental_ai_top10_{name}.csv", index=False, float_format="%.6f"
        )

    assert_lock_state_unchanged(before)

    report = {
        "generated_utc": run_ts,
        "inventory": inventory,
        "retrain_checks": retrain,
        "wp_check": wp,
        "partition": {k: v for k, v in part.items() if isinstance(v, (int, float, str, bool))},
        "summary": summary,
        "rows_loaded": int(len(df)),
        "periods_loaded": sorted(df["period"].unique().tolist()),
        "test_rows_loaded": int((df["period"] == "TEST").sum()),
        "lock_unchanged": True,
    }
    (REPORTS_DIR / "phase8_ai_verification.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, default=str))
    _ = PHASE8_DB
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
