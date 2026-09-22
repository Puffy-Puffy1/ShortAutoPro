import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeRuntimeHardeningRound5Tests(unittest.TestCase):
    def test_profiler_uses_cross_process_file_lock(self):
        text = (ROOT / "production_profiler.py").read_text(encoding="utf-8")
        self.assertIn("import fcntl", text)
        self.assertIn("fcntl.flock(handle.fileno(), fcntl.LOCK_EX)", text)
        self.assertIn("handle.flush()", text)
        self.assertIn("fcntl.LOCK_UN", text)

    def test_missing_media_report_is_atomic(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("tempfile.mkstemp(", text)
        self.assertIn("def _sap_atomic_media_checkpoint(", text)
        self.assertIn("os.replace(tmp, MISSING_REPORT)", text)
        self.assertIn("os.fsync(handle.fileno())", text)

    def test_timeout_cleanup_tolerates_os_signal_errors(self):
        text = (ROOT / "subprocess_guard.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("except OSError:"), 2)
        self.assertNotIn("except ProcessLookupError:", text)

    def test_wikimedia_has_bounded_transient_retry(self):
        text = (ROOT / "wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("for attempt in range(2):", text)
        for status in ("500", "502", "503", "504"):
            self.assertIn(status, text)
        self.assertIn('r.status_code', text)
        self.assertIn('time.sleep(\n                    0.6', text)
        self.assertIn("401/403 and 429 open a bounded circuit immediately", text)


if __name__ == "__main__":
    unittest.main()
