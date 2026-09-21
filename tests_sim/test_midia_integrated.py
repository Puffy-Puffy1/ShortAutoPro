import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDIA = ROOT / "midia.py"


class IntegratedMediaSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MIDIA.read_text(encoding="utf-8")

    def test_selector_compiles_without_runtime_rewrite(self):
        compile(self.source, str(MIDIA), "exec")

    def test_webp_cleanup_is_native(self):
        start = self.source.index("# LIMPAR MÍDIA ANTIGA")
        end = self.source.index("# TEXTO", start)
        self.assertIn('".webp"', self.source[start:end])

    def test_minimum_resolution_guard_is_native(self):
        self.assertIn("pixels < 320 * 180", self.source)
        self.assertIn("mídia abaixo do piso técnico", self.source)

    def test_professional_media_floor_is_native(self):
        self.assertIn("def _sap_professional_media_accept_v1", self.source)
        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", self.source)
        self.assertIn('evidence_class == "CASE_DIRECT"', self.source)
        self.assertIn("ok = _sap_professional_media_accept_v1", self.source)

    def test_known_premature_break_anchors_are_gone(self):
        self.assertNotIn("                break\n                destino = destino_teste", self.source)
        self.assertNotIn("        _vse42_cleanup_scene_sibling(destino)\n        break", self.source)
        self.assertNotIn("        _vse42_commit_safe(escolhido)\n        break", self.source)

    def test_download_floor_precedes_commit_replace(self):
        guard = self.source.index("pixels < 320 * 180")
        replace = self.source.index("os.replace(", guard)
        self.assertLess(guard, replace)


if __name__ == "__main__":
    unittest.main()
