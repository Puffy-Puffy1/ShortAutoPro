import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import shortautopro_evolution as evo


class EvolutionSandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = {
            "BASE": evo.BASE,
            "STATE_DIR": evo.STATE_DIR,
            "REPORT_DIR": evo.REPORT_DIR,
            "METRICS_DIR": evo.METRICS_DIR,
            "PROFILES_FILE": evo.PROFILES_FILE,
        }
        evo.BASE = self.base
        evo.STATE_DIR = self.base / ".sap_state"
        evo.REPORT_DIR = self.base / "reports" / "evolution"
        evo.METRICS_DIR = self.base / "metrics"
        evo.PROFILES_FILE = self.base / "config" / "channel_profiles.json"
        evo.PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
        evo.PROFILES_FILE.write_text(json.dumps({
            "default": {
                "captions": {"max_words_per_event": 7, "max_lines": 2},
                "audio": {"target_lufs": -14, "true_peak_db": -1.5, "music_ducking_db": -12},
            }
        }), encoding="utf-8")

    def tearDown(self):
        for key, value in self.old.items():
            setattr(evo, key, value)
        self.temp.cleanup()

    def write_json(self, relative, payload):
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class CheckpointTests(EvolutionSandbox):
    def test_checkpoint_and_resume_plan(self):
        with patch("shortautopro_evolution.time.time", side_effect=[100.0, 103.5]):
            evo.checkpoint("roteiro.py", "start", "ROTEIRO", "s1")
            result = evo.checkpoint("roteiro.py", "pass", "ROTEIRO", "s1")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["elapsed_seconds"], 3.5)
        plan = evo.resume_plan("s1")
        self.assertEqual(plan["passed_count"], 1)
        self.assertIsNone(plan["resume_candidate"])

    def test_failed_stage_is_resume_candidate(self):
        evo.checkpoint("midia.py", "start", "MIDIA", "s2")
        evo.checkpoint("midia.py", "fail", "MIDIA", "s2")
        plan = evo.resume_plan("s2")
        self.assertEqual(plan["resume_candidate"], "midia.py")


class VisualAuditTests(EvolutionSandbox):
    def test_strong_twelve_scene_project_scores_high(self):
        sid = "demo"
        # Use cenas semanticamente distintas de verdade. O fixture anterior
        # repetia "unique subject city" em todas as queries e corretamente
        # acionava o guard de repetição (Jaccard >= 0.55).
        queries = [
            "steam locomotive station",
            "mountain rescue helicopter",
            "courtroom evidence document",
            "coastal lighthouse storm",
            "factory assembly workers",
            "historic atlas border",
            "hospital corridor doctor",
            "airport runway aircraft",
            "museum artifact display",
            "newspaper archive headline",
            "forest search volunteers",
            "memorial candles crowd",
        ]
        scenes = []
        for index, query in enumerate(queries, start=1):
            scenes.append({
                "scene": index,
                "query": query,
                "must_have": [query.split()[0]],
                "visual_mode": ["archive", "map", "document", "location"][index % 4],
            })
        self.write_json(f"roteiros/scene_map_{sid}.json", {"scenes": scenes})
        self.write_json(f"roteiros/supervisor_{sid}.json", {"status": "PASS"})
        media = self.base / "imagens" / f"short_{sid}"
        media.mkdir(parents=True)
        for index in range(1, 13):
            (media / f"scene_{index}.jpg").write_bytes(b"fake")
        result = evo.visual_audit(sid)
        self.assertGreaterEqual(result["score"], 90)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["details"]["repeated_adjacent_queries"], 0)
        self.assertEqual(result["details"]["physical_media_count"], 12)

    def test_repetition_lowers_diversity(self):
        sid = "repeat"
        scenes = [
            {"scene": i, "query": "same police building", "must_have": ["police"], "visual_mode": "archive"}
            for i in range(1, 13)
        ]
        self.write_json(f"roteiros/scene_map_{sid}.json", {"scenes": scenes})
        self.write_json(f"roteiros/supervisor_{sid}.json", {"status": "WARNING"})
        result = evo.visual_audit(sid)
        self.assertGreater(result["details"]["repeated_adjacent_queries"], 0)
        self.assertLess(result["components"]["diversity_continuity"], 20)


