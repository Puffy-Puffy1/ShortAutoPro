#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import render_preflight


class RenderPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.sid = "test_stage6"
        for name in ("roteiros", "audios", "imagens", "videos", "temp"):
            (self.base / name).mkdir(parents=True, exist_ok=True)
        self.media = self.base / "imagens" / f"short_{self.sid}"
        self.media.mkdir(parents=True, exist_ok=True)

        scenes = [{"scene": i, "segment": f"cena {i}"} for i in range(1, 7)]
        (self.base / "roteiros" / f"scene_map_{self.sid}.json").write_text(
            json.dumps({"schema_version": "1.0", "short_id": self.sid, "scenes": scenes}),
            encoding="utf-8",
        )
        (self.base / "roteiros" / f"pro_edit_plan_{self.sid}.json").write_text(
            json.dumps({"version": "PRO_EDIT_TEST", "scenes": scenes}),
            encoding="utf-8",
        )
        for i in range(1, 7):
            # Suffix deliberately exercises compatibility with canonical renderer regex.
            (self.media / f"scene_{i:02d}_primary.jpg").write_bytes(b"x" * 2048)

        (self.base / "audios" / f"short_{self.sid}.mp3").write_bytes(b"a" * 6000)
        (self.base / "videos" / f"short_{self.sid}.ass").write_text(
            "[Script Info]\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Primeira\n"
            # Intentional overlap; valid because starts remain monotonic.
            "Dialogue: 0,0:00:01.80,0:00:04.00,Default,,0,0,0,,Segunda\n"
            "Dialogue: 0,0:00:04.00,0:00:11.80,Default,,0,0,0,,Terceira\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_ready_accepts_monotonic_overlapping_ass_and_renderer_style_names(self):
        disk = os.statvfs(self.base)
        fake_usage = mock.Mock()
        fake_usage.free = max(2 * 1024**3, disk.f_bavail * disk.f_frsize)

        with (
            mock.patch.object(render_preflight, "BASE", self.base),
            mock.patch.object(render_preflight, "_probe_media", return_value=None),
            mock.patch.object(render_preflight, "_duration", return_value=12.0),
            mock.patch.object(render_preflight.shutil, "which", return_value="/usr/bin/fake"),
            mock.patch.object(render_preflight.shutil, "disk_usage", return_value=fake_usage),
            mock.patch.dict(os.environ, {"SHORT_QTD_CENAS": "6"}, clear=False),
        ):
            report = render_preflight.inspect(self.sid)

        self.assertEqual(report["status"], "READY", report)
        self.assertEqual(report["valid_assets"], 6)
        self.assertTrue(report["checks"]["subtitles"])

    def test_ass_rejects_timestamp_start_regression(self):
        path = self.base / "bad.ass"
        path.write_text(
            "[Events]\n"
            "Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,A\n"
            "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,B\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            render_preflight._ass_bounds(path)


if __name__ == "__main__":
    unittest.main()
