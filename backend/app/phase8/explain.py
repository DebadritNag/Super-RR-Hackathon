"""Plain-language evidence text and data-based exclusion reasons.

Every sentence is built from stored numbers. A player without enough evidence is never described
as a poor performer; the reason says what is missing (counts against the declared floors) or what
the interval and the inclusion probability show.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

REASON_CODES = (
    "BELOW_ELIGIBILITY_FLOOR",
    "INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR",
    "LOW_TOP10_INCLUSION_PROBABILITY",
    "ONE_FORMAT_ONLY_LOW_EVIDENCE",
    "INCONSISTENT_ACROSS_MATCHES",
    "HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT",
    "NO_PRESSURE_ESTIMATE",
)
LOW_INCLUSION = 0.25
RULE_LABELS = {
    "matches": "matches",
    "effective_n": "effective pressure-weighted deliveries",
    "balls": "balls",
    "high_intensity_units": "high-intensity innings or spells",
}


def _f(v: Any, nd: int = 3, sign: bool = False) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v):
        return "n/a"
    return f"{float(v):+.{nd}f}" if sign else f"{float(v):.{nd}f}"


def _pct(v: Any) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{100.0 * float(v):.0f}%"


def short_explanation(row: dict[str, Any], role: str, approach: str) -> str:
    """One paragraph for a selected player (also the ``short_explanation`` column)."""
    verb = (
        ("scored", "runs per ball", "dismissal")
        if role == "batter"
        else ("conceded", "runs per ball", "wicket")
    )
    exposure = (
        f"{_f(row['pressure_innings_or_spells'], 0)} pressure "
        f"{'innings' if role == 'batter' else 'spells'} and {_f(row['pressure_deliveries'], 0)} "
        f"pressure deliveries in {_f(row['total_matches'], 0)} matches"
    )
    if approach == "C":
        head = (
            f"Rank {row['rank']} by the Pressure Response Index ({_f(row['pressure_score'], 2, True)}, "
            f"0 is the typical eligible {role}): in {_pct(row['positive_unit_share'])} of "
            f"{exposure.split(' and ')[0]} the {role} did better than the model expected."
        )
    else:
        head = f"Rank {row['rank']} by context-adjusted pressure performance ({_f(row['pressure_score'], 4, True)})."
    obs = ""
    if pd.notna(row.get("observed_runs_per_ball")) and pd.notna(row.get("expected_runs_per_ball")):
        obs = (
            f" On pressure deliveries the {role} {verb[0]} {_f(row['observed_runs_per_ball'], 2)} "
            f"{verb[1]} against {_f(row['expected_runs_per_ball'], 2)} expected for the same match "
            f"situations; {verb[2]} rate {_f(row['observed_wicket_rate'], 3)} against "
            f"{_f(row['expected_wicket_rate'], 3)} expected."
        )
    base = ""
    if pd.notna(row.get("normal_baseline")):
        base = (
            f" Normal-play baseline {_f(row['normal_baseline'], 3, True)}, pressure level "
            f"{_f(row['pressure_performance_unshrunk'], 3, True)}, difference "
            f"{_f(row['pressure_delta'], 3, True)}."
        )
    delta = row.get("pressure_delta")
    if pd.notna(delta):
        base += (
            " The pressure level is above the normal-play baseline, so the result is not only overall quality."
            if delta > 0
            else " The pressure level is below the normal-play baseline: the rank reflects performance above "
            "expectation in pressure situations, not an improvement over the player's normal play."
        )
    tail = (
        f" Evidence: {exposure}. Top-10 inclusion {_pct(row['top10_inclusion_probability'])}, "
        f"95% rank interval {_f(row['rank_interval_low'], 0)} to {_f(row['rank_interval_high'], 0)}, "
        f"evidence class {row['evidence_class']}. Status {row['ranking_status']}: the order is not "
        "shown to separate players beyond noise."
    )
    return (head + obs + base + tail).strip()


def reasons_for_eligible(
    r: pd.Series, tenth_score: float, min_matches: float, raw_standout: bool
) -> list[tuple[str, str]]:
    """Exclusion reasons (code, detail) for an eligible player outside the Top 10."""
    out: list[tuple[str, str]] = []
    p = r.get("top_k_prob")
    if pd.notna(p) and p < LOW_INCLUSION:
        out.append(
            (
                "LOW_TOP10_INCLUSION_PROBABILITY",
                f"inclusion probability {_pct(p)} across the match-cluster bootstrap draws "
                f"(selected players need {_pct(LOW_INCLUSION)} for a PROVISIONAL row; rank "
                f"interval {_f(r.get('rank_low'), 0)} to {_f(r.get('rank_high'), 0)})",
            )
        )
    if (
        r["score"] < tenth_score
        and pd.notna(r["interval_high"])
        and r["interval_high"] >= tenth_score
    ):
        out.append(
            (
                "INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR",
                f"score {_f(r['score'], 4, True)} is below the tenth-ranked score "
                f"{_f(tenth_score, 4, True)}, although the 95% interval reaches "
                f"{_f(r['interval_high'], 4, True)}; the order between them is within noise",
            )
        )
    if r.get("evidence_class") == "INCONSISTENT":
        out.append(
            (
                "INCONSISTENT_ACROSS_MATCHES",
                f"{_pct(r.get('pos_share'))} of {_f(r.get('n_units'), 0)} pressure units beat the "
                "expectation; the declared INCONSISTENT rule applies",
            )
        )
    ipl, t20 = r.get("matches_ipl"), r.get("matches_t20i")
    n_ipl = 0.0 if pd.isna(ipl) else float(ipl)
    n_t20 = 0.0 if pd.isna(t20) else float(t20)
    if min(n_ipl, n_t20) < min_matches / 2:
        only = "IPL" if n_t20 < n_ipl else "T20I"
        out.append(
            (
                "ONE_FORMAT_ONLY_LOW_EVIDENCE",
                f"{_f(max(n_ipl, n_t20), 0)} matches in {only} and {_f(min(n_ipl, n_t20), 0)} in "
                "the other format; the cross-format check cannot be applied to this player",
            )
        )
    if raw_standout and (
        (pd.notna(r.get("pressure_perf_unshrunk")) and r["pressure_perf_unshrunk"] <= 0)
        or r["score"] <= 0
    ):
        out.append(
            (
                "HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT",
                "high on the raw death-overs statistic, but at or below the model expectation "
                "once the match situation is accounted for",
            )
        )
    if not out:
        out.append(
            (
                "INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR",
                f"score {_f(r['score'], 4, True)} is lower than the tenth-ranked "
                f"{_f(tenth_score, 4, True)}; the difference is inside the 95% interval",
            )
        )
    return out


def reason_below_floor(r: pd.Series, role: str) -> tuple[str, str]:
    """Counts against the declared floors for a player below at least one of them."""
    failed = [x for x in str(r.get("failed_rules", "")).split(";") if x]
    parts = []
    for k in failed:
        parts.append(RULE_LABELS.get(k, k))
    ball_word = "balls faced" if role == "batter" else "balls bowled"
    return (
        "BELOW_ELIGIBILITY_FLOOR",
        f"{_f(r.get('n_matches'), 0)} matches, {_f(r.get('balls'), 0)} {ball_word}, "
        f"{_f(r.get('hi_units'), 0)} high-intensity {'innings' if role == 'batter' else 'spells'}; "
        f"below the declared floor on: {', '.join(parts) or 'not recorded'}. This is a lack of "
        "evidence, not a finding about the player's quality",
    )


def no_estimate_reason() -> tuple[str, str]:
    return (
        "NO_PRESSURE_ESTIMATE",
        "no delivery with a defined pressure intensity and a residual was found in the "
        "pre-test window; the value is missing, not zero",
    )
