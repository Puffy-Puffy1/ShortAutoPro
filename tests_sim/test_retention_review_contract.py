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
        with mock.patch.object(sys, "argv", ["retention_engine.py", "--repair", "--enforce"]),              mock.patch.object(retention_engine, "score", side_effect=[dict(report), dict(report)]),              mock.patch.object(retention_engine, "repair_pacing", return_value=[]),              mock.patch.object(retention_engine, "atomic"):
            rc = retention_engine.main()
        self.assertEqual(rc, 20)

    def test_retention_engine_block_remains_fatal(self):
        report = {
            "retention_score": 62.0,
            "threshold": 78.0,
            "status": "BLOCK",
            "issues": ["critical"],
        }
        with mock.patch.object(sys, "argv", ["retention_engine.py", "--enforce"]),              mock.patch.object(retention_engine, "score", return_value=dict(report)),              mock.patch.object(retention_engine, "atomic"):
            rc = retention_engine.main()
        self.assertEqual(rc, 1)

    def test_canonical_pipeline_uses_v2_and_does_not_invoke_legacy_stage6(self):
        calls = []

        class FakePipeline:
            sid = "case"

            def run(self, title, script, *args, **kwargs):
                calls.append((title, script, args, kwargs))
                return 0

        main.stages_before_render(FakePipeline())
        scripts = [x[1] for x in calls]
        self.assertIn("media_engine_v2.py", scripts)
        self.assertIn("render_plan_v2.py", scripts)
        self.assertNotIn("media_stage_runtime.py", scripts)
        self.assertNotIn("retention_engine.py", scripts)

    def test_pre_render_recovery_repairs_only_v2_inputs(self):
        source = open(production_recovery.__file__, encoding="utf-8").read()
        self.assertIn("media_engine_v2.py", source)
        self.assertIn("render_plan_v2.py", source)
        self.assertNotIn("retention_engine.py", source)
        self.assertNotIn("media_stage_runtime.py", source)

    def test_resume_requires_frozen_v2_manifest(self):
        valid_plan = {
            "schema_version": "render-plan-v2",
            "short_id": "case",
            "scenes": [{"scene": i} for i in range(1, 13)],
        }
        valid_manifest = {
            "schema_version": "media-manifest-v2",
            "short_id": "case",
            "immutable": True,
            "scenes": [
                {"scene": i, "asset": {"validated": True, "checksum_sha256": f"sha-{i}"}}
                for i in range(1, 13)
            ],
        }
        with mock.patch.object(
            resume_short_runtime,
            "read_json",
            side_effect=lambda path: valid_plan if "pro_edit_plan_" in str(path) else valid_manifest,
        ):
            self.assertTrue(resume_short_runtime.consolidation_plan_ok("case"))

        blocked_manifest = dict(valid_manifest)
        blocked_manifest["immutable"] = False
        with mock.patch.object(
            resume_short_runtime,
            "read_json",
            side_effect=lambda path: valid_plan if "pro_edit_plan_" in str(path) else blocked_manifest,
        ):
            self.assertFalse(resume_short_runtime.consolidation_plan_ok("case"))


if __name__ == "__main__":
    unittest.main()
