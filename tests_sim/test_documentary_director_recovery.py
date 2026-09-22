"""Contract tests for Documentary Director on top of shared gemini_runtime."""
import contextlib
import copy
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gemini_runtime import GeminiTemporaryUnavailable

ROOT = Path(__file__).resolve().parents[1]


class DocumentaryDirectorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.folder = self.base / "roteiros"
        self.folder.mkdir()
        self.sid = "test-director"
        self.scenes = [{
            "scene": i,
            "segment": f"Narração original {i}.",
            "query": "historic railway station archival photograph",
            "must_have": ["railway station"],
            "avoid": ["modern cars", "portraits"],
            "visual_mode": "location",
            "shot_type": "wide",
            "timing": {"start": i},
        } for i in range(1, 13)]
        self.original = {"scenes": self.scenes, "provenance": "preserve-me"}
        self.path = self.folder / f"scene_map_{self.sid}.json"
        self.path.write_text(json.dumps(self.original), encoding="utf-8")
        for prefix in ("fonte", "used_topic"):
            (self.folder / f"{prefix}_{self.sid}.txt").write_text(
                "Estação ferroviária histórica", encoding="utf-8"
            )
        self.valid = {"scenes": copy.deepcopy(self.scenes)}

    def execute(self, responses):
        output = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "SHORTAUTOPRO_BASE": str(self.base),
                    "SHORT_ID": self.sid,
                    "SHORT_QTD_CENAS": "12",
                    "GEMINI_API_KEY": "test-only",
                },
                clear=False,
            ),
            patch("gemini_runtime.generate_text", side_effect=responses) as generate,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(output),
        ):
            try:
                runpy.run_path(
                    str(ROOT / "documentary_director.py"),
                    run_name="__main__",
                )
                self.exit = 0
            except SystemExit as exc:
                self.exit = exc.code
        self.output = output.getvalue()
        self.generate = generate
        report = self.folder / f"documentary_director_{self.sid}.json"
        self.report = json.loads(report.read_text()) if report.exists() else {}
        self.result = json.loads(self.path.read_text())

    def assert_degraded_preserved(self):
        self.assertEqual(self.result, self.original)
        self.assertEqual(self.report["status"], "DEGRADED")
        self.assertTrue(self.report["preserved_original_scene_map"])
        self.assertEqual(self.exit, 0)

    def test_success_preserves_narration_timing_and_metadata(self):
        self.execute([json.dumps(self.valid)])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.report["version"], "3.6")
        self.assertEqual(self.report["attempts"], 1)
        self.assertEqual(self.result["provenance"], "preserve-me")
        self.assertEqual(self.result["scenes"], self.scenes)
        backup = self.folder / f"scene_map_pre_documentary_{self.sid}.json"
        self.assertEqual(json.loads(backup.read_text()), self.original)

    def test_malformed_json_retries_and_recovers(self):
        self.execute(['{"scenes":[', json.dumps(self.valid)])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(self.report["attempts"], 2)

    def test_exhaustion_preserves_input_and_records_each_attempt(self):
        self.execute(["invalid"] * 3)
        self.assert_degraded_preserved()
        self.assertEqual(self.generate.call_count, 3)
        self.assertEqual(self.report["attempts"], 3)
        self.assertEqual(len(self.report["attempt_history"]), 3)

    def test_fenced_json_and_quoted_prose(self):
        for prefix, suffix in [
            ("\x60\x60\x60json\n", "\n\x60\x60\x60"),
            ('Resposta "documental":\n', "\nFim."),
        ]:
            with self.subTest(prefix=prefix):
                self.execute([prefix + json.dumps(self.valid) + suffix])
                self.assertEqual(self.exit, 0)

    def test_invalid_scene_contract_retries(self):
        case = copy.deepcopy(self.valid)
        case["scenes"][0]["visual_mode"] = "nonsense"
        self.execute([json.dumps(case), json.dumps(self.valid)])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.generate.call_count, 2)

    def test_typed_shared_runtime_outage_fails_open_once(self):
        self.execute([GeminiTemporaryUnavailable("capacity")])
        self.assert_degraded_preserved()
        self.assertEqual(self.generate.call_count, 1)
        self.assertEqual(self.report["attempts"], 1)

    def test_literal_braces_and_markdown_inside_json_strings_are_preserved(self):
        self.valid["scenes"][0]["query"] = (
            'archive "railway" station {historic} photograph'
        )
        self.execute([json.dumps(self.valid)])
        self.assertEqual(self.exit, 0)
        self.assertEqual(
            self.result["scenes"][0]["query"],
            self.valid["scenes"][0]["query"],
        )

    def test_extra_nonobject_scene_blocks_before_ai(self):
        self.original["scenes"].append(None)
        self.path.write_text(json.dumps(self.original), encoding="utf-8")
        self.execute([])
        self.assertNotEqual(self.exit, 0)
        self.assertEqual(self.generate.call_count, 0)
        self.assertEqual(self.result, self.original)

    def test_corrupt_original_map_blocks_before_ai(self):
        self.original["scenes"][0]["scene"] = True
        self.path.write_text(json.dumps(self.original), encoding="utf-8")
        self.execute([])
        self.assertNotEqual(self.exit, 0)
        self.assertEqual(self.generate.call_count, 0)
        self.assertEqual(self.result, self.original)

    def test_version_can_be_checked_without_api_or_artifacts(self):
        env = dict(
            os.environ,
            SHORTAUTOPRO_BASE=str(self.base / "absent"),
            GEMINI_API_KEY="",
        )
        proc = subprocess.run(
            [sys.executable, str(ROOT / "documentary_director.py"), "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("STABLE 3.6", proc.stdout)


if __name__ == "__main__":
    unittest.main()
