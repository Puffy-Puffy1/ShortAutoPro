import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeManifestInputHarmonyRound14Tests(unittest.TestCase):
    def test_manifest_fingerprints_release_critical_inputs(self):
        text = (ROOT / "production_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"input_artifacts": input_artifacts', text)
        for key in (
            '"hook_sha256": file_sha256(HOOK)',
            '"script_sha256": file_sha256(ROTEIRO)',
            '"source_sha256": file_sha256(FONTE)',
            '"publish_sha256": file_sha256(PUBLISH)',
            '"publish_integrity_sha256": file_sha256(PUBLISH_INTEGRITY)',
            '"source_ledger_sha256": file_sha256(LEDGER)',
        ):
            self.assertIn(key, text)

    def test_release_guard_revalidates_manifest_inputs(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("manifest_input_identity_mismatch", text)
        self.assertIn("critical_inputs = {", text)
        self.assertIn('"script_sha256": ROTEIROS / f"short_{sid}.txt"', text)
        self.assertIn('"publish_sha256": ROTEIROS / f"publish_{sid}.json"', text)
        self.assertIn('"source_ledger_sha256": CREDITS / f"ledger_{sid}.json"', text)

    def test_topic_path_is_restricted_to_canonical_files(self):
        text = (ROOT / "release_artifact_guard.py").read_text(encoding="utf-8")
        self.assertIn("allowed_topics = {", text)
        self.assertIn("manifest_topic_path_mismatch", text)


if __name__ == "__main__":
    unittest.main()