class CaptionTests(EvolutionSandbox):
    def test_ass_caption_policy_detects_long_event(self):
        sid = "captions"
        temp_dir = self.base / "temp"
        temp_dir.mkdir(parents=True)
        ass = """[Events]\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,curta legenda\nDialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,uma legenda com palavras demais para caber muito bem aqui agora\n"""
        (temp_dir / f"legenda_{sid}.ass").write_text(ass, encoding="utf-8")
        result = evo.caption_audit(sid)
        self.assertEqual(result["events"], 2)
        self.assertEqual(result["violations"]["too_many_words"], 1)
        self.assertLess(result["score"], 100)


class QualityScoreTests(EvolutionSandbox):
    def test_central_quality_weighting(self):
        sid = "quality"
        self.write_json(f"manifests/{sid}_quality.json", {"approved": True, "total_score": 90})
        fake_visual = {"score": 92}
        fake_captions = {"score": 88}
        fake_technical = {"score": 100, "errors": [], "audio_streams": 1}
        with patch.object(evo, "visual_audit", return_value=fake_visual), \
             patch.object(evo, "caption_audit", return_value=fake_captions), \
             patch.object(evo, "latest_video", return_value=self.base / "videos" / "x.mp4"), \
             patch.object(evo, "ffprobe_video", return_value=fake_technical):
            result = evo.quality_score(sid)
        expected = 92 * 0.35 + 88 * 0.15 + 100 * 0.15 + 100 * 0.20 + 90 * 0.15
        self.assertAlmostEqual(result["total_score"], round(expected, 1))
        self.assertEqual(result["status"], "PASS")

    def test_missing_video_is_block(self):
        sid = "bad"
        self.write_json(f"manifests/{sid}_quality.json", {"approved": True, "total_score": 90})
        with patch.object(evo, "visual_audit", return_value={"score": 90}), \
             patch.object(evo, "caption_audit", return_value={"score": 90}), \
             patch.object(evo, "latest_video", return_value=None):
            result = evo.quality_score(sid)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("video_missing", result["critical"])


class InventoryTests(EvolutionSandbox):
    def test_inventory_marks_pipeline_and_dependencies(self):
        (self.base / "gerar_short.sh").write_text('python "alpha.py"\n', encoding="utf-8")
        (self.base / "control_center.sh").write_text("echo menu\n", encoding="utf-8")
        (self.base / "alpha.py").write_text("import beta\n", encoding="utf-8")
        (self.base / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.base / "mystery.py").write_text("VALUE = 2\n", encoding="utf-8")
        report = evo.build_inventory()
        categories = {item["path"]: item["category"] for item in report["files"]}
        self.assertEqual(categories["alpha.py"], "PRODUCAO")
        self.assertEqual(categories["beta.py"], "DEPENDENCIA")
        self.assertEqual(categories["mystery.py"], "NAO_IDENTIFICADO")


class ProductFoundationTests(EvolutionSandbox):
    def test_longform_plan_has_resumeable_chapters(self):
        plan = evo.longform_plan("Tema de teste", 15, 5)
        self.assertEqual(len(plan["chapters"]), 5)
        self.assertTrue(plan["continuity"]["resume_by_chapter"])
        self.assertEqual(plan["chapters"][-1]["objective"], "conclusion")

    def test_client_job_has_complete_deliverables(self):
        job = evo.client_job("Cliente X", "Tema", 3, "pt-BR", "default")
        self.assertEqual(job["quantity"], 3)
        self.assertIn("quality_report", job["deliverables"])
        self.assertEqual(job["status"], "QUEUED")


if __name__ == "__main__":
    unittest.main()
