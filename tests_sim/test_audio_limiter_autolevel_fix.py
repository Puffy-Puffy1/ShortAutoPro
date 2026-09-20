import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AudioLimiterAutoLevelFixTests(unittest.TestCase):
    def test_finalizer_disables_alimiter_auto_level(self):
        text = (ROOT / "audio_finalizer.py").read_text(encoding="utf-8")
        self.assertIn("alimiter=limit=", text)
        self.assertIn(":level=false", text)
        self.assertIn('"version":"1.3"', text)

    def test_v6_disables_auto_level_on_all_limiters(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        occurrences = text.count("alimiter=limit={limiter:.5f}")
        disabled = text.count("alimiter=limit={limiter:.5f}:level=false")
        self.assertGreaterEqual(disabled, 3)
        self.assertEqual(occurrences, disabled)

    def test_final_output_contract_is_not_changed(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        for needle in (
            '"-c:v", "libx264"',
            '"-pix_fmt", "yuv420p"',
            '"-r", "30"',
            '"-c:a", "aac"',
            '"-b:a", "192k"',
            '"-ar", "48000"',
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
