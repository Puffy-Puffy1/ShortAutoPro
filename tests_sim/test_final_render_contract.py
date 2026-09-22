import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import v6_professional as renderer


class FinalRenderContractTests(unittest.TestCase):
    def _artifact(self, folder: Path) -> Path:
        path = folder / "final.mp4"
        path.write_bytes(b"x" * 600000)
        return path

    def test_valid_contract_requires_probe_and_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._artifact(Path(tmp))
            probe = json.dumps({
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "avg_frame_rate": "30/1"},
                    {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
                ],
                "format": {"duration": "40.10", "size": "600000"},
            })
            with mock.patch.object(renderer, "check_output_group", return_value=probe), \
                 mock.patch.object(renderer, "run_group", return_value=subprocess.CompletedProcess([], 0, "", "")) as decode:
                ok, detail = renderer.validate_final_output(path, 40.0)
            self.assertTrue(ok)
            self.assertEqual(detail["resolution"], "1080x1920")
            self.assertEqual(detail["decode_check"], "PASS")
            decode.assert_called_once()

    def test_duration_mismatch_fails_before_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._artifact(Path(tmp))
            probe = json.dumps({
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"duration": "32.0", "size": "600000"},
            })
            with mock.patch.object(renderer, "check_output_group", return_value=probe), \
                 mock.patch.object(renderer, "run_group") as decode:
                ok, detail = renderer.validate_final_output(path, 40.0)
            self.assertFalse(ok)
            self.assertTrue(any("duration_mismatch" in item for item in detail["errors"]))
            decode.assert_not_called()

    def test_missing_audio_stream_is_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._artifact(Path(tmp))
            probe = json.dumps({
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                ],
                "format": {"duration": "40.0", "size": "600000"},
            })
            with mock.patch.object(renderer, "check_output_group", return_value=probe), \
                 mock.patch.object(renderer, "run_group") as decode:
                ok, detail = renderer.validate_final_output(path, 40.0)
            self.assertFalse(ok)
            self.assertIn("SAP-E009:audio_stream_missing", detail["errors"])
            decode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
