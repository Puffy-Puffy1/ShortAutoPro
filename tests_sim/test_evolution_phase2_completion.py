import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import longform_runtime as lfr
import profile_runtime as pr
import resume_short_runtime as rsr
import shortautopro_evolution as evo


ROOT = Path(__file__).resolve().parents[1]


class LongformRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old_profiles = pr.PROFILES
        pr.PROFILES = self.base / "profiles.json"
        pr.PROFILES.write_text(json.dumps({
            "default": {
                "language": "pt-BR",
                "voice": "pt_BR-faber-medium",
                "audio": {"target_lufs": -14, "true_peak_db": -1.5},
                "captions": {"max_words_per_event": 7},
            },
            "true_crime": {"language": "pt-BR"},
            "english_future": {"language": "en-US", "voice": "en_US-test"},
        }), encoding="utf-8")

    def tearDown(self):
        pr.PROFILES = self.old_profiles
        self.temp.cleanup()

    def test_longform_rejects_non_portuguese_profile(self):
        with self.assertRaises(SystemExit):
            lfr.safe_profile("english_future")

    def test_outline_contract_requires_exact_chapter_count(self):
        payload = {
            "chapters": [
                {"title": "Início", "objective": "contexto"},
                {"title": "Busca", "objective": "desenvolvimento"},
                {"title": "Desfecho", "objective": "conclusão"},
            ]
        }
        with patch.object(lfr, "gemini", return_value=json.dumps(payload)):
            outline = lfr.build_outline("Caso Teste", "fonte factual " * 200, 3, 10)
        self.assertEqual(len(outline), 3)
        self.assertEqual(outline[0]["chapter"], 1)
        self.assertEqual(outline[-1]["title"], "Desfecho")

    def test_chapter_script_enforces_narration_and_visual_queries(self):
        narration = " ".join(f"palavra{i}" for i in range(220))
        payload = {
            "narration": narration,
            "summary": "Resumo factual curto.",
            "visual_queries": [f"historical scene {i}" for i in range(6)],
        }
        chapter = {"chapter": 1, "title": "Contexto", "objective": "explicar contexto"}
        with patch.object(lfr, "gemini", return_value=json.dumps(payload)):
            result = lfr.chapter_script("Caso", "fonte " * 300, chapter, 220, [])
        self.assertEqual(result["word_count"], 220)
        self.assertEqual(len(result["visual_queries"]), 6)

    def test_longform_ass_has_readable_events(self):
        path = self.base / "captions.ass"
        narration = "um dois três quatro cinco seis sete oito nove dez onze doze"
        lfr.make_ass(path, narration, 12.0, 6)
        text = path.read_text(encoding="utf-8")
        self.assertIn("PlayResX: 1920", text)
        self.assertIn("PlayResY: 1080", text)
        self.assertEqual(text.count("Dialogue:"), 2)

    def test_credits_keep_source_license_and_author(self):
        text = lfr.credits_text([{
            "title": "File:Example.jpg",
            "artist": "Autor",
            "license": "CC BY-SA 4.0",
            "license_url": "https://example/license",
            "description_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        }])
        self.assertIn("Autor", text)
        self.assertIn("CC BY-SA 4.0", text)
        self.assertIn("commons.wikimedia.org", text.lower())


class ResumeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = {
            "rsr_base": rsr.BASE,
            "evo_base": evo.BASE,
            "evo_state": evo.STATE_DIR,
        }
        rsr.BASE = self.base
        evo.BASE = self.base
        evo.STATE_DIR = self.base / ".sap_state"
        self.sid = "resume_test"
        os.environ["SHORT_QTD_CENAS"] = "12"

        roteiros = self.base / "roteiros"
        roteiros.mkdir(parents=True)
        (roteiros / f"scene_map_{self.sid}.json").write_text(
            json.dumps({"scenes": [{"scene": i} for i in range(1, 13)]}), encoding="utf-8"
        )
        (roteiros / f"supervisor_{self.sid}.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        (roteiros / f"media_quality_{self.sid}.json").write_text(
            json.dumps({"status": "PASS", "critical": []}), encoding="utf-8"
        )
        # V2 checkpoint artifacts: deterministic render plan + immutable media manifest.
        (roteiros / f"pro_edit_plan_{self.sid}.json").write_text(json.dumps({
            "schema_version": "render-plan-v2",
            "short_id": self.sid,
            "scenes": [{"scene": i} for i in range(1, 13)],
        }), encoding="utf-8")
        manifest_dir = self.base / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        media = self.base / "imagens" / f"short_{self.sid}"
        media.mkdir(parents=True)
        media_rows = []
        for i in range(1, 13):
            asset_path = media / f"scene_{i:02d}.jpg"
            asset_path.write_bytes(b"asset-" + bytes([i]) * 2000)
            digest = __import__("hashlib").sha256(asset_path.read_bytes()).hexdigest()
            media_rows.append({
                "scene_id": str(i),
                "scene_number": i,
                "asset": {
                    "validated": True,
                    "checksum_sha256": digest,
                    "path": str(asset_path),
                },
            })
        manifest = {
            "schema_version": "media-manifest-v2",
            "engine_version": "2.0.1",
            "short_id": self.sid,
            "immutable": True,
            "scene_count": 12,
            "scenes": media_rows,
        }
        import media_engine_v2
        manifest["integrity_sha256"] = media_engine_v2._manifest_integrity(manifest)
        (manifest_dir / f"media_{self.sid}.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        planning = {
            f"retention_{self.sid}.json": {"status": "PASS", "retention_score": 95, "notes": ["validated"]},
            f"sound_design_{self.sid}.json": {"status": "PASS", "scenes": [{"scene": 1, "mood": "tension"}]},
            f"multi_asset_{self.sid}.json": {"status": "PASS", "scenes": [{"scene": 1, "assets": ["scene_01.jpg"]}]},
            f"visual_score_{self.sid}.json": {"status": "PASS", "visual_score": 92, "dimensions": {"relevance": 94}},
            f"visual_continuity_{self.sid}.json": {"status": "PASS", "visual_continuity_score": 91, "pairs": 11},
        }
        for name, payload in planning.items():
            (roteiros / name).write_text(json.dumps(payload), encoding="utf-8")

        state = self.base / ".sap_state" / f"{self.sid}.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "short_id": self.sid,
            "stages": {"production_supervisor.py": {"status": "PASS"}},
        }), encoding="utf-8")

        # Media files are created above as part of the immutable V2 manifest fixture.

    def tearDown(self):
        rsr.BASE = self.old["rsr_base"]
        evo.BASE = self.old["evo_base"]
        evo.STATE_DIR = self.old["evo_state"]
        os.environ.pop("SHORT_QTD_CENAS", None)
        self.temp.cleanup()

    def test_resume_advances_only_when_artifacts_exist(self):
        self.assertEqual(rsr.boundary(self.sid), "post_planning")

        audio = self.base / "audios" / f"short_{self.sid}.mp3"
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b"a" * 6000)
        self.assertEqual(rsr.boundary(self.sid), "post_audio")

        ass = self.base / "videos" / f"short_{self.sid}.ass"
        ass.parent.mkdir(parents=True)
        ass.write_text("[Events]\n" + ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,teste\n" * 5), encoding="utf-8")
        self.assertEqual(rsr.boundary(self.sid), "post_captions")

        assembly = self.base / "temp" / self.sid / "video_sem_audio.mp4"
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"v" * 120000)
        self.assertEqual(rsr.boundary(self.sid), "post_assembly")

    def test_resume_falls_back_to_full_when_supervisor_proof_missing(self):
        (self.base / "roteiros" / f"supervisor_{self.sid}.json").unlink()
        self.assertEqual(rsr.boundary(self.sid), "full")

    def test_resume_falls_back_to_full_when_media_gate_blocked(self):
        quality = self.base / "roteiros" / f"media_quality_{self.sid}.json"
        quality.write_text(json.dumps({
            "status": "BLOCK",
            "critical": ["very_low_resolution:scene_09.jpg"],
        }), encoding="utf-8")
        self.assertEqual(rsr.boundary(self.sid), "full")

    def test_resume_falls_back_to_full_without_v2_manifest(self):
        (self.base / "manifests" / f"media_{self.sid}.json").unlink()
        self.assertEqual(rsr.boundary(self.sid), "full")

    def test_render_boundary_can_skip_to_final_gates(self):
        with patch.object(rsr, "final_ok", return_value=False), patch.object(rsr, "render_ok", return_value=True):
            self.assertEqual(rsr.boundary(self.sid), "post_render")


