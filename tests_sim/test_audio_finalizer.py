"""Regression tests for bounded audio-finalizer recovery."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audio_finalizer as finalizer


class AudioFinalizerRecoveryTests(unittest.TestCase):
    def test_retries_dynamic_mastering_when_first_pass_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "short.mp4"
            video.write_bytes(b"x" * 600_000)
            report = root / "report.json"
            measurements = iter([
                {"lufs": -18.28, "true_peak_db": -0.01, "lra": 4.0, "threshold": -28.0, "offset": 4.0},
                {"lufs": -18.10, "true_peak_db": -0.50, "lra": 4.0, "threshold": -28.0, "offset": 4.0},
                {"lufs": -14.20, "true_peak_db": -1.70, "lra": 4.0, "threshold": -24.0, "offset": 0.0},
            ])
            calls = []

            with patch.object(finalizer, "VIDEO", video), patch.object(finalizer, "REPORT", report), patch.object(
                finalizer, "measure", side_effect=lambda _path: next(measurements)
            ), patch.object(
                finalizer, "remaster",
                side_effect=lambda _path, measured, *, linear=True: calls.append((measured["lufs"], linear)),
            ):
                self.assertEqual(finalizer.main(), 0)

            self.assertEqual(calls, [(-18.28, True), (-18.1, False)])
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["measurement_source"], "post_remaster_dynamic_retry")

    def test_does_not_remaster_when_audio_is_already_within_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "short.mp4"
            video.write_bytes(b"x" * 600_000)
            report = root / "report.json"
            good = {"lufs": -14.1, "true_peak_db": -1.6, "lra": 4.0, "threshold": -24.0, "offset": 0.0}

            with patch.object(finalizer, "VIDEO", video), patch.object(finalizer, "REPORT", report), patch.object(
                finalizer, "measure", return_value=good
            ), patch.object(finalizer, "remaster", side_effect=AssertionError("unexpected remaster")):
                self.assertEqual(finalizer.main(), 0)


if __name__ == "__main__":
    unittest.main()
