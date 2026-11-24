import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from longform_runtime import verify_generated_manifest


def _canonical(payload):
    value = dict(payload)
    value.pop("integrity_sha256", None)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class GeneratedManifestIntegrationTests(unittest.TestCase):
    def _write_manifest(self, root):
        project = root / "project_01"
        project.mkdir()
        media = project / "clip_0001.mp4"
        media.write_bytes(b"validated video fixture")
        payload = {
            "schema_version": "shortautopro-generated-clips-v1",
            "project_id": "project_01",
            "clip_count": 1,
            "project": {"kind": "longform", "aspect_ratio": "16:9"},
            "clips": [{
                "clip_index": 1,
                "start_seconds": 0,
                "duration_seconds": 10,
                "path": str(media),
                "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
                "ffprobe": {"status": "GENERATED_AND_PROBED", "video_codec": "h264"},
            }],
        }
        payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
        manifest = project / "generated_manifest.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return manifest, media, payload

    def test_accepts_valid_manifest_and_clip_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            result = verify_generated_manifest(manifest)
            self.assertEqual(result["project_id"], payload["project_id"])
            self.assertEqual(len(result["clips"]), 1)

    def test_rejects_manifest_integrity_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, payload = self._write_manifest(Path(tmp))
            payload["clips"][0]["prompt"] = "tampered"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integridade"):
                verify_generated_manifest(manifest)

    def test_rejects_clip_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, media, payload = self._write_manifest(Path(tmp))
            media.write_bytes(b"changed video fixture")
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_generated_manifest(manifest)

    def test_rejects_clip_path_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, media, payload = self._write_manifest(Path(tmp))
            outside = Path(tmp) / "outside.mp4"
            outside.write_bytes(media.read_bytes())
            payload["clips"][0]["path"] = str(outside)
            payload["clips"][0]["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fora do workspace"):
                verify_generated_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
