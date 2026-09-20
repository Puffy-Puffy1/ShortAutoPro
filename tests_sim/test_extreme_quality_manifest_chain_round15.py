import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeQualityManifestChainRound15Tests(unittest.TestCase):
    def test_final_quality_records_manifest_fingerprint(self):
        text = (ROOT / "final_quality.py").read_text(encoding="utf-8")
        self.assertIn("FINAL_QUALITY_2.6_MANIFEST_CHAIN", text)
        self.assertIn('"production_manifest_sha256": file_sha256(MANIFEST)', text)
        self.assertIn("def file_sha256(", text)

    def test_release_gate_blocks_detached_quality_report(self):
        text = (ROOT / "release_gate.py").read_text(encoding="utf-8")
        self.assertIn("final_quality_manifest_identity_missing", text)
        self.assertIn("final_quality_manifest_identity_mismatch", text)
        self.assertIn("quality_manifest_sha!=manifest_sha_now", text)

    def test_release_guard_rechecks_quality_manifest_binding(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("quality_manifest_identity_mismatch", text)
        self.assertIn('quality_input.get("production_manifest_sha256")', text)


if __name__ == "__main__":
    unittest.main()
