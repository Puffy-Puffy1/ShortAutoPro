import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RenderSimulationTests(unittest.TestCase):
    def test_webp_scene_assembler_and_v6_final_render(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("FFmpeg/ffprobe não disponíveis")

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = home / "ShortAutoPro"
            short_id = "render_sim"
            media = base / "imagens" / f"short_{short_id}"
            audio_dir = base / "audios"
            roteiros = base / "roteiros"
            videos = base / "videos"
            temp_dir = base / "temp" / short_id
            for folder in (media, audio_dir, roteiros, videos, temp_dir):
                folder.mkdir(parents=True, exist_ok=True)

            # Gera uma imagem WebP real para testar o contrato que antes
            # era aceito pelos gates, mas ignorado pelo renderer.
            sample_webp = base / "sample.webp"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=320x568:d=0.1",
                    "-frames:v", "1", str(sample_webp),
                ],
                check=True,
                timeout=30,
            )
            for i in range(1, 7):
                shutil.copy2(sample_webp, media / f"scene_{i:02d}.webp")

            audio = audio_dir / f"short_{short_id}.mp3"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6",
                    "-c:a", "libmp3lame", "-b:a", "96k", str(audio),
                ],
                check=True,
                timeout=30,
            )

            scenes = [
                {
                    "scene": i,
                    "segment": f"Trecho narrativo simulado da cena {i}.",
                    "query": f"simulated documentary scene {i}",
                    "must_have": ["documentary"],
                    "avoid": [],
                    "words": 6,
                }
                for i in range(1, 7)
            ]
            (roteiros / f"scene_map_{short_id}.json").write_text(
                json.dumps({"scenes": scenes}),
                encoding="utf-8",
            )

            ass = videos / f"short_{short_id}.ass"
            ass.write_text(
                """[Script Info]\n"
                "ScriptType: v4.00+\n"
                "PlayResX: 1080\n"
                "PlayResY: 1920\n\n"
                "[V4+ Styles]\n"
                "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
                "Style: Dynamic,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,220,1\n\n"
                "[Events]\n"
                "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
                "Dialogue: 0,0:00:00.00,0:00:05.80,Dynamic,,0,0,0,,Teste de render\n""",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "SHORT_ID": short_id,
                    "SHORT_QTD_CENAS": "6",
                    "SHORT_PRESET_CENAS": "ultrafast",
                    "SHORT_CRF_CENAS": "35",
                    "SHORT_PRESET": "ultrafast",
                    "SHORT_CRF": "35",
                    "SHORT_USAR_MUSICA": "0",
                    "SHORT_USAR_SFX": "0",
                    "SHORT_USAR_POP": "0",
                    "SHORT_RETENTION_ENGINE": "0",
                    "VI700_CANARY_MODE": "OFF",
                }
            )

            scene_proc = subprocess.run(
                [sys.executable, str(ROOT / "video.py")],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            scene_output = scene_proc.stdout + scene_proc.stderr
            self.assertEqual(scene_proc.returncode, 0, scene_output)
            base_video = temp_dir / "video_sem_audio.mp4"
            self.assertTrue(base_video.is_file(), scene_output)
            self.assertGreater(base_video.stat().st_size, 0)

            final_proc = subprocess.run(
                [sys.executable, str(ROOT / "v6.py")],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            final_output = final_proc.stdout + final_proc.stderr
            self.assertEqual(final_proc.returncode, 0, final_output)

            final_video = videos / f"short_v6_{short_id}.mp4"
            self.assertTrue(final_video.is_file(), final_output)
            self.assertGreater(final_video.stat().st_size, 0)

            probe = subprocess.check_output(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=codec_type,width,height",
                    "-of", "json", str(final_video),
                ],
                text=True,
                timeout=30,
            )
            info = json.loads(probe)
            streams = info.get("streams", [])
            video_streams = [x for x in streams if x.get("codec_type") == "video"]
            audio_streams = [x for x in streams if x.get("codec_type") == "audio"]
            self.assertTrue(video_streams)
            self.assertTrue(audio_streams)
            self.assertEqual(video_streams[0].get("width"), 1080)
            self.assertEqual(video_streams[0].get("height"), 1920)


if __name__ == "__main__":
    unittest.main()
