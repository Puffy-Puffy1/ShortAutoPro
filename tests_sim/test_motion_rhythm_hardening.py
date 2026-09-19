import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MOTION = REPO / "motion_director.py"
RHYTHM = REPO / "rhythm_director.py"
MIDIA = REPO / "midia.py"


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class MotionRhythmHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env.update({
            "SHORTAUTOPRO_BASE": str(self.base),
            "SHORT_ID": "case",
            "SHORT_QTD_CENAS": "6",
        })
        (self.base / "roteiros").mkdir(parents=True, exist_ok=True)
        (self.base / "imagens" / "short_case").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script: Path):
        return subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def prepare_valid_input(self):
        scenes = []
        for i in range(1, 7):
            scenes.append({
                "scene": i,
                "segment": f"Trecho narrativo {i}",
                "query": f"documentary scene {i}",
                "must_have": ["documentary"],
                "avoid": [],
                "words": 4,
            })
            (self.base / "imagens" / "short_case" / f"scene_{i:02d}.jpg").write_bytes(b"x")
        write_json(self.base / "roteiros" / "scene_map_case.json", {"scenes": scenes})
        return scenes

    def test_motion_rejects_missing_media(self):
        scenes = self.prepare_valid_input()
        (self.base / "imagens" / "short_case" / "scene_06.jpg").unlink()
        result = self.run_script(MOTION)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mídia", result.stdout.lower())

    def test_motion_and_rhythm_accept_configured_six_scene_contract(self):
        self.prepare_valid_input()
        motion = self.run_script(MOTION)
        self.assertEqual(motion.returncode, 0, motion.stdout + motion.stderr)
        rhythm = self.run_script(RHYTHM)
        self.assertEqual(rhythm.returncode, 0, rhythm.stdout + rhythm.stderr)

    def test_rhythm_accepts_human_context_video_without_artificial_pan(self):
        scenes = self.prepare_valid_input()
        motion = self.run_script(MOTION)
        self.assertEqual(motion.returncode, 0, motion.stdout + motion.stderr)
        path = self.base / "roteiros" / "motion_plan_case.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["scenes"][0]["media_type"] = "video"
        payload["scenes"][0]["shot_type"] = "human_context"
        payload["scenes"][0]["pan"] = "center"
        write_json(path, payload)
        rhythm = self.run_script(RHYTHM)
        self.assertEqual(rhythm.returncode, 0, rhythm.stdout + rhythm.stderr)

    def test_motion_rejects_nonsequential_scene_map(self):
        scenes = self.prepare_valid_input()
        payload = {"scenes": scenes}
        payload["scenes"][2]["scene"] = 4
        write_json(self.base / "roteiros" / "scene_map_case.json", payload)
        result = self.run_script(MOTION)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("numeração", result.stdout)

    def test_rhythm_rejects_malformed_zoom(self):
        self.prepare_valid_input()
        motion = self.run_script(MOTION)
        self.assertEqual(motion.returncode, 0, motion.stdout + motion.stderr)
        path = self.base / "roteiros" / "motion_plan_case.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["scenes"][1]["zoom_end"] = "oops"
        write_json(path, payload)
        result = self.run_script(RHYTHM)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("zoom_end", result.stdout)

    def test_media_selector_is_native_and_compiles(self):
        source = MIDIA.read_text(encoding="utf-8")
        self.assertIn("largura * altura < 320 * 180", source)
        self.assertIn("def _sap_professional_media_accept_v1", source)
        pipeline = (REPO / "main.py").read_text(encoding="utf-8")
        self.assertIn('p.run("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py"', pipeline)
        self.assertNotIn("midia_runtime.py", pipeline)
        self.assertFalse((REPO / "gerar_short.sh").exists())
        runtime = (REPO / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn('MIDIA = BASE / "midia.py"', runtime)
        compile(source, str(MIDIA), "exec")
        compile(runtime, "media_stage_runtime.py", "exec")


if __name__ == "__main__":
    unittest.main()
