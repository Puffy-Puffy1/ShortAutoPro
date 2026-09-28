#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RenderEngineV2FfmpegBackendTests(unittest.TestCase):
    def test_ffmpeg_backend_one_real_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ShortAutoPro"
            sid = "v2_ffmpeg_android"
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            (base / "roteiros").mkdir(parents=True)
            (base / "audios").mkdir(parents=True)
            (base / "videos").mkdir(parents=True)

            for i in range(1, 4):
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-loglevel", "error",
                        "-f", "lavfi", "-i",
                        "testsrc2=size=1080x1920:rate=30:duration=0.8",
                        "-frames:v", "1",
                        str(media / f"scene_{i:02d}.png"),
                    ],
                    check=True, timeout=30,
                )

            audio = base / "audios" / f"short_{sid}.mp3"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=48000:duration=3",
                    "-c:a", "libmp3lame", str(audio),
                ],
                check=True, timeout=30,
            )

            ass = base / "videos" / f"short_{sid}.ass"
            ass.write_text(
                "[Script Info]\nScriptType: v4.00+\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,"
                "&H80000000,1,0,0,0,100,100,0,0,1,3,0,2,40,40,180,1\n"
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
                "MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TESTE V2\n",
                encoding="utf-8",
            )

            scenes = [{"scene": i, "segment": f"cena {i}", "words": 3} for i in range(1, 4)]
            plan = [
                {"scene": i, "pace_multiplier": 1.0, "zoom_start": 1.0,
                 "zoom_end": 1.04, "pan": "center", "transition_duration": 0.0}
                for i in range(1, 4)
            ]
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                json.dumps({"scenes": scenes}), encoding="utf-8"
            )
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
                json.dumps({"scenes": plan}), encoding="utf-8"
            )

            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            env["SAP_RENDER_V2_BACKEND"] = "ffmpeg"
            env["SAP_RENDER_V2_FFMPEG_SCENE_TIMEOUT_SECONDS"] = "120"
            env["SAP_RENDER_V2_FFMPEG_SUBTITLE_TIMEOUT_SECONDS"] = "120"

            proc = subprocess.run(
                [sys.executable, str(ROOT / "render_engine_v2.py"), "--short-id", sid],
                env=env, cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)

            report = json.loads(
                (base / "render_jobs" / sid / "render_001" / "render_report.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(report["quality_gate"], "PASS")
            self.assertEqual(report["backend"], "ffmpeg")
            self.assertTrue(report["real_media"])
            self.assertTrue((base / "videos" / f"short_v6_{sid}.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
