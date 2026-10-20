import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_provider_router_v2 import MediaProviderRouterV2, _query_variants
from media_validator_v2 import validate
from media_must_verifier import verified_must
import media_engine_v2
import render_engine_v2

class FakeProvider:
    def __init__(self,name,candidates): self.name=name; self.candidates=candidates
    def search(self,query,must,avoid,**kwargs): return list(self.candidates)

class AcquisitionV2Tests(unittest.TestCase):
    def test_canvas_tent_must_accepts_asset_metadata_for_tent(self):
        result = verified_must(
            {"title": "A damaged camping tent in a snowy field", "description": "snowfall"},
            {"must_have": ["canvas tent", "snow"]},
        )
        self.assertEqual(result["hits"], 2)
        self.assertEqual(result["missing"], [])

    def test_train_must_accepts_asset_metadata_for_locomotive(self):
        result = verified_must(
            {"title": "Soviet steam locomotive in winter", "description": "railway transport"},
            {"must_have": ["train"]},
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["missing"], [])

    def test_topographic_map_retrieval_aliases_are_bounded_and_used(self):
        variants = _query_variants(
            "topographic map of Dyatlov Pass Kholat Syakhl Ural mountains",
            ["topographic map"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertIn("contour map", variants)
        self.assertIn("relief map", variants)

    def test_topographic_map_must_accepts_specific_map_metadata(self):
        result = verified_must(
            {"title": "Topographical contour map of the Ural Mountains"},
            {"must_have": ["topographic map"]},
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["missing"], [])

    def test_topographic_map_must_does_not_accept_search_query_as_evidence(self):
        result = verified_must(
            {"title": "Winter landscape of the Ural Mountains", "query": "topographic map"},
            {"must_have": ["topographic map"]},
        )
        self.assertEqual(result["hits"], 0)
        self.assertEqual(result["missing"], ["topographic map"])

    def test_train_must_does_not_accept_search_query_as_evidence(self):
        result = verified_must(
            {"title": "Snowy mountain expedition", "query": "Soviet train in winter"},
            {"must_have": ["train"]},
        )
        self.assertEqual(result["hits"], 0)
        self.assertEqual(result["missing"], ["train"])

    def test_manuscript_must_accepts_asset_metadata_alias(self):
        result = verified_must(
            {"title": "15th-century illuminated manuscript leaf"},
            {"must_have": ["manuscript"]},
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["missing"], [])

    def test_manuscript_must_does_not_accept_search_query_as_evidence(self):
        result = verified_must(
            {"title": "Old parchment page", "query": "medieval manuscript"},
            {"must_have": ["manuscript"]},
        )
        self.assertEqual(result["hits"], 0)
        self.assertEqual(result["missing"], ["manuscript"])

    def test_canvas_tent_must_does_not_accept_search_query_as_evidence(self):
        result = verified_must(
            {"title": "A snowy landscape in the mountains", "query": "canvas tent in snow"},
            {"must_have": ["canvas tent", "snow"]},
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["missing"], ["canvas tent"])

    def test_router_retries_bounded_query_when_provider_returns_empty(self):
        class QuerySensitiveProvider:
            name = "test"
            def __init__(self):
                self.queries = []
            def search(self, query, must, avoid, **kwargs):
                self.queries.append(query)
                if query == "very long overly specific maritime documentary visual query":
                    return []
                return [{
                    "fonte": "test",
                    "tipo": "image",
                    "id": "fallback-1",
                    "url": "https://example.invalid/fallback.jpg",
                    "descricao": "maritime ship",
                    "must_hits": 1,
                    "avoid_hits": 0,
                    "score": 60,
                }]
        provider = QuerySensitiveProvider()
        router = MediaProviderRouterV2([provider])
        candidates = router.search(
            "very long overly specific maritime documentary visual query",
            ["ship"],
            [],
        )
        self.assertEqual([c["id"] for c in candidates], ["fallback-1"])
        self.assertGreaterEqual(len(provider.queries), 2)
        self.assertEqual(provider.queries[0], "very long overly specific maritime documentary visual query")

    def test_router_query_fallback_does_not_relax_avoid_filter(self):
        class Provider:
            name = "test"
            def search(self, query, must, avoid, **kwargs):
                return [{
                    "fonte": "test",
                    "tipo": "image",
                    "id": "bad",
                    "url": "https://example.invalid/bad.jpg",
                    "descricao": "ship radio",
                    "must_hits": 1,
                    "avoid_hits": 1,
                    "score": 90,
                }]
        router = MediaProviderRouterV2([Provider()])
        self.assertEqual(router.search("very long query", ["ship"], ["radio"]), [])

    def test_router_falls_back_per_asset(self):
        a={"fonte":"pexels","tipo":"video","id":"a","url":"https://invalid/a.mp4","must_hits":1,"avoid_hits":0,"score":90}
        b={"fonte":"pixabay","tipo":"video","id":"b","url":"https://invalid/b.mp4","must_hits":1,"avoid_hits":0,"score":80}
        router=MediaProviderRouterV2([FakeProvider("pexels",[a]),FakeProvider("pixabay",[b])])
        self.assertEqual([x["id"] for x in router.search("x",["x"],[])],["a","b"])

    def test_router_rejects_path_traversal_short_id(self):
        class DownloadProvider:
            name = "test"
            def search(self, query, must, avoid):
                return []
        router = MediaProviderRouterV2([DownloadProvider()])
        with patch("media_provider_router_v2.requests.get") as get:
            ok, path, meta = router.download(
                {"fonte": "test", "tipo": "video", "id": "x", "url": "https://example.invalid/x.mp4"},
                1,
                "../ESCAPE",
            )
        self.assertFalse(ok)
        self.assertEqual(meta["error_class"], "SHORT_ID_INVALID")
        get.assert_not_called()

    def test_router_rejects_invalid_scene_number(self):
        router = MediaProviderRouterV2([])
        ok, path, meta = router.download(
            {"fonte": "test", "tipo": "video", "id": "x", "url": "https://example.invalid/x.mp4"},
            0,
            "SAFE_SHORT",
        )
        self.assertFalse(ok)
        self.assertEqual(meta["error_class"], "SCENE_NUMBER_INVALID")

    def test_engine_retries_next_candidate_after_download_failure(self):
        class FakeEngineProvider:
            def __init__(self):
                self.calls = []
            def search(self, *args, **kwargs):
                return [
                    {"fonte": "pexels", "id": "a", "tipo": "video", "must_hits": 1, "avoid_hits": 0},
                    {"fonte": "pixabay", "id": "b", "tipo": "video", "must_hits": 1, "avoid_hits": 0},
                ]
            def prepare(self, candidates, total_must):
                return candidates
            def download(self, candidate, scene_number, short_id):
                self.calls.append(candidate["id"])
                if candidate["id"] == "a":
                    return False, "", {"error_class": "DOWNLOAD_FAILED"}
                return True, "/tmp/verified-b.mp4", {"validated": True}
        fake = FakeEngineProvider()
        with patch.object(media_engine_v2, "PROVIDER", fake), \
             patch.object(media_engine_v2, "validate_asset", return_value={"probe": {"width": 1920, "height": 1080}, "sha256": "b"}), \
             patch.object(media_engine_v2, "_candidate_record", return_value={"asset_id": "b"}):
            result = media_engine_v2.acquire_scene(
                "SID_B", 1, {"query": "test", "must_have": ["test"], "avoid": []}, Path("/tmp")
            )
        self.assertEqual(fake.calls, ["a", "b"])
        self.assertEqual(result["asset_id"], "b")

    def test_resume_existing_asset_does_not_query_provider(self):
        with tempfile.TemporaryDirectory() as td:
            media_dir = Path(td)
            asset = media_dir / "scene_01.jpg"
            sidecar = media_dir / "scene_01.json"
            asset.write_bytes(b"x" * 2000)
            digest = media_engine_v2.sha256(asset)
            sidecar.write_text(
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1, "validated": True, "short_id": media_dir.name.removeprefix("short_"), "scene_number": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}), \
                 patch.object(media_engine_v2, "validate_asset", return_value={"sha256": digest, "probe": {"width": 1080, "height": 1920}, "validated": True}):
                record = media_engine_v2._existing_asset_record(
                    media_dir, 1, {"must_have": ["test"]}
                )
            self.assertIsNotNone(record)
            self.assertEqual(record["checksum_sha256"], digest)

    def test_validator_rejects_html_jpg(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.jpg"
            p.write_bytes(b"<html>" + b"x"*2000)
            with self.assertRaises(ValueError):
                validate(p)

    def test_validator_rejects_empty_media(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.mp4"; p.write_bytes(b"")
            with self.assertRaises(ValueError):
                validate(p)

    def test_provider_module_does_not_import_legacy(self):
        import media_provider_v2
        self.assertNotIn("midia", getattr(media_provider_v2,"__dict__",{}))

    def test_short_ids_are_isolated_by_router_output_path(self):
        router = MediaProviderRouterV2([])
        with patch("media_provider_router_v2.requests.get") as get:
            get.side_effect = AssertionError("network must not be reached for invalid IDs")
            for sid in ("../OTHER", "short/../OTHER", "A B"):
                ok, _, meta = router.download(
                    {"fonte": "test", "tipo": "video", "id": "x", "url": "https://example.invalid/x.mp4"},
                    1, sid,
                )
                self.assertFalse(ok)
                self.assertEqual(meta["error_class"], "SHORT_ID_INVALID")

    def test_existing_asset_is_scoped_to_media_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            media_a = root / "short_A"
            media_b = root / "short_B"
            media_a.mkdir(); media_b.mkdir()
            asset = media_a / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            digest = media_engine_v2.sha256(asset)
            (media_a / "scene_01.json").write_text(
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1, "validated": True, "short_id": media_a.name.removeprefix("short_"), "scene_number": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}), \
                 patch.object(media_engine_v2, "validate_asset", return_value={"sha256": digest, "probe": {"width": 1080, "height": 1920}, "validated": True}):
                self.assertIsNotNone(media_engine_v2._existing_asset_record(media_a, 1, {"must_have": ["x"]}))
                self.assertIsNone(media_engine_v2._existing_asset_record(media_b, 1, {"must_have": ["x"]}))

    def test_validator_rejects_fake_tiny_or_uniform_jpeg_signature(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fake.jpg"
            p.write_bytes(b"\xff\xd8\xff" + b"\x00" * 3000)
            with patch("media_validator_v2.probe", side_effect=ValueError("PROBE_FAIL")):
                with self.assertRaises(ValueError):
                    validate(p)

    def test_validator_rejects_invalid_visual_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.jpg"
            p.write_bytes(b"\xff\xd8\xff" + b"x" * 3000)
            with patch("media_validator_v2.probe", side_effect=ValueError("INVALID_DIMENSIONS")):
                with self.assertRaisesRegex(ValueError, "INVALID_DIMENSIONS"):
                    validate(p)

    def test_build_manifest_reuses_verified_asset_without_provider(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "SHORT_A"
            (base / "roteiros").mkdir()
            (base / "imagens" / f"short_{sid}").mkdir(parents=True)
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                __import__("json").dumps({"scenes": [{"query": "test", "must_have": ["test"]}]}),
                encoding="utf-8",
            )
            asset = base / "imagens" / f"short_{sid}" / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            digest = media_engine_v2.sha256(asset)
            (asset.parent / "scene_01.json").write_text(
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1, "validated": True, "short_id": sid, "scene_number": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}), \
                 patch.object(media_engine_v2, "validate_asset", return_value={"sha256": digest, "probe": {"width": 1080, "height": 1920}, "validated": True}), \
                 patch.object(media_engine_v2.PROVIDER, "search", side_effect=AssertionError("resume must not query")):
                manifest = media_engine_v2.build_manifest(sid)
            self.assertEqual(manifest["short_id"], sid)
            self.assertEqual(manifest["scene_count"], 1)
            self.assertTrue((base / "manifests" / f"media_{sid}.json").is_file())

    def test_manifest_matches_render_engine_v2_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "SHORT_CONTRACT"
            (base / "roteiros").mkdir()
            (base / "imagens" / f"short_{sid}").mkdir(parents=True)
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                __import__("json").dumps({"scenes": [{"scene_id": "s1", "query": "test", "must_have": []}]}),
                encoding="utf-8",
            )
            asset = base / "imagens" / f"short_{sid}" / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            digest = media_engine_v2.sha256(asset)
            (asset.parent / "scene_01.json").write_text(
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 0, "validated": True, "short_id": sid, "scene_number": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}), \
                 patch.object(media_engine_v2, "validate_asset", return_value={"sha256": digest, "probe": {"width": 1080, "height": 1920}, "validated": True}):
                manifest = media_engine_v2.build_manifest(sid)
            self.assertEqual(manifest["schema_version"], "media-manifest-v2")
            self.assertEqual(manifest["short_id"], sid)
            self.assertEqual(len(manifest["scenes"]), 1)
            self.assertIsInstance(manifest["scenes"][0]["asset"], dict)
            self.assertTrue(manifest["scenes"][0]["asset"]["validated"])
            self.assertTrue((base / "manifests" / f"media_{sid}.json").is_file())

    def test_render_manifest_rejects_cross_short_asset(self):
        source = __import__("render_engine_v2")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "SHORT_A"
            other = base / "imagens" / "short_SHORT_B"
            other.mkdir(parents=True)
            asset = other / "scene_01.jpg"
            asset.write_bytes(b"x" * 2000)
            manifest = {
                "schema_version": "media-manifest-v2", "short_id": sid,
                "scene_count": 1, "scenes": [{"asset": {"validated": True, "path": str(asset)}}],
            }
            (base / "roteiros").mkdir()
            (base / "audios").mkdir()
            (base / "videos").mkdir()
            (base / "manifests").mkdir()
            (base / "roteiros" / ("scene_map_" + sid + ".json")).write_text(__import__("json").dumps({"scenes":[{}]}), encoding="utf-8")
            (base / "roteiros" / ("pro_edit_plan_" + sid + ".json")).write_text(__import__("json").dumps({"scenes":[{}]}), encoding="utf-8")
            (base / "manifests" / ("media_" + sid + ".json")).write_text(__import__("json").dumps(manifest), encoding="utf-8")
            (base / "audios" / ("short_" + sid + ".mp3")).write_bytes(b"x")
            source.BASE = base
            with patch.object(source, "audio_duration", return_value=1.0):
                with self.assertRaisesRegex(RuntimeError, "media_manifest_asset_scope"):
                    source.build_job(sid)


    def test_render_validate_input_rejects_cross_short_job_scope(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            job = base / "render_jobs" / "SHORT_A" / "render_001"
            job.mkdir(parents=True)
            (base / "imagens" / "short_SHORT_A").mkdir(parents=True)
            (job / "job.json").write_text('{"short_id":"SHORT_B","render_id":"render_001"}', encoding="utf-8")
            (job / "manifest.json").write_text('{"short_id":"SHORT_B","assets":[]}', encoding="utf-8")
            (job / "timeline.json").write_text('{"short_id":"SHORT_B","scenes":[]}', encoding="utf-8")
            with patch.object(render_engine_v2, "BASE", base):
                with self.assertRaisesRegex(RuntimeError, "job_scope"):
                    render_engine_v2.validate_input(job)

    def test_render_main_revalidates_existing_passed_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "SHORT_PASS_REVALIDATE"
            job = base / "render_jobs" / sid / "render_001"
            job.mkdir(parents=True)
            (job / "state.json").write_text(
                __import__("json").dumps({"status": "PASSED"}), encoding="utf-8"
            )
            (job / "render_report.json").write_text(
                __import__("json").dumps({"status": "PASSED", "short_id": sid}), encoding="utf-8"
            )
            (job / "job.json").write_text(
                __import__("json").dumps({"short_id": sid, "render_id": "render_001", "duration_target": 1}),
                encoding="utf-8",
            )
            (job / "manifest.json").write_text(
                __import__("json").dumps({"short_id": sid, "assets": []}), encoding="utf-8"
            )
            (job / "timeline.json").write_text(
                __import__("json").dumps({"short_id": sid, "scenes": []}), encoding="utf-8"
            )
            (base / "roteiros").mkdir()
            (base / "audios").mkdir()
            (base / "videos").mkdir()
            (base / "manifests").mkdir()
            (base / "roteiros" / ("scene_map_" + sid + ".json")).write_text(
                __import__("json").dumps({"scenes": []}), encoding="utf-8"
            )
            (base / "roteiros" / ("pro_edit_plan_" + sid + ".json")).write_text(
                __import__("json").dumps({"scenes": []}), encoding="utf-8"
            )
            (base / "audios" / ("short_" + sid + ".mp3")).write_bytes(b"x")
            (base / "videos" / ("short_" + sid + ".ass")).write_text("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Test\n", encoding="utf-8")
            (base / "videos" / ("short_v6_" + sid + ".mp4")).write_bytes(b"x" * 2000)
            media = base / "imagens" / ("short_" + sid)
            media.mkdir(parents=True)
            media_asset = media / "scene_01.jpg"
            media_manifest = {"schema_version": "media-manifest-v2", "short_id": sid, "immutable": True,
                              "scene_count": 1, "scenes": [{"scene_id": "1", "scene_number": 1,
                              "asset": {"validated": True, "path": str(media_asset)}}]}
            (base / "manifests" / ("media_" + sid + ".json")).write_text(__import__("json").dumps(media_manifest), encoding="utf-8")
            (base / "roteiros" / ("scene_map_" + sid + ".json")).write_text(__import__("json").dumps({"scenes": [{"scene": 1, "segment": "test", "words": 1}]}), encoding="utf-8")
            (base / "roteiros" / ("pro_edit_plan_" + sid + ".json")).write_text(__import__("json").dumps({"scenes": [{"scene": 1, "pace_multiplier": 1.0}]}), encoding="utf-8")
            with patch.object(render_engine_v2, "BASE", base):
                with patch.object(render_engine_v2, "audio_duration", return_value=1.0):
                    with patch.object(
                        render_engine_v2, "validate_output",
                        side_effect=RuntimeError("QUALITY_GATE_FAIL:stale_output"),
                    ) as validate:
                        with patch.object(
                            render_engine_v2.sys, "argv",
                            ["render_engine_v2.py", "--short-id", sid],
                        ):
                            self.assertNotEqual(render_engine_v2.main(), 0)
                        validate.assert_called_once()

    def test_render_main_does_not_trust_stale_passed_state(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "SHORT_PASS"
            job = base / "render_jobs" / sid / "render_001"
            job.mkdir(parents=True)
            (job / "state.json").write_text('{"status":"PASSED"}', encoding="utf-8")
            (job / "render_report.json").write_text('{"status":"PASSED","short_id":"SHORT_PASS"}', encoding="utf-8")
            (job / "job.json").write_text('{"short_id":"SHORT_PASS","render_id":"render_001","duration_target":1}', encoding="utf-8")
            (job / "manifest.json").write_text('{"short_id":"SHORT_PASS","assets":[]}', encoding="utf-8")
            (job / "timeline.json").write_text('{"short_id":"SHORT_PASS","scenes":[]}', encoding="utf-8")
            (base / "roteiros").mkdir()
            (base / "audios").mkdir()
            (base / "manifests").mkdir()
            (base / "imagens" / ("short_" + sid)).mkdir(parents=True)
            (base / "roteiros" / ("scene_map_" + sid + ".json")).write_text('{"scenes":[{"scene":1,"segment":"test","words":1}]}', encoding="utf-8")
            (base / "roteiros" / ("pro_edit_plan_" + sid + ".json")).write_text('{"scenes":[{"scene":1,"pace_multiplier":1.0}]}', encoding="utf-8")
            (base / "audios" / ("short_" + sid + ".mp3")).write_bytes(b"x")
            (base / "videos").mkdir()
            (base / "videos" / ("short_" + sid + ".ass")).write_text("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Test\n", encoding="utf-8")
            asset = base / "imagens" / ("short_" + sid) / "scene_01.jpg"
            media_manifest = {"schema_version":"media-manifest-v2","short_id":sid,"immutable":True,"scene_count":1,
                              "scenes":[{"scene_id":"1","scene_number":1,"asset":{"validated":True,"path":str(asset)}}]}
            (base / "manifests" / ("media_" + sid + ".json")).write_text(__import__("json").dumps(media_manifest), encoding="utf-8")
            with patch.object(render_engine_v2, "BASE", base):
                with patch.object(render_engine_v2, "audio_duration", return_value=1.0):
                    with patch.object(render_engine_v2.sys, "argv", ["render_engine_v2.py", "--short-id", sid]):
                        self.assertNotEqual(render_engine_v2.main(), 0)

if __name__ == "__main__":
    unittest.main()
