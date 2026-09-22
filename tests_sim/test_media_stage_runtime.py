import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_stage_runtime as msr


class MediaStageRuntimeTests(unittest.TestCase):
    def test_round_env_increases_retrieval_effort_only(self):
        first = msr.round_env(0)
        second = msr.round_env(1)
        third = msr.round_env(2)
        self.assertEqual(first["SAP_MEDIA_INCREMENTAL"], "1")
        self.assertEqual(first["SAP_STOCK_RESCUE_MAX_QUERIES"], "1")
        self.assertEqual(second["SAP_STOCK_RESCUE_MAX_QUERIES"], "2")
        self.assertEqual(third["SAP_STOCK_RESCUE_MAX_QUERIES"], "3")
        self.assertLess(
            int(first["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
            int(third["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
        )
        for env in (first, second, third):
            self.assertNotIn("SAP_STRICT_MUST_DISABLED", env)
            self.assertNotIn("SAP_ALLOW_UNVERIFIED_MUST", env)

    def test_missing_report_parsing(self):
        report = {
            "total": 8,
            "expected": 12,
            "missing_scenes": [
                {"scene": 4},
                {"scene": 5},
                {"scene": 11},
                {"scene": 12},
            ],
        }
        self.assertEqual(msr.total_from(report), 8)
        self.assertEqual(msr.expected_from(report), 12)
        self.assertEqual(msr.missing_numbers(report), [4, 5, 11, 12])

    def test_main_pipeline_uses_media_stage_runtime(self):
        text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('p.run("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py")', text)
        self.assertNotIn('p.run("6 - SMART MEDIA SELECTOR", "midia.py")', text)

    def test_semantic_resume_uses_media_stage_runtime(self):
        text = Path("resume_after_semantic_fix.py").read_text(encoding="utf-8")
        self.assertIn('("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py"', text)

    def test_runtime_preserves_fail_closed_contract(self):
        text = Path("media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn("MUST verification remains strict", text)
        self.assertIn("NO_VALID_MISSING_REPORT", text)
        self.assertIn("MEDIA_STAGE_RUNTIME=NO_PROGRESS", text)
        self.assertIn("MEDIA_STAGE_RUNTIME=EXHAUSTED", text)

    def test_preflight_and_health_require_runtime(self):
        self.assertIn(
            "media_stage_runtime.py",
            Path("preflight_check.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "media_stage_runtime.py",
            Path("health_check.sh").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
