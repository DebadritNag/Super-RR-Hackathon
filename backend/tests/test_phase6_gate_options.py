"""The 0.5 data-weight gate stays 0.5: no code path lowers or bypasses it, and the options table
and report never present a lowered gate as an option."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase4 import eligibility as el
from app.phase5.constants import GATES_CONFIG, REPORTS_DIR
from app.phase6 import context_reliability as cr6
from app.phase6 import data_weight_options as dw
from app.phase6 import eligibility_reliability as er

ROOT = Path(__file__).resolve().parents[1]
PHASE6_CODE = sorted((ROOT / "app" / "phase6").rglob("*.py")) + sorted(
    (ROOT / "scripts").glob("phase6_*.py")
)
ALL_CODE = sorted((ROOT / "app").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))


def _num(node: ast.AST) -> float | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _num(node.operand)
        return None if v is None else -v
    return None


def _name(t: ast.AST) -> str | None:
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Attribute):
        return t.attr
    return None


def _gate_assignments(path: Path, with_sequences: bool) -> list[str]:
    """Assignments of a number below 0.5 (or of a sequence of numbers) to a name with 'gate'."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        pairs: list[tuple[str | None, ast.AST]] = []
        if isinstance(node, ast.Assign):
            pairs = [(_name(t), node.value) for t in node.targets]
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            pairs = [(_name(node.target), node.value)]
        elif isinstance(node, ast.Call):
            pairs = [(k.arg, k.value) for k in node.keywords if k.arg]
        for name, value in pairs:
            if not name or "gate" not in name.lower():
                continue
            v = _num(value)
            if v is not None and v < 0.5:
                hits.append(f"{path.name}:{node.lineno} {name} = {v}")
            if with_sequences and isinstance(value, (ast.Tuple, ast.List, ast.Set)):
                if any((_num(e) is not None and _num(e) < 0.5) for e in value.elts):
                    hits.append(f"{path.name}:{node.lineno} {name} holds a value below 0.5")
    return hits


# ---------------------------------------------------------------- the constant
def test_gate_constant_is_half_everywhere_it_is_read():
    assert el.GATE_B == 0.5
    assert dw.GATE == 0.5 and er.GATE == 0.5 and cr6.GATE == 0.5


def test_gate_is_imported_not_redefined_in_phase6_code():
    for p in PHASE6_CODE:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for t in targets:
                if _name(t) == "GATE_B":
                    pytest.fail(f"{p.name}:{node.lineno} assigns GATE_B")
        text = p.read_text(encoding="utf-8")
        assert "ALT_GATES" not in text, f"{p.name} uses the Phase 4 alternative gates"
        assert "GATE_B =" not in text and "GATE_B=" not in text


def test_no_phase6_code_assigns_a_gate_below_half():
    hits = [h for p in PHASE6_CODE for h in _gate_assignments(p, with_sequences=True)]
    assert hits == []


def test_no_code_in_app_or_scripts_assigns_a_numeric_gate_below_half():
    """Single numbers only: the Phase 4 diagnostic tuple ``ALT_GATES`` is reported in the
    options report as a pre-existing constant that no Phase 6 path reads."""
    hits = [h for p in ALL_CODE for h in _gate_assignments(p, with_sequences=False)]
    assert hits == []


def test_gate_is_only_applied_with_greater_or_equal_to_the_constant():
    """Every comparison with GATE in Phase 6 compares against the constant itself."""
    for p in PHASE6_CODE:
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r">=\s*(0\.\d+)\b", src):
            line = src[: m.start()].count("\n") + 1
            ctx = src.splitlines()[line - 1]
            if "gate" in ctx.lower() or "GATE" in ctx:
                assert float(m.group(1)) >= 0.5, f"{p.name}:{line}: {ctx.strip()}"


def test_gate_files_match_the_guard_written_by_the_options_run():
    guard_path = REPORTS_DIR / "phase6_gate_guard.json"
    if not guard_path.exists():
        pytest.skip("the data-weight options script has not been run")
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    assert guard["gate_value"] == 0.5 and guard["gate_used_in_options"] == [0.5]
    for rel, digest in guard["files_sha256"].items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert got == digest, f"{rel} changed since the options run"


def test_gates_config_has_no_numeric_gate_value():
    cfg = json.loads(GATES_CONFIG.read_text(encoding="utf-8"))
    assert "data_weight_gate_passed" in cfg["gates"]
    assert not [k for k, v in cfg.items() if "gate" in k.lower() and isinstance(v, (int, float))]


