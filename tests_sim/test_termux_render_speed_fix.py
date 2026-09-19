import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TermuxRenderSpeedFixTests(unittest.TestCase):
    def test_termux_defaults_to_veryfast_but_keeps_override(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('return "veryfast" if termux_runtime() else "fast"', text)
        self.assertIn('os.getenv("SHORT_PRESET", "")', text)

    def test_output_contract_is_preserved(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('"-c:v", "libx264"', text)
        self.assertIn('os.getenv("SHORT_CRF", "20")', text)
        self.assertIn('"-profile:v", "high"', text)
        self.assertIn('"-level", "4.1"', text)
        self.assertIn('"-pix_fmt", "yuv420p"', text)
        self.assertIn('"-r", "30"', text)
        self.assertIn('"-c:a", "aac"', text)
        self.assertIn('"-b:a", "192k"', text)
        self.assertIn('"-ar", "48000"', text)

    def test_redundant_base_scale_is_skipped_for_native_vertical_base(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("if base_w == 1080 and base_h == 1920:", text)
        self.assertIn('base_filter = "[0:v]"', text)
        self.assertIn("video_stream_info(VIDEO_BASE)", text)

    def test_full_range_is_converted_not_only_relabelled(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("in_range=pc:out_range=tv", text)
        self.assertIn('"-color_range", "tv"', text)

    def test_mobile_fastpath_removes_dynamic_zoom_and_uses_smaller_unsharp(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('SAP_RENDER_MOBILE_FASTPATH', text)
        self.assertIn("and not mobile_fastpath", text)
        self.assertIn("unsharp_size = 3 if mobile_fastpath else 5", text)

    def test_render_threads_and_timing_are_reported(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn('SAP_RENDER_THREADS', text)
        self.assertIn('"-filter_threads"', text)
        self.assertIn('"-filter_complex_threads"', text)
        self.assertIn('"render_elapsed_seconds"', text)
        self.assertIn('"render_preset"', text)
        self.assertIn("speed_ratio", text)


if __name__ == "__main__":
    unittest.main()
