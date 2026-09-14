import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BatchReportTests(unittest.TestCase):
    def test_malformed_numeric_fields_do_not_crash_report(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifests = base / "manifests"
            manifests.mkdir(parents=True)

            manifest = {
                "short_id": "test-001",
                "status": "QUALITY_PASS",
                "topic": "Teste",
                "hook": "Hook",
                "publish": {"chosen_title": "Título de teste"},
                "video": {
                    "duration_seconds": 42.5,
                    "path": str(base / "videos" / "test.mp4"),
                },
                "quality": {
                    "resolution_ok": True,
                    "fps_ok": True,
                    "audio_exists": True,
                    "physical_scene_count": "not-a-number",
                    "expected_scene_count": None,
                },
            }
            (manifests / "test-001.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            result = subprocess.run(
                [sys.executable, str(repo / "batch_report.py"), "1"],
                cwd=str(repo),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            reports = sorted((base / "reports").glob("batch_report_*.json"))
            self.assertEqual(len(reports), 1)
            data = json.loads(reports[0].read_text(encoding="utf-8"))
            production = data["productions"][0]
            self.assertEqual(production["scenes"], 0)
            self.assertEqual(production["expected_scenes"], 12)


if __name__ == "__main__":
    unittest.main()
