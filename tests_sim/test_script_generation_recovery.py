import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import script_runtime


class ScriptGenerationRecoveryTests(unittest.TestCase):
    def test_main_routes_script_stage_through_runtime(self):
        text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('"script_runtime.py"', text)
        self.assertNotIn('p.run("2 - ROTEIRO + PESQUISA FACTUAL", "roteiro.py"', text)

    def test_roteiro_retries_http_200_without_candidates(self):
        roteiro = Path("roteiro.py").read_text(encoding="utf-8")
        runtime = Path("gemini_runtime.py").read_text(encoding="utf-8")
        self.assertIn("GeminiGenerationUnavailable = GeminiInvalidResponse", roteiro)
        self.assertIn("generate_text(", roteiro)
        self.assertIn("no_usable_candidates", runtime)
        self.assertIn("if attempt < attempts:", runtime)

    def test_roteiro_prompt_requires_non_graphic_documentary_treatment(self):
        text = Path("roteiro.py").read_text(encoding="utf-8")
        self.assertIn("trate de forma documental e não gráfica", text)
        self.assertIn("Não descreva violência sexual, tortura", text)

    def test_runtime_rejects_only_topic_incompatible_code(self):
        text = Path("script_runtime.py").read_text(encoding="utf-8")
        self.assertIn("TOPIC_INCOMPATIBLE = 24", text)
        self.assertIn("if code != TOPIC_INCOMPATIBLE", text)
        self.assertIn("SCRIPT_RUNTIME=HARD_FAIL", text)
        self.assertIn("SCRIPT_RUNTIME=RESELECT_TOPIC", text)

    def test_runtime_persists_rejected_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir()
            rejected = roteiros / "topic_rejected_test.json"
            with mock.patch.object(script_runtime, "REJECTED_FILE", rejected), \
                 mock.patch.object(script_runtime, "SID", "test"):
                script_runtime.reject_topic("Tema A", "gemini_no_usable_candidate")
                script_runtime.reject_topic("Tema A", "gemini_no_usable_candidate")
                data = json.loads(rejected.read_text(encoding="utf-8"))
            self.assertEqual(len(data["topics"]), 1)
            self.assertEqual(data["topics"][0]["topic"], "Tema A")

    def test_topic_engine_honors_runtime_rejections(self):
        text = Path("topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("REJEITADOS_RUNTIME", text)
        self.assertIn("runtime_script_incompatible", text)
        self.assertIn("runtime_rejected_topics", text)
        self.assertIn("rejeitados_runtime_norm", text)

    def test_topic_engine_prompt_prefers_generation_safe_cases(self):
        text = Path("topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("forma documental e não gráfica", text)
        self.assertIn("violência sexual contra menores", text)

    def test_preflight_and_health_require_script_runtime(self):
        self.assertIn("script_runtime.py", Path("preflight_check.sh").read_text(encoding="utf-8"))
        self.assertIn("script_runtime.py", Path("health_check.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
