"""Phase 5 classification: three real ``international_status`` values.

The real values are VERIFIED_CAPPED, DERIVED_CAPPED and UNKNOWN. VERIFIED_UNCAPPED is a DISABLED
PLACEHOLDER, not an established fourth status: no authoritative source exists, strict uncapped
selection is disabled, and it can only be stored through a validated override row.
VERIFIED_CAPPED exists only through a validated override row or an authoritative source.
DERIVED_CAPPED is data-proven (a player appeared for a national team in an official T20I in the
data on or before the as-of date). UNKNOWN means "not proven capped in the data" and is never
"uncapped". Nothing here reads names, domestic or IPL records: the module takes a classification
frame (built from T20I appearances by ``app.phase4.classification``) and migrates its labels.

The Phase 4 labels are migrated by an explicit mapping (``MIGRATION_MAP``). An unmapped
combination is fatal; there is no silent relabel.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.phase4 import classification as cl
from app.phase5.constants import CLASSIFICATION_V2_CONFIG, CLASSIFICATION_V2_VERSION

ClassificationConfigError = cl.ClassificationConfigError

VERIFIED_CAPPED = "VERIFIED_CAPPED"
DERIVED_CAPPED = "DERIVED_CAPPED"
VERIFIED_UNCAPPED = "VERIFIED_UNCAPPED"
UNKNOWN = "UNKNOWN"
# The three real values. Used for the public enum, reported counts and the capabilities list.
STATUS_VALUES = (VERIFIED_CAPPED, DERIVED_CAPPED, UNKNOWN)
# Disabled placeholder: kept so the strict-uncapped filter and the override mechanism still work.
DISABLED_PLACEHOLDER_VALUES = (VERIFIED_UNCAPPED,)
# Everything a stored or overridden value may be (three real values + the disabled placeholder).
ACCEPTED_STORED_VALUES = STATUS_VALUES + DISABLED_PLACEHOLDER_VALUES
CAPPED_VALUES = (VERIFIED_CAPPED, DERIVED_CAPPED)
VERIFIED_VALUES = (VERIFIED_CAPPED, VERIFIED_UNCAPPED)
UNKNOWN_STATUS_LABEL = "UNKNOWN_STATUS"
UNKNOWN_STATUS_BANNER = "NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED"
LEGACY_STATUSES = ("Capped", "Uncapped", "Unknown")

# (Phase 4 status, Phase 4 verification label) -> Phase 5 status. The only allowed combinations.
MIGRATION_MAP: dict[tuple[str, str], str] = {
    ("Capped", cl.V_T20I): DERIVED_CAPPED,
    ("Capped", cl.V_SOURCE): VERIFIED_CAPPED,
    ("Uncapped", cl.V_SOURCE): VERIFIED_UNCAPPED,
    ("Unknown", cl.V_NONE): UNKNOWN,
}
# Legacy status -> Phase 5 statuses it may become (used for the count assertions).
_LEGACY_TO_NEW = {
    "Capped": (DERIVED_CAPPED, VERIFIED_CAPPED),
    "Uncapped": (VERIFIED_UNCAPPED,),
    "Unknown": (UNKNOWN,),
}
OVERRIDE_STATUS_VALUES = (VERIFIED_CAPPED, VERIFIED_UNCAPPED)
OVERRIDE_NATIONALITY_VALUES = ("Indian", "Overseas")
PLACEHOLDERS = {"tbd", "unknown", "n/a", "na", "none", "todo", "?"}


class ClassificationMigrationError(ValueError):
    """Raised when a Phase 4 label combination has no entry in the migration map."""


def load_config(path: Path | str = CLASSIFICATION_V2_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def status_display(status: str) -> str:
    """UNKNOWN is shown only as the clearly labelled group UNKNOWN_STATUS."""
    return UNKNOWN_STATUS_LABEL if status == UNKNOWN else status


# ----------------------------------------------------------------------------- migration


def migration_map_frame() -> pd.DataFrame:
    """The explicit mapping as a table (stored as ``p5_classification_migration_map``)."""
    return pd.DataFrame(
        [
            {"phase4_status": s, "phase4_verification": v, "phase5_status": n}
            for (s, v), n in MIGRATION_MAP.items()
        ]
    )


def migrate_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Map Phase 4 labels to the Phase 5 enum. Fatal on any unmapped combination."""
    for col in ("player_id", "international_status", "international_status_verification"):
        if col not in df.columns:
            raise ClassificationMigrationError(f"input is missing column '{col}'")
    if df["player_id"].duplicated().any():
        raise ClassificationMigrationError("duplicate player_id in the classification input")
    keys = list(
        zip(df["international_status"], df["international_status_verification"], strict=True)
    )
    bad = [i for i, k in enumerate(keys) if k not in MIGRATION_MAP]
    if bad:
        ids = [int(p) for p in df["player_id"].iloc[bad][:20]]
        combos = sorted({keys[i] for i in bad})
        raise ClassificationMigrationError(
            f"{len(bad)} players have an unmapped (status, verification) combination {combos}; "
            f"first player ids: {ids}"
        )
    out = df.copy()
    out["legacy_international_status"] = df["international_status"]
    out["international_status"] = [MIGRATION_MAP[k] for k in keys]
    out["status_reason"] = out.get("international_status_unknown_reason")
    out["status_display"] = [status_display(s) for s in out["international_status"]]
    out["derived_evidence"] = [
        cl.V_T20I if s == DERIVED_CAPPED else None for s in out["international_status"]
    ]
    out["migration_version"] = CLASSIFICATION_V2_VERSION
    _assert_counts(df, out)
    return out


