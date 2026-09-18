import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GeneralProductionOptimizationTests(unittest.TestCase):
    def test_main_uses_inprocess_evolution_checkpoints(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("import shortautopro_evolution as evo", text)
        self.assertIn("evo.checkpoint(name, status, title, self.sid)", text)
        self.assertIn("evo.finish_production(status, self.sid)", text)
        self.assertNotIn('[sys.executable, str(EVOLUTION), "checkpoint"', text)

    def test_preflight_caches_expensive_code_validation_by_clean_commit(self):
        text = (ROOT / "preflight_check.sh").read_text(encoding="utf-8")
        self.assertIn("preflight_code_cache.txt", text)
        self.assertIn("CODE_CACHE_HIT", text)
        self.assertIn("git -C \"$BASE\" status --porcelain", text)
        self.assertIn("validação de sintaxe/imports em cache", text)

    def test_health_reuses_preflight_commit_cache(self):
        text = (ROOT / "health_check.sh").read_text(encoding="utf-8")
        self.assertIn("preflight_code_cache.txt", text)
        self.assertIn("CODE_CACHE_HIT", text)
        self.assertIn("imports runtime críticos 3.0.2 (cache commit", text)

    def test_professional_quality_reuses_fresh_audio_measurement(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn("AUDIO_REPORT", text)
        self.assertIn("def cached_loudness(", text)
        self.assertIn("PRO_QUALITY_AUDIO_MEASURE=CACHE_HIT", text)
        self.assertIn("PRO_QUALITY_AUDIO_MEASURE=FFMPEG", text)
        self.assertIn("VIDEO.stat().st_mtime > AUDIO_REPORT.stat().st_mtime", text)

    def test_professional_quality_reuses_fresh_manifest_probe(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn("PRODUCTION_MANIFEST", text)
        self.assertIn("def cached_technical_score(", text)
        self.assertIn("PRO_QUALITY_TECHNICAL=MANIFEST_CACHE_HIT", text)
        self.assertIn("PRO_QUALITY_TECHNICAL=FFPROBE", text)
        self.assertIn("VIDEO.stat().st_mtime > PRODUCTION_MANIFEST.stat().st_mtime", text)

    def test_quality_fallbacks_remain_available(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn("def technical_score()", text)
        self.assertIn("def measure_loudness(", text)
        self.assertIn("loudness = measure_loudness(target_lufs, target_tp)", text)

    def test_audio_finalizer_reuses_measurement_when_file_is_unchanged(self):
        text = (ROOT / "audio_finalizer.py").read_text(encoding="utf-8")
        self.assertIn('measurement_source="unchanged_reuse"', text)
        self.assertIn('after=before', text)
        self.assertIn('after=measure(VIDEO)', text)
        self.assertIn('"remastered":need', text)

    def test_assembler_duration_probe_is_cached_by_file_identity(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertIn("_DURATION_CACHE", text)
        self.assertIn("st_mtime_ns", text)
        self.assertIn("st_size", text)
        self.assertIn("_DURATION_CACHE.get(key)", text)

    def test_resume_boundary_reuses_single_render_probe(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("render_valid = render_ok(sid)", text)
        self.assertIn("final_ok(sid, render_valid)", text)
        self.assertIn("if render_valid:", text)

    def test_no_certified_visual_selector_relaxation(self):
        midia = (ROOT / "midia.py").read_text(encoding="utf-8")
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertNotIn("SAP_STRICT_MUST_GUARD=DISABLED", midia)
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)


if __name__ == "__main__":
    unittest.main()
