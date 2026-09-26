import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeBatchRetrySemanticsRound14Tests(unittest.TestCase):
    def test_state_is_per_item_not_contiguous(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "BATCH_STATE_3.0_PER_ITEM"', text)
        for status in ("queued", "running", "retry_pending", "recovering", "completed", "failed_permanent", "blocked_global"):
            self.assertIn(f'"{status}"', text)
        self.assertNotIn("last_completed_index", text)

    def test_partial_item_resumes_exact_short_id(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('"resume", "--short-id", sid', text)
        self.assertIn("artifacts_exist(sid)", text)
        self.assertNotIn('"--reuse-short-id"', text)

    def test_recoverable_failure_does_not_abort_following_items(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('item["status"] = "retry_pending"', text)
        self.assertIn("BATCH_CONTINUE next=", text)
        self.assertIn("BATCH_RECOVERY_ROUND=", text)

    def test_success_requires_exact_release_revalidation(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn("proc.returncode == 0 and release_ok(sid)", text)
        self.assertIn('item["status"] == "completed" and not release_ok', text)

    def test_historical_attempt_failures_do_not_prevent_recovered_completion(self):
        text = (ROOT / "batch_runtime.py").read_text(encoding="utf-8")
        self.assertIn('state["status"] = "completed"', text)
        self.assertIn('counts["failed_permanent"]', text)
        self.assertNotIn('failures == 0', text)


if __name__ == "__main__":
    unittest.main()
