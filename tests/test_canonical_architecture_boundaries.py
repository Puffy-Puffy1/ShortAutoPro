import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = (
    "main.py",
    "first_video.py",
    "media_acquisition_v3.py",
    "media_v3/acquisition.py",
    "media_v3/providers.py",
    "media_v3/library.py",
    "render_plan_v2.py",
    "render_engine_v2.py",
    "production_recovery.py",
    "recovery_controller.py",
)

RETIRED_MODULES = {
    "media_stage_runtime",
    "media_engine_v2",
    "media_provider_v2",
    "media_provider_router_v2",
    "shortauto_repair_engine",
    "media_acquisition_recovery",
    "media_master_gate",
    "media_strict_must_guard",
    "midia",
    "vg4x_bridge",
    "vi6_13_recovery_planner",
    "vi6_17_recovery_router",
    "vi6_19_true_recovery",
    "vi6_20_recovery_normalizer",
    "vi6_21_recovery_circuit",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


class CanonicalArchitectureBoundaryTests(unittest.TestCase):
    def test_canonical_modules_do_not_import_retired_runtime(self):
        for rel in CANONICAL:
            path = ROOT / rel
            if not path.is_file():
                continue
            forbidden = sorted(_imports(path) & RETIRED_MODULES)
            self.assertFalse(forbidden, f"{rel} imports retired runtime: {forbidden}")

    def test_canonical_modules_compile(self):
        for rel in CANONICAL:
            path = ROOT / rel
            if path.is_file():
                ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=rel)

    def test_retired_modules_are_absent_from_active_tree(self):
        for module in RETIRED_MODULES:
            self.assertFalse((ROOT / f"{module}.py").exists(), f"retired module still active: {module}")


if __name__ == "__main__":
    unittest.main()
