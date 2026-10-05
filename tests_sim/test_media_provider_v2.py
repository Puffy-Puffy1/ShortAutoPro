import unittest
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

    def test_provider_boundary_does_not_import_legacy(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("from midia import", source)
        self.assertNotIn("import midia", source)

    def test_provider_boundary_does_not_own_rendering(self):
        source = Path("media_provider_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("render_engine_v2", source)
        self.assertNotIn("ffmpeg", source.lower())
        self.assertNotIn("SHORT_ID", source)

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
