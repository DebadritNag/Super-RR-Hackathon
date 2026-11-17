"""Phase 5 classification: three separate capped values, explicit migration, override validation."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase4.spotchecks import check_capped_count
from app.phase5 import classification_v2 as c2
from tests.phase4_api_helpers import (
    all_pass_gates,
    base_classification,
    base_classification_v2,
    build_store,
    overrides_frame,
)

P = "/api/v1"
TODAY = date(2026, 6, 1)


def _raw(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(cl.OVERRIDE_COLUMNS), dtype=str)


def _good(pid="7", field="international_status", value="VERIFIED_UNCAPPED") -> tuple:
    return (pid, field, value, "Board cap list 2026", "Ann Lee", "2026-02-01")


# ----------------------------------------------------------------------------- enum and migration


def test_three_real_status_values_are_separate_and_unknown_is_not_uncapped():
    assert c2.STATUS_VALUES == ("VERIFIED_CAPPED", "DERIVED_CAPPED", "UNKNOWN")
    assert len(set(c2.STATUS_VALUES)) == 3
    assert c2.DISABLED_PLACEHOLDER_VALUES == ("VERIFIED_UNCAPPED",)
    assert c2.ACCEPTED_STORED_VALUES == (*c2.STATUS_VALUES, "VERIFIED_UNCAPPED")
    assert "UNCAPPED" not in c2.UNKNOWN
    assert c2.status_display("UNKNOWN") == "UNKNOWN_STATUS"
    assert c2.status_display("DERIVED_CAPPED") == "DERIVED_CAPPED"


@pytest.mark.parametrize(
    ("status", "verification", "expected"),
    [
        ("Capped", cl.V_T20I, "DERIVED_CAPPED"),
        ("Capped", cl.V_SOURCE, "VERIFIED_CAPPED"),
        ("Uncapped", cl.V_SOURCE, "VERIFIED_UNCAPPED"),
        ("Unknown", cl.V_NONE, "UNKNOWN"),
    ],
)
def test_every_mapped_combination_migrates_explicitly(status, verification, expected):
    df = base_classification().head(1).copy()
    df["international_status"] = status
    df["international_status_verification"] = verification
    out = c2.migrate_classification(df)
    assert out["international_status"].iloc[0] == expected
    assert out["legacy_international_status"].iloc[0] == status  # the old label is kept
    assert out["migration_version"].iloc[0] == c2.CLASSIFICATION_V2_VERSION


def test_mapping_table_equals_the_documented_mapping():
    m = c2.migration_map_frame()
    assert len(m) == 4
    assert set(m["phase5_status"]) == set(c2.ACCEPTED_STORED_VALUES)


@pytest.mark.parametrize(
    ("status", "verification"),
    [
        ("Capped", cl.V_NONE),
        ("Uncapped", cl.V_T20I),
        ("Uncapped", cl.V_NONE),
        ("Unknown", cl.V_T20I),
        ("Unknown", cl.V_SOURCE),
        ("Maybe", cl.V_NONE),
    ],
)
def test_unmapped_combination_is_fatal_and_names_the_players(status, verification):
    df = base_classification().head(3).copy()
    df.loc[df.index[1], "international_status"] = status
    df.loc[df.index[1], "international_status_verification"] = verification
    bad_id = int(df["player_id"].iloc[1])
    with pytest.raises(c2.ClassificationMigrationError, match=str(bad_id)):
        c2.migrate_classification(df)


def test_migration_preserves_rows_and_counts_on_synthetic_data():
    legacy = base_classification()
    out = c2.migrate_classification(legacy)
    assert len(out) == len(legacy) and out["player_id"].is_unique
    n_capped = int((legacy["international_status"] == "Capped").sum())
    assert int(out["international_status"].isin(c2.CAPPED_VALUES).sum()) == n_capped == 12
    assert int((out["international_status"] == "UNKNOWN").sum()) == 12
    assert int((out["international_status"] == "DERIVED_CAPPED").sum()) == 12  # all derived
    assert out["status_display"].eq("UNKNOWN_STATUS").sum() == 12
    # every non-status column is carried over unchanged
    pd.testing.assert_series_equal(out["nationality"], legacy["nationality"])
    assert out["derived_evidence"].notna().sum() == 12


def test_migration_rejects_duplicate_player_ids():
    df = base_classification().head(2).copy()
    df.loc[df.index[1], "player_id"] = df["player_id"].iloc[0]
    with pytest.raises(c2.ClassificationMigrationError, match="duplicate"):
        c2.migrate_classification(df)


def test_phase4_coverage_comparison_passes_and_fails_loudly():
    out = c2.migrate_classification(base_classification())
    cov = cl.coverage(base_classification())
    res = c2.assert_matches_phase4_coverage(out, cov)
    assert res["phase4_capped"] == res["phase5_capped_total"] == 12
    bad = {**cov, "players_total": cov["players_total"] + 1}
    with pytest.raises(c2.ClassificationMigrationError):
        c2.assert_matches_phase4_coverage(out, bad)
    tampered = out.copy()
    tampered.loc[tampered["international_status"] == "UNKNOWN", "international_status"] = (
        "DERIVED_CAPPED"
    )
    with pytest.raises(c2.ClassificationMigrationError):
        c2.assert_matches_phase4_coverage(tampered, cov)


# ----------------------------------------------------------------------------- no inference


def test_no_inference_from_names_domestic_experience_or_ipl_participation():
    df = base_classification().head(1).copy()
    df["player_name"] = "Uncapped Capped Kid"  # a misleading name must change nothing
    df["international_status"] = "Unknown"
    df["international_status_verification"] = cl.V_NONE
    df["t20i_appearances_to_as_of"] = 0
    df["ipl_matches"] = 50  # heavy IPL participation
    df["domestic_matches"] = 200  # domestic experience
    df["squad_match_type"] = "EXACT_UNIQUE"
    out = c2.migrate_classification(df)
    assert out["international_status"].iloc[0] == "UNKNOWN"
    assert out["derived_evidence"].iloc[0] is None


def test_classification_module_imports_no_name_squad_or_ipl_sources():
    tree = ast.parse(Path(c2.__file__).read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add(n.module or "")
    assert mods <= {
        "__future__", "json", "collections", "collections.abc", "datetime", "pathlib",
        "typing", "pandas", "app.phase4", "app.phase5.constants",
    }  # fmt: skip
    idents = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    idents |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    idents |= {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for ident in idents:
        for forbidden in ("squad", "domestic", "ipl", "player_name", "name_variants"):
            assert forbidden not in ident.lower(), ident


def test_unknown_group_label_is_never_uncapped():
    from app.phase4.selection import assign_group

    assert assign_group("Indian", "UNKNOWN") == "UNKNOWN"
    assert assign_group("Overseas", "UNKNOWN") == "UNKNOWN"
    from app.services.phase4_service import group_label

    assert group_label("UNKNOWN") == "UNKNOWN_STATUS"
    assert "UNCAPPED" not in group_label("UNKNOWN")


# ----------------------------------------------------------------------------- overrides


def test_override_header_only_file_is_empty_and_unchanged():
    base = base_classification_v2()
    assert c2.load_overrides_v2(cl.OVERRIDES_FILE, base).empty
    text = cl.OVERRIDES_FILE.read_text(encoding="utf-8").strip()
    assert text == ",".join(cl.OVERRIDE_COLUMNS)
    assert cl.OVERRIDES_FILE.read_bytes() == (",".join(cl.OVERRIDE_COLUMNS) + "\n").encode("utf-8")


def test_valid_overrides_pass_and_apply_to_the_named_player_only():
    base = base_classification_v2()
    ov = c2.validate_overrides_v2(
        _raw(
            [_good("7"), _good("1", value="VERIFIED_CAPPED"), _good("9", "nationality", "Overseas")]
        ),
        base,
        TODAY,
    )
    assert len(ov) == 3 and list(ov["player_id"]) == [7, 1, 9]
    final = c2.apply_overrides_v2(base, ov).set_index("player_id")
    b = base.set_index("player_id")
    assert final.loc[7, "international_status"] == "VERIFIED_UNCAPPED"
    assert final.loc[7, "international_status_verification"] == cl.V_SOURCE
    assert final.loc[7, "international_status_source"] == "MANUAL_OVERRIDE:Board cap list 2026"
    assert final.loc[7, "status_verified_by"] == "Ann Lee"
    assert final.loc[7, "status_display"] == "VERIFIED_UNCAPPED"
    # a VERIFIED_CAPPED override upgrades a DERIVED_CAPPED player and keeps the derived evidence
    assert b.loc[1, "international_status"] == "DERIVED_CAPPED"
    assert final.loc[1, "international_status"] == "VERIFIED_CAPPED"
    assert final.loc[1, "derived_evidence"] == cl.V_T20I
    assert final.loc[9, "nationality"] == "Overseas"
    assert final.loc[9, "nationality_verification"] == cl.V_SOURCE
    assert final.loc[9, "international_status"] == "UNKNOWN"  # independent fields
    untouched = [p for p in b.index if p not in (7, 1, 9)]
    for col in ("international_status", "nationality", "international_status_verification"):
        pd.testing.assert_series_equal(final.loc[untouched, col], b.loc[untouched, col])


@pytest.mark.parametrize(
    ("row", "code"),
    [
        (
            ("x", "international_status", "VERIFIED_UNCAPPED", "s", "v", "2026-01-01"),
            "UNKNOWN_PLAYER_ID",
        ),
        (
            ("500", "international_status", "VERIFIED_UNCAPPED", "s", "v", "2026-01-01"),
            "UNKNOWN_PLAYER_ID",
        ),
        (("7", "height", "VERIFIED_UNCAPPED", "s", "v", "2026-01-01"), "INVALID_FIELD"),
        (("7", "international_status", "UNKNOWN", "s", "v", "2026-01-01"), "INVALID_VALUE"),
        (("7", "nationality", "Martian", "s", "v", "2026-01-01"), "INVALID_VALUE"),
        (("7", "international_status", "Uncapped", "s", "v", "2026-01-01"), "LEGACY_STATUS_VALUE"),
        (("7", "international_status", "Capped", "s", "v", "2026-01-01"), "LEGACY_STATUS_VALUE"),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "", "v", "2026-01-01"),
            "MISSING_SOURCE",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "TBD", "v", "2026-01-01"),
            "MISSING_SOURCE",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "n/a", "v", "2026-01-01"),
            "MISSING_SOURCE",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "s", "", "2026-01-01"),
            "MISSING_VERIFIED_BY",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "s", "v", ""),
            "MISSING_OR_BAD_VERIFIED_DATE",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "s", "v", "01/02/2026"),
            "MISSING_OR_BAD_VERIFIED_DATE",
        ),
        (
            ("7", "international_status", "VERIFIED_UNCAPPED", "s", "v", "2026-06-02"),
            "MISSING_OR_BAD_VERIFIED_DATE",
        ),
        (
            ("1", "international_status", "VERIFIED_UNCAPPED", "s", "v", "2026-01-01"),
            "CONTRADICTS_DERIVED_EVIDENCE",
        ),
    ],
)
def test_override_validation_rejects_each_bad_row_with_its_code(row, code):
    with pytest.raises(c2.ClassificationConfigError, match=code):
        c2.validate_overrides_v2(_raw([row]), base_classification_v2(), TODAY)


def test_override_validation_collects_all_errors_and_rejects_duplicates():
    rows = [
        _good("7"),
        _good("7"),  # duplicate (7, international_status)
        ("8", "international_status", "Uncapped", "", "", "bad"),
    ]
    with pytest.raises(c2.ClassificationConfigError) as ei:
        c2.validate_overrides_v2(_raw(rows), base_classification_v2(), TODAY)
    msg = str(ei.value)
    for code in (
        "DUPLICATE_OVERRIDE",
        "LEGACY_STATUS_VALUE",
        "MISSING_SOURCE",
        "MISSING_VERIFIED_BY",
    ):
        assert code in msg
    assert "line 3" in msg and "line 4" in msg


def test_legacy_value_message_names_the_mapping():
    with pytest.raises(c2.ClassificationConfigError, match="VERIFIED_CAPPED or VERIFIED_UNCAPPED"):
        c2.validate_overrides_v2(_raw([_good(value="Uncapped")]), base_classification_v2(), TODAY)


def test_override_columns_must_match_exactly():
    with pytest.raises(c2.ClassificationConfigError, match="columns"):
        c2.validate_overrides_v2(pd.DataFrame({"player_id": []}), base_classification_v2(), TODAY)


def test_empty_overrides_leave_every_row_unchanged():
    base = base_classification_v2()
    final = c2.apply_overrides_v2(base, pd.DataFrame(columns=list(cl.OVERRIDE_COLUMNS)))
    for col in base.columns:
        pd.testing.assert_series_equal(final[col], base[col])


# ----------------------------------------------------------------------------- coverage


def test_coverage_v2_has_nine_combinations_and_separate_counts():
    base = base_classification_v2()
    ov = c2.validate_overrides_v2(
        _raw([_good("7"), _good("1", value="VERIFIED_CAPPED")]), base, TODAY
    )
    final = c2.apply_overrides_v2(base, ov)
    cov = c2.coverage_v2(final, scored_ids=range(1, 13))
    # 3 nationalities x 3 real statuses; the disabled placeholder has no combination rows.
    assert len(cov["combinations_all_players"]) == 9
    assert sum(c["players"] for c in cov["combinations_all_players"]) == 24 - 1
    assert cov["status_counts"] == {"VERIFIED_CAPPED": 1, "DERIVED_CAPPED": 11, "UNKNOWN": 11}
    assert cov["disabled_placeholder_counts"] == {"VERIFIED_UNCAPPED": 1}
    assert cov["uncapped_verified_count"] == 1 and cov["unknown_status_count"] == 11
    assert cov["unknown_status_label"] == "UNKNOWN_STATUS"
    assert cov["scored_players_total"] == 12


# ----------------------------------------------------------------------------- API surface


def test_api_exposes_separate_values_and_unknown_status_label(tmp_path):
    store = build_store(tmp_path, overrides_frame([(7, "international_status", "Uncapped")]))
    c = TestClient(create_app(store, gate_inputs=all_pass_gates()))
    items = c.get(f"{P}/players?limit=200").json()["page"]["items"]
    by = {i["player_id"]: i for i in items}
    assert by[1]["international_status"] == "DERIVED_CAPPED"
    assert by[1]["international_status_verification"] == cl.V_T20I
    assert by[8]["international_status"] == "UNKNOWN" and by[8]["group_label"] == "UNKNOWN_STATUS"
    assert by[7]["international_status"] == "VERIFIED_UNCAPPED"
    assert {i["international_status"] for i in items} <= set(c2.ACCEPTED_STORED_VALUES)
    detail = c.get(f"{P}/players/1").json()
    assert detail["derived_evidence"] == cl.V_T20I
    cov = c.get(f"{P}/meta/classification-coverage").json()["coverage"]["summary"]
    assert cov["status_counts"]["DERIVED_CAPPED"] == 12
    assert "VERIFIED_UNCAPPED" not in cov["status_counts"]
    assert cov["disabled_placeholder_counts"] == {"VERIFIED_UNCAPPED": 1}
    assert cov["unknown_status_count"] == 11
    caps = c.get(f"{P}/meta/capabilities").json()
    assert caps["classification_values"] == list(c2.STATUS_VALUES)
    assert caps["disabled_placeholder_values"] == ["VERIFIED_UNCAPPED"]
    assert caps["unknown_status_banner"] == "NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED"


def test_repository_requires_the_phase5_table_and_has_no_legacy_fallback(tmp_path):
    import duckdb

    from app.repositories.phase4_repo import StoreUnavailableError, load_tables

    store = build_store(tmp_path)
    con = duckdb.connect(str(store))
    con.execute("DROP TABLE p5_player_classification")
    con.close()
    with pytest.raises(StoreUnavailableError, match="p5_player_classification"):
        load_tables(store)


# ----------------------------------------------------------------------------- real data


@pytest.mark.realdata
def test_real_counts_recomputed_from_raw_csvs_equal_the_stored_migration():
    import duckdb

    from app.core.config import get_settings
    from app.services.pressure_service import EXPLORATORY_DB

    s = get_settings()
    if not EXPLORATORY_DB.exists() or not (Path(s.data_root) / "playing_eleven.csv").exists():
        pytest.skip("real data absent")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        have = {
            t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        if "p5_player_classification" not in have:
            pytest.skip("phase5 classification not built")
        df = con.execute("SELECT * FROM p5_player_classification").df()
    finally:
        con.close()
    counts = df["international_status"].value_counts().to_dict()
    independent = check_capped_count(Path(s.data_root), df)["independent"]  # csv module recount
    assert counts.get("DERIVED_CAPPED", 0) == independent == 655
    assert counts.get("UNKNOWN", 0) == 562
    assert counts.get("VERIFIED_CAPPED", 0) == 0 and counts.get("VERIFIED_UNCAPPED", 0) == 0
    assert len(df) == 1217 and df["player_id"].is_unique
    assert (
        df.loc[df["international_status"] == "DERIVED_CAPPED", "t20i_appearances_to_as_of"] > 0
    ).all()
    assert (df.loc[df["international_status"] == "UNKNOWN", "t20i_appearances_to_as_of"] == 0).all()
