import unittest
from pathlib import Path


class TermuxBridgeReadmeTests(unittest.TestCase):
    def test_readme_documents_stable_branch_and_install_command(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "automation" / "TERMUX_BRIDGE_README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("termux-stable", text)
        self.assertIn("bash automation/install_termux_bridge.sh", text)
        self.assertIn("SHORTAUTOPRO_TERMUX_BRIDGE", text)


if __name__ == "__main__":
    unittest.main()
