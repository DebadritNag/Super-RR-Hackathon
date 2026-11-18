"""Top 10 construction for the submitted pressure rankings.

Input is one role's stored estimate table of the chosen approach (all scopes). Ordering is by the
approach's own score, descending; only exact numeric ties (absolute difference below 1e-12) are
broken by ``player_id`` ascending, so the id never decides an order that the data decide.
Nothing is padded: when fewer than ten eligible players exist the list is shorter, the status is
INSUFFICIENT_EVIDENCE and the remaining players form a labelled candidate pool.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.phase8.stability import point_ranking
from app.phase8.status import check_label, row_status

TOP_N = 10
POOL_N = 10
METHODOLOGY_VERSION = "phase8_methodology_v1"
ROLES = ("batter", "bowler")
APPROACH_NAMES = {
    "A": "Approach A: context-adjusted performance under continuous pressure intensity",
    "B": "Approach B: leverage-weighted win probability added",
    "C": "Approach C: Pressure Response Index (consistency of pressure units)",
}

# column of the stored table holding the ranking score, its interval and the score unit
SPEC = {
    "A": {"score": "estimate", "low": "est_low", "high": "est_high", "unit": "standardised residual per delivery (REML posterior)"},
    "B": {"score": "estimate", "low": "est_low", "high": "est_high", "unit": "win-probability-added residual per delivery"},
    "C": {"score": "pri", "low": "pri_low", "high": "pri_high", "unit": "PRI (cohort standard deviations; 0 is the typical eligible player)"},
}  # fmt: skip
COMPONENT_COLS = {
    "A": ("comp_runs", "comp_wicket", "comp_dot", "comp_boundary"),
    "B": ("obs_wpa", "exp_wpa_given_leverage", "mean_leverage_pressure", "lw_wpa_per_opp"),
    "C": ("z_A", "z_B", "z_CONS"),
}

OUT_COLUMNS = [
    "rank", "player_id", "player_name", "role", "primary_methodology", "rank_basis",
    "pressure_score", "score_unit", "interval_low", "interval_high", "interval_method",
    "interval_flag", "pressure_performance_unshrunk", "normal_baseline", "pressure_delta",
    "observed_runs_per_ball", "expected_runs_per_ball", "observed_wicket_rate",
    "expected_wicket_rate", "component_scores", "pressure_matches", "pressure_innings_or_spells",
    "pressure_deliveries", "total_matches", "ipl_matches", "t20i_matches", "ipl_contribution",
    "t20i_contribution", "ipl_score", "t20i_score", "combination_basis", "mean_intensity",
    "positive_unit_share", "sample_reliability", "top10_inclusion_probability",
    "rank_interval_low", "rank_interval_high", "evidence_class", "rank_in_A", "rank_in_B",
    "rank_in_C", "rank_in_IPL", "rank_in_T20I", "short_explanation", "ranking_status",
    "model_validation_status", "list_status", "eligibility_flags", "data_quality_flags",
    "methodology_version", "data_version_hash", "criteria_sha256", "generated_at",
]  # fmt: skip


class RankingError(ValueError):
    """The estimate table cannot be turned into a ranking."""


def order_players(frame: pd.DataFrame, score_col: str) -> pd.Series:
    """Deterministic rank 1..n (descending score; exact ties by ``player_id`` ascending)."""
    if frame["player_id"].duplicated().any():
        raise RankingError("player_id must be unique within one ranking")
    s = frame.set_index("player_id")[score_col].astype("float64")
    return point_ranking(s)


def _share(num: pd.Series, den: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        return (num / den).where(den > 0)


def combined_frame(est: pd.DataFrame, approach: str, role: str) -> pd.DataFrame:
    """COMBINED rows of ``role`` with the IPL and T20I scope values attached as columns."""
    sp = SPEC[approach]
    d = est[est["role"] == role]
    comb = d[d["scope"] == "COMBINED"].copy()
    if comb.empty:
        raise RankingError(f"no COMBINED estimates for {role} under approach {approach}")
    for scope, tag in (("IPL", "ipl"), ("T20I", "t20i")):
        s = d[d["scope"] == scope].set_index("player_id")
        comb[f"{tag}_score"] = comb["player_id"].map(s[sp["score"]])
        comb[f"{tag}_rank_scope"] = comb["player_id"].map(s["rank"])
        comb[f"{tag}_sum_w"] = comb["player_id"].map(s["sum_w"])
    # Contribution = share of the player's matches (with a defined pressure intensity) that were
    # played in each format. The scope tables only hold players that meet the floors inside that
    # format, so the match counts of the COMBINED table are the complete basis.
    ipl_m = comb["matches_ipl"].fillna(0.0) if "matches_ipl" in comb.columns else 0.0
    t20_m = comb["matches_t20i"].fillna(0.0) if "matches_t20i" in comb.columns else 0.0
    tot = ipl_m + t20_m
    # A missing count in the match-count table means no delivery with a defined intensity in that
    # format (a true count of zero), unlike a missing score, which stays empty.
    comb["matches_ipl"], comb["matches_t20i"] = ipl_m, t20_m
    comb["ipl_contribution"] = _share(ipl_m, tot)
    comb["t20i_contribution"] = _share(t20_m, tot)
    if "sample_reliability" not in comb.columns:
        comb["sample_reliability"] = comb["B"] if "B" in comb.columns else np.nan
    comb["score"] = comb[sp["score"]].astype("float64")
    comb["interval_low"] = comb[sp["low"]]
    comb["interval_high"] = comb[sp["high"]]
    return comb


def interval_flag(score: float, low: float, high: float) -> str:
    """Flag intervals that do not behave like a symmetric interval around the point estimate."""
    if not (np.isfinite(score) and np.isfinite(low) and np.isfinite(high)):
        return "INTERVAL_UNAVAILABLE"
    if score < low or score > high:
        return "POINT_OUTSIDE_INTERVAL"
    lo_gap, hi_gap = score - low, high - score
    if lo_gap > 0 and hi_gap > 2.0 * lo_gap:
        return "ASYMMETRIC_UPPER_TAIL"
    if hi_gap > 0 and lo_gap > 2.0 * hi_gap:
        return "ASYMMETRIC_LOWER_TAIL"
    return "OK"


def eligibility_flags(row: pd.Series, min_matches: float) -> str:
    flags = ["MEETS_ALL_DECLARED_FLOORS"]
    if row["n_matches"] < 2 * min_matches:
        flags.append("MATCHES_BELOW_2X_FLOOR")
    ipl, t20 = row.get("matches_ipl"), row.get("matches_t20i")
    n_ipl = 0.0 if pd.isna(ipl) else float(ipl)
    n_t20 = 0.0 if pd.isna(t20) else float(t20)
    if n_ipl < min_matches / 2 or n_t20 < min_matches / 2:
        flags.append("ONE_FORMAT_BELOW_HALF_FLOOR")
    return ";".join(flags)


def quality_flags(
    row: pd.Series, floor_cell: bool, combo_basis: str, definition_status: str
) -> str:
    flags = [definition_status]
    if combo_basis.startswith("FORMAT_COMBINATION_UNSUPPORTED"):
        flags.append("FORMAT_COMBINATION_UNSUPPORTED")
    if floor_cell:
        flags.append("BETWEEN_PLAYER_VARIANCE_AT_FLOOR")
    rel = row.get("sample_reliability")
    if pd.notna(rel) and rel < 0.5:
        flags.append("DATA_WEIGHT_BELOW_0_5")
    return ";".join(flags)


def build_list(
    frame: pd.DataFrame,
    *,
    approach: str,
    role: str,
    list_label: str,
    validation_label: str,
    rank_basis: str,
    ranks_by_approach: dict[str, pd.Series],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Return ``{"top": DataFrame, "pool": DataFrame, "shortfall": str | None, "label": str}``."""
    check_label(list_label)
    check_label(validation_label)
    if role not in ROLES:
        raise RankingError("role must be batter or bowler")
    f = frame.copy()
    f["rank_calc"] = f["player_id"].map(order_players(f, "score")).astype(int)
    f = f.sort_values(["rank_calc", "player_id"]).reset_index(drop=True)
    n_eligible = int(len(f))
    shortfall = None
    label = list_label
    if n_eligible < TOP_N:
        label = "INSUFFICIENT_EVIDENCE"
        shortfall = (
            f"Only {n_eligible} {role}s meet the declared eligibility floors, fewer than {TOP_N}. "
            "The list is shorter and is not padded; the remaining players form the candidate pool."
        )
    top = f.head(TOP_N).copy()
    pool = f.iloc[TOP_N : TOP_N + POOL_N].copy() if n_eligible > TOP_N else f.iloc[0:0].copy()
    if shortfall:
        pool = f.copy()
    for part in (top, pool):
        part["rank"] = part["rank_calc"].astype(int)
    for part in (top, pool):
        part["ranking_status"] = [
            row_status(label, r["evidence_class"], r["top_k_prob"], True)
            for _, r in part.iterrows()
        ]
        part["model_validation_status"] = validation_label
        part["list_status"] = label
    ctx = dict(context)
    ctx["approach"] = approach
    for part in (top, pool):
        part["rank_in_A"] = part["player_id"].map(
            ranks_by_approach.get("A", pd.Series(dtype=float))
        )
        part["rank_in_B"] = part["player_id"].map(
            ranks_by_approach.get("B", pd.Series(dtype=float))
        )
        part["rank_in_C"] = part["player_id"].map(
            ranks_by_approach.get("C", pd.Series(dtype=float))
        )
    return {"top": top, "pool": pool, "shortfall": shortfall, "label": label, "ctx": ctx,
            "n_eligible": n_eligible, "rank_basis": rank_basis}  # fmt: skip


