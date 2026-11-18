#!/usr/bin/env python3
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from render_v2.ffmpeg_visual_renderer import _scene_filter


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe are required")
class FFmpegVisualSmokeTests(unittest.TestCase):
    def test_landscape_scene_filter_produces_valid_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "landscape_smoke.mp4"
            filter_graph = _scene_filter(
                {"effect": {"zoom_start": 1.0, "zoom_end": 1.04}},
                width=1280,
                height=720,
                fps=24,
                duration=2.0,
            )
            render = subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=blue:s=1280x720:r=24:d=2",
                    "-vf", filter_graph, "-r", "24", "-frames:v", "48",
                    "-an", "-c:v", "libx264", "-preset", "ultrafast",
                    "-crf", "28", "-pix_fmt", "yuv420p", str(output),
                ],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr[-2000:])
            self.assertGreater(output.stat().st_size, 1000)
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=width,height,avg_frame_rate", "-show_entries",
                    "format=duration", "-of", "json", str(output),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            info = json.loads(probe.stdout)
            video = next(x for x in info["streams"] if x.get("width"))
            self.assertEqual((video["width"], video["height"]), (1280, 720))
            self.assertEqual(video["avg_frame_rate"], "24/1")
            self.assertGreaterEqual(float(info["format"]["duration"]), 1.8)


if __name__ == "__main__":
    unittest.main()
