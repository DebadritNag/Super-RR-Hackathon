"""Phase 6 chunk 1: run the cleanup checks on the real code and data and write the report.

Writes ``phase6_cleanup_checks.json`` and ``phase6_cleanup_report.md`` (new files only; Phase 4 and
Phase 5 reports and the official data are hashed before and after and must not change).
Read-only on the analytical store. INTERNAL / EXPERIMENTAL_NOT_VALIDATED; nothing is published.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.main import create_app  # noqa: E402
from app.phase5 import classification_v2 as c2  # noqa: E402
from app.phase5.cache import GATE_CONFIG_VERSION, cache_key  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.filters import FilterSpec  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402
from app.phase6.cleanup_scans import (  # noqa: E402
    forbidden_public_names,
    scan_vacuous_assertions,
    scan_wording,
    vacuous_in_source,
    walk_model_fields,
)
from app.schemas import phase4 as sc  # noqa: E402

PRERUN = Path("d:/Data/.agents/tasks/phase6_prerun_hashes.json")
WORDING_FILES = (
    "docs/frontend_backend_contracts.md",
    "docs/backend_implementation_spec.md",
    "app/phase5/classification_v2.py",
    "app/phase5/reports.py",
    "app/phase5/filters.py",
    "app/schemas/phase5.py",
    "app/services/phase4_service.py",
    "scripts/phase5_classification.py",
)
OLD_VACUOUS = {
    "tests/test_phase5_dynamic_ranking.py:583": 'assert r["interval_low"] <= r["score"] <= r["interval_high"] or True',
    "tests/test_phase5_dynamic_ranking.py:594": 'assert len(table) == len(specs) == len(set(table["spec_hash"]) | set()) or True',
    "tests/test_pressure_state.py:45": "assert s.team_wickets_before.tolist() == [0, 0, 0, 0, 0, 1, 1][:3] + [0, 1, 1, 1][:0] or True",
}
PUBLIC_DIRECTORY_PATHS = ("/api/v1/players", "/api/v1/players/{player_id}")
# (file, why) for every existing test edited during the cleanup.
TESTS_EDITED = [
    (
        "tests/test_phase5_dynamic_ranking.py",
        "two vacuous asserts replaced; cache tests use the new cache_key / get_or_compute signature and assert copies (`is not`) instead of identity",
    ),
    (
        "tests/test_pressure_state.py",
        "always-true line deleted (the next line asserts the real list)",
    ),
    (
        "tests/test_phase5_classification.py",
        "STATUS_VALUES now three real values; coverage has 9 combinations and a separate placeholder count; mapping test uses ACCEPTED_STORED_VALUES",
    ),
    (
        "tests/test_phase4_api.py",
        "public /players has its own descriptive flags; coverage has 9 combinations (stored placeholder rows counted separately)",
    ),
    (
        "tests/test_phase5_gating.py",
        "public directory carries descriptive_only and no publication fields; route census counts the two new /internal/players routes (10 -> 12)",
    ),
    (
        "tests/test_phase5_strict_uncapped.py",
        "directory strict-uncapped checks: internal route keeps the full disabled body, public route returns the minimal PublicDisabled body",
    ),
]
FILES_CHANGED = [
    "app/phase5/classification_v2.py", "app/phase5/cache.py", "app/phase5/filters.py",
    "app/phase5/reports.py", "app/phase4/uncapped.py", "app/schemas/phase4.py",
    "app/schemas/phase5.py", "app/services/phase4_service.py", "app/services/phase5_service.py",
    "app/api/v1/routes.py", "app/api/v1/routes_phase5.py", "scripts/phase5_classification.py",
    "scripts/phase5_gates.py", "docs/frontend_backend_contracts.md",
    "docs/backend_implementation_spec.md",
]  # fmt: skip
FILES_ADDED = [
    "app/phase6/__init__.py", "app/phase6/cleanup_scans.py", "scripts/phase6_cleanup_checks.py",
    "tests/test_phase6_classification_wording.py", "tests/test_phase6_no_vacuous_assertions.py",
    "tests/test_phase6_public_schema.py", "tests/test_phase6_cache_isolation.py",
    "tests/test_phase6_cleanup.py",
]  # fmt: skip


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_wording() -> dict:
    hits = {}
    for rel in WORDING_FILES:
        found = scan_wording((ROOT / rel).read_text(encoding="utf-8"))
        if found:
            hits[rel] = found
    return {"files_scanned": len(WORDING_FILES), "hits": hits}


def check_vacuous() -> dict:
    tests = ROOT / "tests"
    hits = scan_vacuous_assertions(tests, exclude=("test_phase6_no_vacuous_assertions.py",))
    scanner_detects_old = len(vacuous_in_source("\n".join(OLD_VACUOUS.values()))) == len(
        OLD_VACUOUS
    )
    files = sorted(p for p in tests.rglob("*.py"))
    return {
        "test_files_scanned": len(files),
        "found_before_cleanup": OLD_VACUOUS,
        "found_after_cleanup": [list(h) for h in hits],
        "scanner_detects_the_original_lines": scanner_detects_old,
    }


def check_schema(app) -> dict:
    public = {
        m.__name__: sorted(walk_model_fields(m))
        for m in (
            sc.PublicPlayerRow,
            sc.PublicPlayerListResponse,
            sc.PublicPlayerDetailResponse,
            sc.PublicDisabled,
        )
    }
    forbidden = {k: forbidden_public_names(set(v)) for k, v in public.items()}
    internal_only = sorted(
        walk_model_fields(sc.PlayerListResponse) - set(public["PublicPlayerListResponse"])
    )
    routes = []
    for r in app.routes:
        if not isinstance(r, APIRoute) or not r.path.startswith("/api/v1"):
            continue
        scope = (
            "internal" if "/internal/" in r.path else "admin" if "/admin/" in r.path else "public"
        )
        row = {"path": r.path, "methods": sorted(r.methods - {"HEAD", "OPTIONS"}), "scope": scope}
        if r.path in PUBLIC_DIRECTORY_PATHS:
            row["response_fields_forbidden"] = forbidden_public_names(
                walk_model_fields(r.response_model)
            )
        routes.append(row)
    return {
        "public_model_fields": public,
        "forbidden_names_in_public_models": forbidden,
        "fields_only_on_internal_directory_model": internal_only,
        "routes": sorted(routes, key=lambda x: (x["scope"], x["path"])),
        "public_directory_routes_clean": all(
            not r.get("response_fields_forbidden")
            for r in routes
            if r["path"] in PUBLIC_DIRECTORY_PATHS
        ),
    }


def check_cache(app) -> dict:
    svc = app.state.service5
    base = ("spec", "d", "m", GATE_CONFIG_VERSION, "internal", "l", "s")
    keys = {cache_key(*base)}
    for i, alt in enumerate(["spec2", "d2", "m2", "g2", "public", "l2", "s2"]):
        parts = list(base)
        parts[i] = alt
        keys.add(cache_key(*parts))
    spec = FilterSpec(role="batter", format="COMBINED_w70_30", limit=10)
    first = svc.ranking(spec, internal=True)
    pristine = copy.deepcopy(first)
    first["page"]["items"][0]["score"] = -1.0e9
    first["versions"]["model_version"] = "tampered"
    first["page"]["items"].clear()
    second = svc.ranking(spec, internal=True)
    pristine["cache_hit"] = True
    mutation_safe = second == pristine and second["cache_hit"] is True
    # Cost of one deep copy on the largest real full ranking among a few broad contexts.
    timings = {}
    worst = (0.0, "")
    for fmt in ("IPL", "T20I", "COMBINED_w70_30"):
        for role in ("batter", "bowler"):
            sp = FilterSpec(role=role, format=fmt)
            full, _ = svc._full(sp, True)
            t0 = time.perf_counter()
            copy.deepcopy(full)
            ms = (time.perf_counter() - t0) * 1000.0
            timings[f"{fmt}|{role}"] = {
                "rows": len(full.get("rows", [])),
                "deepcopy_ms": round(ms, 2),
            }
            worst = max(worst, (ms, f"{fmt}|{role}"))
    inside = total = 0
    full, _ = svc._full(FilterSpec(role="batter", format="COMBINED_w70_30"), True)
    for r in full.get("rows", []):
        if r.get("interval_low") is None or r.get("score") is None:
            continue
        total += 1
        inside += int(r["interval_low"] <= r["score"] <= r["interval_high"])
    return {
        "distinct_keys_for_8_variants": len(keys),
        "mutation_safe_on_real_data": bool(mutation_safe),
        "scope_values_in_key": ["internal", "public"],
        "deepcopy_budget_ms": 50,
        "within_budget": worst[0] <= 50.0,
        "interval_contains_score": {
            "context": "batter COMBINED_w70_30 ALL/ALL",
            "inside": inside,
            "rows": total,
        },
        "cache_stats": svc.cache.stats() if svc.cache else {},
        # wall-clock timings are machine dependent: kept out of the hashed outputs
        "_timings": {
            "deepcopy_timings": timings,
            "worst_deepcopy_ms": round(worst[0], 2),
            "worst_context": worst[1],
        },
    }


def check_classification(app) -> dict:
    cov = app.state.service.coverage()["coverage"]["summary"]
    caps = app.state.service.capabilities()
    return {
        "status_values": list(c2.STATUS_VALUES),
        "disabled_placeholder_values": list(c2.DISABLED_PLACEHOLDER_VALUES),
        "capabilities_classification_values": caps["classification_values"],
        "capabilities_disabled_placeholder_values": caps["disabled_placeholder_values"],
        "status_counts": cov["status_counts"],
        "disabled_placeholder_counts": cov["disabled_placeholder_counts"],
        "combinations": len(cov["combinations_all_players"]),
        "players_total": cov["players_total"],
        "strict_uncapped_enabled": caps["strict_uncapped_enabled"],
    }


def preservation_vs_prerun() -> dict:
    if not PRERUN.exists():
        return {"available": False}
    files = json.loads(PRERUN.read_text(encoding="utf-8-sig"))["files"]
    changed = []
    # exploratory.duckdb holds the p6_ tables written by Phase 6 itself; its p4_/p5_ tables are
    # compared table by table in the orchestrator, so the file hash is not a valid check.
    files = {k: v for k, v in files.items() if Path(k).name != "exploratory.duckdb"}
    for name, rec in files.items():
        p = Path(name)
        if not p.exists() or sha(p) != rec["sha256"]:
            changed.append(name)
    return {"available": True, "files_checked": len(files), "changed": sorted(changed)}


def md(results: dict) -> str:
    w, v, s, c, k, p = (
        results["wording"], results["vacuous"], results["schema"], results["cache"],
        results["classification"], results["preservation"],
    )  # fmt: skip
    L: list[str] = [
        "# Phase 6 cleanup report",
        "",
        f"Status: `{STATUS}`. INTERNAL only. No official Top 10, no public experimental ranking, no ML training, no change to the methodology, thresholds or the 0.5 data-weight gate. Numbers below come from `scripts/phase6_cleanup_checks.py` run on the real code and data.",
        "",
        "## 1. Classification wording (decision 1)",
        f"- Real values: {', '.join(f'`{x}`' for x in k['status_values'])}. Disabled placeholder (not an established fourth status): {', '.join(f'`{x}`' for x in k['disabled_placeholder_values'])}.",
        f"- `GET /meta/capabilities` now lists `classification_values` = {k['capabilities_classification_values']} and `disabled_placeholder_values` = {k['capabilities_disabled_placeholder_values']}. `strict_uncapped_enabled` = {k['strict_uncapped_enabled']}.",
        f"- Real data ({k['players_total']} players): status counts {k['status_counts']}; placeholder count {k['disabled_placeholder_counts']}; coverage has {k['combinations']} combinations (3 nationalities x 3 real statuses).",
        "- Unchanged: the strict-uncapped filter still answers `STRICT_UNCAPPED_DISABLED`, the validated override mechanism still accepts the placeholder value, and verified status is never inferred.",
        f"- Wording scan over {w['files_scanned']} contract, spec, schema and generator files for a four-valued description: {len(w['hits'])} files with hits ({w['hits'] or 'none'}).",
        "- Stored Phase 5 reports (`phase5_*`) are byte-identical and were not rewritten. They still contain the old four-status wording in places. The corrected wording is in the generators and in this Phase 6 output.",
        "- `docs/phase5_design.md` is a historical design record and still describes four values; it is superseded by section 10 of `docs/frontend_backend_contracts.md` and section 12 of `docs/backend_implementation_spec.md`.",
        "",
        "## 2. Vacuous assertions (decision 6b)",
        f"- Before: {len(v['found_before_cleanup'])} always-true assertions, found by grep (the brief named two; the scan found a third).",
    ]
    for loc, line in v["found_before_cleanup"].items():
        L.append(f"  - `{loc}`: `{line}`")
    L += [
        f"- After: {len(v['found_after_cleanup'])} found by an AST scan of {v['test_files_scanned']} test files. The scanner detects the original three lines: {v['scanner_detects_the_original_lines']}.",
        "- Replacements: the interval line now asserts both bounds are finite and `interval_low <= interval_high` (containment of the point score is not asserted, see below); the spec-hash line asserts one row per spec and unique hashes; the third line was deleted because the next line already asserts the real list.",
        f"- Observed rate at which the bootstrap interval contains the point score (real data, {c['interval_contains_score']['context']}): {c['interval_contains_score']['inside']} of {c['interval_contains_score']['rows']} rows. A rate below 1 is reported here and does not fail a test, because a percentile band of a shrunk score need not bracket the point estimate.",
        "- New guard: `tests/test_phase6_no_vacuous_assertions.py` fails on any `assert ... or True`, `assert True` or `assert <truthy constant>` in `tests/`.",
        "",
        "## 3. Public descriptive directory (decision 6c)",
        f"- Public models walked recursively; forbidden-name hits: { {k_: v_ for k_, v_ in s['forbidden_names_in_public_models'].items()} }.",
        f"- Public directory routes clean: {s['public_directory_routes_clean']}.",
        f"- Fields present only on the internal directory model: {s['fields_only_on_internal_directory_model']}.",
        "- Public `/players` and `/players/{player_id}` return `PublicPlayerListResponse` / `PublicPlayerDetailResponse`: identity, nationality and status with their verification labels, group, squad role and match counts, plus `status`, `disclaimer`, `descriptive_only`. No `official_ranking`, `publication_status` or `gate_results`.",
        "- Removed from the public shape: `eligible_scopes`, `conflict_flag`, the publication and gate fields, and the `min_pressure_matches` query filter (open decision OD-6; an API change visible to any caller that used them). All remain on `/internal/players` and `/internal/players/{player_id}` (admin token).",
        "- Score-bearing routes were already split before this phase: the public twins of rankings, profile, compare, selection and dynamic rankings answer 403 `PUBLICATION_GATE_NOT_SATISFIED` without rows, and `/internal/...` needs the admin token. No route had to be moved.",
        "- Route census (path, scope):",
    ]
    for r in s["routes"]:
        L.append(f"  - `{r['path']}` {','.join(r['methods'])}: {r['scope']}")
    L += [
        "",
        "## 4. Cache isolation (decision 6d)",
        "- Key: SHA-256 of the JSON list `[spec hash, data version, model version, gate-config version, scope, lock version, gate-state hash]`. `scope` is `internal` or `public`; `lock version` is the SHA-256 of `config/phase5_methodology_lock_v1.json`; `gate-state hash` hashes the sorted ids of failing gates.",
        f"- Eight single-component variants of one key give {c['distinct_keys_for_8_variants']} distinct keys.",
        "- Entries are stored as deep copies and returned as deep copies (hit and miss). The paged payload is also copied.",
        f"- Mutating a real-data response (score, versions, item list) did not change the next response: {c['mutation_safe_on_real_data']}.",
        f"- Deep-copy cost on the real full rankings (six broad contexts) is within the {c['deepcopy_budget_ms']} ms budget: {c['within_budget']}. The pickled-bytes fallback of open decision OD-10 is therefore not needed. The measured milliseconds are machine dependent and are written to `phase6_cleanup_timings.json` (excluded from the reproducibility hash).",
    ]
    L += [
        "",
        "## 5. Existing tests edited (reason for each)",
    ]
    for f, why in TESTS_EDITED:
        L.append(f"- `{f}`: {why}.")
    L += [
        "",
        "## 6. Files",
        "- Changed: " + ", ".join(f"`{x}`" for x in FILES_CHANGED) + ".",
        "- Added: " + ", ".join(f"`{x}`" for x in FILES_ADDED) + ".",
        "",
        "## 7. Preservation",
        f"- Official data, Phase 4 reports and the TEST lock log: all preserved = {results['preservation_live']['all_preserved']}; Phase 5 lock log events = {results['preservation_live']['phase5_lock_log_events']}; TEST opened = {results['preservation_live']['test_opened']}.",
        (
            f"- {p['files_checked']} files hashed before Phase 6 (databases, source CSVs, Phase 4 and Phase 5 reports) compared now: {len(p['changed'])} changed {p['changed'] or ''}."
            if p.get("available")
            else "- Pre-run hash file not found."
        ),
        "",
        "## 8. What this does not do",
        "- No methodology, threshold, gate or ranking value changed. The 0.5 data-weight gate is untouched. The 42 late-dated T20I matches stay excluded. TEST stays unopened and is not pristine.",
        "- Public rankings stay gated: every publication gate except the per-request pool gate still fails.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    pres = Preservation(args.reports)
    app = create_app(admin_token="phase6-cleanup")
    results = {
        "status": STATUS,
        "official_ranking": False,
        "classification": check_classification(app),
        "wording": check_wording(),
        "vacuous": check_vacuous(),
        "schema": check_schema(app),
        "cache": check_cache(app),
    }
    results["preservation_live"] = pres.verify()
    results["preservation"] = preservation_vs_prerun()
    ok = (
        not results["wording"]["hits"]
        and not results["vacuous"]["found_after_cleanup"]
        and results["vacuous"]["scanner_detects_the_original_lines"]
        and results["schema"]["public_directory_routes_clean"]
        and all(not v for v in results["schema"]["forbidden_names_in_public_models"].values())
        and results["cache"]["mutation_safe_on_real_data"]
        and results["cache"]["distinct_keys_for_8_variants"] == 8
        and results["preservation_live"]["all_preserved"]
        and results["preservation"].get("changed", []) == []
    )
    results["all_checks_passed"] = bool(ok)
    timings = results["cache"].pop("_timings")
    args.reports.mkdir(parents=True, exist_ok=True)
    write_json_deterministic(args.reports / "phase6_cleanup_checks.json", results)
    write_json_deterministic(args.reports / "phase6_cleanup_timings.json", timings)
    (args.reports / "phase6_cleanup_report.md").write_text(md(results), encoding="utf-8")
    print(
        json.dumps(
            {k: results[k] for k in ("all_checks_passed", "wording", "classification")}, indent=1
        )[:1500]
    )
    print(
        "preserved:",
        results["preservation_live"]["all_preserved"],
        results["preservation"].get("changed"),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
