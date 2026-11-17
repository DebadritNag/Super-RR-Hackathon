"""Compute the continuous intensity candidates on PRE_TEST deliveries and write coverage tables.

This script produces no validity or ranking result: it fits the TRAIN-only scaling, records the
fitted composite and the share of deliveries with a defined intensity per candidate.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from app.phase8.criteria import begin_step
from app.phase8.data import load_pre_test_deliveries
from app.phase8.intensity import build_intensity, coverage
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state
from app.phase8.splits import assert_pre_test
from app.phase8.store import write_p8_table


def main() -> int:
    check_protected()
    before = lock_state()
    begin_step("intensity")
    df, _ = load_pre_test_deliveries()
    assert_pre_test(df)
    w, info = build_intensity(df)
    cov = coverage(df, w)
    write_p8_table(cov, "p8_intensity_coverage")
    corr = w.corr(method="spearman").stack().rename("spearman").reset_index()
    corr.columns = ["candidate_a", "candidate_b", "spearman"]
    write_p8_table(corr, "p8_intensity_corr")
    write_p8_table(pd.DataFrame([{"info": json.dumps(info, sort_keys=True)}]), "p8_intensity_fit")
    assert_lock_state_unchanged(before)
    check_protected()
    print(json.dumps(info, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
