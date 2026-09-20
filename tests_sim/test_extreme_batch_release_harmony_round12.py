import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeBatchReleaseHarmonyRound12Tests(unittest.TestCase):
    def test_release_guard_binds_manifests_to_exact_current_mp4(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("video_size_identity_mismatch", text)
        self.assertIn("video_mtime_identity_mismatch", text)
        self.assertIn('VIDEOS / f"short_v6_{sid}.mp4"', text)
        self.assertIn('release_short_id_mismatch', text)

    def test_batch_paths_use_shared_release_guard(self):
        for name in ("batch_queue.sh", "batch_recovery.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("release_artifact_guard.py", text, name)
        queue = (ROOT / "batch_queue.sh").read_text(encoding="utf-8")
        recovery = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertNotIn('manifest=json.loads(', queue)
        self.assertNotIn('m=json.loads(', recovery)

    def test_health_preflight_and_audit_require_release_guard(self):
        for name in ("preflight_check.sh", "health_check.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("release_artifact_guard.py", text, name)
        audit = (ROOT / "tools" / "repo_audit.py").read_text(encoding="utf-8")
        self.assertIn('"release_artifact_guard.py"', audit)

    def test_professional_threshold_uses_bounded_shared_config(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('env_float("SAP_PROFESSIONAL_MIN_SCORE", 88.0, 50.0, 100.0)', text)
        self.assertNotIn('safe_float(os.getenv("SAP_PROFESSIONAL_MIN_SCORE"', text)


if __name__ == "__main__":
    unittest.main()
