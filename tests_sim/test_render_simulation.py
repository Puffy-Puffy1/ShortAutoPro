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
    def test_webp_scene_assembler_and_v6_professional_final_render(self):
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

            # WebP real com detalhe suficiente para exercitar crop/zoom profissional.
            sample_webp = base / "sample.webp"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=1:duration=0.1",
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

            pro_scenes = [
                {
                    "scene": i,
                    "narrative_role": "development",
                    "pace_multiplier": 1.0,
                    "cut_style": "editorial_cut",
                    "transition_duration": 0.07,
                    "zoom_start": 1.0,
                    "zoom_end": 1.012,
                    "pan": "center",
                }
                for i in range(1, 7)
            ]
            (roteiros / f"pro_edit_plan_{short_id}.json").write_text(
                json.dumps({
                    "version": "PRO_EDIT_TEST",
                    "profile": "default",
                    "style": "premium_documentary",
                    "scenes": pro_scenes,
                    "finish": {"hook_scale": 1.0, "caption_pop": 100},
                    "audio": {"target_lufs": -14.0, "true_peak_db": -1.5},
                }),
                encoding="utf-8",
            )

            ass = videos / f"short_{short_id}.ass"
            ass_text = (
                "[Script Info]\n"
                "ScriptType: v4.00+\n"
                "PlayResX: 1080\n"
                "PlayResY: 1920\n\n"
                "[V4+ Styles]\n"
                "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
                "Style: Dynamic,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,220,1\n\n"
                "[Events]\n"
                "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
                "Dialogue: 0,0:00:00.00,0:00:05.80,Dynamic,,0,0,0,,Teste de render profissional\n"
            )
            ass.write_text(ass_text, encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "SHORTAUTOPRO_BASE": str(base),
                    "SHORT_ID": short_id,
                    "SHORT_QTD_CENAS": "6",
                    "SHORT_PRESET_CENAS": "ultrafast",
                    "SHORT_CRF_CENAS": "30",
                    "SHORT_PRESET": "ultrafast",
                    "SHORT_CRF": "30",
                    "SHORT_USAR_MUSICA": "0",
                    "SHORT_USAR_SFX": "0",
                    "SHORT_USAR_POP": "0",
                    "SHORT_RETENTION_ENGINE": "0",
                    "SAP_MULTI_BEAT_FALLBACK": "0",
                }
            )

            scene_proc = subprocess.run(
                [sys.executable, str(ROOT / "video_professional.py")],
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
            self.assertGreater(base_video.stat().st_size, 100_000)

            final_proc = subprocess.run(
                [sys.executable, str(ROOT / "v6_professional.py")],
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
            self.assertGreater(final_video.stat().st_size, 500_000)

            probe = subprocess.check_output(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate",
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
            self.assertEqual(video_streams[0].get("codec_name"), "h264")
            self.assertEqual(audio_streams[0].get("codec_name"), "aac")
            self.assertEqual(video_streams[0].get("width"), 1080)
            self.assertEqual(video_streams[0].get("height"), 1920)
            self.assertEqual(video_streams[0].get("avg_frame_rate"), "30/1")


if __name__ == "__main__":
    unittest.main()
