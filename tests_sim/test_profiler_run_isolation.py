import tempfile
import unittest
from pathlib import Path
from unittest import mock

import production_profiler


class ProfilerRunIsolationTests(unittest.TestCase):
    def test_latest_run_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            with mock.patch.object(production_profiler, "REPORT_DIR", report_dir):
                production_profiler.begin_run("abc", "run-1")
                production_profiler.record("media_stage", 100, short_id="abc", category="stage")
                production_profiler.begin_run("abc", "run-2")
                production_profiler.record("media_stage", 20, short_id="abc", category="stage")

                self.assertEqual(production_profiler.latest_run_id("abc"), "run-2")
                rows = production_profiler.summarize("abc", run_id="run-2")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["count"], 1)
                self.assertAlmostEqual(rows[0]["total_seconds"], 20.0)

    def test_history_can_still_aggregate_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            with mock.patch.object(production_profiler, "REPORT_DIR", report_dir):
                production_profiler.begin_run("abc", "run-1")
                production_profiler.record("media_stage", 100, short_id="abc", category="stage")
                production_profiler.begin_run("abc", "run-2")
                production_profiler.record("media_stage", 20, short_id="abc", category="stage")

                rows = production_profiler.summarize("abc")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["count"], 2)
                self.assertAlmostEqual(rows[0]["total_seconds"], 120.0)

    def test_resume_starts_profile_run(self):
        text = Path("resume_after_semantic_fix.py").read_text(encoding="utf-8")
        self.assertIn("profile_begin_run(sid)", text)
        self.assertIn("PROFILE_RUN_ID=", text)


if __name__ == "__main__":
    unittest.main()
