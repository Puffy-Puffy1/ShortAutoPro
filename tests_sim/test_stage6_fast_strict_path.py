import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Stage6FastStrictPathTests(unittest.TestCase):
    def test_initial_scene_uses_canonical_parallel_acquisition(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        marker = "SAP_MEDIA_INITIAL_ACQUISITION=CANONICAL_PARALLEL"
        self.assertIn(marker, text)
        block_start = text.index("# Single canonical acquisition path.")
        block_end = text.index("# MAIN WIKIMEDIA EVIDENCE 5.2", block_start)
        block = text[block_start:block_end]
        self.assertIn("buscar_todos_candidatos(", block)
        self.assertNotIn("pexels_video(", block)
        self.assertNotIn("pixabay_video(", block)
        self.assertNotIn("pexels_foto(", block)
        self.assertNotIn("pixabay_foto(", block)

    def test_explicit_must_uses_bounded_simplified_retries(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MUST_SIMPLIFIED_RETRIES=ENABLED", text)
        retry_start = text.index("# RETRY COM QUERY SIMPLIFICADA")
        late_start = text.index("# EXPLICIT-MUST LATE STRICT RECOVERY", retry_start)
        block = text[retry_start:late_start]
        self.assertIn("alternativas = simplificar_busca(", block)
        self.assertIn("_alt_seen", block)
        self.assertIn("_alt_clean", block)
        self.assertNotIn("alternativas = []", block)
        self.assertIn("_sap_call_original", block)
        self.assertIn("SAP_MEDIA_SIMPLIFIED_RETRY_MAX", block)
        self.assertIn("busca_alt,", block)
        self.assertIn("must_have,", block)
        self.assertIn("one_shot=", block)

    def test_canonical_recovery_unwraps_legacy_vse42_search_rescue(self):
        text = (ROOT / "media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "2.0"', text)
        self.assertIn("_sap_query_expansion_original", text)
        self.assertIn("_sap_vse42_original", text)
        self.assertIn("__wrapped__", text)
        self.assertIn("SAP_MEDIA_RESCUE_NESTING=DISABLED", text)
        self.assertIn("provider_search(", text)

    def test_recovery_remains_bounded_and_cached(self):
        text = (ROOT / "media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MUST_RESCUE_MAX_QUERIES", text)
        self.assertIn("return out[:8]", text)
        self.assertIn("SAP_MUST_RESCUE_CACHE=HIT", text)
        self.assertIn("SAP_MEDIA_ACQUISITION_CACHE=HIT", text)

    def test_provider_round_uses_shared_deadline_without_order_loss(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_done, _not_done = wait(", text)
        self.assertIn("timeout=_PROVIDER_RESULT_TIMEOUT", text)
        self.assertIn("if future not in _done:", text)
        self.assertIn("round_deadline=", text)
        self.assertIn('SAP_MEDIA_PROVIDER_RESULT_TIMEOUT", "6"', text)
        self.assertNotIn("_provider_remaining", text)

    def test_recovery_exposes_one_shot_and_mobile_budget(self):
        text = (ROOT / "media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn("_sap_call_original = call_original", text)
        self.assertIn('SAP_MUST_RESCUE_MAX_QUERIES", "2"', text)
        self.assertIn('SAP_STOCK_RESCUE_MAX_QUERIES", "4"', text)

    def test_strict_must_still_fail_closed(self):
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)
        self.assertIn("hits >= total", strict)

    def test_visual_selection_engine_is_untouched_by_speed_path(self):
        midia = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertNotIn("SAP_STRICT_MUST_GUARD=DISABLED", midia)


if __name__ == "__main__":
    unittest.main()
