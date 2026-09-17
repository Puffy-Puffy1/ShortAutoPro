import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class WorkflowRuntimeHygieneTests(unittest.TestCase):
    def test_checkout_actions_use_node24_generation(self):
        for name in (
            "shortautopro-portable.yml",
            "shortautopro-remote.yml",
            "promote-termux-stable.yml",
            "runner-smoke-test.yml",
        ):
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            self.assertIn("actions/checkout@v7", text, name)
            self.assertNotIn("actions/checkout@v4", text, name)

    def test_portable_setup_python_uses_current_generation(self):
        text = (WORKFLOWS / "shortautopro-portable.yml").read_text(encoding="utf-8")
        self.assertIn("actions/setup-python@v7", text)
        self.assertNotIn("actions/setup-python@v5", text)


if __name__ == "__main__":
    unittest.main()
