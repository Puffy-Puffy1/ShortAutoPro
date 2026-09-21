import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaRootCauseRegressionTests(unittest.TestCase):
    def test_provider_executor_is_per_acquisition(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertNotIn("_PROVIDER_EXECUTOR = ThreadPoolExecutor", text)
        self.assertIn("_executor = ThreadPoolExecutor(", text)
        self.assertIn("cancel_futures=True", text)

    def test_parallel_deadline_collects_completed_futures_without_order_loss(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("from concurrent.futures import ThreadPoolExecutor, wait", text)
        self.assertIn("_done, _not_done = wait(", text)
        self.assertIn("if future not in _done:", text)
        self.assertIn("future.result()", text)
        self.assertNotIn("timeout=_provider_remaining", text)

    def test_local_fallback_commits_only_after_successful_copy(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        start = text.index("# FALLBACK LOCAL FINAL")
        end = text.index("# EMERGENCY EDITORIAL COMPLETION", start)
        block = text[start:end]
        self.assertEqual(block.count("_vse42_commit_safe(escolhido)"), 1)
        self.assertIn("if sucesso:\n                _vse42_cleanup_scene_sibling(destino)", block)

    def test_unconfigured_stock_providers_are_not_enqueued(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("if USAR_PEXELS and PEXELS_KEY:", text)
        self.assertIn("if USAR_PIXABAY and PIXABAY_KEY:", text)
        self.assertIn("if USAR_COVERR and COVERR_KEY:", text)

    def test_rescue_skips_provider_stall(self):
        text = (ROOT / "media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn("INITIAL_PROVIDER_STALL", text)
        self.assertIn("initial_elapsed", text)
        self.assertIn('VERSION = "2.0"', text)

    def test_editorial_fallback_self_checks_duplicates(self):
        text = (ROOT / "media_emergency_fallback.py").read_text(encoding="utf-8")
        self.assertIn("NEAR_DUPLICATE_THRESHOLD = 0.985", text)
        self.assertIn("def _conflict(", text)
        self.assertIn("SAP_MEDIA_EDITORIAL_VARIANT_REJECTED", text)
        self.assertIn("editorial_scene_numbers", text)
        self.assertNotIn("scene_number) % 5", text)

    def test_editorial_outputs_are_not_reused_as_primary_sources(self):
        text = (ROOT / "media_emergency_fallback.py").read_text(encoding="utf-8")
        self.assertIn("or number in editorial", text)
        self.assertIn('INDEX_NAME = ".editorial_reuse_index.json"', text)

    def test_editorial_semantic_trust_is_explicit(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('trust = "EDITORIAL_NON_EVIDENTIARY"', text)

    def test_media_gate_reports_editorial_reuse(self):
        text = (ROOT / "media_master_gate.py").read_text(encoding="utf-8")
        self.assertIn('"editorial_reuse_count"', text)
        self.assertIn("editorial_reuse_scenes=", text)


if __name__ == "__main__":
    unittest.main()
