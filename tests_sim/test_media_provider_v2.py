import unittest
from unittest.mock import patch
from pathlib import Path

from media_provider_v2 import MediaProviderV2


class MediaProviderV2Tests(unittest.TestCase):
    def test_provider_boundary_is_small_and_explicit(self):
        self.assertEqual(
            {"search", "prepare", "download"},
            {
                name for name in ("search", "prepare", "download")
                if callable(getattr(MediaProviderV2, name, None))
            },
        )

    def test_search_normalizes_non_list_provider_result(self):
        provider = MediaProviderV2()
        with patch("media_provider_v2._legacy", return_value=(lambda *a, **k: None, None, None, lambda q, must: [q])):
            self.assertEqual(provider.search("q", [], []), [])

    def test_search_retries_a_bounded_simplified_query(self):
        provider = MediaProviderV2()
        calls = []

        def search(query, must, avoid, **kwargs):
            calls.append(query)
            return [{"id": "asset-1", "descricao": "verified asset"}] if len(calls) == 2 else []

        def simplify(query, must):
            return ["must anchor", "fallback query"]

        with patch(
            "media_provider_v2._legacy",
            return_value=(search, None, None, simplify),
        ):
            rows = provider.search(
                "very specific unavailable query",
                ["must anchor"],
                [],
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "asset-1")
        self.assertEqual(calls, ["very specific unavailable query", "must anchor"])

    def test_provider_boundary_does_not_own_rendering(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg", source.lower())
        self.assertNotIn("SHORT_ID", source)


if __name__ == "__main__":
    unittest.main()