def _num(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v):
        return None
    return float(v)


def to_output(part: pd.DataFrame, built: dict[str, Any], explain_fn: Any) -> pd.DataFrame:
    """Final output columns (unavailable values stay empty, never zero)."""
    ctx = built["ctx"]
    approach, role = ctx["approach"], ctx["role"]
    comps = COMPONENT_COLS[approach]
    rows: list[dict[str, Any]] = []
    for _, r in part.iterrows():
        comp = {c: _num(r.get(c)) for c in comps if c in part.columns}
        flag = interval_flag(float(r["score"]), float(r["interval_low"]), float(r["interval_high"]))
        pressure_balls = _num(r.get("n_innings1", np.nan))
        if pressure_balls is not None and _num(r.get("n_innings2", np.nan)) is not None:
            pressure_balls += float(r["n_innings2"])
        row = {
            "rank": int(r["rank"]), "player_id": int(r["player_id"]),
            "player_name": r["player_name"], "role": role,
            "primary_methodology": APPROACH_NAMES[approach], "rank_basis": built["rank_basis"],
            "pressure_score": _num(r["score"]), "score_unit": SPEC[approach]["unit"],
            "interval_low": _num(r["interval_low"]), "interval_high": _num(r["interval_high"]),
            "interval_method": ctx["interval_method"], "interval_flag": flag,
            "pressure_performance_unshrunk": _num(r.get("pressure_perf_unshrunk")),
            "normal_baseline": _num(r.get("normal_baseline")),
            "pressure_delta": _num(r.get("pressure_delta")),
            "observed_runs_per_ball": _num(r.get("obs_runs")),
            "expected_runs_per_ball": _num(r.get("exp_runs")),
            "observed_wicket_rate": _num(r.get("obs_wicket")),
            "expected_wicket_rate": _num(r.get("exp_wicket")),
            "component_scores": json.dumps(comp, sort_keys=True),
            "pressure_matches": _num(r.get("pressure_matches")),
            "pressure_innings_or_spells": _num(r.get("n_units")),
            "pressure_deliveries": pressure_balls, "total_matches": _num(r.get("n_matches")),
            "ipl_matches": _num(r.get("matches_ipl")), "t20i_matches": _num(r.get("matches_t20i")),
            "ipl_contribution": _num(r.get("ipl_contribution")),
            "t20i_contribution": _num(r.get("t20i_contribution")),
            "ipl_score": _num(r.get("ipl_score")), "t20i_score": _num(r.get("t20i_score")),
            "combination_basis": ctx["combination_basis"],
            "mean_intensity": _num(r.get("mean_intensity")),
            "positive_unit_share": _num(r.get("pos_share")),
            "sample_reliability": _num(r.get("sample_reliability")),
            "top10_inclusion_probability": _num(r.get("top_k_prob")),
            "rank_interval_low": _num(r.get("rank_low")),
            "rank_interval_high": _num(r.get("rank_high")),
            "evidence_class": r["evidence_class"],
            "rank_in_A": _num(r.get("rank_in_A")), "rank_in_B": _num(r.get("rank_in_B")),
            "rank_in_C": _num(r.get("rank_in_C")),
            "rank_in_IPL": _num(r.get("ipl_rank_scope")), "rank_in_T20I": _num(r.get("t20i_rank_scope")),
            "ranking_status": r["ranking_status"],
            "model_validation_status": r["model_validation_status"],
            "list_status": r["list_status"],
            "eligibility_flags": eligibility_flags(r, ctx["min_matches"]),
            "data_quality_flags": quality_flags(
                r, ctx["floor_cell"], ctx["combination_basis"], ctx["definition_status"]
            ),
            "methodology_version": METHODOLOGY_VERSION,
            "data_version_hash": ctx["data_version_hash"],
            "criteria_sha256": ctx["criteria_sha256"],
            "generated_at": ctx["generated_at"],
        }  # fmt: skip
        row["short_explanation"] = explain_fn(row, role, approach)
        rows.append(row)
    out = pd.DataFrame(rows, columns=OUT_COLUMNS)
    return out


def check_output(out: pd.DataFrame, list_label: str) -> None:
    """Invariants of a submitted list (also used by the tests)."""
    if len(out) > TOP_N:
        raise RankingError("more than ten rows")
    if list(out["rank"]) != list(range(1, len(out) + 1)):
        raise RankingError("ranks must be 1..n without gaps")
    if out["player_id"].duplicated().any():
        raise RankingError("duplicate player")
    for s in out["ranking_status"]:
        check_label(s)
    if list_label != "VALIDATED" and (out["ranking_status"] == "VALIDATED").any():
        raise RankingError("a row is VALIDATED in a list that is not")


def csv_text(out: pd.DataFrame) -> str:
    """Deterministic CSV text (fixed column order, 10 significant decimals, LF line ends)."""
    return out.to_csv(index=False, float_format="%.10g", lineterminator="\n")


def json_payload(out: pd.DataFrame, header: dict[str, Any]) -> str:
    """Deterministic JSON text with the list header and the rows (NaN becomes null)."""
    rows = json.loads(out.to_json(orient="records", double_precision=10))
    return json.dumps({**header, "rows": rows}, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path | str, text: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return sha256_text(text)
