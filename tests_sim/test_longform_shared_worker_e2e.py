"""End-to-end proof that Long-form uses the shared queue and canonical renderer.

The CI workflow checks out the worker branch before running this test. FFmpeg is
used only as a deterministic local test backend; it is not presented as AI output.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import longform_runtime as longform


class LongFormSharedWorkerEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import generative_video_poc.brain  # noqa: F401
            import generative_video_poc.manifest  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(
                "shared worker branch must be present for this integration test"
            ) from exc
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise unittest.SkipTest("FFmpeg and FFprobe are required")

    def test_shared_queue_manifest_and_canonical_chapter_render(self):
        with tempfile.TemporaryDirectory(prefix="shortautopro-longform-e2e-") as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            run_dir = root / "runs" / "e2e"
            run_dir.mkdir(parents=True)
            config = root / "local_video_backend.json"
            config.write_text(json.dumps({
                "executable": shutil.which("ffmpeg"),
                "command_template": [
                    "-y", "-f", "lavfi", "-i",
                    "color=c=blue:s={width}x{height}:r=12",
                    "-frames:v", "{frames}", "-an", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", "{output}",
                ],
                "timeout_seconds": 120,
                "fps": 12,
                "seed": 7,
                "model": "ci-ffmpeg-fixture-not-ai",
            }), encoding="utf-8")

            state = {}
            outline = [
                {"chapter": 1, "title": "Contexto", "objective": "Apresentar o contexto"},
                {"chapter": 2, "title": "Consequências", "objective": "Mostrar consequências"},
            ]
            with mock.patch.object(longform, "BASE", Path(__file__).resolve().parents[1]), \
                 mock.patch.dict(os.environ, {"HOME": str(home), "SAP_GENERATIVE_VIDEO_ROOT": str(home / ".shortautopro")}):
                manifest = longform._generate_local_longform_manifest(
                    "longform-e2e", "Tema de teste", 1, outline,
                    config, state, run_dir,
                )

                self.assertEqual(state["local_generation_status"], "COMPLETE")
                self.assertEqual(state["generated_media_source"], "shared_local_queue")
                self.assertEqual(len(manifest["clips"]), 6)
                self.assertEqual(int(manifest["project"]["target_duration_seconds"]), 60)
                for clip in manifest["clips"]:
                    clip_path = Path(clip["path"])
                    self.assertTrue(clip_path.is_file())
                    self.assertGreater(clip_path.stat().st_size, 0)

                audio = root / "voice.m4a"
                subprocess.run([
                    "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=10", "-c:a", "aac",
                    "-b:a", "192k", str(audio),
                ], check=True, timeout=60)
                ass = root / "captions.ass"
                ass.write_text(
                    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
                    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                    "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                    "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,40,1\n"
                    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
                    encoding="utf-8",
                )
                chapter = root / "chapter"
                output = longform.render_generated_chapter(
                    chapter, manifest, 0, 10, audio, 10, ass,
                )
                probe = longform.probe_video(output)

            self.assertEqual(probe["width"], 1920)
            self.assertEqual(probe["height"], 1080)
            self.assertEqual(probe["video_codec"], "h264")
            self.assertEqual(probe["audio_codec"], "aac")
            self.assertGreaterEqual(probe["duration"], 9.5)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 100_000)


if __name__ == "__main__":
    unittest.main()