# ---------------------------------------------------------------- the options table validator
def _row(**kw):
    base = dw.option_row(option_id="O1_x", label="ACTUAL_RE_ESTIMATE", scope="cell:IPL|batter",
                         window="PRE_TEST", k_source="PHASE4_FLOOR_TAU4", data_weight=0.1)  # fmt: skip
    base.update(kw)
    return base


def _table(*rows):
    return pd.DataFrame(list(rows))


def test_valid_table_passes():
    dw.validate_options_table(
        _table(_row(), _row(option_id="O7_x", label="DESCRIPTIVE_PROJECTION"))
    )


def test_option_row_always_uses_the_gate_constant():
    assert dw.option_row(option_id="x", gate_used=0.1)["gate_used"] == 0.5
    assert dw.option_row(option_id="x", gate_used=0.0)["gate_used"] == dw.GATE


def test_a_lowered_gate_in_a_row_is_rejected():
    bad = _row()
    bad["gate_used"] = 0.3
    with pytest.raises(dw.OptionsTableError, match="0.5"):
        dw.validate_options_table(_table(_row(), bad))


@pytest.mark.parametrize(
    "option_id",
    ["O9_lower_gate", "O9_relax_threshold", "O9_bypass", "O9_tau_multiplier", "O9_gate_0.3",
     "O9_TAU_MULT", "O9_Lower"],
)  # fmt: skip
def test_forbidden_option_ids_are_rejected(option_id):
    with pytest.raises(dw.OptionsTableError, match="forbidden option"):
        dw.validate_options_table(_table(_row(option_id=option_id)))


def test_assumed_multiplier_k_source_is_rejected():
    with pytest.raises(dw.OptionsTableError, match="ASSUMED_MULTIPLIER"):
        dw.validate_options_table(_table(_row(k_source="ASSUMED_MULTIPLIER")))


def test_missing_label_or_unknown_label_is_rejected():
    with pytest.raises(dw.OptionsTableError, match="label"):
        dw.validate_options_table(_table(_row(label="VALIDATED")))


def test_match_cluster_k_must_pair_with_cluster_basis():
    ok = _row(k_source="MATCH_CLUSTER_REML_OWN_CONTEXT", n_eff_basis="MATCH_CLUSTER")
    dw.validate_options_table(_table(ok))
    with pytest.raises(dw.OptionsTableError, match="match-cluster"):
        dw.validate_options_table(_table(_row(k_source="MATCH_CLUSTER_REML_OWN_CONTEXT")))
    with pytest.raises(dw.OptionsTableError, match="match-cluster"):
        dw.validate_options_table(_table(_row(n_eff_basis="MATCH_CLUSTER")))


def test_missing_required_column_is_rejected():
    with pytest.raises(dw.OptionsTableError, match="lacks columns"):
        dw.validate_options_table(_table(_row()).drop(columns=["passes_gate"]))


# ---------------------------------------------------------------- the stored options and report
def _stored_options():
    p = REPORTS_DIR / "phase6_data_weight_improvement_options.csv"
    if not p.exists():
        pytest.skip("the data-weight options script has not been run")
    return pd.read_csv(p)


def test_stored_options_pass_the_validator_and_use_gate_half():
    df = _stored_options()
    dw.validate_options_table(df)
    assert set(df["gate_used"]) == {0.5}
    assert not df["option_id"].str.contains(dw.FORBIDDEN_ID).any()


def test_stored_options_are_labelled_and_basis_is_consistent():
    df = _stored_options()
    assert set(df["label"]) <= set(dw.LABELS)
    cluster = df["option_id"].str.startswith(("O3_", "O6_"))
    assert (df.loc[cluster, "n_eff_basis"] == "MATCH_CLUSTER").all()
    assert (df.loc[~cluster, "n_eff_basis"] == "KISH_MATCH").all()
    assert df.loc[cluster, "requires_methodology_decision"].astype(bool).all()
    assert df.loc[df["option_id"].str.startswith("O8_"), "applicable"].astype(bool).eq(False).all()


def test_stored_gate_status_never_changes_the_stored_state():
    p = REPORTS_DIR / "phase6_data_weight_improvement_options_gate_status.csv"
    if not p.exists():
        pytest.skip("the data-weight options script has not been run")
    gs = pd.read_csv(p)
    assert set(gs["gate_used"]) == {0.5} and len(gs) == 48
    # the stored Phase 5 state is copied, and a failing context stays RESTRICTED
    stored = gs["data_weight_gate_passed"].astype(bool)
    assert (gs["stored_state"] == stored.map({True: "PASS", False: "RESTRICTED"})).all()
    assert not stored.any()  # none of the 48 contexts passes in the stored state
    assert (gs.loc[~stored, "stored_state"] == "RESTRICTED").all()


