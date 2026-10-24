import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2
import render_engine_v2


class V2ReliabilityHardeningTests(unittest.TestCase):
    def test_manifest_has_verifiable_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "INTEGRITY_001"
            scenes = [{"scene_id": "01", "query": "ship", "must_have": ["ship"], "avoid": []}]
            record = {
                "validated": True,
                "checksum_sha256": "a",
                "path": str(base / "imagens" / f"short_{sid}" / "scene_01.jpg"),
                "probe": {},
                "must_hits": 1,
            }
            with patch.object(media_engine_v2, "load_scene_map", return_value=scenes),                  patch.object(media_engine_v2, "acquire_scene", return_value=record):
                payload = media_engine_v2.build_manifest(sid)
            self.assertEqual(
                payload["integrity_sha256"],
                media_engine_v2._manifest_integrity(payload),
            )
            payload["scenes"][0]["asset"]["must_hits"] = 99
            self.assertNotEqual(
                payload["integrity_sha256"],
                media_engine_v2._manifest_integrity(payload),
            )

    def test_query_relaxation_can_recover_real_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td)
            asset = media / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            candidate = {
                "fonte": "Mock",
                "id": "partial",
                "tipo": "imagem",
                "must_hits": 1,
                "avoid_hits": 0,
                "score": 70,
                "url": "https://example.invalid/asset.jpg",
                "descricao": "ship radio",
            }

            def fake_download(_candidate, _number, _sid):
                return True, str(asset), {"sha256": "fixture", "probe": {"width": 1920, "height": 1080}}

            with patch.object(media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]), \
                 patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[]), \
                 patch.object(media_engine_v2.PROVIDER, "download", side_effect=fake_download), \
                 patch.object(media_engine_v2, "validate_asset", return_value={
                     "sha256": "fixture",
                     "probe": {"width": 1920, "height": 1080},
                     "validated": True,
                 }), \
                 patch.object(media_engine_v2, "_verify_scene_pixels", return_value={"status": "PASS", "must": [], "avoid": []}):
                result = media_engine_v2.acquire_scene(
                    "RELAX_001", 1,
                    {"query": "ship radio", "must_have": ["ship", "radio"], "avoid": []},
                    media,
                )
            self.assertEqual(result["verification_mode"], "gemini_visual_must")
            self.assertEqual(result["must_hits"], 2)
            self.assertEqual(result["must_total"], 2)

    def test_render_input_rejects_tampered_frozen_asset(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            render_engine_v2.BASE = base
            sid = "TAMPER_001"
            job = base / "render_jobs" / sid / "render_001"
            job.mkdir(parents=True)
            asset = job / "asset.mp4"
            asset.write_bytes(b"x" * 2000)
            audio = job / "audio.mp3"
            audio.write_bytes(b"y" * 2000)
            ass = job / "sub.ass"
            ass.write_text(
                "[Script Info]\nScriptType: v4.00+\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                "MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,20,20,80,1\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,test\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            adigest = hashlib.sha256(audio.read_bytes()).hexdigest()
            sdigest = hashlib.sha256(ass.read_bytes()).hexdigest()
            job_meta = {"short_id": sid, "render_id": "render_001"}
            manifest = {
                "short_id": sid,
                "assets": [{
                    "scene_id": "01",
                    "asset_path": str(asset),
                    "validation_status": "FROZEN_LOCAL",
                    "checksum_sha256": digest,
                }],
                "audio": {"path": str(audio), "checksum_sha256": adigest},
                "subtitles": {"path": str(ass), "checksum_sha256": sdigest},
            }
            timeline = {"short_id": sid, "scenes": [{"scene_id": "01"}], "subtitles": []}
            (job / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")
            (job / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (job / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
            asset.write_bytes(b"tampered" * 300)
            with self.assertRaisesRegex(RuntimeError, "RENDER_ASSET_CHECKSUM"):
                render_engine_v2.validate_input(job)


if __name__ == "__main__":
    unittest.main()
