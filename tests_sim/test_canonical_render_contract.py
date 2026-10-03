import unittest
from pathlib import Path

import production_manifest as manifest


ROOT = Path(__file__).resolve().parents[1]

GOOD_PROBE = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1080,
            "height": 1920,
            "avg_frame_rate": "30/1",
        },
        {"codec_type": "audio", "codec_name": "aac"},
    ],
    "format": {"duration": "45"},
}


class CanonicalRenderContractTests(unittest.TestCase):
    def test_valid_probe_is_parsed_as_professional_contract(self):
        duration, width, height, fps, video_codec, audio_codec = manifest.inspect_video(GOOD_PROBE)
        self.assertEqual((width, height), (1080, 1920))
        self.assertAlmostEqual(fps, 30.0)
        self.assertEqual(video_codec, "h264")
        self.assertEqual(audio_codec, "aac")
        self.assertEqual(duration, 45.0)

    def test_missing_audio_is_visible_to_fail_closed_manifest(self):
        probe = {"streams": [GOOD_PROBE["streams"][0]], "format": {"duration": "45"}}
        *_, audio_codec = manifest.inspect_video(probe)
        self.assertEqual(audio_codec, "")

    def test_bad_resolution_and_duration_are_exposed(self):
        probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 720,
                    "height": 1280,
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "181"},
        }
        duration, width, height, fps, _, _ = manifest.inspect_video(probe)
        self.assertEqual((width, height), (720, 1280))
        self.assertAlmostEqual(fps, 30.0)
        self.assertEqual(duration, 181.0)

    def test_manifest_keeps_original_v6_technical_guards(self):
        source = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"resolution_ok": width == 1080 and height == 1920', source)
        self.assertIn('"fps_ok": 29.0 <= fps <= 31.0', source)
        self.assertIn('"video_codec_ok": video_codec_normalized == "h264"', source)
        self.assertIn('"audio_codec_ok": audio_codec_normalized == "aac"', source)
        self.assertIn('"duration_ok": 15.0 <= duration <= 180.0', source)

    def test_main_uses_render_engine_v2_as_canonical_route(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('9 - RENDER ENGINE V2 (REMOTION + FFMPEG + FFPROBE)', source)
        self.assertIn('"render_engine_v2.py"', source)
        self.assertIn("RENDER_ENGINE_LEGACY_DISABLED", source)
        self.assertNotIn('p.run("9L - PROFESSIONAL MULTI-BEAT ASSEMBLER"', source)
        self.assertNotIn('p.run("10L - FINAL RENDER V6 PROFESSIONAL"', source)
        self.assertNotIn("v6_runtime.py", source)
        self.assertNotIn('"v6.py"', source)
        self.assertIn('os.getenv("RENDER_ENGINE", "v2")', source)
        self.assertNotIn('render_engine == "legacy"', source)
        self.assertNotIn("SAP_PRO_EDIT", source)
        self.assertFalse((ROOT / "v6_runtime.py").exists())
        self.assertFalse((ROOT / "v6.py").exists())


if __name__ == "__main__":
    unittest.main()
