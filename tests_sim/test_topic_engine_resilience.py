import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TopicEngineResilienceTests(unittest.TestCase):
    def test_model_chain_rotates_after_transient_capacity_errors(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("MODEL_CHAIN", text)
        self.assertIn('"gemini-3.1-flash-lite"', text)
        self.assertIn('"gemini-3.5-flash"', text)
        self.assertIn("TOPIC_ENGINE_TRANSIENT=", text)
        self.assertIn("action=MODEL_FAILOVER", text)

    def test_timeout_is_bounded_for_mobile_runtime(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        self.assertIn(
            'GEMINI_TIMEOUT = env_float("SAP_GEMINI_TIMEOUT", 28.0, 8.0, 60.0)',
            text,
        )
        self.assertNotIn('SAP_GEMINI_TIMEOUT", "75"', text)

    def test_verified_non_llm_fallback_exists(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("def escolher_fallback_sem_llm()", text)
        self.assertIn("TOPIC_ENGINE_FALLBACK=VERIFIED_RESERVE", text)
        self.assertIn("TOPIC_ENGINE_FALLBACK=LOCAL_WIKIPEDIA_DISCOVERY", text)
        self.assertIn("local_wikipedia_verified", text)

    def test_missing_api_key_no_longer_blocks_pipeline(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("GEMINI_API_KEY ausente; usando recuperação verificada", text)
        self.assertNotIn('sys.exit("ERRO: GEMINI_API_KEY não configurada.")', text)

    def test_degraded_mode_exits_success_after_writing_artifacts(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        self.assertIn("TOPIC ENGINE DEGRADED MODE: OK", text)
        self.assertIn('"topic_engine_degraded": True', text)
        self.assertIn("raise SystemExit(0)", text)

    def test_topic_reserve_honors_runtime_base(self):
        text = (ROOT / "topic_reserve.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")', text)


if __name__ == "__main__":
    unittest.main()
