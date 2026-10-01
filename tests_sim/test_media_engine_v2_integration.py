import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_engine_v2


class MediaEngineV2IntegrationTests(unittest.TestCase):
    def test_mock_provider_to_frozen_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media_engine_v2.BASE = base
            sid = "INTEGRATION_V2"
            (base / "roteiros").mkdir(parents=True)
            (base / "imagens" / f"short_{sid}").mkdir(parents=True)
            scenes = [
                {"scene_id": "01", "query": "ship", "must_have": ["ship"], "avoid": []}
            ]
            (base / "roteiros" / f"scene_map_{sid}.json").write_text(
                json.dumps({"scenes": scenes}), encoding="utf-8"
            )
            fake = {
                "source": "Mock",
                "asset_id": "A",
                "url": "",
                "asset_type": "image",
                "description": "ship",
                "evidence_class": "MOCK",
                "must_hits": 1,
                "must_total": 1,
                "path": str(base / "imagens" / f"short_{sid}" / "scene_01.jpg"),
                "checksum_sha256": "fixture",
                "probe": {"width": 100, "height": 100},
                "validated": True,
            }
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[]),                  patch.object(media_engine_v2, "_local_library_asset", return_value=fake),                  patch.object(media_engine_v2, "ffprobe_asset", return_value=fake["probe"]):
                manifest = media_engine_v2.build_manifest(sid)
            p = base / "manifests" / f"media_{sid}.json"
            data = json.loads(p.read_text())
            self.assertEqual(manifest["short_id"], sid)
            self.assertEqual(data["short_id"], sid)
            self.assertEqual(data["scene_count"], 1)
            self.assertEqual(data["scenes"][0]["asset"]["must_hits"], 1)


if __name__ == "__main__":
    unittest.main()
