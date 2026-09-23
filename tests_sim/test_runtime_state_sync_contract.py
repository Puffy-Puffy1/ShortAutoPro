import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeStateSyncContractTests(unittest.TestCase):
    def test_mutable_batch_state_is_not_tracked(self):
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "queue/batch_state.json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_runtime_outputs_are_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for rule in (
            "queue/batch_state.json",
            "queue/.batch_recovery.lock",
            "queue/.batch_recovery.lockdir/",
            "reports/performance/",
            "reports/production/",
        ):
            self.assertIn(rule, text)


if __name__ == "__main__":
    unittest.main()
