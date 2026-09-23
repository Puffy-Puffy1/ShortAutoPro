import sys
import unittest
from unittest import mock

import main
import production_recovery
import resume_short_runtime
import retention_engine


class RetentionReviewContractTests(unittest.TestCase):
    def test_retention_engine_review_keeps_exit_20_contract(self):
        report = {
            "retention_score": 75.2,
            "threshold": 78.0,
            "status": "REVIEW",
            "issues": [],
        }
        with mock.patch.object(sys, "argv", ["retention_engine.py", "--repair", "--enforce"]), \
             mock.patch.object(retention_engine, "score", side_effect=[dict(report), dict(report)]), \
             mock.patch.object(retention_engine, "repair_pacing", return_value=[]), \
             mock.patch.object(retention_engine, "atomic"):
            rc = retention_engine.main()
        self.assertEqual(rc, 20)

    def test_retention_engine_block_remains_fatal(self):
        report = {
            "retention_score": 62.0,
            "threshold": 78.0,
            "status": "BLOCK",
            "issues": ["critical"],
        }
        with mock.patch.object(sys, "argv", ["retention_engine.py", "--enforce"]), \
             mock.patch.object(retention_engine, "score", return_value=dict(report)), \
             mock.patch.object(retention_engine, "atomic"):
            rc = retention_engine.main()
        self.assertEqual(rc, 1)

    def test_canonical_pipeline_accepts_review_code_and_continues(self):
        calls = []

        class FakePipeline:
            def run(self, title, script, *args, **kwargs):
                calls.append((title, script, args, kwargs))
                if script == "retention_engine.py":
                    return 20
                return 0

        main.stages_before_render(FakePipeline())
        retention = [x for x in calls if x[1] == "retention_engine.py"]
        self.assertEqual(len(retention), 1)
        self.assertEqual(retention[0][3].get("allow_codes"), {0, 20})
        self.assertIn("--repair", retention[0][2])
        self.assertIn("--enforce", retention[0][2])

    def test_pre_render_recovery_repairs_retention_without_enforce(self):
        source = open(production_recovery.__file__, encoding="utf-8").read()
        self.assertNotIn(
            '("retention_engine.py", ("--repair", "--enforce"))',
            source,
        )
        self.assertGreaterEqual(
            source.count('("retention_engine.py", ("--repair",))'),
            2,
        )

    def test_resume_accepts_review_checkpoint_but_rejects_block(self):
        def fake_read_json(path):
            name = str(path)
            if "retention_" in name:
                return {"retention_score": 75.2, "status": "REVIEW"}
            return {"ok": True}

        with mock.patch.object(resume_short_runtime, "pro_plan_ok", return_value=True), \
             mock.patch.object(resume_short_runtime, "nonempty", return_value=True), \
             mock.patch.object(resume_short_runtime, "read_json", side_effect=fake_read_json):
            self.assertTrue(resume_short_runtime.consolidation_plan_ok("case"))

        def blocked_read_json(path):
            name = str(path)
            if "retention_" in name:
                return {"retention_score": 62.0, "status": "BLOCK"}
            return {"ok": True}

        with mock.patch.object(resume_short_runtime, "pro_plan_ok", return_value=True), \
             mock.patch.object(resume_short_runtime, "nonempty", return_value=True), \
             mock.patch.object(resume_short_runtime, "read_json", side_effect=blocked_read_json):
            self.assertFalse(resume_short_runtime.consolidation_plan_ok("case"))


if __name__ == "__main__":
    unittest.main()
