import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_stage_runtime as stage
import resume_short_runtime as resume


class Stage6TimeoutResumeTests(unittest.TestCase):
    def test_outer_round_budget_matches_selector_scene_budget(self):
        report = {"pending_scenes": list(range(3, 13))}
        with mock.patch.object(stage, "read_report", return_value=report), \
             mock.patch.object(stage, "scene_count_hint", return_value=12), \
             mock.patch.dict(os.environ, {}, clear=False):
            for key in (
                "SAP_MEDIA_ROUND_TIMEOUT",
                "SAP_MEDIA_SCENE_BUDGET_SECONDS",
                "SAP_MEDIA_ROUND_GRACE_SECONDS",
            ):
                os.environ.pop(key, None)
            timeout, remaining = stage.round_timeout_seconds()
        self.assertEqual(remaining, 10)
        self.assertEqual(timeout, 192)
        self.assertGreater(timeout, 128)

    def test_final_editorial_completion_is_bounded_and_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            media = base / "imagens" / "short_case"
            media.mkdir(parents=True)
            candidates = []
            for number in (11, 12):
                path = media / f"scene_{number:02d}.jpg"
                candidates.append({
                    "fonte": "EditorialReuse",
                    "tipo": "foto",
                    "local_path": str(path),
                    "truth_claim": "NONE",
                    "id": f"editorial-{number}",
                })

            certified = {
                "valid": 12,
                "expected": 12,
                "missing": [],
                "invalid": [],
                "errors": [],
            }
            with mock.patch.object(stage, "BASE", base), \
                 mock.patch.object(stage, "SID", "case"), \
                 mock.patch.object(stage, "create_editorial_reuse", side_effect=candidates) as create, \
                 mock.patch.object(stage, "_probe_asset", return_value=(True, "ok")), \
                 mock.patch.object(stage, "_scene_rows", return_value=[{} for _ in range(12)]), \
                 mock.patch.object(stage, "write_provenance"), \
                 mock.patch.object(stage.visual_engine_unified, "note_commit_runtime"), \
                 mock.patch.object(stage, "_atomic_json"), \
                 mock.patch.object(stage, "_clear_missing_report"), \
                 mock.patch.object(stage, "validate_media_completion", side_effect=[(True, certified), (True, certified)]):
                self.assertTrue(stage.final_editorial_completion([11, 12]))
            self.assertEqual(create.call_count, 2)

    def test_final_editorial_refuses_large_missing_set(self):
        with mock.patch.object(stage, "create_editorial_reuse") as create, \
             mock.patch.dict(os.environ, {"SAP_MEDIA_FINAL_EDITORIAL_MAX": "3"}, clear=False):
            self.assertFalse(stage.final_editorial_completion([1, 2, 3, 4]))
        create.assert_not_called()

    def test_pre_media_checkpoint_accepts_stage5e_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "case"
            r = base / "roteiros"
            r.mkdir(parents=True)
            (r / f"short_{sid}.txt").write_text("roteiro " * 20, encoding="utf-8")
            (r / f"fonte_{sid}.txt").write_text("fonte factual " * 20, encoding="utf-8")
            (r / f"used_topic_{sid}.txt").write_text("Tema", encoding="utf-8")
            (r / f"scene_map_{sid}.json").write_text(
                json.dumps({"scenes": [{"scene": i} for i in range(1, 13)]}),
                encoding="utf-8",
            )
            (r / f"post_script_truth_{sid}.json").write_text(
                json.dumps({"status": "PASS"}), encoding="utf-8"
            )
            (r / f"semantic_integrity_{sid}.json").write_text(
                json.dumps({"status": "PASS"}), encoding="utf-8"
            )
            (r / f"visual_continuity_{sid}.json").write_text(
                json.dumps({"status": "REVIEW", "visual_continuity_score": 53.3}),
                encoding="utf-8",
            )

            with mock.patch.object(resume, "BASE", base), \
                 mock.patch.dict(os.environ, {"SHORT_QTD_CENAS": "12"}, clear=False):
                self.assertTrue(resume.pre_media_plan_ok(sid))

    def test_boundary_prefers_stage6_resume_over_full_rerun(self):
        with mock.patch.object(resume, "render_ok", return_value=False), \
             mock.patch.object(resume, "final_ok", return_value=False), \
             mock.patch.object(resume, "consolidation_plan_ok", return_value=False), \
             mock.patch.object(resume, "pre_media_plan_ok", return_value=True):
            self.assertEqual(resume.boundary("case"), "post_scene_plan")


if __name__ == "__main__":
    unittest.main()
