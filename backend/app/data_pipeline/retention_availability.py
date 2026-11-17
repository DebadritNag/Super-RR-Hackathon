"""Availability-aware candidate output built from the imported retention list.

Descriptive context only: no score, rank or recommendation order (rows are sorted by name).
RETAINED players are removed from the candidate pool; a player is ``confirmed_available`` only
when an authoritative AUCTION_AVAILABLE row names them. Everyone else keeps the status the list
gave them, or UNKNOWN. With no list the output is header-only and the manifest says so.
Historical profile data is read, never changed.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import BACKEND_ROOT
from app.data_pipeline.retention_importer import (
    REPORTS_DIR,
    effective_status,
    sha256_file,
)
from app.services.pressure_service import EXPLORATORY_DB

COLUMNS = (
    "player_id", "player_name", "side", "availability_status", "confirmed_available",
    "listed_in_retention_file", "team", "verification_status", "source", "snapshot_date",
    "matches_played", "balls_faced", "legal_balls_bowled", "note",
)  # fmt: skip
NO_LIST = "NO_RETENTION_FILE_YET"
STATEMENT = (
    "Availability is descriptive context. It does not change any score, status or eligibility. "
    "Rows are sorted by player name, not by merit. RETAINED players are excluded; only an "
    "authoritative AUCTION_AVAILABLE row makes a player confirmed available; UNKNOWN stays UNKNOWN."
)
PROFILE_DIR = BACKEND_ROOT / "data" / "reports"


def _profiles(profile_dir: Path | str) -> pd.DataFrame:
    d = Path(profile_dir)
    bat = pd.read_csv(d / "descriptive_batter_profiles.csv")
    bowl = pd.read_csv(d / "descriptive_bowler_profiles.csv")
    b = bat.groupby("player_id").agg(
        player_name=("player_name", "first"), matches=("matches_played", "sum"),
        balls_faced=("balls_faced", "sum"),
    )  # fmt: skip
    w = bowl.groupby("player_id").agg(
        player_name=("player_name", "first"), matches_b=("matches_played", "sum"),
        legal_balls=("legal_balls", "sum"),
    )  # fmt: skip
    j = b.join(w, how="outer", lsuffix="", rsuffix="_w")
    j["player_name"] = j["player_name"].fillna(j["player_name_w"])
    j["matches"] = j[["matches", "matches_b"]].max(axis=1)
    j["side"] = [
        "batter+bowler" if pd.notna(a) and pd.notna(c) else ("batter" if pd.notna(a) else "bowler")
        for a, c in zip(j["balls_faced"], j["legal_balls"], strict=True)
    ]
    return j.reset_index()


def build_availability(
    store: Path | str = EXPLORATORY_DB,
    out_dir: Path | str = REPORTS_DIR,
    profile_dir: Path | str = PROFILE_DIR,
) -> dict[str, Any]:
    """Write ``candidate_availability.csv`` and its manifest. Never writes a database."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path, man_path = (
        out / "candidate_availability.csv",
        out / "candidate_availability_manifest.json",
    )
    meta, per, unresolved = effective_status(store)
    rows: list[list[Any]] = []
    retained: list[int] = []
    if meta is not None:
        prof = _profiles(profile_dir)
        retained = sorted(p for p, d in per.items() if d["status"] == "RETAINED")
        for r in prof.sort_values("player_name", key=lambda s: s.str.casefold()).itertuples():
            pid = int(r.player_id)
            d = per.get(pid)
            if d is not None and d["status"] == "RETAINED":
                continue
            status = d["status"] if d else "UNKNOWN"
            note = ""
            if status == "CONFLICT":
                note = "conflicting statuses in the list; treated as not confirmed"
            elif d is None:
                note = "not listed (no status inferred from absence)"
            rows.append([
                pid, r.player_name, r.side, status, bool(d and d["confirmed_available"]),
                d is not None, d["team"] if d else "",
                meta["verification_status"] if d else "", meta["source"] if d else "",
                str(meta["snapshot_date"]) if d else "",
                "" if pd.isna(r.matches) else int(r.matches),
                "" if pd.isna(r.balls_faced) else int(r.balls_faced),
                "" if pd.isna(r.legal_balls) else int(r.legal_balls), note,
            ])  # fmt: skip
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    state = NO_LIST if meta is None else "LIST_IMPORTED"
    manifest = {
        "state": state,
        "list_received": meta is not None,
        "generated_at": datetime.now(UTC).isoformat(),
        "statement": STATEMENT,
        "rows": len(rows),
        "retained_excluded": len(retained),
        "retained_player_ids": retained,
        "confirmed_available": sum(1 for r in rows if r[4]),
        "unresolved_rows_in_list": unresolved,
        "unresolved_warning": (
            "unresolved rows may name retained players who are not yet excluded; "
            "resolve the review queue first" if unresolved else ""
        ),
        "import": None if meta is None else {
            k: (str(v) if k == "snapshot_date" else v) for k, v in meta.items()
        },
        "output_sha256": sha256_file(csv_path),
    }  # fmt: skip
    man_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return manifest
