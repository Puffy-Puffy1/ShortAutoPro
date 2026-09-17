import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DirectorRepairConsolidationTests(unittest.TestCase):
    def test_main_orders_director_before_media_and_asset_library_after_media_gate(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        visual = text.index('5B - AI VISUAL DIRECTOR')
        director = text.index('5B0 - DIRECTOR AI PROVENANCE + VISUAL INTENT')
        media = text.index('6 - SMART MEDIA SELECTOR')
        media_gate = text.index('6A - MEDIA MASTER GATE')
        assets = text.index('6A0 - ASSET LIBRARY + FIRST FRAME')
        self.assertLess(visual, director)
        self.assertLess(director, media)
        self.assertLess(media_gate, assets)

    def test_repair_cycle_uses_bounded_formal_engine(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('shortauto_repair_engine.py', text)
        self.assertIn('"--max-cycles", "1"', text)
        self.assertIn('allow_codes={0, 20}', text)

    def test_new_layer_does_not_modify_visual_selection_v4(self):
        director = (ROOT / "shortauto_director_ai.py").read_text(encoding="utf-8")
        repair = (ROOT / "shortauto_repair_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("import visual_selection_engine_v4", director)
        self.assertNotIn("import visual_selection_engine_v4", repair)
        self.assertIn('"does_not_replace_visual_selection_v4": True', director)
        self.assertIn('"strict_must_can_never_be_relaxed": True', repair)

    def test_control_center_exposes_new_operations(self):
        text = (ROOT / "control_center.sh").read_text(encoding="utf-8")
        self.assertIn("23) Director AI - Provenance/Visual Intent", text)
        self.assertIn("24) Asset Library - Status", text)
        self.assertIn("25) Repair Engine - Plano/Executar", text)

    def test_runtime_outputs_are_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for item in ("reports/director_ai/", "reports/assets/", "reports/repair/"):
            self.assertIn(item, text)

    def test_health_check_tracks_new_modules(self):
        text = (ROOT / "health_check.sh").read_text(encoding="utf-8")
        for item in (
            "shortauto_director_ai.py", "shortauto_asset_library.py",
            "shortauto_repair_engine.py", '"shortauto_director_ai"',
            '"shortauto_asset_library"', '"shortauto_repair_engine"',
        ):
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
