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

    def test_generic_temp_cleanup_resnapshots_active_runs_before_delete(self):
        text = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn("current_active=active_ids()", text)
        self.assertIn('if p.parent==BASE/"temp":', text)
        self.assertNotIn("active=active_ids()\n  for p in remove:", text)


    def test_hook_retries_incomplete_successful_gemini_response(self):
        text = (ROOT / "hook_engine.py").read_text(encoding="utf-8")
        self.assertIn("resposta Gemini incompleta", text)
        self.assertIn('r.headers.get("Retry-After")', text)
        self.assertIn("if tentativa == 4:", text)

    def test_secondary_asset_download_has_total_size_cap(self):
        text = (ROOT / "multi_asset_director.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MULTI_ASSET_MAX_BYTES", text)
        self.assertIn("if declared>MAX_ASSET_BYTES:return False", text)
        self.assertIn("if total>MAX_ASSET_BYTES:return False", text)


if __name__ == "__main__":
    unittest.main()
