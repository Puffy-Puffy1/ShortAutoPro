import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import professional_edit_director as ped
import resume_short_runtime as rsr


ROOT = Path(__file__).resolve().parents[1]


class ProfessionalEditDirectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = {
            "base": ped.BASE,
            "scene_map": ped.SCENE_MAP,
            "rhythm": ped.RHYTHM_PLAN,
            "motion": ped.MOTION_PLAN,
            "output": ped.OUTPUT,
            "profile": ped.PROFILE,
            "expected": ped.EXPECTED,
        }
        ped.BASE = self.base
        ped.EXPECTED = 12
        ped.PROFILE = "true_crime"
        roteiros = self.base / "roteiros"
        roteiros.mkdir(parents=True)
        ped.SCENE_MAP = roteiros / "scene_map_test.json"
        ped.RHYTHM_PLAN = roteiros / "rhythm_plan_test.json"
        ped.MOTION_PLAN = roteiros / "motion_plan_test.json"
        ped.OUTPUT = roteiros / "pro_edit_plan_test.json"

        scene_map = {"scenes": []}
        rhythm = {"scenes": []}
        roles = ["hook", "context", "evidence", "development", "escalation", "development", "reveal", "explanation", "development", "aftermath", "payoff", "conclusion"]
        shots = ["closeup", "wide", "detail", "medium", "wide", "closeup", "detail", "medium", "wide", "portrait", "detail", "wide"]
        for i in range(1, 13):
            scene_map["scenes"].append({
                "scene": i,
                "narrative_role": roles[i - 1],
                "visual_mode": "evidence" if roles[i - 1] == "evidence" else "environment",
                "shot_type": shots[i - 1],
                "segment": "texto factual da cena com palavras suficientes",
                "words": 8,
            })
            rhythm["scenes"].append({
                "scene": i,
                "media_type": "photo" if i % 4 else "video",
                "shot_type": shots[i - 1],
                "visual_mode": scene_map["scenes"][-1]["visual_mode"],
                "energy": 4 if roles[i - 1] in {"hook", "escalation"} else 2 if roles[i - 1] in {"evidence", "conclusion"} else 3,
                "zoom_start": 1.0,
                "zoom_end": 1.04,
                "pan": "right" if i % 2 else "left",
                "motion_profile": "test",
            })
        ped.SCENE_MAP.write_text(json.dumps(scene_map), encoding="utf-8")
        ped.RHYTHM_PLAN.write_text(json.dumps(rhythm), encoding="utf-8")

    def tearDown(self):
        ped.BASE = self.old["base"]
        ped.SCENE_MAP = self.old["scene_map"]
        ped.RHYTHM_PLAN = self.old["rhythm"]
        ped.MOTION_PLAN = self.old["motion"]
        ped.OUTPUT = self.old["output"]
        ped.PROFILE = self.old["profile"]
        ped.EXPECTED = self.old["expected"]
        self.temp.cleanup()

    def test_true_crime_plan_is_restrained_and_varied(self):
        plan = ped.build_plan()
        self.assertEqual(plan["profile"], "true_crime")
        self.assertEqual(plan["scene_count"], 12)
        self.assertGreaterEqual(plan["professional_score"], 88)
        self.assertLess(plan["finish"]["saturation"], 1.0)
        self.assertAlmostEqual(plan["audio"]["target_lufs"], -14.0)
        self.assertLess(plan["scenes"][0]["transition_duration"], plan["scenes"][2]["transition_duration"])
        self.assertLessEqual(max(x["zoom_end"] - x["zoom_start"] for x in plan["scenes"] if x["media_type"] == "photo"), 0.0281)
        self.assertGreaterEqual(len({x["pace_multiplier"] for x in plan["scenes"]}), 3)


class UnifiedProfessionalPipelineTests(unittest.TestCase):
    def test_canonical_pipeline_contains_both_modes_without_runtime_patching(self):
        source = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")
        self.assertIn('SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"', source)
        self.assertIn("professional_edit_director.py", source)
        self.assertIn("professional_edit_repair.py", source)
        self.assertIn("professional_caption_director.py", source)
        self.assertIn("video_professional.py", source)
        self.assertIn('"video.py"', source)
        self.assertIn("professional_quality_gate.py", source)
        self.assertIn("v6_runtime.py", source)
        self.assertNotIn("professional_pipeline_runtime.py", source)
        self.assertNotIn("v6_professional_runtime.py", source)

    def test_profile_run_uses_one_canonical_generator_with_explicit_rollback(self):
        text = (ROOT / "profile_run.sh").read_text(encoding="utf-8")
        self.assertIn('SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"', text)
        self.assertIn('GENERATOR="$BASE/gerar_short.sh"', text)
        self.assertIn("STANDARD_ROLLBACK", text)
        self.assertNotIn("gerar_short_professional.sh", text)

    def test_professional_renderer_uses_policy_loudness_not_legacy_minus16(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("target_lufs", text)
        self.assertIn("SAP_AUDIO_TARGET_LUFS", text)
        self.assertNotIn('"I=-16:', text)
        self.assertIn("curated_sfx", text)
        self.assertIn("deterministic_pick", text)

    def test_professional_scene_assembler_has_smoothstep_and_variable_transitions(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertIn("pow(", text)
        self.assertIn("transition_duration", text)
        self.assertIn("PRO_CAPTION_SEMANTIC", text)
        self.assertIn("pro_edit_runtime_", text)

    def test_professional_quality_is_observational_by_default(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('SAP_PROFESSIONAL_ENFORCE", "0"', text)
        self.assertIn("SAP_PROFESSIONAL_MIN_SCORE", text)
        self.assertIn("measure_loudness", text)


class UnifiedResumeTests(unittest.TestCase):
    def test_partial_professional_resume_without_plan_falls_back_full(self):
        with patch.object(rsr, "base_boundary", return_value="post_audio"), patch.object(rsr, "pro_plan_ok", return_value=False), patch.dict(os.environ, {"SAP_PRO_EDIT": "1"}, clear=False):
            self.assertEqual(rsr.boundary("x"), "full")

    def test_standard_resume_does_not_require_professional_plan(self):
        with patch.object(rsr, "base_boundary", return_value="post_audio"), patch.object(rsr, "pro_plan_ok", return_value=False), patch.dict(os.environ, {"SAP_PRO_EDIT": "0"}, clear=False):
            self.assertEqual(rsr.boundary("x"), "post_audio")

    def test_unified_resume_contains_professional_and_standard_routes(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("video_professional.py", text)
        self.assertIn('"video.py"', text)
        self.assertIn("professional_quality_gate.py", text)
        self.assertIn("v6_runtime.py", text)
        self.assertNotIn("v6_professional_runtime.py", text)
        self.assertNotIn("gerar_short_professional.sh", text)


if __name__ == "__main__":
    unittest.main()
