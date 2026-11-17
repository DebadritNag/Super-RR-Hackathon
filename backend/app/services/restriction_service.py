"""Metric-level application of the data-quality restriction register (Phase 3 prep, Stage 7).

Reads `config/data_quality_restrictions_v1.json` through `app.validation.restrictions`. A rule
never deletes a record and never excludes a match globally: it yields a row mask for a named
metric, a sensitivity variant, a field guard, or a join guard. The official tables are only read.

Frame columns used are those of the exploratory pre-delivery state (`exp_pre_delivery_state`),
plus optional `aux_*` columns added by `attach_aux` from the official database (read-only).
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from app.validation.restrictions import load_restrictions, restrictions_for_metric

EXCLUDE = "EXCLUDE_ROWS_FROM_METRIC"
SENSITIVITY_EFFECTS = ("SENSITIVITY_EXCLUDE", "REPORT_WITH_SENSITIVITY")
NAME_COLUMNS = {"player_name", "name", "name_variants", "batter_name", "bowler_name"}
STRIKER_METRICS = {
    "batter_balls_faced", "batter_runs_per_ball", "batter_strike_rate", "batter_dismissal_rate",
    "batter_pressure_sample",
}  # fmt: skip
BOWLER_METRICS = {"bowler_legal_balls", "bowler_economy", "bowler_wicket_rate",
                  "bowler_pressure_sample"}  # fmt: skip
# Fields that a DO_NOT_INTERPRET_FIELD / DO_NOT_USE_AS_LABEL rule bars from its metrics
GUARDED_FIELDS = {
    "RULE_EXTRAS_SECONDARY": {"extras_secondary_runs", "out_extras_secondary_runs"},
    "RULE_UTC_SUFFIX": {"delivery_time_raw", "delivery_ts"},
    "RULE_MIDNIGHT_TIMES": {"delivery_time_is_midnight", "delivery_ts"},
    "RULE_MOM_SENTINEL": {"man_of_the_match"},
}
SQUAD_METRICS_GUARD = {"team_composition_features", "squad_membership_features"}


class RestrictionViolation(RuntimeError):
    """A restricted field, join or inference was attempted."""


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        raise RestrictionViolation(f"frame lacks column {name!r} needed by the restriction rule")
    return df[name]


def _b(s: pd.Series) -> pd.Series:
    return s.fillna(False).astype(bool)


# ------------------------------------------------------------------ row predicates (frame level)
def _inn34(df):
    return df["innings_number"].isin([3, 4])


def _extras(kind: str) -> Callable[[pd.DataFrame], pd.Series]:
    return lambda df: _col(df, "out_extras_type").eq(kind)


def _secondary(df):
    return _col(df, "out_extras_secondary_runs").fillna(0).gt(0)


def _dismissed_no_flag(df):
    return _col(df, "out_dismissed_player_id").notna() & ~_b(_col(df, "out_is_wicket"))


def _wicket_no_dismissed(df):
    return _b(_col(df, "out_is_wicket")) & _col(df, "out_dismissed_player_id").isna()


def _cricsheet_totals(df):
    return _b(_col(df, "dq_cricsheet_total_disagreement_innings"))


def _dls(df):
    return _b(_col(df, "dls_match_flag"))


def _aux(name: str) -> Callable[[pd.DataFrame], pd.Series]:
    return lambda df: _b(_col(df, name))


# kind: FRAME (callable on the frame), OFFICIAL_SQL (scalar count), DOCUMENT_ONLY (note only)
RULE_IMPLEMENTATIONS: dict[str, dict[str, Any]] = {
    "RULE_INNINGS_3_4": {"kind": "FRAME", "fn": _inn34, "code": "innings_number IN (3, 4)"},
    "RULE_EXTRAS_OTHER": {"kind": "FRAME", "fn": _extras("other"), "code": "extras_type = other"},
    "RULE_EXTRAS_PENALTY": {"kind": "FRAME", "fn": _extras("Penalty"),
                            "code": "extras_type = Penalty"},  # fmt: skip
    "RULE_EXTRAS_SECONDARY": {"kind": "FRAME", "fn": _secondary, "code": "secondary runs > 0"},
    "RULE_XI_DUPLICATES": {"kind": "OFFICIAL_SQL",
                           "sql": "SELECT count(*) FROM match_squads WHERE duplicate_key_flag"},
    "RULE_NO_XI_MATCHES": {"kind": "FRAME", "fn": _aux("aux_no_xi"), "code": "match has no XI rows"},
    "RULE_NO_MAPPING_ROW": {"kind": "OFFICIAL_SQL",
                            "sql": "SELECT count(*) FROM match_squads WHERE NOT mapping_row_exists"},
    "RULE_STRIKER_NOT_IN_SQUAD": {"kind": "FRAME", "fn": _aux("aux_striker_not_in_squad"),
                                  "code": "striker absent from squad"},  # fmt: skip
    "RULE_BOWLER_NOT_IN_SQUAD": {"kind": "FRAME", "fn": _aux("aux_bowler_not_in_squad"),
                                 "code": "bowler absent from squad"},  # fmt: skip
    "RULE_DISMISSED_NO_FLAG": {"kind": "FRAME", "fn": _dismissed_no_flag,
                               "code": "dismissed_player_id set, is_wicket false"},  # fmt: skip
    "RULE_WICKET_NO_DISMISSED": {"kind": "FRAME", "fn": _wicket_no_dismissed,
                                 "code": "is_wicket true, dismissed_player_id null"},  # fmt: skip
    "RULE_MOM_SENTINEL": {"kind": "OFFICIAL_SQL",
                          "sql": "SELECT count(*) FROM matches WHERE man_of_the_match = 0"},
    "RULE_UTC_SUFFIX": {"kind": "OFFICIAL_SQL",
                        "sql": "SELECT count(*) FROM deliveries WHERE delivery_time_raw LIKE '%UTC%'"},
    "RULE_MIDNIGHT_TIMES": {"kind": "OFFICIAL_SQL",
                            "sql": "SELECT count(*) FROM deliveries WHERE delivery_time_is_midnight"},
    "RULE_DUPLICATE_NAMES": {"kind": "OFFICIAL_SQL",
                             "sql": "SELECT count(*) FROM players WHERE shares_name_with_other_id"},
    "RULE_CRICSHEET_TOTALS": {"kind": "FRAME", "fn": _cricsheet_totals,
                              "code": "ten disagreeing innings"},  # fmt: skip
    "RULE_UNLINKABLE_MATCHES": {"kind": "DOCUMENT_ONLY", "note": "no Cricsheet counterpart"},
    "RULE_NO_RESULT_MATCHES": {"kind": "FRAME", "fn": _aux("aux_no_result"),
                               "code": "NO_RESULT/ABANDONED with deliveries"},  # fmt: skip
    "RULE_DLS_TARGETS": {"kind": "FRAME", "fn": _dls, "code": "revised target or overs present"},
    "RULE_XI_COUNT": {"kind": "OFFICIAL_SQL",
                      "sql": "SELECT count(*) FROM (SELECT match_id, team_id FROM match_squads "
                             "WHERE is_played GROUP BY 1, 2 HAVING count(*) <> 11)"},  # fmt: skip
    "RULE_FIRST_INNINGS_TEAM": {"kind": "DOCUMENT_ONLY", "note": "field not used as a feature"},
    "RULE_INFO_NO_DELIVERY_MATCHES": {"kind": "OFFICIAL_SQL",
                                      "sql": "SELECT count(*) FROM matches WHERE NOT has_deliveries"},
    "RULE_INFO_RESULT_STATUS": {"kind": "OFFICIAL_SQL",
                                "sql": "SELECT count(*) FROM matches "
                                       "WHERE result_status <> 'COMPLETED'"},  # fmt: skip
    "RULE_INFO_COMP_TYPE": {"kind": "OFFICIAL_SQL",
                            "sql": "SELECT count(*) FROM matches WHERE competition_type = 'OTHER_T20'"},
    "RULE_INFO_IPL_FORMAT": {"kind": "OFFICIAL_SQL",
                             "sql": "SELECT count(*) FROM competitions WHERE competition_type = 'IPL' "
                                    "AND match_format <> 'T20'"},  # fmt: skip
    "RULE_INFO_EXTRAS1_COMPARISON": {"kind": "OFFICIAL_SQL",
                                     "sql": "SELECT count(*) FROM ball_by_ball_comparison_detail"},
}  # fmt: skip


def metric_base(metric: str, df: pd.DataFrame) -> pd.Series:
    """Rows a metric actually draws on (its denominator), before any restriction."""
    if metric in ("batter_balls_faced", "batter_runs_per_ball", "batter_strike_rate"):
        # BATTER_SQL definition: wides and Penalty are not balls faced (source columns only)
        return ~_col(df, "out_extras_type").isin(["wide", "Penalty"])
    if metric in ("bowler_legal_balls", "bowler_economy", "bowler_wicket_rate"):
        return pd.Series(True, index=df.index)
    return pd.Series(True, index=df.index)


def extras_category(df: pd.DataFrame) -> pd.Series:
    """Extras category per row. 'other', 'Penalty' and runs with type None stay separate."""
    t = _col(df, "out_extras_type").astype("object").where(lambda s: s.notna(), "None")
    prim = _col(df, "out_extras_primary_runs").fillna(0)
    sec = _col(df, "out_extras_secondary_runs").fillna(0)
    none_with_runs = t.eq("None") & ((prim + sec) > 0)
    return t.where(~none_with_runs, "None_with_runs")


class RestrictionApplier:
    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg if cfg is not None else load_restrictions()
        self.rules = {r["rule_id"]: r for r in self.cfg["restrictions"]}
        missing = sorted(set(self.rules) - set(RULE_IMPLEMENTATIONS))
        extra = sorted(set(RULE_IMPLEMENTATIONS) - set(self.rules))
        if missing or extra:
            raise RestrictionViolation(f"rules without implementation {missing}; unknown {extra}")

    # ---- masks
    def rule_mask(self, rule_id: str, df: pd.DataFrame) -> pd.Series:
        impl = RULE_IMPLEMENTATIONS[rule_id]
        if impl["kind"] != "FRAME":
            raise RestrictionViolation(f"{rule_id} has no row-level predicate ({impl['kind']})")
        return _b(impl["fn"](df)).reindex(df.index, fill_value=False)

    def mask_for(self, metric: str, df: pd.DataFrame) -> pd.Series:
        """True for rows that must NOT enter `metric` (union of EXCLUDE_ROWS_FROM_METRIC rules).
        A metric with no EXCLUDE rule gets an all-False mask. Sensitivity rules never enter."""
        out = pd.Series(False, index=df.index)
        for r in restrictions_for_metric(metric, self.cfg):
            if r["effect"] == EXCLUDE and RULE_IMPLEMENTATIONS[r["rule_id"]]["kind"] == "FRAME":
                out |= self.rule_mask(r["rule_id"], df)
        return out

    def apply(self, metric: str, df: pd.DataFrame) -> pd.DataFrame:
        """Rows allowed into `metric`; the input frame is not modified."""
        return df.loc[~self.mask_for(metric, df)]

    # ---- variants
    def variants_for(self, metric: str) -> list[dict[str, Any]]:
        out = [{"variant": "primary", "rule_id": None, "kind": "primary",
                "description": "EXCLUDE_ROWS_FROM_METRIC rules only"}]  # fmt: skip
        for r in restrictions_for_metric(metric, self.cfg):
            rid = r["rule_id"]
            if r["effect"] in SENSITIVITY_EFFECTS:
                out.append({"variant": f"sensitivity:{rid}", "rule_id": rid,
                            "kind": r["effect"], "description": self._variant_text(rid)})  # fmt: skip
            elif rid == "RULE_DLS_TARGETS":
                out.append({"variant": f"diagnostic:{rid}", "rule_id": rid, "kind": "DIAGNOSTIC",
                            "description": self._variant_text(rid)})  # fmt: skip
        return out

    @staticmethod
    def _variant_text(rule_id: str) -> str:
        return {
            "RULE_EXTRAS_OTHER": "drop rows with extras_type = other (primary keeps them)",
            "RULE_DISMISSED_NO_FLAG": "count rows with dismissed player but is_wicket false as "
            "wickets (primary: is_wicket is authoritative)",  # fmt: skip
            "RULE_CRICSHEET_TOTALS": "drop the ten innings whose total disagrees with Cricsheet",
            "RULE_DLS_TARGETS": "revised versus naive (innings-1 total + 1) target, diagnostic",
        }.get(rule_id, rule_id)

    def variant_drop_mask(self, variant: dict[str, Any], df: pd.DataFrame) -> pd.Series:
        """Extra rows to drop for a sensitivity variant (on top of the primary mask)."""
        rid = variant["rule_id"]
        if rid in ("RULE_EXTRAS_OTHER", "RULE_CRICSHEET_TOTALS"):
            return self.rule_mask(rid, df)
        return pd.Series(False, index=df.index)

    @staticmethod
    def wicket_label(df: pd.DataFrame, include_dismissed_no_flag: bool = False) -> pd.Series:
        """Dismissal label. Primary: is_wicket. Rows with is_wicket true and no dismissed player
        are removed by RULE_WICKET_NO_DISMISSED for dismissal metrics (see mask_for)."""
        w = _b(_col(df, "out_is_wicket"))
        if include_dismissed_no_flag:
            w = w | _dismissed_no_flag(df)
        return w

    # ---- guards
    def guard_field(self, metric: str, field: str) -> None:
        for r in restrictions_for_metric(metric, self.cfg):
            if r["effect"] in ("DO_NOT_INTERPRET_FIELD", "DO_NOT_USE_AS_LABEL"):
                if field in GUARDED_FIELDS.get(r["rule_id"], set()):
                    raise RestrictionViolation(f"{r['rule_id']}: {field} may not feed {metric}")

    def guard_squad_inference(self, metric: str) -> None:
        for r in restrictions_for_metric(metric, self.cfg):
            if r["effect"] == "DO_NOT_INFER_FROM_SQUAD":
                raise RestrictionViolation(f"{r['rule_id']}: {metric} may not infer from squads")

    @staticmethod
    def assert_no_name_join(*columns: str) -> None:
        """RULE_DUPLICATE_NAMES: identities join on player_id only."""
        bad = sorted({c for c in columns if c.lower() in NAME_COLUMNS})
        if bad:
            raise RestrictionViolation(f"RULE_DUPLICATE_NAMES: join on name column(s) {bad}")

    @staticmethod
    def require_revised_state(df: pd.DataFrame) -> pd.Series:
        """RULE_DLS_TARGETS: rows whose revised state cannot be reconstructed are not primary."""
        return _b(_col(df, "dls_match_flag")) & _b(_col(df, "dls_exclude_primary"))

    # ---- squads
    @staticmethod
    def dedup_squad(squad: pd.DataFrame) -> pd.DataFrame:
        """One row per (match_id, team_id, player_id): duplicate squad records never multiply."""
        return squad.drop_duplicates(["match_id", "team_id", "player_id"]).reset_index(drop=True)

    def safe_squad_join(self, df: pd.DataFrame, squad: pd.DataFrame, left_on: str) -> pd.DataFrame:
        sq = self.dedup_squad(squad)[["match_id", "player_id"]].drop_duplicates()
        sq = sq.assign(in_squad=True)
        out = df.merge(sq, left_on=["match_id", left_on], right_on=["match_id", "player_id"],
                       how="left", suffixes=("", "_sq"))  # fmt: skip
        if len(out) != len(df):
            raise RestrictionViolation("RULE_XI_DUPLICATES: squad join multiplied rows")
        return out

    # ---- ledger
    def ledger(self, df: pd.DataFrame, extra_counts: dict[str, int] | None = None) -> pd.DataFrame:
        rows = []
        for rid, r in self.rules.items():
            impl = RULE_IMPLEMENTATIONS[rid]
            flagged = self.rule_mask(rid, df) if impl["kind"] == "FRAME" else None
            for m in r["applies_to_metrics"]:
                rec = {"rule_id": rid, "metric": m, "effect": r["effect"], "kind": impl["kind"]}
                if flagged is not None:
                    inscope = flagged & metric_base(m, df)
                    pid = pd.concat([df.loc[inscope, c] for c in self._player_cols(m)]).dropna()
                    rec |= {
                        "rows_flagged": int(flagged.sum()),
                        "rows_in_metric_scope": int(inscope.sum()),
                        "rows_excluded": int(inscope.sum()) if r["effect"] == EXCLUDE else 0,
                        "matches_affected": int(df.loc[inscope, "match_id"].nunique()),
                        "players_affected": int(pid.nunique()),
                        "reason_codes": sorted(
                            map(str, df.loc[inscope, "exclusion_reason_code"].dropna().unique())
                        )
                        if "exclusion_reason_code" in df.columns
                        else [],
                    }
                else:
                    rec |= {"rows_flagged": None, "rows_in_metric_scope": None,
                            "rows_excluded": 0, "matches_affected": None,
                            "players_affected": None, "reason_codes": [],
                            "official_count": (extra_counts or {}).get(rid)}  # fmt: skip
                rows.append(rec)
        return pd.DataFrame(rows)

    @staticmethod
    def _player_cols(metric: str) -> list[str]:
        if metric in STRIKER_METRICS:
            return ["striker_id"]
        if metric in BOWLER_METRICS:
            return ["bowler_id"]
        return ["striker_id", "bowler_id"]


def attach_aux(df: pd.DataFrame, con) -> pd.DataFrame:
    """Add aux_* flags from the official DB (read-only connection). No row is added or removed."""
    out = df.copy()
    nr = con.execute(
        "SELECT match_id FROM matches WHERE result_status IN ('NO_RESULT','ABANDONED') "
        "AND has_deliveries"
    ).df()["match_id"]
    out["aux_no_result"] = out["match_id"].isin(nr)
    squad = con.execute("SELECT DISTINCT match_id, player_id FROM match_squads").df()
    out["aux_no_xi"] = ~out["match_id"].isin(squad["match_id"].unique())
    keys = set(map(tuple, squad[["match_id", "player_id"]].to_numpy().tolist()))
    for col, name in (("striker_id", "aux_striker_not_in_squad"),
                      ("bowler_id", "aux_bowler_not_in_squad")):  # fmt: skip
        pairs = list(zip(out["match_id"].tolist(), out[col].tolist()))
        has_squad = ~out["aux_no_xi"].to_numpy()
        out[name] = np.array([p not in keys for p in pairs]) & has_squad
    return out
