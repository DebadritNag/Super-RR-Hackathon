"""Phase 5 Chunk 1: classification migration (three separate capped values) and strict-uncapped status.

Reads the stored Phase 4 classification tables from the exploratory store (read-only) and the
override file, migrates the labels with the explicit mapping, and writes ``p5_`` tables to the
exploratory store plus reports to ``data/reports``. Nothing is inferred from names, domestic
experience or IPL participation. The official database and source CSVs are never modified (hashed
before and after; exit 1 on any change). Output is deterministic (no timestamps).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import classification as cl  # noqa: E402
from app.phase4.spotchecks import check_capped_count  # noqa: E402
from app.phase5 import classification_v2 as c2  # noqa: E402
from app.phase5.constants import (  # noqa: E402
    CLASSIFICATION_V2_CONFIG,
    FROZEN_CHOICES,
    REPORTS_DIR,
    SOURCE_MANIFEST,
    STATUS,
)
from app.phase5.store import write_p5_table  # noqa: E402
from app.repositories.phase4_repo import SCORES_SQL, frozen_shrinkage, pick_shrinkage, scored_ids  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def read_store(store: Path) -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return {
            "base": con.execute("SELECT * FROM p4_player_classification_base").df(),
            "final": con.execute("SELECT * FROM p4_player_classification").df(),
            "scores": pick_shrinkage(
                con.execute(SCORES_SQL).df(), frozen_shrinkage(FROZEN_CHOICES)
            ),
        }
    finally:
        con.close()


def render(res: dict[str, Any]) -> str:
    cov, cap, chk = res["coverage"], res["capability"], res["phase4_check"]
    L = [
        "# Phase 5 classification migration",
        "",
        f"Status: {STATUS}. Classification version `{c2.CLASSIFICATION_V2_VERSION}`. "
        "Nothing here is a validated cap list.",
        "",
        "## What changed",
        "`international_status` has three real **separate** values: `VERIFIED_CAPPED` "
        "(authoritative source or validated override only), `DERIVED_CAPPED` (the player appeared "
        "for a national team in an official T20I in the data on or before the as-of date), "
        "and `UNKNOWN`. `VERIFIED_UNCAPPED` is a disabled placeholder, not an established status "
        "(it needs an authoritative source or validated override, and none exists). "
        "Each row keeps its own evidence label (`international_status_verification`). `UNKNOWN` "
        f"is shown only as the group `{c2.UNKNOWN_STATUS_LABEL}` with the banner "
        f"`{c2.UNKNOWN_STATUS_BANNER}`: a player not proven capped is never labelled uncapped.",
        "",
        "## Migration mapping (explicit; any other combination is fatal)",
        md_table(
            ["Phase 4 status", "Phase 4 verification", "Phase 5 status"],
            [
                [r.phase4_status, r.phase4_verification, r.phase5_status]
                for r in res["map"].itertuples()
            ],
        ),
        "",
        "## Counts from the real data",
        md_table(
            ["Phase 5 status", "players", "Phase 4 label", "Phase 4 players"],
            [
                [
                    "VERIFIED_CAPPED",
                    cov["status_counts"]["VERIFIED_CAPPED"],
                    "Capped (VERIFIED_FROM_SOURCE)",
                    res["p4_verified_capped"],
                ],
                [
                    "DERIVED_CAPPED",
                    cov["status_counts"]["DERIVED_CAPPED"],
                    "Capped (DERIVED_FROM_OFFICIAL_T20I_APPEARANCES)",
                    chk["phase4_capped"],
                ],
                [
                    "VERIFIED_UNCAPPED (disabled placeholder)",
                    cov["disabled_placeholder_counts"]["VERIFIED_UNCAPPED"],
                    "Uncapped",
                    chk["phase4_uncapped"],
                ],
                [
                    "UNKNOWN (UNKNOWN_STATUS)",
                    cov["status_counts"]["UNKNOWN"],
                    "Unknown",
                    chk["phase4_unknown"],
                ],
            ],
        ),
        "",
        f"Players total: {cov['players_total']}. Phase 4 coverage JSON agrees "
        f"(capped {chk['phase4_capped']}, uncapped {chk['phase4_uncapped']}, unknown "
        f"{chk['phase4_unknown']}); the migration asserts this and stops on any mismatch.",
        "",
        "### Independent recount",
        f"- DERIVED_CAPPED recounted from `competitions.csv`, `matches.csv` and `playing_eleven.csv` "
        f"with the csv module: **{res['independent_capped']}** (stored {cov['derived_capped_count']}).",
        "",
        "### Nationality x status (all players)",
        md_table(
            ["nationality", "international_status", "players"],
            [
                [r["nationality"], r["international_status"], r["players"]]
                for r in cov["combinations_all_players"]
            ],
        ),
        "",
        f"### Nationality x status (scored players, {cov['scored_players_total']})",
        md_table(
            ["nationality", "international_status", "players"],
            [
                [r["nationality"], r["international_status"], r["players"]]
                for r in cov["combinations_scored_players"]
            ],
        ),
        "",
        "### Evidence labels and reasons",
        f"- status verification: {cov['status_verification']}",
        f"- nationality verification: {cov['nationality_verification']}",
        f"- UNKNOWN reasons: {cov['status_unknown_reasons']}",
        "",
        "## Dates",
        "DERIVED_CAPPED uses T20I matches dated on or before the as-of date "
        f"`{res['as_of']}`. The 42 T20I matches with disputed dates are all later than that date, "
        "so no DERIVED_CAPPED count depends on them.",
        "",
        "## No inference",
        "The migration reads only the stored classification table (built from T20I playing-eleven "
        "appearances). It imports no names, squad, domestic or IPL tables and never infers capped "
        "status from them. A player with IPL matches and no T20I stays `UNKNOWN`.",
        "",
        "## Overrides",
        f"- Override file rows loaded and validated: {res['overrides_loaded']}. The file stays "
        "header-only and unchanged.",
        "- A row needs `player_id`, `field`, `value`, `source`, `verified_by`, `verified_date` "
        "(ISO, not in the future). Legacy `Capped`/`Uncapped` values are rejected with the mapping "
        "named. A `VERIFIED_UNCAPPED` row for a `DERIVED_CAPPED` player is rejected "
        "(`CONTRADICTS_DERIVED_EVIDENCE`).",
        "",
        "## Strict uncapped capability",
        f"- `strict_uncapped_enabled`: **{cap['enabled']}** (computed, never hand-set).",
        f"- reasons: {cap['reasons']}",
        f"- authoritative id-keyed sources declared: {cap['authoritative_sources']}; verified rows: "
        f"{cap['verified_rows']}; verified coverage of the scored pool: {cap['verified_coverage']} "
        f"(minimum {cap['min_verified_coverage']}, provisional; scored pool {cap['scored_pool_size']}).",
        "- While disabled, every uncapped ranking, uncapped preset, uncapped filter and uncapped "
        "composition constraint answers `STRICT_UNCAPPED_DISABLED` with the reason, the source "
        "needed and no rows. No approximation is produced.",
        f"- Source needed: {cap['source_needed']}",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--overrides", type=Path, default=cl.OVERRIDES_FILE)
    ap.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    ap.add_argument("--config", type=Path, default=CLASSIFICATION_V2_CONFIG)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    data = read_store(args.store)
    cfg = c2.load_config(args.config)
    phase4_cov = json.loads(
        (args.reports / "phase4_classification_coverage.json").read_text(encoding="utf-8")
    )

    base5 = c2.migrate_classification(data["base"])
    overrides = c2.load_overrides_v2(args.overrides, base5)
    final5 = c2.apply_overrides_v2(base5, overrides)
    phase4_check = c2.assert_matches_phase4_coverage(final5, phase4_cov)
    scored = sorted(scored_ids(data["scores"]))
    cov = c2.coverage_v2(final5, scored)
    capability = c2.strict_uncapped_capability(
        final5, c2.load_source_manifest(args.manifest), scored, cfg
    )
    independent = check_capped_count(s.data_root, final5)["independent"]
    mapping = c2.migration_map_frame()

    write_p5_table(base5, "p5_player_classification_base", args.store)
    write_p5_table(final5, "p5_player_classification", args.store)
    write_p5_table(mapping, "p5_classification_migration_map", args.store)
    rows = pd.DataFrame(cov["combinations_all_players"]).assign(population="ALL_PLAYERS")
    rows = pd.concat(
        [rows, pd.DataFrame(cov["combinations_scored_players"]).assign(population="SCORED_PLAYERS")]
    )
    write_p5_table(rows, "p5_classification_coverage", args.store)
    cap_row = pd.DataFrame(
        [
            {
                "enabled": capability["enabled"],
                "reasons": ",".join(capability["reasons"]),
                "verified_coverage": capability["verified_coverage"],
                "min_verified_coverage": capability["min_verified_coverage"],
                "scored_pool_size": capability["scored_pool_size"],
                "verified_rows": capability["verified_rows"],
                "authoritative_sources": capability["authoritative_sources"],
            }
        ]
    )
    write_p5_table(cap_row, "p5_strict_uncapped_capability", args.store)

    out = args.reports
    res = {
        "coverage": cov,
        "capability": capability,
        "phase4_check": phase4_check,
        "map": mapping,
        "independent_capped": independent,
        "as_of": str(final5["as_of_date"].iloc[0])[:10],
        "overrides_loaded": int(len(overrides)),
        "p4_verified_capped": int(
            (
                (data["final"]["international_status"] == "Capped")
                & (data["final"]["international_status_verification"] == cl.V_SOURCE)
            ).sum()
        ),
    }
    write_text(out / "phase5_classification_migration.md", render(res))
    write_json_deterministic(
        out / "phase5_classification_migration.json",
        {
            "status": STATUS,
            "classification_version": c2.CLASSIFICATION_V2_VERSION,
            "migration_map": mapping,
            "coverage": cov,
            "phase4_comparison": phase4_check,
            "independent_derived_capped_recount": independent,
            "strict_uncapped_capability": capability,
            "overrides_loaded": int(len(overrides)),
        },
    )
    rows.to_csv(out / "phase5_classification_coverage.csv", index=False, lineterminator="\n")
    cols = [
        "player_id", "player_name", "nationality", "nationality_verification",
        "international_status", "international_status_verification", "status_display",
        "status_reason", "legacy_international_status", "derived_evidence",
        "t20i_appearances_to_as_of", "first_t20i_date", "conflict_flag",
    ]  # fmt: skip
    final5[cols].to_csv(out / "phase5_classification.csv", index=False, lineterminator="\n")
    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("players:", len(final5), cov["status_counts"], "independent capped:", independent)
    print("strict_uncapped_enabled:", capability["enabled"], capability["reasons"])
    print("official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
