import unittest
from pathlib import Path

from media_provider_v2 import MediaProviderV2
from media_provider_router_v2 import _normalize_image_extension, _query_variants


class MediaProviderV2Tests(unittest.TestCase):
    def test_image_extension_matches_downloaded_signature(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene_01_wikimedia.jpg"
            png.write_bytes(b"\\x89PNG\\r\\n\\x1a\\n" + b"fixture")
            normalized = _normalize_image_extension(png)
            self.assertEqual(normalized.suffix, ".png")
            self.assertTrue(normalized.is_file())
            self.assertFalse(png.exists())

            webp = root / "scene_02_wikimedia.jpg"
            webp.write_bytes(b"RIFF" + b"\\x00\\x00\\x00\\x00" + b"WEBP" + b"fixture")
            normalized = _normalize_image_extension(webp)
            self.assertEqual(normalized.suffix, ".webp")
            self.assertTrue(normalized.is_file())

    def test_unknown_download_signature_is_not_relabelled(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene_01_wikimedia.jpg"
            path.write_bytes(b"<html>rate limited</html>")
            normalized = _normalize_image_extension(path)
            self.assertEqual(normalized, path)
            self.assertTrue(path.is_file())

    def test_provider_boundary_is_small_and_explicit(self):
        self.assertEqual(
            {"search", "prepare", "download"},
            {
                name for name in ("search", "prepare", "download")
                if callable(getattr(MediaProviderV2, name, None))
            },
        )

    def test_provider_boundary_does_not_import_legacy(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("from midia import", source)
        self.assertNotIn("import midia", source)

    def test_provider_boundary_does_not_own_rendering(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg", source.lower())
        self.assertNotIn("SHORT_ID", source)

    def test_maritime_must_uses_bounded_retrieval_aliases(self):
        variants = _query_variants(
            "abandoned wooden brigantine ship drifting in atlantic ocean",
            ["ship"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertIn("ship", variants)
        self.assertTrue(
            any(item in variants for item in ("vessel", "boat", "watercraft")),
            variants,
        )


    def test_car_must_uses_bounded_vehicle_retrieval_aliases(self):
        variants = _query_variants(
            "archival photograph of a car on a city street",
            ["car"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertIn("car", variants)
        self.assertTrue(
            any(item in variants for item in ("automobile", "motor vehicle", "road vehicle")),
            variants,
        )

    def test_retrieval_aliases_do_not_weaken_strict_acceptance(self):
        provider = MediaProviderV2(router=object())
        candidate = {
            "id": "metadata-does-not-prove-ship",
            "fonte": "Mock",
            "must_hits": 0,
            "avoid_hits": 0,
            "score": 100,
            "descricao": "A vessel at sea",
        }
        self.assertEqual(provider.prepare([candidate], 1), [])

    def test_prepare_prefers_strict_must_verification(self):
        provider = MediaProviderV2(router=object())
        candidates = [
            {"id": "strict", "fonte": "Mock", "must_hits": 2, "avoid_hits": 0, "score": 50},
            {"id": "partial", "fonte": "Mock", "must_hits": 1, "avoid_hits": 0, "score": 90},
        ]
        result = provider.prepare(candidates, 2)
        self.assertEqual([x["id"] for x in result], ["strict"])

    def test_prepare_fails_closed_when_strict_must_is_empty(self):
        provider = MediaProviderV2(router=object())
        candidates = [
            {"id": "weak", "fonte": "Mock", "must_hits": 1, "avoid_hits": 0, "score": 30},
            {"id": "good", "fonte": "Mock", "must_hits": 1, "avoid_hits": 0, "score": 60},
            {"id": "wrong", "fonte": "Mock", "must_hits": 0, "avoid_hits": 0, "score": 100},
            {"id": "unsafe", "fonte": "Mock", "must_hits": 2, "avoid_hits": 1, "score": 100},
        ]
        self.assertEqual(provider.prepare(candidates, 2), [])


if __name__ == "__main__":
    unittest.main()
