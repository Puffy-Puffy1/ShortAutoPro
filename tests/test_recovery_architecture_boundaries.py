from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _parse(name: str) -> str:
    path = ROOT / name
    return path.read_text(encoding="utf-8")


def test_recovery_controller_is_bounded_and_canonical():
    source = _parse("production_recovery.py")
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RecoveryController"]
    assert classes, "RecoveryController must be the canonical recovery boundary"
    cls = classes[0]
    max_attempts = next(
        n for n in cls.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "MAX_ATTEMPTS" for t in n.targets)
    )
    assert isinstance(max_attempts.value, ast.Constant)
    assert max_attempts.value.value == 1
    assert "media_stage_runtime.py" not in source
    assert "media_engine_v2.py" not in source


def test_compat_repair_engine_cannot_reenter_retired_stage6():
    source = _parse("shortauto_repair_engine.py")
    assert "media_stage_runtime.py" not in source
    assert "media_engine_v2.py" not in source
    assert "media_acquisition_v3.py" in source


def test_canonical_recovery_has_no_dynamic_legacy_recovery_imports():
    for name in ("production_recovery.py", "shortauto_repair_engine.py"):
        tree = ast.parse(_parse(name))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith("vi6_"), f"{name} imports legacy recovery: {module}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("vi6_"), f"{name} imports legacy recovery: {alias.name}"
