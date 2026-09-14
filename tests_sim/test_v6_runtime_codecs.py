import unittest

from v6_runtime import validate_probe


class V6RuntimeCodecTests(unittest.TestCase):
    def test_non_h264_and_non_aac_are_rejected(self):
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
        errors = validate_probe(probe)
        self.assertIn("video_codec_invalid=vp9", errors)
        self.assertIn("audio_codec_invalid=opus", errors)


if __name__ == "__main__":
    unittest.main()
