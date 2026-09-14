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


if __name__ == "__main__":
    unittest.main()
