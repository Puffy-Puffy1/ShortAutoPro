import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_provider_router_v2 import MediaProviderRouterV2
from media_provider_router_v2 import MediaProvider
from media_validator_v2 import validate
import media_engine_v2

class FakeProvider:
    def __init__(self,name,candidates): self.name=name; self.candidates=candidates
    def search(self,query,must,avoid): return list(self.candidates)

class AcquisitionV2Tests(unittest.TestCase):
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
                    return False, ""
                return True, "/tmp/verified-b.mp4"

        fake = FakeEngineProvider()
        fake.download = lambda candidate, scene_number, short_id: (
            (False, "", {"error_class": "DOWNLOAD_FAILED"})
            if candidate["id"] == "a"
            else (True, "/tmp/verified-b.mp4", {"validated": True})
        )
        with patch.object(media_engine_v2, "PROVIDER", fake), \
             patch.object(media_engine_v2, "validate_asset", return_value={"probe": {}, "sha256": "b"}), \
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
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}):
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
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}):
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
                __import__("json").dumps({"checksum_sha256": digest, "must_total": 1}),
                encoding="utf-8",
            )
            with patch.object(media_engine_v2, "ffprobe_asset", return_value={"width": 1080, "height": 1920}),                  patch.object(media_engine_v2.PROVIDER, "search", side_effect=AssertionError("resume must not query")):
                manifest = media_engine_v2.build_manifest(sid)
            self.assertEqual(manifest["short_id"], sid)
            self.assertEqual(manifest["scene_count"], 1)
            self.assertTrue((base / "roteiros" / f"media_manifest_v2_{sid}.json").is_file())

if __name__ == "__main__":
    unittest.main()
