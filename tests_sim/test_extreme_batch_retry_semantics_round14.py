import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeBatchRetrySemanticsRound14Tests(unittest.TestCase):
    def test_state_declares_last_completed_semantics(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('"version":"BATCH_STATE_2.0_CONTIGUOUS"', text)
        self.assertIn('"current_semantics":"last_completed_index"', text)

    def test_failed_item_is_left_pending_for_resume(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('"retry_pending"', text)
        self.assertIn('salvar_estado "$BATCH_ID" "$TOTAL" "$((i-1))"', text)
        self.assertIn('será repetido no --resume', text)

    def test_resume_accepts_retry_pending_and_retries_current_plus_one(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('[ "$STATUS" = "retry_pending" ]', text)
        self.assertIn('INICIO=$((ATUAL+1))', text)
        self.assertIn('[ "$SUCESSOS" -le "$ATUAL" ]', text)

    def test_success_requires_post_run_exact_release_validation(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('python "$BASE/main.py" run && resultado_final_ok "$SHORT_ID"', text)

    def test_historical_attempt_failures_do_not_prevent_recovered_completion(self):
        text = (ROOT / "batch_recovery.sh").read_text(encoding="utf-8")
        self.assertIn('if [ "$SUCESSOS" -eq "$TOTAL" ]; then STATUS_FINAL="completed"', text)
        self.assertNotIn('[ "$FALHAS" -eq 0 ] && [ "$SUCESSOS" -eq "$TOTAL" ]', text)


if __name__ == "__main__":
    unittest.main()
