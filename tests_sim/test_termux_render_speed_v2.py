import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TermuxRenderSpeedV2Tests(unittest.TestCase):
    def test_termux_defaults_to_superfast_with_override_preserved(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('return "superfast" if termux_runtime() else "fast"', text)
        self.assertIn('os.getenv("SHORT_PRESET", "")', text)

    def test_mobile_fastpath_skips_v6_unsharp(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('if mobile_fastpath:', text)
        self.assertIn('detail_filter = ""', text)
        self.assertIn('mobile_unsharp=', text)

    def test_desktop_path_keeps_unsharp(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('unsharp_size = 5', text)
        self.assertIn('unsharp=', text)

    def test_output_contract_stays_1080p30_h264_crf20_aac(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        for needle in (
            '"-c:v", "libx264"',
            'os.getenv("SHORT_CRF", "20")',
            '"-profile:v", "high"',
            '"-level", "4.1"',
            '"-pix_fmt", "yuv420p"',
            '"-r", "30"',
            '"-c:a", "aac"',
            '"-b:a", "192k"',
            '"-ar", "48000"',
        ):
            self.assertIn(needle, text)

    def test_renderer_version_incremented(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("V6 PROFESSIONAL RENDERER 2.2", text)
        self.assertIn('"version": "2.2"', text)


if __name__ == "__main__":
    unittest.main()
