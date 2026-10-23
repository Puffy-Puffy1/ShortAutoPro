import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2


class MediaEngineContractTests(unittest.TestCase):
    def test_load_scene_map_normalizes_book_requirements_for_manuscript_query(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_MANUSCRIPT_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "old illustrated manuscript open pages studio lighting",
                        "must_have": ["book", "parchment pages"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["manuscript"])

    def test_load_scene_map_normalizes_tent_fabric_only_when_torn_context_exists(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_TENT_FABRIC_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "torn winter tent fabric in snow",
                        "must_have": ["tent fabric", "snow"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["torn tent", "snow"])

    def test_load_scene_map_normalizes_torn_tent_and_snow_requirements(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_TORN_TENT_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "vintage black and white photo of a torn tent in snowy mountains",
                        "must_have": ["ripped canvas", "snowy background"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["torn tent", "snow"])

    def test_load_scene_map_collapses_duplicate_ocean_water_requirements(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_OCEAN_WATER_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "Bass Strait dark ocean aerial view at dusk",
                        "must_have": ["ocean", "water"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["ocean"])

    def test_load_scene_map_normalizes_skeleton_for_rib_cage_xray_query(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_RIB_CAGE_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "07",
                        "query": "medical x ray showing human rib cage and skeletal structure",
                        "must_have": ["skeleton"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["rib cage"])

    def test_load_scene_map_normalizes_book_page_requirement_for_printed_text_query(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_PRINTED_BOOK_PAGE"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "06",
                        "query": "vintage book page with Persian text printed",
                        "must_have": ["book page"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["page"])

    def test_load_scene_map_normalizes_pilot_to_microphone_for_equipment_query(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_PILOT_RADIO_EQUIPMENT"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "06",
                        "query": "vintage aviation radio microphone and headset equipment",
                        "must_have": ["pilot"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["microphone"])

    def test_load_scene_map_keeps_pilot_when_visual_query_shows_a_person(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_VISIBLE_PILOT"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "pilot screaming inside cockpit wearing headset",
                        "must_have": ["pilot"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["pilot"])

    def test_load_scene_map_uses_musts_to_normalize_ski_winter_gear(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_SOVIET_SKIERS"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "01",
                        "query": "soviet winter mountain expedition snow landscape 1950s",
                        "must_have": ["skiers", "snow", "winter gear"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(
                scenes[0]["must_have"],
                ["skiers", "snow", "ski equipment"],
            )

    def test_scene_contract_fingerprint_is_stable_and_tracks_visual_requirements(self):
        first = {
            "query": "  Blue   Boat ",
            "segment": "Boat on the water",
            "visual_mode": "Object",
            "must_have": ["boat", "water"],
            "avoid": ["airplane", "cartoon"],
        }
        reordered = {
            "query": "blue boat",
            "segment": " boat   on the water ",
            "visual_mode": "object",
            "must_have": ["water", "BOAT", "boat"],
            "avoid": ["cartoon", "airplane"],
        }
        self.assertEqual(
            media_engine_v2._scene_contract_fingerprint(first),
            media_engine_v2._scene_contract_fingerprint(reordered),
        )
        changed = dict(reordered, must_have=["airplane"])
        self.assertNotEqual(
            media_engine_v2._scene_contract_fingerprint(first),
            media_engine_v2._scene_contract_fingerprint(changed),
        )

    def test_cached_asset_is_rejected_when_scene_contract_changes(self):
        with tempfile.TemporaryDirectory() as td:
            media_dir = Path(td) / "short_TEST_CACHE"
            media_dir.mkdir(parents=True)
            asset = media_dir / "scene_01_wikimedia.jpg"
            asset.write_bytes(b"cached fixture")

            old_scene = {
                "query": "red vintage car",
                "segment": "red car",
                "visual_mode": "object",
                "must_have": ["car"],
                "avoid": ["boat"],
            }
            current_scene = {
                "query": "blue wooden boat",
                "segment": "boat offshore",
                "visual_mode": "object",
                "must_have": ["boat"],
                "avoid": ["car"],
            }
            record = {
                "query_relevance": {"ok": True},
                "checksum_sha256": media_engine_v2.sha256(asset),
                "validated": True,
                "short_id": "TEST_CACHE",
                "scene_number": 1,
                "must_total": 1,
                "scene_contract_fingerprint": media_engine_v2._scene_contract_fingerprint(old_scene),
            }
            (media_dir / "scene_01.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

            with patch.object(media_engine_v2, "validate_asset") as validate:
                result = media_engine_v2._existing_asset_record(
                    media_dir, 1, current_scene
                )

            self.assertIsNone(result)
            validate.assert_not_called()

    def test_matching_scene_contract_allows_a_valid_cached_asset(self):
        with tempfile.TemporaryDirectory() as td:
            media_dir = Path(td) / "short_TEST_CACHE"
            media_dir.mkdir(parents=True)
            asset = media_dir / "scene_01_wikimedia.jpg"
            asset.write_bytes(b"valid cached fixture")
            checksum = media_engine_v2.sha256(asset)
            scene = {
                "query": "red vintage car",
                "segment": "red car",
                "visual_mode": "object",
                "must_have": ["car"],
                "avoid": ["boat"],
            }
            record = {
                "query_relevance": {"ok": True},
                "checksum_sha256": checksum,
                "validated": True,
                "short_id": "TEST_CACHE",
                "scene_number": 1,
                "must_total": 1,
                "scene_contract_fingerprint": media_engine_v2._scene_contract_fingerprint(scene),
            }
            (media_dir / "scene_01.json").write_text(
                json.dumps(record), encoding="utf-8"
            )
            probe = {"width": 1920, "height": 1080}
            with patch.object(
                media_engine_v2,
                "validate_asset",
                return_value={"sha256": checksum, "probe": probe},
            ) as validate:
                cached = media_engine_v2._existing_asset_record(
                    media_dir, 1, scene
                )
            self.assertIsNotNone(cached)
            self.assertEqual(cached["scene_contract_fingerprint"], record["scene_contract_fingerprint"])
            validate.assert_called_once()

    def test_load_scene_map_normalizes_soviet_train_without_erasing_era(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_SOVIET_TRAIN_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "02",
                        "query": "vintage soviet train winter tracks Ural mountains",
                        "era": "Soviet Union, 1959",
                        "must_have": ["soviet train"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["train"])
            self.assertEqual(scenes[0]["era"], "Soviet Union, 1959")
            self.assertIn("soviet", scenes[0]["query"].casefold())

    def test_load_scene_map_normalizes_ski_equipment_without_erasing_era(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_SKI_EQUIPMENT_MUST"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "02",
                        "query": "vintage soviet skiing expedition equipment and wooden skis",
                        "era": "Soviet Union, 1959",
                        "must_have": ["vintage equipment", "skis"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["vintage", "ski equipment"])
            self.assertEqual(scenes[0]["era"], "Soviet Union, 1959")
            self.assertIn("wooden skis", scenes[0]["query"].casefold())

    def test_load_scene_map_normalizes_generic_text_for_archive_document_query(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "TEST_ARCHIVE_DOCUMENT_TEXT"
            scripts = base / "roteiros"
            scripts.mkdir(parents=True)
            scene_map = scripts / f"scene_map_{sid}.json"
            scene_map.write_text(
                json.dumps({
                    "scenes": [{
                        "scene_id": "06",
                        "query": "old soviet investigation report paper document with russian text",
                        "must_have": ["document", "text"],
                        "avoid": [],
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "BASE", base):
                scenes = media_engine_v2.load_scene_map(sid)
            self.assertEqual(scenes[0]["must_have"], ["document"])

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
