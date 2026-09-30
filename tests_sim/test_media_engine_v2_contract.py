import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2


class MediaEngineContractTests(unittest.TestCase):
    def test_manifest_schema_is_frozen_and_complete(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "TEST_MEDIA_V2"
            scenes = [
                {"scene_id":"01","query":"ship","must_have":["ship"],"avoid":[]},
                {"scene_id":"02","query":"ocean","must_have":["ocean"],"avoid":[]},
            ]
            p = base / "manifests" / f"media_{sid}.json"
            payload = media_engine_v2.build_manifest(sid, scenes, [
                {"validated":True,"checksum_sha256":"a","path":"/tmp/a","probe":{}},
                {"validated":True,"checksum_sha256":"b","path":"/tmp/b","probe":{}},
            ])
            media_engine_v2.atomic_json(p, payload)
            data=json.loads(p.read_text())
            self.assertEqual(data["schema_version"], "media-manifest-v2")
            self.assertTrue(data["immutable"])
            self.assertEqual(len(data["scenes"]), 2)

    def test_no_render_or_stage6_import(self):
        source = Path("media_engine_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("media_stage_runtime", source)
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg_visual_renderer", source)

    def test_provider_failure_contract(self):
        with patch.object(media_engine_v2, "buscar_todos_candidatos", side_effect=RuntimeError("provider timeout")):
            with self.assertRaises(RuntimeError) as ctx:
                media_engine_v2.acquire_scene("X", 1, {"query":"ship","must_have":["ship"]}, Path(tempfile.mkdtemp()))
            self.assertIn("provider timeout", str(ctx.exception))
