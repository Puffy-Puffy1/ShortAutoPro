import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SelectiveRepairRerenderTests(unittest.TestCase):
    def test_audio_only_repair_does_not_force_rerender(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("REPAIR_RERENDER=NO", text)
        self.assertIn('"media_reacquire"', text)
        self.assertIn('"caption_repair"', text)
        self.assertNotIn('"audio_remaster",\n    }', text)

    def test_repair_history_drives_rerender_decision(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('reports" / "repair" / f"repair_{p.sid}.json"', text)
        self.assertIn("performed.intersection(rerender_actions)", text)
        self.assertIn("REPAIR_RERENDER=YES", text)


if __name__ == "__main__":
    unittest.main()
