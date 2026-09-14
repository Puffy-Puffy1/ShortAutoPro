import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BatchShellBaseTests(unittest.TestCase):
    def test_batch_queue_respects_shortautopro_base(self):
        text = (ROOT / "batch_queue.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('"$BASE/gerar_short.sh"', text)
        self.assertIn('"$BASE/manifests/${SHORT_ID}.json"', text)

    def test_batch_recovery_respects_shortautopro_base(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"', text)
        self.assertIn('STATE_DIR="$BASE/queue"', text)
        self.assertIn('"$BASE/gerar_short.sh"', text)
        self.assertIn('python "$BASE/register_topic.py"', text)


if __name__ == "__main__":
    unittest.main()
