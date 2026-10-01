import os
import unittest
from pathlib import Path
from unittest import mock

import media_acquisition_recovery as recovery


class MediaTwoPassRecoveryTests(unittest.TestCase):
    def test_recovery_pass_adds_alias_and_compact_queries(self):
        with mock.patch.dict(os.environ, {"SAP_MEDIA_RECOVERY_PASS":"1"}, clear=False):
            queries = recovery._rescue_queries(
                "empty ornate golden picture frames on wall",
                ["picture frame"],
                assunto="Museum",
                segmento="empty ornate golden frames remain on the wall",
                visual_mode="object",
            )
        joined = " | ".join(queries).lower()
        self.assertTrue("frame" in joined)
        self.assertGreaterEqual(len(queries), 3)

    def test_normal_pass_stays_bounded(self):
        with mock.patch.dict(os.environ, {"SAP_MEDIA_RECOVERY_PASS":"0"}, clear=False):
            queries = recovery._rescue_queries(
                "ventilation duct tunnel",
                ["ventilation duct"],
                visual_mode="object",
            )
        self.assertLessEqual(len(queries), 8)

    def test_runtime_preserves_first_pass_then_targeted_recovery(self):
        text = Path("media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_RECOVERY_ROUND", text)
        self.assertIn("SAP_MEDIA_INCREMENTAL", text)
        self.assertIn("SAP_MUST_RESCUE_MAX_QUERIES", text)
        self.assertIn("SAP_STOCK_RESCUE_MAX_QUERIES", text)
        self.assertIn("acquisition_missing_", text)

    def test_main_uses_media_runtime_not_raw_midia(self):
        text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('"media_engine_v2.py"', text)
        self.assertIn('"render_plan_v2.py"', text)
        self.assertNotIn('p.run("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py")', text)

    def test_semantic_resume_uses_same_runtime(self):
        text = Path("resume_after_semantic_fix.py").read_text(encoding="utf-8")
        self.assertIn('"media_stage_runtime.py"', text)

    def test_recovery_does_not_modify_strict_guard(self):
        guard = Path("media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", guard)
        self.assertIn("return False", guard)

    def test_recovery_module_version_incremented(self):
        self.assertGreaterEqual(tuple(map(int, recovery.VERSION.split("."))), (1, 7))


if __name__ == "__main__":
    unittest.main()
