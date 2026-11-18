"""Read-only service behind ``/api/v1/submission/*``.

Sources are the generated report files and the analytical store of the configured source (Phase 9
by default; ``SUPERR_SUBMISSION_SOURCE=phase8`` serves the Phase 8 store and the ``_phase8`` file copies) (opened read-only
with fixed, parameterised queries; no request value is ever placed in SQL text). Nothing is
computed from request values except sorting, filtering and percentile ranks of stored profiles.
Every call builds new response objects.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.api.errors import ApiError
from app.phase8.constants import PHASE8_DB, PHASE9_DB, REPORTS_DIR

ROLE = {"batters": "batter", "bowlers": "bowler"}
STATUS_ORDER = ["INSUFFICIENT_EVIDENCE", "EXPLORATORY", "PROVISIONAL", "VALIDATED"]
NAVIGATION = [
    "Overview",
    "Top 10 Batters",
    "Top 10 Bowlers",
    "Batter Profiles",
    "Bowler Profiles",
    "Player Comparison",
    "Why Selected / Why Not Selected",
    "Pressure Methodology",
    "Data & Validation",
    "Experimental AI Predictions",
]
MIN_RADAR_DENOMINATOR = 30
BASE_CAVEATS = [
    "Pressure rankings are exploratory unless a status label says otherwise; the order of "
    "players is not shown to separate them beyond noise.",
    "Experimental AI outputs are separate from the submitted lists and are not validated.",
    "Descriptive profiles carry no rank, score or eligibility field.",
]
# (key, label, value column, denominator column, denominator label, higher is better)
RADAR = {
    "batter": [
        ("strike_rate", "Strike rate", "strike_rate", "balls_faced", "balls faced", True),
        (
            "boundary_ball_share",
            "Boundary ball share",
            "boundary_ball_share",
            "balls_faced",
            "balls faced",
            True,
        ),
        ("dot_ball_share", "Dot ball share", "dot_ball_share", "balls_faced", "balls faced", False),
        (
            "balls_per_dismissal",
            "Balls per dismissal",
            "balls_per_dismissal",
            "balls_faced",
            "balls faced",
            True,
        ),
        (
            "pp_strike_rate",
            "Powerplay strike rate",
            "pp_strike_rate",
            "pp_balls",
            "powerplay balls",
            True,
        ),
        (
            "mid_strike_rate",
            "Middle-overs strike rate",
            "mid_strike_rate",
            "mid_balls",
            "middle balls",
            True,
        ),
        (
            "death_strike_rate",
            "Death-overs strike rate",
            "death_strike_rate",
            "death_balls",
            "death balls",
            True,
        ),
        (
            "vs_pace_strike_rate",
            "Strike rate vs pace",
            "vs_pace_strike_rate",
            "vs_pace_balls",
            "balls vs pace",
            True,
        ),
        (
            "vs_spin_strike_rate",
            "Strike rate vs spin",
            "vs_spin_strike_rate",
            "vs_spin_balls",
            "balls vs spin",
            True,
        ),
    ],
    "bowler": [
        ("economy", "Economy", "economy", "legal_balls", "legal balls", False),
        ("dot_ball_share", "Dot ball share", "dot_ball_share", "legal_balls", "legal balls", True),
        (
            "boundary_conceded_share",
            "Boundary share of runs conceded",
            "boundary_conceded_share",
            "legal_balls",
            "legal balls",
            False,
        ),
        (
            "balls_per_wicket",
            "Balls per wicket",
            "balls_per_wicket",
            "legal_balls",
            "legal balls",
            False,
        ),
        ("pp_economy", "Powerplay economy", "pp_economy", "pp_balls", "powerplay balls", False),
        ("mid_economy", "Middle-overs economy", "mid_economy", "mid_balls", "middle balls", False),
        (
            "death_economy",
            "Death-overs economy",
            "death_economy",
            "death_balls",
            "death balls",
            False,
        ),
        (
            "vs_rhb_economy",
            "Economy vs right-handers",
            "vs_rhb_economy",
            "vs_rhb_balls",
            "balls vs right-handers",
            False,
        ),
        (
            "vs_lhb_economy",
            "Economy vs left-handers",
            "vs_lhb_economy",
            "vs_lhb_balls",
            "balls vs left-handers",
            False,
        ),
    ],
}
VOLUME_COL = {"batter": "balls_faced", "bowler": "legal_balls"}


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """JSON-safe records: NaN and NaT become null, numpy scalars become Python values."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class SubmissionService:
    def __init__(
        self,
        reports: Path | str | None = None,
        db: Path | str | None = None,
        descriptive_reports: Path | str | None = None,
        source: str | None = None,
    ) -> None:
        src = (source or os.environ.get("SUPERR_SUBMISSION_SOURCE") or "phase9").lower()
        if src not in ("phase8", "phase9"):
            raise ValueError(f"unknown submission source '{src}' (phase8 or phase9)")
        self.source = src
        self.prefix = "p9_" if src == "phase9" else "p8_"
        self.suffix = "" if src == "phase9" else "_phase8"
        self.reports = Path(reports) if reports else REPORTS_DIR
        self.db = Path(db) if db else (PHASE9_DB if src == "phase9" else PHASE8_DB)
        self.descriptive_reports = (
            Path(descriptive_reports) if descriptive_reports else self.reports
        )
        self._lock = threading.Lock()
        self._frames: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------ storage helpers
    def _unavailable(self, what: str, exc: Exception | None = None) -> ApiError:
        return ApiError(
            503,
            "SUBMISSION_DATA_UNAVAILABLE",
            f"{what} is not available; run the Phase 8 scripts",
            str(exc) if exc else None,
        )

    def _fn(self, name: str) -> str:
        """Report file name of the active source (Phase 8 outputs are kept as ``*_phase8`` copies)."""
        if not self.suffix:
            return name
        stem, dot, ext = name.rpartition(".")
        return f"{stem}{self.suffix}{dot}{ext}"

    def query(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        """Fixed SQL text only; values are always bound parameters."""
        try:
            con = duckdb.connect(str(self.db), read_only=True)
        except (duckdb.Error, OSError) as exc:
            raise self._unavailable("the Phase 8 analytical store", exc) from exc
        try:
            return con.execute(sql.replace("p8_", self.prefix), params or []).df()
        except duckdb.Error as exc:
            raise self._unavailable("a Phase 8 analytical table", exc) from exc
        finally:
            con.close()

    def _csv(self, name: str, base: Path | None = None) -> pd.DataFrame:
        p = (base or self.reports) / self._fn(name)
        try:
            stamp = p.stat()
            key = f"{self.source}|{p}|{stamp.st_mtime_ns}|{stamp.st_size}"
        except OSError:
            key = f"{self.source}|{p}"
        with self._lock:
            if key not in self._frames:
                try:
                    self._frames[key] = pd.read_csv(p)
                except (OSError, ValueError) as exc:
                    raise self._unavailable(name, exc) from exc
            return self._frames[key].copy()

    # ------------------------------------------------------------------ status and stamps
    def list_status(self) -> list[dict[str, Any]]:
        d = self.query(
            "SELECT role, list_status, model_validation_status, approach, rank_basis, n_eligible, "
            "list_length, shortfall, banner, reason, combination_basis, intensity_basis "
            "FROM p8_top10_status ORDER BY role"
        )
        return _records(d)

    def weakest_status(self, statuses: list[dict[str, Any]] | None = None) -> str:
        rows = statuses if statuses is not None else self.list_status()
        order = [
            STATUS_ORDER.index(r["list_status"]) for r in rows if r["list_status"] in STATUS_ORDER
        ]
        return STATUS_ORDER[min(order)] if order else "INSUFFICIENT_EVIDENCE"

    def data_version(self) -> dict[str, Any]:
        d = self.query(
            "SELECT criteria_sha256, MAX(run_seq) AS run_seq FROM p8_top10_status GROUP BY 1"
        )
        out: dict[str, Any] = {"phase8_store_file": self.db.name, "submission_source": self.source}
        man = self.reports / self._fn(f"{self.source}_build_manifest.json")
        if man.exists():
            out["manifest_sha256"] = _sha(man)
        if len(d):
            out["criteria_sha256"] = str(d.iloc[0]["criteria_sha256"])
            out["run_seq"] = int(d.iloc[0]["run_seq"])
        t = self._csv("pressure_batters_top10.csv")
        if len(t):
            out["methodology_version"] = str(t.iloc[0].get("methodology_version"))
            out["data_version_hash"] = str(t.iloc[0].get("data_version_hash"))
            out["generated_at"] = str(t.iloc[0].get("generated_at"))
        return out

    def caveats(self, statuses: list[dict[str, Any]] | None = None) -> list[str]:
        rows = statuses if statuses is not None else self.list_status()
        out = list(BASE_CAVEATS)
        for r in rows:
            out.append(f"{r['role']}: {r['reason']}")
        return out

    # ------------------------------------------------------------------ overview and lists
    def overview(self) -> dict[str, Any]:
        st = self.list_status()
        cmp_ = self.query(
            "SELECT role, approach, sb, sb_low, sb_high, time_sb, oot, phase6_gate_passed, "
            "indicative_status, chosen, n_eligible FROM p8_method_comparison ORDER BY role, approach"
        )
        files = []
        for name in (
            "pressure_batters_top10.csv",
            "pressure_bowlers_top10.csv",
            "player_selection_explanations.md",
            "methodology_comparison.md",
            "descriptive_batter_profiles.csv",
            "descriptive_bowler_profiles.csv",
        ):
            p = self.reports / self._fn(name)
            if p.exists():
                files.append({"name": name, "bytes": p.stat().st_size, "sha256": _sha(p)})
        return {
            "status_label": self.weakest_status(st),
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "lists": st,
            "approaches_compared": _records(cmp_),
            "files": files,
            "navigation": list(NAVIGATION),
        }

    def top10(self, role: str) -> dict[str, Any]:
        r = ROLE[role]
        st = [s for s in self.list_status() if s["role"] == r]
        if not st:
            raise self._unavailable("list status")
        t = self._csv(f"pressure_{role}_top10.csv").sort_values(["rank", "player_id"])
        rows = _records(t)
        for row in rows:
            cs = row.get("component_scores")
            if isinstance(cs, str):
                try:
                    row["component_scores"] = json.loads(cs)
                except ValueError:
                    pass
        return {
            "status_label": st[0]["list_status"],
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "role": role,
            "list_status": st[0],
            "rows": rows,
        }

    # ------------------------------------------------------------------ player evidence
    def _chosen_table(self, r: str) -> str:
        d = self.query("SELECT approach_chosen FROM p8_method_selection WHERE role = ?", [r])
        ap = str(d.iloc[0]["approach_chosen"]) if len(d) else "A"
        return {"A": "p8_a_estimates", "B": "p8_b_estimates", "C": "p8_c_estimates"}.get(
            ap, "p8_a_estimates"
        )

    def _descriptive_rows(self, role: str, player_id: int) -> list[dict[str, Any]]:
        d = self._csv(f"descriptive_{ROLE[role]}_profiles.csv", self.descriptive_reports)
        return _records(d[d["player_id"] == player_id])

    def player_evidence(self, role: str, player_id: int) -> dict[str, Any]:
        r = ROLE[role]
        st = [s for s in self.list_status() if s["role"] == r]
        top = self._csv(f"pressure_{role}_top10.csv")
        sel = top[top["player_id"] == player_id]
        expl = self.query(
            "SELECT kind, rank, reason_code, detail, player_name FROM p8_explanations "
            "WHERE role = ? AND player_id = ? ORDER BY kind, reason_code",
            [r, player_id],
        )
        table = self._chosen_table(r)
        est = self.query(
            f"SELECT * FROM {table} WHERE role = ? AND player_id = ? AND scope = 'COMBINED'",
            [r, player_id],
        )
        inel = self.query(
            "SELECT * FROM p8_a_ineligible WHERE role = ? AND player_id = ?", [r, player_id]
        )
        desc = self._descriptive_rows(role, player_id)
        name = None
        for source in (
            sel.get("player_name"),
            expl.get("player_name"),
            est.get("player_name"),
            inel.get("player_name"),
        ):
            if source is not None and len(source):
                name = str(source.iloc[0])
                break
        if name is None and desc:
            name = desc[0].get("player_name")
        if len(sel):
            state = "SELECTED"
        elif len(est):
            state = "NOT_SELECTED_ELIGIBLE"
        elif len(inel):
            state = "NOT_ELIGIBLE"
        else:
            state = "NOT_IN_POOL"
        if state == "NOT_IN_POOL" and not desc:
            raise ApiError(404, "NOT_FOUND", f"player {player_id} is not in the {role} data")
        top_row = None
        if len(sel):
            top_row = _records(sel)[0]
            if isinstance(top_row.get("component_scores"), str):
                top_row["component_scores"] = json.loads(top_row["component_scores"])
        return {
            "status_label": st[0]["list_status"] if st else "EXPLORATORY",
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "role": role,
            "player_id": player_id,
            "player_name": name,
            "selection_state": state,
            "top10_row": top_row,
            "explanations": _records(expl.drop(columns=["player_name"], errors="ignore")),
            "estimate": _records(est)[0] if len(est) else None,
            "ineligibility": _records(inel)[0] if len(inel) else None,
            "descriptive": desc,
        }

    def why(self, role: str, kind: str | None, limit: int, offset: int) -> dict[str, Any]:
        r = ROLE[role]
        st = [s for s in self.list_status() if s["role"] == r]
        where, params = "WHERE role = ?", [r]
        if kind:
            where += " AND kind = ?"
            params.append(kind)
        total = int(
            self.query(f"SELECT COUNT(*) AS n FROM p8_explanations {where}", params).iloc[0]["n"]
        )
        d = self.query(
            "SELECT role, player_id, player_name, kind, rank, reason_code, detail "
            f"FROM p8_explanations {where} ORDER BY rank, player_id, reason_code LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        return {
            "status_label": st[0]["list_status"] if st else "EXPLORATORY",
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "role": role,
            "kind": kind,
            "page": {"total": total, "limit": limit, "offset": offset},
            "rows": _records(d),
        }

    # ------------------------------------------------------------------ method and validation
    def methodology(self) -> dict[str, Any]:
        st = self.list_status()
        docs = []
        for name in (
            "submission_methodology.md",
            "methodology_comparison.md",
            "pressure_methodology_research.md",
            "pressure_top10_status.md",
            "player_selection_explanations.md",
        ):
            p = self.reports / self._fn(name)
            docs.append(
                {"name": name, "available": p.exists(), "sha256": _sha(p) if p.exists() else None}
            )
        return {
            "status_label": self.weakest_status(st),
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "role_selection": _records(
                self.query(
                    "SELECT role, approach_chosen, rule_path, lower_bound_path, point_estimate_path, "
                    "paths_agree, list_status_cap, reason, rule_text FROM p8_method_selection ORDER BY role"
                )
            ),
            "approach_comparison": _records(
                self.query(
                    "SELECT role, approach, sb, sb_low, sb_high, time_sb, oot, oot_low, icc1, "
                    "between_player_variance_at_floor, mean_data_weight, phase6_gate_passed, "
                    "top10_prob_ge_0_5, n_eligible, indicative_status, explainability, chosen "
                    "FROM p8_method_comparison ORDER BY role, approach"
                )
            ),
            "pressure_definitions": _records(
                self.query(
                    'SELECT candidate, "pass", n_tests_passed, validation_signs_ok, phases_passing, '
                    'innings_coverage, reference_only, "primary", primary_basis '
                    "FROM p8_intensity_selection ORDER BY candidate"
                )
            ),
            "documents": docs,
        }

    def validation(self) -> dict[str, Any]:
        st = self.list_status()
        rel = []
        for tab, ap in (("p8_a_reliability", "A"), ("p8_b_reliability", "B")):
            d = self.query(
                f"SELECT role, intensity, metric, n_players, r, spearman_brown, sb_low, sb_high "
                f"FROM {tab} WHERE intensity = 'P4'"
            )
            d.insert(0, "approach", ap)
            rel.append(d)
        c = self.query(
            "SELECT role, metric, n_players, r, spearman_brown, sb_low, sb_high FROM p8_c_reliability"
        )
        c.insert(0, "approach", "C")
        rel.append(c)
        gates = self.query(
            "SELECT role, approach, phase6_gate_passed, share_players_weight_gt_0_5, "
            "between_player_variance_at_floor FROM p8_method_comparison ORDER BY role, approach"
        )
        sens = self.query(
            "SELECT role, approach, family, comparison, n_common, spearman, top10_overlap "
            "FROM p8_final_sensitivity ORDER BY role, approach, family, comparison"
        )
        phase6 = None
        p6 = self.reports / "phase6_definition_reliability_comparison_outcome.json"
        if p6.exists():
            phase6 = json.loads(p6.read_text(encoding="utf-8"))
        ai = None
        pa = self.reports / self._fn(f"{self.source}_ai_verification.json")
        if pa.exists():
            ai = json.loads(pa.read_text(encoding="utf-8"))
        return {
            "status_label": self.weakest_status(st),
            "caveats": self.caveats(st),
            "data_version": self.data_version(),
            "reliability": _records(pd.concat(rel, ignore_index=True)),
            "win_probability": _records(
                self.query("SELECT * EXCLUDE (criteria_sha256, run_seq) FROM p8_wp_metrics")
            ),
            "win_probability_calibration": _records(
                self.query(
                    "SELECT model, bin, n, mean_pred, mean_obs FROM p8_wp_calibration ORDER BY model, bin"
                )
            ),
            "expected_outcome_models": _records(
                self.query(
                    "SELECT role, target, kind, chosen, n_train, n_validation, gbm_rmse, const_rmse, "
                    "gbm_log_loss, const_log_loss, gain_vs_const_pct FROM p8_a_model_metrics ORDER BY role, target"
                )
            ),
            "gates": _records(gates),
            "sensitivity": _records(sens),
            "phase6": phase6,
            "ai_verification": ai,
        }

    # ------------------------------------------------------------------ descriptive profiles
    def _profiles(self, role: str) -> pd.DataFrame:
        return self._csv(f"descriptive_{ROLE[role]}_profiles.csv", self.descriptive_reports)

    def profiles(
        self, role: str, fmt: str | None, q: str | None, min_volume: int, sort_by: str, order: str,
        limit: int, offset: int,
    ) -> dict[str, Any]:  # fmt: skip
        d = self._profiles(role)
        vol = VOLUME_COL[ROLE[role]]
        if fmt:
            d = d[d["format"] == fmt]
        if q:
            d = d[d["player_name"].str.contains(q, case=False, regex=False, na=False)]
        d = d[d[vol].fillna(0) >= min_volume]
        key = {"player_name": "player_name", "player_id": "player_id", "volume": vol,
               "matches_played": "matches_played"}[sort_by]  # fmt: skip
        d = d.sort_values(
            [key, "player_id", "format"], ascending=[order == "asc", True, True], kind="mergesort"
        )
        total = len(d)
        return {
            "status_label": "DESCRIPTIVE_ONLY",
            "caveats": [
                "Descriptive counts and rates only: no score, rank or eligibility.",
                "Formats are listed separately and never pooled.",
            ],  # fmt: skip
            "data_version": {
                "descriptive_version": str(d["descriptive_version"].iloc[0]) if total else ""
            },
            "role": role,
            "page": {"total": total, "limit": limit, "offset": offset},
            "rows": _records(d.iloc[offset : offset + limit]),
        }

    def compare(self, role: str, ids: list[int], fmt: str | None) -> dict[str, Any]:
        d = self._profiles(role)
        if fmt:
            d = d[d["format"] == fmt]
        top = self._csv(f"pressure_{role}_top10.csv").set_index("player_id")
        out = []
        for pid in ids:
            rows = d[d["player_id"] == pid]
            if rows.empty:
                raise ApiError(404, "NOT_FOUND", f"player {pid} has no {role} profile")
            ev = None
            if pid in top.index:
                t = top.loc[pid]
                ev = {
                    "rank": int(t["rank"]),
                    "pressure_score": None
                    if pd.isna(t["pressure_score"])
                    else float(t["pressure_score"]),
                    "interval_low": None
                    if pd.isna(t["interval_low"])
                    else float(t["interval_low"]),
                    "interval_high": None
                    if pd.isna(t["interval_high"])
                    else float(t["interval_high"]),
                    "top10_inclusion_probability": None
                    if pd.isna(t["top10_inclusion_probability"])
                    else float(t["top10_inclusion_probability"]),
                    "list_status": str(t["list_status"]),
                }
            out.append(
                {"player_id": pid, "profiles": _records(rows), "submitted_list_evidence": ev}
            )
        st = self.list_status()
        return {
            "status_label": "DESCRIPTIVE_ONLY",
            "caveats": self.caveats(st),
            "data_version": {},
            "role": role,
            "players": out,
            "superiority_note": (
                "Metrics are shown side by side with their denominators. No claim is made that one "
                "player is the better pressure performer: the stored intervals overlap and the "
                "order is exploratory."
            ),
        }

    def radar(self, role: str, player_id: int, fmt: str) -> dict[str, Any]:
        r = ROLE[role]
        d = self._profiles(role)
        d = d[d["format"] == fmt]
        me = d[d["player_id"] == player_id]
        if me.empty:
            raise ApiError(404, "NOT_FOUND", f"player {player_id} has no {fmt} {role} profile")
        row = me.iloc[0]
        dims = []
        cohort_sizes = []
        for key, label, vcol, dcol, dlabel, hib in RADAR[r]:
            val = row.get(vcol)
            den = row.get(dcol)
            avail = bool(pd.notna(val) and pd.notna(den) and den >= MIN_RADAR_DENOMINATOR)
            reason = None
            pct = None
            if not avail:
                reason = (
                    "value undefined"
                    if pd.isna(val)
                    else f"fewer than {MIN_RADAR_DENOMINATOR} {dlabel}"
                )
            else:
                co = d[(d[dcol] >= MIN_RADAR_DENOMINATOR) & d[vcol].notna()][vcol].to_numpy(float)
                cohort_sizes.append(len(co))
                less, eq = float((co < val).sum()), float((co == val).sum())
                share = (less + 0.5 * eq) / len(co)
                pct = float(100 * (share if hib else 1 - share))
            dims.append(
                {
                    "key": key, "label": label,
                    "value": None if pd.isna(val) else float(val),
                    "denominator": None if pd.isna(den) else float(den),
                    "denominator_label": dlabel, "cohort_percentile": pct,
                    "higher_is_better": hib, "available": avail, "unavailable_reason": reason,
                }
            )  # fmt: skip
        return {
            "status_label": "DESCRIPTIVE_ONLY",
            "caveats": [
                "Descriptive dimensions only. There is no composite score.",
                "A dimension with fewer than "
                f"{MIN_RADAR_DENOMINATOR} observations is shown as unavailable, never as zero.",
                "Percentiles are relative to the cohort stated in normalisation_cohort.",
            ],
            "data_version": {},
            "role": role,
            "player_id": player_id,
            "player_name": str(row["player_name"]),
            "format": fmt,
            "normalisation_cohort": (
                f"all {fmt} {r} profiles with at least {MIN_RADAR_DENOMINATOR} observations in the "
                "dimension (per-dimension cohort; percentile oriented so higher is better)"
            ),
            "cohort_size": int(np.max(cohort_sizes)) if cohort_sizes else 0,
            "composite": None,
            "dimensions": dims,
        }

    # ------------------------------------------------------------------ experimental AI
    def experimental_ai(self, role: str) -> dict[str, Any]:
        name = f"experimental_ai_top10_{role}.csv"
        p = self.reports / self._fn(name)
        if not p.exists():
            return {
                "status_label": "EXPERIMENTAL_NOT_VALIDATED", "caveats": list(BASE_CAVEATS),
                "data_version": {}, "role": role, "state": "INSUFFICIENT_DATA",
                "model_note": f"{name} not found; run scripts/phase9_ai_verify.py",
                "rows": [], "artefacts": [],
            }  # fmt: skip
        d = self._csv(name)
        meta = self.reports / self._fn(f"{self.source}_ai_verification.json")
        arte = []
        if meta.exists():
            arte = json.loads(meta.read_text(encoding="utf-8")).get("inventory", [])
        return {
            "status_label": "EXPERIMENTAL_NOT_VALIDATED",
            "caveats": [
                *BASE_CAVEATS,
                "Single-year out-of-sample residuals from a gradient-boosting expectation model; "
                "technical success of the model is not evidence of a reliable player order.",
            ],
            "data_version": {"file_sha256": _sha(p)},
            "role": role,
            "state": "AVAILABLE" if len(d) else "INSUFFICIENT_DATA",
            "model_note": "Not the submitted ranking. Not validated. Separate from /submission/top10.",
            "rows": _records(d),
            "artefacts": arte,
        }
