import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import production_profiler


ROOT = Path(__file__).resolve().parents[1]


class ProductionSpeedToolsTests(unittest.TestCase):
    def test_media_uses_persistent_provider_executor(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_PROVIDER_EXECUTOR = ThreadPoolExecutor", text)
        self.assertIn("_PROVIDER_EXECUTOR.submit(", text)
        self.assertNotIn("with ThreadPoolExecutor(", text)

    def test_media_uses_named_persistent_http_sessions(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_HTTP_SESSIONS", text)
        self.assertIn("_sap_http_session", text)
        for name in (
            "download",
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        ):
            self.assertIn(f'_sap_http_session("{name}")', text)

    def test_video_provider_variants_are_compacted(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("melhor_variante = None"), 2)
        self.assertGreaterEqual(text.count("if melhor_variante is not None:"), 2)
        self.assertIn('"_variant_width": w', text)
        self.assertIn('"_variant_height": h', text)

    def test_vi6_report_persistence_is_batched_not_every_scene(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_vi6_persist_now", text)
        self.assertIn("numero % 4 == 0", text)
        self.assertIn("STORYBOARD=PERSIST_DEFERRED", text)

    def test_media_runtime_is_profiled(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('from production_profiler import record as _sap_profile_record', text)
        self.assertIn('"media_acquisition"', text)
        self.assertIn('"media_scene"', text)
        self.assertIn('"media_stage"', text)

    def test_resume_records_stage_timings(self):
        text = (ROOT / "resume_after_semantic_fix.py").read_text(encoding="utf-8")
        self.assertIn("from production_profiler import record as profile_record", text)
        self.assertIn("stage_started = time.monotonic()", text)
        self.assertIn("ETAPA OK: {title} ({elapsed:.1f}s)", text)

    def test_profiler_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            with mock.patch.object(production_profiler, "REPORT_DIR", report_dir):
                production_profiler.record(
                    "media_scene",
                    1.25,
                    short_id="abc",
                    category="media",
                    scene=3,
                )
                production_profiler.record(
                    "media_scene",
                    2.75,
                    short_id="abc",
                    category="media",
                    scene=5,
                )
                rows = production_profiler.summarize("abc")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["count"], 2)
                self.assertAlmostEqual(rows[0]["total_seconds"], 4.0)

    def test_strict_must_remains_fail_closed(self):
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)
        self.assertIn("hits >= total", strict)


if __name__ == "__main__":
    unittest.main()
