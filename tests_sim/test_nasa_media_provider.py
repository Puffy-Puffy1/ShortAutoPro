import unittest
from unittest.mock import patch

import media_provider_router_v2 as router


class _Response:
    ok = True
    status_code = 200
    headers = {}

    def json(self):
        return {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "media_type": "image",
                            "nasa_id": "AS11-40-5875",
                            "title": "Apollo 11 astronaut on the lunar surface",
                            "description": "Buzz Aldrin stands on the Moon during the Apollo 11 lunar landing.",
                            "keywords": ["Apollo 11", "Moon", "lunar surface", "NASA"],
                            "center": "JSC",
                            "date_created": "1969-07-20",
                        }],
                        "links": [{
                            "rel": "preview",
                            "render": "image",
                            "href": "https://images-assets.nasa.gov/image/AS11-40-5875/AS11-40-5875~thumb.jpg",
                        }],
                    },
                    {
                        "data": [{
                            "media_type": "video",
                            "nasa_id": "VIDEO-ONLY",
                            "title": "Apollo 11 video",
                            "description": "Not an image result",
                        }],
                        "links": [{
                            "rel": "preview",
                            "render": "image",
                            "href": "https://images-assets.nasa.gov/image/VIDEO-ONLY/VIDEO-ONLY~thumb.jpg",
                        }],
                    },
                    {
                        "data": [{
                            "media_type": "image",
                            "nasa_id": "UNTRUSTED",
                            "title": "Untrusted image link",
                            "description": "Should be ignored",
                        }],
                        "links": [{
                            "rel": "preview",
                            "render": "image",
                            "href": "https://example.test/untrusted.jpg",
                        }],
                    },
                ]
            }
        }


class NasaMediaProviderTests(unittest.TestCase):
    def setUp(self):
        router._NASA_CACHE.clear()

    def tearDown(self):
        router._NASA_CACHE.clear()

    def test_search_returns_nasa_image_metadata_and_large_preview(self):
        response = _Response()
        with patch.object(router, "provider_gate", return_value=(True, "CLOSED", 0)), \
             patch.object(router.requests, "get", return_value=response) as get, \
             patch.object(router, "note_response", return_value="SUCCESS"), \
             patch.object(router, "note_provider_event"), \
             patch.object(router, "note_exception"):
            results = router.NasaProvider().search(
                "apollo 11 moon landing historical photo",
                ["moon"],
                ["modern rocket"],
            )

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["fonte"], "nasa")
        self.assertEqual(item["id"], "AS11-40-5875")
        self.assertEqual(
            item["url"],
            "https://images-assets.nasa.gov/image/AS11-40-5875/AS11-40-5875~large.jpg",
        )
        self.assertIn("lunar surface", item["image_description"])
        self.assertIn("Moon", item["tags"])
        self.assertEqual(item["must_hits"], 1)
        self.assertEqual(item["tipo"], "image")
        self.assertEqual(get.call_args.kwargs["params"]["media_type"], "image")

    def test_rejects_non_nasa_preview_urls(self):
        item = {
            "links": [{
                "rel": "preview",
                "render": "image",
                "href": "https://attacker.example/nasa-image.jpg",
            }]
        }
        self.assertEqual(router.NasaProvider._preview_url(item), "")

    def test_rejects_non_https_and_non_image_urls(self):
        for url in (
            "http://images-assets.nasa.gov/image/a/a.jpg",
            "https://images-assets.nasa.gov/video/a/a.mp4",
            "https://images-assets.nasa.gov/image/a/collection.json",
        ):
            item = {"links": [{"rel": "preview", "render": "image", "href": url}]}
            self.assertEqual(router.NasaProvider._preview_url(item), "")

    def test_default_router_includes_nasa_without_api_key(self):
        providers = router.MediaProviderRouterV2().providers
        self.assertTrue(any(isinstance(provider, router.NasaProvider) for provider in providers))

    def test_search_result_is_cached_by_exact_query(self):
        with patch.object(router, "provider_gate", return_value=(True, "CLOSED", 0)), \
             patch.object(router.requests, "get", return_value=_Response()) as get, \
             patch.object(router, "note_response", return_value="SUCCESS"), \
             patch.object(router, "note_provider_event"), \
             patch.object(router, "note_exception"):
            provider = router.NasaProvider()
            first = provider.search("Apollo 11 lunar landing", ["moon"], [])
            second = provider.search("Apollo 11 lunar landing", ["moon"], [])

        self.assertEqual(first, second)
        get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
