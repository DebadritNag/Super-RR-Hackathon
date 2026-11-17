"""Load the PRE_TEST deliveries once, check split integrity and write ``p8_data_exclusions``."""

from __future__ import annotations

import json
import sys

from app.analytics.integrity import sha256_file
from app.phase8.constants import EXPLORATORY_DB, OFFICIAL_DB
from app.phase8.criteria import begin_step
from app.phase8.data import FEATURE_COLS, assert_feature_list_clean, load_pre_test_deliveries
from app.phase8.lockguard import assert_lock_state_unchanged, check_protected, lock_state
from app.phase8.splits import assert_pre_test, check_match_partition
from app.phase8.store import write_p8_table


def main() -> int:
    check_protected()
    before = lock_state()
    begin_step(
        "data",
        inputs_hash=sha256_file(EXPLORATORY_DB)[:16] + "/" + sha256_file(OFFICIAL_DB)[:16],
    )
    df, excl = load_pre_test_deliveries()
    assert_pre_test(df)
    part = check_match_partition(df)
    assert_feature_list_clean(FEATURE_COLS)
    n = write_p8_table(excl, "p8_data_exclusions")
    assert_lock_state_unchanged(before)
    check_protected()
    print(
        json.dumps(
            {
                "rows": len(df),
                "matches": int(df["match_id"].nunique()),
                "partition": part,
                "exclusion_rows": n,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
