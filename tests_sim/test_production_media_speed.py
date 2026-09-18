import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProductionMediaSpeedTests(unittest.TestCase):
    def test_provider_searches_are_parallel_by_default(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("from concurrent.futures import ThreadPoolExecutor", text)
        self.assertIn("SAP_MEDIA_PARALLEL_PROVIDERS", text)
        self.assertIn('"1"', text)
        self.assertIn("SAP_MEDIA_PROVIDER_MODE=PARALLEL", text)

    def test_parallel_search_preserves_canonical_result_order(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        order_block_start = text.index("# Preserva a ordem canônica anterior:")
        order_block_end = text.index("return todos", order_block_start)
        block = text[order_block_start:order_block_end]
        expected = [
            '"pexels_video"',
            '"pixabay_video"',
            '"coverr_video"',
            '"pexels_foto"',
            '"pixabay_foto"',
        ]
        positions = [block.index(item) for item in expected]
        self.assertEqual(positions, sorted(positions))

    def test_parallel_failure_falls_back_without_disabling_validation(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_PARALLEL=FAIL_OPEN", text)
        self.assertIn("SAP_MEDIA_PROVIDER_MODE=SEQUENTIAL", text)
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)

    def test_provider_worker_count_is_bounded(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_WORKERS", text)
        self.assertIn("min(", text)
        self.assertIn("max_workers", text)

    def test_inter_scene_delay_is_small_and_configurable(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_SCENE_DELAY", text)
        self.assertIn('"0.05"', text)
        self.assertNotIn("time.sleep(\n        0.20\n    )", text)

    def test_certified_visual_selector_is_not_imported_or_rewritten(self):
        changed_layer = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertNotIn("SAP_STRICT_MUST_GUARD=DISABLED", changed_layer)


if __name__ == "__main__":
    unittest.main()
