import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeConsistencyTests(unittest.TestCase):
    def test_preflight_compiles_critical_shared_modules(self):
        text = (ROOT / "preflight_check.sh").read_text(encoding="utf-8")
        for name in (
            "gemini_runtime.py",
            "media_emergency_fallback.py",
            "media_must_priority.py",
            "media_strict_must_guard.py",
            "media_acquisition_recovery.py",
        ):
            self.assertIn(name, text)

    def test_health_checks_shared_runtimes(self):
        text = (ROOT / "health_check.sh").read_text(encoding="utf-8")
        self.assertIn("gemini_runtime.py", text)
        self.assertIn("media_must_priority.py", text)
        self.assertIn('"gemini_runtime"', text)
        self.assertIn('"media_must_priority"', text)

    def test_critical_scene_modules_honor_runtime_base(self):
        for name in (
            "scene_truth_refiner_6_7.py",
            "wikimedia_source.py",
            "editorial_continuity.py",
            "semantic_integrity_gate.py",
            "editorial_gate.py",
        ):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn('os.getenv("SHORTAUTOPRO_BASE"', text)

    def test_pipeline_has_stage_specific_watchdogs(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("def _stage_timeout_seconds", text)
        self.assertIn("SAP_STAGE_TIMEOUT_AI_SECONDS", text)
        self.assertIn("SAP_STAGE_TIMEOUT_MEDIA_SECONDS", text)
        self.assertIn("SAP_STAGE_TIMEOUT_RENDER_SECONDS", text)
        self.assertIn("SAP_STAGE_TIMEOUT_DEFAULT_SECONDS", text)
        self.assertNotIn(
            'stage_timeout = env_int("SAP_STAGE_TIMEOUT_SECONDS", 1800',
            text,
        )


if __name__ == "__main__":
    unittest.main()
