"""Build the Phase 7 descriptive profile CSVs, manifest and context JSON.

Reads the official database and the exploratory store read-only. Writes only files under
data/reports/. Run: ``python scripts/phase7_build_descriptive.py`` from ``backend``.
``--phase9`` extends the window to the 2026 matches (owner decision D1, release record required).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.phase7 import context as ctx  # noqa: E402
from app.phase7 import descriptive as ds  # noqa: E402


def main() -> None:
    phase9 = "--phase9" in sys.argv[1:]
    cfg = ds.load_config()
    if phase9:
        cfg = {
            **cfg,
            "window": "2022-01-22 to 2026-11-01 (all matches, 2026 included by owner decision D1)",
        }
    official_sha = ds.sha256_file(ds.OFFICIAL_DB)
    store_sha = ds.sha256_file(ds.EXPLORATORY_DB)
    frame = ds.load_frame(include_test=phase9)
    ref = ds.load_reference(include_test=phase9)
    prov = {
        "state_version": str(frame["state_version"].iloc[0]),
        "official_db_sha256": official_sha,
        "analytical_store_sha256": store_sha,
    }
    out = ds.build_profiles(frame, ref, cfg, prov)
    rep = ds.REPORTS
    hashes = {
        ds.BATTER_CSV: ds.write_csv(out["batters"], rep / ds.BATTER_CSV),
        ds.BOWLER_CSV: ds.write_csv(out["bowlers"], rep / ds.BOWLER_CSV),
        ds.PER_MATCH_CSV: ds.write_csv(out["per_match"], rep / ds.PER_MATCH_CSV),
    }
    summary = {
        "window": cfg["window"],
        "formats": {
            f: {
                "matches": int(g["match_id"].nunique()),
                "delivery_rows": int(len(g)),
                "batter_profiles": int((out["batters"]["format"] == f).sum()),
                "bowler_profiles": int((out["bowlers"]["format"] == f).sum()),
            }
            for f, g in frame.groupby("format")
        },
        "players_with_any_profile": int(
            len(set(out["batters"]["player_id"]) | set(out["bowlers"]["player_id"]))
        ),
    }
    context = ctx.build_context(summary)
    context["overview"]["descriptive_hashes"] = hashes
    (rep / ds.CONTEXT_JSON).write_text(
        json.dumps(context, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "descriptive_version": cfg["version"],
        "config_sha256": ds.sha256_file(ds.CONFIG_PATH),
        "inputs": {
            "superr.duckdb": official_sha,
            "exploratory.duckdb": store_sha,
            "state_version": prov["state_version"],
        },
        "bootstrap": cfg["bootstrap"],
        "rows": {
            "batter_profiles": int(len(out["batters"])),
            "bowler_profiles": int(len(out["bowlers"])),
            "per_match": int(len(out["per_match"])),
            "frame_rows": int(len(frame)),
        },
        "outputs_sha256": hashes,
    }
    (rep / ds.MANIFEST_JSON).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["rows"]), json.dumps(summary["formats"]))


if __name__ == "__main__":
    main()
