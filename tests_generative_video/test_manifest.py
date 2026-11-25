import tempfile
import unittest
from pathlib import Path

from generative_video_poc.manifest import build_ready_manifest, verify_ready_manifest
from generative_video_poc.state_store import ProjectStore


def spec():
    return {
        "kind": "shorts",
        "target_duration_seconds": 20,
        "aspect_ratio": "9:16",
        "width": 360,
        "height": 640,
        "clip_seconds": 10,
        "clip_prompts": ["A lighthouse in a storm", "A lighthouse at sunrise"],
    }


class GeneratedManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.temp.name))
        self.store.create_project("manifest-test", spec())

    def tearDown(self):
        self.temp.cleanup()

    def complete_all(self):
        for index in (1, 2):
            claim = self.store.claim_next_clip("manifest-worker", project_id="manifest-test")
            self.assertEqual(claim["clip_index"], index)
            output = Path(claim["output_path"])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(f"fixture-clip-{index}".encode())
            metadata = {
                "status": "GENERATED_AND_PROBED",
                "duration_seconds": 10.0,
                "video_codec": "h264",
                "width": 360,
                "height": 640,
                "model": "test-model",
            }
            self.store.complete_clip(
                "manifest-test", index, "manifest-worker",
                claim["lease_token"], output, metadata,
            )

    def test_exports_ordered_manifest_and_verifies_checksums(self):
        self.complete_all()
        manifest = build_ready_manifest(self.store, "manifest-test")
        verified = verify_ready_manifest(manifest["manifest_path"])
        self.assertEqual(verified["clip_count"], 2)
        self.assertEqual([item["clip_index"] for item in verified["clips"]], [1, 2])
        self.assertEqual(verified["clips"][0]["prompt"], "A lighthouse in a storm")
        self.assertEqual(verified["clips"][1]["ffprobe"]["model"], "test-model")

    def test_manifest_verification_detects_clip_tampering(self):
        self.complete_all()
        manifest = build_ready_manifest(self.store, "manifest-test")
        Path(manifest["clips"][0]["path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_ready_manifest(manifest["manifest_path"])

    def test_incomplete_project_cannot_export_manifest(self):
        with self.assertRaisesRegex(ValueError, "COMPLETE"):
            build_ready_manifest(self.store, "manifest-test")


if __name__ == "__main__":
    unittest.main()
