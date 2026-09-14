import subprocess
import unittest
from pathlib import Path


class RuntimeStateGitPolicyTests(unittest.TestCase):
    def test_topic_history_is_ignored(self):
        text = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn("historico_assuntos.json", text)
        self.assertIn("historico_assuntos.json.lock", text)

    def test_topic_history_is_not_tracked(self):
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "historico_assuntos.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
