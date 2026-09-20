import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeBatchReportHarmonyRound15Tests(unittest.TestCase):
    def test_batch_report_excludes_auxiliary_manifest_files(self):
        text = (ROOT / "batch_report.py").read_text(encoding="utf-8")
        for suffix in (
            "_quality.json",
            "_release.json",
            "_professional.json",
            "_render_identity.json",
        ):
            self.assertIn(suffix, text)
        self.assertIn("AUXILIARY_SUFFIXES", text)

    def test_batch_report_uses_exact_release_guard(self):
        text = (ROOT / "batch_report.py").read_text(encoding="utf-8")
        self.assertIn("import release_artifact_guard", text)
        self.assertIn("release_artifact_guard.validate(short_id)", text)
        self.assertIn('"release_valid": release_valid', text)
        self.assertIn('"release_validation_reason": release_reason', text)

    def test_batch_report_surfaces_release_ready_count(self):
        text = (ROOT / "batch_report.py").read_text(encoding="utf-8")
        self.assertIn('release_ready = sum(1 for p in productions if p["release_valid"])', text)
        self.assertIn('"release_ready": release_ready', text)
        self.assertIn("Release exata válida", text)


if __name__ == "__main__":
    unittest.main()
