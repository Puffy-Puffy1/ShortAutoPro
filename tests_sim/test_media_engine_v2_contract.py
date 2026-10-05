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
                {"scene_id": "01", "query": "ship", "must_have": ["ship"], "avoid": []},
                {"scene_id": "02", "query": "ocean", "must_have": ["ocean"], "avoid": []},
            ]
            records = [
                {"validated": True, "checksum_sha256": "a", "path": "/tmp/a", "probe": {}, "must_hits": 1},
                {"validated": True, "checksum_sha256": "b", "path": "/tmp/b", "probe": {}, "must_hits": 1},
            ]
            p = base / "manifests" / f"media_{sid}.json"
            with patch.object(media_engine_v2, "load_scene_map", return_value=scenes),                  patch.object(media_engine_v2, "acquire_scene", side_effect=records):
                payload = media_engine_v2.build_manifest(sid)
            media_engine_v2.atomic_json(p, payload)
            data = json.loads(p.read_text())
            self.assertEqual(data["schema_version"], "media-manifest-v2")
            self.assertEqual(data["engine_version"], media_engine_v2.ENGINE_VERSION)
            self.assertEqual(data["short_id"], sid)
            self.assertTrue(data["immutable"])
            self.assertEqual(data["scene_count"], 2)
            self.assertEqual(len(data["scenes"]), 2)
            self.assertEqual(data["scenes"][0]["asset"]["checksum_sha256"], "a")
            self.assertEqual(data["scenes"][1]["asset"]["checksum_sha256"], "b")

    def test_no_render_or_stage6_import(self):
        source = Path("media_engine_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("media_stage_runtime", source)
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg_visual_renderer", source)

    def test_provider_failure_contract(self):
        with patch.object(media_engine_v2.PROVIDER, "search", side_effect=RuntimeError("provider timeout")):
            with self.assertRaises(RuntimeError) as ctx:
                media_engine_v2.acquire_scene(
                    "X", 1, {"query": "ship", "must_have": ["ship"]}, Path(tempfile.mkdtemp())
                )
            self.assertIn("provider timeout", str(ctx.exception))


    def test_provider_router_query_recovery_preserves_must_anchors(self):
        from media_provider_router_v2 import _query_variants
        variants = _query_variants(
            "long editorial query with noisy historical context",
            ["ship", "ocean"],
        )
        self.assertIn("ship ocean", variants)
        self.assertIn("ship", variants)
        self.assertIn("ocean", variants)
        self.assertLessEqual(len(variants), 4)
