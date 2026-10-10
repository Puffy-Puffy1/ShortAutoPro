from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LEGACY_MODULES = {
    "media_acquisition_recovery",
    "media_engine_v2",
    "media_provider_v2",
    "media_stage_runtime",
    "media_strict_must_guard",
    "midia",
    "media_master_gate",
    "vg4x_bridge",
    "vi6_13_recovery_planner",
    "vi6_17_recovery_router",
    "vi6_19_true_recovery",
    "vi6_20_recovery_normalizer",
    "vi6_21_recovery_circuit",
    "shortauto_repair_engine",
}

RETIRED_ACTIVE_FILES = {f"{name}.py" for name in LEGACY_MODULES}

LEGACY_TEST_NAMES = {
    "test_media_acquisition_recovery.py",
    "test_media_engine_v2_contract.py",
    "test_media_engine_v2_failure_modes.py",
    "test_media_engine_v2_integration.py",
    "test_media_provider_v2.py",
    "test_media_stage_runtime.py",
    "test_media_strict_must_guard.py",
    "test_midia_integrated.py",
    "test_stage6_completion_contract.py",
    "test_stage6_early_must_recovery.py",
    "test_stage6_fast_strict_path.py",
    "test_stage6_recovery_unwrap.py",
    "test_stage6_semantic_anchor_recovery.py",
    "test_stage6_timeout_resume.py",
    "test_media_acquisition_v2.py",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_canonical_tests_do_not_import_legacy_media_runtime():
    tests_dir = ROOT / "tests"
    for path in tests_dir.glob("test_*.py"):
        imported = _imports(path)
        forbidden = sorted(imported & LEGACY_MODULES)
        assert not forbidden, f"{path.name} imports legacy runtime: {forbidden}"


def test_legacy_tests_are_quarantined_outside_canonical_tests():
    tests_dir = ROOT / "tests"
    names = {path.name for path in tests_dir.glob("test_*.py")}
    leaked = sorted(names & LEGACY_TEST_NAMES)
    assert not leaked, f"legacy compatibility tests leaked into canonical tests/: {leaked}"


def test_retired_runtime_files_are_not_active():
    for filename in RETIRED_ACTIVE_FILES:
        assert not (ROOT / filename).exists(), f"retired runtime is active: {filename}"


def test_legacy_suite_has_explicit_compatibility_root():
    compat = ROOT / "tests_compat" / "legacy_media"
    assert compat.is_dir()
    for name in LEGACY_TEST_NAMES:
        path = compat / name
        if name in {
            "test_media_engine_v2_contract.py",
            "test_media_engine_v2_failure_modes.py",
            "test_media_engine_v2_integration.py",
            "test_media_provider_v2.py",
            "test_media_stage_runtime.py",
            "test_media_acquisition_recovery.py",
            "test_media_strict_must_guard.py",
            "test_midia_integrated.py",
        }:
            path = compat / f"{name}.disabled"
        assert path.is_file(), f"missing quarantined compatibility test: {path.name}"
