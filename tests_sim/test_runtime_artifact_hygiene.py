import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RuntimeArtifactHygieneTests(unittest.TestCase):
    def test_generated_short_media_is_not_tracked(self):
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked = [
            line.strip()
            for line in proc.stdout.splitlines()
            if line.strip().startswith("imagens/short_")
        ]
        self.assertEqual(tracked, [])

    def test_client_runtime_artifacts_are_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        expected = {
            "credits/attribution_client_*.txt",
            "credits/ledger_client_*.json",
            "credits/short_client_*.txt",
            "manifests/client_*.json",
        }
        for pattern in expected:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignore)

    def test_short_runtime_media_rule_remains_present(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("imagens/short_*/", ignore)


if __name__ == "__main__":
    unittest.main()
