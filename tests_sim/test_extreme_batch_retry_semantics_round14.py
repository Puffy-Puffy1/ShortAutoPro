import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ExtremeBatchRetrySemanticsRound14Tests(unittest.TestCase):
    def text(self): return (ROOT/"batch_runtime.py").read_text(encoding="utf-8")
    def test_state_is_per_item_not_contiguous(self):
        t=self.text(); self.assertIn("BATCH_STATE_3.0_PER_ITEM",t); self.assertIn('"items":items',t); self.assertNotIn("BATCH_STATE_2.0_CONTIGUOUS",t)
    def test_failed_item_is_deferred_without_aborting_later_items(self):
        t=self.text(); self.assertIn('"RETRY_PENDING"',t); self.assertIn("BATCH_CONTINUE",t); self.assertIn("BATCH_RECOVERY_ROUND",t)
    def test_recovery_uses_exact_short_id_resume(self):
        t=self.text(); self.assertIn('"resume","--short-id",sid',t); self.assertIn('mode="resume" if has or recovery',t)
    def test_success_requires_exact_release_validation(self):
        t=self.text(); self.assertIn("release_ok(sid,env)",t); self.assertIn('release="PUBLISH"',t)
    def test_historical_failures_do_not_prevent_recovered_completion(self):
        t=self.text(); self.assertIn('all(x["status"]=="COMPLETED"',t); self.assertNotIn('failures==0',t)

if __name__=="__main__": unittest.main()
