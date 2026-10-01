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
        with patch("media_provider_v2._legacy", return_value=(lambda *a, **k: None, None, None)):
            self.assertEqual(provider.search("q", [], []), [])

    def test_provider_boundary_does_not_own_rendering(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg", source.lower())
        self.assertNotIn("SHORT_ID", source)


if __name__ == "__main__":
    unittest.main()
