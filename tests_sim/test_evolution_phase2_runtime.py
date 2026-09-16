import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import client_job_runner as cjr
import profile_runtime as pr
import topic_engine_runtime as ter


ROOT = Path(__file__).resolve().parents[1]


class ProfileRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old_profiles = pr.PROFILES
        pr.PROFILES = self.base / "profiles.json"
        pr.PROFILES.write_text(json.dumps({
            "default": {
                "language": "pt-BR",
                "scene_count": 12,
                "target_duration_seconds": 55,
                "voice": "pt_BR-faber-medium",
                "audio": {"target_lufs": -14, "true_peak_db": -1.5},
                "visual": {"minimum_score": 78},
                "captions": {"max_words_per_event": 7, "max_lines": 2},
            },
            "crime": {
                "scene_count": 14,
                "theme": "casos reais documentados",
                "visual": {"minimum_score": 84},
                "narrative": {"tone": "suspense", "hook_style": "fast", "cta_style": "subtle"},
            },
        }), encoding="utf-8")

    def tearDown(self):
        pr.PROFILES = self.old_profiles
        self.temp.cleanup()

    def test_profile_merges_and_maps_real_runtime_variables(self):
        env = pr.runtime_env("crime")
        self.assertEqual(env["SHORT_QTD_CENAS"], "14")
        self.assertEqual(env["SHORT_TEMA"], "casos reais documentados")
        self.assertEqual(env["PIPER_MODEL"], "pt_BR-faber-medium")
        self.assertEqual(env["SAP_VISUAL_MIN_SCORE"], "84.0")
        self.assertEqual(env["SAP_NARRATIVE_TONE"], "suspense")

    def test_unknown_profile_is_blocked(self):
        with self.assertRaises(SystemExit):
            pr.runtime_env("missing")


class ExactTopicRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = {
            "BASE": ter.BASE,
            "HISTORY": ter.HISTORY,
            "TOPIC_OUT": ter.TOPIC_OUT,
            "VERIFY_OUT": ter.VERIFY_OUT,
            "EXACT": ter.EXACT,
            "ALLOW_REPEAT": ter.ALLOW_REPEAT,
        }
        ter.BASE = self.base
        ter.HISTORY = self.base / "historico_assuntos.json"
        ter.TOPIC_OUT = self.base / "roteiros" / "topic_x.txt"
        ter.VERIFY_OUT = self.base / "roteiros" / "topic_verified_x.json"
        ter.EXACT = "Caso Exemplo"
        ter.ALLOW_REPEAT = False

    def tearDown(self):
        for key, value in self.old.items():
            setattr(ter, key, value)
        self.temp.cleanup()

    def test_exact_topic_keeps_factual_gate(self):
        with patch.object(ter, "wiki_search_client", return_value=[{"title": "Caso Exemplo"}]), \
             patch.object(ter, "wiki_extract_client", return_value="contexto " * 500), \
             patch.object(ter, "validar_identidade", return_value={"valid": True, "score": 0.96, "reason": "match"}):
            code = ter.exact_mode()
        self.assertEqual(code, 0)
        self.assertEqual(ter.TOPIC_OUT.read_text(encoding="utf-8"), "Caso Exemplo")
        report = json.loads(ter.VERIFY_OUT.read_text(encoding="utf-8"))
        self.assertEqual(report["mode"], "exact_verified")
        self.assertTrue(report["selected"]["exact"])

    def test_exact_topic_rejects_unverified_subject(self):
        with patch.object(ter, "wiki_search_client", return_value=[]):
            with self.assertRaises(SystemExit):
                ter.exact_mode()

    def test_exact_topic_blocks_duplicate_by_default(self):
        ter.HISTORY.write_text(json.dumps([{"topic": "Caso Exemplo"}]), encoding="utf-8")
        with self.assertRaises(SystemExit):
            ter.exact_mode()


class ClientRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = {"BASE": cjr.BASE, "JOBS": cjr.JOBS, "PROFILE_RUN": cjr.PROFILE_RUN}
        cjr.BASE = self.base
        cjr.JOBS = self.base / "reports" / "evolution" / "client_jobs"
        cjr.PROFILE_RUN = self.base / "profile_run.sh"
        cjr.PROFILE_RUN.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")

    def tearDown(self):
        for key, value in self.old.items():
            setattr(cjr, key, value)
        self.temp.cleanup()

    def test_dry_run_does_not_start_production(self):
        path = cjr.JOBS / "job1.json"
        path.parent.mkdir(parents=True)
        job = {
            "job_id": "job1", "client": "Cliente", "topic": "Mistérios",
            "topic_mode": "theme", "quantity": 2, "language": "pt-BR", "profile": "default",
        }
        path.write_text(json.dumps(job), encoding="utf-8")
        with patch("client_job_runner.subprocess.run") as mocked:
            code = cjr.run_job(path, job, execute=False)
        self.assertEqual(code, 0)
        mocked.assert_not_called()
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "QUEUED")
        self.assertEqual(len(saved["items"]), 2)

    def test_passed_item_with_valid_output_is_resumable(self):
        path = cjr.JOBS / "job2.json"
        path.parent.mkdir(parents=True)
        sid = "client_job2_001"
        video = self.base / "videos" / f"short_v6_{sid}.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video")
        quality = self.base / "manifests" / f"{sid}_quality.json"
        quality.parent.mkdir(parents=True)
        quality.write_text(json.dumps({"approved": True}), encoding="utf-8")
        job = {
            "job_id": "job2", "client": "Cliente", "topic": "Tema",
            "topic_mode": "theme", "quantity": 1, "language": "pt-BR", "profile": "default",
            "items": [{"index": 1, "short_id": sid, "status": "PASS"}],
        }
        path.write_text(json.dumps(job), encoding="utf-8")
        with patch("client_job_runner.subprocess.run") as mocked:
            code = cjr.run_job(path, job, execute=True)
        self.assertEqual(code, 0)
        mocked.assert_not_called()
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "PASS")


class IntegrationTests(unittest.TestCase):
    def test_main_pipeline_uses_verified_topic_runtime(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('p.run("1 - TOPIC ENGINE", "topic_engine_runtime.py"', text)
        self.assertNotIn('p.run("1 - TOPIC ENGINE", "topic_engine.py"', text)
        self.assertFalse((ROOT / "gerar_short.sh").exists())

    def test_profile_runner_only_eval_trusted_profile_output(self):
        text = (ROOT / "profile_run.sh").read_text(encoding="utf-8")
        self.assertIn('profile_runtime.py', text)
        self.assertIn('--shell', text)
        self.assertIn('eval "$PROFILE_EXPORTS"', text)

    def test_evolution_center_exposes_real_product_flows(self):
        text = (ROOT / "evolution_center.sh").read_text(encoding="utf-8")
        self.assertIn("Gerar Short com perfil / assunto exato", text)
        self.assertIn("Executar ou retomar último job de cliente", text)
        self.assertIn("client_job_create.py", text)
        self.assertIn("client_job_runner.py", text)


if __name__ == "__main__":
    unittest.main()
