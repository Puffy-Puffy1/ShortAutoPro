from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _parse(name: str) -> str:
    path = ROOT / name
    return path.read_text(encoding="utf-8")


def test_recovery_controller_is_bounded_and_canonical():
    controller_source = _parse("recovery_controller.py")
    tree = ast.parse(controller_source)
    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RecoveryController"
    ]
    assert classes, "RecoveryController must be the canonical recovery boundary"
    cls = classes[0]
    max_actions = next(
        node for node in cls.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "MAX_ACTIONS" for target in node.targets)
    )
    assert isinstance(max_actions.value, ast.Constant)
    assert max_actions.value.value == 4

    production = _parse("production_recovery.py")
    assert "RecoveryController(max_actions=1)" in production
    assert "media_stage_runtime.py" not in production
    assert "media_engine_v2.py" not in production


def test_main_does_not_call_a_second_recovery_engine():
    source = _parse("main.py")
    assert "shortauto_repair_engine.py" not in source
    assert '"production_recovery.py"' in source


def test_control_center_does_not_expose_legacy_repair_engine():
    source = _parse("control_center.sh")
    assert "shortauto_repair_engine.py" not in source
    assert "production_recovery.py" in source


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


CANONICAL_SEEDS = (
    "main.py",
    "first_video.py",
    "media_acquisition_v3.py",
    "media_v3/acquisition.py",
    "media_v3/providers.py",
    "media_v3/library.py",
    "render_plan_v2.py",
    "render_engine_v2.py",
    "recovery_controller.py",
    "production_recovery.py",
)

LEGACY_RECOVERY_MODULES = {
    "media_acquisition_recovery",
    "media_external_resilience",
    "media_master_gate",
    "media_strict_must_guard",
    "shortauto_repair_engine",
    "vi6_13_recovery_planner",
    "vi6_17_recovery_router",
    "vi6_19_true_recovery",
    "vi6_20_recovery_normalizer",
    "vi6_21_recovery_circuit",
}


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
    return found


def test_canonical_pipeline_has_single_recovery_authority():
    for name in CANONICAL_SEEDS:
        source = _parse(name)
        imported = _imported_modules(source)
        forbidden = sorted(imported & LEGACY_RECOVERY_MODULES)
        assert not forbidden, (
            f"{name} imports legacy recovery/gate modules: "
            + ", ".join(forbidden)
        )


def test_canonical_pipeline_has_no_dynamic_legacy_recovery_names():
    legacy_names = tuple(sorted(LEGACY_RECOVERY_MODULES))
    for name in CANONICAL_SEEDS:
        source = _parse(name)
        for legacy in legacy_names:
            assert f'"{legacy}"' not in source
            assert f"'{legacy}'" not in source
