"""Synthetic analytical store and classification frames for the Chunk 4 tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.phase4 import classification as cl
from app.phase4.store import write_p4_table
from app.phase5 import classification_v2 as c2
from app.phase5.gating import GateInput
from app.phase5.store import write_p5_table

N_PLAYERS = 24
ROLES = ["Batter", "Bowler", "All Rounder", "Wicket Keeper"]
RESTR = "innings 1-2 only; IPL/T20I only; TRAIN+VALIDATION"


def base_classification() -> pd.DataFrame:
    """Players 1-6 Indian/Capped (derived), 7-12 Indian/Unknown, 13-18 Overseas/Capped,
    19-22 Overseas/Unknown, 23-24 Unknown/Unknown."""
    rows = []
    for pid in range(1, N_PLAYERS + 1):
        if pid <= 12:
            nat = "Indian"
        elif pid <= 22:
            nat = "Overseas"
        else:
            nat = "Unknown"
        capped = pid <= 6 or 13 <= pid <= 18
        rows.append(
            {
                "player_id": pid,
                "player_name": f"Player {pid:02d}",
                "squad_team_name": None,
                "squad_role": ROLES[pid % 4] if pid <= 20 else None,
                "squad_designation": None,
                "squad_nationality_raw": None,
                "squad_match_type": "EXACT_UNIQUE" if pid <= 20 else "NO_MATCH",
                "nationality": nat,
                "nationality_verification": cl.V_DERIVED if nat != "Unknown" else cl.V_NONE,
                "nationality_source": cl.SOURCE_SQUAD if nat != "Unknown" else None,
                "nationality_unknown_reason": None if nat != "Unknown" else cl.R_NO_RECORD,
                "international_status": "Capped" if capped else "Unknown",
                "international_status_verification": cl.V_T20I if capped else cl.V_NONE,
                "international_status_source": cl.V_T20I if capped else None,
                "international_status_unknown_reason": None if capped else cl.R_NOT_PROVEN,
                "conflict_flag": False,
                "first_t20i_date": "2024-01-01" if capped else None,
                "t20i_appearances_to_as_of": 3 if capped else 0,
                "t20i_teams": "X" if capped else "",
                "as_of_date": "2025-12-31",
                "classification_version": cl.CLASSIFICATION_VERSION,
            }
        )
    return pd.DataFrame(rows)


def base_classification_v2() -> pd.DataFrame:
    """The synthetic base classification after the explicit Phase 5 migration."""
    return c2.migrate_classification(base_classification())


def all_pass_gates(strict: bool = True, min_pool: int = 0) -> GateInput:
    """Synthetic fixture in which every publication gate passes (tests only)."""
    cells = {f"{f}|{r}": "VALIDATED" for f in ("IPL", "T20I") for r in ("batter", "bowler")}
    return GateInput(
        cell_statuses=cells,
        methodology={
            "validated": True,
            "validated_by": "tester",
            "validated_date": "2026-01-01",
            "evidence_path": "synthetic",
        },
        date_gate={"passed": True, "detail": "synthetic"},
        strict_enabled=strict,
        min_public_pool=min_pool,
    )


def write_strict_config(tmp: Path) -> tuple[Path, Path]:
    """A manifest declaring an authoritative id-keyed source and a zero coverage minimum."""
    manifest = tmp / "source_manifest.json"
    manifest.write_text(
        json.dumps({"sources": [{"id": "synthetic", "authoritative": True, "id_keyed": True}]}),
        encoding="utf-8",
    )
    cfg = c2.load_config()
    cfg["min_verified_coverage"] = 0.0
    config = tmp / "classification_v2.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    return manifest, config


def score_rows() -> pd.DataFrame:
    rows = []

    def add(pid, role, stream, fmt, est, eligible, opp=40, dm=8):
        rows.append(
            {
                "status": "EXPERIMENTAL_NOT_VALIDATED",
                "official_ranking": False,
                "player_id": pid,
                "role": role,
                "stream": stream,
                "format": fmt,
                "window": "PRE_TEST",
                "definition_id": "any|q0.75",
                "definition_version": "p4_pressure_def_v1",
                "baseline_version": "p4_baseline_b0_train_frozen_v1",
                "shrinkage_config": "shrink_tau4",
                "raw_pressure_outcome": 1.5,
                "expected_baseline_outcome": 1.4,
                "residual": est * 2,
                "shrunk_estimate": est,
                "interval_low": est - 0.05,
                "interval_high": est + 0.05,
                "pressure_opportunities": opp + pid,
                "distinct_matches": dm + pid % 5,
                "effective_sample_size": 5.0 + pid / 10,
                "eligibility_status": "ELIGIBLE_WORKING_POOL_NOT_VALIDATED"
                if eligible
                else "NOT_ELIGIBLE",
                "applied_restrictions": RESTR,
                "is_carried_definition": True,
                "is_leading_provisional": False,
            }
        )

    for pid in range(1, N_PLAYERS + 1):
        add(pid, "batter", "runs", "IPL", round(0.30 - 0.01 * pid, 4), pid not in (5, 6))
        add(pid, "batter", "runs", "T20I", round(0.20 - 0.005 * pid, 4), pid <= 12)
        add(pid, "batter", "dismissal", "IPL", 0.01, True)
    for pid in range(10, N_PLAYERS + 1):
        # bowler 'charged' stream: lower shrunk runs conceded is better (score is negated)
        add(pid, "bowler", "charged", "IPL", round(-0.2 + 0.01 * pid, 4), pid != 12)
        add(pid, "bowler", "wkt", "IPL", 0.02, True)
    # a second shrinkage configuration that the loader must ignore
    extra = pd.DataFrame(rows[:5]).assign(shrinkage_config="shrink_none", shrunk_estimate=9.9)
    return pd.concat([pd.DataFrame(rows), extra], ignore_index=True)


def stats_rows() -> pd.DataFrame:
    rows = []
    for pid in range(1, N_PLAYERS + 1):
        for fmt in ("IPL", "T20I"):
            bat = 100 + 20 * pid if fmt == "IPL" else 30 + pid
            bowl = 90 + 12 * pid if pid >= 10 else 0
            rows.append(
                {
                    "player_id": pid,
                    "format": fmt,
                    "bat_matches": 10,
                    "bat_balls": bat,
                    "bat_runs": int(bat * (1.1 + pid / 100)),
                    "bat_fours": int(bat * 0.1),
                    "bat_sixes": int(bat * 0.04),
                    "bat_dismissals": max(1, bat // 25) if pid != 3 else 0,
                    "bowl_matches": 5 if bowl else 0,
                    "bowl_balls": bowl,
                    "bowl_runs": int(bowl * (1.2 + pid / 100)),
                    "bowl_wickets": bowl // 20,
                    "bowl_dots": int(bowl * 0.4),
                    "matches_played": 10 + pid,
                    "window": "PRE_TEST",
                    "restrictions": RESTR,
                }
            )
    return pd.DataFrame(rows)


def ranking_dist() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scope": "IPL",
                "role": "batter",
                "player_id": pid,
                "top10_inclusion_prob": 0.5,
                "rank_lo": 1.0,
                "rank_hi": 20.0,
            }
            for pid in range(1, 12)
        ]
    )


def build_store(
    tmp: Path, overrides: pd.DataFrame | None = None, frozen: Path | None = None
) -> Path:
    """Write a synthetic analytical store; ``overrides`` are applied to the base classification."""
    store = tmp / "synthetic_exploratory.duckdb"
    base = base_classification()
    final = cl.apply_overrides(base, overrides if overrides is not None else pd.DataFrame())
    write_p4_table(base, "p4_player_classification_base", store)
    write_p4_table(final, "p4_player_classification", store)
    base5 = c2.migrate_classification(base)
    final5 = c2.migrate_classification(final)
    write_p5_table(base5, "p5_player_classification_base", store)
    write_p5_table(final5, "p5_player_classification", store)
    write_p4_table(score_rows(), "p4_pressure_scores_frozen_rules", store)
    write_p4_table(stats_rows(), "p4_player_stats", store)
    write_p4_table(ranking_dist(), "p4_ranking_distributions", store)
    write_p5_table(
        pd.DataFrame(c2.coverage_v2(final5)["combinations_all_players"]).assign(
            population="ALL_PLAYERS"
        ),
        "p5_classification_coverage",
        store,
    )
    write_p4_table(
        pd.DataFrame({"squad_player": ["Ghost"], "match_type": ["NO_MATCH"]}),
        "p4_classification_unresolved",
        store,
    )
    if frozen is not None:
        frozen.write_text(json.dumps({"shrinkage": {"config": "shrink_tau4"}}), encoding="utf-8")
    return store


def overrides_frame(rows: list[tuple[int, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": pid,
                "field": field,
                "value": value,
                "source": "test sheet",
                "verified_by": "tester",
                "verified_date": "2026-01-01",
            }
            for pid, field, value in rows
        ],
        columns=list(cl.OVERRIDE_COLUMNS),
    )
