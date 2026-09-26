import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import shortauto_asset_library as sal


class VerifiedLocalAssetTests(unittest.TestCase):
    def test_only_metadata_verified_asset_can_satisfy_must(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / "asset_library.json"
            good = base / "ocean.jpg"
            good.write_bytes(b"x" * 2000)
            state.write_text(json.dumps({
                "assets": [
                    {
                        "asset_id": "sha256:good",
                        "path": str(good),
                        "quality": 92,
                        "source": "wikimedia",
                        "license": "CC-BY",
                        "entities": ["ocean", "waves"],
                        "location": "",
                        "year_or_era": "",
                        "used_count": 1,
                        "short_ids": ["old"],
                    },
                    {
                        "asset_id": "sha256:bad",
                        "path": str(good),
                        "quality": 99,
                        "source": "unknown",
                        "license": "unknown",
                        "entities": ["ocean"],
                        "used_count": 0,
                    },
                ]
            }), encoding="utf-8")
            with mock.patch.object(sal, "STATE", state):
                result = sal.verified_candidate({"must_have": ["ocean"]}, exclude_short_id="new")
            self.assertIsNotNone(result)
            self.assertEqual(result["asset_id"], "sha256:good")

    def test_missing_must_or_mismatch_never_becomes_verified_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / "asset_library.json"
            asset = base / "forest.jpg"
            asset.write_bytes(b"x" * 2000)
            state.write_text(json.dumps({
                "assets": [{
                    "asset_id": "sha256:forest",
                    "path": str(asset),
                    "quality": 95,
                    "source": "pixabay",
                    "license": "provider-license",
                    "entities": ["forest"],
                    "used_count": 0,
                    "short_ids": ["old"],
                }]
            }), encoding="utf-8")
            with mock.patch.object(sal, "STATE", state):
                self.assertIsNone(sal.verified_candidate({"must_have": []}))
                self.assertIsNone(sal.verified_candidate({"must_have": ["ocean"]}))


if __name__ == "__main__":
    unittest.main()
