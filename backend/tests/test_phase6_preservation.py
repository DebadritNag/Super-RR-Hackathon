"""Phase 6 preservation: official data and Phase 4/5 artefacts byte-identical, TEST untouched,
no Cricsheet in scoring modules, the gate and thresholds unchanged.

Hash checks compare against ``.agents/tasks/phase6_prerun_hashes.json`` (written before Phase 6
started) and are skipped when that record or the real data is absent. ``exploratory.duckdb`` itself
is excluded (it holds the p6_ tables); its p4_/p5_ tables are compared separately.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from app.core.config import BACKEND_ROOT
from app.phase5.constants import REPORTS_DIR
from app.phase5.lockguard import PHASE5_LOCK_LOG, read_events
from app.phase6 import store as p6store
from app.services.pressure_service import EXPLORATORY_DB

PRERUN = BACKEND_ROOT.parent / ".agents" / "tasks" / "phase6_prerun_hashes.json"
APP = BACKEND_ROOT / "app"
SCRIPTS = BACKEND_ROOT / "scripts"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def prerun() -> dict:
    if not PRERUN.is_file():
        pytest.skip("pre-run hash record not available")
    return json.loads(PRERUN.read_text(encoding="utf-8-sig"))["files"]


def _check(prerun: dict, pick) -> int:
    n = 0
    for path, rec in prerun.items():
        p = Path(path)
        if p.name == "exploratory.duckdb" or not pick(p):
            continue
        if not p.is_file():
            pytest.skip(f"{p} is not present")
        assert _sha(p) == rec["sha256"].lower(), f"{p.name} changed"
        n += 1
    return n


def test_official_database_and_source_csvs_unchanged(prerun):
    n = _check(prerun, lambda p: p.name == "superr.duckdb" or p.suffix == ".csv"
               and "reports" not in p.parts)  # fmt: skip
    assert n >= 10


def test_phase4_report_files_byte_identical(prerun):
    assert _check(prerun, lambda p: p.name.startswith("phase4_")) >= 50


def test_phase5_report_files_byte_identical(prerun):
    assert _check(prerun, lambda p: p.name.startswith("phase5_")) >= 50


def test_every_prerun_file_except_the_store_is_unchanged(prerun):
    assert _check(prerun, lambda p: True) >= 100


def test_phase4_and_phase5_tables_exist_and_are_stable_between_reads():
    if not EXPLORATORY_DB.is_file():
        pytest.skip("exploratory store not present")
    a = p6store.table_hashes(EXPLORATORY_DB, "p4_")
    b = p6store.table_hashes(EXPLORATORY_DB, "p5_")
    assert len(a) >= 20 and len(b) >= 10
    assert p6store.table_hashes(EXPLORATORY_DB, "p4_") == a
    assert p6store.table_hashes(EXPLORATORY_DB, "p5_") == b


def test_no_phase6_run_wrote_a_new_test_lock_event():
    p4 = REPORTS_DIR / "phase4_lock_log.json"
    if not p4.is_file():
        pytest.skip("phase4 lock log not present")
    assert [e["event"] for e in read_events(p4)] == ["FREEZE", "OPEN", "CLOSE"]
    assert read_events(PHASE5_LOCK_LOG) == []


def test_phase6_never_writes_phase4_or_phase5_names():
    for path in [*sorted((APP / "phase6").glob("*.py")), *sorted(SCRIPTS.glob("*phase6*.py"))]:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if fn in {"write_p4_table", "write_p5_table"}:
                    pytest.fail(f"{path.name} calls {fn}")
        for banned in ("write_p4_table", "write_p5_table"):
            assert f"import {banned}" not in text


def test_p6_writer_rejects_other_prefixes_and_the_official_database(tmp_path):
    import pandas as pd

    df = pd.DataFrame({"a": [1]})
    with pytest.raises(p6store.StoreError):
        p6store.write_p6_table(df, "p5_x", tmp_path / "s.duckdb")
    with pytest.raises(p6store.StoreError):
        p6store.write_p6_table(df, "p4_x", tmp_path / "s.duckdb")
    with pytest.raises(p6store.StoreError):
        p6store.write_p6_table(df, "p6_x", p6store.OFFICIAL_DB, p6store.OFFICIAL_DB)


# ---------------------------------------------------------------- no Cricsheet in scoring
FORBIDDEN_IMPORTS = ("cricsheet_auditor", "cricsheet_super_over")
FORBIDDEN_LITERALS = ("_male_json", "cricsheet_index", "staging/")
DATE_VERIFICATION = APP / "phase5" / "date_verification.py"


def _docstrings(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) \
                    and isinstance(b[0].value.value, str):  # fmt: skip
                ids.add(id(b[0].value))
    return ids


def _scan(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstrings(tree)
    hits = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *[a.name for a in node.names]]
        hits += [f"import {n}" for n in names if any(f in n for f in FORBIDDEN_IMPORTS)]
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip \
                and any(f in node.value for f in FORBIDDEN_LITERALS):  # fmt: skip
            hits.append(f"literal {node.value[:40]!r}")
    return hits


def _scoring_and_phase6_modules() -> list[Path]:
    mods = sorted((APP / "phase4").glob("*.py")) + sorted((APP / "phase5").glob("*.py"))
    mods += sorted((APP / "phase6").glob("*.py")) + sorted((APP / "repositories").glob("*.py"))
    mods += sorted((APP / "services").glob("*.py")) + sorted(SCRIPTS.glob("*phase6*.py"))
    mods += [SCRIPTS / "run_phase6.py"]
    return sorted({m for m in mods if m.is_file() and m != DATE_VERIFICATION})


def test_no_cricsheet_loader_or_path_in_scoring_or_phase6_modules():
    bad = {m.name: h for m in _scoring_and_phase6_modules() if (h := _scan(m))}
    assert bad == {}


def test_no_cricsheet_word_in_phase6_code_outside_comments_of_the_label():
    # Phase 6 may say "Cricsheet: not used" in docs and reports, never import or open it.
    for m in sorted((APP / "phase6").glob("*.py")):
        tree = ast.parse(m.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = (node.module or "") if isinstance(node, ast.ImportFrom) else ""
                names = [a.name for a in node.names] + [mod]
                assert not any("cricsheet" in n.lower() for n in names), m.name


def test_phase6_never_imports_a_test_opening_function():
    banned = ("evaluate_on_test", "_open_for_evaluation", "LockedFrame", "test_eval",
              "load_test_match_outcomes")  # fmt: skip
    for m in [*sorted((APP / "phase6").glob("*.py")), *sorted(SCRIPTS.glob("*phase6*.py")),
              SCRIPTS / "run_phase6.py"]:  # fmt: skip
        tree = ast.parse(m.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = [node.module or "", *[a.name for a in node.names]]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            for n in names:
                assert not any(b in n for b in banned), f"{m.name} imports {n}"


def test_gate_value_unchanged_and_never_assigned_below_half_in_phase6_code():
    from app.phase4 import eligibility as el

    assert el.GATE_B == 0.5
    for m in [*sorted((APP / "phase6").glob("*.py")), *sorted(SCRIPTS.glob("*phase6*.py")),
              SCRIPTS / "run_phase6.py"]:  # fmt: skip
        for node in ast.walk(ast.parse(m.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    nm = t.id if isinstance(t, ast.Name) else getattr(t, "attr", "")
                    if "gate" in nm.lower() and isinstance(node.value, ast.Constant) \
                            and isinstance(node.value.value, (int, float)) \
                            and not isinstance(node.value.value, bool):  # fmt: skip
                        assert node.value.value >= 0.5, f"{m.name}:{node.lineno} lowers {nm}"


def test_orchestrator_order_runs_every_phase6_script_and_never_creates_a_lock():
    text = (SCRIPTS / "run_phase6.py").read_text(encoding="utf-8")
    steps = [p.name for p in sorted(SCRIPTS.glob("phase6_*.py"))]
    assert len(steps) >= 12
    for s in steps:
        assert s in text, f"{s} is not run by the orchestrator"
    assert "--confirm-lock" not in text and "--create-lock" not in text
    assert text.index("phase6_investigation_plan.py") < text.index("phase6_variance_floor.py")
    assert text.index("phase6_reports.py") > text.index("phase6_season_robustness.py")


def test_orchestrator_hashes_mask_only_the_run_log_sequence_number():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_phase6", SCRIPTS / "run_phase6.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a = mod.SEQ.sub(rb"\1N", b"x run-log seq 33 for this step")
    b = mod.SEQ.sub(rb"\1N", b"x run-log seq 7 for this step")
    assert a == b
    c = mod.SEQ.sub(rb"\1N", b"value 0.33 for this step")
    assert c == b"value 0.33 for this step"
