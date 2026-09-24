import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "production_manifest.py"


class ProductionManifestTests(unittest.TestCase):
    def base_env(self, base):
        env = os.environ.copy()
        env.update(
            {
                "SHORTAUTOPRO_BASE": str(base),
                "SHORT_ID": "case",
                "SHORT_QTD_CENAS": "6",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        return env

    def test_incomplete_manifest_returns_failure_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=str(REPO),
                env=self.base_env(base),
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest_path = base / "manifests" / "case.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "INCOMPLETE")
            self.assertFalse(manifest["quality"]["video_exists"])
            self.assertFalse(manifest["quality"]["video_codec_ok"])
            self.assertFalse(manifest["quality"]["audio_codec_ok"])

    def test_complete_synthetic_v6_contract_can_pass_without_real_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r = base / "roteiros"
            media = base / "imagens" / "short_case"
            credits = base / "credits"
            videos = base / "videos"
            manifests = base / "manifests"
            for path in (r, media, credits, videos, manifests):
                path.mkdir(parents=True, exist_ok=True)

            (r / "used_topic_case.txt").write_text("Caso de Teste", encoding="utf-8")
            (r / "hook_case.txt").write_text(
                "Este caso ainda levanta perguntas importantes.", encoding="utf-8"
            )
            (r / "short_case.txt").write_text(
                " ".join(f"palavra{i}" for i in range(110)), encoding="utf-8"
            )
            (r / "fonte_case.txt").write_text(
                "ASSUNTO: Caso de Teste\nFONTE: Wikipedia — Caso de Teste",
                encoding="utf-8",
            )
            (r / "scene_map_case.json").write_text(
                json.dumps(
                    {
                        "scenes": [
                            {"scene": i, "query": f"scene {i}"}
                            for i in range(1, 7)
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (r / "publish_case.json").write_text(
                json.dumps(
                    {
                        "chosen_title": "Um título factual de teste para publicação",
                        "titles": ["Um título factual de teste para publicação"],
                        "description": "Descrição factual suficientemente completa para o teste.",
                        "hashtags": ["#Shorts", "#Caso", "#Teste", "#Fatos", "#Video"],
                        "pinned_comment": "Qual é a sua opinião?",
                    }
                ),
                encoding="utf-8",
            )
            (r / "publish_integrity_case.json").write_text(
                json.dumps({"status": "PASS"}), encoding="utf-8"
            )
            (credits / "ledger_case.json").write_text(
                json.dumps({"short_id": "case"}), encoding="utf-8"
            )
            (r / "media_quality_case.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "critical": [],
                    "neutral_editorial_scenes": [],
                }),
                encoding="utf-8",
            )
            evolution = base / "reports" / "evolution"
            evolution.mkdir(parents=True, exist_ok=True)
            (evolution / "visual_qa_case.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "measurements": {
                        "rendered_content": {
                            "available": True,
                            "opening_blank": False,
                            "blank_scenes": [],
                        }
                    },
                }),
                encoding="utf-8",
            )
            for i in range(1, 7):
                suffix = ".webp" if i == 1 else ".jpg"
                (media / f"scene_{i:02d}{suffix}").write_bytes(b"asset")
            (videos / "short_v6_case.mp4").write_bytes(b"0" * 600_000)
            import hashlib
            topic = "Caso de Teste"
            (manifests / "case_render_identity.json").write_text(
                json.dumps({
                    "schema": "SHORTAUTOPRO_RENDER_IDENTITY_V1",
                    "short_id": "case",
                    "topic": topic,
                    "topic_sha256": hashlib.sha256(topic.encode("utf-8")).hexdigest(),
                }),
                encoding="utf-8",
            )

            probe = {
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
            code = (
                "import json, production_manifest as p; "
                f"m, ok = p.build_manifest({probe!r}); "
                "print(json.dumps({'ok': ok, 'status': m['status'], 'quality': m['quality']}))"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(REPO),
                env=self.base_env(base),
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertTrue(payload["ok"], payload["quality"])
            self.assertEqual(payload["status"], "QUALITY_PASS")
            self.assertTrue(payload["quality"]["video_codec_ok"])
            self.assertTrue(payload["quality"]["audio_codec_ok"])

    def test_overlong_duration_blocks_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code = (
                "import production_manifest as p; "
                "m, ok = p.build_manifest({'streams': [], 'format': {'duration': '181'}}); "
                "print(ok, m['quality']['duration_ok'])"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(REPO),
                env=self.base_env(base),
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("False False", result.stdout)

    def test_wrong_codecs_block_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            probe = {
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "vp9",
                        "width": 1080,
                        "height": 1920,
                        "avg_frame_rate": "30/1",
                    },
                    {"codec_type": "audio", "codec_name": "opus"},
                ],
                "format": {"duration": "45"},
            }
            code = (
                "import json, production_manifest as p; "
                f"m, ok = p.build_manifest({probe!r}); "
                "print(json.dumps({'ok': ok, 'video': m['quality']['video_codec_ok'], 'audio': m['quality']['audio_codec_ok']}))"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(REPO),
                env=self.base_env(base),
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertFalse(payload["ok"])
            self.assertFalse(payload["video"])
            self.assertFalse(payload["audio"])


if __name__ == "__main__":
    unittest.main()
