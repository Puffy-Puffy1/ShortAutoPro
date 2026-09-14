import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "batch_report.py"


class BatchReportBaseTests(unittest.TestCase):
    def test_respects_shortautopro_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifests = base / "manifests"
            manifests.mkdir(parents=True)

            manifest = {
                "short_id": "test_run_001",
                "status": "QUALITY_PASS",
                "topic": "Teste isolado",
                "hook": "Hook factual de teste",
                "publish": {"chosen_title": "Título de teste"},
                "video": {
                    "duration_seconds": 42.5,
                    "path": str(base / "videos" / "short.mp4"),
                },
                "quality": {
                    "resolution_ok": True,
                    "fps_ok": True,
                    "audio_exists": True,
                    "physical_scene_count": 12,
                    "expected_scene_count": 12,
                },
            }
            (manifests / "test_run_001.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "1"],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("BATCH REPORT: OK", result.stdout)

            reports = list((base / "reports").glob("batch_report_*.json"))
            self.assertEqual(len(reports), 1)
            payload = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["quality_pass"], 1)
            self.assertEqual(payload["failures"], 0)
            self.assertEqual(payload["productions"][0]["short_id"], "test_run_001")


if __name__ == "__main__":
    unittest.main()
