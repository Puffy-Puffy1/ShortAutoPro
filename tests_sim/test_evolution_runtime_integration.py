import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EvolutionRuntimeIntegrationTests(unittest.TestCase):
    def test_generation_pipeline_has_evolution_observability(self):
        text = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")
        self.assertIn('shortautopro_evolution.py" visual-audit', text)
        self.assertIn('shortautopro_evolution.py" caption-audit', text)
        self.assertIn('shortautopro_evolution.py" e2e', text)
        self.assertIn('shortautopro_evolution.py" quality-score', text)
        self.assertIn('evolution_checkpoint "$ARQUIVO" "start"', text)
        self.assertIn('evolution_finish "SUCCESS"', text)

    def test_quality_enforcement_is_safe_rollout(self):
        text = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")
        self.assertIn('SAP_EVOLUTION_ENFORCE:-0', text)
        self.assertIn('quality-score --enforce', text)

    def test_audio_uses_loudness_mastering(self):
        text = (ROOT / "audio.py").read_text(encoding="utf-8")
        self.assertIn('SAP_AUDIO_TARGET_LUFS', text)
        self.assertIn('SAP_AUDIO_TRUE_PEAK_DB', text)
        self.assertIn('loudnorm=I=', text)
        self.assertIn('"-b:a", "160k"', text)

    def test_caption_audit_mirror_is_preserved(self):
        text = (ROOT / "legenda_dinamica.py").read_text(encoding="utf-8")
        self.assertIn("ASS_AUDIT", text)
        self.assertIn("shutil.copyfile(ASS_FINAL, ASS_AUDIT)", text)

    def test_profiles_have_expected_free_presets(self):
        profiles = json.loads((ROOT / "config" / "channel_profiles.json").read_text(encoding="utf-8"))
        for name in ("default", "true_crime", "cinepulsar", "psicotoon"):
            self.assertIn(name, profiles)
        self.assertNotIn("english", profiles)
        self.assertEqual(profiles["default"]["scene_count"], 12)
        self.assertTrue(profiles["default"]["visual"]["retry_weak_scenes"])
        self.assertTrue(all(str(data.get("language", "pt-BR")).lower().startswith("pt") for data in profiles.values()))

    def test_final_summary_uses_real_quality_reports(self):
        text = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")
        self.assertIn("QUALITY_REPORT=", text)
        self.assertIn("EVOLUTION_REPORT", text)
        self.assertIn("REVIEW (EVOLUTION", text)
        self.assertNotIn('echo "QUALITY: PASS"', text)


if __name__ == "__main__":
    unittest.main()
