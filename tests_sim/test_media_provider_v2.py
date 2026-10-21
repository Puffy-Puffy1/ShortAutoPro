import unittest
from pathlib import Path

from media_provider_v2 import MediaProviderV2
from media_provider_router_v2 import _normalize_image_extension, _query_variants, _wikimedia_image_url


class MediaProviderV2Tests(unittest.TestCase):
    def test_image_extension_matches_downloaded_signature(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene_01_wikimedia.jpg"
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fixture")
            normalized = _normalize_image_extension(png)
            self.assertEqual(normalized.suffix, ".png")
            self.assertTrue(normalized.is_file())
            self.assertFalse(png.exists())

            webp = root / "scene_02_wikimedia.jpg"
            webp.write_bytes(b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"fixture")
            normalized = _normalize_image_extension(webp)
            self.assertEqual(normalized.suffix, ".webp")
            self.assertTrue(normalized.is_file())

    def test_wikimedia_uses_large_thumbnail_when_available(self):
        info = {
            "thumburl": "https://example.test/thumb.jpg",
            "url": "https://example.test/original.jpg",
            "thumbwidth": 1920,
            "thumbheight": 1080,
            "width": 4000,
            "height": 3000,
        }
        self.assertEqual(_wikimedia_image_url(info), info["thumburl"])

    def test_wikimedia_falls_back_to_original_when_thumbnail_is_too_small(self):
        info = {
            "thumburl": "https://example.test/thumb.jpg",
            "url": "https://example.test/original.jpg",
            "thumbwidth": 640,
            "thumbheight": 480,
            "width": 2400,
            "height": 1600,
        }
        self.assertEqual(_wikimedia_image_url(info), info["url"])

    def test_wikimedia_keeps_available_url_when_resolution_is_unknown(self):
        info = {"thumburl": "https://example.test/thumb.jpg", "url": ""}
        self.assertEqual(_wikimedia_image_url(info), info["thumburl"])

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


    def test_darkness_alias_preserves_scene_context(self):
        variants = _query_variants(
            "dark snowy mountain slope at night winter storm",
            ["darkness"],
        )
        self.assertLessEqual(len(variants), 8)
        self.assertTrue(
            any(
                "snowy mountain slope" in item.casefold()
                and "nighttime" in item.casefold()
                for item in variants
            ),
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

    def test_query_relevance_ignores_generic_wikimedia_categories(self):
        from media_provider_router_v2 import query_relevance

        candidate = {
            "title": "Portrait of Lord Buddha created with money in Kahtein festival",
            "image_description": "Portrait created from money",
            "tags": ["Category:Money", "Category:Portraits"],
            "descricao": "Category:Money Category:Portraits",
        }
        result = query_relevance("bundle of twenty dollar bills ransom money", candidate)
        self.assertFalse(result["ok"])
        self.assertEqual(result["matched_terms"], ["money"])

    def test_query_relevance_accepts_specific_title_and_description_match(self):
        from media_provider_router_v2 import query_relevance

        candidate = {
            "title": "Vintage Boeing 727 on airport tarmac",
            "image_description": "Vintage Boeing 727 parked on airport tarmac",
            "tags": ["Category:Airplanes"],
        }
        result = query_relevance("vintage Boeing 727 on airport tarmac", candidate)
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["ratio"], 0.6)

    def test_query_relevance_accepts_relevant_partial_title_for_long_scene_query(self):
        from media_provider_router_v2 import query_relevance

        candidate = {
            "title": "Pine forest in winter after snowfall",
            "image_description": "Snow-covered conifer forest",
            "tags": ["Category:Forests"],
        }
        result = query_relevance(
            "frigid Ural mountains forest winter snowstorm", candidate
        )
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["matched_count"], 2)

    def test_query_relevance_still_rejects_single_generic_overlap(self):
        from media_provider_router_v2 import query_relevance

        candidate = {
            "title": "Portrait of money at a festival",
            "image_description": "Portrait created from money",
            "tags": ["Category:Money", "Category:Portraits"],
        }
        result = query_relevance(
            "bundle of twenty dollar bills ransom money", candidate
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["matched_count"], 1)

    def test_prepare_rejects_irrelevant_asset_even_when_must_hits(self):
        provider = MediaProviderV2(router=object())
        candidate = {
            "id": "generic-money-image", "fonte": "Wikimedia",
            "must_hits": 1, "avoid_hits": 0, "score": 100,
            "query_relevance": {
                "ok": False, "matched_terms": ["money"],
                "matched_count": 1, "query_term_count": 6,
                "required_terms": 4, "ratio": 0.167,
            },
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
