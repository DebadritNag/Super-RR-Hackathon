"""Stage 7: apply the data-quality restriction register at metric and feature level (EXPLORATORY).

Reads the exploratory pre-delivery state and the official DuckDB (read-only). Writes
data/reports/phase3_data_quality_application_report.md/.json and
data/reports/pressure_feature_dictionary.json. No record is deleted, no match is excluded
globally, no score is validated. Exit 1 if official data changed or an invariant fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics import feature_registry as fr  # noqa: E402
from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import (  # noqa: E402
    fmt,
    md_table,
    provenance,
    write_json_deterministic,
    write_text,
)
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402
from app.services import restriction_service as rs  # noqa: E402
from app.validation.restrictions import RESTRICTIONS_PATH, load_restrictions  # noqa: E402

STATUS = {"status": "EXPLORATORY_NOT_VALIDATED", "official_ranking": False,
          "not_for_publication": True}  # fmt: skip
COLS = """match_id, innings_number, innings_ball_num, competition_type, striker_id, bowler_id,
 chase_flag, wickets_remaining, innings_phase, rrr, target, team_runs_before, team_wickets_before,
 team_wickets_alt_before, req_nonpositive_flag, target_basis_unverified, dls_flag, dls_match_flag,
 dls_exclude_primary, state_wicket_flag_disagreement, regulation_pressure_eligible,
 format_out_of_scope, dq_cricsheet_total_disagreement_innings, restricted_innings_flag,
 exclusion_reason_code, exclusion_rule_id, out_batter_runs, out_is_wicket, out_dismissal_type,
 out_dismissed_player_id, out_extras_type, out_extras_primary_runs, out_extras_secondary_runs,
 out_runs_row, den_counts_as_ball_faced, den_bowler_counts_row, den_bowler_charged_runs,
 den_bowler_credited_wicket, den_extras_category_known, den_extras_label_unverified,
 den_extras_runs_with_none_type"""
MIN_BALLS = {("batter", "IPL"): 24, ("batter", "T20I"): 24, ("bowler", "IPL"): 32,
             ("bowler", "T20I"): 36}  # fmt: skip


def load_frame(store: Path) -> pd.DataFrame:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return con.execute(
            f"SELECT {COLS} FROM exp_pre_delivery_state "
            "ORDER BY match_id, innings_number, innings_ball_num"
        ).df()
    finally:
        con.close()


def chase_pressure_population(df: pd.DataFrame, applier: rs.RestrictionApplier, metric: str):
    """Exploratory pressure sample: valid chase rows in scope, minus rows the register excludes."""
    d = pf.add_populations(df)
    return d["chase_pop"] & ~applier.mask_for(metric, d)


def proxy_scores(df: pd.DataFrame, keep: pd.Series, role: str) -> pd.DataFrame:
    """Raw (unshrunk) residual per ball against a comp x phase x wickets cell mean computed on
    the same sample. EXPLORATORY PROXY, not a pressure score and not the Stage 4 baseline."""
    if role == "batter":
        s = df[keep & df["den_counts_as_ball_faced"].fillna(False).astype(bool)].copy()
        s["y"], pid = s["out_batter_runs"].astype(float), "striker_id"
    else:
        s = df[keep & df["den_bowler_counts_row"].fillna(False).astype(bool)].copy()
        s["y"], pid = s["den_bowler_charged_runs"].astype(float), "bowler_id"
    cell = ["competition_type", "innings_phase", "wickets_remaining"]
    s["resid"] = s["y"] - s.groupby(cell)["y"].transform("mean")
    g = s.groupby(["competition_type", pid]).agg(
        balls=("y", "size"), matches=("match_id", "nunique"), resid_per_ball=("resid", "mean")
    )
    g.index.names = ["competition_type", "player_id"]
    return g.reset_index()


def compare_variants(df, base_keep, var_keep, role) -> dict:
    a, b = proxy_scores(df, base_keep, role), proxy_scores(df, var_keep, role)
    out = {}
    for comp in ("IPL", "T20I"):
        t = MIN_BALLS[(role, comp)]
        ea = a[(a.competition_type == comp) & (a.balls >= t)]
        eb = b[(b.competition_type == comp) & (b.balls >= t)]
        j = ea.merge(eb, on="player_id", suffixes=("_p", "_v"))
        rho = None
        if (
            len(j) >= 3
            and j["resid_per_ball_p"].nunique() > 1
            and j["resid_per_ball_v"].nunique() > 1
        ):
            rho = float(j["resid_per_ball_p"].corr(j["resid_per_ball_v"], method="spearman"))
        out[comp] = {
            "min_balls": t,
            "pressure_rows_primary": int(a.loc[a.competition_type == comp, "balls"].sum()),
            "pressure_rows_variant": int(b.loc[b.competition_type == comp, "balls"].sum()),
            "eligible_primary": int(len(ea)),
            "eligible_variant": int(len(eb)),
            "eligible_in_both": int(len(j)),
            "spearman_common": rho,
            "max_abs_change_resid_per_ball": float(
                (j["resid_per_ball_p"] - j["resid_per_ball_v"]).abs().max()
            )
            if len(j)
            else None,
        }
    return out


def official_counts(con) -> dict[str, int]:
    out = {}
    for rid, impl in rs.RULE_IMPLEMENTATIONS.items():
        if impl["kind"] == "OFFICIAL_SQL":
            out[rid] = int(con.execute(impl["sql"]).fetchone()[0])
    return out


def run_checks(df, d, applier, con, cfg) -> dict:
    res: dict = {}
    # Rule: unverified innings 3/4
    r34 = df[df.innings_number.isin([3, 4])]
    reg_pressure = pf.add_populations(df)
    in_any_pop = reg_pressure.loc[r34.index, ["base_pop", "chase_pop", "inn1_pop"]].any(axis=None)
    res["innings_3_4"] = {
        "rows": int(len(r34)),
        "matches": int(r34.match_id.nunique()),
        "rows_by_innings": {str(k): int(v) for k, v in r34.innings_number.value_counts().items()},
        "reason_codes": {k: int(v) for k, v in r34.exclusion_reason_code.value_counts().items()},
        "matches_by_reason": {
            k: sorted(map(int, g.match_id.unique()))
            for k, g in r34.groupby("exclusion_reason_code")
        },
        "rows_excluded_by_mask_batter_pressure_sample": int(
            applier.mask_for("batter_pressure_sample", df).sum()
        ),
        "rows_excluded_by_mask_bowler_pressure_sample": int(
            applier.mask_for("bowler_pressure_sample", df).sum()
        ),
        "source_rows_preserved_in_official_db": int(
            con.execute("SELECT count(*) FROM deliveries WHERE innings_number IN (3,4)").fetchone()[
                0
            ]
        ),
        "any_row_in_a_pressure_population": bool(in_any_pop),
    }
    # Rule: unknown extras never silently zero
    cat = rs.extras_category(df)
    res["extras"] = {
        "category_counts": {k: int(v) for k, v in cat.value_counts().items()},
        "other_rows_mapped_to_none": int(((df.out_extras_type == "other") & cat.eq("None")).sum()),
        "penalty_rows_mapped_to_none": int(
            ((df.out_extras_type == "Penalty") & cat.eq("None")).sum()
        ),
        "none_type_with_runs_rows": int(cat.eq("None_with_runs").sum()),
        "unverified_label_rows": int(df.den_extras_label_unverified.fillna(False).sum()),
        "penalty_rows_excluded_by_metric_mask": {
            m: int((applier.mask_for(m, df) & df.out_extras_type.eq("Penalty")).sum())
            for m in ("batter_balls_faced", "bowler_legal_balls")
        },
        "secondary_runs_rows": int(applier.rule_mask("RULE_EXTRAS_SECONDARY", df).sum()),
        "secondary_guard_blocks_economy": _raises(
            lambda: applier.guard_field("bowler_economy", "extras_secondary_runs")
        ),
    }
    # Rule: wicket-flag disagreements (dismissal metrics only)
    wf = applier.rule_mask("RULE_DISMISSED_NO_FLAG", df)
    wn = applier.rule_mask("RULE_WICKET_NO_DISMISSED", df)
    reg = df.innings_number.isin([1, 2])
    res["wicket_flags"] = {
        "dismissed_without_wicket_flag_rows": int(wf.sum()),
        "wicket_flag_without_dismissed_rows": int(wn.sum()),
        "rows_in_regulation": {
            "dismissed_no_flag": int((wf & reg).sum()),
            "wicket_no_dismissed": int((wn & reg).sum()),
        },  # fmt: skip
        "state_rows_where_wicket_count_variants_differ": int(
            (df.team_wickets_before != df.team_wickets_alt_before).sum()
        ),
        "state_rows_with_flag_disagreement_in_earlier_rows": int(
            df.state_wicket_flag_disagreement.fillna(False).sum()
        ),
        "dismissal_metric_rows_excluded_primary": {
            m: int(applier.mask_for(m, df).sum())
            for m in ("wicket_event_label", "batter_dismissal_rate", "bowler_wicket_rate")
        },
        "state_features_rows_dropped": 0,
        "handling": "state features keep is_wicket and report the alt count as a variant; only "
        "dismissal metrics apply the masks",  # fmt: skip
    }
    # Rule: DLS needs reconstructed revised state
    dls = df[df.dls_match_flag.fillna(False).astype(bool)]
    ch = pf.add_populations(df)
    res["dls"] = {
        "dls_match_rows": int(len(dls)),
        "dls_matches": int(dls.match_id.nunique()),
        "dls_flag_rows": int(df.dls_flag.fillna(False).sum()),
        "rows_without_reconstructable_revised_state": int(applier.require_revised_state(df).sum()),
        "matches_without_reconstructable_revised_state": int(
            df[applier.require_revised_state(df)].match_id.nunique()
        ),
        "dls_rows_in_primary_chase_population": int(
            (ch.chase_pop & df.dls_match_flag.fillna(False)).sum()
        ),
        "dls_exclude_primary_rows_in_primary_chase_population": int(
            (ch.chase_pop & df.dls_exclude_primary.fillna(False)).sum()
        ),
    }
    # Rule: names never merge identities
    pl = con.execute("SELECT player_id, player_name FROM players").df()
    shared = con.execute("SELECT count(*) FROM players WHERE shares_name_with_other_id").fetchone()[
        0
    ]
    names = pl.groupby("player_name").player_id.nunique()
    dup_names = names[names > 1]
    ids = pd.Series(pd.concat([df.striker_id, df.bowler_id]).dropna().unique(), name="player_id")
    by_id = ids.to_frame().merge(pl, on="player_id", how="left")
    by_name = by_id.merge(pl[["player_id", "player_name"]], on="player_name",
                          suffixes=("", "_other"))  # fmt: skip
    res["duplicate_names"] = {
        "players_sharing_a_name": int(shared),
        "distinct_shared_names": int(len(dup_names)),
        "ids_in_deliveries": int(len(ids)),
        "rows_if_joined_on_id": int(len(by_id)),
        "rows_if_naively_joined_on_name": int(len(by_name)),
        "ids_that_would_merge_by_name": int(
            by_name[by_name.player_id != by_name.player_id_other].player_id.nunique()
        ),
        "name_join_guard_raises": _raises(lambda: applier.assert_no_name_join("player_name")),
        "pipeline_join_key": "player_id only",
    }
    # Rule: duplicate squad records must not multiply statistics
    squad = con.execute("SELECT * FROM match_squads").df()
    pop = chase_pressure_population(df, applier, "batter_pressure_sample")
    sample = df[pop]
    safe = applier.safe_squad_join(sample, squad, "striker_id")
    naive = sample.merge(squad[["match_id", "player_id"]], left_on=["match_id", "striker_id"],
                         right_on=["match_id", "player_id"], how="left")  # fmt: skip
    cnt0 = sample.groupby("striker_id").size()
    cnt1 = safe.groupby("striker_id").size()
    dedup_n = len(applier.dedup_squad(squad))
    res["xi_duplicates"] = {
        "squad_rows": int(len(squad)),
        "duplicate_flag_rows": int(squad.duplicate_key_flag.fillna(False).sum()),
        "squad_rows_after_dedup": int(dedup_n),
        "pressure_sample_rows": int(len(sample)),
        "rows_with_safe_squad_join": int(len(safe)),
        "rows_with_naive_squad_join": int(len(naive)),
        "naive_join_extra_rows": int(len(naive) - len(sample)),
        "per_player_counts_identical_without_and_with_safe_join": bool(cnt0.equals(cnt1)),
        "matches_without_xi_rows": int(
            len(set(df.match_id.unique()) - set(squad.match_id.unique()))
        ),
        "pipeline_uses_match_squads": False,
        "squad_inference_guard_raises": _raises(
            lambda: applier.guard_squad_inference("squad_membership_features")
        ),
    }
    return res


def _raises(fn) -> bool:
    try:
        fn()
    except rs.RestrictionViolation:
        return True
    return False


def sensitivity(df, applier) -> dict:
    out = {}
    for role, metric in (
        ("batter", "batter_pressure_sample"),
        ("bowler", "bowler_pressure_sample"),
    ):
        base = chase_pressure_population(df, applier, metric)
        v = {}
        # RULE_EXTRAS_OTHER with / without
        other = applier.rule_mask("RULE_EXTRAS_OTHER", df)
        v["RULE_EXTRAS_OTHER (drop other rows)"] = {
            "rows_dropped": int((base & other).sum()),
            "metrics": compare_variants(df, base, base & ~other, role),
        }
        # RULE_CRICSHEET_TOTALS: ten innings
        cs = applier.rule_mask("RULE_CRICSHEET_TOTALS", df)
        v["RULE_CRICSHEET_TOTALS (drop ten innings)"] = {
            "rows_dropped": int((base & cs).sum()),
            "innings_dropped_in_sample": int(
                df[base & cs][["match_id", "innings_number"]].drop_duplicates().shape[0]
            ),
            "metrics": compare_variants(df, base, base & ~cs, role),
        }
        # RULE_DLS_TARGETS: DLS rows in the (already primary-excluded) population: show what would
        # change if DLS rows were forced in using the naive target
        dls = df.dls_match_flag.fillna(False).astype(bool)
        # base_pop already excludes dls_exclude_primary rows, so use rows before that filter
        loose2 = (
            df.regulation_pressure_eligible.fillna(False).astype(bool)
            & ~df.format_out_of_scope.fillna(False).astype(bool)
            & df.innings_number.isin([1, 2])
            & df.competition_type.isin(pf.SCOPE)
            & df.chase_flag.fillna(False).astype(bool)
            & df.rrr.notna()
            & ~df.req_nonpositive_flag.fillna(False).astype(bool)
            & ~df.target_basis_unverified.fillna(False).astype(bool)
            & ~applier.mask_for(metric, df)
        )
        v["RULE_DLS_TARGETS (force DLS rows into sample, diagnostic only)"] = {
            "dls_rows_added": int((loose2 & dls & ~base).sum()),
            "dls_rows_in_primary": int((base & dls).sum()),
            "metrics": compare_variants(df, base, base | (loose2 & dls), role),
            "note": "diagnostic: the revised state is not reconstructable for these rows",
        }
        out[role] = v
    # Dismissal metric: with / without the 12 flagged rows (regulation rows, per striker)
    reg = df[df.innings_number.isin([1, 2])]
    prim = reg[~applier.mask_for("batter_dismissal_rate", reg)]
    w0 = applier.wicket_label(prim) & (prim.out_dismissed_player_id == prim.striker_id)
    w1 = applier.wicket_label(prim, True) & (prim.out_dismissed_player_id == prim.striker_id)
    d0 = prim[w0].groupby("striker_id").size()
    d1 = prim[w1].groupby("striker_id").size()
    diff = d1.reindex(d1.index.union(d0.index), fill_value=0) - d0.reindex(
        d1.index.union(d0.index), fill_value=0
    )
    out["dismissal_metric_wicket_flag_variants"] = {
        "dismissals_primary": int(w0.sum()),
        "dismissals_with_dismissed_no_flag": int(w1.sum()),
        "players_with_changed_dismissal_count": int((diff != 0).sum()),
        "rows_excluded_wicket_no_dismissed": int(
            applier.rule_mask("RULE_WICKET_NO_DISMISSED", reg).sum()
        ),
    }
    return out


def feature_dictionary(cfg) -> dict:
    feats = fr.build_dictionary(cfg)
    return {
        **STATUS,
        "version": "pressure_feature_dictionary_v1",
        "validated_features": [],
        "note": "Every feature is EXPLORATORY_NOT_VALIDATED. Availability: PRE_DELIVERY means "
        "computable from earlier rows only; PARTIAL_PRE_DELIVERY uses data that was not "
        "all known at the delivery (descriptive only); OUTCOME_OF_DELIVERY and the "
        "denominator flags depend on delivery k itself; POST_INNINGS and POST_MATCH are "
        "forbidden as inputs.",  # fmt: skip
        "restriction_register": RESTRICTIONS_PATH.name,
        "availability_counts": {
            a: sum(1 for f in feats if f["availability"] == a) for a in fr.AVAILABILITY
        },
        "feature_count": len(feats),
        "features": feats,
    }


def render(res, ledger, sens, counts, cfg, fd) -> str:
    L = ["# Phase 3 data-quality application report", ""]
    L += [
        "## 1. Status",
        "",
        "Every figure below is an EXPLORATORY PROXY calculation from DuckDB. No pressure score "
        "is validated, no official ranking is produced, no ML model is trained, 70:30 stays a "
        "provisional default. The restriction register (`data_quality_restrictions_v1.json`, "
        f"{len(cfg['restrictions'])} rules, `global_exclusion: false`) is applied at metric and "
        "feature level only. No official record was changed or deleted; the source deliveries "
        "of innings 3 and 4 remain in `deliveries`.",
        "",
    ]
    i = res["innings_3_4"]
    L += [
        "## 2. Unverified innings 3/4 (RULE_INNINGS_3_4)",
        "",
        f"{i['rows']} rows in {i['matches']} matches (by innings: {i['rows_by_innings']}). "
        f"Reason codes: {i['reason_codes']}. Matches by reason: {i['matches_by_reason']}. "
        f"Rows excluded by the batter-pressure mask: {i['rows_excluded_by_mask_batter_pressure_sample']}; "
        f"bowler-pressure mask: {i['rows_excluded_by_mask_bowler_pressure_sample']}. "
        f"Rows still present in the official `deliveries` table: {i['source_rows_preserved_in_official_db']}. "
        f"Any of these rows inside a pressure population: {i['any_row_in_a_pressure_population']}.",
        "",
    ]
    e = res["extras"]
    L += [
        "## 3. Unknown extras never silently zero",
        "",
        md_table(["Category", "Rows"], [[k, v] for k, v in e["category_counts"].items()]),
        "",
        f"`other` rows mapped to None: {e['other_rows_mapped_to_none']}; Penalty mapped to None: "
        f"{e['penalty_rows_mapped_to_none']}; None-type rows with runs (kept as `None_with_runs`): "
        f"{e['none_type_with_runs_rows']}; rows with an unverified label: {e['unverified_label_rows']}. "
        f"Penalty rows removed from ball-count masks: {e['penalty_rows_excluded_by_metric_mask']}. "
        f"Rows with secondary extras runs: {e['secondary_runs_rows']} (field guard blocks it in bowler "
        f"economy: {e['secondary_guard_blocks_economy']}).",
        "",
    ]
    w = res["wicket_flags"]
    L += [
        "## 4. Wicket-flag disagreements (dismissal metrics only)",
        "",
        f"Rows with a dismissed player but `is_wicket` false: {w['dismissed_without_wicket_flag_rows']} "
        f"(regulation: {w['rows_in_regulation']['dismissed_no_flag']}). Rows with `is_wicket` true and "
        f"no dismissed player: {w['wicket_flag_without_dismissed_rows']} (regulation: "
        f"{w['rows_in_regulation']['wicket_no_dismissed']}). State rows where the two wicket counts "
        f"differ: {w['state_rows_where_wicket_count_variants_differ']}; state features drop "
        f"{w['state_features_rows_dropped']} rows. Primary dismissal-metric rows excluded: "
        f"{w['dismissal_metric_rows_excluded_primary']}.",
        "",
    ]
    d = res["dls"]
    L += [
        "## 5. DLS matches (RULE_DLS_TARGETS)",
        "",
        f"{d['dls_matches']} matches with revised fields ({d['dls_match_rows']} rows). Rows whose "
        f"revised state is not reconstructable: {d['rows_without_reconstructable_revised_state']} in "
        f"{d['matches_without_reconstructable_revised_state']} matches. DLS rows inside the primary chase "
        f"population: {d['dls_rows_in_primary_chase_population']}; of these flagged "
        f"`dls_exclude_primary`: {d['dls_exclude_primary_rows_in_primary_chase_population']}.",
        "",
    ]
    n = res["duplicate_names"]
    L += [
        "## 6. Duplicate names (RULE_DUPLICATE_NAMES)",
        "",
        f"{n['players_sharing_a_name']} players share a name ({n['distinct_shared_names']} names). "
        f"Of {n['ids_in_deliveries']} player ids in deliveries, a join on name would turn "
        f"{n['rows_if_joined_on_id']} rows into {n['rows_if_naively_joined_on_name']} and would merge "
        f"{n['ids_that_would_merge_by_name']} ids. The pipeline joins on `player_id` only; the guard "
        f"raises on name columns: {n['name_join_guard_raises']}.",
        "",
    ]
    x = res["xi_duplicates"]
    L += [
        "## 7. Duplicate squad records (RULE_XI_DUPLICATES)",
        "",
        f"`match_squads` has {x['squad_rows']} rows, {x['duplicate_flag_rows']} flagged duplicates, "
        f"{x['squad_rows_after_dedup']} after dedup. The chase pressure batter sample has "
        f"{x['pressure_sample_rows']} rows without a squad join, {x['rows_with_safe_squad_join']} with "
        f"the deduplicated join (per-player counts identical: "
        f"{x['per_player_counts_identical_without_and_with_safe_join']}), and "
        f"{x['rows_with_naive_squad_join']} with a naive join ({x['naive_join_extra_rows']} extra rows). "
        f"The pipeline does not use `match_squads`.",
        "",
    ]
    L += [
        "## 8. Exclusion ledger: rule x metric",
        "",
        "`rows_excluded` is non-zero only for EXCLUDE_ROWS_FROM_METRIC. Other effects report "
        "`rows_in_metric_scope` as flagged rows that are handled by a variant, guard or note. "
        "Rules without a row-level predicate show the official-table count.",
        "",
    ]

    def na(v):
        return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else fmt(v, 0)

    rows = []
    for r in ledger.to_dict("records"):
        flagged = r["rows_flagged"] if not pd.isna(r["rows_flagged"]) else r.get("official_count")
        rows.append(
            [
                r["rule_id"],
                r["metric"],
                r["effect"],
                na(flagged),
                na(r["rows_in_metric_scope"]),
                r["rows_excluded"],
                na(r["matches_affected"]),
                na(r["players_affected"]),
            ]
        )
    L += [
        md_table(
            [
                "Rule",
                "Metric",
                "Effect",
                "Flagged / official count",
                "In metric scope",
                "Excluded",
                "Matches",
                "Players",
            ],
            rows,
        ),
        "",
    ]
    L += [
        "Official-table counts for rules without a frame predicate:",
        "",
        md_table(["Rule", "Count"], [[k, v] for k, v in counts.items()]),
        "",
    ]
    L += [
        "## 9. Sensitivity: effect on exploratory pressure samples",
        "",
        "Sample: chase rows with a valid RRR in IPL/T20I, minus rows the register excludes. Score: raw "
        "residual per ball against a comp x phase x wickets cell mean, unshrunk (proxy, not the Stage 4 "
        "baseline). Minimum balls are the Stage 5 exploratory thresholds. `spearman_common` is over "
        "players eligible in both runs.",
        "",
    ]
    for role in ("batter", "bowler"):
        for name, v in sens[role].items():
            L += [f"### {role}: {name}", ""]
            L += [f"Rows dropped / added: {v.get('rows_dropped', v.get('dls_rows_added'))}.", ""]
            L += [
                md_table(
                    [
                        "Competition",
                        "Min balls",
                        "Rows primary",
                        "Rows variant",
                        "Eligible primary",
                        "Eligible variant",
                        "In both",
                        "Spearman",
                        "Max abs change",
                    ],
                    [
                        [
                            c,
                            m["min_balls"],
                            m["pressure_rows_primary"],
                            m["pressure_rows_variant"],
                            m["eligible_primary"],
                            m["eligible_variant"],
                            m["eligible_in_both"],
                            fmt(m["spearman_common"], 3),
                            fmt(m["max_abs_change_resid_per_ball"], 4),
                        ]
                        for c, m in v["metrics"].items()
                    ],
                ),
                "",
            ]
    dm = sens["dismissal_metric_wicket_flag_variants"]
    L += [
        "### Dismissal metric: wicket-flag variants",
        "",
        f"Striker dismissals primary {dm['dismissals_primary']}, with the dismissed-without-flag rows "
        f"{dm['dismissals_with_dismissed_no_flag']}; players whose count changes: "
        f"{dm['players_with_changed_dismissal_count']}; rows removed by RULE_WICKET_NO_DISMISSED: "
        f"{dm['rows_excluded_wicket_no_dismissed']}.",
        "",
    ]
    L += [
        "## 10. Feature dictionary",
        "",
        f"`pressure_feature_dictionary.json` lists {fd['feature_count']} features: "
        f"{fd['availability_counts']}. All are exploratory; none is validated.",
        "",
    ]
    L += [
        "## 11. Stop point",
        "",
        "Nothing here is a validated pressure result. Full pressure scoring, official rankings and "
        "ML training wait for explicit approval.",
    ]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    args = ap.parse_args(argv)
    cfg = load_restrictions()
    applier = rs.RestrictionApplier(cfg)
    before = snapshot_from_settings(s, args.db)
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        df = rs.attach_aux(load_frame(args.store), con)
        counts = official_counts(con)
        res = run_checks(df, None, applier, con, cfg)
        ledger = applier.ledger(df, counts)
    finally:
        con.close()
    sens = sensitivity(df, applier)
    fd = feature_dictionary(cfg)
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    invariants = {
        "register_rules": len(cfg["restrictions"]),
        "all_rules_implemented": True,
        "innings_3_4_rows_in_pressure_population": res["innings_3_4"][
            "any_row_in_a_pressure_population"
        ],
        "other_penalty_mapped_to_none": res["extras"]["other_rows_mapped_to_none"]
        + res["extras"]["penalty_rows_mapped_to_none"],
        "xi_counts_identical": res["xi_duplicates"][
            "per_player_counts_identical_without_and_with_safe_join"
        ],
        "official_unchanged": not diff,
    }
    ok = (
        len(cfg["restrictions"]) == 26
        and not invariants["innings_3_4_rows_in_pressure_population"]
        and invariants["other_penalty_mapped_to_none"] == 0
        and invariants["xi_counts_identical"]
        and not diff
    )
    out = {
        **STATUS,
        "register": RESTRICTIONS_PATH.name,
        "global_exclusion": False,
        "records_deleted": 0,
        "invariants": invariants,
        "checks": res,
        "ledger": ledger.to_dict("records"),
        "official_table_counts": counts,
        "sensitivity": sens,
        "provenance": provenance(None, RESTRICTIONS_PATH),
        "preservation": {"official_unchanged": not diff, "diff": diff},
    }
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    write_json_deterministic(args.reports_dir / "phase3_data_quality_application.json", out)
    write_json_deterministic(args.reports_dir / "pressure_feature_dictionary.json", fd)
    write_text(
        args.reports_dir / "phase3_data_quality_application_report.md",
        render(res, ledger, sens, counts, cfg, fd),
    )
    print(
        f"rules={len(cfg['restrictions'])} features={fd['feature_count']} ok={ok} "
        f"official_unchanged={not diff}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
