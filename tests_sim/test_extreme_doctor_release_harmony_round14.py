import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeDoctorReleaseHarmonyRound14Tests(unittest.TestCase):
    def test_doctor_uses_shared_release_artifact_guard(self):
        text = (ROOT / "production_doctor.py").read_text(encoding="utf-8")
        self.assertIn("import release_artifact_guard", text)
        self.assertIn("release_artifact_guard.validate(sid)", text)

    def test_stale_release_blocks_complete_boundary(self):
        text = (ROOT / "production_doctor.py").read_text(encoding="utf-8")
        self.assertIn('"code": "RELEASE_ARTIFACT_STALE"', text)
        self.assertIn('"severity": "BLOCK"', text)
        self.assertIn("elif release_valid:", text)
        self.assertNotIn('elif release_decision in {"PUBLISH", "ACCEPTABLE", "PASS", "APPROVED", "RELEASE"}:', text)

    def test_doctor_reports_release_validation_details(self):
        text = (ROOT / "production_doctor.py").read_text(encoding="utf-8")
        self.assertIn('"release_valid": release_valid', text)
        self.assertIn('"release_validation_reason": release_reason', text)


if __name__ == "__main__":
    unittest.main()
