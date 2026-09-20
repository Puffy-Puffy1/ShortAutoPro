import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BatchShellBaseTests(unittest.TestCase):
    def test_batch_queue_respects_shortautopro_base(self):
        text = (ROOT / "batch_queue.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('"$BASE/main.py"', text)
        self.assertIn('python "$BASE/main.py" run', text)
        self.assertIn('"$BASE/release_artifact_guard.py"', text)
        self.assertIn('python "$BASE/release_artifact_guard.py" --short-id "$run_id"', text)
        self.assertNotIn("gerar_short.sh", text)

    def test_batch_recovery_respects_shortautopro_base(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('STATE_DIR="$BASE/queue"', text)
        self.assertIn('"$BASE/main.py"', text)
        self.assertIn('python "$BASE/main.py" run', text)
        self.assertIn('python "$BASE/register_topic.py"', text)
        self.assertIn('"$BASE/release_artifact_guard.py"', text)
        self.assertIn('python "$BASE/release_artifact_guard.py" --short-id "$1"', text)
        self.assertNotIn("gerar_short.sh", text)


if __name__ == "__main__":
    unittest.main()
