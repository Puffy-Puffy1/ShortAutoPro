import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeConfigHarmonyRound10Tests(unittest.TestCase):
    def test_operational_modules_use_shared_env_int(self):
        modules = (
            "main.py",
            "media_stage_runtime.py",
            "video_professional.py",
            "v6_professional.py",
            "resume_short_runtime.py",
            "production_center.py",
            "client_job_runner.py",
        )
        for name in modules:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("runtime_config import env_int", text, name)

    def test_existing_operational_bounds_are_preserved(self):
        expectations = {
            "main.py": 'env_int("SAP_CONTROL_COMMAND_TIMEOUT", 7200, 300, 21600)',
            "media_stage_runtime.py": 'env_int("SAP_MEDIA_STAGE_ROUNDS", 2, 1, 3)',
            "video_professional.py": 'env_int("SHORT_SCENE_RENDER_TIMEOUT", 300, 60, 1200)',
            "v6_professional.py": 'env_int("SAP_RENDER_THREADS", 0, 0, 8)',
            "resume_short_runtime.py": 'env_int("SAP_RESUME_FULL_RERUN_TIMEOUT", 7200, 600, 21600)',
            "production_center.py": 'env_int("SAP_CONTROL_COMMAND_TIMEOUT", 7200, 300, 21600)',
            "client_job_runner.py": 'env_int("SAP_CLIENT_JOB_TIMEOUT", 7200, 600, 21600)',
        }
        for name, needle in expectations.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(needle, text, name)

    def test_video_renderer_no_longer_duplicates_env_int_parser(self):
        text = (ROOT / "video_professional.py").read_text(encoding="utf-8")
        self.assertNotIn("def timeout_value(", text)
        self.assertIn('env_int("SHORT_QTD_CENAS", 12, 6, 20)', text)

    def test_media_runtime_uses_shared_parser_for_round_timeout(self):
        text = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn('env_int("SAP_MEDIA_ROUND_TIMEOUT", 75, 30, 150)', text)


if __name__ == "__main__":
    unittest.main()
