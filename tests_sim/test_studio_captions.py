#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import caption_layout_guard
from subtitle_style_policy import style_header


class StudioCaptionTests(unittest.TestCase):
    def test_portrait_ass_header_uses_short_canvas(self):
        with patch.dict(os.environ, {"SAP_STUDIO_WIDTH": "1080", "SAP_STUDIO_HEIGHT": "1920"}):
            header = style_header()
        self.assertIn("PlayResX: 1080", header)
        self.assertIn("PlayResY: 1920", header)
        self.assertIn("Style: Dynamic,DejaVu Sans,66,", header)

    def test_landscape_ass_header_uses_long_video_canvas(self):
        with patch.dict(os.environ, {"SAP_STUDIO_WIDTH": "1280", "SAP_STUDIO_HEIGHT": "720"}):
            header = style_header()
        self.assertIn("PlayResX: 1280", header)
        self.assertIn("PlayResY: 720", header)
        self.assertIn("Style: Dynamic,DejaVu Sans,42,", header)

    def test_safe_zone_guard_scales_vertical_margin_for_landscape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass_path = root / "short_test.ass"
            map_path = root / "scene_map_test.json"
            report_path = root / "caption_layout_test.json"
            with patch.dict(os.environ, {"SAP_STUDIO_WIDTH": "1280", "SAP_STUDIO_HEIGHT": "720"}):
                ass_path.write_text(
                    style_header() + "Dialogue: 0,0:00:00.00,0:00:01.00,Dynamic,,0,0,0,,Teste\n",
                    encoding="utf-8",
                )
            map_path.write_text(
                json.dumps({"scenes": [
                    {"protected_zone": "bottom"},
                    {"protected_zone": "bottom"},
                    {"protected_zone": "center"},
                    {"protected_zone": "center"},
                ]}),
                encoding="utf-8",
            )
            with patch.object(caption_layout_guard, "ASS", ass_path), \
                 patch.object(caption_layout_guard, "MAP", map_path), \
                 patch.object(caption_layout_guard, "REPORT", report_path), \
                 patch.dict(os.environ, {"SAP_STUDIO_HEIGHT": "720"}):
                self.assertEqual(caption_layout_guard.main(), 0)
            updated = ass_path.read_text(encoding="utf-8")
            self.assertIn(",158,1", updated)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["play_res_y"], 720)
            self.assertEqual(report["margin_v"], 158)


if __name__ == "__main__":
    unittest.main()
