import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDIA = ROOT / "midia.py"


class MediaResolutionGuardTests(unittest.TestCase):
    def test_guard_rejects_subcritical_download_before_commit(self):
        source = MIDIA.read_text(encoding="utf-8")
        self.assertIn("largura * altura < 320 * 180", source)
        self.assertIn("mídia abaixo do piso técnico", source)
        guard = source.index("largura * altura < 320 * 180")
        commit = source.index("os.replace(", guard)
        self.assertLess(guard, commit)

    def test_canonical_media_runtime_wraps_without_rewriting_selector(self):
        self.assertFalse((ROOT / "midia_runtime.py").exists())
        self.assertFalse((ROOT / "gerar_short.sh").exists())
        self.assertTrue((ROOT / "media_stage_runtime.py").exists())
        pipeline = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("media_acquisition_v3.py", pipeline)
        self.assertIn("render_plan_v2.py", pipeline)
        self.assertNotIn("media_stage_runtime.py", pipeline)
        self.assertNotIn("midia_runtime.py", pipeline)


if __name__ == "__main__":
    unittest.main()
