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

    def test_runtime_rewrite_module_is_not_required(self):
        self.assertFalse((ROOT / "midia_runtime.py").exists())
        self.assertFalse((ROOT / "gerar_short.sh").exists())
        pipeline = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('p.run("6 - SMART MEDIA SELECTOR", "midia.py"', pipeline)
        self.assertNotIn("midia_runtime.py", pipeline)


if __name__ == "__main__":
    unittest.main()
