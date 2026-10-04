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

    def test_canonical_pipeline_uses_v3_and_does_not_invoke_legacy_stage6(self):
        calls = []

        class FakePipeline:
            sid = "case"

            def run(self, title, script, *args, **kwargs):
                calls.append((title, script, args, kwargs))
                return 0

        main.stages_before_render(FakePipeline())
        scripts = [x[1] for x in calls]
        self.assertIn("media_acquisition_v3.py", scripts)
        self.assertIn("render_plan_v2.py", scripts)
        self.assertNotIn("media_stage_runtime.py", scripts)
        self.assertNotIn("retention_engine.py", scripts)

    def test_pre_render_recovery_uses_only_v3_inputs(self):
        source = open(production_recovery.__file__, encoding="utf-8").read()
        self.assertIn("media_acquisition_v3.py", source)
        self.assertIn("render_plan_v2.py", source)
        self.assertNotIn("retention_engine.py", source)
        self.assertNotIn("media_stage_runtime.py", source)

    def test_resume_requires_frozen_v3_manifest(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        import media_acquisition_v3

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sid = "case"
            (base / "roteiros").mkdir(parents=True)
            (base / "manifests").mkdir(parents=True)
            (base / "imagens" / f"short_{sid}").mkdir(parents=True)
            plan = {
                "schema_version": "render-plan-v2",
                "short_id": sid,
                "scenes": [{"scene_id": str(i)} for i in range(1, 13)],
            }
            (base / "roteiros" / f"pro_edit_plan_{sid}.json").write_text(
                json.dumps(plan), encoding="utf-8"
            )
            rows = []
            for i in range(1, 13):
                asset = base / "imagens" / f"short_{sid}" / f"scene_{i:02d}.jpg"
                asset.write_bytes(b"x" * 2000)
                digest = hashlib.sha256(asset.read_bytes()).hexdigest()
                rows.append({
                    "scene_id": str(i),
                    "scene_number": i,
                    "asset": {
                        "validated": True,
                        "checksum_sha256": digest,
                        "path": str(asset),
                    },
                })
            manifest = {
                "schema_version": "media-manifest-v2",
                "engine_version": "3.0.0",
                "short_id": sid,
                "immutable": True,
                "scene_count": 12,
                "scenes": rows,
            }
            manifest["integrity_sha256"] = media_acquisition_v3.digest(manifest)
            (base / "manifests" / f"media_{sid}.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with mock.patch.object(resume_short_runtime, "BASE", base):
                self.assertTrue(resume_short_runtime.consolidation_plan_ok(sid))

            manifest["immutable"] = False
            (base / "manifests" / f"media_{sid}.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with mock.patch.object(resume_short_runtime, "BASE", base):
                self.assertFalse(resume_short_runtime.consolidation_plan_ok(sid))



if __name__ == "__main__":
    unittest.main()
