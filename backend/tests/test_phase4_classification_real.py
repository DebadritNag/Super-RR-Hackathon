"""Real-data checks on the stored classification (skipped when the analytical store is absent)."""

from __future__ import annotations

import duckdb
import pytest

from app.phase4 import classification as cl
from app.services.pressure_service import EXPLORATORY_DB

pytestmark = pytest.mark.realdata


@pytest.fixture(scope="module")
def cls():
    if not EXPLORATORY_DB.exists():
        pytest.skip("analytical store absent")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        have = {
            t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        if "p4_player_classification" not in have:
            pytest.skip("classification not built")
        return con.execute("SELECT * FROM p4_player_classification").df()
    finally:
        con.close()


def test_no_uncapped_without_a_verified_source(cls):
    overrides = cl.load_overrides(cl.OVERRIDES_FILE, cls["player_id"])
    unc = cls[cls["international_status"] == "Uncapped"]
    assert len(unc) == len(overrides[overrides["value"] == "Uncapped"])
    assert (unc["international_status_verification"] == cl.V_SOURCE).all()


def test_capped_is_only_derived_from_t20i_appearances_or_override(cls):
    capped = cls[cls["international_status"] == "Capped"]
    derived = capped["international_status_verification"] == cl.V_T20I
    assert (capped.loc[derived, "t20i_appearances_to_as_of"] > 0).all()
    assert (capped.loc[~derived, "international_status_verification"] == cl.V_SOURCE).all()


def test_unknown_players_carry_a_reason(cls):
    nat = cls[cls["nationality"] == "Unknown"]
    st = cls[cls["international_status"] == "Unknown"]
    assert nat["nationality_unknown_reason"].notna().all()
    assert st["international_status_unknown_reason"].notna().all()
    assert (nat["nationality_verification"] == cl.V_NONE).all()


def test_squad_nationality_requires_corroboration(cls):
    squad = cls[cls["nationality_source"] == cl.SOURCE_SQUAD]
    assert len(squad) > 0 and (squad["squad_match_type"] == "EXACT_UNIQUE").all()
    assert (squad["nationality_verification"] == cl.V_DERIVED).all()


def test_one_row_per_player_and_all_nine_combinations_countable(cls):
    assert cls["player_id"].is_unique
    cov = cl.coverage(cls)
    assert len(cov["combinations_all_players"]) == 9
    assert sum(c["players"] for c in cov["combinations_all_players"]) == len(cls)
