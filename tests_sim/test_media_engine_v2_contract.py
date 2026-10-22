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

    def test_duplicate_cached_asset_is_reacquired_for_scene(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "TEST_DEDUP"
            scenes = [
                {"scene_id": "01", "query": "ship", "must_have": ["ship"], "avoid": []},
                {"scene_id": "02", "query": "ocean", "must_have": ["ocean"], "avoid": []},
            ]
            first_path = base / "imagens" / f"short_{sid}" / "scene_01_wikimedia.jpg"
            second_path = base / "imagens" / f"short_{sid}" / "scene_02_wikimedia.jpg"
            first_path.parent.mkdir(parents=True)
            first_path.write_bytes(b"first")
            second_path.write_bytes(b"duplicate")
            first = {
                "validated": True, "checksum_sha256": "same", "path": str(first_path),
                "probe": {}, "must_hits": 1, "short_id": sid, "scene_number": 1,
                "must_total": 1,
            }
            duplicate = {
                "validated": True, "checksum_sha256": "same", "path": str(second_path),
                "probe": {}, "must_hits": 1, "short_id": sid, "scene_number": 2,
                "must_total": 1,
            }
            replacement = {
                "validated": True, "checksum_sha256": "unique", "path": str(second_path),
                "probe": {}, "must_hits": 1,
            }
            observed_used_hashes = []
            def reacquire(*args):
                observed_used_hashes.append(set(args[4]))
                return replacement
            with patch.object(media_engine_v2, "load_scene_map", return_value=scenes), \
                 patch.object(media_engine_v2, "_existing_asset_record", side_effect=[first, duplicate]), \
                 patch.object(media_engine_v2, "acquire_scene", side_effect=reacquire):
                payload = media_engine_v2.build_manifest(sid)
            self.assertEqual(payload["scenes"][0]["asset"]["checksum_sha256"], "same")
            self.assertEqual(payload["scenes"][1]["asset"]["checksum_sha256"], "unique")
            self.assertEqual(observed_used_hashes, [{"same"}])

    def test_relaxed_fallback_requires_context_beyond_verified_must(self):
        accept = media_engine_v2._relaxed_relevance_acceptable
        self.assertTrue(
            accept({"query_relevance": {"ok": True, "matched_terms": ["quill", "inkwell"]}}, ["quill pen"])
        )
        self.assertTrue(
            accept({"query_relevance": {"ok": False, "matched_terms": ["inkwell"]}}, ["quill pen"])
        )
        self.assertFalse(
            accept({"query_relevance": {"ok": False, "matched_terms": ["quill"]}}, ["quill pen"])
        )
        self.assertFalse(
            accept({"query_relevance": {"ok": False, "matched_terms": ["money"]}}, ["money"])
        )
        self.assertTrue(accept({}, ["quill pen"]))

    def test_quill_pen_search_variants_are_bounded_and_contextual(self):
        from media_provider_router_v2 import _query_variants
        variants = _query_variants(
            "vintage quill pen and inkwell on old wooden desk",
            ["quill pen"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(any("feather quill" in item.casefold() for item in variants), variants)
        self.assertEqual(variants[0], "vintage quill pen and inkwell on old wooden desk")

    def test_security_sensor_retrieval_variants_are_bounded(self):
        from media_provider_router_v2 import _query_variants
        variants = _query_variants(
            "historical building security equipment",
            ["security sensor"],
        )
        self.assertIn("security sensor", variants)
        self.assertIn("motion sensor", variants)
        self.assertIn("alarm sensor", variants)
        self.assertIn("door sensor", variants)
        self.assertLessEqual(len(variants), 8)

    def test_security_sensor_requires_visual_evidence(self):
        from media_must_verifier import requirement_matches
        self.assertTrue(
            requirement_matches(
                "security sensor",
                {"description": "motion sensor on a security door"},
            )
        )
        self.assertFalse(
            requirement_matches(
                "security sensor",
                {"description": "security camera monitoring a building"},
            )
        )

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
        self.assertLessEqual(len(variants), 8)
