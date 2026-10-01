import json
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
        ped.EXPECTED = self.old["expected"]
        ped.PROFILE = self.old["profile"]
        ped.SCENE_MAP = self.old["scene_map"]
        ped.RHYTHM_PLAN = self.old["rhythm"]
        ped.MOTION_PLAN = self.old["motion"]
        ped.OUTPUT = self.old["output"]
        self.temp.cleanup()

    def test_true_crime_plan_is_restrained_and_varied(self):
        plan = ped.build_plan()
        self.assertEqual(plan["profile"], "true_crime")
        self.assertEqual(plan["scene_count"], 12)
        self.assertGreaterEqual(plan["professional_score"], 88)
        self.assertLess(plan["finish"]["saturation"], 1.0)
        self.assertAlmostEqual(plan["audio"]["target_lufs"], -14.0)
        self.assertLess(plan["scenes"][0]["transition_duration"], plan["scenes"][2]["transition_duration"])
        self.assertLessEqual(
            max(x["zoom_end"] - x["zoom_start"] for x in plan["scenes"] if x["media_type"] == "photo"),
            0.0281,
        )
        self.assertGreaterEqual(len({x["pace_multiplier"] for x in plan["scenes"]}), 3)


class CanonicalProfessionalPipelineTests(unittest.TestCase):
    def test_main_is_single_production_pipeline(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("PROFESSIONAL_CANONICAL", source)
        for required in (
            "media_engine_v2.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
            "multi_asset_director.py",
            "sound_design_engine.py",
            "speech_director.py",
            "professional_caption_director.py",
            "caption_layout_guard.py",
            "audio_finalizer.py",
            "visual_qa.py",
            "professional_quality_gate.py",
            "release_gate.py",
        ):
            self.assertIn(required, source)
        self.assertNotIn("media_stage_runtime.py", source)
        self.assertNotIn("STANDARD_ROLLBACK", source)
        self.assertNotIn("SAP_PRO_EDIT", source)
        self.assertNotIn('"video.py"', source)
        self.assertNotIn('"v6_runtime.py"', source)

    def test_profile_run_delegates_to_main_only(self):
        text = (ROOT / "profile_run.sh").read_text(encoding="utf-8")
        self.assertIn('MAIN="$BASE/main.py"', text)
        self.assertIn("PROFESSIONAL_CANONICAL", text)
        self.assertNotIn("STANDARD_ROLLBACK", text)
        self.assertNotIn("SAP_PRO_EDIT", text)
        self.assertNotIn("gerar_short.sh", text)

    def test_professional_renderer_uses_policy_loudness(self):
        text = (ROOT / "v6_professional.py").read_text(encoding="utf-8")
        self.assertIn("target_lufs", text)
        self.assertIn("SAP_AUDIO_TARGET_LUFS", text)
        self.assertNotIn('"I=-16:', text)
        self.assertIn("deterministic_pick", text)

    def test_professional_scene_assembler_has_multibeat_motion(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertIn("pow(", text)
        self.assertIn("transition_duration", text)
        self.assertIn("multi_asset", text)
        self.assertIn("pro_edit_runtime_", text)

    def test_professional_quality_is_observational_until_calibration(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('SAP_PROFESSIONAL_ENFORCE", "0"', text)
        self.assertIn("SAP_PROFESSIONAL_MIN_SCORE", text)
        self.assertIn("measure_loudness", text)


class CanonicalResumeTests(unittest.TestCase):
    def test_old_partial_state_falls_back_to_full(self):
        with patch.object(rsr, "final_ok", return_value=False), patch.object(rsr, "consolidation_plan_ok", return_value=False):
            self.assertEqual(rsr.boundary("x"), "full")

    def test_resume_contains_only_v2_render_route(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("render_engine_v2.py", text)
        self.assertIn("media_engine_v2.py", text)
        self.assertIn("render_plan_v2.py", text)
        self.assertNotIn("media_stage_runtime.py", text)
        self.assertNotIn("STANDARD_ROLLBACK", text)
        self.assertNotIn("SAP_PRO_EDIT", text)
        self.assertNotIn('"video.py"', text)
        self.assertNotIn('"v6_runtime.py"', text)


if __name__ == "__main__":
    unittest.main()
