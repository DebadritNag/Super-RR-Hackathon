"""Markdown report for the format-weight sensitivity result (reads only the JSON dict)."""

from __future__ import annotations

from typing import Any

from app.analytics.reporting import INTERPRETATION, fmt, md_table


def render_report(res: dict[str, Any]) -> str:
    cfgs = res["config"]
    L: list[str] = []
    L.append("# Format weight sensitivity report (Decision 1)\n")
    L.append("## 1. Status and interpretation\n")
    L.append(
        f"- proxy_run: {fmt(res['proxy_run'])}\n"
        f"- pressure_status: {res['pressure_status']}\n"
        f"- score_label: {res['score_label']}\n"
        f"- not_for_publication: {fmt(res['not_for_publication'])}\n"
        f"- default configuration: {cfgs['default_config_id']} "
        f"({cfgs['default_flag']}, config status {cfgs['status']})\n"
        f"- config version: {cfgs['version']}, hash `{cfgs['config_hash']}`\n"
        f"- eligibility level for the primary run: {res['eligibility_level']}\n"
    )
    L.append(INTERPRETATION + "\n")
    L.append(
        "The 70:30 weighting is a provisional default, not a validated choice. Format scores "
        "are computed independently. A combined score exists only for players eligible in both "
        "formats; missing format observations are never replaced by zero.\n"
    )
    L.append("## 2. Configurations\n")
    L.append(
        md_table(
            ["id", "IPL weight", "T20I weight"],
            [[c["id"], c["ipl_weight"], c["t20i_weight"]] for c in cfgs["configurations"]],
        )
    )
    L.append("## 3. Method notes\n")
    for k, v in res["method_notes"].items():
        L.append(f"- **{k}**: {v}")
    L.append("")
    L.append("Format eligibility thresholds (balls, percentile rule):\n")
    L.append(
        md_table(
            ["role", "IPL", "T20I"],
            [[r, t["IPL"], t["T20I"]] for r, t in res["thresholds"].items()],
        )
    )
    n = 4
    for role, rr in res["roles"].items():
        L.append(f"## {n}. {role.capitalize()}s\n")
        n += 1
        sc = rr["status_counts"]
        L.append(f"Players seen in either format: {sc['players_total']}.\n")
        L.append(
            md_table(
                ["combined status", "players"],
                [[k, v] for k, v in sc["combined_status"].items()],
            )
        )
        L.append(
            md_table(
                ["format", "ELIGIBLE", "OBSERVED_NOT_ELIGIBLE", "NOT_OBSERVED"],
                [
                    [
                        f.upper(),
                        sc[f"{f}_status"]["ELIGIBLE"],
                        sc[f"{f}_status"]["OBSERVED_NOT_ELIGIBLE"],
                        sc[f"{f}_status"]["NOT_OBSERVED"],
                    ]
                    for f in ("ipl", "t20i")
                ],
            )
        )
        ecs = rr["eligibility_change_summary"]
        L.append(
            f"Combined population: {rr['combined_population']} players, identical across "
            f"configurations: {fmt(ecs['eligibility_identical_across_configs'])}. Single-format "
            "players are ranked only in their own format list and excluded from the combined "
            "ranking.\n"
        )
        L.append("### Sensitivity versus the default configuration\n")
        rows = []
        for cid, e in rr["configs"].items():
            mv = e["movement_vs_default"]
            rows.append(
                [
                    cid,
                    e["n_ranked"],
                    e["overlap_with_default"],
                    e["spearman_with_default"],
                    mv["mean_abs_change"],
                    mv["max_abs_change"],
                    len(mv["entering_top_k"]),
                    len(mv["leaving_top_k"]),
                ]
            )
        L.append(
            md_table(
                [
                    "config",
                    "n ranked",
                    "Top 10 overlap",
                    "Spearman",
                    "mean abs rank change",
                    "max abs rank change",
                    "entering Top 10",
                    "leaving Top 10",
                ],
                rows,
            )
        )
        L.append("### Pairwise Top 10 overlap\n")
        pw = rr["pairwise"]
        L.append(
            md_table(
                [""] + pw["config_ids"],
                [[pw["config_ids"][i]] + row for i, row in enumerate(pw["top_k_overlap"])],
            )
        )
        L.append(f"### Pairwise Spearman (n = {pw['n_common'][0][0]} in every cell)\n")
        L.append(
            md_table(
                [""] + pw["config_ids"],
                [[pw["config_ids"][i]] + row for i, row in enumerate(pw["spearman"])],
            )
        )
        L.append("### Degenerate configurations\n")
        for cid, d in rr["degenerate_check"].items():
            L.append(
                f"- {cid}: ranks equal single-format z-score ranks within the same population "
                f"of {d['population']}: {fmt(d['ranks_equal_single_format_zscore_ranks'])}"
            )
        L.append("")
        L.append("### Biggest movers versus default\n")
        mrows = []
        for cid, e in rr["configs"].items():
            for m in e["movement_vs_default"]["biggest_movers"][:3]:
                mrows.append([cid, m["player_id"], m["rank_a"], m["rank_b"], m["change"]])
        L.append(md_table(["config", "player_id", "default rank", "config rank", "change"], mrows))
        adj = rr["adjusted_estimate"]
        L.append(f"### {adj['label']} (separate section)\n")
        L.append(adj["note"] + f" Players with an estimate: {adj['n_players']}.\n")
    L.append(f"## {n}. Robustness to the eligibility level\n")
    n += 1
    for level, rob in res["robustness"].items():
        L.append(f"### Level {level}\n")
        rows = []
        for role, rr in rob["roles"].items():
            ch = rr["eligibility_change_vs_primary"]
            c5 = rr["configs"]
            worst_overlap = min(e["overlap_with_default"] for e in c5.values())
            rhos = [
                e["spearman_with_default"]
                for e in c5.values()
                if e["spearman_with_default"] is not None
            ]
            rows.append(
                [
                    role,
                    rob["thresholds"][role]["IPL"],
                    rob["thresholds"][role]["T20I"],
                    ch["combined_population_this_level"],
                    ch["combined_population_primary"],
                    ch["entering"],
                    ch["leaving"],
                    worst_overlap,
                    min(rhos) if rhos else None,
                ]
            )
        L.append(
            md_table(
                [
                    "role",
                    "IPL threshold",
                    "T20I threshold",
                    "combined pop",
                    "pop at primary",
                    "entering",
                    "leaving",
                    "min Top 10 overlap vs default",
                    "min Spearman vs default",
                ],
                rows,
            )
        )
    L.append(f"## {n}. Technical appendix (PROXY_NOT_PRESSURE, not for publication)\n")
    for role, rr in res["roles"].items():
        app = rr.get("technical_appendix")
        if app:
            L.append(f"{role.capitalize()} default-configuration Top 10 (proxy):\n")
            L.append(
                md_table(
                    ["player_id", "name"],
                    [[p["player_id"], p["name"]] for p in app["default_config_top10"]],
                )
            )
    return "\n".join(L) + "\n"
