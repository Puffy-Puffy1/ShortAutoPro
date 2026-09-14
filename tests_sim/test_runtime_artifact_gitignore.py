import subprocess
import unittest
from pathlib import Path


class RuntimeArtifactGitignoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def ignored(self, path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path],
            cwd=self.root,
            check=False,
        )
        return result.returncode == 0

    def test_timestamped_runtime_outputs_are_ignored(self):
        samples = [
            "credits/attribution_2026-09-14_040315_12615.txt",
            "credits/ledger_2026-09-14_040315_12615.json",
            "credits/short_2026-09-14_040315_12615.txt",
            "manifests/2026-09-14_040315_12615.json",
            "manifests/2026-09-14_040315_12615_quality.json",
            "roteiros/supervisor_2026-09-14_040315_12615.json",
        ]
        for path in samples:
            with self.subTest(path=path):
                self.assertTrue(self.ignored(path), path)

    def test_structural_files_are_not_hidden_by_new_rules(self):
        samples = [
            "credits/README.md",
            "credits/attribution_template.txt",
            "manifests/schema.json",
            "roteiros/supervisor_template.json",
        ]
        for path in samples:
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path), path)


if __name__ == "__main__":
    unittest.main()
