"""Phase 9: 2026 out-of-time check table and reproducibility check of the p9 model artefacts.

* ``p9_2026_check``: the metrics of the eight expected-outcome models and of W1/W2 on the calendar-2026
  matches ("2026 out-of-time check; data previously held out, released by owner decision"). The models
  were fitted on matches to 2025-12-31 with the Phase 8 hyperparameters; nothing was tuned on 2026.
* ``p9_reproducibility``: every model is refitted from scratch with the same seed and parameters and
  its predictions on the 2026 rows are compared with the stored artefact (maximum absolute
  difference; 0.0 means identical).
"""

from __future__ import annotations

import json
import os
import sys

os.environ["SUPERR_PHASE"] = "phase9"

import duckdb  # noqa: E402
import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.analytics.integrity import sha256_file  # noqa: E402
from app.phase8 import store  # noqa: E402
from app.phase8.ai_verify import load_artefact  # noqa: E402
from app.phase8.constants import EXPLORATORY_DB, MODELS_DIR, OFFICIAL_DB  # noqa: E402
from app.phase8.criteria import begin_step  # noqa: E402
from app.phase8.data import load_pre_test_deliveries  # noqa: E402
from app.phase8.expected import (  # noqa: E402
    SPECS,
    category_codes,
    fit_predict,
    prepare_features,
    target_frame,
)
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state  # noqa: E402
from app.phase8.splits import fit_group  # noqa: E402
from app.phase8.winprob import (  # noqa: E402
    W1_COLS,
    W2_COLS,
    fit_binary,
    frame_features,
    match_labels,
    wp_labels,
)
from app.phase9.fixed import phase8_expected_choice, phase8_wp_params  # noqa: E402

LABEL = "2026 out-of-time check; data previously held out, released by owner decision"


def _wp_inputs(df: pd.DataFrame):
    con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
    try:
        m = con.execute(
            "SELECT match_id, result, win_team_id, revised_target, result_status FROM matches"
        ).df()
    finally:
        con.close()
    x = frame_features(df)
    labels = match_labels(m)
    y2, pop2 = wp_labels(df, labels, 2)
    y1, pop1 = wp_labels(df, labels, 1)
    s2 = (df["innings_number"] == 2) & x[["runs_required", "rrr"]].notna().all(axis=1)
    s1 = (df["innings_number"] == 1) & x["legal_balls_remaining"].notna()
    return x, (y1, pop1 & s1), (y2, pop2 & s2)


def main() -> int:
    check_protected()
    before = lock_state()
    begin_step("models_check", inputs_hash=sha256_file(EXPLORATORY_DB)[:16])
    df, _ = load_pre_test_deliveries()
    grp = fit_group(df)
    is_val = (grp == "VALIDATION").to_numpy()
    is_tr = (grp == "TRAIN").to_numpy()
    codes = category_codes(df)
    x = prepare_features(df, codes)
    repro, check = [], []
    for spec in SPECS:
        stem = f"p9_expected_{spec.role}_{spec.name}_v1"
        art = load_artefact(stem)
        y, pop = target_frame(df, spec)
        ok = pop.to_numpy() & y.notna().to_numpy()
        tr, va = is_tr & ok, is_val & ok
        learner, params = phase8_expected_choice(spec.role, spec.name)
        pred_new = fit_predict(learner, spec.kind, params, x[tr], y.to_numpy()[tr])(x[va])
        xs = prepare_features(df, art["obj"]["codes"])[art["obj"]["features"]]
        pred_old = art["obj"]["predictor"](xs[va])
        repro.append(
            {
                "model": stem,
                "learner": learner,
                "params": json.dumps(params, sort_keys=True),
                "rows_compared": int(va.sum()),
                "max_abs_diff": float(np.max(np.abs(pred_new - pred_old))),
                "identical": bool(np.array_equal(pred_new, pred_old)),
                "artefact_sha256": art["sha256"],
            }
        )
    x_wp, (y1, p1), (y2, p2) = _wp_inputs(df)
    bundle = joblib.load(MODELS_DIR / "p9_wp_v1.joblib")
    for name, y, pop, cols, key in (("W1", y1, p1, W1_COLS, "w1"), ("W2", y2, p2, W2_COLS, "w2")):
        params = phase8_wp_params(name)
        tr, va = is_tr & pop.to_numpy(), is_val & pop.to_numpy()
        new = fit_binary("gbm", cols, x_wp[tr], y.to_numpy()[tr], params)(x_wp[va])
        old = bundle[key](x_wp[va])
        repro.append(
            {
                "model": f"p9_wp_v1:{name}",
                "learner": "gbm",
                "params": json.dumps(params, sort_keys=True),
                "rows_compared": int(va.sum()),
                "max_abs_diff": float(np.max(np.abs(new - old))),
                "identical": bool(np.array_equal(new, old)),
                "artefact_sha256": sha256_file(MODELS_DIR / "p9_wp_v1.joblib"),
            }
        )
    em = store.read_table("p8_a_model_metrics")
    for r in em.itertuples():
        pm = r.primary_metric
        check.append(
            {
                "model": f"{r.role}_{r.target}",
                "kind": r.kind,
                "metric": pm,
                "model_value_2026": float(getattr(r, f"gbm_{pm}")),
                "constant_value_2026": float(getattr(r, f"const_{pm}")),
                "gain_vs_constant_pct": float(r.gain_vs_const_pct),
                "n_2026": int(r.n_validation),
                "slope": float(getattr(r, "chosen_slope", np.nan)),
                "label": LABEL,
            }
        )
    wm = store.read_table("p8_wp_metrics")
    for r in wm.itertuples():
        check.append(
            {
                "model": r.model,
                "kind": "win_probability",
                "metric": "brier",
                "model_value_2026": float(r.brier),
                "constant_value_2026": float(r.brier_const),
                "gain_vs_constant_pct": 100.0 * float(r.brier_gain_vs_const),
                "n_2026": int(r.n_validation),
                "slope": float(r.slope),
                "label": LABEL,
            }
        )
    store.write_p8_table(pd.DataFrame(check), "p8_2026_check")
    store.write_p8_table(pd.DataFrame(repro), "p8_reproducibility")
    assert_lock_state_unchanged(before)
    check_protected()
    print(json.dumps({"check": check, "reproducibility": repro}, indent=1, default=str))
    return 0 if all(r["identical"] for r in repro) else 4


if __name__ == "__main__":
    sys.exit(main())
