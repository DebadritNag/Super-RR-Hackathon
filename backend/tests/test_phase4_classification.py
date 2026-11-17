"""Classification pipeline, overrides, coverage and filters (Chunk 4)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from app.phase4 import classification as cl
from app.phase4 import uncapped as unc
from app.phase5 import classification_v2 as c2
from tests.phase4_api_helpers import (
    base_classification,
    base_classification_v2,
    overrides_frame,
)


def _cfg():
    cfg = cl.load_config()
    cfg["squad_corroboration"] = {"min_resolved_rows_per_team": 2, "min_plurality_share": 0.8}
    return cfg


def _inputs():
    names = {i: f"Player {i}" for i in range(1, 17)}
    names[7] = names[8] = "Twin Name"
    names[9] = "Victor Name"
    players = pd.DataFrame(
        {
            "player_id": list(names),
            "player_name": list(names.values()),
            "name_variants": [json.dumps([n]) for n in names.values()],
        }
    )
    players.loc[players["player_id"] == 9, "name_variants"] = json.dumps(
        ["Victor Name", "Vee Name"]
    )
    team = {1: 100, 2: 100, 13: 100, 14: 100, 3: 200, 4: 200, 5: 200, 6: 200}
    mapping = pd.DataFrame({"player_id": list(team), "team_id": list(team.values())})
    squad = pd.DataFrame(
        [
            ("1", "T1", "Player 1", "Indian"),
            ("1", "T1", "Player 2", "Overseas"),
            ("1", "T1", "Player 13", "Indian"),
            ("1", "T1", "Player 14", "Indian"),
            ("1", "T1", "Player 3", "Indian"),  # team mismatch: uncorroborated
            ("2", "T2", "Player 4", "Overseas"),
            ("2", "T2", "Player 5", "Indian"),
            ("2", "T2", "Player 6", "Indian"),
            ("2", "T2", "Twin Name", "Indian"),  # two ids share the name
            ("2", "T2", "Vee Name", "Indian"),  # spelling variant only
            ("2", "T2", "Ghost", "Indian"),  # nobody
        ],
        columns=["team_no", "team_name", "player", "nationality"],
    ).assign(role="Batter", designation="", squad_row=lambda d: range(1, len(d) + 1))
    t20i = pd.DataFrame(
        [
            (2, "England", "2024-01-01"),
            (4, "India", "2023-05-01"),
            (3, "Australia", "2024-02-01"),
            (10, "India", "2024-03-01"),
            (11, "India", "2024-03-01"),
            (11, "England", "2024-04-01"),
            (12, "India", "2026-02-01"),
        ],
        columns=["player_id", "team_name", "match_date"],
    )
    return players, squad, mapping, t20i


@pytest.fixture(scope="module")
def built():
    players, squad, mapping, t20i = _inputs()
    out = cl.build_classification(players, squad, mapping, t20i, _cfg())
    return out["classification"].set_index("player_id"), out


def test_squad_nationality_applied_only_with_unique_name_and_team_corroboration(built):
    c, _ = built
    assert (c.loc[1, "nationality"], c.loc[1, "nationality_verification"]) == (
        "Indian",
        cl.V_DERIVED,
    )
    assert c.loc[1, "nationality_source"] == cl.SOURCE_SQUAD
    assert c.loc[2, "nationality"] == "Overseas"


def test_no_name_only_merge(built):
    c, out = built
    # player 3: unique name, but his IPL team does not match the squad team group
    assert c.loc[3, "nationality_source"] != cl.SOURCE_SQUAD
    assert str(c.loc[3, "nationality_source"]).startswith(cl.SOURCE_NATIONAL_TEAM)
    # ambiguous name: neither id receives the squad nationality
    for pid in (7, 8):
        assert c.loc[pid, "nationality"] == "Unknown"
        assert c.loc[pid, "nationality_unknown_reason"] == cl.R_AMBIGUOUS
    # spelling variant is only a candidate: never applied
    assert c.loc[9, "nationality"] == "Unknown"
    assert c.loc[9, "nationality_unknown_reason"] == cl.R_VARIANT
    un = out["unresolved"]
    assert set(un["squad_player"]) == {"Twin Name", "Vee Name", "Ghost"}
    assert "9" in set(un["candidate_ids"])


def test_capped_is_derived_from_t20i_appearances_only(built):
    c, _ = built
    assert c.loc[2, "international_status"] == "Capped"
    assert c.loc[2, "international_status_verification"] == cl.V_T20I
    assert c.loc[2, "international_status_source"] == cl.V_T20I
    assert c.loc[2, "international_status_verification"] != cl.V_SOURCE


def test_never_appearing_is_not_uncapped(built):
    c, _ = built
    assert c.loc[5, "international_status"] == "Unknown"
    assert c.loc[5, "international_status_unknown_reason"] == cl.R_NOT_PROVEN
    assert c.loc[15, "international_status"] == "Unknown"
    assert (c["international_status"] == "Uncapped").sum() == 0


def test_debut_after_as_of_date_is_not_capped(built):
    c, _ = built
    assert c.loc[12, "international_status"] == "Unknown"
    assert c.loc[12, "international_status_unknown_reason"] == cl.R_AFTER
    assert c.loc[12, "first_t20i_date"] == "2026-02-01"


def test_national_team_derivation_and_mixed_teams(built):
    c, _ = built
    assert c.loc[10, "nationality"] == "Indian"
    assert c.loc[10, "nationality_source"].startswith(cl.SOURCE_NATIONAL_TEAM)
    assert c.loc[11, "nationality"] == "Unknown"
    assert c.loc[11, "nationality_unknown_reason"] == cl.R_MIXED
    assert c.loc[11, "international_status"] == "Capped"  # fields are independent


def test_conflicts_are_flagged_and_squad_value_kept(built):
    c, _ = built
    assert c.loc[4, "nationality"] == "Overseas" and bool(c.loc[4, "conflict_flag"])
    assert bool(c.loc[3, "conflict_flag"])  # uncorroborated squad Indian vs derived Overseas


def test_unknown_stays_unknown(built):
    c, _ = built
    for pid in (15, 16):
        assert c.loc[pid, "nationality"] == "Unknown"
        assert c.loc[pid, "nationality_verification"] == cl.V_NONE
        assert c.loc[pid, "international_status"] == "Unknown"


def test_four_combinations_are_independent_via_overrides(built):
    c, _ = built
    base = c.reset_index()
    ov = overrides_frame(
        [
            (5, "international_status", "Uncapped"),  # Indian + Uncapped
            (15, "nationality", "Overseas"),
            (15, "international_status", "Uncapped"),  # Overseas + Uncapped
            (16, "nationality", "Indian"),
            (16, "international_status", "Capped"),  # Indian + Capped
            (4, "international_status", "Capped"),  # Overseas + Capped (derived Indian conflict)
        ]
    )
    final = cl.apply_overrides(base, ov).set_index("player_id")
    combos = {
        (final.loc[p, "nationality"], final.loc[p, "international_status"]) for p in (5, 15, 16, 4)
    }
    assert combos == {
        ("Indian", "Uncapped"),
        ("Overseas", "Uncapped"),
        ("Indian", "Capped"),
        ("Overseas", "Capped"),
    }
    assert final.loc[15, "international_status_verification"] == cl.V_SOURCE
    assert final.loc[15, "international_status_source"] == "MANUAL_OVERRIDE:test sheet"
    # changing one field never changes the other
    assert final.loc[5, "nationality"] == c.loc[5, "nationality"]
    cov = cl.coverage(final.reset_index())
    assert len(cov["combinations_all_players"]) == 9
    assert cov["uncapped_verified_count"] == 2


def test_override_flags_disagreement_with_derived_evidence(built):
    c, _ = built
    final = cl.apply_overrides(
        c.reset_index(), overrides_frame([(2, "international_status", "Uncapped")])
    ).set_index("player_id")
    assert final.loc[2, "international_status"] == "Uncapped"
    assert bool(final.loc[2, "conflict_flag"])


def _load(tmp_path, rows, header=None):
    p = tmp_path / "ov.csv"
    head = header or ",".join(cl.OVERRIDE_COLUMNS)
    p.write_text("\n".join([head, *rows]) + "\n", encoding="utf-8")
    return cl.load_overrides(p, range(1, 100))


def test_override_file_shipped_is_header_only():
    df = cl.load_overrides(cl.OVERRIDES_FILE, [1, 2])
    assert df.empty
    assert cl.OVERRIDES_FILE.read_text(encoding="utf-8").strip() == ",".join(cl.OVERRIDE_COLUMNS)


def test_override_validation_accepts_good_rows(tmp_path):
    df = _load(tmp_path, ["5,nationality,Indian,sheet A,Ann,2026-01-02"])
    assert len(df) == 1 and df.loc[0, "player_id"] == 5


@pytest.mark.parametrize(
    "row",
    [
        "x,nationality,Indian,s,v,2026-01-01",  # id not an integer
        "500,nationality,Indian,s,v,2026-01-01",  # unknown player
        "5,height,Indian,s,v,2026-01-01",  # unknown field
        "5,nationality,Martian,s,v,2026-01-01",  # value outside enum
        "5,international_status,Unknown,s,v,2026-01-01",  # Unknown is not a verified value
        "5,nationality,Indian,,v,2026-01-01",  # empty source
        "5,nationality,Indian,s,,2026-01-01",  # empty verified_by
        "5,nationality,Indian,s,v,01/02/2026",  # not ISO
    ],
)
def test_override_validation_rejects_bad_rows(tmp_path, row):
    with pytest.raises(cl.ClassificationConfigError):
        _load(tmp_path, [row])


def test_override_validation_rejects_duplicates_and_bad_columns(tmp_path):
    with pytest.raises(cl.ClassificationConfigError, match="duplicate"):
        _load(
            tmp_path,
            ["5,nationality,Indian,s,v,2026-01-01", "5,nationality,Overseas,s,v,2026-01-01"],
        )
    with pytest.raises(cl.ClassificationConfigError, match="columns"):
        _load(tmp_path, [], header="player_id,field,value")


def test_derived_never_counts_as_verified_uncapped():
    cls = unc.effective_classification(
        base_classification_v2(), unc.ClassificationBasis.INCLUDE_DERIVED_CAPPED
    )
    assert not unc.verified_uncapped_mask(cls).any()
    assert not (cls["international_status"] == "VERIFIED_UNCAPPED").any()


def test_verified_only_basis_masks_derived_values():
    cls = unc.effective_classification(
        base_classification_v2(), unc.ClassificationBasis.VERIFIED_ONLY
    )
    assert set(cls["eff_status"]) == {"UNKNOWN"}
    assert set(cls["eff_nationality"]) == {"Unknown"}
    assert set(cls["eff_status_verification"]) == {cl.V_NONE}


def _view(overrides):
    # Phase 5 mapping: the legacy override labels are migrated explicitly before filtering
    base = c2.migrate_classification(cl.apply_overrides(base_classification(), overrides))
    d = unc.effective_classification(base, unc.ClassificationBasis.INCLUDE_DERIVED_CAPPED)
    d["matches"] = d["player_id"]
    d["distinct_matches"] = d["player_id"] % 7
    return d


def test_filters():
    ov = overrides_frame(
        [(7, "international_status", "Uncapped"), (19, "international_status", "Uncapped")]
    )
    d = _view(ov)
    F = unc.FilterParams
    CF = unc.ClassificationFilter
    ids = lambda p: set(unc.apply_filters(d, p)["player_id"])  # noqa: E731
    assert ids(F(CF.indian_uncapped)) == {7}
    assert ids(F(CF.overseas_uncapped)) == {19}
    assert ids(F(CF.all_uncapped)) == {7, 19}
    assert ids(F(CF.capped_any)) == set(range(1, 7)) | set(range(13, 19))
    assert ids(F(CF.capped_derived)) == set(range(1, 7)) | set(range(13, 19))
    assert ids(F(CF.capped_verified)) == set()  # nobody is VERIFIED_CAPPED
    assert 7 not in ids(F(CF.unknown_international_status)) and 8 in ids(
        F(CF.unknown_international_status)
    )
    assert ids(F(uncapped_mode=unc.UncappedMode.exclude_uncapped)) == set(range(1, 25)) - {7, 19}
    assert ids(F(uncapped_mode=unc.UncappedMode.include_uncapped)) == set(range(1, 25))
    assert ids(F(CF.all_uncapped, min_matches=10)) == {19}
    assert ids(F(CF.all_uncapped, min_pressure_matches=1)) == {19}  # player 7 has 0 (7 % 7)
    with pytest.raises(unc.FilterError):
        unc.apply_filters(d, F(CF.all_uncapped, unc.UncappedMode.exclude_uncapped))


def test_unverified_candidates_are_a_separate_unknown_status_list():
    d = _view(overrides_frame([(7, "international_status", "Uncapped")]))
    cand = unc.unverified_candidates(d, unc.UncappedKind.indian_batters)
    assert 7 not in set(cand["player_id"])
    assert set(cand["eff_status"]) == {"UNKNOWN"} and set(cand["eff_nationality"]) == {"Indian"}
