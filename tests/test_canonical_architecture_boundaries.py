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
)

LEGACY = (
    "media_stage_runtime.py",
    "media_engine_v2.py",
    "media_provider_v2.py",
    "media_provider_router_v2.py",
)

class CanonicalArchitectureBoundaryTests(unittest.TestCase):
    def test_canonical_modules_do_not_reference_legacy_media_runtime(self):
        for rel in CANONICAL:
            path = ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for legacy in LEGACY:
                self.assertNotIn(legacy, text, f"{rel} references {legacy}")

    def test_canonical_modules_compile(self):
        for rel in CANONICAL:
            path = ROOT / rel
            if path.is_file():
                ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=rel)

if __name__ == "__main__":
    unittest.main()
