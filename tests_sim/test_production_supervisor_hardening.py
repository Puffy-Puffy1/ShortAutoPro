import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "production_supervisor.py"


def env_for(base):
    env = os.environ.copy()
    env.update(
        {
            "SHORTAUTOPRO_BASE": str(base),
            "SHORT_ID": "case",
            "SHORT_QTD_CENAS": "6",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return env


def prepare(base, scene_numbers=None, duplicate_media=False):
    r = base / "roteiros"
    media = base / "imagens" / "short_case"
    r.mkdir(parents=True, exist_ok=True)
    media.mkdir(parents=True, exist_ok=True)

    (r / "used_topic_case.txt").write_text("Voo MH370", encoding="utf-8")
    (r / "short_case.txt").write_text(
        " ".join(f"palavra{i}" for i in range(110)), encoding="utf-8"
    )
    (r / "fonte_case.txt").write_text(
        "ASSUNTO: Voo MH370\nFONTE: Wikipedia — Malaysia Airlines Flight 370\nMH370",
        encoding="utf-8",
    )

    numbers = scene_numbers or list(range(1, 7))
    (r / "scene_map_case.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene": number,
                        "query": f"query {index}",
                        "must_have": [f"anchor{index}"],
                        "visual_mode": [
                            "document", "location", "transport",
                            "object", "environment", "human_context",
                        ][index - 1],
                    }
                    for index, number in enumerate(numbers, start=1)
                ]
            }
        ),
        encoding="utf-8",
    )
    (r / "motion_plan_case.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {"scene": i, "motion_profile": f"profile{i}"}
                    for i in range(1, 7)
                ]
            }
        ),
        encoding="utf-8",
    )

    for i in range(1, 7):
        (media / f"scene_{i:02d}.jpg").write_bytes(b"asset")
    if duplicate_media:
        (media / "scene_01.webp").write_bytes(b"duplicate")


class ProductionSupervisorHardeningTests(unittest.TestCase):
    def run_case(self, base):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(REPO),
            env=env_for(base),
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_nonsequential_scene_map_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            prepare(base, scene_numbers=[1, 2, 4, 3, 5, 6])
            result = self.run_case(base)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (base / "roteiros" / "supervisor_case.json").read_text(encoding="utf-8")
            )
            self.assertIn("scene_map_numbering_invalid", report["critical"])

    def test_duplicate_media_scene_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            prepare(base, duplicate_media=True)
            result = self.run_case(base)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (base / "roteiros" / "supervisor_case.json").read_text(encoding="utf-8")
            )
            self.assertIn("media_duplicate_scene:1", report["critical"])


if __name__ == "__main__":
    unittest.main()