def _assert_counts(legacy: pd.DataFrame, new: pd.DataFrame) -> None:
    if len(legacy) != len(new):
        raise ClassificationMigrationError("row count changed during migration")
    old_counts = Counter(legacy["international_status"])
    new_counts = Counter(new["international_status"])
    for old, targets in _LEGACY_TO_NEW.items():
        if old_counts.get(old, 0) != sum(new_counts.get(t, 0) for t in targets):
            raise ClassificationMigrationError(f"count mismatch for legacy status '{old}'")
    if set(new_counts) - set(ACCEPTED_STORED_VALUES):
        raise ClassificationMigrationError("migration produced a value outside the enum")


def assert_matches_phase4_coverage(migrated: pd.DataFrame, phase4_cov: dict[str, Any]) -> dict:
    """Compare migrated counts with the stored Phase 4 coverage JSON; fatal on a mismatch."""
    combos = phase4_cov["combinations_all_players"]
    p4 = Counter()
    for c in combos:
        p4[c["international_status"]] += int(c["players"])
    new = Counter(migrated["international_status"])
    result = {
        "phase4_capped": p4["Capped"],
        "phase4_uncapped": p4["Uncapped"],
        "phase4_unknown": p4["Unknown"],
        "phase5_capped_total": new[VERIFIED_CAPPED] + new[DERIVED_CAPPED],
        "phase5_verified_uncapped": new[VERIFIED_UNCAPPED],
        "phase5_unknown": new[UNKNOWN],
        "players_total": int(phase4_cov["players_total"]),
    }
    ok = (
        result["phase4_capped"] == result["phase5_capped_total"]
        and result["phase4_uncapped"] == result["phase5_verified_uncapped"]
        and result["phase4_unknown"] == result["phase5_unknown"]
        and result["players_total"] == len(migrated)
    )
    if not ok:
        raise ClassificationMigrationError(f"Phase 4 coverage mismatch: {result}")
    return result


# ----------------------------------------------------------------------------- overrides


