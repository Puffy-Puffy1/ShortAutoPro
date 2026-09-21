import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDIA = ROOT / "midia.py"


class MediaResolutionGuardTests(unittest.TestCase):
    def test_guard_rejects_subcritical_download_before_commit(self):
        source = MIDIA.read_text(encoding="utf-8")
        self.assertIn("pixels < 320 * 180", source)
        self.assertIn("mídia abaixo do piso técnico", source)
        guard = source.index("pixels < 320 * 180")
        commit = source.index("os.replace(", guard)
        self.assertLess(guard, commit)

    def test_canonical_media_runtime_wraps_without_rewriting_selector(self):
        self.assertFalse((ROOT / "midia_runtime.py").exists())
        self.assertFalse((ROOT / "gerar_short.sh").exists())
        self.assertTrue((ROOT / "media_stage_runtime.py").exists())
        pipeline = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('p.run("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py"', pipeline)
        runtime = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn('MIDIA = BASE / "midia.py"', runtime)
        self.assertNotIn("midia_runtime.py", pipeline)


if __name__ == "__main__":
    unittest.main()
