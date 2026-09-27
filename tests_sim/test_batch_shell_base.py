import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class BatchShellBaseTests(unittest.TestCase):
    def test_batch_wrappers_respect_shortautopro_base_and_delegate(self):
        for name in ("batch_queue.sh","batch_recovery.sh"):
            text=(ROOT/name).read_text(encoding="utf-8")
            self.assertIn('BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"',text)
            self.assertIn('"$BASE/batch_runtime.py"',text)
            self.assertNotIn("gerar_short.sh",text)
    def test_canonical_runtime_uses_base_for_state_main_resume_and_release(self):
        text=(ROOT/"batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('QUEUE=BASE/"queue"',text)
        self.assertIn('str(BASE/"main.py")',text)
        self.assertIn('str(BASE/"release_artifact_guard.py")',text)
        self.assertIn('"resume","--short-id",sid',text)

if __name__=="__main__": unittest.main()