def validate_overrides_v2(
    raw: pd.DataFrame, base: pd.DataFrame, today: date | None = None
) -> pd.DataFrame:
    """Validate override rows against the migrated base table; collect every row error."""
    today = today or date.today()
    if list(raw.columns) != list(cl.OVERRIDE_COLUMNS):
        raise ClassificationConfigError(
            f"override columns must be exactly {list(cl.OVERRIDE_COLUMNS)}, got {list(raw.columns)}"
        )
    known = {int(p) for p in base["player_id"]}
    derived = {
        int(p)
        for p, s in zip(base["player_id"], base["international_status"], strict=True)
        if s == DERIVED_CAPPED
    }
    errors: list[str] = []
    seen: set[tuple[int, str]] = set()
    rows: list[dict[str, Any]] = []
    for i, r in raw.iterrows():
        line = int(i) + 2

        def err(code: str, msg: str, line: int = line) -> None:
            errors.append(f"line {line}: {code}: {msg}")

        pid = None
        try:
            pid = int(str(r["player_id"]).strip())
        except ValueError:
            err("UNKNOWN_PLAYER_ID", f"player_id '{r['player_id']}' is not an integer")
        if pid is not None and pid not in known:
            err("UNKNOWN_PLAYER_ID", f"player_id {pid} is not in the classification table")
        field = str(r["field"]).strip()
        value = str(r["value"]).strip()
        if field not in cl.OVERRIDE_FIELDS:
            err("INVALID_FIELD", f"field '{field}' must be one of {list(cl.OVERRIDE_FIELDS)}")
        elif field == "international_status":
            if value in ("Capped", "Uncapped"):
                err(
                    "LEGACY_STATUS_VALUE",
                    f"'{value}' is a Phase 4 label; use VERIFIED_CAPPED or VERIFIED_UNCAPPED "
                    "(mapping in docs/frontend_backend_contracts.md)",
                )
            elif value not in OVERRIDE_STATUS_VALUES:
                err("INVALID_VALUE", f"'{value}' must be one of {list(OVERRIDE_STATUS_VALUES)}")
        elif value not in OVERRIDE_NATIONALITY_VALUES:
            err("INVALID_VALUE", f"'{value}' must be one of {list(OVERRIDE_NATIONALITY_VALUES)}")
        source = str(r["source"]).strip()
        if not source or source.casefold() in PLACEHOLDERS:
            err("MISSING_SOURCE", "source must be a real, non-placeholder reference")
        if not str(r["verified_by"]).strip():
            err("MISSING_VERIFIED_BY", "verified_by must not be empty")
        vd = str(r["verified_date"]).strip()
        try:
            parsed = date.fromisoformat(vd)
            if parsed > today:
                err("MISSING_OR_BAD_VERIFIED_DATE", f"verified_date {vd} is in the future")
        except ValueError:
            err("MISSING_OR_BAD_VERIFIED_DATE", f"verified_date '{vd}' is not ISO YYYY-MM-DD")
        if pid is not None:
            if (pid, field) in seen:
                err("DUPLICATE_OVERRIDE", f"more than one override for ({pid}, {field})")
            seen.add((pid, field))
            if field == "international_status" and value == VERIFIED_UNCAPPED and pid in derived:
                err(
                    "CONTRADICTS_DERIVED_EVIDENCE",
                    f"player {pid} is DERIVED_CAPPED from T20I appearances; a human must resolve "
                    "the contradiction before VERIFIED_UNCAPPED can be applied",
                )
        rows.append(
            {
                "player_id": pid,
                "field": field,
                "value": value,
                "source": source,
                "verified_by": str(r["verified_by"]).strip(),
                "verified_date": vd,
            }
        )
    if errors:
        raise ClassificationConfigError("; ".join(errors))
    out = pd.DataFrame(rows, columns=list(cl.OVERRIDE_COLUMNS))
    if len(out):
        out["player_id"] = out["player_id"].astype("int64")
    return out


def load_overrides_v2(
    path: Path | str, base: pd.DataFrame, today: date | None = None
) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    return validate_overrides_v2(raw, base, today)