def test_report_lists_no_lowered_gate_option():
    p = REPORTS_DIR / "phase6_data_weight_improvement_options.md"
    if not p.exists():
        pytest.skip("the data-weight options script has not been run")
    text = p.read_text(encoding="utf-8")
    section = text.split("## 3. Summary per option")[1].split("## 4.")[0]
    ids = re.findall(r"^\| (O\d\w*)", section, flags=re.M)
    assert ids, "no option rows found in the summary section"
    assert not [i for i in ids if dw.FORBIDDEN_ID.search(i)]
    excluded = text.split("## 2. Excluded by rule")[1].split("## 3.")[0]
    assert "lowering the 0.5 gate" in excluded  # named as excluded, not as an option
    assert "GATE_B` = 0.5" in text
    assert not re.search(r"gate[^\n]{0,40}\b0\.[0-4]\d*\b[^\n]{0,20}option", text, flags=re.I)


# ---------------------------------------------------------------- helpers on synthetic data
def test_kish_stats_marginal_individual_and_gap():
    est = pd.DataFrame({"n_eff": [1.0, 4.0, 30.0], "matches": [1, 6, 40]})
    s = dw.kish_stats(est, np.array([True, True, True]), 25.0)
    assert s["n_eff_marginal"] == 1.0 and s["data_weight"] == pytest.approx(1 / 26)
    assert s["extra_n_eff_required"] == 24.0 and s["extra_matches_required"] == 24.0
    assert s["pool_n_eff_at_least_k"] == 1
    assert dw.kish_stats(est, np.array([False] * 3), 25.0) == {"eligible": 0}


def test_cluster_b_is_tau2_over_tau2_plus_noise_and_k_matches():
    out = dw.cluster_b(0.2, np.array([0.1, 0.8, float("nan")]), 4.0)
    assert out["data_weight"] == pytest.approx(0.2 / (0.2 + 0.8))
    assert out["k_used"] == pytest.approx(4.0 / 0.2)
    assert out["n_eff_marginal"] == pytest.approx(4.0 / 0.8)
    # B = n_eff / (n_eff + k) holds on this basis
    assert out["data_weight"] == pytest.approx(
        out["n_eff_marginal"] / (out["n_eff_marginal"] + out["k_used"])
    )
    assert out["players_used"] == 2
    assert dw.cluster_b(0.0, np.array([0.5]), 1.0)["data_weight"] == 0.0
    assert dw.cluster_b(None, np.array([0.5]), 1.0)["status"] == "NOT_ESTIMABLE"


def test_parent_contexts():
    assert dw.parent_of("powerplay", "chase", "phases_pooled") == ("ALL", "chase")
    assert dw.parent_of("ALL", "chase", "phases_pooled") is None
    assert dw.parent_of("death", "chase", "situations_pooled") == ("death", "ALL")
    assert dw.parent_of("death", "ALL", "situations_pooled") is None
    with pytest.raises(ValueError):
        dw.parent_of("death", "ALL", "other")


def test_mad_tau2_is_robust_to_an_outlier():
    rng = np.random.default_rng(0)
    y = rng.normal(0, 0.5, 200)
    v = np.full(200, 0.04)
    clean = dw.mad_tau2(y, v)
    y2 = y.copy()
    y2[0] = 50.0
    assert dw.mad_tau2(y2, v) == pytest.approx(clean, rel=0.05)
    assert clean == pytest.approx(0.25 - 0.04, abs=0.06)
    assert dw.mad_tau2(np.zeros(5), v[:5]) == 0.0  # floor at zero


def test_summary_counts_passes_and_lists_scopes():
    df = _table(
        _row(option_id="O3_a", scope="context:a", passes_gate=True, data_weight=0.6),
        _row(option_id="O3_a", scope="context:b", passes_gate=False, data_weight=0.1),
        _row(option_id="O7_b", scope="context:a", label="DESCRIPTIVE_PROJECTION", data_weight=0.2),
    )
    s = dw.summarize(df).set_index("option_id")
    assert s.loc["O3_a", "rows"] == 2 and s.loc["O3_a", "rows_passing_gate"] == 1
    assert s.loc["O3_a", "passing_scopes"] == "context:a"
    assert s.loc["O7_b", "passing_scopes"] == "none"
    assert (s["gate_used"] == 0.5).all()
