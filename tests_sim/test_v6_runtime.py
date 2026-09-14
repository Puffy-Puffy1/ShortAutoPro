import os
import subprocess
import unittest
from unittest import mock

from v6_runtime import render_timeout, run_renderer, validate_probe


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


class V6RuntimeTests(unittest.TestCase):
    def test_valid_probe_passes(self):
        self.assertEqual(validate_probe(GOOD_PROBE), [])

    def test_missing_audio_blocks(self):
        probe = {"streams": [GOOD_PROBE["streams"][0]], "format": {"duration": "45"}}
        self.assertIn("audio_stream_missing", validate_probe(probe))

    def test_bad_resolution_and_duration_block(self):
        probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 720,
                    "height": 1280,
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio"},
            ],
            "format": {"duration": "181"},
        }
        errors = validate_probe(probe)
        self.assertTrue(any(x.startswith("resolution_invalid=") for x in errors))
        self.assertTrue(any(x.startswith("duration_invalid=") for x in errors))

    def test_render_timeout_is_bounded(self):
        with mock.patch.dict(os.environ, {"SHORT_RENDER_TIMEOUT": "10"}, clear=False):
            self.assertEqual(render_timeout(), 120)
        with mock.patch.dict(os.environ, {"SHORT_RENDER_TIMEOUT": "99999"}, clear=False):
            self.assertEqual(render_timeout(), 1800)

    @mock.patch("v6_runtime.subprocess.Popen")
    def test_renderer_stdin_is_detached(self, popen):
        process = popen.return_value
        process.wait.return_value = 0
        self.assertEqual(run_renderer(120), 0)
        self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
