"""Phase 5 Chunk 4: run the example filter sets through the running app (internal token).

Writes ``phase5_dynamic_examples.json``: for each example (All players, Indian + Batter, Overseas +
Capped, Death overs, Chase situations, a custom combination, and the disabled Indian + Uncapped and
Uncapped + Bowler sets) the status, pool size, reasons and the top rows. Rows are experimental
working-pool output labelled INTERNAL_EXPERIMENTAL_ONLY; nothing here is a published Top 10.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.analytics.reporting import write_json_deterministic  # noqa: E402
from app.main import create_app  # noqa: E402
from app.phase5.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402

EXAMPLES = {
    "All players (batters)": {"role": "batter"},
    "All players (bowlers)": {"role": "bowler"},
    "Indian + Uncapped (disabled)": {"role": "batter", "nationality": "Indian", "status": "VERIFIED_UNCAPPED"},
    "Overseas + Capped (derived or verified)": {"role": "batter", "nationality": "Overseas", "status": "CAPPED_ANY"},
    "Indian + Batter": {"role": "batter", "nationality": "Indian"},
    "Uncapped + Bowler (disabled)": {"role": "bowler", "status": "VERIFIED_UNCAPPED"},
    "Death overs (bowlers)": {"role": "bowler", "phase": "death"},
    "Chase situations (batters)": {"role": "batter", "situation": "chase"},
    "Custom: Indian + DERIVED_CAPPED + death + chase (batters)": {
        "role": "batter", "nationality": "Indian", "status": "DERIVED_CAPPED", "phase": "death", "situation": "chase",
    },
    "Custom: IPL powerplay chase Indian DERIVED_CAPPED bowlers": {
        "role": "bowler", "format": "IPL", "nationality": "Indian", "status": "DERIVED_CAPPED",
        "phase": "powerplay", "situation": "chase",
    },
}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args(argv)
    pres = Preservation(args.reports)
    c = TestClient(create_app(admin_token="demo"))
    h = {"X-Admin-Token": "demo"}
    out = {}
    for name, body in EXAMPLES.items():
        r = c.post("/api/v1/internal/rankings/dynamic", json={**body, "limit": args.top}, headers=h)
        d = r.json()
        entry = {"request": body, "http": r.status_code, "result_status": d.get("result_status"),
                 "publication_status": d.get("publication_status"),
                 "pool_size": d.get("pool_size"), "reasons": d.get("reasons", [])}  # fmt: skip
        if "page" in d:
            entry["context_data_weight"] = d["context_data_weight"]
            entry["top_rows"] = [
                {
                    k: i[k]
                    for k in (
                        "rank",
                        "player_id",
                        "name",
                        "score",
                        "n",
                        "matches",
                        "n_eff",
                        "shrinkage_weight",
                        "top10_inclusion_prob",
                        "international_status",
                        "nationality",
                    )
                }  # fmt: skip
                for i in d["page"]["items"]
            ]
        else:
            entry["source_needed"] = d.get("source_needed")
        out[name] = entry
    ok = pres.verify()
    write_json_deterministic(
        args.reports / "phase5_dynamic_examples.json",
        {"status": STATUS, "official_ranking": False, "publication_status": "INTERNAL_EXPERIMENTAL_ONLY",
         "examples": out, "preservation": ok},
    )  # fmt: skip
    for n, e in out.items():
        print(
            f"{n}: {e['result_status']} pool={e['pool_size']} reasons={[r['code'] for r in e['reasons']]}"
        )
    print("preserved:", ok["all_preserved"])
    return 0 if ok["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
