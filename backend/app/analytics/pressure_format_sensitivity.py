"""Format-weight sensitivity on pressure-specific eligibility (Phase 3 prep, Stage 6).

EXPLORATORY_NOT_VALIDATED. Reuses the Phase 2.5 combination engine (`normalization_engine`) with
pressure tables injected. A format score that does not exist is never filled: a player without an
eligible score in both formats has a NULL combined score and an explicit status. 70:30 stays a
provisional default. No official Top 10 is produced: rankings are technical, player ids only.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics import confidence_engine as ce
from app.analytics import normalization_engine as ne
from app.analytics.format_config import config_hash
from app.analytics.reporting import PROXY_FIELDS

STATUS = {
    **PROXY_FIELDS,
    "status": "EXPLORATORY_NOT_VALIDATED",
    "official_ranking": False,
    "not_for_publication": True,
    "pressure_status": "EXPLORATORY_PROXY_NOT_VALIDATED_PRESSURE",
    "score_label": "PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE",
}
TRIM = 10


def pressure_tables(
    batter: pd.DataFrame, bowler: pd.DataFrame, min_balls: dict[str, dict[str, float]]
) -> tuple[dict[str, dict[str, pd.DataFrame]], dict[str, dict[str, float]]]:
    """Per role and format player tables (player_id, balls, score, eligible) from pressure samples.

    A format with no pressure rows yields an EMPTY table (never zero rows of fake players).
    """
    frames = {"batter": batter, "bowler": bowler}
    tables: dict[str, dict[str, pd.DataFrame]] = {}
    thresholds: dict[str, dict[str, float]] = {}
    for role in ne.ROLES:
        tables[role], thresholds[role] = {}, {}
        for fmt in ne.FORMATS:
            thr = min_balls[fmt][role]
            rows = frames[role][frames[role]["format"] == fmt]
            if rows.empty:
                tables[role][fmt] = pd.DataFrame(
                    {"player_id": [], "balls": [], "score": [], "eligible": []}
                )
            else:
                t = ce.player_table(ce.Prepared(rows, role))[["player_id", "balls", "score"]].copy()
                t["eligible"] = t["balls"] >= thr
                tables[role][fmt] = t
            thresholds[role][fmt] = thr
    return tables, thresholds


def missing_format_audit(frame: pd.DataFrame, cfg: dict) -> dict[str, Any]:
    """Proof that a missing or ineligible format score is never filled or treated as zero."""
    bad = 0
    for c in cfg["configurations"]:
        sc = ne.combined_scores(frame, c["ipl_weight"], c["t20i_weight"])
        bad += int((sc.notna() & (frame["combined_status"] != ne.BOTH)).sum())
    not_both = frame["combined_status"] != ne.BOTH
    return {
        "players_not_in_both_formats": int(not_both.sum()),
        "combined_scores_present_for_them": bad,
        "z_present_for_not_eligible_format": int(
            ((frame["ipl_status"] != ne.ELIGIBLE) & frame["ipl_z"].notna()).sum()
            + ((frame["t20i_status"] != ne.ELIGIBLE) & frame["t20i_z"].notna()).sum()
        ),
        "rule": "combined score = NULL unless ELIGIBLE in both formats; no zero fill, no imputation",
    }


def _trim_rows(rows: list[dict], k: int = TRIM) -> list[dict]:
    return rows[:k]


def trim_for_publication_safety(role_res: dict) -> dict:
    """Drop full rankings: only technical top-k player ids remain (no names, no scores list)."""
    for c in role_res["configs"].values():
        c.pop("ranking", None)
    fr = role_res.get("format_rankings", {})
    for key, rows in list(fr.items()):
        fr[key] = {
            "label": "TECHNICAL_TOP_IDS_NOT_A_PUBLISHED_RANKING",
            "n_ranked": len(rows),
            "top_rows": _trim_rows(rows),
        }
    adj = role_res.get("adjusted_estimate")
    if adj:
        adj["n_ranked"] = len(adj["ranking"])
        adj["ranking"] = _trim_rows(adj["ranking"])
        adj["label_scope"] = "SEPARATE_SECTION_SINGLE_FORMAT_ADJUSTED_ESTIMATES_TRIMMED_TO_TOP_IDS"
    return role_res


def run(
    batter: pd.DataFrame,
    bowler: pd.DataFrame,
    cfg: dict,
    thresholds: dict[str, dict[str, float]],
    robustness: dict[str, dict[str, dict[str, float]]],
    list_size: int,
    label: str,
) -> dict[str, Any]:
    """Run the eight configurations with pressure-specific tables.

    thresholds: {format: {role: min_balls}} primary; robustness: {label: same shape}.
    """
    tables, thr = pressure_tables(batter, bowler, thresholds)
    rob = {lab: pressure_tables(batter, bowler, m) for lab, m in robustness.items()}
    res = ne.run_sensitivity(
        None,
        cfg,
        list_size,
        names=None,
        tables=tables,
        thresholds=thr,
        robustness=rob,
        eligibility_label=label,
    )
    res.update(STATUS)
    res["config_hash_all_results"] = config_hash(cfg)
    res["audit"] = {}
    for role in ne.ROLES:
        frame = ne.build_player_frame(tables[role])
        res["audit"][role] = missing_format_audit(frame, cfg)
        res["roles"][role]["format_populations"] = {
            "IPL_eligible": int((frame["ipl_status"] == ne.ELIGIBLE).sum()),
            "T20I_eligible": int((frame["t20i_status"] == ne.ELIGIBLE).sum()),
            "both_eligible": int((frame["combined_status"] == ne.BOTH).sum()),
        }
        trim_for_publication_safety(res["roles"][role])
    return res


def population_changes(res: dict, all_situation: dict | None) -> dict[str, Any]:
    """Eligible-population change between thresholds and versus the Phase 2.5 all-situation run."""
    out: dict[str, Any] = {}
    for role in ne.ROLES:
        r = res["roles"][role]
        sc = r["status_counts"]
        row: dict[str, Any] = {
            "pressure_primary": {
                "IPL_eligible": sc["ipl_status"][ne.ELIGIBLE],
                "T20I_eligible": sc["t20i_status"][ne.ELIGIBLE],
                "combined": r["combined_population"],
            },
            "pressure_robustness": {
                lab: {
                    "IPL_eligible": x["roles"][role]["status_counts"]["ipl_status"][ne.ELIGIBLE],
                    "T20I_eligible": x["roles"][role]["status_counts"]["t20i_status"][ne.ELIGIBLE],
                    "combined": x["roles"][role]["combined_population"],
                    "change_vs_primary": x["roles"][role]["eligibility_change_vs_primary"],
                }
                for lab, x in res["robustness"].items()
            },
        }
        if all_situation is not None:
            a = all_situation["roles"][role]
            asc = a["status_counts"]
            row["phase25_all_situation"] = {
                "IPL_eligible": asc["ipl_status"][ne.ELIGIBLE],
                "T20I_eligible": asc["t20i_status"][ne.ELIGIBLE],
                "combined": a["combined_population"],
                "level": all_situation.get("eligibility_level"),
            }
        out[role] = row
    return out


def degenerate_note(res: dict) -> dict[str, bool]:
    """100:0 and 0:100 use the same combined population as every other configuration."""
    out = {}
    for role in ne.ROLES:
        pops = {e["n_ranked"] for e in res["roles"][role]["configs"].values()}
        out[role] = len(pops) == 1
    return out
