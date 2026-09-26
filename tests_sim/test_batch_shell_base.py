import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BatchShellBaseTests(unittest.TestCase):
    def test_batch_queue_is_thin_wrapper_over_canonical_runtime(self):
        text = (ROOT / "batch_queue.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('"$BASE/batch_runtime.py" run', text)
        self.assertNotIn('"$BASE/main.py"', text)
        self.assertNotIn("release_artifact_guard.py", text)
        self.assertNotIn("gerar_short.sh", text)

    def test_batch_recovery_is_thin_wrapper_over_canonical_runtime(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('"$BASE/batch_runtime.py" resume', text)
        self.assertIn('"$BASE/batch_runtime.py" status', text)
        self.assertNotIn('"$BASE/main.py"', text)
        self.assertNotIn("gerar_short.sh", text)

    def test_canonical_runtime_owns_fresh_resume_and_release_contracts(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('"main.py"), "resume", "--short-id", sid', text)
        self.assertIn('"main.py"), "run"', text)
        self.assertIn('"release_artifact_guard.py"', text)
        self.assertIn('"BATCH_STATE_3.0_PER_ITEM"', text)


if __name__ == "__main__":
    unittest.main()
