"""Discover expected datasets in the workspace (read-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExpectedFile:
    name: str
    expected_rows: int | None
    expected_cols: int | None
    role: str = "core"


EXPECTED_CSVS: dict[str, ExpectedFile] = {
    "competitions.csv": ExpectedFile("competitions.csv", 141, 4),
    "teams.csv": ExpectedFile("teams.csv", 353, 3),
    "matches.csv": ExpectedFile("matches.csv", 883, 22),
    "playing_eleven.csv": ExpectedFile("playing_eleven.csv", 28381, 9),
    "competition_team_player_mapping.csv": ExpectedFile(
        "competition_team_player_mapping.csv", 6413, 6
    ),
    "ball_by_ball.csv": ExpectedFile("ball_by_ball.csv", 200999, 33),
    "ipl squad.csv": ExpectedFile("ipl squad.csv", None, 6, "squad"),
}

# Known supplementary files that are not in the original spec list.
SUPPLEMENTARY_CSVS: dict[str, str] = {
    "updated_ball_by_ball.csv": "alternative ball-by-ball file",
    "matches 2026.csv": "2026 match summary (different schema)",
    "batting_stats2026.csv": "2026 batting aggregates",
    "bowling_stats2026.csv": "2026 bowling aggregates",
    "fielding_stats2026.csv": "2026 fielding aggregates",
}

# Directory name -> spec file count (order from the brief).
EXPECTED_JSON_DIRS: dict[str, int] = {
    "ipl_male_json": 1243,
    "t20s_male_json": 3649,
    "it20s_male_json": 240,
    "bbl_male_json": 662,
    "cpl_male_json": 445,
    "mlc_male_json": 109,
    "india_male_json": 1037,
    "2026_male_json": 1619,
}


@dataclass
class DiscoveryResult:
    found: dict[str, Path] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    supplementary: dict[str, Path] = field(default_factory=dict)
    extras: list[str] = field(default_factory=list)
    json_dirs: dict[str, dict] = field(default_factory=dict)
    missing_json_dirs: list[str] = field(default_factory=list)
    pdfs: list[Path] = field(default_factory=list)


def find_problem_statement_pdf(root: Path) -> Path | None:
    pdfs = sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    return pdfs[0] if pdfs else None


def discover_datasets(root: Path, cricsheet_root: Path | None = None) -> DiscoveryResult:
    cricsheet_root = cricsheet_root or root
    res = DiscoveryResult()
    by_lower = {p.name.lower(): p for p in root.iterdir()}
    expected_lower = {k.lower(): k for k in EXPECTED_CSVS}
    supp_lower = {k.lower(): k for k in SUPPLEMENTARY_CSVS}
    for lower, key in expected_lower.items():
        if lower in by_lower:
            res.found[key] = by_lower[lower]
        else:
            res.missing.append(key)
    for lower, key in supp_lower.items():
        if lower in by_lower:
            res.supplementary[key] = by_lower[lower]
    for lower, p in sorted(by_lower.items()):
        if p.is_dir():
            continue
        if lower in expected_lower or lower in supp_lower:
            continue
        if p.suffix.lower() == ".pdf":
            res.pdfs.append(p)
        res.extras.append(p.name)
    for name in EXPECTED_JSON_DIRS:
        d = cricsheet_root / name
        if d.is_dir():
            files = list(d.iterdir())
            json_files = [f for f in files if f.suffix.lower() == ".json"]
            res.json_dirs[name] = {
                "path": d,
                "total_files": len(files),
                "json_files": len(json_files),
                "txt_files": [f.name for f in files if f.suffix.lower() == ".txt"],
                "other_files": [f.name for f in files if f.suffix.lower() not in (".json", ".txt")],
            }
        else:
            res.missing_json_dirs.append(name)
    return res
