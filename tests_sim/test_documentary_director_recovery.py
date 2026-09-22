"""Execute the real stage with temporary artifacts and mocked HTTP only."""
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

import requests

ROOT = Path(__file__).resolve().parents[1]


class Response:
    def __init__(self, text="", *, parts=None, finish="STOP", status=200, envelope=None, headers=None):
        self.ok = status < 400
        self.status_code = status
        self.headers = headers or {}
        self.body = envelope if envelope is not None else {
            "candidates": [{"finishReason": finish, "content": {
                "parts": parts if parts is not None else [{"text": text}]
            }}]
        }

    def json(self):
        return self.body


class DocumentaryDirectorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.folder = self.base / "roteiros"
        self.folder.mkdir()
        self.sid = "test-director"
        self.scenes = [{
            "scene": i, "segment": f"Narração original {i}.",
            "query": "historic railway station archival photograph",
            "must_have": ["railway station"], "avoid": ["modern cars", "portraits"],
            "visual_mode": "location", "shot_type": "wide", "timing": {"start": i},
        } for i in range(1, 13)]
        self.original = {"scenes": self.scenes, "provenance": "preserve-me"}
        self.path = self.folder / f"scene_map_{self.sid}.json"
        self.path.write_text(json.dumps(self.original), encoding="utf-8")
        for prefix in ("fonte", "used_topic"):
            (self.folder / f"{prefix}_{self.sid}.txt").write_text("Estação ferroviária histórica", encoding="utf-8")
        self.valid = {"scenes": copy.deepcopy(self.scenes)}

    def response(self, value=None, **kwargs):
        return Response(json.dumps(self.valid if value is None else value), **kwargs)

    def execute(self, responses):
        output = io.StringIO()
        with patch.dict(os.environ, {
            "SHORTAUTOPRO_BASE": str(self.base), "SHORT_ID": self.sid,
            "SHORT_QTD_CENAS": "12", "GEMINI_API_KEY": "test-only",
        }), patch("requests.post", side_effect=responses) as post, patch("time.sleep") as sleep:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                try:
                    runpy.run_path(str(ROOT / "documentary_director.py"), run_name="__main__")
                    self.exit = 0
                except SystemExit as exc:
                    self.exit = exc.code
        self.output = output.getvalue()
        self.post = post
        self.sleep = sleep
        report = self.folder / f"documentary_director_{self.sid}.json"
        self.report = json.loads(report.read_text()) if report.exists() else {}
        self.result = json.loads(self.path.read_text())

    def assert_preserved(self):
        self.assertEqual(self.result, self.original)
        self.assertEqual(self.report["status"], "DEGRADED")
        self.assertTrue(self.report.get("preserved_original_scene_map"))
        self.assertEqual(self.exit, 0)

    def test_success_preserves_narration_timing_and_metadata(self):
        self.execute([self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.report["version"], "3.6")
        self.assertEqual(self.report["attempts"], 1)
        self.assertEqual(self.result["provenance"], "preserve-me")
        self.assertEqual(self.result["scenes"], self.scenes)
        self.assertEqual(json.loads((self.folder / f"scene_map_pre_documentary_{self.sid}.json").read_text()), self.original)

    def test_malformed_json_retries_and_recovers(self):
        self.execute([Response('{"scenes":['), self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.report["attempts"], 2)
        self.assertIn("contrato JSON", self.post.call_args_list[1].kwargs["json"]["contents"][0]["parts"][0]["text"])

    def test_exhaustion_preserves_input_and_records_each_attempt(self):
        self.execute([Response("invalid")] * 3)
        self.assert_preserved()
        self.assertEqual(self.post.call_count, 3)
        self.assertEqual(self.report["attempts"], 3)
        self.assertEqual(len(self.report["attempt_history"]), 3)

    def test_fenced_json_and_quoted_prose(self):
        for prefix, suffix in [('```json\n', '\n```'), ('Resposta "documental":\n', '\nFim.')]:
            with self.subTest(prefix=prefix):
                self.execute([Response(prefix + json.dumps(self.valid) + suffix)])
                self.assertEqual(self.exit, 0)

    def test_split_text_parts_are_joined_without_changing_json_strings(self):
        raw = json.dumps(self.valid)
        cut = raw.index("railway") + 3
        self.execute([Response(parts=[{"text": raw[:cut]}, {"text": raw[cut:]}])])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.result["scenes"], self.scenes)

    def test_thinking_parts_are_not_parsed_as_final_json(self):
        self.execute([Response(parts=[{"text": "internal {reasoning}", "thought": True}, {"text": json.dumps(self.valid)}])])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 1)

    def test_truncation_is_identified_and_increases_output_budget(self):
        self.execute([self.response(finish="MAX_TOKENS"), self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 2)
        self.assertGreaterEqual(self.post.call_count, 2)
        self.assertEqual(self.report["status"], "PASS")

    def test_prompt_block_is_explicit_and_preserves_input(self):
        self.execute([Response(envelope={"promptFeedback": {"blockReason": "SAFETY"}})] * 3)
        self.assert_preserved()
        self.assertIn("SAFETY", self.report["error"])

    def test_candidate_safety_stop_never_applies_even_complete_json(self):
        self.execute([self.response(finish="SAFETY")] * 3)
        self.assert_preserved()

    def test_envelope_failures_retry(self):
        for envelope in ({}, {"candidates": []}, {"candidates": [None]}, {"candidates": [{"content": {"parts": None}}]}, {"candidates": [{"content": {"parts": "wrong"}}]}):
            with self.subTest(envelope=envelope):
                self.execute([Response(envelope=envelope), self.response()])
                self.assertEqual(self.exit, 0)
                self.assertEqual(self.post.call_count, 2)

    def test_invalid_scene_contract_retries(self):
        cases = []
        for field, value in (("scene", True), ("scene", 1.5), ("query", {"bad": "type"}), ("query", "short"), ("must_have", [{"bad": "type"}]), ("visual_mode", "nonsense"), ("shot_type", "nonsense"), ("visual_mode", {}), ("shot_type", [])):
            case = copy.deepcopy(self.valid)
            case["scenes"][0][field] = value
            cases.append(case)
        cases.extend([{"scenes": self.scenes[:-1]}, {"scenes": list(reversed(self.scenes))}, {"scenes": [self.scenes[0]] * 12}])
        for case in cases:
            with self.subTest(case=case["scenes"][0]):
                self.execute([self.response(case), self.response()])
                self.assertEqual(self.exit, 0)
                self.assertEqual(self.post.call_count, 2)

    def test_no_nested_json_salvage_from_truncated_outer_document(self):
        self.execute([Response('{"broken":' + json.dumps(self.valid))] * 3)
        self.assert_preserved()

    def test_network_timeout_retries(self):
        self.execute([requests.Timeout("simulated timeout"), self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 2)

    def test_rate_limit_wait_is_capped(self):
        self.execute([Response(status=429, headers={"Retry-After": "99999"}), self.response()])
        self.assertEqual(self.exit, 0)
        self.assertLessEqual(self.sleep.call_args.args[0], 30)

    def test_transient_server_error_retries(self):
        self.execute([Response(status=503), self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 2)

    def test_auth_failure_does_not_claim_three_attempts(self):
        self.execute([Response(status=401)])
        self.assert_preserved()
        self.assertEqual(self.report["attempts"], 1)
        self.assertEqual(self.post.call_count, 1)
        self.assertNotIn("após 3 tentativas", str(self.exit))

    def test_version_can_be_checked_without_api_or_artifacts(self):
        env = dict(os.environ, SHORTAUTOPRO_BASE=str(self.base / "absent"), GEMINI_API_KEY="")
        proc = subprocess.run([sys.executable, str(ROOT / "documentary_director.py"), "--version"],
                              env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("STABLE 3.6", proc.stdout)

    def test_literal_braces_and_markdown_inside_json_strings_are_preserved(self):
        self.valid["scenes"][0]["query"] = 'archive "railway" station {historic} ```json photograph'
        self.execute([self.response()])
        self.assertEqual(self.exit, 0)
        self.assertEqual(self.result["scenes"][0]["query"], self.valid["scenes"][0]["query"])

    def test_extra_nonobject_scene_is_not_silently_removed(self):
        self.original["scenes"].append(None)
        self.path.write_text(json.dumps(self.original))
        self.execute([])
        self.assertNotEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 0)
        self.assertEqual(self.result, self.original)

    def test_corrupt_original_map_blocks_before_network(self):
        self.original["scenes"][0]["scene"] = True
        self.path.write_text(json.dumps(self.original))
        self.execute([])
        self.assertNotEqual(self.exit, 0)
        self.assertEqual(self.post.call_count, 0)
        self.assertEqual(self.result, self.original)


if __name__ == "__main__":
    unittest.main()