class CompletionIntegrationTests(unittest.TestCase):
    def test_english_profile_is_not_operational(self):
        profiles = json.loads((ROOT / "config" / "channel_profiles.json").read_text(encoding="utf-8"))
        self.assertNotIn("english", profiles)
        self.assertTrue(all(str(x.get("language", "pt-BR")).lower().startswith("pt") for x in profiles.values()))

    def test_evolution_center_exposes_resume_and_real_longform(self):
        text = (ROOT / "evolution_center.sh").read_text(encoding="utf-8")
        self.assertIn("Gerar vídeo longo", text)
        self.assertIn("Retomar Short interrompido com checkpoint seguro", text)
        self.assertIn("Retomar último vídeo longo", text)
        self.assertIn("longform_runtime.py", text)
        self.assertIn("resume_short.sh", text)

    def test_longform_runtime_is_separate_from_short_constraints(self):
        text = (ROOT / "longform_runtime.py").read_text(encoding="utf-8")
        self.assertIn("1920:1080", text)
        self.assertIn("Wikimedia Commons", text)
        self.assertIn("resume", text)
        self.assertNotIn("105 e 125", text)

    def test_longform_runtime_outputs_are_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("longform/", text)
        self.assertIn("reports/evolution/", text)

    def test_safe_resume_never_claims_legacy_partial_skip(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn('return "full"', text)
        self.assertIn("consolidation_plan_ok", text)
        self.assertIn("PROFESSIONAL_CANONICAL", text)
        self.assertIn("supervisor_ok", text)
        self.assertNotIn("SAP_PRO_EDIT", text)


if __name__ == "__main__":
    unittest.main()
