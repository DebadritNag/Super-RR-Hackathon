"""Phase 4 Stage F report renderers. EXPERIMENTAL_NOT_VALIDATED, no official ranking.

Every number in a rendered report is read from a stored result (JSON/CSV in ``data/reports``, the
exploratory store, or the register config) or computed from those by the functions below. No
number is typed into a template. Narrative text states method and limits only.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.analytics.reporting import md_table
from app.phase4.constants import STATUS

BACKEND = Path(__file__).resolve().parents[2]
DISCLAIMER = (
    f"Status: {STATUS}. Not an official ranking and not a validated methodology. No final ML "
    "model was trained. Automated tests passing does not validate the methodology."
)


# ---------------------------------------------------------------- loading
@dataclass
class Bundle:
    reports: Path
    manifest: dict = field(default_factory=dict)
    calibration: dict = field(default_factory=dict)
    selection: dict = field(default_factory=dict)
    frozen: dict = field(default_factory=dict)
    shrink_choice: dict = field(default_factory=dict)
    classification_cov: dict = field(default_factory=dict)
    test_eval: dict | None = None
    spot: dict | None = None
    dq: dict = field(default_factory=dict)
    lock_log: list = field(default_factory=list)
    scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    elig_frozen: pd.DataFrame = field(default_factory=pd.DataFrame)
    elig_cand: pd.DataFrame = field(default_factory=pd.DataFrame)
    fw_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    rank_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    rank_dist: pd.DataFrame = field(default_factory=pd.DataFrame)
    shrink_sens: pd.DataFrame = field(default_factory=pd.DataFrame)
    def_comp: pd.DataFrame = field(default_factory=pd.DataFrame)
    unresolved: pd.DataFrame = field(default_factory=pd.DataFrame)


def _json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_bundle(reports: Path | str) -> Bundle:
    r = Path(reports)
    csv = lambda n: pd.read_csv(r / n) if (r / n).exists() else pd.DataFrame()  # noqa: E731
    return Bundle(
        reports=r,
        manifest=_json(r / "phase4_split_manifest.json") or {},
        calibration=_json(r / "phase4_calibration.json") or {},
        selection=(_json(r / "phase4_definition_selection.json") or {}),
        frozen=_json(r / "phase4_frozen_choices.json") or {},
        shrink_choice=_json(r / "phase4_shrinkage_choice_final.json") or {},
        classification_cov=_json(r / "phase4_classification_coverage.json") or {},
        test_eval=_json(r / "phase4_test_evaluation.json"),
        spot=_json(r / "phase4_spot_checks.json"),
        dq=_json(r / "phase3_data_quality_application.json") or {},
        lock_log=_json(r / "phase4_lock_log.json") or [],
        scores=csv("phase4_pressure_scores_frozen_rules.csv"),
        elig_frozen=csv("phase4_eligibility_frozen.csv"),
        elig_cand=csv("phase4_eligibility_candidates.csv"),
        fw_results=csv("phase4_format_weight_results.csv"),
        rank_summary=csv("phase4_ranking_summary.csv"),
        rank_dist=csv("phase4_ranking_distributions.csv"),
        shrink_sens=csv("phase4_shrinkage_sensitivity.csv"),
        def_comp=csv("phase4_definition_comparison.csv"),
        unresolved=csv("phase4_unresolved_players.csv"),
    )


def _clean(v: Any) -> Any:
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, np.generic):
        return _clean(v.item())
    return v


def rows_of(df: pd.DataFrame, cols: list[str]) -> list[list[Any]]:
    return [[_clean(v) for v in r] for r in df[cols].itertuples(index=False, name=None)]


def kv(d: dict) -> str:
    return md_table(["item", "value"], [[k, _clean(v)] for k, v in d.items()])


# ---------------------------------------------------------------- derived facts
def lock_facts(log: list[dict]) -> dict[str, Any]:
    ev = [e["event"] for e in log]
    freeze_idx = [i for i, e in enumerate(ev) if e == "FREEZE"]
    open_idx = [i for i, e in enumerate(ev) if e == "OPEN"]
    return {
        "log_entries": len(log),
        "FREEZE_entries": len(freeze_idx),
        "OPEN_entries": len(open_idx),
        "CLOSE_entries": ev.count("CLOSE"),
        "READ_DENIED_entries": ev.count("READ_DENIED"),
        "freeze_recorded_before_open": bool(
            open_idx and freeze_idx and freeze_idx[-1] < open_idx[0]
        )
        if open_idx
        else None,
        "opened_exactly_once": len(open_idx) == 1,
        "hash_at_open_equals_hash_at_freeze": bool(
            open_idx
            and freeze_idx
            and log[open_idx[0]].get("sha256") == log[freeze_idx[-1]]["sha256"]
        )
        if open_idx
        else None,
    }


def _med(x: pd.Series) -> float | None:
    x = x.dropna()
    return None if x.empty else _clean(float(x.median()))


def cell_summary(scores: pd.DataFrame, frozen: dict) -> pd.DataFrame:
    """Per (role, stream, format) summary of the carried definition under the frozen shrinkage."""
    s = scores[
        (scores["definition_id"] == frozen["definition"]["id"])
        & (scores["shrinkage_config"] == frozen["shrinkage"]["config"])
    ]
    rows = []
    for (role, stream, fmt_), g in s.groupby(["role", "stream", "format"]):
        el = g[g["eligibility_status"].str.startswith("ELIGIBLE")]
        w = (el["interval_high"] - el["interval_low"]) if len(el) else pd.Series(dtype=float)
        excl0 = ((el["interval_low"] > 0) | (el["interval_high"] < 0)) if len(el) else w
        rows.append(
            {
                "role": role,
                "stream": stream,
                "format": fmt_,
                "records": int(len(g)),
                "eligible": int(len(el)),
                "median_pressure_balls_eligible": _med(el["pressure_opportunities"]),
                "median_data_weight": _med(el["data_weight"]),
                "median_interval_width": _med(w),
                "share_interval_excludes_0": _clean(float(excl0.mean())) if len(el) else None,
                "floor_hit_share": _clean(
                    float(
                        g["shrinkage_floor_hit"]
                        .map(lambda x: bool(x) if pd.notna(x) else False)
                        .mean()
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def elig_text(b: Bundle) -> str:
    ef = b.elig_frozen
    n = len(ef)
    bad = int((ef["status"] == "THRESHOLD_NOT_VALIDATED").sum())
    if n and bad == n:
        return (
            f"All {n} format-role cells are THRESHOLD_NOT_VALIDATED: no data-derived threshold "
            "passed the pre-declared data-weight gate, so none is validated and none was lowered "
            "to reach ten players. A labelled working pool is used downstream."
        )
    return (
        f"{bad} of {n} format-role cells are THRESHOLD_NOT_VALIDATED; the others have a threshold "
        "that passed the pre-declared gates. No threshold was lowered to reach ten players."
    )


def snr_text(b: Bundle) -> str:
    d = b.def_comp
    if d.empty or "snr" not in d:
        return "Signal-to-noise results are not available."
    c = d[d["definition_id"] == b.frozen["definition"]["id"]]
    n, bad = int(c["snr"].notna().sum()), int((c["snr"] <= 0).sum())
    return (
        f"For the carried definition, the estimated between-player variance is not above noise "
        f"(signal-to-noise at or below 0) in {bad} of {n} format-role-stream cells. Where it is "
        "not above noise, estimates shrink strongly toward the pool and rankings are fragile."
    )


def selection_text(b: Bundle) -> str:
    sel = b.selection["selection"]
    c = pd.DataFrame(sel["candidates"]).set_index("definition_id")
    share = float(c.loc[sel["winner"], "selection_share"])
    return (
        f"The winner takes {share:.2f} of the bootstrap resamples; {len(sel['top_group'])} "
        f"candidates lie within the tie margin ({sel['tie_margin_used']:.3f}) of the best score. "
        "The choice is therefore weak, and no multiplicity correction is applied."
    )


def nonoutcome_literals(files: list[Path], needle: str) -> dict[str, Any]:
    """String literals (not docstrings) containing ``needle`` in the given Python files."""
    hits: list[str] = []
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                body = getattr(node, "body", [])
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                ):
                    docs.add(id(body[0].value))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docs
                and needle in node.value.lower()
            ):
                hits.append(f"{f.name}:{node.lineno}")
    return {"files_scanned": len(files), "string_literal_hits": len(hits), "hits": hits}


REPORT_ONLY_FILES = {"reports.py", "phase4_reports.py"}


def phase4_sources() -> list[Path]:
    """Phase 4 code that loads or transforms data. The report writers are excluded because they
    print the word as text (and the scanner passes the needle as a string)."""
    files = sorted((BACKEND / "app" / "phase4").glob("*.py")) + sorted(
        (BACKEND / "scripts").glob("phase4_*.py")
    )
    return [f for f in files if f.name not in REPORT_ONLY_FILES]


def row_exclusions(store: Path | str, split_cfg: dict) -> pd.DataFrame:
    """Mutually exclusive row categories by period (flags and dates only, no outcome columns)."""
    p = split_cfg["periods"]
    sql = f"""
    SELECT CASE WHEN match_date <= DATE '{p["TRAIN"]["end"]}' THEN 'TRAIN'
                WHEN match_date <= DATE '{p["VALIDATION"]["end"]}' THEN 'VALIDATION'
                ELSE 'TEST' END AS period,
           CASE WHEN innings_number NOT IN (1, 2) THEN '1_innings_3_4_restricted'
                WHEN COALESCE(format_out_of_scope, false)
                     OR competition_type NOT IN ('IPL', 'T20I') THEN '2_out_of_scope_format'
                WHEN COALESCE(dls_exclude_primary, false) THEN '3_dls_not_reconstructable'
                WHEN NOT COALESCE(regulation_pressure_eligible, false) THEN '4_not_regulation_eligible'
                ELSE '5_in_primary_scoring_base' END AS category,
           count(*) AS rows
    FROM exp_pre_delivery_state GROUP BY 1, 2 ORDER BY 1, 2
    """
    con = duckdb.connect(str(store), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def late_t20i_dates(store: Path | str, core_end: str) -> dict[str, Any]:
    con = duckdb.connect(str(store), read_only=True)
    try:
        r = con.execute(
            "SELECT count(*), min(match_date), max(match_date) FROM p4_match_period "
            f"WHERE competition_type = 'T20I' AND match_date > DATE '{core_end}'"
        ).fetchone()
        t = con.execute(
            "SELECT count(*) FROM p4_match_period WHERE competition_type = 'T20I' "
            "AND period = 'TEST'"
        ).fetchone()
    finally:
        con.close()
    return {
        "core_end": core_end,
        "t20i_matches_after_core_end": int(r[0]),
        "first_date_after_core_end": str(r[1])[:10] if r[0] else None,
        "last_date": str(r[2])[:10] if r[0] else None,
        "t20i_test_period_matches": int(t[0]),
    }


# ---------------------------------------------------------------- test evaluation
def render_test_evaluation(res: dict) -> str:
    L = [
        "# Phase 4 final TEST-period evaluation",
        "",
        DISCLAIMER,
        "",
        f"Frozen definition `{res['definition_id']}`, shrinkage `{res['shrinkage_config']}`, "
        f"baseline `{res['baseline_version']}`. The configuration was frozen from TRAIN and "
        "VALIDATION only. The test lock was opened once by `evaluate_on_test`; nothing was "
        "changed after seeing TEST outcomes.",
        "",
        kv(
            {
                "frozen thresholds reproduced from TRAIN": res["frozen_thresholds_reproduced"],
                "TEST delivery rows": res["test_rows_total"],
                "TEST matches": res["test_matches"],
                "TEST_CORE end date": res["test_core_end"],
                "players required for a player-level test": res["min_players_player_level"],
                "TEST pressure balls a qualifying player needs": res["min_test_balls"],
            }
        ),
        "",
        "## B0 calibration on TEST (out of period)",
        md_table(
            [
                "scope",
                "format",
                "role",
                "stream",
                "rows",
                "matches",
                "actual",
                "expected",
                "residual",
            ],
            [
                [
                    r["test_scope"],
                    r["format"],
                    r["role"],
                    r["stream"],
                    r["rows"],
                    r["matches"],
                    r["mean_actual"],
                    r["mean_expected"],
                    r["mean_residual"],
                ]
                for r in res["calibration"]
            ],
        ),  # fmt: skip
        "",
        "## Pressure effect on TEST (population level)",
        "Mean B0 residual of pressure rows minus non-pressure rows of the same definition "
        "population. The interval is a seeded match-cluster bootstrap (2.5 and 97.5 percentiles).",
        md_table(
            [
                "scope",
                "format",
                "role",
                "stream",
                "pressure rows",
                "other rows",
                "matches",
                "effect",
                "low",
                "high",
                "status",
            ],
            [
                [
                    r["test_scope"],
                    r["format"],
                    r["role"],
                    r["stream"],
                    r["pressure_rows"],
                    r["non_pressure_rows"],
                    r["matches"],
                    r["effect"],
                    r["ci_low"],
                    r["ci_high"],
                    r["status"],
                ]
                for r in res["population"]
            ],
        ),  # fmt: skip
        "",
        "## Player level (PRE_TEST estimate against TEST outcome)",
        "A cell is evaluated only when enough players qualify (eligible in the frozen working "
        "pool and with enough TEST pressure balls). Otherwise it is reported as insufficient and "
        "is not relaxed. Loss is the TEST-ball-weighted squared error.",
        md_table(
            [
                "scope",
                "format",
                "role",
                "eligible with TEST balls",
                "qualifying",
                "status",
                "loss shrunk",
                "loss raw",
                "loss zero",
                "shrunk minus raw",
                "ci low",
                "ci high",
                "Spearman shrunk",
                "Spearman raw",
            ],
            [
                [
                    r["test_scope"],
                    r["format"],
                    r["role"],
                    r.get("pre_test_eligible_players_with_test_balls"),
                    r.get("qualifying_players"),
                    r["status"],
                    (r.get("loss_weighted_mse") or {}).get("shrunk"),
                    (r.get("loss_weighted_mse") or {}).get("raw"),
                    (r.get("loss_weighted_mse") or {}).get("zero"),
                    r.get("loss_diff_shrunk_minus_raw"),
                    r.get("loss_diff_ci_low"),
                    r.get("loss_diff_ci_high"),
                    r.get("spearman_shrunk_vs_test"),
                    r.get("spearman_raw_vs_test"),
                ]
                for r in res["player_level"]
            ],
        ),  # fmt: skip
        "",
        "## Notes",
        "- TEST par is strictly prior and includes earlier TEST first innings (they precede the "
        "evaluated match); the frozen thresholds were fitted on TRAIN only.",
        "- `TEST_CORE` limits TEST to dates up to the configured core end; the later T20I dates "
        "are kept as recorded in `TEST`.",
        "- A negative `shrunk minus raw` loss difference favours shrinkage. The interval is "
        "descriptive and not corrected for the number of cells.",
    ]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- pressure scoring report
def render_pressure_scoring(b: Bundle) -> str:
    f, s = b.frozen, b.scores
    defn, cfg = f["definition"]["id"], f["shrinkage"]["config"]
    lead = b.selection["selection"]["leading_provisional"]
    carried = s[s["definition_id"] == defn]
    summ = cell_summary(s, f)
    by_def = (
        s.groupby("definition_id")
        .agg(
            records=("player_id", "size"),
            eligible=("eligibility_status", lambda x: int(x.str.startswith("ELIGIBLE").sum())),
        )
        .reset_index()
    )
    lead_rows = s[(s["definition_id"] == lead) & (s["shrinkage_config"] == cfg)]
    lead_el = lead_rows[lead_rows["eligibility_status"].str.startswith("ELIGIBLE")]
    car_el = carried[
        (carried["shrinkage_config"] == cfg)
        & carried["eligibility_status"].str.startswith("ELIGIBLE")
    ]
    pools = pd.concat(
        [
            car_el.groupby(["role", "stream", "format"]).size().rename(f"eligible_{defn}"),
            lead_el.groupby(["role", "stream", "format"]).size().rename(f"eligible_{lead}"),
        ],
        axis=1,
    ).reset_index()
    none = carried[carried["shrinkage_config"] == "shrink_none"]
    cmpr = []
    if len(none):
        m = carried[carried["shrinkage_config"] == cfg].merge(
            none, on=["player_id", "role", "stream", "format"], suffixes=("_s", "_n")
        )
        for (role, stream, fmt_), g in m.groupby(["role", "stream", "format"]):
            cmpr.append(
                [role, stream, fmt_, len(g), float((g["shrunk_estimate_s"] - g["shrunk_estimate_n"]).abs().mean()),
                 float(g["interval_high_s"].sub(g["interval_low_s"]).median()),
                 float(g["interval_high_n"].sub(g["interval_low_n"]).median())]
            )  # fmt: skip
    schema = [c for c in s.columns if c not in ("is_carried_definition", "is_leading_provisional")]
    L = [
        "# Phase 4 pressure scoring report (Stage C)",
        "",
        DISCLAIMER,
        "",
        "These are experimental player estimates, not rankings. " + elig_text(b) + " Players in "
        "the working pool are labelled by their eligibility status below.",
        "",
        "## Configuration (frozen before the TEST period was opened)",
        kv(
            {
                "carried definition": f"{defn} ({f['definition']['label']})",
                "leading provisional (Phase 3, not validated)": lead,
                "pressure definition version": carried["definition_version"].iloc[0],
                "baseline version": f["baseline"]["version"],
                "shrinkage configuration": cfg,
                "shrinkage rule": f["shrinkage"]["rule"],
                "seed": str(f["seed"]),
                "bootstrap resamples": f["n_boot"],
                "window": ", ".join(sorted(carried["window"].unique())),
                "TRAIN-only thresholds": json.dumps(f["definition"]["train_only_thresholds"]),
            }
        ),
        "",
        "Zero shrinkage (`shrink_none`) is kept as a sensitivity configuration for the carried "
        "definition. All nine candidate definitions are scored under the frozen shrinkage "
        "configuration; the carried definition is flagged `is_carried_definition` and "
        f"`{lead}` is flagged `is_leading_provisional` so the choice can be reviewed.",
        "",
        "## Record schema",
        "Each record holds: " + ", ".join(f"`{c}`" for c in schema) + ".",
        "",
        "## Records and eligible players by definition (all shrinkage configurations scored)",
        md_table(
            ["definition", "records", "eligible"],
            rows_of(by_def, ["definition_id", "records", "eligible"]),
        ),
        "",
        "## Cells of the carried definition (frozen shrinkage, eligible = working pool)",
        md_table(list(summ.columns), rows_of(summ, list(summ.columns))),
        "",
        "## Eligible pools: carried definition versus the leading provisional",
        md_table(list(pools.columns), rows_of(pools, list(pools.columns))),
        "",
        "## Shrinkage effect on the carried definition",
        "Mean absolute difference between the shrunk estimates under the frozen configuration "
        "and under zero shrinkage, and the median interval width of each.",
        md_table(
            [
                "role",
                "stream",
                "format",
                "players",
                "mean abs diff",
                "median width (frozen)",
                "median width (zero)",
            ],
            cmpr,
        ),
        "",
        "## Eligibility status values",
        md_table(
            ["status", "records"],
            [[k, int(v)] for k, v in carried["eligibility_status"].value_counts().items()],
        ),
        "",
        "## Applied data restrictions",
        carried["applied_restrictions"].iloc[0],
        "",
        "## Final TEST evaluation",
        "See `phase4_test_evaluation.md`. It uses this frozen configuration and changes no value "
        "in this report."
        if b.test_eval
        else "The TEST evaluation has not been run for this report.",
        "",
        "## Limitations",
        "- The primary residual mixes pressure-specific skill and general skill (B0 has no "
        "player term). A within-player differential is not reported.",
        "- Bowler pressure uses the batter state signals (the bowler-specific signal is not "
        "implemented).",
        "- Intervals hold the shrinkage strength and target fixed; between-player variance "
        "uncertainty is not propagated.",
        "- Combined records exist only for players eligible in both formats under the same "
        "frozen rules. The 70:30 weight is a provisional default, not an optimised weight.",
        "- A shrinkage strength was chosen on VALIDATION; compare the differences between "
        "candidate strengths with their bootstrap error in the shrinkage report.",
        "- `shrinkage_floor_hit` true means the fitted between-player variance fell below the "
        "floor, so the strength is capped by the floor (see the floor-hit share above).",
        "- " + snr_text(b),
    ]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- data quality report
def render_data_quality(
    b: Bundle, split_cfg: dict, exclusions: pd.DataFrame, late: dict, literals: dict
) -> str:
    dq, ph = b.dq, b.manifest["phases"]
    chk = dq["checks"]
    reg = json.loads((BACKEND / "config" / "data_quality_restrictions_v1.json").read_text("utf-8"))
    i34, ex, wf, dls, dn, xi = (
        chk["innings_3_4"], chk["extras"], chk["wicket_flags"], chk["dls"],
        chk["duplicate_names"], chk["xi_duplicates"],
    )  # fmt: skip
    ex_tab = exclusions.copy()
    ex_tab["share_of_period"] = ex_tab["rows"] / ex_tab.groupby("period")["rows"].transform("sum")
    total_rows = int(ex_tab["rows"].sum())
    L = [
        "# Phase 4 data-quality report",
        "",
        DISCLAIMER,
        "",
        "Restrictions come from `config/data_quality_restrictions_v1.json` and are applied as "
        "masks on metrics and features. No official record was changed or deleted and no match "
        "was excluded globally. Figures below are read from the stored Phase 3 register "
        "application (`phase3_data_quality_application.json`), the Phase 4 split manifest, the "
        "exploratory store, and a scan of the Phase 4 source files.",
        "",
        "## 1. Register",
        kv(
            {
                "register version": reg["version"],
                "register status": reg["status"],
                "rules": len(reg["restrictions"]),
                "global exclusion": reg["global_exclusion"],
                "rules implemented": dq["invariants"]["all_rules_implemented"],
                "records deleted": dq["records_deleted"],
                "innings 3/4 rows in a pressure population": dq["invariants"][
                    "innings_3_4_rows_in_pressure_population"
                ],
            }
        ),
        "",
        "## 2. Row categories used by Phase 4 scoring (all delivery rows preserved)",
        f"Total state rows: {total_rows:,}. Categories are mutually exclusive and applied in the "
        "listed order. Counts use flags and dates only (no outcome columns).",
        md_table(
            ["period", "category", "rows", "share of period"],
            rows_of(ex_tab, ["period", "category", "rows", "share_of_period"]),
        ),
        "",
        "## 3. Innings 3 and 4 (RULE_INNINGS_3_4)",
        kv(
            {
                "rows": i34["rows"],
                "matches": i34["matches"],
                "rows by innings": json.dumps(i34["rows_by_innings"]),
                "reason codes (rows)": json.dumps(i34["reason_codes"]),
                "matches by reason": json.dumps(i34["matches_by_reason"]),
                "rows still in the official deliveries table": i34[
                    "source_rows_preserved_in_official_db"
                ],
                "any row in a pressure population": i34["any_row_in_a_pressure_population"],
            }
        ),
        "",
        "Two reason codes apply: `CONFIRMED_SUPER_OVER_BY_CRICSHEET` (confirmed by the Phase 2.5 "
        "validation report) and `UNVERIFIED_INNINGS_ROLE` (role not verified). Both are excluded "
        "from every metric the rule lists.",
        "",
        "## 4. Extras (`other`, `Penalty`) preserved and flagged",
        md_table(["extras category", "rows"], [[k, v] for k, v in ex["category_counts"].items()]),
        kv(
            {
                "`other` rows mapped to None": ex["other_rows_mapped_to_none"],
                "`Penalty` rows mapped to None": ex["penalty_rows_mapped_to_none"],
                "rows with an unverified label": ex["unverified_label_rows"],
                "Penalty rows removed from ball-count masks": json.dumps(
                    ex["penalty_rows_excluded_by_metric_mask"]
                ),
                "rows with secondary extras runs": ex["secondary_runs_rows"],
                "secondary-runs guard blocks bowler economy": ex["secondary_guard_blocks_economy"],
            }
        ),
        "",
        "## 5. Wicket-flag anomalies",
        kv(
            {
                "dismissed player without wicket flag (rows)": wf[
                    "dismissed_without_wicket_flag_rows"
                ],
                "wicket flag without dismissed player (rows)": wf[
                    "wicket_flag_without_dismissed_rows"
                ],
                "state rows where wicket-count variants differ": wf[
                    "state_rows_where_wicket_count_variants_differ"
                ],
                "state rows dropped": wf["state_features_rows_dropped"],
                "dismissal-metric rows excluded (primary)": json.dumps(
                    wf["dismissal_metric_rows_excluded_primary"]
                ),
            }
        ),
        "",
        "## 6. DLS and shortened innings (never imputed)",
        kv(
            {
                "DLS matches": dls["dls_matches"],
                "DLS rows": dls["dls_match_rows"],
                "rows without reconstructable revised state": dls[
                    "rows_without_reconstructable_revised_state"
                ],
                "shortened innings (limit below 120)": ph["shortened"]["shortened_innings"],
                "shortened matches": ph["shortened"]["shortened_matches"],
                "shortened deliveries": ph["shortened"]["shortened_deliveries"],
                "all shortened innings excluded by the DLS mask": ph["shortened"][
                    "shortened_innings_all_rows_dls_excluded"
                ],
                "chase rows excluded that would otherwise be eligible": ph["dls"][
                    "dls_excluded_chase_rows_otherwise_eligible"
                ],
                "DLS resources imputed": ph["dls"]["dls_resources_imputed"],
                "delivery rows deleted": ph["dls"]["rows_deleted"],
                "deliveries whose phase label depends on a revised limit": ph["revision_timing"][
                    "deliveries_whose_label_depends_on_revised_limit"
                ],
                "revision announcement time in the data": ph["revision_timing"][
                    "announcement_time_in_data"
                ],
            }
        ),
        "",
        "Shortened innings by period: "
        + json.dumps(ph["shortened"]["shortened_innings_by_period"], sort_keys=True)
        + ". Phase boundaries for every innings limit present are in `phase4_phase_boundaries.md`. "
        "Phase labels use only the legal balls bowled before the delivery and the innings limit.",
        "",
        "## 7. Identity by player_id only",
        kv(
            {
                "players sharing a name": dn["players_sharing_a_name"],
                "distinct shared names": dn["distinct_shared_names"],
                "rows if joined on id": dn["rows_if_joined_on_id"],
                "rows if naively joined on name": dn["rows_if_naively_joined_on_name"],
                "ids a name join would merge": dn["ids_that_would_merge_by_name"],
                "name-join guard raises": dn["name_join_guard_raises"],
                "pipeline join key": dn["pipeline_join_key"],
            }
        ),
        "",
        "## 8. Duplicate squad records never multiply statistics",
        kv(
            {
                "squad rows": xi["squad_rows"],
                "rows flagged duplicate": xi["duplicate_flag_rows"],
                "pressure-sample rows without a squad join": xi["pressure_sample_rows"],
                "rows with the safe join": xi["rows_with_safe_squad_join"],
                "rows with a naive join": xi["rows_with_naive_squad_join"],
                "per-player counts identical with and without the safe join": xi[
                    "per_player_counts_identical_without_and_with_safe_join"
                ],
                "Phase 4 scoring uses match_squads": xi["pipeline_uses_match_squads"],
            }
        ),
        "",
        "## 9. Cricsheet is not a data source",
        f"Scan of {literals['files_scanned']} Phase 4 data and scoring source files (the report writers "
        f"are excluded) for string literals (excluding docstrings) containing `cricsheet`: {literals['string_literal_hits']} hits"
        + (f" ({', '.join(literals['hits'])})." if literals["hits"] else ".")
        + " Cricsheet appears only as a reason-code label inherited from the Phase 2.5 register.",
        "",
        "## 10. Date observation",
        kv(late),
        "",
        "T20I matches dated after the core end carry deliveries and sit in the TEST period. Dates "
        "are used as recorded and were not corrected. The TEST evaluation reports a `TEST_CORE` "
        "sensitivity that excludes them. Please confirm whether these dates are real.",
        "",
        "## 11. Limits",
        "- The register application (sections 3 to 8) was computed in Phase 3 over all periods "
        "from descriptive flags, not from TEST outcomes.",
        "- The register is PROVISIONAL; rules marked DOCUMENT_ONLY change no metric.",
        "- Split boundaries: " + json.dumps(split_cfg["periods"], sort_keys=True) + ".",
    ]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- user summary
def render_user_summary(b: Bundle, split_cfg: dict, late: dict) -> str:
    m, f, sel = b.manifest, b.frozen, b.selection["selection"]
    cand = pd.DataFrame(sel["candidates"])
    lock = lock_facts(b.lock_log)
    cov = b.classification_cov
    summ = cell_summary(b.scores, f)
    te = b.test_eval
    fw = b.fw_results
    mp = pd.DataFrame(m["matches_by_format_period"])
    cal_rows = []
    for name, st in b.calibration["streams"].items():
        v = st["periods"].get("VALIDATION", {})
        cal_rows.append([name, v.get("rows"), v.get("mean_residual"), v.get("residual_sd"),
                         max(i["rel_diff"] for i in st["calibration_identity_train_pooled"].values())])  # fmt: skip
    ef = b.elig_frozen
    pools = b.rank_summary
    L = [
        "# Phase 4 user summary: experimental pressure scoring and temporal validation",
        "",
        DISCLAIMER,
        "",
        "**Exploratory versus validated.** Everything here is exploratory. No pressure definition, "
        "threshold, shrinkage strength or format weight is validated. **Official rankings and final "
        "ML model training are not authorised and have not been done; they await your approval.**",
        "",
        "## 1. Data split methodology",
        "Chronological, by match date. Matches and their deliveries stay together; there is no "
        "random row split. Boundaries were written to `config/phase4_split_v1.json` before any "
        "evaluation code ran.",
        md_table(
            ["period", "start", "end"],
            [[k, v.get("start"), v.get("end")] for k, v in split_cfg["periods"].items()],
        ),
        md_table(
            ["format", "period", "matches", "first date", "last date"],
            rows_of(mp, ["competition_type", "period", "matches", "first", "last"]),
        ),
        "Baseline cells, wickets bins, shrinkage strength and the shrinkage target use TRAIN "
        "only. Pressure thresholds use TRAIN only. VALIDATION chose the shrinkage strength. TEST "
        "was opened once, after the choices were frozen.",
        "",
        "## 2. Temporal leakage checks",
        kv(
            {
                "matches in more than one period": m["integrity"][
                    "matches_in_more_than_one_period"
                ],
                "rows whose period differs from the date rule": m["integrity"][
                    "rows_with_period_not_equal_to_date_rule"
                ],
                "periods strictly ordered by date": m["integrity"][
                    "periods_strictly_ordered_by_date"
                ],
                "par: rows unavailable (insufficient prior matches)": m["par_coverage"][
                    "total_rows_unavailable"
                ],
                "par: innings unavailable": m["par_coverage"]["total_innings_unavailable"],
                "par: null pattern identical to the earlier prior-only column": m[
                    "par_equivalence"
                ]["null_pattern_identical"],
                "phase labels equal a function of (legal balls before, limit)": m["phases"][
                    "label_checks"
                ]["stored_labels_equal_recomputed_from_B_and_L"],
                "labels unchanged when the last 30% of each innings is removed": m["phases"][
                    "label_checks"
                ]["labels_unchanged_when_last_30pct_of_each_innings_removed"],
                "test lock: FREEZE recorded before OPEN": lock["freeze_recorded_before_open"],
                "test lock: opened exactly once": lock["opened_exactly_once"],
                "test lock: hash at open equals hash at freeze": lock[
                    "hash_at_open_equals_hash_at_freeze"
                ],
                "test lock: refused reads logged": lock["READ_DENIED_entries"],
                "frozen thresholds reproduced inside the TEST run": None
                if not te
                else te["frozen_thresholds_reproduced"],
            }
        ),
        "Par uses only matches dated strictly before the evaluated match (same-day matches "
        "excluded); with too few prior matches the value is missing and flagged, never zero. "
        "Leave-one-match-out par is descriptive only. The lock is a convention-level guard, not a "
        "security boundary.",
        "",
        "## 3. Baseline calibration",
        f"Baseline `{b.calibration['baseline_version']}`; calibration identity on TRAIN holds: "
        f"{b.calibration['identity_ok']}.",
        md_table(
            [
                "stream",
                "VALIDATION rows",
                "mean residual",
                "residual sd",
                "TRAIN identity relative diff",
            ],
            cal_rows,
        ),
        "Details by format, phase, wickets remaining, expected decile and year are in "
        "`phase4_baseline_calibration_report.md`.",
        "",
        "## 4. Pressure definition comparison",
        f"Rule file SHA-256 `{b.selection['rule_sha256']}` (written before the metrics). "
        f"The rule winner is `{sel['winner']}`, labelled: {sel['label']}. The Phase 3 leading "
        f"candidate `{sel['leading_provisional']}` has status `{sel['leading_status']}` and is "
        f"{'in' if sel['leading_in_top_group'] else 'not in'} the top group "
        f"({', '.join(sel['top_group'])}; tie margin {sel['tie_margin_used']:.3f}). Eligible "
        "population never decides the choice.",
        md_table(
            [
                "definition",
                "status",
                "Sc",
                "bootstrap SE",
                "selection share",
                "min players per cell",
            ],
            rows_of(
                cand, ["definition_id", "status", "Sc", "Sc_boot_se", "selection_share", "min_P"]
            ),
        ),
        selection_text(b) + " Full table: `phase4_definition_comparison.md`.",
        "",
        "## 5. Eligibility thresholds",
        "Thresholds were re-derived per format and role from TRAIN distributions. " + elig_text(b),
        md_table(
            ["format", "role", "status", "working threshold (balls)", "window ratio", "pool size"],
            [
                [
                    r["format"],
                    r["role"],
                    r["status"],
                    r["working_pool_threshold_balls"],
                    r["window_ratio_W"],
                    _pool(pools, r["format"], r["role"]),
                ]
                for _, r in ef.iterrows()
            ],
        ),  # fmt: skip
        "",
        "## 6. Shrinkage",
        f"Chosen on VALIDATION: `{b.shrink_choice['chosen']}` (rule: {b.shrink_choice['rule']}). "
        "Zero shrinkage is retained as a sensitivity configuration.",
        md_table(
            ["config", "validation loss", "difference vs eb", "bootstrap SE", "choosable"],
            [
                [k, v["loss"], v["diff_vs_eb"], v["bootstrap_se"], v["choosable"]]
                for k, v in b.shrink_choice["losses"].items()
            ],
        ),
        "",
        "## 7. Format weighting (independent of the definition comparison)",
        "70:30 stays a provisional default; the evidence does not show it is optimal or validated. "
        "Pools are players eligible in both formats under the same frozen rules.",
        md_table(
            [
                "role",
                "config",
                "pool",
                "Top 10 overlap vs 70:30",
                "Spearman vs 70:30",
                "bootstrap Spearman",
            ],
            rows_of(
                fw,
                [
                    "role",
                    "config_id",
                    "pool_size",
                    "top10_overlap_vs_default",
                    "spearman_vs_default",
                    "bootstrap_mean_spearman",
                ],
            ),
        ),
        "",
        "## 8. Ranking stability (experimental distributions, not rankings)",
        md_table(
            [
                "format",
                "role",
                "pool",
                "expected Top 10 overlap",
                "mean Spearman",
                "Spearman 2.5%",
                "Spearman 97.5%",
            ],
            rows_of(
                pools,
                [
                    "scope",
                    "role",
                    "pool_size",
                    "expected_top10_overlap",
                    "mean_spearman",
                    "spearman_p2_5",
                    "spearman_p97_5",
                ],
            ),
        ),
        "Pools are never padded; pools smaller than ten are reported as they are.",
        "",
        "## 9. Uncertainty",
        md_table(
            [
                "role",
                "stream",
                "format",
                "eligible",
                "median interval width",
                "share of intervals excluding 0",
            ],
            rows_of(
                summ,
                [
                    "role",
                    "stream",
                    "format",
                    "eligible",
                    "median_interval_width",
                    "share_interval_excludes_0",
                ],
            ),
        ),
        _rank_interval_line(b.rank_dist),
        "",
        "## 10. Final TEST evaluation",
        _test_lines(te),
        "",
        "## 11. Data-quality restrictions applied",
        f"Register `data_quality_restrictions_v1` ({b.dq['invariants']['register_rules']} rules, "
        f"global exclusion {b.dq['global_exclusion']}). Innings 3 and 4, DLS rows that cannot be "
        "reconstructed, `Penalty` extras, and wicket-flag anomalies are masked per rule; "
        f"{m['phases']['dls']['dls_excluded_rows_in_scope']} DLS rows in "
        f"{m['phases']['dls']['dls_excluded_regulation_innings']} innings are excluded and no "
        "resources are imputed. Details: `phase4_data_quality_report.md`. The T20I dates after "
        f"{late['core_end']} ({late['t20i_matches_after_core_end']} matches, last "
        f"{late['last_date']}) need your confirmation.",
        "",
        "## 12. Classification coverage (uncapped intelligence)",
        f"{cov['players_total']} players. Verified Uncapped: {cov['uncapped_verified_count']}. "
        "Nationality and status are independent fields with per-field verification.",
        md_table(
            ["nationality", "status", "all players", "players with an eligible score"],
            [
                [a["nationality"], a["international_status"], a["players"], c["players"]]
                for a, c in zip(
                    cov["combinations_all_players"], cov["combinations_scored_players"], strict=True
                )
            ],
        ),
        f"Nationality unknown reasons: {json.dumps(cov['nationality_unknown_reasons'])}. Status "
        f"unknown reasons: {json.dumps(cov['status_unknown_reasons'])}. Every uncapped ranking and "
        "preset is empty or reports a pool-too-small status until a verified cap source is supplied.",
        "",
        "## 13. Known limitations",
        "- " + snr_text(b),
        "- Bowler pressure uses batter state signals. The primary residual mixes pressure-specific "
        "and general skill.",
        "- Shrinkage and eligibility choices rest on small samples; no multiplicity correction.",
        "- The bootstrap holds thresholds, baseline and shrinkage strength fixed.",
        "- " + _test_support_text(te),
        "",
        "## 14. Recommended final methodology (a recommendation that needs your approval)",
        "- Keep the B0 baseline fitted on TRAIN (or on TRAIN plus VALIDATION after approval).",
        f"- Treat `{f['definition']['id']}` as one of several defensible definitions, not the answer; "
        f"the rule winner and `{sel['leading_provisional']}` are not distinguished with confidence.",
        f"- Use leave-one-player-out shrinkage toward the pooled mean of other players "
        f"(`{f['shrinkage']['config']}` here) and always publish intervals and the data weight.",
        "- Do not publish a Top 10 until a threshold passes the data-weight gate or you accept the "
        "working-pool label, and until more matches accumulate.",
        "- Keep 70:30 labelled provisional unless you accept it as a policy choice.",
        "",
        "## 15. Open decisions for you",
        "1. Accept or change the split boundaries and the TEST period (including the late T20I dates).",
        "2. Choose the pressure definition (rule winner, the Phase 3 leading candidate, or another).",
        "3. Decide whether a working pool below the data-weight gate may support any public output.",
        "4. Decide whether to refit on TRAIN plus VALIDATION for the final model.",
        "5. Supply the classification source below, or confirm that status stays Unknown.",
        "6. Approve (or not) the next stage: official rankings and any ML model training.",
        "",
        "## 16. Data request list",
        "- A verified list of capped/uncapped status keyed by `player_id` (or name plus team), from "
        "an official board or ICC record or a squad sheet with a capped column.",
        f"- `player_id` keys for the {len(b.unresolved)} unresolved squad names "
        "(`phase4_unresolved_players.csv`).",
        "- Nationality for players outside the squad file, if needed.",
        "- Confirmation of the T20I match dates after the TEST core end.",
        "",
        "## 17. Reproducibility and preservation",
        _spot_lines(b.spot),
    ]
    return "\n".join(L) + "\n"


def _pool(pools: pd.DataFrame, fmt_: str, role: str) -> Any:
    g = pools[(pools["scope"] == fmt_) & (pools["role"] == role)]
    return None if g.empty else int(g["pool_size"].iloc[0])


def _rank_interval_line(dist: pd.DataFrame) -> str:
    if dist.empty:
        return ""
    w = (dist["rank_hi"] - dist["rank_lo"]).groupby([dist["scope"], dist["role"]]).median()
    rows = [[a, b, float(v)] for (a, b), v in w.items()]
    return "Median width of the rank interval (95%):\n\n" + md_table(
        ["format", "role", "median rank-interval width"], rows
    )


def _test_lines(te: dict | None) -> str:
    if not te:
        return "The TEST evaluation was not run."
    pl = te["player_level"]
    ok = [r for r in pl if r["status"] == "OK" and r["test_scope"] == "TEST"]
    insuff = [r for r in pl if r["status"] != "OK" and r["test_scope"] == "TEST"]
    pe = [r for r in te["population"] if r["test_scope"] == "TEST" and r["effect"] is not None]
    lines = [
        f"The frozen configuration was evaluated once on {te['test_matches']} TEST matches. "
        f"Population-level pressure effects: {len(pe)} cells estimated. Player-level: {len(ok)} "
        f"cells with enough qualifying players, {len(insuff)} reported as insufficient. "
        "Details and intervals: `phase4_test_evaluation.md`.",
    ]
    cal = [
        r["mean_residual"]
        for r in te["calibration"]
        if r["test_scope"] == "TEST" and r["stream"] in ("runs", "charged")
    ]
    if cal:
        lines.append(
            f"B0 mean residual on TEST for the run streams ranges from {min(cal):.3f} to "
            f"{max(cal):.3f} runs per ball (VALIDATION values are in section 3); a positive value "
            "means the TRAIN-frozen baseline under-predicts scoring in the TEST year."
        )
    if ok:
        n_excl = sum(
            1
            for r in ok
            if r["loss_diff_ci_low"] is not None
            and r["loss_diff_ci_high"] is not None
            and (r["loss_diff_ci_high"] < 0 or r["loss_diff_ci_low"] > 0)
        )
        lines.append(
            f"The shrunk-minus-raw loss interval excludes 0 in {n_excl} of {len(ok)} cells; the "
            "intervals are not corrected for the number of cells."
        )
        lines.append(
            md_table(
                ["format", "role", "qualifying", "shrunk minus raw loss", "ci low", "ci high"],
                [
                    [
                        r["format"],
                        r["role"],
                        r["qualifying_players"],
                        r["loss_diff_shrunk_minus_raw"],
                        r["loss_diff_ci_low"],
                        r["loss_diff_ci_high"],
                    ]
                    for r in ok
                ],
            )  # fmt: skip
        )
    return "\n\n".join(lines)


def _test_support_text(te: dict | None) -> str:
    if not te:
        return "The TEST evaluation was not run."
    pl = [r for r in te["player_level"] if r["test_scope"] == "TEST"]
    bad = [r for r in pl if r["status"] != "OK"]
    return (
        f"{len(pl) - len(bad)} of {len(pl)} player-level TEST cells had enough qualifying players "
        "(cells without enough are reported as insufficient, never relaxed)."
    )


def _spot_lines(sp: dict | None) -> str:
    if not sp:
        return "Spot checks have not been run."
    return (
        f"Independent spot checks: {sum(1 for c in sp['checks'] if c['ok'])} of "
        f"{len(sp['checks'])} agree (`phase4_spot_checks.json`).\n\n"
        + md_table(
            ["check", "method", "ok"], [[c["id"], c["method"], c["ok"]] for c in sp["checks"]]
        )
    )
