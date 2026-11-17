"""Phase 5 Chunk 2: T20I date verification and restricted TEST-set manifest (read-only, lock respected).

Never modifies the official database, the source CSVs or any Phase 4 file. Never opens TEST: only
identity columns of TEST matches are read (no outcome columns). Cricsheet is read here as
secondary, validation-only evidence. Deterministic (no timestamps). Writes p5_ tables to the
exploratory store and the phase5_* reports.

Usage: python scripts/phase5_date_verification.py [--official-csv PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.phase4.config import load_split_config  # noqa: E402
from app.phase4.store import OFFICIAL_DB  # noqa: E402
from app.phase5 import date_verification as dv  # noqa: E402
from app.phase5 import test_manifest as tm  # noqa: E402
from app.phase5.constants import CONFIG_DIR, DATE_SUMMARY, REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.data import load_test_match_state_nonoutcome  # noqa: E402
from app.phase5.lockguard import (  # noqa: E402
    PHASE5_LOCK_LOG,
    assert_phase4_lock_untouched,
    assert_phase5_lock_not_opened,
    file_sha256,
    phase4_lock_events,
)
from app.phase5.store import write_p5_table  # noqa: E402

DATA = Path("d:/Data")
CFG_PATH = CONFIG_DIR / "phase5_date_verification_v1.json"
TEMPLATE = CONFIG_DIR / "t20i_official_date_verification_template.csv"
DEFAULT_OFFICIAL = CONFIG_DIR / "t20i_official_date_verification.csv"
CS_INDEX = ROOT / "data" / "staging" / "cricsheet_index.parquet"
PRERUN = Path("d:/Data/.agents/tasks/phase5_prerun_hashes.json")
SOURCE_CSVS = ("matches.csv", "updated_ball_by_ball.csv", "competitions.csv", "matches 2026.csv")

EVIDENCE_COLS = [
    "match_id", "comp_id", "comp_name", "competition_type", "match_number", "home_team", "away_team",
    "original_match_date", "late_after_cutoff", "has_deliveries", "in_phase4_state", "state_deliveries",
    "ts_first_date", "ts_last_date", "ts_diff_first_days", "ts_diff_last_days", "timestamp_informative",
    "ts_status", "ordering_consistent", "ordering_detail", "double_booking", "season_token_status",
    "m26_status", "m26_date", "m26_diff_days", "cs_status", "cs_match_id", "cs_dir", "cs_date",
    "cs_diff_days", "cs_candidates", "n_agreeing_sources", "agreeing_sources", "n_conflicting_sources",
    "conflicting_sources", "internal_conflicts", "date_class", "official_verified", "official_status",
    "official_date",
]  # fmt: skip


def date_column_hash(db: Path) -> str:
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute("SELECT match_id, match_date FROM matches ORDER BY match_id").fetchall()
    finally:
        con.close()
    return tm.sha256_json([[int(i), str(d)[:10]] for i, d in rows])


def source_hashes() -> dict[str, str]:
    return {n: file_sha256(DATA / n) for n in SOURCE_CSVS}


def load_inputs(db: Path, test_start: str):
    con = duckdb.connect(str(db), read_only=True)
    try:
        matches = con.execute("SELECT * FROM matches ORDER BY match_id").df()
        ts = con.execute(
            "SELECT CAST(match_id AS INTEGER) AS match_id, count(*) AS n_rows, "
            "sum(CASE WHEN substr(delivery_ist_time, 12, 8) <> '00:00:00' THEN 1 ELSE 0 END) "
            "AS n_nonmidnight, "
            "min(CASE WHEN substr(delivery_ist_time, 12, 8) <> '00:00:00' THEN delivery_ist_time END) "
            "AS min_ts, "
            "max(CASE WHEN substr(delivery_ist_time, 12, 8) <> '00:00:00' THEN delivery_ist_time END) "
            "AS max_ts FROM raw_ball_by_ball_updated GROUP BY 1"
        ).df()
        fi = con.execute(
            "SELECT match_id, batting_team_id, source_total_runs AS total_runs FROM innings "
            "WHERE innings_number = 1"
        ).df()
    finally:
        con.close()
    return matches, ts, fi


def csv_recompute(ids: list[int]) -> dict[int, str]:
    """Independent read of the original match dates straight from matches.csv."""
    out: dict[int, str] = {}
    with (DATA / "matches.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["match_id"]) in ids:
                out[int(r["match_id"])] = r["match_date"][:10]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--official-csv", default=str(DEFAULT_OFFICIAL))
    args = ap.parse_args()

    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    split_cfg = load_split_config()
    core_end = str(split_cfg["test_core_end"])
    test_start = str(split_cfg["periods"]["TEST"]["start"])
    assert core_end == cfg["late_cutoff"], "late cutoff must equal the split test_core_end"

    prerun = json.loads(PRERUN.read_text(encoding="utf-8"))
    lock_sha = prerun["phase4_reports"]["d:/Data/backend/data/reports/phase4_lock_log.json"].lower()
    lock_before = assert_phase4_lock_untouched(lock_sha)
    lock_events = phase4_lock_events()
    if not PHASE5_LOCK_LOG.exists():
        write_text(PHASE5_LOCK_LOG, "[]")
    assert_phase5_lock_not_opened()
    db_before = file_sha256(OFFICIAL_DB)
    dates_before = date_column_hash(OFFICIAL_DB)
    src_before = source_hashes()

    matches, ts, fi = load_inputs(OFFICIAL_DB, test_start)
    comps = pd.read_csv(DATA / "competitions.csv")
    scope = matches["competition_type"].isin(["IPL", "T20I"])
    late = (matches["competition_type"] == "T20I") & (
        matches["match_date"] > pd.Timestamp(core_end)
    )
    test_ids = matches["match_date"] >= pd.Timestamp(test_start)
    targets = matches[scope & (late | test_ids)].copy()

    t20i_ids = {int(i) for i in matches[matches["competition_type"] == "T20I"]["match_id"]}
    orig = {int(r.match_id): r.match_date.date() for r in matches.itertuples()}
    cs = dv.load_cricsheet_index(CS_INDEX, test_start)
    m26 = dv.load_matches_2026(DATA / "matches 2026.csv")
    official = dv.load_official_verification(args.official_csv, t20i_ids, orig)

    check = dv.build_date_check(matches, targets, comps, ts, fi, cs, m26, official, cfg)

    state = load_test_match_state_nonoutcome()
    state_ids = {int(i) for i in state["match_id"].unique()}
    deliv = state.groupby("match_id").size().to_dict()
    check["in_phase4_state"] = check["match_id"].isin(state_ids)
    check["state_deliveries"] = check["match_id"].map(lambda i: int(deliv.get(i, 0)))
    check = check[EVIDENCE_COLS].reset_index(drop=True)
    late42 = check[check["late_after_cutoff"] & (check["competition_type"] == "T20I")].copy()

    comp_type = {int(r.match_id): r.competition_type for r in check.itertuples()}
    membership = tm.build_membership(check, core_end, state_ids)
    inputs = {
        "date_verification_config_sha256": file_sha256(CFG_PATH),
        "split_config_sha256": file_sha256(CONFIG_DIR / "phase4_split_v1.json"),
        "matches_date_column_sha256": dates_before,
        "date_check_table_sha256": tm.sha256_json(check.astype(str).values.tolist()),
        "phase4_lock_log_sha256": lock_before,
        "official_verification_rows": int(len(official["official"])),
    }
    absent = check[~check["in_phase4_state"]]
    extra = {
        "test_matches_in_matches_table_not_in_phase4_state": [
            {
                "match_id": int(r.match_id),
                "original_match_date": r.original_match_date,
                "competition_type": r.competition_type,
                "has_deliveries": bool(r.has_deliveries),
                "deliveries": int(r.state_deliveries),
            }
            for r in absent.itertuples()
        ],
        "future_lock_log": "d:/Data/backend/data/reports/phase5_lock_log.json (empty; never opened)",
    }
    manifest = tm.build_manifest(membership, check, state, comp_type, core_end, inputs, extra)

    # ------------------------------------------------ post-run guards
    db_after = file_sha256(OFFICIAL_DB)
    dates_after = date_column_hash(OFFICIAL_DB)
    src_after = source_hashes()
    lock_after = assert_phase4_lock_untouched(lock_sha)
    events_p5 = assert_phase5_lock_not_opened()
    csv_dates = csv_recompute({int(i) for i in late42["match_id"]})
    originals_equal = all(
        csv_dates[int(r.match_id)] == r.original_match_date for r in late42.itertuples()
    )
    guards = {
        "official_db_unchanged": db_before == db_after,
        "matches_date_column_unchanged": dates_before == dates_after,
        "source_csvs_unchanged": src_before == src_after,
        "phase4_lock_log_sha256_before": lock_before,
        "phase4_lock_log_sha256_after": lock_after,
        "phase4_lock_log_unchanged": lock_before == lock_after,
        "phase4_lock_events": lock_events,
        "phase5_lock_log_events": events_p5,
        "phase5_test_opened": False,
        "late42_originals_equal_matches_csv": originals_equal,
    }
    assert all(v for k, v in guards.items() if isinstance(v, bool) and k != "phase5_test_opened")

    # ------------------------------------------------ outputs
    dist42 = late42["date_class"].value_counts().reindex(dv.CLASSES, fill_value=0)
    dist_all = check["date_class"].value_counts().reindex(dv.CLASSES, fill_value=0)
    n_off = int((late42["official_status"] == "OFFICIAL_VERIFIED").sum())
    gate = {
        "passed": bool(len(late42) > 0 and n_off == len(late42)),
        "detail": f"{n_off} of {len(late42)} late T20I matches are official-verified; "
        f"classes {dict(dist42)}; none verified against an authoritative record unless supplied",
    }
    summary = {
        "status": STATUS,
        "statement": dv.NOT_OFFICIAL_STATEMENT,
        "late_cutoff": core_end,
        "n_late_t20i_matches": len(late42),
        "class_distribution_late42": {k: int(v) for k, v in dist42.items()},
        "class_distribution_all_test_matches": {k: int(v) for k, v in dist_all.items()},
        "official_verified_late42": n_off,
        "official_incomplete_rows": official["incomplete"],
        "official_date_differs_rows": int(len(official["differs"])),
        "guards": guards,
        "manifest_self_sha256": manifest["self_sha256"],
        "gate": gate,
        "late42": late42.where(late42.notna(), None).to_dict(orient="records"),
    }
    write_p5_table(late42, "p5_t20i_date_verification")
    write_p5_table(check, "p5_test_match_date_check")
    write_p5_table(membership, "p5_test_set_membership")
    write_p5_table(
        pd.DataFrame(
            [
                {"set_name": s, "matches": v["counts"]["matches"], "deliveries": v["counts"]["deliveries"],
                 "players": v["counts"]["players"], "ids_sha256": v["ids_and_original_dates_sha256"]}
                for s, v in manifest["sets"].items()
            ]
        ),
        "p5_test_set_manifest",
    )  # fmt: skip
    late42.to_csv(
        REPORTS_DIR / "phase5_t20i_date_verification.csv", index=False, lineterminator="\n"
    )
    check.to_csv(REPORTS_DIR / "phase5_test_match_date_check.csv", index=False, lineterminator="\n")
    write_json_deterministic(DATE_SUMMARY, summary)
    write_json_deterministic(REPORTS_DIR / "phase5_test_set_manifest.json", manifest)
    write_text(REPORTS_DIR / "phase5_t20i_official_verification_template.csv", TEMPLATE.read_text())
    write_text(
        REPORTS_DIR / "phase5_t20i_date_verification.md", render(summary, late42, check, manifest)
    )
    print(late42["date_class"].value_counts().to_string())
    print({k: v for k, v in guards.items()})
    return 0


def render(summary: dict, late42: pd.DataFrame, check: pd.DataFrame, manifest: dict) -> str:
    sets = manifest["sets"]
    g = summary["guards"]
    lines = [
        "# Phase 5: T20I date verification and restricted TEST set",
        "",
        f"Status: **{STATUS}**. Internal investigation only. No ranking is published.",
        "",
        "## Statement",
        "",
        f"**{summary['statement']}**",
        "",
        "Original dates are preserved exactly (SHA-256 of the `matches` date column and of the database "
        "file are identical before and after the run; the 42 late dates also equal `matches.csv` read "
        "independently). Cricsheet is secondary, validation-only evidence and not an official record. "
        "It is read only by `app/phase5/date_verification.py` and is not an input to any score, "
        "baseline, threshold or ranking.",
        "",
        "## Evidence checks",
        "",
        "| Check | Source | Counts as agreeing source |",
        "|---|---|---|",
        "| (a) first/last `delivery_ist_time` date part (column carries a `UTC` suffix; compared "
        "within +-1 day, conflict at 2+ days) | updated_ball_by_ball | yes |",
        "| (b) series ordering by match_number, spacing, a team on two matches on one date | matches | no (internal) |",
        "| (c) competition season/year token vs date year (competitions.csv has no date windows) | competitions.csv | no (internal, weak) |",
        "| (d) `matches 2026.csv` (IPL 2026 only, first 39 matches) | matches 2026.csv | yes, IPL only |",
        "| (e) Cricsheet date for the same team pair within 3 days, identity confirmed by first-innings team and total | cricsheet_index | yes |",
        "| (f) internal conflicts (any failed internal check or source disagreement) | derived | creates DATE_CONFLICT |",
        "",
        "## Class distribution",
        "",
        md_table(
            ["Class", "42 late T20I matches", "All TEST-period matches checked"],
            [
                [
                    c,
                    summary["class_distribution_late42"][c],
                    summary["class_distribution_all_test_matches"][c],
                ]
                for c in dv.CLASSES
            ],
        ),
        f"Official-verified among the 42: **{summary['official_verified_late42']}**. "
        f"Publication gate `date_verification`: passed = {summary['gate']['passed']}.",
        "",
        "## The 42 T20I matches dated after " + summary["late_cutoff"],
        "",
        md_table(
            [
                "match_id",
                "series",
                "teams",
                "original date",
                "timestamp",
                "Cricsheet",
                "ordering",
                "class",
            ],
            [
                [
                    str(r.match_id),
                    r.comp_name,
                    f"{r.home_team} v {r.away_team}",
                    r.original_match_date,
                    f"{r.ts_status} ({r.ts_first_date})",
                    f"{r.cs_status} ({r.cs_date})",
                    "ok" if r.ordering_consistent and not r.double_booking else "FAIL",
                    r.date_class,
                ]
                for r in late42.itertuples()
            ],
        ),
        "Full evidence columns: `phase5_t20i_date_verification.csv` / `.json`. Every TEST-period match: "
        "`phase5_test_match_date_check.csv`.",
        "",
        "## Official verification template",
        "",
        "Fill `config/t20i_official_date_verification.csv` (header copy: "
        "`phase5_t20i_official_verification_template.csv`) with columns `match_id, verified_date, source, "
        "verified_by, verified_date_of_verification`. Only rows with all five fields are OFFICIAL; "
        "incomplete rows are listed and ignored. A bad ISO date or unknown match id stops the run. A "
        "verified date that differs from the original is reported as `OFFICIAL_DATE_DIFFERS`; the "
        "original is not changed and the match is not treated as verified. Then re-run "
        "`python scripts/phase5_date_verification.py`.",
        "",
        "## Restricted TEST sets (definition only, TEST not evaluated)",
        "",
        md_table(
            ["Set", "Rule", "Matches", "Deliveries", "Players"],
            [
                [
                    s,
                    v["rule"],
                    v["counts"]["matches"],
                    v["counts"]["deliveries"],
                    v["counts"]["players"],
                ]
                for s, v in sets.items()
            ],
        ),
        "Affected by the PRIMARY_RESTRICTED rule: "
        f"{manifest['excluded_from_primary']['excluded_matches']} matches, "
        f"{manifest['excluded_from_primary']['excluded_deliveries']} deliveries, "
        f"{manifest['excluded_from_primary']['players_in_excluded_matches']} players appear in them "
        f"({manifest['excluded_from_primary']['players_only_in_excluded_matches']} appear in no included "
        "TEST match). Under STRICT_OFFICIAL_ONLY every match is excluded until official rows are supplied: "
        f"{manifest['excluded_from_strict']['excluded_matches']} matches, "
        f"{manifest['excluded_from_strict']['excluded_deliveries']} deliveries.",
        "",
        "Per competition type (matches / deliveries / players):",
        "",
        md_table(
            ["Set", "Competition type", "Matches", "Deliveries", "Players"],
            [
                [s, ct, c["matches"], c["deliveries"], c["players"]]
                for s, v in sets.items()
                for ct, c in v["counts"]["by_competition_type"].items()
            ],
        ),
        "TEST-period matches in `matches` but absent from the Phase 4 state: "
        + "; ".join(
            f"{x['match_id']} ({x['competition_type']}, {x['original_match_date']}, "
            f"deliveries {x['deliveries']})"
            for x in manifest["test_matches_in_matches_table_not_in_phase4_state"]
        )
        + ". They have no deliveries (abandoned), so they never entered the Phase 4 evaluation and do "
        "not change any set.",
        "",
        f"Manifest: `phase5_test_set_manifest.json`, self SHA-256 `{manifest['self_sha256']}`.",
        "",
        "## TEST lock handling (option D1)",
        "",
        "TEST is **not** re-opened. The Phase 4 lock is single-use (an OPEN event is already logged) and "
        "re-opening it would need a log reset that erases the evidence of the original opening. The "
        "methodology and the data-weight gate are not locked, so a second evaluation is premature. "
        "Phase 5 reads only identity columns (`match_id`, innings, ball number, striker, bowler) of TEST "
        "matches through an allow-list that rejects `out_`, `den_`, `post_innings_` and residual "
        "columns. The restricted sets are frozen in the manifest for one future evaluation under a new "
        "`phase5_lock_log.json`, which stays empty.",
        "",
        md_table(
            ["Guard", "Result"],
            [
                ["Phase 4 lock log SHA-256 before", g["phase4_lock_log_sha256_before"]],
                ["Phase 4 lock log SHA-256 after", g["phase4_lock_log_sha256_after"]],
                ["Phase 4 lock log events", ", ".join(g["phase4_lock_events"])],
                ["Phase 5 lock log events (no OPEN)", g["phase5_lock_log_events"]],
                ["official database file unchanged", g["official_db_unchanged"]],
                ["matches date column unchanged", g["matches_date_column_unchanged"]],
                ["source CSVs unchanged", g["source_csvs_unchanged"]],
                ["42 originals equal matches.csv", g["late42_originals_equal_matches_csv"]],
            ],
        ),
        "Phase 4's TEST evaluation covered all 144 state matches, including the 42 late matches whose "
        "dates are unverified. It is preserved byte-identical and is sensitivity-only in Phase 5 reports.",
        "",
        "## Open decisions and unresolved issues",
        "",
        "1. **Primary-set strictness.** The brief's strict default would exclude all 144 matches until "
        "officially verified. The plan chose PRIMARY_RESTRICTED (early consistent matches plus official "
        "rows). STRICT_OFFICIAL_ONLY is also frozen; the user should confirm which is primary.",
        "2. **Not a pristine hold-out.** Aggregate TEST results were already shown in Phase 4, so a later "
        "evaluation is not a clean hold-out.",
        "3. **No official record is supplied.** All 42 dates remain unverified against an authoritative "
        "source. Cricsheet agreement is secondary evidence only.",
        "4. **Weak checks.** `competitions.csv` has no date windows (season token only); `matches 2026.csv` "
        "covers 39 IPL matches only; Cricsheet identity needs the first innings to be present.",
        "5. **Timestamp column name.** `delivery_ist_time` ends in `UTC`; the clock times behave like UTC, so "
        "a one-day offset is tolerated and larger offsets are conflicts.",
        "6. **Lock hash note.** The plan quoted `86f5ce9d...` as the lock log hash; that is the hash of "
        "`phase4_frozen_choices.json`. The lock log hash recorded in `phase5_prerun_hashes.json` is used.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
