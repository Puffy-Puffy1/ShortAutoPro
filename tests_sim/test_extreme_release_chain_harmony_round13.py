import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeReleaseChainHarmonyRound13Tests(unittest.TestCase):
    def test_release_gate_fingerprints_manifest_and_final_quality(self):
        text = (ROOT / "release_gate.py").read_text(encoding="utf-8")
        self.assertIn('PRODUCTION_MANIFEST=M/f"{SID}.json"', text)
        self.assertIn('FINAL_QUALITY=M/f"{SID}_quality.json"', text)
        self.assertIn('"production_manifest_sha256":file_sha(PRODUCTION_MANIFEST)', text)
        self.assertIn('"final_quality_sha256":file_sha(FINAL_QUALITY)', text)
        self.assertIn('"version":"RELEASE_GATE_1.6_VISUAL_CONTENT_INTEGRITY"', text)

    def test_release_guard_rejects_stale_manifest_or_quality_chain(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("def file_sha256(", text)
        self.assertIn("release_manifest_identity_mismatch", text)
        self.assertIn("release_quality_identity_mismatch", text)
        self.assertIn('input_identity.get("production_manifest_sha256")', text)
        self.assertIn('input_identity.get("final_quality_sha256")', text)

    def test_release_guard_still_checks_exact_mp4_identity(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("video_size_identity_mismatch", text)
        self.assertIn("video_mtime_identity_mismatch", text)


if __name__ == "__main__":
    unittest.main()
