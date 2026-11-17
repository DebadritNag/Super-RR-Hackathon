"""Phase 4 Chunk 4: player classification, descriptive player stats and coverage reports.

Reads the official DuckDB and the squad CSV read-only, writes only ``p4_`` tables to the
exploratory store and reports to ``data/reports``. Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import md_table, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import classification as cl  # noqa: E402
from app.phase4.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase4.serving import build_player_stats, run_classification  # noqa: E402
from app.phase4.store import write_p4_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402
from app.utils.jsonio import write_json  # noqa: E402


def scored_player_ids(store: Path) -> list[int]:
    con = duckdb.connect(str(store), read_only=True)
    try:
        tables = {
            t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        if "p4_pressure_scores_frozen_rules" not in tables:
            return []
        return [
            int(r[0])
            for r in con.execute(
                "SELECT DISTINCT player_id FROM p4_pressure_scores_frozen_rules "
                "WHERE is_carried_definition AND eligibility_status LIKE 'ELIGIBLE%'"
            ).fetchall()
        ]
    finally:
        con.close()


def render(res: dict, scored: list[int]) -> str:
    cov, built = res["coverage"], res["built"]
    ev, unres = built["evidence"], built["unresolved"]
    exact = ev[ev["match_type"] == "EXACT_UNIQUE"]
    L = [
        "# Phase 4 player classification coverage",
        "",
        f"Status: {STATUS}. Classification version `{res['version']}`, as-of date "
        f"`{res['config']['as_of_date']}`. Built only from records in the data; nothing is "
        "taken from memory or outside sources.",
        "",
        "## What the records contain",
        f"- `ipl squad.csv`: {len(ev)} rows. The `nationality` column holds Indian/Overseas. The "
        "`designation` column holds only `Captain` or blank, so **the squad file carries no "
        "capped/uncapped information**.",
        "- `competition_team_player_mapping.csv`, `ball_by_ball.csv` and `playing_eleven.csv` carry no "
        "nationality or cap status.",
        f"- Squad rows resolved to exactly one player_id by exact name: {len(exact)} of {len(ev)}; "
        f"corroborated by the player's IPL 2026 team (id-keyed): "
        f"{int(exact['team_corroborated'].sum())}; unresolved or ambiguous: {len(unres)}.",
        "",
        "## Coverage, all players (nationality x international status)",
        md_table(
            ["nationality", "international_status", "players"],
            [
                [r["nationality"], r["international_status"], r["players"]]
                for r in cov["combinations_all_players"]
            ],
        ),
        "",
        f"Players total: {cov['players_total']}. Verified Uncapped players: "
        f"**{cov['uncapped_verified_count']}**. Conflicts flagged: {cov['conflicts']}.",
    ]
    if "combinations_scored_players" in cov:
        L += [
            "",
            f"## Coverage, players with an eligible experimental score ({cov['scored_players_total']})",
            md_table(
                ["nationality", "international_status", "players"],
                [
                    [r["nationality"], r["international_status"], r["players"]]
                    for r in cov["combinations_scored_players"]
                ],
            ),
        ]
    L += [
        "",
        "## Verification labels",
        f"- nationality: {cov['nationality_verification']}",
        f"- international status: {cov['status_verification']}",
        "",
        "## Why players are Unknown",
        f"- nationality: {cov['nationality_unknown_reasons']}",
        f"- international status: {cov['status_unknown_reasons']}",
        "",
        "## Rules applied",
        "- Capped is DERIVED_FROM_OFFICIAL_T20I_APPEARANCES only: the player was listed as playing in "
        "a T20I in the data on or before the as-of date. This is derived evidence, never a verified "
        "cap list.",
        "- Uncapped is never derived. A player absent from the T20I data stays Unknown "
        "(`NOT_PROVEN_CAPPED_IN_DATA`) because the data starts in 2022 and says nothing about earlier caps.",
        "- Nationality comes from the squad row only when the name is unique and the team corroborates "
        "it through ids; otherwise it can be derived from T20I national-team appearances "
        "(`DERIVED_FROM_T20I_NATIONAL_TEAM`), and a franchise team never implies nationality.",
        "- Overrides: `config/classification_overrides_v1.csv` (empty by default).",
        f"- Overrides loaded: {len(res['overrides'])}.",
        "",
        "## What is needed to populate Uncapped",
        res["config"]["source_needed"],
        "",
        "## Unresolved squad names (not applied)",
        md_table(
            ["squad_player", "team", "match_type", "candidate_ids", "corroborated_variant"],
            [
                [
                    r.squad_player,
                    r.squad_team_name,
                    r.match_type,
                    r.candidate_ids,
                    r.variant_team_corroborated,
                ]
                for r in unres.itertuples(index=False)
            ],
        ),
    ]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--official-db", type=Path, default=s.duckdb_path)
    ap.add_argument("--squad", type=Path, default=s.squad_csv)
    ap.add_argument("--overrides", type=Path, default=cl.OVERRIDES_FILE)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    scored = scored_player_ids(args.store)
    res = run_classification(
        args.official_db, args.store, args.squad, args.overrides, scored_ids=scored or None
    )
    stats = build_player_stats(args.store, args.official_db)
    write_p4_table(stats, "p4_player_stats", args.store)
    out = args.reports
    final: pd.DataFrame = res["final"]
    final.to_csv(out / "phase4_classification.csv", index=False)
    res["built"]["unresolved"].to_csv(out / "phase4_unresolved_players.csv", index=False)
    write_json(out / "phase4_classification_coverage.json", res["coverage"])
    write_text(out / "phase4_classification_coverage_report.md", render(res, scored))
    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("players:", len(final), "uncapped verified:", res["coverage"]["uncapped_verified_count"])
    print("stats rows:", len(stats), "official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
