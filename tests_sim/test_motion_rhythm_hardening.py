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


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def scene_map(count=6):
    return {
        "scenes": [
            {
                "scene": i,
                "visual_mode": "environment" if i % 2 else "document",
                "shot_type": "medium",
            }
            for i in range(1, count + 1)
        ]
    }


class MotionRhythmHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "roteiros").mkdir(parents=True)
        (self.base / "imagens" / "short_case").mkdir(parents=True)
        self.env = os.environ.copy()
        self.env.update(
            {
                "SHORTAUTOPRO_BASE": str(self.base),
                "SHORT_ID": "case",
                "SHORT_QTD_CENAS": "6",
                "PYTHONIOENCODING": "utf-8",
            }
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script):
        return subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def prepare_valid_input(self):
        write_json(self.base / "roteiros" / "scene_map_case.json", scene_map())
        media = self.base / "imagens" / "short_case"
        for i in range(1, 7):
            suffix = ".webp" if i == 1 else ".jpg"
            (media / f"scene_{i:02d}{suffix}").write_bytes(b"x")

    def test_motion_and_rhythm_accept_configured_six_scene_contract(self):
        self.prepare_valid_input()

        motion = self.run_script(MOTION)
        self.assertEqual(motion.returncode, 0, motion.stdout + motion.stderr)

        motion_payload = json.loads(
            (self.base / "roteiros" / "motion_plan_case.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(motion_payload["scene_count"], 6)
        self.assertEqual(motion_payload["expected_scenes"], 6)
        self.assertEqual(
            [x["scene"] for x in motion_payload["scenes"]],
            list(range(1, 7)),
        )
        self.assertEqual(motion_payload["scenes"][0]["media_type"], "photo")

        rhythm = self.run_script(RHYTHM)
        self.assertEqual(rhythm.returncode, 0, rhythm.stdout + rhythm.stderr)

        rhythm_payload = json.loads(
            (self.base / "roteiros" / "rhythm_plan_case.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(rhythm_payload["expected_scenes"], 6)
        self.assertEqual(len(rhythm_payload["scenes"]), 6)
        self.assertTrue(
            (self.base / "roteiros" / "motion_plan_pre_rhythm_case.json").is_file()
        )

    def test_rhythm_accepts_human_context_video_without_artificial_pan(self):
        payload = scene_map()
        payload["scenes"][0]["visual_mode"] = "human_context"
        write_json(self.base / "roteiros" / "scene_map_case.json", payload)
        media = self.base / "imagens" / "short_case"
        (media / "scene_01.mp4").write_bytes(b"x")
        for i in range(2, 7):
            (media / f"scene_{i:02d}.jpg").write_bytes(b"x")

        motion = self.run_script(MOTION)
        self.assertEqual(motion.returncode, 0, motion.stdout + motion.stderr)

        rhythm = self.run_script(RHYTHM)
        self.assertEqual(rhythm.returncode, 0, rhythm.stdout + rhythm.stderr)
        rhythm_payload = json.loads(
            (self.base / "roteiros" / "rhythm_plan_case.json").read_text(
                encoding="utf-8"
            )
        )
        first = rhythm_payload["scenes"][0]
        self.assertEqual(first["media_type"], "video")
        self.assertEqual(first["visual_mode"], "human_context")
        self.assertEqual(first["pan"], "none")
        self.assertEqual(first["zoom_start"], 1.0)
        self.assertEqual(first["zoom_end"], 1.0)

    def test_motion_rejects_missing_media(self):
        self.prepare_valid_input()
        (self.base / "imagens" / "short_case" / "scene_04.jpg").unlink()

        result = self.run_script(MOTION)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mídia ausente", result.stdout)

    def test_motion_rejects_nonsequential_scene_map(self):
        payload = scene_map()
        payload["scenes"][2]["scene"] = 4
        write_json(self.base / "roteiros" / "scene_map_case.json", payload)
        media = self.base / "imagens" / "short_case"
        for i in range(1, 7):
            (media / f"scene_{i:02d}.jpg").write_bytes(b"x")

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
        self.assertNotIn("midia_runtime.py", (REPO / "gerar_short.sh").read_text(encoding="utf-8"))
        compile(source, str(MIDIA), "exec")


if __name__ == "__main__":
    unittest.main()
