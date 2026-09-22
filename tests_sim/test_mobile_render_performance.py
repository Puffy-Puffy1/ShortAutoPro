import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MobileRenderPerformanceTests(unittest.TestCase):
    def test_single_image_multi_beat_is_opt_in(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertIn('SAP_MULTI_BEAT_FALLBACK", "0"', text)
        self.assertIn("secondary is not None", text)
        self.assertIn("source_asset_count", text)

    def test_scene_and_assembly_timeouts_are_bounded(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertIn('SHORT_SCENE_RENDER_TIMEOUT", 180', text)
        self.assertIn('SHORT_ASSEMBLY_TIMEOUT", 600', text)

    def test_visual_qa_uses_single_ffmpeg_scan(self):
        text = (ROOT / "visual_qa.py").read_text(encoding="utf-8")
        self.assertIn("def analyze_final_video", text)
        self.assertIn('"single_pass": True', text)
        self.assertIn("split={count}", text)
        self.assertIn("video_scan=SINGLE_PASS", text)
        self.assertNotIn("def black_seconds(", text)
        self.assertNotIn("def crop_detect(", text)
        self.assertNotIn("def blur_risk(", text)

    def test_mobile_final_renderer_fastpath_remains_default(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('SAP_RENDER_MOBILE_FASTPATH", "1"', text)


if __name__ == "__main__":
    unittest.main()
