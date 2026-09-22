import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaStageRealtimeBudgetTests(unittest.TestCase):
    def test_midia_persists_live_pending_checkpoint(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("def _sap_atomic_media_checkpoint(", text)
        self.assertIn('phase=f"before_scene_{numero}"', text)
        self.assertIn('phase=f"after_scene_{numero}"', text)
        self.assertIn('"pending_scenes":', text)

    def test_scene_retries_stop_when_budget_is_exhausted(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('SAP_MEDIA_SCENE_BUDGET_SECONDS', text)
        self.assertIn('SAP_MEDIA_SCENE_MIN_RETRY_SECONDS', text)
        self.assertIn('if not _scene_retry_allowed("simplified_retry"):', text)
        self.assertIn('and _scene_retry_allowed("late_strict_recovery")', text)

    def test_runtime_treats_pending_as_missing_after_timeout(self):
        text = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn('report.get("pending_scenes"', text)
        self.assertIn("def round_timeout_seconds()", text)
        self.assertIn('remaining * scene_budget + grace', text)

    def test_certified_recovery_budgets_are_preserved(self):
        text = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn("rescue_budget = (1, 2, 3, 4)", text)
        self.assertNotIn('env["SAP_MEDIA_SIMPLIFIED_RETRY_MAX"]', text)

    def test_midia_uses_canonical_base_override(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("SHORTAUTOPRO_BASE"', text)


if __name__ == "__main__":
    unittest.main()
