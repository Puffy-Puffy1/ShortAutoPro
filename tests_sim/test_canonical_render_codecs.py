import unittest
from pathlib import Path

import production_manifest as manifest


ROOT = Path(__file__).resolve().parents[1]


class CanonicalCodecContractTests(unittest.TestCase):
    def test_non_h264_and_non_aac_are_exposed_and_rejected_by_manifest_contract(self):
        probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "vp9",
                    "width": 1080,
                    "height": 1920,
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio", "codec_name": "opus"},
            ],
            "format": {"duration": "45"},
        }
        _, _, _, _, video_codec, audio_codec = manifest.inspect_video(probe)
        self.assertEqual(video_codec, "vp9")
        self.assertEqual(audio_codec, "opus")

        source = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('video_codec_normalized == "h264"', source)
        self.assertIn('audio_codec_normalized == "aac"', source)


if __name__ == "__main__":
    unittest.main()
