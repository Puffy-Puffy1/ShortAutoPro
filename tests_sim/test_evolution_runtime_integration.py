import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EvolutionRuntimeIntegrationTests(unittest.TestCase):
    def test_generation_pipeline_has_evolution_observability(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"shortautopro_evolution.py", "caption-audit"', text)
        self.assertIn('"shortautopro_evolution.py", "caption-audit"', text)
        self.assertIn('"shortautopro_evolution.py", "e2e"', text)
        self.assertIn('evo_args = ["quality-score"]', text)
        self.assertIn("self.checkpoint(file, \"start\", title)", text)
        self.assertIn('p.finish("SUCCESS")', text)

    def test_quality_enforcement_is_safe_rollout(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('SAP_EVOLUTION_ENFORCE", "0"', text)
        self.assertIn('["--enforce"]', text)
        self.assertIn('SAP_RELEASE_ENFORCE", "1"', text)
        self.assertIn('release_gate.py', text)

    def test_audio_uses_loudness_mastering(self):
        text = (ROOT / "audio.py").read_text(encoding="utf-8")
        self.assertIn("SAP_AUDIO_TARGET_LUFS", text)
        self.assertIn("SAP_AUDIO_TRUE_PEAK_DB", text)
        self.assertIn("loudnorm=I=", text)
        self.assertIn("160k", text)
        self.assertIn("atempo", text)

    def test_caption_audit_mirror_is_preserved(self):
        text = (ROOT / "legenda_dinamica.py").read_text(encoding="utf-8")
        self.assertIn("ASS_AUDIT", text)
        self.assertIn("os.replace(audit_tmp, ASS_AUDIT)", text)
        self.assertIn("espelho ASS incompleto", text)

    def test_profiles_have_expected_free_presets(self):
        profiles = json.loads((ROOT / "config" / "channel_profiles.json").read_text(encoding="utf-8"))
        for name in ("default", "true_crime", "cinepulsar", "psicotoon"):
            self.assertIn(name, profiles)
        self.assertNotIn("english", profiles)
        self.assertEqual(profiles["default"]["scene_count"], 12)
        self.assertTrue(profiles["default"]["visual"]["retry_weak_scenes"])
        self.assertTrue(all(str(data.get("language", "pt-BR")).lower().startswith("pt") for data in profiles.values()))

    def test_final_summary_uses_real_release_report(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('release_path = BASE / "manifests" / f"{sid}_release.json"', text)
        self.assertIn("ShortAutoPro Score:", text)
        self.assertIn("Release:", text)
        self.assertNotIn('echo "QUALITY: PASS"', text)


if __name__ == "__main__":
    unittest.main()
