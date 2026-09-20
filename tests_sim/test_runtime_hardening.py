import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHardeningTests(unittest.TestCase):
    def test_process_guard_uses_new_session_and_kills_process_group(self):
        text = (ROOT / "subprocess_guard.py").read_text(encoding="utf-8")
        self.assertIn("start_new_session=True", text)
        self.assertIn("os.killpg(proc.pid, signal.SIGTERM)", text)
        self.assertIn("os.killpg(proc.pid, signal.SIGKILL)", text)

    def test_canonical_long_running_paths_use_process_guard(self):
        for name in (
            "main.py",
            "media_stage_runtime.py",
            "client_job_runner.py",
            "production_center.py",
            "resume_short_runtime.py",
        ):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("run_group", text, name)

    def test_resume_full_rerun_is_bounded(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("SAP_RESUME_FULL_RERUN_TIMEOUT", text)
        self.assertIn("full rerun excedeu timeout", text)

    def test_storage_probes_kernel_lock_and_reports_actual_removals(self):
        text = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn("LOCK_EX|fcntl.LOCK_NB", text)
        self.assertIn("lock.unlink(missing_ok=True)", text)
        self.assertIn('"planned"', text)
        self.assertIn('"skipped_active"', text)


if __name__ == "__main__":
    unittest.main()
