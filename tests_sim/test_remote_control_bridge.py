import unittest
from pathlib import Path


class RemoteControlBridgeTests(unittest.TestCase):
    def setUp(self):
        self.workflow = Path(".github/workflows/shortautopro-remote.yml")
        self.text = self.workflow.read_text(encoding="utf-8")

    def test_remote_control_workflow_exists(self):
        self.assertTrue(self.workflow.is_file())

    def test_runner_targets_self_hosted_windows_x64(self):
        self.assertIn("runs-on: [self-hosted, Windows, X64]", self.text)

    def test_workflow_keeps_repository_contents_read_only(self):
        self.assertIn("permissions:\n  contents: read", self.text)

    def test_push_changes_trigger_remote_validation(self):
        self.assertIn("push:", self.text)
        self.assertIn('      - "**.py"', self.text)
        self.assertIn('      - "**.sh"', self.text)
        self.assertIn('      - ".github/workflows/**"', self.text)

    def test_windows_health_targets_canonical_consolidation3_runtime(self):
        for required in (
            "main.py",
            "resume_short_runtime.py",
            "video_professional.py",
            "v6_professional.py",
            "media_acquisition_recovery.py",
            "media_strict_must_guard.py",
            "release_gate.py",
        ):
            self.assertIn(required, self.text)
        self.assertIn("wrapper legado presente", self.text)
        self.assertIn("v6_runtime.py v6.py video.py limpar_storage.sh", self.text)

    def test_remote_checkout_uses_current_node24_action_generation(self):
        self.assertIn("uses: actions/checkout@v7", self.text)
        self.assertNotIn("uses: actions/checkout@v4", self.text)


if __name__ == "__main__":
    unittest.main()
