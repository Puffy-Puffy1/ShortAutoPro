import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeInfraHealthHarmonyRound11Tests(unittest.TestCase):
    def test_health_initializes_error_counter_before_legacy_check(self):
        text = (ROOT / "health_check.sh").read_text(encoding="utf-8")
        init = text.index("ERROS=0")
        legacy = text.index('if [ -f "$BASE/tools/purge_legacy_runtime.py" ]')
        self.assertLess(init, legacy)
        self.assertEqual(text.count("ERROS=0"), 1)

    def test_preflight_and_health_require_shared_runtime_infrastructure(self):
        required = (
            "runtime_config.py",
            "subprocess_guard.py",
            "production_profiler.py",
            "production_doctor.py",
        )
        for name in ("preflight_check.sh", "health_check.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for item in required:
                self.assertIn(item, text, f"{name}: {item}")

    def test_repo_audit_requires_shared_runtime_infrastructure(self):
        text = (ROOT / "tools" / "repo_audit.py").read_text(encoding="utf-8")
        for item in (
            '"runtime_config.py"',
            '"subprocess_guard.py"',
            '"production_profiler.py"',
            '"production_doctor.py"',
        ):
            self.assertIn(item, text)

    def test_remaining_core_runtime_config_is_centralized(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        storage = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn('SAP_STAGE_TIMEOUT_SECONDS', main)
        self.assertIn('env_int("SAP_STAGE_TIMEOUT_AI_SECONDS", 240, 60, 900)', main)
        self.assertIn('env_int("SAP_STAGE_TIMEOUT_MEDIA_SECONDS", 420, 120, 900)', main)
        self.assertIn('env_int("SHORT_STORAGE_KEEP_PROJECTS",3,1,20)', storage)
        self.assertIn('env_float("SAP_MIN_FREE_GB",1.2,0.5,20.0)', storage)
        self.assertNotIn("def bounded_int(", storage)


if __name__ == "__main__":
    unittest.main()
