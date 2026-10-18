import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_quality_report


class MediaQualityReportTests(unittest.TestCase):
    def make_fixture(self, duplicate=False):
        temporary = tempfile.TemporaryDirectory()
        base = Path(temporary.name)
        media_quality_report.BASE = base
        media_dir = base / "imagens" / "short_case"
        media_dir.mkdir(parents=True)
        roteiro_dir = base / "roteiros"
        roteiro_dir.mkdir(parents=True)
        paths = []
        contents = [b"first asset bytes", b"first asset bytes" if duplicate else b"second asset bytes"]
        scenes = []
        for index, content in enumerate(contents, start=1):
            path = media_dir / f"scene_{index:02d}_wikimedia.jpg"
            path.write_bytes(content)
            paths.append(path)
            digest = hashlib.sha256(content).hexdigest()
            scenes.append({
                "scene_number": index,
                "asset": {
                    "path": str(path),
                    "checksum_sha256": digest,
                    "must_total": 1,
                    "must_hits": 1,
                    "validated": True,
                },
            })
        scene_map = {"scenes": [
            {"scene": 1, "must_have": ["ship"]},
            {"scene": 2, "must_have": ["ocean"]},
        ]}
        (roteiro_dir / "scene_map_case.json").write_text(json.dumps(scene_map), encoding="utf-8")
        manifest = {
            "schema_version": "media-manifest-v2",
            "engine_version": "2.0.1",
            "short_id": "case",
            "immutable": True,
            "scene_count": len(scenes),
            "scenes": scenes,
        }
        manifest["integrity_sha256"] = media_quality_report.manifest_integrity(manifest)
        (base / "manifests").mkdir()
        (base / "manifests" / "media_case.json").write_text(json.dumps(manifest), encoding="utf-8")
        return temporary, paths

    def test_valid_manifest_generates_pass_report(self):
        temporary, paths = self.make_fixture()
        try:
            def fake_validate(path):
                return {
                    "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    "probe": {"width": 1920, "height": 1080},
                }
            with patch.object(media_quality_report, "validate_asset", side_effect=fake_validate):
                report = media_quality_report.evaluate("case")
            self.assertEqual(report["status"], "PASS", report["errors"])
            self.assertEqual(report["validated_scenes"], 2)
        finally:
            temporary.cleanup()

    def test_duplicate_asset_hash_blocks_report(self):
        temporary, paths = self.make_fixture(duplicate=True)
        try:
            def fake_validate(path):
                return {
                    "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    "probe": {"width": 1920, "height": 1080},
                }
            with patch.object(media_quality_report, "validate_asset", side_effect=fake_validate):
                report = media_quality_report.evaluate("case")
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("duplicate_asset_checksum" in error for error in report["errors"]))
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