def apply_overrides_v2(base: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Overrides win for the named player and field only; derived evidence is kept alongside."""
    out = base.copy()
    for col in (
        "nationality_verified_by",
        "nationality_verified_date",
        "status_verified_by",
        "status_verified_date",
    ):
        out[col] = None
    if overrides is None or overrides.empty:
        return out
    for o in overrides.itertuples(index=False):
        mask = out["player_id"] == o.player_id
        if not mask.any():
            continue
        if o.field == "nationality":
            previous = out.loc[mask, "nationality"].iloc[0]
            prev_ver = out.loc[mask, "nationality_verification"].iloc[0]
            if prev_ver != cl.V_NONE and previous not in ("Unknown", o.value):
                out.loc[mask, "conflict_flag"] = True
            out.loc[mask, "nationality"] = o.value
            out.loc[mask, "nationality_verification"] = cl.V_SOURCE
            out.loc[mask, "nationality_source"] = f"MANUAL_OVERRIDE:{o.source}"
            out.loc[mask, "nationality_unknown_reason"] = None
            out.loc[mask, "nationality_verified_by"] = o.verified_by
            out.loc[mask, "nationality_verified_date"] = o.verified_date
        else:
            out.loc[mask, "international_status"] = o.value
            out.loc[mask, "international_status_verification"] = cl.V_SOURCE
            out.loc[mask, "international_status_source"] = f"MANUAL_OVERRIDE:{o.source}"
            out.loc[mask, "international_status_unknown_reason"] = None
            out.loc[mask, "status_reason"] = None
            out.loc[mask, "status_display"] = status_display(o.value)
            out.loc[mask, "status_verified_by"] = o.verified_by
            out.loc[mask, "status_verified_date"] = o.verified_date
    return out


# ----------------------------------------------------------------------------- coverage


def coverage_v2(cls: pd.DataFrame, scored_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Counts per nationality x real status (3 x 3 combinations) and per real status.

    The disabled placeholder VERIFIED_UNCAPPED is not a status row; its stored count is reported
    separately in ``disabled_placeholder_counts``.
    """

    def combos(df: pd.DataFrame) -> list[dict[str, Any]]:
        c = Counter(zip(df["nationality"], df["international_status"], strict=True))
        return [
            {"nationality": n, "international_status": s, "players": int(c.get((n, s), 0))}
            for n in cl.NATIONALITIES
            for s in STATUS_VALUES
        ]

    def tally(df: pd.DataFrame, col: str) -> dict[str, int]:
        return {str(k): int(v) for k, v in df[col].value_counts(dropna=False).items()}

    by_status = {s: int((cls["international_status"] == s).sum()) for s in STATUS_VALUES}
    placeholder_counts = {
        s: int((cls["international_status"] == s).sum()) for s in DISABLED_PLACEHOLDER_VALUES
    }
    out: dict[str, Any] = {
        "classification_version": CLASSIFICATION_V2_VERSION,
        "players_total": int(len(cls)),
        "status_counts": by_status,
        "disabled_placeholder_counts": placeholder_counts,
        "combinations_all_players": combos(cls),
        "nationality_verification": tally(cls, "nationality_verification"),
        "status_verification": tally(cls, "international_status_verification"),
        "nationality_unknown_reasons": tally(
            cls[cls["nationality"] == "Unknown"], "nationality_unknown_reason"
        ),
        "status_unknown_reasons": tally(
            cls[cls["international_status"] == UNKNOWN], "status_reason"
        ),
        "verified_capped_count": by_status[VERIFIED_CAPPED],
        "derived_capped_count": by_status[DERIVED_CAPPED],
        "uncapped_verified_count": placeholder_counts[VERIFIED_UNCAPPED],
        "unknown_status_count": by_status[UNKNOWN],
        "unknown_status_label": UNKNOWN_STATUS_LABEL,
        "unknown_status_banner": UNKNOWN_STATUS_BANNER,
        "conflicts": int(cls["conflict_flag"].sum()),
    }
    if scored_ids is not None:
        ids = {int(i) for i in scored_ids}
        sub = cls[cls["player_id"].isin(ids)]
        out["scored_players_total"] = int(len(sub))
        out["combinations_scored_players"] = combos(sub)
    return out


# ----------------------------------------------------------------------------- capability


def load_source_manifest(path: Path | str) -> dict[str, Any]:
    """Read the declared-source manifest. A missing or malformed file fails closed."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        sources = data["sources"]
        if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
            raise ValueError("sources must be a list of objects")
        return {"sources": sources, "malformed": False}
    except (OSError, ValueError, KeyError, TypeError):
        return {"sources": [], "malformed": True}


def strict_uncapped_capability(
    classification: pd.DataFrame,
    manifest: dict[str, Any],
    scored_ids: Iterable[int],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Computed capability flag. It is never stored or edited by hand; it fails closed."""
    reasons: list[str] = []
    if manifest.get("malformed"):
        reasons.append("MANIFEST_MALFORMED")
    authoritative = [
        s
        for s in manifest.get("sources", [])
        if s.get("authoritative") is True and s.get("id_keyed") is True
    ]
    if not authoritative:
        reasons.append("NO_AUTHORITATIVE_SOURCE")
    verified_rows = int(
        (
            classification["international_status"].isin(VERIFIED_VALUES)
            & (classification["international_status_verification"] == cl.V_SOURCE)
        ).sum()
    )
    if verified_rows == 0:
        reasons.append("NO_VERIFIED_ROWS")
    ids = {int(i) for i in scored_ids}
    pool = classification[classification["player_id"].isin(ids)]
    verified_in_pool = int(
        (
            pool["international_status"].isin(VERIFIED_VALUES)
            & (pool["international_status_verification"] == cl.V_SOURCE)
        ).sum()
    )
    coverage = verified_in_pool / len(pool) if len(pool) else 0.0
    minimum = float(cfg["min_verified_coverage"])
    if coverage < minimum:
        reasons.append("COVERAGE_BELOW_MINIMUM")
    return {
        "enabled": not reasons,
        "reasons": reasons,
        "source_needed": cfg["source_needed"],
        "verified_coverage": round(coverage, 6),
        "min_verified_coverage": minimum,
        "scored_pool_size": int(len(pool)),
        "verified_rows": verified_rows,
        "authoritative_sources": len(authoritative),
    }
